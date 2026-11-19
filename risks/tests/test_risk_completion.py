# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A risk is opened from its assessment on one screen, then worked on its page.

A risk has no register dialog : it comes out of an assessment, so the generic
tests of ``core/tests/test_usability_standard.py`` that create a record from
its register do not apply to it. This file holds them for the risk, with what
is particular to it : the assessment it is opened from is not asked, its owner
is never assumed, and its rating is read on the scales of its assessment.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from assets.tests.factories import EssentialAssetFactory
from core.completeness import completeness_of
from risks.forms import RiskCreateForm, RiskUpdateForm
from risks.models import Risk
from risks.tests.factories import RiskAssessmentFactory, RiskCriteriaFactory, RiskFactory, ScaleLevelFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
SECTIONS = ("identity", "evaluation", "treatment", "relations")


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _mcp(user, tool, arguments):
    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    server = McpServer()
    register_all_tools(server)
    answer = server.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }), user)
    return json.loads(answer["result"]["content"][0]["text"])


def _linkable_asset():
    from core.lifecycle import linkable_states

    asset = EssentialAssetFactory()
    type(asset).objects.filter(pk=asset.pk).update(workflow_state=sorted(linkable_states(type(asset)))[0])
    asset.refresh_from_db()
    return asset


class TestOpeningARiskIsShort:
    def test_the_assessment_it_is_opened_from_is_not_asked(self, admin):
        assessment = RiskAssessmentFactory()

        form = RiskCreateForm(user=admin, initial={"assessment": assessment.pk})

        assert list(form.fields) == [
            "assessment", "name", "description", "risk_source", "risk_owner", "affected_essential_assets",
        ]
        assert form.fields["assessment"].widget.is_hidden
        assert len([f for f in form.fields.values() if not f.widget.is_hidden]) == 5
        assert form.is_multistep is False

    def test_its_owner_is_never_assumed(self, admin):
        form = RiskCreateForm(user=admin, initial={"assessment": RiskAssessmentFactory().pk})

        # Whoever notes a risk is seldom the one entitled to accept it.
        assert form.fields["risk_owner"].initial is None

    def test_a_risk_is_created_and_lands_on_its_page(self, client, admin):
        assessment = RiskAssessmentFactory()

        response = client.post(
            reverse("risks:risk-create") + f"?assessment={assessment.pk}",
            {"assessment": str(assessment.pk), "name": "Customer data leaked after a phishing attack",
             "risk_source": "manual", "description": ""},
            **DRAWER,
        )

        risk = Risk.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == risk.get_absolute_url()
        assert risk.assessment == assessment and risk.risk_owner is None and risk.created_by == admin

    def test_outside_an_assessment_the_reader_is_sent_to_the_assessments(self, client, admin):
        response = client.get(reverse("risks:risk-create"))

        assert response.status_code == 302
        assert response.url == reverse("risks:assessment-list")


class TestWhatItStillNeeds:
    def test_a_new_risk_lists_what_would_make_it_useful(self, client, admin):
        risk = RiskFactory()
        edit = reverse("risks:risk-update", kwargs={"pk": risk.pk})

        report = completeness_of(risk)
        html = client.get(risk.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["rating", "owner", "decision", "assets"]
        # Advice : nothing holds its lifecycle back.
        assert report.blocking_missing == [] and report.can_advance
        assert "Rate the current likelihood and impact" in html
        for section in SECTIONS:
            assert f'href="{edit}?section={section}"' in html, section

    def test_what_is_done_leaves_the_list(self, admin):
        risk = RiskFactory(
            current_likelihood=3, current_impact=4, risk_owner=admin, treatment_decision="mitigate",
        )
        risk.affected_essential_assets.add(EssentialAssetFactory())

        assert completeness_of(risk).is_complete

    def test_one_rating_out_of_two_is_not_a_rating(self):
        risk = RiskFactory(current_likelihood=3)

        assert "rating" in [item.key for item in completeness_of(risk).advised_missing]


class TestItsPage:
    def test_every_section_of_its_form_opens_on_its_own(self, admin):
        risk = RiskFactory()

        fields = {
            section: list(RiskUpdateForm(instance=risk, user=admin, section=section).fields)
            for section in SECTIONS
        }

        assert fields["evaluation"] == [
            "initial_likelihood", "initial_impact", "current_likelihood", "current_impact",
        ]
        assert fields["treatment"] == ["treatment_decision", "treatment_justification", "priority", "review_date"]
        assert fields["relations"] == [
            "affected_essential_assets", "affected_support_assets", "linked_requirements",
        ]
        assert all(step.key for step in RiskUpdateForm.steps)

    def test_rating_it_leaves_the_rest_of_the_risk_alone(self, client, admin):
        asset = _linkable_asset()
        risk = RiskFactory(name="Customer data leaked", treatment_decision="mitigate")
        risk.affected_essential_assets.add(asset)
        edit = reverse("risks:risk-update", kwargs={"pk": risk.pk})

        response = client.post(
            edit, {"_section": "evaluation", "current_likelihood": "3", "current_impact": "4",
                   "initial_likelihood": "", "initial_impact": ""},
            **DRAWER,
        )

        risk.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert (risk.current_likelihood, risk.current_impact) == (3, 4)
        assert risk.name == "Customer data leaked" and risk.treatment_decision == "mitigate"
        assert list(risk.affected_essential_assets.all()) == [asset]

    def test_its_rating_is_read_on_the_scales_of_its_assessment(self, admin):
        criteria = RiskCriteriaFactory()
        ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=1, name="Once in a career")
        risk = RiskFactory(assessment=RiskAssessmentFactory(risk_criteria=criteria))

        form = RiskUpdateForm(instance=risk, user=admin, section="evaluation")

        assert ("1", "1 - Once in a career") in [(str(v), label) for v, label in form.fields["current_likelihood"].choices]

    def test_its_assessment_and_its_source_are_set_once(self, admin):
        form = RiskUpdateForm(instance=RiskFactory(), user=admin, section="identity")

        assert form.fields["assessment"].disabled and form.fields["risk_source"].disabled

    def test_a_reader_is_offered_no_edit(self, client):
        reader = UserFactory(is_superuser=False)
        group = GroupFactory()
        group.permissions.add(PermissionFactory(codename="risks.risk.read"))
        group.users.add(reader)
        client.force_login(reader)
        risk = RiskFactory()
        edit = reverse("risks:risk-update", kwargs={"pk": risk.pk})

        response = client.get(risk.get_absolute_url())

        assert response.status_code == 200
        assert edit not in response.content.decode()

    def test_what_it_would_affect_is_said_in_words(self, client, admin):
        risk = RiskFactory(impact_confidentiality=True, impact_availability=True)

        html = client.get(risk.get_absolute_url()).content.decode()

        assert "Security needs affected" in html and "Impact C / I / A" not in html
        assert "Confidentiality" in html and "Availability" in html

    def test_the_empty_register_says_where_risks_come_from(self, client, admin):
        html = client.get(reverse("risks:risk-list")).content.decode()

        assert "No risk yet." in html
        assert "open a risk assessment" in html


class TestTheApiAndTheMcpServer:
    def test_they_report_the_completeness_of_one_risk(self, admin):
        risk = RiskFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/risks/risks/{risk.pk}/").json()
        one = one.get("data", one)
        read = _mcp(admin, "get_risk", {"id": str(risk.pk)})

        assert [item["key"] for item in one["completeness"]["missing"]] == ["rating", "owner", "decision", "assets"]
        assert [item["key"] for item in read["completeness"]["missing"]] == ["rating", "owner", "decision", "assets"]

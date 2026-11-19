# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A risk assessment is created on one screen, then completed on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the risk assessment : its method is a decision nobody takes for
the reader, and the criteria the organisation marked as its default are the
answer unless the reader picks others.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from risks.forms import RiskAssessmentCreateForm, RiskAssessmentUpdateForm
from risks.models import RiskAssessment
from risks.tests.factories import RiskAssessmentFactory, RiskCriteriaFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


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


class TestCreationIsShort:
    def test_it_asks_how_it_is_conducted_by_whom_and_on_which_scales(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = RiskAssessmentCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "description", "methodology", "assessor", "risk_criteria"]
        assert form.is_multistep is False

    def test_its_method_is_a_decision_nobody_takes_for_the_reader(self, client, admin):
        html = client.get(reverse("risks:assessment-create"), **DRAWER).content.decode()
        select = html[html.index('name="methodology"'):]
        select = select[:select.index("</select>")]

        # The model answers "ISO 27005" : the form opens on no answer.
        assert 'value="" selected' in select
        assert select.count("selected") == 1

    def test_whoever_creates_it_conducts_it_unless_they_say_otherwise(self, admin):
        form = RiskAssessmentCreateForm(user=admin)

        assert form.fields["assessor"].initial == admin.pk

    def test_the_default_criteria_of_the_organisation_are_the_answer(self, admin):
        RiskCriteriaFactory(name="Other criteria")
        default = RiskCriteriaFactory(name="Corporate criteria", is_default=True)

        form = RiskAssessmentCreateForm(user=admin)

        assert form.fields["risk_criteria"].initial == default.pk

    def test_with_no_default_criteria_none_is_chosen_for_the_reader(self, admin):
        RiskCriteriaFactory()

        form = RiskAssessmentCreateForm(user=admin)

        assert form.fields["risk_criteria"].initial is None

    def test_an_assessment_is_created_and_lands_on_its_page(self, client, admin):
        criteria = RiskCriteriaFactory(is_default=True)

        response = client.post(
            reverse("risks:assessment-create"),
            {"name": "Risk assessment of the customer portal", "methodology": "iso27005",
             "assessor": str(admin.pk), "risk_criteria": str(criteria.pk), "description": ""},
            **DRAWER,
        )

        assessment = RiskAssessment.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == assessment.get_absolute_url()
        assert assessment.assessor == admin and assessment.risk_criteria == criteria

    def test_leaving_the_method_out_is_refused(self, client, admin):
        response = client.post(
            reverse("risks:assessment-create"),
            {"name": "Risk assessment of the customer portal", "description": ""},
            **DRAWER,
        )

        assert response.status_code == 200
        assert not RiskAssessment.objects.exists()

    def test_an_existing_assessment_keeps_the_method_it_has(self, admin):
        assessment = RiskAssessmentFactory(methodology="ebios_rm")

        form = RiskAssessmentUpdateForm(instance=assessment, user=admin, section="identity")

        assert form["methodology"].value() == "ebios_rm"


class TestWhatItStillNeeds:
    def test_a_bare_assessment_lists_what_would_make_it_useful(self, client, admin):
        assessment = RiskAssessmentFactory()
        edit = reverse("risks:assessment-update", kwargs={"pk": assessment.pk})

        report = completeness_of(assessment)
        html = client.get(assessment.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["criteria", "assessor", "review"]
        # Advice : nothing holds its lifecycle back.
        assert report.blocking_missing == [] and report.can_advance
        assert "Choose the risk criteria" in html
        assert f'href="{edit}?section=identity"' in html
        assert f'href="{edit}?section=planning"' in html

    def test_the_card_of_the_dates_sets_them_and_leaves_the_rest_alone(self, client, admin):
        assessment = RiskAssessmentFactory(name="Customer portal", methodology="ebios_rm")
        edit = reverse("risks:assessment-update", kwargs={"pk": assessment.pk})

        response = client.post(
            edit, {"_section": "planning", "assessment_date": "2026-06-01", "next_review_date": "2027-06-01",
                   "summary": ""},
            **DRAWER,
        )

        assessment.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert str(assessment.next_review_date) == "2027-06-01"
        assert assessment.name == "Customer portal" and assessment.methodology == "ebios_rm"


class TestThePage:
    def test_dates_nobody_set_read_as_one_line(self, client, admin):
        html = client.get(RiskAssessmentFactory().get_absolute_url()).content.decode()

        assert "Not filled in yet : Assessment date, Next review, Summary." in html

    def test_the_empty_register_explains_and_offers_the_first_assessment(self, client, admin):
        html = client.get(reverse("risks:assessment-list")).content.decode()

        assert "No risk assessment yet." in html
        create = reverse("risks:assessment-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApiAndTheMcpServer:
    def test_they_report_the_completeness_of_one_assessment(self, admin):
        assessment = RiskAssessmentFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/risks/assessments/{assessment.pk}/").json()
        one = one.get("data", one)
        many = api.get("/api/v1/risks/assessments/").json()
        rows = many.get("data", many.get("results", many))
        read = _mcp(admin, "get_risk_assessment", {"id": str(assessment.pk)})

        assert [item["key"] for item in one["completeness"]["missing"]] == ["criteria", "assessor", "review"]
        assert rows and "completeness" not in rows[0]
        assert [item["key"] for item in read["completeness"]["missing"]] == ["criteria", "assessor", "review"]

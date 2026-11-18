# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An ISO 27005 analysis is opened on one screen, then rated on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the analysis : the assessment it is opened from is not asked,
its ratings are picked on the named levels of that assessment's criteria, and
an address that names no assessment within reach never raises.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, UserFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from risks.forms import ISO27005RiskCreateForm, ISO27005RiskUpdateForm
from risks.models import ISO27005Risk
from risks.tests.factories import (
    RiskAssessmentFactory,
    RiskCriteriaFactory,
    ScaleLevelFactory,
    ThreatFactory,
    VulnerabilityFactory,
)

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _analysis(**fields):
    fields.setdefault("assessment", RiskAssessmentFactory(methodology="iso27005"))
    fields.setdefault("threat", ThreatFactory())
    fields.setdefault("vulnerability", VulnerabilityFactory())
    return ISO27005Risk.objects.create(**fields)


def _criteria_with_scales():
    criteria = RiskCriteriaFactory()
    ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=1, name="Once in a career")
    ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=2, name="Once a year")
    ScaleLevelFactory(criteria=criteria, scale_type="impact", level=1, name="A bad day")
    return criteria


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


class TestOpeningAnAnalysisIsShort:
    def test_it_asks_for_the_scenario_and_what_it_would_harm(self, admin):
        form = ISO27005RiskCreateForm(user=admin)

        assert list(form.fields) == ["assessment", "threat", "vulnerability", "affected_essential_assets", "description"]
        assert form.is_multistep is False

    def test_the_assessment_it_is_opened_from_is_not_asked(self, client, admin):
        assessment = RiskAssessmentFactory(methodology="iso27005")

        html = client.get(reverse("risks:iso27005-create"), {"assessment": str(assessment.pk)}, **DRAWER).content.decode()

        assert f'<input type="hidden" name="assessment" value="{assessment.pk}"' in html

    def test_only_assessments_conducted_with_that_method_are_offered(self, admin):
        iso = RiskAssessmentFactory(methodology="iso27005")
        RiskAssessmentFactory(methodology="ebios_rm")

        form = ISO27005RiskCreateForm(user=admin)

        assert list(form.fields["assessment"].queryset) == [iso]

    def test_an_analysis_is_created_and_lands_on_its_page(self, client, admin):
        assessment = RiskAssessmentFactory(methodology="iso27005")
        threat, vulnerability = ThreatFactory(), VulnerabilityFactory()

        response = client.post(
            reverse("risks:iso27005-create") + f"?assessment={assessment.pk}",
            {"assessment": str(assessment.pk), "threat": str(threat.pk), "vulnerability": str(vulnerability.pk),
             "description": ""},
            **DRAWER,
        )

        analysis = ISO27005Risk.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        # On its page, where it is rated : not back on the assessment.
        assert response.headers["HX-Redirect"] == analysis.get_absolute_url()
        assert analysis.risk_level is None


class TestAnAddressThatNamesNoAssessmentWithinReach:
    @pytest.mark.parametrize("url_name", ["risks:iso27005-create", "risks:risk-create"])
    def test_a_malformed_one_does_not_raise(self, client, admin, url_name):
        response = client.get(reverse(url_name), {"assessment": "garbage"})

        # The analysis asks which assessment; the risk sends to the assessments.
        assert response.status_code in (200, 302)

    def test_an_assessment_out_of_reach_is_not_the_answer(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        group = GroupFactory()
        group.allowed_scopes.add(mine)
        user = UserFactory(is_superuser=False)
        group.users.add(user)
        from accounts.tests.factories import PermissionFactory

        for codename in ("risks.iso27005.create", "risks.risk.create"):
            group.permissions.add(PermissionFactory(codename=codename))
        assessment = RiskAssessmentFactory(methodology="iso27005")
        assessment.scopes.add(theirs)
        client.force_login(user)

        analysis_form = client.get(reverse("risks:iso27005-create"), {"assessment": str(assessment.pk)})
        risk_form = client.get(reverse("risks:risk-create"), {"assessment": str(assessment.pk)})

        assert str(assessment.pk) not in analysis_form.content.decode()
        assert risk_form.status_code == 302 and risk_form.url == reverse("risks:assessment-list")


class TestItsRatings:
    def test_they_are_picked_on_the_named_levels_of_its_criteria(self, admin):
        analysis = _analysis(assessment=RiskAssessmentFactory(methodology="iso27005", risk_criteria=_criteria_with_scales()))

        form = ISO27005RiskUpdateForm(instance=analysis, user=admin, section="evaluation")

        assert list(form.fields["threat_likelihood"].choices) == [
            ("", "---------"), (1, "1 - Once in a career"), (2, "2 - Once a year"),
        ]
        assert (1, "1 - A bad day") in list(form.fields["impact_availability"].choices)

    def test_a_level_rated_on_scales_that_changed_since_is_kept(self, admin):
        analysis = _analysis(
            assessment=RiskAssessmentFactory(methodology="iso27005", risk_criteria=_criteria_with_scales()),
            threat_likelihood=5,
        )

        form = ISO27005RiskUpdateForm(instance=analysis, user=admin, section="evaluation")

        assert (5, "5") in list(form.fields["threat_likelihood"].choices)

    def test_rating_it_leaves_the_scenario_alone(self, client, admin):
        analysis = _analysis(
            assessment=RiskAssessmentFactory(methodology="iso27005", risk_criteria=_criteria_with_scales()),
            description="<p>Phishing of a maintainer.</p>",
        )
        edit = reverse("risks:iso27005-update", kwargs={"pk": analysis.pk})

        response = client.post(
            edit,
            {"_section": "evaluation", "threat_likelihood": "2", "vulnerability_exposure": "1",
             "impact_confidentiality": "", "impact_integrity": "", "impact_availability": "1",
             "existing_controls": ""},
            **DRAWER,
        )

        analysis.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert (analysis.combined_likelihood, analysis.max_impact) == (2, 1)
        assert "Phishing of a maintainer" in analysis.description

    def test_a_value_off_the_scale_is_refused(self, admin):
        analysis = _analysis(assessment=RiskAssessmentFactory(methodology="iso27005", risk_criteria=_criteria_with_scales()))

        form = ISO27005RiskUpdateForm(
            {"_section": "evaluation", "threat_likelihood": "9"}, instance=analysis, user=admin, section="evaluation",
        )

        assert not form.is_valid() and "threat_likelihood" in form.errors


class TestWhatItStillNeeds:
    def test_a_new_analysis_asks_for_its_rating_and_what_it_would_harm(self, client, admin):
        analysis = _analysis()
        edit = reverse("risks:iso27005-update", kwargs={"pk": analysis.pk})

        report = completeness_of(analysis)
        html = client.get(analysis.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["rating", "assets"]
        assert report.blocking_missing == [] and report.can_advance
        assert f'href="{edit}?section=evaluation"' in html
        assert f'href="{edit}?section=assets"' in html

    def test_a_likelihood_alone_is_not_a_rating(self):
        analysis = _analysis(threat_likelihood=3)

        assert "rating" in [item.key for item in completeness_of(analysis).advised_missing]


class TestThePageAndItsRegister:
    def test_the_dialogs_say_analysis_like_the_rest_of_the_product(self, client, admin):
        html = client.get(reverse("risks:iso27005-create"), **DRAWER).content.decode()

        assert "New ISO 27005 analysis" in html and "New ISO 27005 risk" not in html

    def test_a_row_of_the_register_carries_one_link_per_cell(self, client, admin):
        """Two links stacked in a cell are closer than a pointer target allows (WCAG 2.5.8)."""
        import re

        _analysis()

        html = client.get(reverse("risks:iso27005-table-body")).content.decode()
        cells = re.findall(r'<td data-col="(?:reference|scenario)">(.*?)</td>', html, re.S)

        assert len(cells) == 2
        assert all(cell.count("<a ") == 1 for cell in cells)

    def test_the_empty_register_explains_and_offers_the_first_analysis(self, client, admin):
        html = client.get(reverse("risks:iso27005-list")).content.decode()

        assert "No ISO 27005 analysis yet." in html
        create = reverse("risks:iso27005-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApiAndTheMcpServer:
    def test_they_report_the_completeness_of_one_analysis(self, admin):
        analysis = _analysis()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/risks/iso27005-risks/{analysis.pk}/").json()
        one = one.get("data", one)
        read = _mcp(admin, "get_iso27005_risk", {"id": str(analysis.pk)})

        assert [item["key"] for item in one["completeness"]["missing"]] == ["rating", "assets"]
        assert [item["key"] for item in read["completeness"]["missing"]] == ["rating", "assets"]

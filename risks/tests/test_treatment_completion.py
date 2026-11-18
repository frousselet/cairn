# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A treatment plan and a risk acceptance are created short, then completed on their page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to these two : both are about a risk, which is not asked when
they are opened from its page; the target of a plan is read on the scales of
that risk's assessment; and an action is a row added to its plan.
"""

import json
from datetime import date

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from core.completeness import completeness_of
from risks.forms import (
    RiskAcceptanceCreateForm,
    RiskTreatmentPlanCreateForm,
    RiskTreatmentPlanUpdateForm,
    TreatmentActionCreateForm,
)
from risks.models import RiskAcceptance, RiskTreatmentPlan, TreatmentAction
from risks.tests.factories import (
    RiskAcceptanceFactory,
    RiskAssessmentFactory,
    RiskCriteriaFactory,
    RiskFactory,
    RiskTreatmentPlanFactory,
    ScaleLevelFactory,
    TreatmentActionFactory,
)

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


class TestATreatmentPlan:
    def test_creation_asks_what_will_be_done_about_which_risk_by_whom_and_for_when(self, admin):
        form = RiskTreatmentPlanCreateForm(user=admin)

        assert list(form.fields) == ["risk", "name", "description", "treatment_type", "owner", "target_date"]
        assert form.is_multistep is False
        # Whoever opens the plan carries it unless they say otherwise.
        assert form.fields["owner"].initial == admin.pk

    def test_opened_from_a_risk_that_risk_is_not_asked(self, client, admin):
        risk = RiskFactory()

        html = client.get(reverse("risks:treatment-plan-create"), {"risk": str(risk.pk)}, **DRAWER).content.decode()

        assert f'<input type="hidden" name="risk" value="{risk.pk}"' in html

    def test_the_page_of_a_risk_opens_a_plan_for_that_risk(self, client, admin):
        risk = RiskFactory()

        html = client.get(risk.get_absolute_url()).content.decode()

        assert f'href="{reverse("risks:treatment-plan-create")}?risk={risk.pk}"' in html

    def test_a_malformed_risk_in_the_address_does_not_raise(self, client, admin):
        for url_name in ("risks:treatment-plan-create", "risks:acceptance-create"):
            response = client.get(reverse(url_name), {"risk": "garbage"})

            assert response.status_code == 200, url_name

    def test_a_malformed_risk_posted_to_the_form_is_refused_not_raised(self, client, admin):
        """The form reads the criteria of the posted risk to offer its scales : a
        value that is not an identifier used to raise there."""
        response = client.post(
            reverse("risks:treatment-plan-create"),
            {"risk": "garbage", "name": "Segment the industrial network", "treatment_type": "mitigate"},
            **DRAWER,
        )

        assert response.status_code == 200
        assert not RiskTreatmentPlan.objects.exists()

    def test_a_plan_is_created_and_lands_on_its_page(self, client, admin):
        risk = RiskFactory()

        response = client.post(
            reverse("risks:treatment-plan-create") + f"?risk={risk.pk}",
            {"risk": str(risk.pk), "name": "Segment the industrial network", "treatment_type": "mitigate",
             "owner": str(admin.pk), "description": ""},
            **DRAWER,
        )

        plan = RiskTreatmentPlan.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == plan.get_absolute_url()
        assert plan.risk == risk and plan.owner == admin

    def test_its_target_is_read_on_the_scales_of_the_assessment_of_its_risk(self, admin):
        criteria = RiskCriteriaFactory()
        ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=1, name="Once in a career")
        plan = RiskTreatmentPlanFactory(risk=RiskFactory(assessment=RiskAssessmentFactory(risk_criteria=criteria)))

        form = RiskTreatmentPlanUpdateForm(instance=plan, user=admin, section="planning")

        assert (1, "1 - Once in a career") in list(form.fields["expected_residual_likelihood"].choices)

    def test_its_page_lists_what_would_make_it_useful(self, client, admin):
        plan = RiskTreatmentPlanFactory()
        edit = reverse("risks:treatment-plan-update", kwargs={"pk": plan.pk})

        report = completeness_of(plan)
        html = client.get(plan.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["target", "owner", "deadline", "actions"]
        assert report.blocking_missing == [] and report.can_advance
        assert f'href="{edit}?section=planning"' in html
        assert f'href="{edit}?section=relations"' in html
        # The actions are added from the page : the line opens their dialog.
        assert f'href="{reverse("risks:treatment-action-create", args=[plan.pk])}"' in html

    def test_an_action_answers_the_last_line(self, admin):
        plan = RiskTreatmentPlanFactory(
            owner=admin, target_date=date(2027, 1, 31), expected_residual_likelihood=1, expected_residual_impact=2,
        )
        TreatmentActionFactory(treatment_plan=plan)

        assert completeness_of(plan).is_complete


class TestAnActionOfAPlan:
    def test_it_is_added_on_one_screen_to_the_plan_it_is_opened_from(self, client, admin):
        plan = RiskTreatmentPlanFactory()

        form = TreatmentActionCreateForm(initial={"treatment_plan": plan.pk})
        html = client.get(reverse("risks:treatment-action-create", args=[plan.pk]), **DRAWER).content.decode()

        assert list(form.fields) == ["treatment_plan", "description", "owner", "target_date"]
        assert form.fields["treatment_plan"].widget.is_hidden
        assert f'<input type="hidden" name="treatment_plan" value="{plan.pk}"' in html

    def test_what_was_typed_in_the_editor_is_shown_formatted_not_as_markup(self, client, admin):
        """The description is typed in the rich-text editor, which stores
        markup : the row printed it as text, tags included."""
        plan = RiskTreatmentPlanFactory()
        TreatmentActionFactory(treatment_plan=plan, description="<p>Order the <strong>firewalls</strong>.</p>")

        html = client.get(plan.get_absolute_url()).content.decode()

        assert "<p>Order the <strong>firewalls</strong>.</p>" in html
        assert "&lt;p&gt;" not in html
        # Its deletion is confirmed in words.
        assert "This will permanently delete <strong>Order the firewalls.</strong>" in html

    def test_markup_the_editor_cannot_produce_is_dropped(self, client, admin):
        plan = RiskTreatmentPlanFactory()
        TreatmentActionFactory(
            treatment_plan=plan, description='<p onclick="steal()">Do it</p><script>alert(1)</script>',
        )

        html = client.get(plan.get_absolute_url()).content.decode()

        assert "<p>Do it</p>" in html
        assert "<p onclick" not in html and "<script>alert(1)" not in html

    def test_it_starts_as_planned(self, client, admin):
        plan = RiskTreatmentPlanFactory()

        response = client.post(
            reverse("risks:treatment-action-create", args=[plan.pk]),
            {"treatment_plan": str(plan.pk), "description": "<p>Order the firewalls.</p>"},
            **DRAWER,
        )

        action = TreatmentAction.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert action.treatment_plan == plan and action.status == "planned"


class TestARiskAcceptance:
    def test_creation_asks_which_risk_why_on_what_conditions_and_until_when(self, admin):
        form = RiskAcceptanceCreateForm(user=admin)

        assert list(form.fields) == ["risk", "justification", "conditions", "valid_until", "review_date"]
        assert form.is_multistep is False

    def test_opened_from_a_risk_that_risk_is_not_asked(self, client, admin):
        risk = RiskFactory()

        html = client.get(reverse("risks:acceptance-create"), {"risk": str(risk.pk)}, **DRAWER).content.decode()

        assert f'<input type="hidden" name="risk" value="{risk.pk}"' in html

    def test_an_acceptance_is_created_and_lands_on_its_page(self, client, admin):
        risk = RiskFactory()

        response = client.post(
            reverse("risks:acceptance-create"),
            {"risk": str(risk.pk), "justification": "<p>The fix costs more than the loss it prevents.</p>",
             "conditions": ""},
            **DRAWER,
        )

        acceptance = RiskAcceptance.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == acceptance.get_absolute_url()

    def test_its_page_asks_until_when_it_holds(self, client, admin):
        acceptance = RiskAcceptanceFactory()
        edit = reverse("risks:acceptance-update", kwargs={"pk": acceptance.pk})

        report = completeness_of(acceptance)
        html = client.get(acceptance.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["validity", "review"]
        assert report.blocking_missing == [] and report.can_advance
        assert f'href="{edit}?section=validity"' in html
        assert "Not filled in yet : Valid until, Review date." in html


class TestTheRegisters:
    @pytest.mark.parametrize("list_name, create_name, title", [
        ("risks:treatment-plan-list", "risks:treatment-plan-create", "No treatment plan yet."),
        ("risks:acceptance-list", "risks:acceptance-create", "No risk acceptance yet."),
    ])
    def test_an_empty_one_explains_and_offers_the_first(self, client, admin, list_name, create_name, title):
        html = client.get(reverse(list_name)).content.decode()

        assert title in html
        create = reverse(create_name)
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApiAndTheMcpServer:
    def test_they_report_the_completeness_of_one_record(self, admin):
        plan, acceptance = RiskTreatmentPlanFactory(), RiskAcceptanceFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/risks/treatment-plans/{plan.pk}/").json()
        one = one.get("data", one)
        other = api.get(f"/api/v1/risks/acceptances/{acceptance.pk}/").json()
        other = other.get("data", other)

        assert [item["key"] for item in one["completeness"]["missing"]] == ["target", "owner", "deadline", "actions"]
        assert [item["key"] for item in other["completeness"]["missing"]] == ["validity", "review"]
        assert [
            item["key"] for item in _mcp(admin, "get_risk_treatment_plan", {"id": str(plan.pk)})["completeness"]["missing"]
        ] == ["target", "owner", "deadline", "actions"]
        assert [
            item["key"] for item in _mcp(admin, "get_risk_acceptance", {"id": str(acceptance.pk)})["completeness"]["missing"]
        ] == ["validity", "review"]

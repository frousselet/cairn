# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An action plan is created on one screen, then completed on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the action plan : its gap and its remediation were asked at
creation and are now written on its page, so its lifecycle waits for them
before the plan is submitted for validation, on every surface.
"""

import json
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from compliance.constants import ActionPlanStatus
from compliance.forms import ComplianceActionPlanCreateForm
from compliance.models import ComplianceActionPlan
from compliance.tests.factories import ComplianceActionPlanFactory, FindingFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
REFUSAL = (
    'Before moving to "To validate", this remains to be done : '
    "fill in the gap description ; fill in the remediation plan."
)


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _in_a_month():
    return (timezone.localdate() + timedelta(days=30)).isoformat()


def _undefined_plan(**fields):
    """A plan as the creation dialog leaves it, moved to the step where it is defined."""
    plan = ComplianceActionPlanFactory(gap_description="", remediation_plan="", **fields)
    plan.transition_to(ActionPlanStatus.TO_DEFINE)
    return plan


def _tool(user, name, arguments):
    server = McpServer()
    register_all_tools(server)
    answer = server.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }), user)
    return answer


class TestCreationIsShort:
    def test_it_asks_what_is_to_be_done_by_whom_and_for_when(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = ComplianceActionPlanCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "description", "priority", "owner", "target_date"]
        assert form.is_multistep is False

    def test_the_priority_is_a_decision_nobody_takes_for_the_reader(self, client, admin):
        html = client.get(reverse("compliance:action-plan-create"), **DRAWER).content.decode()
        select = html[html.index('name="priority"'):]
        select = select[:select.index("</select>")]

        assert select.count("selected") == 1
        assert 'value="" selected' in select

    def test_a_plan_is_created_without_its_gap_and_lands_on_its_page(self, client, admin):
        response = client.post(
            reverse("compliance:action-plan-create"),
            {"name": "Encrypt the laptops", "priority": "high", "owner": str(admin.pk),
             "target_date": _in_a_month(), "description": ""},
            **DRAWER,
        )

        plan = ComplianceActionPlan.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == plan.get_absolute_url()
        assert plan.gap_description == "" and plan.remediation_plan == ""
        assert plan.workflow_state == plan.get_lifecycle().initial_step.code


class TestWhatItStillNeeds:
    def test_a_new_plan_lists_what_its_validation_waits_for(self, client, admin):
        plan = ComplianceActionPlanFactory(gap_description="", remediation_plan="")
        edit = reverse("compliance:action-plan-update", kwargs={"pk": plan.pk})

        report = completeness_of(plan)
        html = client.get(plan.get_absolute_url()).content.decode()

        assert [item.key for item in report.blocking_missing] == ["gap", "remediation"]
        assert [item.key for item in report.advised_missing] == ["assignees", "linkages"]
        assert "Fill in the gap description" in html
        assert f'href="{edit}?section=remediation"' in html
        assert f'href="{edit}?section=linkages"' in html

    def test_an_emptied_rich_text_is_not_an_answer(self):
        plan = ComplianceActionPlanFactory(gap_description="<p><br></p>", remediation_plan="<p>&nbsp;</p>")

        assert [item.key for item in completeness_of(plan).blocking_missing] == ["gap", "remediation"]

    def test_one_link_of_any_kind_answers_the_linkages(self):
        plan = ComplianceActionPlanFactory()
        plan.assignees.add(UserFactory())
        plan.findings.add(FindingFactory())

        assert completeness_of(plan).is_complete

    def test_the_card_of_the_gap_fills_it(self, client, admin):
        plan = _undefined_plan()
        edit = reverse("compliance:action-plan-update", kwargs={"pk": plan.pk})

        response = client.post(
            edit,
            {"_section": "remediation", "gap_description": "<p>Half of the laptops are not encrypted.</p>",
             "remediation_plan": "<p>Enable disk encryption through the fleet manager.</p>"},
            **DRAWER,
        )

        plan.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert completeness_of(plan).blocking_missing == []
        # The rest of the plan is untouched by the edit of one card.
        assert plan.priority == "medium" and plan.target_date is not None


class TestTheLifecycleWaitsForTheGapAndItsRemediation:
    def test_a_plan_can_be_defined_before_they_are_written(self):
        plan = ComplianceActionPlanFactory(gap_description="", remediation_plan="")

        plan.transition_to(ActionPlanStatus.TO_DEFINE)

        assert plan.workflow_state == ActionPlanStatus.TO_DEFINE

    def test_the_page_refuses_to_submit_it_and_says_what_remains(self, client, admin):
        plan = _undefined_plan()

        response = client.post(
            reverse("compliance:action-plan-transition", kwargs={"pk": plan.pk}),
            {"target_status": ActionPlanStatus.TO_VALIDATE},
            follow=True,
        )

        plan.refresh_from_db()
        assert plan.workflow_state == ActionPlanStatus.TO_DEFINE
        assert [str(m) for m in response.context["messages"]] == [REFUSAL]

    def test_the_api_refuses_it_with_the_same_sentence(self, admin):
        plan = _undefined_plan()
        api = APIClient()
        api.force_authenticate(admin)

        response = api.post(
            f"/api/v1/compliance/action-plans/{plan.pk}/transition/",
            {"status": ActionPlanStatus.TO_VALIDATE}, format="json",
        )

        plan.refresh_from_db()
        assert response.status_code == 400
        assert response.json()["error"]["detail"] == REFUSAL
        assert plan.workflow_state == ActionPlanStatus.TO_DEFINE

    def test_the_mcp_server_refuses_it_with_the_same_sentence(self, admin):
        plan = _undefined_plan()

        answer = _tool(admin, "action_plan_transition", {
            "action_plan_id": str(plan.pk), "target_status": ActionPlanStatus.TO_VALIDATE,
        })

        plan.refresh_from_db()
        assert answer["result"]["isError"] is True
        assert json.loads(answer["result"]["content"][0]["text"])["error"] == REFUSAL
        assert plan.workflow_state == ActionPlanStatus.TO_DEFINE

    def test_the_mcp_server_creates_a_plan_without_them_and_says_what_remains(self, admin):
        answer = _tool(admin, "create_action_plan", {
            "name": "Encrypt the laptops", "priority": "high", "owner_id": str(admin.pk),
            "target_date": _in_a_month(),
        })

        plan = ComplianceActionPlan.objects.get()
        read = _tool(admin, "get_action_plan", {"id": str(plan.pk)})
        read = json.loads(read["result"]["content"][0]["text"])
        assert answer["result"]["isError"] is False
        assert plan.gap_description == "" and plan.workflow_state == plan.get_lifecycle().initial_step.code
        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == [
            "gap", "remediation",
        ]

    def test_once_written_the_plan_is_submitted(self, client, admin):
        plan = _undefined_plan()
        plan.gap_description = "<p>Half of the laptops are not encrypted.</p>"
        plan.remediation_plan = "<p>Enable disk encryption through the fleet manager.</p>"
        plan.save()

        client.post(
            reverse("compliance:action-plan-transition", kwargs={"pk": plan.pk}),
            {"target_status": ActionPlanStatus.TO_VALIDATE},
        )

        plan.refresh_from_db()
        assert plan.workflow_state == ActionPlanStatus.TO_VALIDATE


class TestThePage:
    def test_a_gap_nobody_wrote_reads_as_one_line(self, client, admin):
        plan = ComplianceActionPlanFactory(gap_description="", remediation_plan="")

        html = client.get(plan.get_absolute_url()).content.decode()

        assert "Not filled in yet : Gap description, Remediation plan." in html

    def test_it_shows_the_scopes_the_plan_is_filed_under(self, client, admin):
        scope = ScopeFactory(name="Head office")
        plan = ComplianceActionPlanFactory()
        plan.scopes.add(scope)

        html = client.get(plan.get_absolute_url()).content.decode()

        assert "Head office" in html

    def test_the_empty_register_explains_and_offers_the_first_plan(self, client, admin):
        html = client.get(reverse("compliance:action-plan-list")).content.decode()

        assert "No action plan yet." in html
        create = reverse("compliance:action-plan-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApi:
    def test_a_plan_is_created_without_its_gap(self, admin):
        api = APIClient()
        api.force_authenticate(admin)

        response = api.post(
            "/api/v1/compliance/action-plans/",
            {"name": "Encrypt the laptops", "priority": "high", "owner": str(admin.pk),
             "target_date": _in_a_month()},
            format="json",
        )

        assert response.status_code == 201, response.content.decode()[:400]
        assert ComplianceActionPlan.objects.get().gap_description == ""

    def test_one_plan_carries_its_completeness_and_a_list_does_not(self, admin):
        plan = ComplianceActionPlanFactory(gap_description="", remediation_plan="")
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/compliance/action-plans/{plan.pk}/").json()
        one = one.get("data", one)
        many = api.get("/api/v1/compliance/action-plans/").json()
        rows = many.get("data", many.get("results", many))

        assert one["completeness"]["complete"] is False
        assert [item["key"] for item in one["completeness"]["missing"] if item["blocking"]] == ["gap", "remediation"]
        assert rows and "completeness" not in rows[0]

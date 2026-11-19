# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A compliance assessment is created on one screen, then completed on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the assessment : what it needs before it is planned (its
frameworks and its dates) was checked by one view, for the web interface
alone, and is now held by its lifecycle on every surface; and its journal
names who moved it.
"""

import json
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from compliance.constants import AssessmentStatus
from compliance.forms import ComplianceAssessmentCreateForm, ComplianceAssessmentUpdateForm
from compliance.models import ComplianceAssessment
from compliance.tests.factories import ComplianceAssessmentFactory, FrameworkFactory, ready_assessment
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from core.models import LifecycleEvent
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
REFUSAL = (
    'Before moving to "Planned", this remains to be done : '
    "choose the frameworks ; set the start and end dates."
)


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _today():
    return timezone.localdate()


def _tool(user, name, arguments):
    server = McpServer()
    register_all_tools(server)
    answer = server.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }), user)
    return answer["result"]["isError"], json.loads(answer["result"]["content"][0]["text"])


def _who_moved(assessment, to):
    event = LifecycleEvent.objects.filter(object_id=str(assessment.pk), to_step=to).latest("created_at")
    return event.actor


class TestCreationIsShort:
    def test_it_asks_what_it_measures_against_who_leads_it_and_when(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = ComplianceAssessmentCreateForm(user=admin)

        assert list(form.fields) == [
            "scopes", "frameworks", "name", "assessment_start_date", "assessment_end_date", "assessor",
        ]
        assert form.is_multistep is False

    def test_the_lead_assessor_is_asked_not_assumed(self, admin):
        form = ComplianceAssessmentCreateForm(user=admin)

        # Whoever files an assessment is seldom the auditor who leads it.
        assert form.fields["assessor"].initial is None
        assert form.fields["assessor"].required

    def test_an_assessment_is_created_and_lands_on_its_page(self, client, admin):
        framework = FrameworkFactory()

        response = client.post(
            reverse("compliance:assessment-create"),
            {"name": "ISO 27001 internal audit 2026", "frameworks": [str(framework.pk)],
             "assessor": str(admin.pk)},
            **DRAWER,
        )

        assessment = ComplianceAssessment.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == assessment.get_absolute_url()
        assert list(assessment.frameworks.all()) == [framework]
        assert assessment.workflow_state == AssessmentStatus.DRAFT

    def test_an_end_before_the_start_is_refused(self, admin):
        form = ComplianceAssessmentCreateForm(
            {"name": "Audit", "assessor": str(admin.pk),
             "assessment_start_date": "2026-06-10", "assessment_end_date": "2026-06-01"},
            user=admin,
        )

        assert not form.is_valid()
        assert "assessment_end_date" in form.errors


class TestWhatItStillNeeds:
    def test_a_new_assessment_lists_what_its_planning_waits_for(self, client, admin):
        assessment = ComplianceAssessmentFactory()
        edit = reverse("compliance:assessment-update", kwargs={"pk": assessment.pk})

        report = completeness_of(assessment)
        html = client.get(assessment.get_absolute_url()).content.decode()

        assert [item.key for item in report.blocking_missing] == ["frameworks", "dates"]
        assert [item.key for item in report.advised_missing] == ["objectives"]
        assert "Choose the frameworks" in html
        assert f'href="{edit}?section=identity"' in html
        assert f'href="{edit}?section=planning"' in html

    def test_one_date_is_not_both(self):
        assessment = ComplianceAssessmentFactory(framework=FrameworkFactory(), assessment_start_date=_today())

        assert [item.key for item in completeness_of(assessment).blocking_missing] == ["dates"]

    def test_the_card_of_the_dates_fills_them(self, client, admin):
        assessment = ComplianceAssessmentFactory(framework=FrameworkFactory())
        edit = reverse("compliance:assessment-update", kwargs={"pk": assessment.pk})

        response = client.post(
            edit,
            {"_section": "planning", "assessment_start_date": "2026-06-01", "assessment_end_date": "2026-06-12",
             "description": "", "limitations": ""},
            **DRAWER,
        )

        assessment.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert completeness_of(assessment).blocking_missing == []
        # The frameworks, on another card, are untouched.
        assert assessment.frameworks.count() == 1


class TestTheLifecycleWaitsForItsFrameworksAndItsDates:
    def test_the_page_refuses_to_plan_it_and_says_what_remains(self, client, admin):
        assessment = ComplianceAssessmentFactory()

        response = client.post(
            reverse("compliance:assessment-transition", kwargs={"pk": assessment.pk}),
            {"target_status": AssessmentStatus.PLANNED},
            follow=True,
        )

        assessment.refresh_from_db()
        assert assessment.workflow_state == AssessmentStatus.DRAFT
        assert [str(m) for m in response.context["messages"]] == [REFUSAL]
        # It stays on the page of the assessment, which lists what is missing.
        assert response.redirect_chain[-1][0] == assessment.get_absolute_url()

    def test_the_api_refuses_it_with_the_same_sentence(self, admin):
        assessment = ComplianceAssessmentFactory()
        api = APIClient()
        api.force_authenticate(admin)

        response = api.post(
            f"/api/v1/compliance/assessments/{assessment.pk}/transition/",
            {"status": AssessmentStatus.PLANNED}, format="json",
        )

        assessment.refresh_from_db()
        assert response.status_code == 400
        assert response.json()["error"]["detail"] == REFUSAL
        assert assessment.workflow_state == AssessmentStatus.DRAFT

    def test_the_mcp_server_refuses_it_with_the_same_sentence(self, admin):
        assessment = ComplianceAssessmentFactory()

        failed, answer = _tool(admin, "update_compliance_assessment", {
            "id": str(assessment.pk), "status": AssessmentStatus.PLANNED,
        })

        assessment.refresh_from_db()
        assert failed and answer["error"] == REFUSAL
        assert assessment.workflow_state == AssessmentStatus.DRAFT

    def test_one_mcp_call_may_complete_it_and_plan_it(self, admin):
        assessment = ComplianceAssessmentFactory()
        framework = FrameworkFactory()

        failed, answer = _tool(admin, "update_compliance_assessment", {
            "id": str(assessment.pk), "status": AssessmentStatus.PLANNED,
            "framework_ids": [str(framework.pk)],
            "assessment_start_date": "2026-06-01", "assessment_end_date": "2026-06-12",
        })

        assessment.refresh_from_db()
        assert not failed, answer
        assert assessment.workflow_state == AssessmentStatus.PLANNED

    def test_an_assessment_is_not_created_planned_without_them(self, admin):
        failed, answer = _tool(admin, "create_compliance_assessment", {
            "name": "ISO 27001 internal audit 2026", "assessor_id": str(admin.pk),
            "status": AssessmentStatus.PLANNED,
        })

        assert failed and answer["error"] == REFUSAL
        # Refused as one unit : nothing is left behind.
        assert not ComplianceAssessment.objects.exists()

    def test_an_assessment_is_created_planned_with_them(self, admin):
        framework = FrameworkFactory()

        failed, answer = _tool(admin, "create_compliance_assessment", {
            "name": "ISO 27001 internal audit 2026", "assessor_id": str(admin.pk),
            "status": AssessmentStatus.PLANNED, "framework_ids": [str(framework.pk)],
            "assessment_start_date": "2026-06-01", "assessment_end_date": "2026-06-12",
        })

        assert not failed, answer
        assert ComplianceAssessment.objects.get().workflow_state == AssessmentStatus.PLANNED


class TestTheJournalNamesWhoMovedIt:
    def test_from_the_page(self, client, admin):
        assessment = ready_assessment()

        client.post(
            reverse("compliance:assessment-transition", kwargs={"pk": assessment.pk}),
            {"target_status": AssessmentStatus.PLANNED},
        )

        assessment.refresh_from_db()
        assert assessment.workflow_state == AssessmentStatus.PLANNED
        assert _who_moved(assessment, AssessmentStatus.PLANNED) == admin

    def test_from_the_api(self, admin):
        assessment = ready_assessment()
        api = APIClient()
        api.force_authenticate(admin)

        response = api.post(
            f"/api/v1/compliance/assessments/{assessment.pk}/transition/",
            {"status": AssessmentStatus.PLANNED}, format="json",
        )

        assert response.status_code == 200, response.content.decode()[:300]
        assert _who_moved(assessment, AssessmentStatus.PLANNED) == admin

    def test_from_the_mcp_server(self, admin):
        assessment = ready_assessment()

        failed, answer = _tool(admin, "update_compliance_assessment", {
            "id": str(assessment.pk), "status": AssessmentStatus.PLANNED,
        })

        assert not failed, answer
        assert _who_moved(assessment, AssessmentStatus.PLANNED) == admin


class TestThePage:
    def test_a_planning_nobody_wrote_reads_as_one_line(self, client, admin):
        assessment = ComplianceAssessmentFactory()

        html = client.get(assessment.get_absolute_url()).content.decode()

        assert "Not filled in yet : Start date, End date, Context and objectives, Limitations." in html

    def test_once_in_progress_its_cards_offer_no_dialog(self, client, admin):
        assessment = ready_assessment(status=AssessmentStatus.IN_PROGRESS)
        edit = reverse("compliance:assessment-update", kwargs={"pk": assessment.pk})

        html = client.get(assessment.get_absolute_url()).content.decode()

        assert f'href="{edit}' not in html

    def test_a_locked_assessment_refuses_an_edit_posted_anyway(self, admin):
        assessment = ready_assessment(status=AssessmentStatus.IN_PROGRESS, name="As planned")

        form = ComplianceAssessmentUpdateForm(
            {"_section": "identity", "name": "Renamed afterwards", "assessor": str(admin.pk)},
            instance=assessment, user=admin, section="identity",
        )

        # A disabled field keeps what the record holds, whatever is posted.
        assert form.is_valid(), form.errors
        assert form.save().name == "As planned"

    def test_the_empty_register_explains_and_offers_the_first_assessment(self, client, admin):
        html = client.get(reverse("compliance:assessment-list")).content.decode()

        assert "No assessment yet." in html
        create = reverse("compliance:assessment-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApi:
    def test_one_assessment_carries_its_completeness_and_a_list_does_not(self, admin):
        assessment = ComplianceAssessmentFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/compliance/assessments/{assessment.pk}/").json()
        one = one.get("data", one)
        many = api.get("/api/v1/compliance/assessments/").json()
        rows = many.get("data", many.get("results", many))

        assert one["completeness"]["complete"] is False
        assert [item["key"] for item in one["completeness"]["missing"] if item["blocking"]] == ["frameworks", "dates"]
        assert rows and "completeness" not in rows[0]

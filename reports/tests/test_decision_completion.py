# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A decision of a management review is recorded short, then completed on its page.

What every form of the usability standard owes (its size, its helpers, its
labels) is checked in ``core/tests/test_usability_standard.py``. A decision
hangs under its review, so its page is tested here : the dialog, opened from
the review, asks what was decided, its category and its priority (never
answered for the reader), its owner (whoever records it, unless they name
someone else) and its due date, and lands on the decision; the page lists the
owner and the due date the closure of the review waits for, and what is
advised; each card opens its section; the texts typed in the editor are shown
formatted; the REST API and the MCP server say the same.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from core.completeness import completeness_of
from reports.constants import DecisionStatus
from reports.forms import ManagementReviewDecisionCreateForm, ManagementReviewDecisionForm
from reports.models import ManagementReviewDecision
from reports.tests.factories import ManagementReviewDecisionFactory, ManagementReviewFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


class TestADecisionIsRecordedShort:
    def test_it_asks_what_was_decided_who_carries_it_out_and_by_when(self, admin):
        form = ManagementReviewDecisionCreateForm(review=ManagementReviewFactory(), user=admin)

        assert sorted(form.fields) == ["category", "description", "due_date", "owner", "priority", "title"]
        assert form.is_multistep is False
        for name in ("category", "priority"):
            field = form.fields[name]
            assert field.required and [value for value, _label in field.choices][0] == "", name
        assert form["owner"].value() == admin.pk

    def test_the_dialog_opened_from_the_review_lands_on_the_decision(self, client, admin):
        review = ManagementReviewFactory()

        response = client.post(reverse("reports:decision-create", args=[review.pk]), {
            "title": "Extend the monitoring to the industrial network", "category": "improvement",
            "description": "Cover the OT perimeter.", "priority": "high", "owner": str(admin.pk),
        }, **DRAWER)
        decision = ManagementReviewDecision.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == decision.get_absolute_url()
        assert (decision.review, decision.owner, decision.priority) == (review, admin, "high")


class TestThePageOfTheDecision:
    def test_it_lists_what_the_closure_of_its_review_waits_for(self, client, admin):
        decision = ManagementReviewDecisionFactory(owner=None, due_date=None)
        edit = reverse("reports:decision-edit", args=[decision.pk])

        html = client.get(decision.get_absolute_url()).content.decode()

        assert _missing(decision) == (["owner", "due_date"], ["rationale"])
        assert "Assign an owner" in html and "Set the due date" in html
        for key in ManagementReviewDecisionForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_an_implemented_decision_is_advised_its_date_and_evidence(self, admin):
        decision = ManagementReviewDecisionFactory(status=DecisionStatus.IMPLEMENTED, rationale="Audit finding.")

        assert _missing(decision) == ([], ["implemented_at", "implementation_evidence"])

    def test_a_section_saves_from_the_drawer(self, client, admin):
        decision = ManagementReviewDecisionFactory(owner=None)
        edit = reverse("reports:decision-edit", args=[decision.pk])

        response = client.post(edit, {
            "_section": "follow_up", "owner": str(admin.pk), "due_date": "2027-03-31", "status": "in_progress",
        }, **DRAWER)
        decision.refresh_from_db()

        assert response.status_code == 204
        assert (decision.owner, str(decision.due_date), decision.status) == (admin, "2027-03-31", "in_progress")

    def test_the_texts_typed_in_the_editor_are_shown_formatted(self, client, admin):
        decision = ManagementReviewDecisionFactory(description="<p>Cover the <b>OT</b> network.</p><script>x()</script>")

        html = client.get(decision.get_absolute_url()).content.decode()

        assert "<b>OT</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_and_the_mcp_server_say_what_the_decision_needs(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        decision = ManagementReviewDecisionFactory(due_date=None)
        api = APIClient()
        api.force_authenticate(user=admin)
        server = McpServer()
        register_all_tools(server)

        body = api.get(f"/api/v1/reports/decisions/{decision.pk}/").json()
        body = body.get("data", body)
        read = server.get_tool("get_management_review_decision")["handler"](admin, {"id": str(decision.pk)})
        listed = api.get("/api/v1/reports/decisions/").json()
        listed = listed.get("data", listed)
        rows = listed.get("results", listed) if isinstance(listed, dict) else listed

        assert [item["key"] for item in body["completeness"]["missing"] if item["blocking"]] == ["due_date"]
        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == ["due_date"]
        assert "completeness" not in rows[0]

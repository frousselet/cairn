"""MCP tests for the persistent management review workflow."""

import base64
import json
from datetime import date, timedelta

import pytest

from accounts.tests.factories import UserFactory
from compliance.models import ComplianceActionPlan
from context.models import Stakeholder
from context.tests.factories import ScopeFactory
from mcp.server import McpServer
from mcp.tools import register_all_tools
from reports.constants import ManagementReviewStatus
from reports.models import (
    IsmsChange,
    ManagementReview,
    ManagementReviewDecision,
)

from .factories import (
    ManagementReviewDecisionFactory,
    ManagementReviewFactory,
)


pytestmark = pytest.mark.django_db


def _call_tool(srv, user, tool_name, arguments):
    result = srv.handle_request(json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }), user)
    raw = result["result"]["content"][0]["text"]
    return json.loads(raw)


class TestManagementReviewMCP:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_list_management_reviews(self):
        ManagementReviewFactory.create_batch(3)
        result = _call_tool(self.srv, self.user, "list_management_reviews", {})
        assert isinstance(result, list)
        assert len(result) == 3

    def test_list_filter_by_status(self):
        ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        ManagementReviewFactory(status=ManagementReviewStatus.HELD)
        result = _call_tool(
            self.srv, self.user, "list_management_reviews",
            {"status": "held"},
        )
        assert len(result) == 1

    def test_get_management_review(self):
        review = ManagementReviewFactory()
        ManagementReviewDecisionFactory(review=review)
        result = _call_tool(
            self.srv, self.user, "get_management_review",
            {"id": str(review.pk)},
        )
        assert result["reference"] == review.reference
        assert result["decisions_count"] == 1

    def test_get_unknown_review_returns_error(self):
        import uuid
        result = _call_tool(
            self.srv, self.user, "get_management_review",
            {"id": str(uuid.uuid4())},
        )
        assert "error" in result

    def test_create_management_review(self):
        today = date.today()
        scope = ScopeFactory()
        result = _call_tool(
            self.srv, self.user, "create_management_review",
            {
                "title": "Revue MCP",
                "frequency": "annual",
                "period_start": (today - timedelta(days=365)).isoformat(),
                "period_end": today.isoformat(),
                "planned_date": today.isoformat(),
                "facilitator_id": str(self.user.pk),
                "scope_ids": [str(scope.pk)],
            },
        )
        assert result.get("title") == "Revue MCP"
        assert ManagementReview.objects.filter(title="Revue MCP").exists()

    def test_create_missing_field_returns_error(self):
        result = _call_tool(
            self.srv, self.user, "create_management_review",
            {"title": "Incomplete"},
        )
        assert "error" in result

    def test_transition_management_review(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        result = _call_tool(
            self.srv, self.user, "transition_management_review",
            {"id": str(review.pk), "target_status": "in_preparation"},
        )
        review.refresh_from_db()
        assert review.status == ManagementReviewStatus.IN_PREPARATION

    def test_transition_to_closed_takes_snapshot(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.HELD)
        ManagementReviewDecisionFactory(review=review)
        _call_tool(
            self.srv, self.user, "transition_management_review",
            {"id": str(review.pk), "target_status": "closed"},
        )
        review.refresh_from_db()
        assert review.status == ManagementReviewStatus.CLOSED
        assert review.has_snapshot

    def test_transition_invalid_returns_error(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        result = _call_tool(
            self.srv, self.user, "transition_management_review",
            {"id": str(review.pk), "target_status": "closed"},
        )
        assert "error" in result

    def test_export_management_review_docx(self):
        review = ManagementReviewFactory()
        result = _call_tool(
            self.srv, self.user, "export_management_review",
            {"id": str(review.pk), "format": "docx"},
        )
        assert "content_base64" in result
        content = base64.b64decode(result["content_base64"])
        assert content[:2] == b"PK"
        assert result["filename"].endswith(".docx")

    def test_export_management_review_pptx(self):
        review = ManagementReviewFactory()
        result = _call_tool(
            self.srv, self.user, "export_management_review",
            {"id": str(review.pk), "format": "pptx"},
        )
        assert "content_base64" in result
        assert result["filename"].endswith(".pptx")


class TestDecisionMCP:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_list_decisions(self):
        review = ManagementReviewFactory()
        ManagementReviewDecisionFactory.create_batch(2, review=review)
        result = _call_tool(
            self.srv, self.user, "list_management_review_decisions",
            {"review_id": str(review.pk)},
        )
        assert len(result) == 2

    def test_create_decision(self):
        review = ManagementReviewFactory()
        result = _call_tool(
            self.srv, self.user, "create_management_review_decision",
            {
                "review_id": str(review.pk),
                "title": "Decision title",
                "description": "desc",
                "category": "improvement",
                "priority": "high",
                "owner_id": str(self.user.pk),
                "due_date": date.today().isoformat(),
            },
        )
        assert result.get("title") == "Decision title"
        assert ManagementReviewDecision.objects.filter(title="Decision title").exists()

    def test_promote_decision_to_action_plan(self):
        decision = ManagementReviewDecisionFactory()
        result = _call_tool(
            self.srv, self.user, "promote_decision_to_action_plan",
            {"decision_id": str(decision.pk)},
        )
        assert "action_plan_id" in result
        decision.refresh_from_db()
        assert decision.linked_action_plan_id is not None
        plan = ComplianceActionPlan.objects.get(pk=result["action_plan_id"])
        assert plan.originating_review == decision.review

    def test_promote_refuses_when_already_linked(self):
        decision = ManagementReviewDecisionFactory()
        _call_tool(
            self.srv, self.user, "promote_decision_to_action_plan",
            {"decision_id": str(decision.pk)},
        )
        result = _call_tool(
            self.srv, self.user, "promote_decision_to_action_plan",
            {"decision_id": str(decision.pk)},
        )
        assert "error" in result


class TestIsmsChangeMCP:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_create_isms_change(self):
        review = ManagementReviewFactory()
        result = _call_tool(
            self.srv, self.user, "create_isms_change",
            {
                "review_id": str(review.pk),
                "change_type": "policy",
                "title": "Update access policy",
                "description": "desc",
                "owner_id": str(self.user.pk),
                "status": "proposed",
            },
        )
        assert result.get("title") == "Update access policy"
        assert IsmsChange.objects.filter(title="Update access policy").exists()

    def test_list_isms_changes_filtered_by_review(self):
        from .factories import IsmsChangeFactory
        review = ManagementReviewFactory()
        IsmsChangeFactory.create_batch(2, review=review)
        IsmsChangeFactory()  # another review
        result = _call_tool(
            self.srv, self.user, "list_isms_changes",
            {"review_id": str(review.pk)},
        )
        assert len(result) == 2


class TestSignatureMCP:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_set_participant_signature(self):
        from .factories import ManagementReviewParticipantFactory
        participant = ManagementReviewParticipantFactory(user=self.user)
        data_uri = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )
        result = _call_tool(
            self.srv, self.user, "set_participant_signature",
            {"participant_id": str(participant.pk), "signature_data_uri": data_uri},
        )
        assert result.get("signed") is True
        participant.refresh_from_db()
        assert participant.signature_data == data_uri
        assert participant.attended is True

    def test_invalid_uri_rejected(self):
        from .factories import ManagementReviewParticipantFactory
        participant = ManagementReviewParticipantFactory(user=self.user)
        result = _call_tool(
            self.srv, self.user, "set_participant_signature",
            {"participant_id": str(participant.pk), "signature_data_uri": "not-a-data-uri"},
        )
        assert "error" in result


class TestStakeholderFeedbackMCP:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_create_feedback(self):
        stakeholder = Stakeholder.objects.create(
            name="Test stakeholder", type="internal",
            category="employees", influence_level="medium",
            interest_level="medium", status="active",
        )
        scope = ScopeFactory()
        result = _call_tool(
            self.srv, self.user, "create_stakeholder_feedback",
            {
                "stakeholder_id": str(stakeholder.pk),
                "channel": "complaint",
                "received_date": date.today().isoformat(),
                "subject": "Feedback subject",
                "content": "Body",
                "scope_ids": [str(scope.pk)],
            },
        )
        assert result.get("subject") == "Feedback subject"

    def test_list_feedback(self):
        from context.models import StakeholderFeedback
        stakeholder = Stakeholder.objects.create(
            name="SH", type="internal",
            category="employees", influence_level="medium",
            interest_level="medium", status="active",
        )
        StakeholderFeedback.objects.create(
            stakeholder=stakeholder,
            channel="email",
            received_date=date.today(),
            subject="s1", content="c1",
        )
        StakeholderFeedback.objects.create(
            stakeholder=stakeholder,
            channel="email",
            received_date=date.today(),
            subject="s2", content="c2",
        )
        result = _call_tool(
            self.srv, self.user, "list_stakeholder_feedback", {},
        )
        assert len(result) == 2


class TestMCPPermissions:
    """Verify @require_perm rejects unauthorized users."""

    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=False)

    def test_list_without_perm_errors(self):
        result = _call_tool(
            self.srv, self.user, "list_management_reviews", {},
        )
        assert "error" in result
        assert "Permission denied" in result["error"]

    def test_create_without_perm_errors(self):
        result = _call_tool(
            self.srv, self.user, "create_management_review",
            {
                "title": "x",
                "frequency": "annual",
                "period_start": date.today().isoformat(),
                "period_end": date.today().isoformat(),
                "planned_date": date.today().isoformat(),
                "facilitator_id": str(self.user.pk),
            },
        )
        assert "error" in result

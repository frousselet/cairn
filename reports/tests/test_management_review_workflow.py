"""Tests for the management review specific workflow (issue #105, phase 6c)."""

import pytest

from accounts.tests.factories import UserFactory
from core.workflow import (
    CommentRequiredError,
    IllegalTransitionError,
    LifecycleProtectedError,
    deletable_states,
    find_transition,
    linkable_states,
    reportable_states,
    resolve_workflow,
)
from reports.constants import ManagementReviewStatus
from reports.models import ManagementReview, ManagementReviewTransition
from reports.tests.factories import ManagementReviewFactory

pytestmark = pytest.mark.django_db


class TestManagementReviewWorkflowDefinition:
    def test_model_resolves_to_specific_workflow(self):
        workflow = resolve_workflow(ManagementReview)
        assert workflow.name == "management_review"
        assert workflow.initial_state.code == "planned"
        assert workflow.subsumes_approval is False

    def test_state_codes_match_status_values(self):
        workflow = resolve_workflow(ManagementReview)
        assert {s.code for s in workflow.states} == {
            s.value for s in ManagementReviewStatus
        }

    def test_governance_flags(self):
        assert deletable_states(ManagementReview) == {"planned"}
        assert linkable_states(ManagementReview) == set()
        assert reportable_states(ManagementReview) == {
            "planned", "in_preparation", "held", "closed",
        }

    def test_closure_requires_approve_action(self):
        workflow = resolve_workflow(ManagementReview)
        assert find_transition(workflow, "held", "closed").action == "approve"
        assert find_transition(workflow, "planned", "in_preparation").action == "update"

    def test_cancellation_requires_comment(self):
        workflow = resolve_workflow(ManagementReview)
        for source in ("planned", "in_preparation", "held"):
            assert find_transition(workflow, source, "cancelled").requires_comment is True


class TestManagementReviewTransitions:
    def test_legacy_contract_happy_path(self):
        user = UserFactory()
        review = ManagementReviewFactory()
        review.transition_to(ManagementReviewStatus.IN_PREPARATION, user)
        review.refresh_from_db()
        assert review.status == "in_preparation"
        assert review.workflow_state == "in_preparation"
        log = ManagementReviewTransition.objects.get(review=review)
        assert log.from_status == "planned"
        assert log.to_status == "in_preparation"
        assert log.performed_by == user

    def test_illegal_transition_raises_valueerror(self):
        user = UserFactory()
        review = ManagementReviewFactory()
        with pytest.raises(ValueError):
            review.transition_to(ManagementReviewStatus.CLOSED, user)
        with pytest.raises(IllegalTransitionError):
            review.transition_to(ManagementReviewStatus.CLOSED, user)

    def test_cancellation_without_comment_raises(self):
        user = UserFactory()
        review = ManagementReviewFactory()
        with pytest.raises(ValueError):
            review.transition_to(ManagementReviewStatus.CANCELLED, user)
        with pytest.raises(CommentRequiredError):
            review.transition_to(ManagementReviewStatus.CANCELLED, user, comment="  ")
        review.transition_to(
            ManagementReviewStatus.CANCELLED, user, comment="Postponed to Q3"
        )
        review.refresh_from_db()
        assert review.workflow_state == "cancelled"

    def test_held_date_set_when_held(self):
        user = UserFactory()
        review = ManagementReviewFactory()
        review.transition_to(ManagementReviewStatus.IN_PREPARATION, user)
        assert review.held_date is None
        review.transition_to(ManagementReviewStatus.HELD, user)
        review.refresh_from_db()
        assert review.held_date is not None

    def test_closure_preconditions_enforced(self):
        from reports.models import ManagementReviewDecision

        user = UserFactory()
        review = ManagementReviewFactory()
        review.transition_to(ManagementReviewStatus.IN_PREPARATION, user)
        review.transition_to(ManagementReviewStatus.HELD, user)
        # An incomplete decision (no owner, no due date) blocks closure.
        ManagementReviewDecision.objects.create(
            review=review, title="Hire a DPO", description="Strengthen governance",
        )
        with pytest.raises(ValueError):
            review.transition_to(ManagementReviewStatus.CLOSED, user)
        review.refresh_from_db()
        assert review.workflow_state == "held"

    def test_is_approved_stays_independent(self):
        user = UserFactory()
        review = ManagementReviewFactory(is_approved=True)
        review.transition_to(ManagementReviewStatus.IN_PREPARATION, user)
        review.refresh_from_db()
        assert review.is_approved is True


class TestManagementReviewGovernance:
    def test_only_planned_deletable(self):
        review = ManagementReviewFactory()
        assert review.is_deletable is True
        user = UserFactory()
        review.transition_to(ManagementReviewStatus.IN_PREPARATION, user)
        assert review.is_deletable is False
        with pytest.raises(LifecycleProtectedError):
            review.delete()

    def test_state_sync_both_ways(self):
        review = ManagementReviewFactory()
        review.status = ManagementReviewStatus.IN_PREPARATION
        review.save()
        review.refresh_from_db()
        assert review.workflow_state == "in_preparation"

        review.workflow_state = "held"
        review.save()
        review.refresh_from_db()
        assert review.status == "held"

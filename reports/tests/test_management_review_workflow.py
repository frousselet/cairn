"""Tests for the management review specific workflow (issue #105, phase 6c)."""

import pytest

from accounts.tests.factories import UserFactory
from core.lifecycle import (
    CommentRequiredError,
    IllegalTransitionError,
    resolve_lifecycle,
)
from core.lifecycle import (
    LifecycleProtectedError,
    deletable_states,
    linkable_states,
    reportable_states,
)
from reports.constants import ManagementReviewStatus
from reports.models import ManagementReview, ManagementReviewTransition
from reports.tests.factories import ManagementReviewFactory

pytestmark = pytest.mark.django_db


class TestManagementReviewWorkflowDefinition:
    def test_model_resolves_to_specific_lifecycle(self):
        lifecycle = resolve_lifecycle(ManagementReview)
        assert lifecycle.name == "management_review"
        assert lifecycle.initial_step.code == "planned"

    def test_step_codes_match_status_values(self):
        lifecycle = resolve_lifecycle(ManagementReview)
        assert {s.code for s in lifecycle.steps} == {
            s.value for s in ManagementReviewStatus
        }

    def test_governance_flags(self):
        assert deletable_states(ManagementReview) == {"planned"}
        assert linkable_states(ManagementReview) == set()
        assert reportable_states(ManagementReview) == {
            "planned", "in_preparation", "held", "closed",
        }

    def test_cancellation_requires_comment(self):
        lifecycle = resolve_lifecycle(ManagementReview)
        for source in ("planned", "in_preparation", "held"):
            assert lifecycle.find_transition(source, "cancelled").requires_comment is True


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

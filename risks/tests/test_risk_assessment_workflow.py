"""Tests for the risk assessment specific workflow (issue #105, phase 6g)."""

import pytest

from accounts.tests.factories import UserFactory
from core.lifecycle import IllegalTransitionError, resolve_lifecycle
from core.lifecycle import (
    LifecycleProtectedError,
    deletable_states,
    reportable_states,
)
from risks.constants import AssessmentStatus
from risks.models import RiskAssessment
from risks.tests.factories import RiskAssessmentFactory

pytestmark = pytest.mark.django_db


class TestRiskAssessmentWorkflow:
    def test_resolution_and_shape(self):
        lifecycle = resolve_lifecycle(RiskAssessment)
        assert lifecycle.name == "risk_assessment"
        assert lifecycle.initial_step.code == "draft"
        assert {s.code for s in lifecycle.steps} == {s.value for s in AssessmentStatus}

    def test_governance_flags(self):
        assert deletable_states(RiskAssessment) == {"draft"}
        assert reportable_states(RiskAssessment) == {
            "in_progress", "completed", "validated",
        }

    def test_campaign_path_with_rework(self):
        user = UserFactory()
        assessment = RiskAssessmentFactory()
        assessment.transition_to(AssessmentStatus.IN_PROGRESS, user)
        assessment.transition_to(AssessmentStatus.COMPLETED, user)
        # Rework loop.
        assessment.transition_to(AssessmentStatus.IN_PROGRESS, user)
        assessment.transition_to(AssessmentStatus.COMPLETED, user)
        assessment.transition_to(AssessmentStatus.VALIDATED, user)
        assessment.transition_to(AssessmentStatus.ARCHIVED, user)
        assessment.refresh_from_db()
        assert assessment.status == "archived"
        assert assessment.workflow_state == "archived"
        with pytest.raises(IllegalTransitionError):
            assessment.transition_to(AssessmentStatus.DRAFT, user)

    def test_only_draft_deletable(self):
        live = RiskAssessmentFactory(status=AssessmentStatus.IN_PROGRESS)
        with pytest.raises(LifecycleProtectedError):
            live.delete()
        draft = RiskAssessmentFactory()
        pk = draft.pk
        draft.delete()
        assert not RiskAssessment.objects.filter(pk=pk).exists()

    def test_state_sync_both_ways(self):
        assessment = RiskAssessmentFactory()
        assessment.status = AssessmentStatus.IN_PROGRESS
        assessment.save()
        assessment.refresh_from_db()
        assert assessment.workflow_state == "in_progress"

        assessment.workflow_state = "completed"
        assessment.save()
        assessment.refresh_from_db()
        assert assessment.status == "completed"

"""Tests for the compliance assessment specific workflow (issue #105, phase 6b)."""

import pytest

from accounts.tests.factories import UserFactory
from compliance.constants import AssessmentStatus
from compliance.models import ComplianceAssessment
from compliance.tests.factories import ComplianceAssessmentFactory
from core.workflow import (
    IllegalTransitionError,
    LifecycleProtectedError,
    deletable_states,
    linkable_states,
    reportable_states,
    resolve_workflow,
)

pytestmark = pytest.mark.django_db


class TestAssessmentWorkflowDefinition:
    def test_model_resolves_to_specific_workflow(self):
        workflow = resolve_workflow(ComplianceAssessment)
        assert workflow.name == "compliance_assessment"
        assert workflow.initial_state.code == "draft"
        assert workflow.subsumes_approval is False  # no 'validated' state

    def test_state_codes_match_status_values(self):
        workflow = resolve_workflow(ComplianceAssessment)
        assert {s.code for s in workflow.states} == {s.value for s in AssessmentStatus}

    def test_governance_flags(self):
        assert deletable_states(ComplianceAssessment) == {"draft"}
        assert linkable_states(ComplianceAssessment) == set()
        assert reportable_states(ComplianceAssessment) == {
            "planned", "in_progress", "completed", "closed",
        }

    def test_terminal_states(self):
        workflow = resolve_workflow(ComplianceAssessment)
        assert {s.code for s in workflow.states if s.is_terminal} == {"closed", "cancelled"}


class TestAssessmentStateSync:
    def test_creation_aligns_workflow_state_with_status(self):
        assessment = ComplianceAssessmentFactory()
        assert assessment.workflow_state == assessment.status

    def test_legacy_status_write_mirrors_to_workflow_state(self):
        assessment = ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT)
        assessment.status = AssessmentStatus.PLANNED
        assessment.save()
        assessment.refresh_from_db()
        assert assessment.workflow_state == "planned"

    def test_framework_write_mirrors_to_status(self):
        assessment = ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT)
        assessment.workflow_state = "planned"
        assessment.save()
        assessment.refresh_from_db()
        assert assessment.status == "planned"


class TestAssessmentTransitions:
    def test_legacy_contract_no_user(self):
        """Bespoke callers pass only the target status."""
        assessment = ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT)
        assessment.transition_to(AssessmentStatus.PLANNED)
        assessment.refresh_from_db()
        assert assessment.status == "planned"
        assert assessment.workflow_state == "planned"

    def test_illegal_transition_raises_valueerror(self):
        assessment = ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT)
        with pytest.raises(ValueError):
            assessment.transition_to(AssessmentStatus.COMPLETED)
        with pytest.raises(IllegalTransitionError):
            assessment.transition_to(AssessmentStatus.COMPLETED)

    def test_cancel_paths(self):
        a1 = ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT)
        a1.transition_to(AssessmentStatus.CANCELLED)
        assert a1.workflow_state == "cancelled"
        a2 = ComplianceAssessmentFactory(status=AssessmentStatus.PLANNED)
        a2.transition_to(AssessmentStatus.CANCELLED)
        assert a2.workflow_state == "cancelled"
        # In progress cannot be cancelled (faithful to the legacy machine).
        a3 = ComplianceAssessmentFactory(status=AssessmentStatus.IN_PROGRESS)
        with pytest.raises(ValueError):
            a3.transition_to(AssessmentStatus.CANCELLED)

    def test_terminal_states_locked(self):
        assessment = ComplianceAssessmentFactory(status=AssessmentStatus.CLOSED)
        with pytest.raises(ValueError):
            assessment.transition_to(AssessmentStatus.DRAFT)

    def test_is_approved_stays_independent(self):
        assessment = ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT, is_approved=True)
        assessment.transition_to(AssessmentStatus.PLANNED)
        assessment.refresh_from_db()
        assert assessment.is_approved is True


class TestAssessmentGovernance:
    def test_only_draft_deletable(self):
        draft = ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT)
        assert draft.is_deletable is True
        planned = ComplianceAssessmentFactory(status=AssessmentStatus.PLANNED)
        assert planned.is_deletable is False
        with pytest.raises(LifecycleProtectedError):
            planned.delete()

    def test_reportable_follows_states(self):
        from core.workflow import reportable

        ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT)
        live = ComplianceAssessmentFactory(status=AssessmentStatus.PLANNED)
        cancelled = ComplianceAssessmentFactory(status=AssessmentStatus.CANCELLED)
        result = set(reportable(ComplianceAssessment.objects.all()))
        assert live in result
        assert cancelled not in result

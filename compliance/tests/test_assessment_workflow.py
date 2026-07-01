"""Tests for the compliance assessment specific workflow (issue #105, phase 6b)."""

import pytest

from compliance.constants import AssessmentStatus
from compliance.models import ComplianceAssessment
from compliance.tests.factories import ComplianceAssessmentFactory
from core.lifecycle import (
    IllegalTransitionError,
    get_lifecycle,
    resolve_lifecycle,
)
from core.lifecycle import LifecycleProtectedError  # delete() guard (relocated at decommission)

pytestmark = pytest.mark.django_db


class TestAssessmentLifecycleDefinition:
    def test_model_resolves_to_specific_lifecycle(self):
        lifecycle = resolve_lifecycle(ComplianceAssessment)
        assert lifecycle.name == "compliance_assessment"
        assert lifecycle.initial_step.code == "draft"

    def test_step_codes_match_status_values(self):
        lifecycle = resolve_lifecycle(ComplianceAssessment)
        assert {s.code for s in lifecycle.steps} == {s.value for s in AssessmentStatus}

    def test_governance_flags(self):
        lifecycle = get_lifecycle("compliance_assessment")
        assert lifecycle.deletable_step_codes == {"draft"}
        assert lifecycle.linkable_step_codes == set()
        assert lifecycle.reportable_step_codes == {
            "planned", "in_progress", "completed", "closed",
        }

    def test_terminal_states(self):
        lifecycle = resolve_lifecycle(ComplianceAssessment)
        assert {s.code for s in lifecycle.steps if s.is_archived} == {"closed", "cancelled"}


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


class TestAssessmentGovernance:
    def test_only_draft_deletable(self):
        draft = ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT)
        assert draft.is_deletable is True
        planned = ComplianceAssessmentFactory(status=AssessmentStatus.PLANNED)
        assert planned.is_deletable is False
        with pytest.raises(LifecycleProtectedError):
            planned.delete()

    def test_reportable_follows_states(self):
        from core.lifecycle import reportable

        ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT)
        live = ComplianceAssessmentFactory(status=AssessmentStatus.PLANNED)
        cancelled = ComplianceAssessmentFactory(status=AssessmentStatus.CANCELLED)
        result = set(reportable(ComplianceAssessment.objects.all()))
        assert live in result
        assert cancelled not in result

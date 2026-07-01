"""Tests for the EBIOS deliverable specific workflows (issue #105, phase 6f)."""

import pytest

from accounts.tests.factories import UserFactory
from core.lifecycle import (
    CommentRequiredError,
    IllegalTransitionError,
    resolve_lifecycle,
)
from core.lifecycle import deletable_states
from risks.constants import (
    BaselineGapStatus,
    EbiosStudyFrameworkStatus,
    EbiosWorkshopStatus,
    PACSMeasureStatus,
)
from risks.models import (
    BaselineGap,
    EbiosSummary,
    EbiosWorkshopProgress,
    PACSMeasure,
    SecurityBaseline,
    StudyFramework,
)

pytestmark = pytest.mark.django_db


def _ebios_assessment():
    from risks.tests.factories import RiskAssessmentFactory

    return RiskAssessmentFactory(methodology="ebios_rm")


def _singleton(model, assessment, **defaults):
    """Fetch the signal-created per-assessment singleton (or create it)."""
    obj, _ = model.objects.get_or_create(assessment=assessment, defaults=defaults)
    return obj


class TestWorkflowResolution:
    def test_all_six_resolve(self):
        expectations = {
            EbiosWorkshopProgress: "ebios_workshop",
            StudyFramework: "ebios_study_framework",
            SecurityBaseline: "ebios_security_baseline",
            EbiosSummary: "ebios_summary",
            BaselineGap: "ebios_baseline_gap",
            PACSMeasure: "ebios_pacs_measure",
        }
        for model, name in expectations.items():
            assert resolve_lifecycle(model).name == name


class TestWorkshopReviewMachine:
    def _workshop(self):
        assessment = _ebios_assessment()
        return assessment.ebios_workshops.first() or EbiosWorkshopProgress.objects.create(
            assessment=assessment, workshop="w1",
        )

    def test_review_cycle_with_rejection(self):
        user = UserFactory()
        workshop = self._workshop()
        workshop.transition_to(EbiosWorkshopStatus.IN_PROGRESS, user)
        workshop.transition_to(EbiosWorkshopStatus.UNDER_REVIEW, user)
        # Rejection requires a comment.
        with pytest.raises(CommentRequiredError):
            workshop.transition_to(EbiosWorkshopStatus.REJECTED, user)
        workshop.transition_to(
            EbiosWorkshopStatus.REJECTED, user, comment="Scope incomplete"
        )
        # Rework loop then validation.
        workshop.transition_to(EbiosWorkshopStatus.IN_PROGRESS, user)
        workshop.transition_to(EbiosWorkshopStatus.UNDER_REVIEW, user)
        workshop.transition_to(EbiosWorkshopStatus.VALIDATED, user)
        workshop.refresh_from_db()
        assert workshop.status == "validated"
        with pytest.raises(IllegalTransitionError):
            workshop.transition_to(EbiosWorkshopStatus.IN_PROGRESS, user)


class TestGovernanceFlags:
    def test_only_initial_states_deletable(self):
        assert deletable_states(EbiosWorkshopProgress) == {"not_started"}
        assert deletable_states(StudyFramework) == {"draft"}
        assert deletable_states(SecurityBaseline) == {"draft"}
        assert deletable_states(EbiosSummary) == {"draft"}
        assert deletable_states(BaselineGap) == {"identified"}
        assert deletable_states(PACSMeasure) == {"planned"}

    def test_cancelled_pacs_measures_leave_reports(self):
        from core.lifecycle import reportable_states

        assert reportable_states(PACSMeasure) == {
            "planned", "in_progress", "overdue", "completed",
        }


class TestGapAndMeasurePaths:
    def test_accepted_gap_can_enter_remediation(self):
        user = UserFactory()
        baseline = _singleton(SecurityBaseline, _ebios_assessment())
        gap = BaselineGap.objects.create(
            baseline=baseline, reference_source="ISO 27002", description="No MFA",
        )
        gap.transition_to(BaselineGapStatus.ACCEPTED, user)
        gap.transition_to(BaselineGapStatus.IN_REMEDIATION, user)
        gap.transition_to(BaselineGapStatus.REMEDIATED, user)
        gap.refresh_from_db()
        assert gap.status == "remediated"

    def test_pacs_overdue_recovery(self):
        user = UserFactory()
        summary = _singleton(EbiosSummary, _ebios_assessment())
        measure = PACSMeasure.objects.create(summary=summary, name="Harden bastion")
        measure.transition_to(PACSMeasureStatus.IN_PROGRESS, user)
        measure.transition_to(PACSMeasureStatus.OVERDUE, user)
        measure.transition_to(PACSMeasureStatus.COMPLETED, user)
        measure.refresh_from_db()
        assert measure.status == "completed"

    def test_study_framework_validation(self):
        user = UserFactory()
        framework = _singleton(StudyFramework, _ebios_assessment())
        framework.transition_to(EbiosStudyFrameworkStatus.VALIDATED, user)
        framework.refresh_from_db()
        assert framework.status == "validated"

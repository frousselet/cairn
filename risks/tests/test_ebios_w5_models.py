"""Tests for EBIOS RM workshop W5 models.

Covers:
- Reference prefixes ESUM / EPAC.
- bootstrap signal now creates an EbiosSummary alongside StudyFramework,
  SecurityBaseline and the 6 EbiosWorkshopProgress rows.
- capture_risk_mappings() builds a stable snapshot shape from the
  assessment's risk register and can update each slot independently.
- PACSMeasure links to RiskTreatmentPlans, BaselineGaps and Requirements
  without scope tenancy (lives under the summary instead).
"""

import pytest

from risks.constants import (
    PACSMeasurePriority,
    PACSMeasureStatus,
    PACSMeasureType,
)
from risks.models import EbiosSummary, PACSMeasure
from risks.tests.factories import (
    BaselineGapFactory,
    EbiosAssessmentFactory,
    EbiosSummaryFactory,
    PACSMeasureFactory,
    RiskFactory,
    RiskTreatmentPlanFactory,
)


pytestmark = pytest.mark.django_db


class TestEbiosSummaryBootstrap:
    def test_summary_created_alongside_other_artifacts(self):
        assessment = EbiosAssessmentFactory()
        assert EbiosSummary.objects.filter(assessment=assessment).exists()

    def test_signal_remains_idempotent_for_summary(self):
        assessment = EbiosAssessmentFactory()
        assessment.save()
        assessment.save()
        assert EbiosSummary.objects.filter(assessment=assessment).count() == 1


class TestEbiosSummaryModel:
    def test_reference_prefix(self):
        summary = EbiosSummaryFactory()
        assert summary.reference.startswith("ESUM-")

    def test_capture_mappings_on_empty_register(self):
        summary = EbiosSummaryFactory()
        summary.capture_risk_mappings()
        summary.refresh_from_db()
        assert summary.risk_mapping_before == {
            "total": 0,
            "by_status": {},
            "by_priority": {},
            "by_initial_risk_level": {},
            "by_current_risk_level": {},
            "by_residual_risk_level": {},
        }
        assert summary.risk_mapping_after == summary.risk_mapping_before

    def test_capture_mappings_counts_risks(self):
        summary = EbiosSummaryFactory()
        RiskFactory(assessment=summary.assessment, current_risk_level=2, initial_risk_level=3)
        RiskFactory(assessment=summary.assessment, current_risk_level=2, initial_risk_level=4)
        RiskFactory(assessment=summary.assessment, current_risk_level=5, initial_risk_level=5)
        summary.capture_risk_mappings()
        summary.refresh_from_db()
        snapshot = summary.risk_mapping_before
        assert snapshot["total"] == 3
        assert snapshot["by_initial_risk_level"]["3"] == 1
        assert snapshot["by_initial_risk_level"]["4"] == 1
        assert snapshot["by_initial_risk_level"]["5"] == 1
        assert snapshot["by_current_risk_level"]["2"] == 2

    def test_capture_only_before_leaves_after_untouched(self):
        summary = EbiosSummaryFactory()
        # Seed an "after" snapshot first
        summary.capture_risk_mappings()
        summary.refresh_from_db()
        original_after = summary.risk_mapping_after
        # Add a risk and capture only "before"
        RiskFactory(assessment=summary.assessment)
        summary.capture_risk_mappings(capture_before=True, capture_after=False)
        summary.refresh_from_db()
        assert summary.risk_mapping_before["total"] == 1
        # The "after" snapshot must not have been overwritten by the new count
        assert summary.risk_mapping_after == original_after


class TestPACSMeasureModel:
    def test_reference_prefix(self):
        measure = PACSMeasureFactory()
        assert measure.reference.startswith("EPAC-")

    def test_link_to_treatment_plan(self):
        measure = PACSMeasureFactory()
        plan = RiskTreatmentPlanFactory()
        measure.linked_treatment_plans.add(plan)
        assert measure.linked_treatment_plans.count() == 1
        assert plan.pacs_measures.first() == measure

    def test_link_to_baseline_gap(self):
        summary = EbiosSummaryFactory()
        # Make sure the gap lives under the same assessment
        gap = BaselineGapFactory(baseline__assessment=summary.assessment)
        measure = PACSMeasureFactory(summary=summary)
        measure.linked_baseline_gaps.add(gap)
        assert measure.linked_baseline_gaps.count() == 1
        assert gap.pacs_measures.first() == measure

    def test_default_status_is_planned(self):
        measure = PACSMeasureFactory()
        assert measure.status == PACSMeasureStatus.PLANNED
        assert measure.measure_type == PACSMeasureType.PROTECTION
        assert measure.priority == PACSMeasurePriority.MEDIUM

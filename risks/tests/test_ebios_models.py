"""Tests for EBIOS RM foundation models (workshops W0 and W1).

Covers:
- Reference auto-generation with the dedicated E* prefixes.
- The post_save signal that bootstraps StudyFramework, SecurityBaseline and
  the 6 EbiosWorkshopProgress instances for every ebios_rm assessment.
- Idempotency of the signal (saving an existing assessment twice does not
  duplicate the workshops or root objects).
- DIC uniqueness constraint on FearedEvent.
- Iteration uniqueness constraint on EbiosWorkshopProgress.
- Criteria snapshot capture on FearedEvent.gravity_level write.
"""

import pytest
from django.db import IntegrityError

from assets.tests.factories import EssentialAssetFactory
from risks.constants import (
    DICCriterion,
    EbiosIterationType,
    EbiosWorkshopNumber,
    Methodology,
)
from risks.models import (
    EbiosWorkshopProgress,
    FearedEvent,
    SecurityBaseline,
    StudyFramework,
)
from risks.tests.factories import (
    BaselineGapFactory,
    EbiosAssessmentFactory,
    FearedEventFactory,
    RiskAssessmentFactory,
    RiskCriteriaFactory,
    SecurityBaselineFactory,
    StudyFrameworkFactory,
)


pytestmark = pytest.mark.django_db


class TestEbiosBootstrapSignal:
    """post_save signal on RiskAssessment creates the EBIOS scaffolding."""

    def test_ebios_assessment_creates_study_framework_and_baseline(self):
        assessment = EbiosAssessmentFactory()
        assert StudyFramework.objects.filter(assessment=assessment).exists()
        assert SecurityBaseline.objects.filter(assessment=assessment).exists()

    def test_ebios_assessment_creates_six_workshops(self):
        assessment = EbiosAssessmentFactory()
        workshops = EbiosWorkshopProgress.objects.filter(assessment=assessment)
        assert workshops.count() == 6
        numbers = sorted(workshops.values_list("workshop_number", flat=True))
        assert numbers == [0, 1, 2, 3, 4, 5]

    def test_ebios_assessment_workshops_are_strategic_iteration_one(self):
        assessment = EbiosAssessmentFactory()
        for workshop in assessment.ebios_workshops.all():
            assert workshop.iteration_type == EbiosIterationType.STRATEGIC
            assert workshop.iteration_number == 1

    def test_iso27005_assessment_does_not_create_ebios_artifacts(self):
        assessment = RiskAssessmentFactory()  # default ISO 27005
        assert not StudyFramework.objects.filter(assessment=assessment).exists()
        assert not SecurityBaseline.objects.filter(assessment=assessment).exists()
        assert not EbiosWorkshopProgress.objects.filter(assessment=assessment).exists()

    def test_signal_is_idempotent_on_resave(self):
        assessment = EbiosAssessmentFactory()
        # Saving the same assessment again must not create extra workshops
        assessment.save()
        assessment.save()
        assert StudyFramework.objects.filter(assessment=assessment).count() == 1
        assert SecurityBaseline.objects.filter(assessment=assessment).count() == 1
        assert EbiosWorkshopProgress.objects.filter(assessment=assessment).count() == 6

    def test_switching_to_ebios_after_iso_creates_artifacts(self):
        assessment = RiskAssessmentFactory()
        assert not assessment.ebios_workshops.exists()
        assessment.methodology = Methodology.EBIOS_RM
        assessment.save()
        assert EbiosWorkshopProgress.objects.filter(assessment=assessment).count() == 6


class TestEbiosReferences:
    """REFERENCE_PREFIX values are exactly the ones specified in M4bis."""

    def test_study_framework_reference_prefix(self):
        framework = StudyFramework.objects.first() or StudyFrameworkFactory()
        assert framework.reference.startswith("EFRA-")

    def test_workshop_progress_reference_prefix(self):
        assessment = EbiosAssessmentFactory()
        workshop = assessment.ebios_workshops.first()
        assert workshop.reference.startswith("EWSP-")

    def test_security_baseline_reference_prefix(self):
        baseline = SecurityBaselineFactory()
        assert baseline.reference.startswith("EBSL-")

    def test_feared_event_reference_prefix(self):
        feared = FearedEventFactory()
        assert feared.reference.startswith("EFER-")

    def test_baseline_gap_reference_prefix(self):
        gap = BaselineGapFactory()
        assert gap.reference.startswith("EBGP-")


class TestFearedEventUniqueness:
    """A baseline cannot have two feared events for the same (asset, DIC)."""

    def test_unique_per_essential_asset_and_dic(self):
        baseline = SecurityBaselineFactory()
        asset = EssentialAssetFactory()
        FearedEventFactory(
            baseline=baseline,
            essential_asset=asset,
            dic_criterion=DICCriterion.CONFIDENTIALITY,
        )
        with pytest.raises(IntegrityError):
            FearedEvent.objects.create(
                baseline=baseline,
                essential_asset=asset,
                dic_criterion=DICCriterion.CONFIDENTIALITY,
                name="dup",
                description="dup",
            )

    def test_same_asset_different_dic_is_allowed(self):
        baseline = SecurityBaselineFactory()
        asset = EssentialAssetFactory()
        FearedEventFactory(
            baseline=baseline,
            essential_asset=asset,
            dic_criterion=DICCriterion.CONFIDENTIALITY,
        )
        # Integrity feared event on the same asset is fine
        FearedEventFactory(
            baseline=baseline,
            essential_asset=asset,
            dic_criterion=DICCriterion.INTEGRITY,
        )
        assert FearedEvent.objects.filter(baseline=baseline, essential_asset=asset).count() == 2


class TestWorkshopIterationUniqueness:
    """Same (workshop_number, iteration_type, iteration_number) cannot repeat."""

    def test_duplicate_iteration_is_rejected(self):
        assessment = EbiosAssessmentFactory()
        with pytest.raises(IntegrityError):
            EbiosWorkshopProgress.objects.create(
                assessment=assessment,
                workshop_number=EbiosWorkshopNumber.W0,
                iteration_type=EbiosIterationType.STRATEGIC,
                iteration_number=1,
            )

    def test_new_iteration_is_allowed(self):
        assessment = EbiosAssessmentFactory()
        EbiosWorkshopProgress.objects.create(
            assessment=assessment,
            workshop_number=EbiosWorkshopNumber.W0,
            iteration_type=EbiosIterationType.STRATEGIC,
            iteration_number=2,
        )
        assert EbiosWorkshopProgress.objects.filter(
            assessment=assessment,
            workshop_number=EbiosWorkshopNumber.W0,
        ).count() == 2


class TestFearedEventCriteriaSnapshot:
    """gravity_level writes capture a snapshot of the criteria."""

    def test_snapshot_captured_when_gravity_set(self):
        criteria = RiskCriteriaFactory()
        assessment = EbiosAssessmentFactory(risk_criteria=criteria)
        baseline = SecurityBaseline.objects.get(assessment=assessment)
        feared = FearedEvent.objects.create(
            baseline=baseline,
            essential_asset=EssentialAssetFactory(),
            name="test",
            description="test",
            dic_criterion=DICCriterion.AVAILABILITY,
            gravity_level=3,
        )
        assert feared.criteria_snapshot is not None
        assert feared.criteria_snapshot["criteria_id"] == str(criteria.pk)

    def test_snapshot_not_overwritten_on_resave(self):
        criteria = RiskCriteriaFactory()
        assessment = EbiosAssessmentFactory(risk_criteria=criteria)
        baseline = SecurityBaseline.objects.get(assessment=assessment)
        feared = FearedEvent.objects.create(
            baseline=baseline,
            essential_asset=EssentialAssetFactory(),
            name="test",
            description="test",
            dic_criterion=DICCriterion.AVAILABILITY,
            gravity_level=3,
        )
        initial_snapshot = feared.criteria_snapshot
        feared.gravity_level = 4
        feared.save()
        feared.refresh_from_db()
        assert feared.criteria_snapshot == initial_snapshot


class TestSecurityBaselineRelations:
    """SecurityBaseline aggregates W1 deliverables."""

    def test_baseline_holds_feared_events_and_gaps(self):
        baseline = SecurityBaselineFactory()
        FearedEventFactory(baseline=baseline)
        FearedEventFactory(baseline=baseline, dic_criterion=DICCriterion.INTEGRITY)
        BaselineGapFactory(baseline=baseline)
        assert baseline.feared_events.count() == 2
        assert baseline.gaps.count() == 1

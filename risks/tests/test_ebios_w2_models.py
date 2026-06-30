"""Tests for EBIOS RM workshop W2 models (risk sources, objectives, SR/OV pairs).

Covers:
- Reference prefixes ERSC / ETOV / ESOV.
- ANSSI Grid A: threat_level = grid(motivation, resources) majorated by activity.
- threat_level snapshot is captured on first scoring and frozen on resave.
- SR/OV pair priority_score recomputed on save.
- SR/OV uniqueness constraint per (assessment, risk_source, targeted_objective).
- Override of the grid via RiskCriteria.risk_matrix["ebios_threat_grid"].
"""

import pytest
from django.db import IntegrityError

from risks.constants import (
    ANSSI_THREAT_LEVEL_GRID,
    Relevance,
    RiskSourceCategory,
    ThreatLevelV,
    compute_anssi_threat_level,
)
from risks.models import RiskSource, RiskSourceObjectivePair
from risks.tests.factories import (
    EbiosAssessmentFactory,
    RiskCriteriaFactory,
    RiskSourceFactory,
    RiskSourceObjectivePairFactory,
    TargetedObjectiveFactory,
)


pytestmark = pytest.mark.django_db


class TestAnssiThreatGridPure:
    """The pure-Python helper compute_anssi_threat_level matches the spec."""

    @pytest.mark.parametrize("motivation,resources,expected", [
        # Rows from M4bis spec §2.8 Grid A.
        (1, 1, 1), (1, 2, 1), (1, 3, 2), (1, 4, 2),
        (2, 1, 1), (2, 2, 2), (2, 3, 3), (2, 4, 3),
        (3, 1, 2), (3, 2, 3), (3, 3, 3), (3, 4, 4),
        (4, 1, 2), (4, 2, 3), (4, 3, 4), (4, 4, 4),
    ])
    def test_grid_a_matches_spec(self, motivation, resources, expected):
        assert compute_anssi_threat_level(motivation, resources) == expected

    def test_high_activity_majorates_by_one(self):
        # Without activity: 2,2 -> V2
        assert compute_anssi_threat_level(2, 2) == 2
        # Activity 3 lifts it to V3
        assert compute_anssi_threat_level(2, 2, activity=3) == 3

    def test_high_activity_is_capped_at_v4(self):
        # 4,4 already at V4; activity 4 must not push it to V5
        assert compute_anssi_threat_level(4, 4, activity=4) == ThreatLevelV.V4

    def test_low_activity_does_not_majorate(self):
        # Activity 2 keeps the base level intact
        assert compute_anssi_threat_level(2, 2, activity=2) == 2

    def test_missing_inputs_return_none(self):
        assert compute_anssi_threat_level(None, 2) is None
        assert compute_anssi_threat_level(2, None) is None


class TestRiskSourceModel:
    def test_reference_prefix(self):
        rs = RiskSourceFactory()
        assert rs.reference.startswith("ERSC-")

    def test_threat_level_computed_on_save(self):
        # motivation 3, resources 3, activity 2 -> V3 (no majoration)
        rs = RiskSourceFactory(
            motivation_level=3, resources_level=3, activity_level=2,
        )
        assert rs.threat_level == ThreatLevelV.V3

    def test_threat_level_majorated_when_activity_high(self):
        rs = RiskSourceFactory(
            motivation_level=2, resources_level=2, activity_level=3,
        )
        assert rs.threat_level == ThreatLevelV.V3

    def test_threat_level_is_none_when_inputs_missing(self):
        rs = RiskSourceFactory(motivation_level=None, resources_level=2)
        assert rs.threat_level is None

    def test_clearing_inputs_clears_threat_level(self):
        rs = RiskSourceFactory(motivation_level=3, resources_level=3)
        assert rs.threat_level is not None
        rs.motivation_level = None
        rs.save()
        rs.refresh_from_db()
        assert rs.threat_level is None

    def test_snapshot_captured_on_first_scoring(self):
        rs = RiskSourceFactory(motivation_level=3, resources_level=3)
        snap = rs.criteria_snapshot
        assert snap is not None
        # The grid copy serializes (m, r) tuples as "m,r" strings
        assert isinstance(snap.get("grid"), dict)
        assert "3,3" in snap["grid"]

    def test_snapshot_not_overwritten_on_resave(self):
        rs = RiskSourceFactory(motivation_level=2, resources_level=2)
        original_snapshot = rs.criteria_snapshot
        rs.motivation_level = 4
        rs.resources_level = 4
        rs.save()
        rs.refresh_from_db()
        assert rs.criteria_snapshot == original_snapshot
        # threat_level still recomputed against the frozen grid (which is the
        # ANSSI default the snapshot captured), so the new inputs map normally.
        assert rs.threat_level == ThreatLevelV.V4

    def test_custom_grid_from_risk_criteria_is_used(self):
        # Create a criteria that overrides the grid: (1,1) -> V4 instead of V1
        criteria = RiskCriteriaFactory()
        criteria.risk_matrix = {
            "ebios_threat_grid": {f"{m},{r}": v for (m, r), v in ANSSI_THREAT_LEVEL_GRID.items()},
        }
        criteria.risk_matrix["ebios_threat_grid"]["1,1"] = ThreatLevelV.V4
        criteria.save()
        assessment = EbiosAssessmentFactory(risk_criteria=criteria)
        rs = RiskSource.objects.create(
            assessment=assessment,
            name="custom",
            motivation_level=1,
            resources_level=1,
            category=RiskSourceCategory.OTHER,
        )
        assert rs.threat_level == ThreatLevelV.V4


class TestTargetedObjectiveModel:
    def test_reference_prefix(self):
        obj = TargetedObjectiveFactory()
        assert obj.reference.startswith("ETOV-")

    def test_objective_belongs_to_risk_source(self):
        rs = RiskSourceFactory()
        obj1 = TargetedObjectiveFactory(risk_source=rs)
        obj2 = TargetedObjectiveFactory(risk_source=rs)
        assert rs.targeted_objectives.count() == 2
        assert set(rs.targeted_objectives.values_list("pk", flat=True)) == {obj1.pk, obj2.pk}


class TestRiskSourceObjectivePairModel:
    def test_reference_prefix(self):
        pair = RiskSourceObjectivePairFactory()
        assert pair.reference.startswith("ESOV-")

    def test_priority_score_is_max_of_threat_and_relevance(self):
        rs = RiskSourceFactory(motivation_level=4, resources_level=4)  # V4
        obj = TargetedObjectiveFactory(risk_source=rs)
        pair = RiskSourceObjectivePairFactory(
            assessment=rs.assessment,
            risk_source=rs,
            targeted_objective=obj,
            relevance=Relevance.LOW,  # weight 1
        )
        # max(V4=4, weight=1) -> 4
        assert pair.priority_score == 4

    def test_priority_score_uses_relevance_when_threat_higher_relevance(self):
        rs = RiskSourceFactory(motivation_level=1, resources_level=1)  # V1
        obj = TargetedObjectiveFactory(risk_source=rs)
        pair = RiskSourceObjectivePairFactory(
            assessment=rs.assessment,
            risk_source=rs,
            targeted_objective=obj,
            relevance=Relevance.CRITICAL,  # weight 4
        )
        # max(V1=1, weight=4) -> 4
        assert pair.priority_score == 4

    def test_uniqueness_of_pair_per_assessment(self):
        rs = RiskSourceFactory()
        obj = TargetedObjectiveFactory(risk_source=rs)
        RiskSourceObjectivePairFactory(
            assessment=rs.assessment,
            risk_source=rs,
            targeted_objective=obj,
        )
        with pytest.raises(IntegrityError):
            RiskSourceObjectivePair.objects.create(
                assessment=rs.assessment,
                risk_source=rs,
                targeted_objective=obj,
                relevance=Relevance.MEDIUM,
            )

    def test_pair_ordering_is_priority_score_desc(self):
        rs_high = RiskSourceFactory(motivation_level=4, resources_level=4)
        rs_low = RiskSourceFactory(motivation_level=1, resources_level=1)
        obj_h = TargetedObjectiveFactory(risk_source=rs_high)
        obj_l = TargetedObjectiveFactory(risk_source=rs_low)
        RiskSourceObjectivePairFactory(
            assessment=rs_low.assessment, risk_source=rs_low,
            targeted_objective=obj_l, relevance=Relevance.LOW,
        )
        RiskSourceObjectivePairFactory(
            assessment=rs_high.assessment, risk_source=rs_high,
            targeted_objective=obj_h, relevance=Relevance.LOW,
        )
        # Default ordering on the Meta class is -priority_score, so V4 pair first.
        first, *_ = RiskSourceObjectivePair.objects.all()
        assert first.priority_score == 4

"""Tests for EBIOS RM workshop W3 models.

Covers:
- Reference prefixes EECS / ESTS / EAPS.
- ANSSI ecosystem formula (dependency * penetration) / (maturity * trust).
- Threat zone mapping with default and custom thresholds.
- Snapshot capture and freeze on the EcosystemStakeholder.
- StrategicScenario risk_level computed via the assessment risk matrix.
- AttackPathStep order uniqueness per scenario.
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError

from risks.constants import (
    DEFAULT_ECOSYSTEM_THRESHOLDS,
    ThreatZone,
    compute_ecosystem_threat_level,
    compute_ecosystem_threat_zone,
)
from risks.models import (
    AttackPathStep,
    EcosystemStakeholder,
    StrategicScenario,
)
from risks.tests.factories import (
    AttackPathStepFactory,
    EbiosAssessmentFactory,
    EcosystemStakeholderFactory,
    RiskCriteriaFactory,
    StrategicScenarioFactory,
)


pytestmark = pytest.mark.django_db


class TestEcosystemFormulaPure:
    """Pure helpers match the ANSSI v1.5 spec §2.6."""

    @pytest.mark.parametrize("d,p,m,t,expected", [
        (1, 1, 1, 1, 1.0),       # neutral
        (4, 4, 1, 1, 16.0),      # max
        (1, 1, 4, 4, 0.0625),    # min
        (2, 2, 2, 2, 1.0),       # symmetric
        (3, 4, 2, 1, 6.0),       # asymmetric high
    ])
    def test_formula_matches_spec(self, d, p, m, t, expected):
        assert compute_ecosystem_threat_level(d, p, m, t) == pytest.approx(expected)

    def test_missing_inputs_return_none(self):
        assert compute_ecosystem_threat_level(None, 2, 2, 2) is None
        assert compute_ecosystem_threat_level(2, 2, None, 2) is None

    def test_zero_denominator_guards_against_div_zero(self):
        # The factory uses positive integers so this is only reachable via direct
        # calls, but the guard must hold.
        assert compute_ecosystem_threat_level(2, 2, 0, 2) is None
        assert compute_ecosystem_threat_level(2, 2, 2, 0) is None

    def test_default_thresholds_map_to_zones(self):
        # threat_level = 0.25 -> control
        assert compute_ecosystem_threat_zone(0.25) == ThreatZone.CONTROL
        # threat_level = 1.0 -> monitoring
        assert compute_ecosystem_threat_zone(1.0) == ThreatZone.MONITORING
        # threat_level = 2.0 -> danger
        assert compute_ecosystem_threat_zone(2.0) == ThreatZone.DANGER

    def test_threshold_boundary_is_inclusive_on_upper_zone(self):
        # The default control threshold is 0.5 (exclusive on the lower side).
        assert compute_ecosystem_threat_zone(0.5) == ThreatZone.MONITORING
        # The default monitoring threshold is 1.5 (exclusive on the lower side).
        assert compute_ecosystem_threat_zone(1.5) == ThreatZone.DANGER

    def test_custom_thresholds_are_respected(self):
        thresholds = {"control": 1.0, "monitoring": 4.0}
        assert compute_ecosystem_threat_zone(0.9, thresholds) == ThreatZone.CONTROL
        assert compute_ecosystem_threat_zone(2.0, thresholds) == ThreatZone.MONITORING
        assert compute_ecosystem_threat_zone(5.0, thresholds) == ThreatZone.DANGER


class TestEcosystemStakeholderModel:
    def test_reference_prefix(self):
        s = EcosystemStakeholderFactory()
        assert s.reference.startswith("EECS-")

    def test_threat_level_computed_on_save(self):
        s = EcosystemStakeholderFactory(
            dependency=4, penetration=4, maturity=1, trust=1,
        )
        # (4*4)/(1*1) = 16
        assert s.threat_level == Decimal("16.00")
        assert s.threat_zone == ThreatZone.DANGER

    def test_threat_zone_control(self):
        s = EcosystemStakeholderFactory(
            dependency=1, penetration=1, maturity=4, trust=4,
        )
        # (1*1)/(4*4) = 0.0625
        assert s.threat_level == Decimal("0.06")
        assert s.threat_zone == ThreatZone.CONTROL

    def test_threat_zone_monitoring(self):
        s = EcosystemStakeholderFactory(
            dependency=2, penetration=2, maturity=2, trust=2,
        )
        # 1.0 -> monitoring with the default thresholds
        assert s.threat_level == Decimal("1.00")
        assert s.threat_zone == ThreatZone.MONITORING

    def test_threat_level_none_when_any_input_missing(self):
        s = EcosystemStakeholderFactory(dependency=None)
        assert s.threat_level is None
        assert s.threat_zone is None

    def test_clearing_input_clears_threat_level(self):
        s = EcosystemStakeholderFactory(
            dependency=2, penetration=2, maturity=2, trust=2,
        )
        assert s.threat_level is not None
        s.maturity = None
        s.save()
        s.refresh_from_db()
        assert s.threat_level is None
        assert s.threat_zone is None

    def test_snapshot_captured_on_first_scoring(self):
        s = EcosystemStakeholderFactory(
            dependency=2, penetration=2, maturity=2, trust=2,
        )
        snap = s.criteria_snapshot
        assert snap is not None
        assert snap["thresholds"]["control"] == DEFAULT_ECOSYSTEM_THRESHOLDS["control"]
        assert snap["thresholds"]["monitoring"] == DEFAULT_ECOSYSTEM_THRESHOLDS["monitoring"]

    def test_snapshot_not_overwritten_on_resave(self):
        s = EcosystemStakeholderFactory(
            dependency=2, penetration=2, maturity=2, trust=2,
        )
        original = s.criteria_snapshot
        s.dependency = 4
        s.save()
        s.refresh_from_db()
        assert s.criteria_snapshot == original

    def test_custom_thresholds_from_risk_criteria(self):
        criteria = RiskCriteriaFactory()
        criteria.risk_matrix = {
            "ebios_ecosystem_thresholds": {"control": 1.0, "monitoring": 4.0},
        }
        criteria.save()
        assessment = EbiosAssessmentFactory(risk_criteria=criteria)
        # threat_level = 1.0 with custom control=1.0 threshold -> monitoring (still)
        s = EcosystemStakeholder.objects.create(
            assessment=assessment,
            name="custom-thresholds",
            dependency=2, penetration=2, maturity=2, trust=2,
        )
        assert s.threat_zone == ThreatZone.MONITORING
        # threat_level = 0.5 with custom control=1.0 -> control (would be monitoring on defaults)
        s2 = EcosystemStakeholder.objects.create(
            assessment=assessment,
            name="below-control-custom",
            dependency=1, penetration=1, maturity=1, trust=2,
        )
        # (1*1)/(1*2) = 0.5
        assert s2.threat_zone == ThreatZone.CONTROL


class TestStrategicScenarioModel:
    def test_reference_prefix(self):
        s = StrategicScenarioFactory()
        assert s.reference.startswith("ESTS-")

    def test_risk_level_computed_via_matrix(self):
        # The default RiskAssessmentFactory does not set criteria, so use one.
        criteria = RiskCriteriaFactory()
        # Build an explicit symmetric 5x5 risk matrix keyed by "L,I"
        criteria.risk_matrix = {f"{l},{i}": min(l + i - 1, 5) for l in range(1, 6) for i in range(1, 6)}
        criteria.save()
        assessment = EbiosAssessmentFactory(risk_criteria=criteria)
        s = StrategicScenario.objects.create(
            assessment=assessment,
            sr_ov_pair=StrategicScenarioFactory(assessment=assessment).sr_ov_pair,
            name="test",
            description="test",
            gravity_level=3,
            likelihood_level=2,
        )
        # matrix[2,3] = min(2+3-1, 5) = 4
        assert s.risk_level == 4

    def test_risk_level_snapshot_captured(self):
        criteria = RiskCriteriaFactory()
        criteria.risk_matrix = {f"{l},{i}": l for l in range(1, 6) for i in range(1, 6)}
        criteria.save()
        assessment = EbiosAssessmentFactory(risk_criteria=criteria)
        s = StrategicScenarioFactory(
            assessment=assessment,
            gravity_level=2, likelihood_level=2,
        )
        assert s.criteria_snapshot is not None
        assert s.criteria_snapshot["criteria_reference"] == criteria.reference


class TestAttackPathStepModel:
    def test_reference_prefix(self):
        step = AttackPathStepFactory()
        assert step.reference.startswith("EAPS-")

    def test_uniqueness_of_order_per_scenario(self):
        scenario = StrategicScenarioFactory()
        AttackPathStepFactory(scenario=scenario, order=1)
        with pytest.raises(IntegrityError):
            AttackPathStep.objects.create(
                scenario=scenario, order=1, description="dup",
            )

    def test_same_order_different_scenario_allowed(self):
        AttackPathStepFactory(order=1)
        # Different scenario with the same order: ok
        AttackPathStepFactory(order=1)
        assert AttackPathStep.objects.count() == 2

    def test_default_ordering_is_by_order(self):
        scenario = StrategicScenarioFactory()
        AttackPathStepFactory(scenario=scenario, order=3)
        AttackPathStepFactory(scenario=scenario, order=1)
        AttackPathStepFactory(scenario=scenario, order=2)
        ordered = list(scenario.attack_path_steps.values_list("order", flat=True))
        assert ordered == [1, 2, 3]

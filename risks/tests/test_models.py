import pytest

from risks.tests.factories import (
    RiskAssessmentFactory,
    RiskCriteriaFactory,
    RiskFactory,
    RiskLevelFactory,
    ScaleLevelFactory,
)

pytestmark = pytest.mark.django_db


class TestRiskMatrixRebuild:
    """P0: rebuild_risk_matrix symmetric formula."""

    def _build_criteria_3x3(self):
        """Create a 3×3 criteria with 3 risk levels."""
        criteria = RiskCriteriaFactory()
        for i in range(1, 4):
            ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=i, name=f"L{i}")
            ScaleLevelFactory(criteria=criteria, scale_type="impact", level=i, name=f"I{i}")
        for i in range(1, 4):
            RiskLevelFactory(criteria=criteria, level=i, name=f"R{i}")
        return criteria

    def test_matrix_populated(self):
        criteria = self._build_criteria_3x3()
        criteria.rebuild_risk_matrix()
        criteria.refresh_from_db()
        assert criteria.risk_matrix
        assert len(criteria.risk_matrix) == 9  # 3x3

    def test_matrix_symmetric(self):
        """cell(L,I) should equal cell(I,L)."""
        criteria = self._build_criteria_3x3()
        criteria.rebuild_risk_matrix()
        criteria.refresh_from_db()
        m = criteria.risk_matrix
        for l_val in range(1, 4):
            for i_val in range(1, 4):
                assert m[f"{l_val},{i_val}"] == m[f"{i_val},{l_val}"]

    def test_matrix_corners(self):
        """Low-low should map to lowest level, high-high to highest."""
        criteria = self._build_criteria_3x3()
        criteria.rebuild_risk_matrix()
        criteria.refresh_from_db()
        m = criteria.risk_matrix
        assert m["1,1"] == 1  # lowest
        assert m["3,3"] == 3  # highest

    def test_empty_scales_produces_empty_matrix(self):
        criteria = RiskCriteriaFactory()
        criteria.rebuild_risk_matrix()
        criteria.refresh_from_db()
        assert criteria.risk_matrix == {}


class TestRiskLevelCalculation:
    """P0: Risk.calculate_risk_level via matrix."""

    def _create_risk_with_criteria(self):
        criteria = RiskCriteriaFactory()
        for i in range(1, 4):
            ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=i, name=f"L{i}")
            ScaleLevelFactory(criteria=criteria, scale_type="impact", level=i, name=f"I{i}")
        for i in range(1, 4):
            RiskLevelFactory(criteria=criteria, level=i, name=f"R{i}")
        criteria.rebuild_risk_matrix()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        return RiskFactory(assessment=assessment), criteria

    def test_auto_calculates_on_save(self):
        risk, criteria = self._create_risk_with_criteria()
        risk.current_likelihood = 3
        risk.current_impact = 3
        risk.save()
        risk.refresh_from_db()
        assert risk.current_risk_level is not None
        assert risk.current_risk_level == 3  # max in 3x3

    def test_initial_and_residual_calculated(self):
        risk, criteria = self._create_risk_with_criteria()
        risk.initial_likelihood = 1
        risk.initial_impact = 1
        risk.residual_likelihood = 2
        risk.residual_impact = 2
        risk.save()
        risk.refresh_from_db()
        assert risk.initial_risk_level == 1
        assert risk.residual_risk_level is not None

    def test_none_likelihood_returns_none(self):
        risk, criteria = self._create_risk_with_criteria()
        assert risk.calculate_risk_level(None, 3) is None

    def test_no_criteria_returns_none(self):
        assessment = RiskAssessmentFactory(risk_criteria=None)
        risk = RiskFactory(assessment=assessment)
        assert risk.calculate_risk_level(1, 1) is None


class TestRiskCriteriaSnapshot:
    """P0-A2: snapshot the risk matrix at evaluation time so later criteria
    edits do not rewrite historical scores."""

    def _build_evaluated_risk(self):
        criteria = RiskCriteriaFactory()
        for i in range(1, 4):
            ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=i, name=f"L{i}")
            ScaleLevelFactory(criteria=criteria, scale_type="impact", level=i, name=f"I{i}")
        for i in range(1, 4):
            RiskLevelFactory(criteria=criteria, level=i, name=f"R{i}")
        criteria.rebuild_risk_matrix()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(assessment=assessment)
        risk.initial_likelihood = 3
        risk.initial_impact = 3
        risk.save()
        risk.refresh_from_db()
        return risk, criteria

    def test_no_snapshot_when_not_evaluated(self):
        criteria = RiskCriteriaFactory()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(assessment=assessment)
        assert risk.criteria_snapshot is None

    def test_snapshot_captured_on_first_evaluation(self):
        risk, criteria = self._build_evaluated_risk()
        assert risk.criteria_snapshot is not None
        assert risk.criteria_snapshot["criteria_id"] == str(criteria.pk)
        assert risk.criteria_snapshot["criteria_name"] == criteria.name
        assert risk.criteria_snapshot["matrix"] == criteria.risk_matrix
        assert "captured_at" in risk.criteria_snapshot

    def test_score_remains_constant_after_criteria_edit(self):
        risk, criteria = self._build_evaluated_risk()
        original_score = risk.initial_risk_level
        original_matrix = dict(criteria.risk_matrix)

        # Mutate the criteria: rewrite the matrix so (3,3) maps to a different level.
        criteria.risk_matrix = {key: 1 for key in original_matrix}
        criteria.save()

        risk.refresh_from_db()
        risk.save()
        risk.refresh_from_db()
        assert risk.initial_risk_level == original_score
        assert risk.initial_risk_level != 1

    def test_snapshot_preserved_on_subsequent_saves(self):
        risk, criteria = self._build_evaluated_risk()
        first_snapshot = dict(risk.criteria_snapshot)
        risk.name = "renamed"
        risk.save()
        risk.refresh_from_db()
        assert risk.criteria_snapshot == first_snapshot

    def test_calculate_uses_snapshot_when_present(self):
        risk, criteria = self._build_evaluated_risk()
        # Stub a snapshot that maps everything to 5; criteria stays at 3.
        risk.criteria_snapshot = {
            "criteria_id": str(criteria.pk),
            "criteria_name": criteria.name,
            "criteria_version": 1,
            "matrix": {key: 5 for key in criteria.risk_matrix},
            "captured_at": "2026-01-01T00:00:00",
        }
        assert risk.calculate_risk_level(2, 2) == 5

    def test_falls_back_to_live_criteria_when_no_snapshot(self):
        criteria = RiskCriteriaFactory()
        for i in range(1, 4):
            ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=i, name=f"L{i}")
            ScaleLevelFactory(criteria=criteria, scale_type="impact", level=i, name=f"I{i}")
        for i in range(1, 4):
            RiskLevelFactory(criteria=criteria, level=i, name=f"R{i}")
        criteria.rebuild_risk_matrix()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(assessment=assessment)
        assert risk.criteria_snapshot is None
        assert risk.calculate_risk_level(3, 3) == 3

    def test_iso27005_snapshot_captured(self):
        from risks.models import ISO27005Risk
        from risks.tests.factories import RiskCriteriaFactory

        criteria = RiskCriteriaFactory()
        for i in range(1, 4):
            ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=i, name=f"L{i}")
            ScaleLevelFactory(criteria=criteria, scale_type="impact", level=i, name=f"I{i}")
        for i in range(1, 4):
            RiskLevelFactory(criteria=criteria, level=i, name=f"R{i}")
        criteria.rebuild_risk_matrix()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)

        from risks.models import Threat, Vulnerability
        threat = Threat.objects.create(name="T", type="deliberate")
        vuln = Vulnerability.objects.create(name="V", severity=3)
        iso = ISO27005Risk.objects.create(
            assessment=assessment, threat=threat, vulnerability=vuln,
            threat_likelihood=3, vulnerability_exposure=3,
            impact_confidentiality=3, impact_integrity=2, impact_availability=1,
        )
        iso.refresh_from_db()
        assert iso.risk_level is not None
        assert iso.criteria_snapshot is not None
        assert iso.criteria_snapshot["matrix"] == criteria.risk_matrix

        original_level = iso.risk_level
        criteria.risk_matrix = {key: 1 for key in criteria.risk_matrix}
        criteria.save()
        iso.save()
        iso.refresh_from_db()
        assert iso.risk_level == original_level

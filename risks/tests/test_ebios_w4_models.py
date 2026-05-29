"""Tests for EBIOS RM workshop W4 models.

Covers:
- Reference prefixes EOPS / EATT and the unprefixed MitreAttackTechnique.
- Gravity inheritance from the parent strategic scenario.
- Risk level computation via the assessment matrix (likelihood_v x gravity).
- AttackTechnique XOR constraint (MITRE FK or custom_name).
- AttackTechnique order uniqueness per scenario.
- MitreAttackTechnique parent / sub-technique relationship.
- MitreAttackTechnique seed via the bundled fixture.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from risks.constants import (
    MitreAttackTactic,
    ThreatLevelV,
)
from risks.models import AttackTechnique, MitreAttackTechnique, OperationalScenario
from risks.tests.factories import (
    AttackTechniqueFactory,
    EbiosAssessmentFactory,
    MitreAttackTechniqueFactory,
    OperationalScenarioFactory,
    RiskCriteriaFactory,
    StrategicScenarioFactory,
)


pytestmark = pytest.mark.django_db


class TestMitreAttackCatalogue:
    def test_seed_fixture_loads(self):
        # Force-reload of the bundled fixture using the helper logic to make
        # sure the file is valid and the parent_technique wiring works.
        from pathlib import Path
        import json

        path = (
            Path(__file__).resolve().parent.parent / "fixtures" / "mitre_attack_v15.json"
        )
        with open(path) as f:
            payload = json.load(f)
        by_mid = {}
        for entry in payload["techniques"]:
            obj, _ = MitreAttackTechnique.objects.update_or_create(
                mitre_id=entry["mitre_id"],
                defaults={
                    "name": entry["name"],
                    "description": entry.get("description", ""),
                    "tactic": entry["tactic"],
                    "url": entry.get("url", ""),
                    "version": payload["version"],
                },
            )
            by_mid[entry["mitre_id"]] = obj
        for entry in payload["techniques"]:
            parent_id = entry.get("parent_mitre_id")
            if parent_id and parent_id in by_mid:
                child = by_mid[entry["mitre_id"]]
                child.parent_technique = by_mid[parent_id]
                child.save(update_fields=["parent_technique"])
        assert MitreAttackTechnique.objects.filter(mitre_id="T1566").exists()
        # The two sub-techniques of T1566 must have it as parent
        sub = MitreAttackTechnique.objects.get(mitre_id="T1566.001")
        assert sub.parent_technique.mitre_id == "T1566"

    def test_tactic_field_indexable(self):
        for tactic in MitreAttackTactic:
            MitreAttackTechniqueFactory(
                mitre_id=f"T9{tactic.value[:4]}", tactic=tactic,
            )
        qs = MitreAttackTechnique.objects.filter(tactic=MitreAttackTactic.INITIAL_ACCESS)
        assert qs.exists()


class TestOperationalScenarioModel:
    def test_reference_prefix(self):
        s = OperationalScenarioFactory()
        assert s.reference.startswith("EOPS-")

    def test_gravity_inherited_from_parent(self):
        parent = StrategicScenarioFactory(gravity_level=4)
        scenario = OperationalScenarioFactory(
            assessment=parent.assessment,
            strategic_scenario=parent,
            gravity_level=None,  # Should be inherited
        )
        assert scenario.gravity_inherited is True
        assert scenario.gravity_level == 4

    def test_gravity_override_clears_inherited_flag(self):
        parent = StrategicScenarioFactory(gravity_level=4)
        # Pass gravity_inherited=False explicitly to override
        scenario = OperationalScenarioFactory(
            assessment=parent.assessment,
            strategic_scenario=parent,
            gravity_inherited=False,
            gravity_level=2,
            gravity_override_justification="lower scope impact",
        )
        assert scenario.gravity_inherited is False
        assert scenario.gravity_level == 2

    def test_risk_level_computed_via_matrix(self):
        criteria = RiskCriteriaFactory()
        criteria.risk_matrix = {
            f"{l},{i}": min(l + i - 1, 5) for l in range(1, 6) for i in range(1, 6)
        }
        criteria.save()
        assessment = EbiosAssessmentFactory(risk_criteria=criteria)
        parent = StrategicScenarioFactory(assessment=assessment, gravity_level=3)
        scenario = OperationalScenarioFactory(
            assessment=assessment,
            strategic_scenario=parent,
            likelihood_v=ThreatLevelV.V2,
        )
        # matrix[2,3] = min(2+3-1, 5) = 4
        assert scenario.risk_level == 4

    def test_risk_level_snapshot_captured(self):
        criteria = RiskCriteriaFactory()
        criteria.risk_matrix = {f"{l},{i}": l for l in range(1, 6) for i in range(1, 6)}
        criteria.save()
        assessment = EbiosAssessmentFactory(risk_criteria=criteria)
        parent = StrategicScenarioFactory(assessment=assessment, gravity_level=2)
        scenario = OperationalScenarioFactory(
            assessment=assessment,
            strategic_scenario=parent,
            likelihood_v=ThreatLevelV.V2,
        )
        assert scenario.criteria_snapshot is not None
        assert scenario.criteria_snapshot["criteria_reference"] == criteria.reference


class TestAttackTechniqueModel:
    def test_reference_prefix(self):
        tech = AttackTechniqueFactory()
        assert tech.reference.startswith("EATT-")

    def test_mitre_or_custom_name_required(self):
        scenario = OperationalScenarioFactory()
        tech = AttackTechnique(
            scenario=scenario,
            order=0,
            description="missing identifier",
        )
        with pytest.raises(ValidationError):
            tech.full_clean()

    def test_custom_name_only_is_valid(self):
        scenario = OperationalScenarioFactory()
        tech = AttackTechnique(
            scenario=scenario,
            order=0,
            description="custom only",
            custom_name="Insider Smart Card Theft",
        )
        tech.full_clean()
        tech.save()
        assert tech.pk is not None

    def test_display_name_prefers_mitre_when_set(self):
        mitre = MitreAttackTechniqueFactory(mitre_id="T1566", name="Phishing")
        tech = AttackTechniqueFactory(mitre_technique=mitre, custom_name="")
        assert "T1566" in str(tech.display_name)

    def test_uniqueness_of_order_per_scenario(self):
        scenario = OperationalScenarioFactory()
        AttackTechniqueFactory(scenario=scenario, order=1)
        with pytest.raises(IntegrityError):
            AttackTechnique.objects.create(
                scenario=scenario,
                order=1,
                description="dup",
                custom_name="dup",
            )

    def test_same_order_different_scenario_allowed(self):
        AttackTechniqueFactory(order=1)
        AttackTechniqueFactory(order=1)
        assert AttackTechnique.objects.count() == 2

    def test_default_ordering_is_by_order(self):
        scenario = OperationalScenarioFactory()
        AttackTechniqueFactory(scenario=scenario, order=3)
        AttackTechniqueFactory(scenario=scenario, order=1)
        AttackTechniqueFactory(scenario=scenario, order=2)
        ordered = list(scenario.attack_techniques.values_list("order", flat=True))
        assert ordered == [1, 2, 3]

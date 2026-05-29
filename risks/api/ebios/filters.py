import django_filters

from risks.models import (
    AttackPathStep,
    AttackTechnique,
    BaselineGap,
    EbiosWorkshopProgress,
    EcosystemStakeholder,
    FearedEvent,
    MitreAttackTechnique,
    OperationalScenario,
    RiskSource,
    RiskSourceObjectivePair,
    SecurityBaseline,
    StrategicScenario,
    StudyFramework,
    TargetedObjective,
)


class StudyFrameworkFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")

    class Meta:
        model = StudyFramework
        fields = {
            "status": ["exact"],
        }


class EbiosWorkshopProgressFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")

    class Meta:
        model = EbiosWorkshopProgress
        fields = {
            "workshop_number": ["exact"],
            "iteration_type": ["exact"],
            "iteration_number": ["exact"],
            "status": ["exact"],
        }


class SecurityBaselineFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")

    class Meta:
        model = SecurityBaseline
        fields = {
            "status": ["exact"],
            "is_approved": ["exact"],
        }


class FearedEventFilter(django_filters.FilterSet):
    baseline = django_filters.UUIDFilter(field_name="baseline_id")
    essential_asset = django_filters.UUIDFilter(field_name="essential_asset_id")

    class Meta:
        model = FearedEvent
        fields = {
            "dic_criterion": ["exact"],
            "gravity_level": ["exact", "gte", "lte"],
        }


class BaselineGapFilter(django_filters.FilterSet):
    baseline = django_filters.UUIDFilter(field_name="baseline_id")
    linked_requirement = django_filters.UUIDFilter(field_name="linked_requirement_id")

    class Meta:
        model = BaselineGap
        fields = {
            "severity": ["exact"],
            "status": ["exact"],
        }


class RiskSourceFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")
    threat_level_min = django_filters.NumberFilter(
        field_name="threat_level", lookup_expr="gte"
    )

    class Meta:
        model = RiskSource
        fields = {
            "category": ["exact"],
            "is_retained": ["exact"],
            "is_from_catalog": ["exact"],
            "is_approved": ["exact"],
            "threat_level": ["exact"],
        }


class TargetedObjectiveFilter(django_filters.FilterSet):
    risk_source = django_filters.UUIDFilter(field_name="risk_source_id")
    assessment = django_filters.UUIDFilter(field_name="risk_source__assessment_id")

    class Meta:
        model = TargetedObjective
        fields = {
            "category": ["exact"],
            "is_retained": ["exact"],
        }


class RiskSourceObjectivePairFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")
    risk_source = django_filters.UUIDFilter(field_name="risk_source_id")
    targeted_objective = django_filters.UUIDFilter(field_name="targeted_objective_id")
    priority_score_min = django_filters.NumberFilter(
        field_name="priority_score", lookup_expr="gte"
    )

    class Meta:
        model = RiskSourceObjectivePair
        fields = {
            "relevance": ["exact"],
            "is_retained": ["exact"],
            "is_approved": ["exact"],
            "priority_score": ["exact"],
        }


class EcosystemStakeholderFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")
    stakeholder = django_filters.UUIDFilter(field_name="stakeholder_id")
    supplier = django_filters.UUIDFilter(field_name="supplier_id")
    threat_level_min = django_filters.NumberFilter(
        field_name="threat_level", lookup_expr="gte"
    )

    class Meta:
        model = EcosystemStakeholder
        fields = {
            "category": ["exact"],
            "threat_zone": ["exact"],
            "is_attack_vector": ["exact"],
            "is_approved": ["exact"],
        }


class StrategicScenarioFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")
    sr_ov_pair = django_filters.UUIDFilter(field_name="sr_ov_pair_id")
    risk_level_min = django_filters.NumberFilter(
        field_name="risk_level", lookup_expr="gte"
    )

    class Meta:
        model = StrategicScenario
        fields = {
            "is_retained": ["exact"],
            "is_approved": ["exact"],
            "risk_level": ["exact"],
            "gravity_level": ["exact", "gte", "lte"],
            "likelihood_level": ["exact", "gte", "lte"],
        }


class AttackPathStepFilter(django_filters.FilterSet):
    scenario = django_filters.UUIDFilter(field_name="scenario_id")
    stakeholder = django_filters.UUIDFilter(field_name="stakeholder_id")

    class Meta:
        model = AttackPathStep
        fields = {
            "action_type": ["exact"],
            "difficulty": ["exact"],
        }


class MitreAttackTechniqueFilter(django_filters.FilterSet):
    parent_technique = django_filters.UUIDFilter(field_name="parent_technique_id")
    parent_mitre_id = django_filters.CharFilter(field_name="parent_technique__mitre_id")
    is_root = django_filters.BooleanFilter(
        field_name="parent_technique", lookup_expr="isnull"
    )

    class Meta:
        model = MitreAttackTechnique
        fields = {
            "mitre_id": ["exact", "icontains"],
            "tactic": ["exact"],
            "is_active": ["exact"],
        }


class OperationalScenarioFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")
    strategic_scenario = django_filters.UUIDFilter(field_name="strategic_scenario_id")
    risk_level_min = django_filters.NumberFilter(
        field_name="risk_level", lookup_expr="gte"
    )

    class Meta:
        model = OperationalScenario
        fields = {
            "likelihood_v": ["exact", "gte"],
            "gravity_level": ["exact", "gte", "lte"],
            "gravity_inherited": ["exact"],
            "is_approved": ["exact"],
            "risk_level": ["exact"],
        }


class AttackTechniqueFilter(django_filters.FilterSet):
    scenario = django_filters.UUIDFilter(field_name="scenario_id")
    mitre_technique = django_filters.UUIDFilter(field_name="mitre_technique_id")
    mitre_id = django_filters.CharFilter(field_name="mitre_technique__mitre_id")
    tactic = django_filters.CharFilter(field_name="mitre_technique__tactic")
    targeted_support_asset = django_filters.UUIDFilter(field_name="targeted_support_asset_id")

    class Meta:
        model = AttackTechnique
        fields = {
            "difficulty": ["exact"],
            "detection_difficulty": ["exact"],
        }

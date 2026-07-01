from rest_framework import serializers

from risks.models import (
    AttackPathStep,
    AttackTechnique,
    BaselineGap,
    EbiosSummary,
    EbiosWorkshopProgress,
    EcosystemStakeholder,
    FearedEvent,
    MitreAttackTechnique,
    OperationalScenario,
    PACSMeasure,
    RiskSource,
    RiskSourceObjectivePair,
    SecurityBaseline,
    StrategicScenario,
    StudyFramework,
    TargetedObjective,
)


class StudyFrameworkSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    class Meta:
        model = StudyFramework
        fields = [
            "id",
            "reference",
            "assessment",
            "mission_statement",
            "business_perimeter",
            "technical_perimeter",
            "temporal_perimeter",
            "financial_envelope",
            "participants",
            "participants_external",
            "applicable_frameworks",
            "assumptions",
            "constraints",
            "expected_deliverables",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "reference", "created_at", "updated_at"]


class EbiosWorkshopProgressSerializer(serializers.ModelSerializer):
    workshop_label = serializers.CharField(source="get_workshop_number_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    status = serializers.CharField(source="workflow_state", read_only=True)
    class Meta:
        model = EbiosWorkshopProgress
        fields = [
            "id",
            "reference",
            "assessment",
            "workshop_number",
            "workshop_label",
            "iteration_type",
            "iteration_number",
            "status",
            "status_label",
            "started_at",
            "validated_by",
            "validated_at",
            "rejection_reason",
            "deliverables_summary",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "workshop_label",
            "status_label",
            "validated_by",
            "validated_at",
            "created_at",
            "updated_at",
        ]


class SecurityBaselineSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="workflow_state", read_only=True)
    class Meta:
        model = SecurityBaseline
        fields = [
            "id",
            "reference",
            "assessment",
            "business_values",
            "essential_assets",
            "support_assets",
            "dic_summary",
            "baseline_references",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "created_at",
            "updated_at",
        ]


class FearedEventSerializer(serializers.ModelSerializer):
    dic_criterion_label = serializers.CharField(source="get_dic_criterion_display", read_only=True)

    class Meta:
        model = FearedEvent
        fields = [
            "id",
            "reference",
            "baseline",
            "essential_asset",
            "name",
            "description",
            "dic_criterion",
            "dic_criterion_label",
            "gravity_level",
            "gravity_justification",
            "business_impacts",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "dic_criterion_label",
            "created_at",
            "updated_at",
        ]


class BaselineGapSerializer(serializers.ModelSerializer):
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    status = serializers.CharField(source="workflow_state", read_only=True)
    class Meta:
        model = BaselineGap
        fields = [
            "id",
            "reference",
            "baseline",
            "reference_source",
            "linked_requirement",
            "description",
            "affected_support_assets",
            "severity",
            "severity_label",
            "recommended_remediation",
            "status",
            "status_label",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "severity_label",
            "status_label",
            "created_at",
            "updated_at",
        ]


class RiskSourceSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    threat_level_label = serializers.CharField(source="get_threat_level_display", read_only=True)

    class Meta:
        model = RiskSource
        fields = [
            "id",
            "reference",
            "assessment",
            "name",
            "description",
            "category",
            "category_label",
            "motivation_level",
            "motivation_description",
            "resources_level",
            "activity_level",
            "threat_level",
            "threat_level_label",
            "is_retained",
            "retention_justification",
            "is_from_catalog",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "category_label",
            "threat_level",
            "threat_level_label",
            "created_at",
            "updated_at",
        ]


class TargetedObjectiveSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = TargetedObjective
        fields = [
            "id",
            "reference",
            "risk_source",
            "name",
            "description",
            "category",
            "category_label",
            "targeted_essential_assets",
            "targeted_feared_events",
            "is_retained",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "category_label",
            "created_at",
            "updated_at",
        ]


class RiskSourceObjectivePairSerializer(serializers.ModelSerializer):
    relevance_label = serializers.CharField(source="get_relevance_display", read_only=True)

    class Meta:
        model = RiskSourceObjectivePair
        fields = [
            "id",
            "reference",
            "assessment",
            "risk_source",
            "targeted_objective",
            "relevance",
            "relevance_label",
            "relevance_justification",
            "priority_score",
            "is_retained",
            "retention_justification",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "relevance_label",
            "priority_score",
            "created_at",
            "updated_at",
        ]


class EcosystemStakeholderSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    threat_zone_label = serializers.CharField(source="get_threat_zone_display", read_only=True)

    class Meta:
        model = EcosystemStakeholder
        fields = [
            "id",
            "reference",
            "assessment",
            "stakeholder",
            "supplier",
            "name",
            "description",
            "category",
            "category_label",
            "dependency",
            "penetration",
            "maturity",
            "trust",
            "threat_level",
            "threat_zone",
            "threat_zone_label",
            "accessible_support_assets",
            "is_attack_vector",
            "attack_vector_justification",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "category_label",
            "threat_level",
            "threat_zone",
            "threat_zone_label",
            "created_at",
            "updated_at",
        ]


class AttackPathStepSerializer(serializers.ModelSerializer):
    action_type_label = serializers.CharField(source="get_action_type_display", read_only=True)
    difficulty_label = serializers.CharField(source="get_difficulty_display", read_only=True)

    class Meta:
        model = AttackPathStep
        fields = [
            "id",
            "reference",
            "scenario",
            "order",
            "stakeholder",
            "description",
            "action_type",
            "action_type_label",
            "difficulty",
            "difficulty_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "action_type_label",
            "difficulty_label",
            "created_at",
            "updated_at",
        ]


class StrategicScenarioSerializer(serializers.ModelSerializer):
    attack_path_steps = AttackPathStepSerializer(many=True, read_only=True)

    class Meta:
        model = StrategicScenario
        fields = [
            "id",
            "reference",
            "assessment",
            "name",
            "description",
            "sr_ov_pair",
            "targeted_feared_events",
            "gravity_level",
            "gravity_justification",
            "likelihood_level",
            "likelihood_justification",
            "risk_level",
            "existing_security_measures",
            "is_retained",
            "retention_justification",
            "consolidated_risk",
            "attack_path_steps",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "risk_level",
            "attack_path_steps",
            "created_at",
            "updated_at",
        ]


class MitreAttackTechniqueSerializer(serializers.ModelSerializer):
    tactic_label = serializers.CharField(source="get_tactic_display", read_only=True)

    class Meta:
        model = MitreAttackTechnique
        fields = [
            "id",
            "mitre_id",
            "name",
            "description",
            "tactic",
            "tactic_label",
            "parent_technique",
            "version",
            "url",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tactic_label", "created_at", "updated_at"]


class AttackTechniqueSerializer(serializers.ModelSerializer):
    difficulty_label = serializers.CharField(source="get_difficulty_display", read_only=True)
    detection_difficulty_label = serializers.CharField(
        source="get_detection_difficulty_display", read_only=True
    )
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = AttackTechnique
        fields = [
            "id",
            "reference",
            "scenario",
            "order",
            "mitre_technique",
            "custom_name",
            "display_name",
            "description",
            "targeted_support_asset",
            "difficulty",
            "difficulty_label",
            "detection_difficulty",
            "detection_difficulty_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "display_name",
            "difficulty_label",
            "detection_difficulty_label",
            "created_at",
            "updated_at",
        ]


class OperationalScenarioSerializer(serializers.ModelSerializer):
    likelihood_v_label = serializers.CharField(source="get_likelihood_v_display", read_only=True)
    attack_techniques = AttackTechniqueSerializer(many=True, read_only=True)

    class Meta:
        model = OperationalScenario
        fields = [
            "id",
            "reference",
            "assessment",
            "strategic_scenario",
            "name",
            "description",
            "targeted_support_assets",
            "gravity_level",
            "gravity_inherited",
            "gravity_override_justification",
            "likelihood_v",
            "likelihood_v_label",
            "likelihood_justification",
            "risk_level",
            "existing_controls",
            "existing_measures",
            "consolidated_risk",
            "mitre_version",
            "attack_techniques",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "likelihood_v_label",
            "risk_level",
            "attack_techniques",
            "created_at",
            "updated_at",
        ]


class PACSMeasureSerializer(serializers.ModelSerializer):
    measure_type_label = serializers.CharField(source="get_measure_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)

    status = serializers.CharField(source="workflow_state", read_only=True)
    class Meta:
        model = PACSMeasure
        fields = [
            "id",
            "reference",
            "summary",
            "name",
            "description",
            "measure_type",
            "measure_type_label",
            "linked_treatment_plans",
            "linked_baseline_gaps",
            "linked_requirements",
            "owner",
            "start_date",
            "target_date",
            "completion_date",
            "cost_estimate",
            "expected_gain",
            "priority",
            "priority_label",
            "status",
            "status_label",
            "progress_percentage",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "measure_type_label",
            "status_label",
            "priority_label",
            "created_at",
            "updated_at",
        ]


class EbiosSummarySerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    pacs_measures = PACSMeasureSerializer(many=True, read_only=True)

    status = serializers.CharField(source="workflow_state", read_only=True)
    class Meta:
        model = EbiosSummary
        fields = [
            "id",
            "reference",
            "assessment",
            "residual_risk_strategy",
            "monitoring_plan",
            "pacs_summary",
            "risk_mapping_before",
            "risk_mapping_after",
            "next_strategic_cycle_date",
            "next_operational_cycle_date",
            "validated_by",
            "validated_at",
            "status",
            "status_label",
            "pacs_measures",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "status_label",
            "validated_by",
            "validated_at",
            "risk_mapping_before",
            "risk_mapping_after",
            "pacs_measures",
            "created_at",
            "updated_at",
        ]

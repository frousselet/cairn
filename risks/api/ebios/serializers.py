from rest_framework import serializers

from risks.models import (
    BaselineGap,
    EbiosWorkshopProgress,
    FearedEvent,
    SecurityBaseline,
    StudyFramework,
)


class StudyFrameworkSerializer(serializers.ModelSerializer):
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
            "is_approved",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "is_approved",
            "approved_by",
            "approved_at",
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

from rest_framework import serializers

from reports.models import (
    IsmsChange,
    ManagementReview,
    ManagementReviewComment,
    ManagementReviewDecision,
    ManagementReviewParticipant,
    ManagementReviewTransition,
    Report,
)


class ReportSerializer(serializers.ModelSerializer):
    has_file = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id", "report_type", "name", "status", "frameworks",
            "file_name", "has_file", "created_at", "created_by",
        ]
        read_only_fields = [
            "id", "file_name", "has_file", "created_at", "created_by",
            "status", "name",
        ]

    def get_has_file(self, obj):
        return bool(obj.file_content)


class SoaReportCreateSerializer(serializers.Serializer):
    framework_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of framework UUIDs to include in the SoA.",
    )


class AuditReportCreateSerializer(serializers.Serializer):
    assessment_id = serializers.UUIDField(
        help_text="UUID of a completed or closed compliance assessment.",
    )


class ManagementReviewCreateSerializer(serializers.Serializer):
    format = serializers.ChoiceField(
        choices=["pptx", "docx"],
        help_text="Output format: 'pptx' for PowerPoint presentation, 'docx' for Word meeting minutes.",
    )
    scope_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        help_text="Optional list of scope UUIDs to filter data.",
    )
    period_start = serializers.DateField(
        required=False,
        default=None,
        help_text="Start of the review period (YYYY-MM-DD). Omit to include all past data.",
    )
    period_end = serializers.DateField(
        required=False,
        default=None,
        help_text="End of the review period (YYYY-MM-DD). Defaults to today.",
    )


# ── Persistent management review serializers ────────────────────────


class ManagementReviewParticipantSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    display_role = serializers.ReadOnlyField()

    class Meta:
        model = ManagementReviewParticipant
        fields = [
            "id", "user", "external_name", "external_role", "role",
            "attended", "display_name", "display_role",
        ]


class ManagementReviewDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagementReviewDecision
        fields = [
            "id", "reference", "review", "category", "input_clause",
            "title", "description", "rationale",
            "owner", "due_date", "priority", "status",
            "implemented_at", "implementation_evidence",
            "linked_action_plan", "linked_treatment_plan",
            "linked_objective", "linked_isms_change",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "reference", "created_at", "updated_at"]
        extra_kwargs = {"review": {"required": False}}


class IsmsChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IsmsChange
        fields = [
            "id", "reference", "review", "change_type", "title",
            "description", "impact_analysis",
            "affected_scopes", "affected_frameworks", "affected_policies",
            "owner", "status", "target_date", "implemented_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "reference", "created_at", "updated_at"]
        extra_kwargs = {"review": {"required": False}}


class ManagementReviewCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagementReviewComment
        fields = ["id", "review", "author", "content", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class ManagementReviewTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagementReviewTransition
        fields = [
            "id", "review", "from_status", "to_status",
            "performed_by", "comment", "created_at",
        ]
        read_only_fields = fields


class ManagementReviewSerializer(serializers.ModelSerializer):
    decisions_count = serializers.SerializerMethodField()
    isms_changes_count = serializers.SerializerMethodField()
    participants_count = serializers.SerializerMethodField()
    snapshot_available = serializers.BooleanField(
        source="has_snapshot", read_only=True,
    )

    status = serializers.CharField(source="workflow_state", read_only=True)
    class Meta:
        model = ManagementReview
        fields = [
            "id", "reference", "title", "description",
            "frequency", "period_start", "period_end",
            "planned_date", "held_date", "location",
            "status", "facilitator", "approver",
            "next_review_date", "summary", "agenda", "minutes",
            "scopes", "tags",
            "snapshot_available", "snapshot_taken_at",
            "is_approved", "approved_by", "approved_at",
            "decisions_count", "isms_changes_count", "participants_count",
            "created_at", "updated_at", "created_by",
        ]
        read_only_fields = [
            "id", "reference", "snapshot_available", "snapshot_taken_at",
            "is_approved", "approved_by", "approved_at",
            "decisions_count", "isms_changes_count", "participants_count",
            "created_at", "updated_at", "created_by",
        ]

    def get_decisions_count(self, obj):
        return obj.decisions.count()

    def get_isms_changes_count(self, obj):
        return obj.isms_changes.count()

    def get_participants_count(self, obj):
        return obj.participants.count()


class ManagementReviewDetailSerializer(ManagementReviewSerializer):
    participants = ManagementReviewParticipantSerializer(many=True, read_only=True)
    decisions = ManagementReviewDecisionSerializer(many=True, read_only=True)
    isms_changes = IsmsChangeSerializer(many=True, read_only=True)

    class Meta(ManagementReviewSerializer.Meta):
        fields = ManagementReviewSerializer.Meta.fields + [
            "participants", "decisions", "isms_changes",
        ]


class TransitionActionSerializer(serializers.Serializer):
    target_status = serializers.ChoiceField(
        choices=[
            "planned", "in_preparation", "held", "closed", "cancelled",
        ],
    )
    comment = serializers.CharField(required=False, allow_blank=True, default="")

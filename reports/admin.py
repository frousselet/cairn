from django.contrib import admin

from .models import (
    IsmsChange,
    ManagementReview,
    ManagementReviewComment,
    ManagementReviewDecision,
    ManagementReviewParticipant,
    ManagementReviewTransition,
    Report,
)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("name", "report_type", "status", "created_at", "created_by")
    list_filter = ("report_type", "status")
    search_fields = ("name",)


class ManagementReviewParticipantInline(admin.TabularInline):
    model = ManagementReviewParticipant
    extra = 0
    autocomplete_fields = ("user",)


class ManagementReviewDecisionInline(admin.TabularInline):
    model = ManagementReviewDecision
    extra = 0
    fields = ("reference", "title", "category", "owner", "due_date", "priority", "status")
    readonly_fields = ("reference",)
    autocomplete_fields = ("owner",)


class IsmsChangeInline(admin.TabularInline):
    model = IsmsChange
    extra = 0
    fields = ("reference", "title", "change_type", "owner", "status", "target_date")
    readonly_fields = ("reference",)
    autocomplete_fields = ("owner",)


@admin.register(ManagementReview)
class ManagementReviewAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "title", "frequency", "period_start", "period_end",
        "planned_date", "workflow_state", "facilitator",
    )
    list_filter = ("workflow_state", "frequency", "scopes")
    search_fields = ("reference", "title", "description")
    readonly_fields = ("reference", "snapshot_taken_at", "created_at", "updated_at")
    filter_horizontal = ("scopes", "tags")
    autocomplete_fields = ("facilitator", "approver")
    inlines = [
        ManagementReviewParticipantInline,
        ManagementReviewDecisionInline,
        IsmsChangeInline,
    ]


@admin.register(ManagementReviewDecision)
class ManagementReviewDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "title", "review", "category", "priority",
        "status", "owner", "due_date",
    )
    list_filter = ("status", "category", "priority")
    search_fields = ("reference", "title", "description")
    readonly_fields = ("reference", "created_at", "updated_at")
    autocomplete_fields = ("owner",)
    raw_id_fields = (
        "review", "linked_action_plan", "linked_treatment_plan",
        "linked_objective", "linked_isms_change",
    )


@admin.register(IsmsChange)
class IsmsChangeAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "title", "review", "change_type",
        "status", "owner", "target_date",
    )
    list_filter = ("status", "change_type")
    search_fields = ("reference", "title", "description")
    readonly_fields = ("reference", "created_at", "updated_at")
    filter_horizontal = ("affected_scopes", "affected_frameworks")
    autocomplete_fields = ("owner",)
    raw_id_fields = ("review",)


@admin.register(ManagementReviewComment)
class ManagementReviewCommentAdmin(admin.ModelAdmin):
    list_display = ("review", "author", "created_at")
    search_fields = ("content",)
    autocomplete_fields = ("author",)
    raw_id_fields = ("review",)


@admin.register(ManagementReviewTransition)
class ManagementReviewTransitionAdmin(admin.ModelAdmin):
    list_display = ("review", "from_status", "to_status", "performed_by", "created_at")
    list_filter = ("from_status", "to_status")
    autocomplete_fields = ("performed_by",)
    raw_id_fields = ("review",)

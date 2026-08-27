# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Django admin registrations for module 6.

The admin is a maintenance surface, not the product : the governed paths are
the web stepper, DRF and MCP, all of which funnel through `transition_to()`.
`workflow_state` is therefore read-only here on every lifecycle-bearing model,
so an administrator cannot move a record between steps without leaving the
`core.LifecycleEvent` row every gate and every report depends on.
"""
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    EvidenceCustodyEvent,
    Incident,
    IncidentEvidence,
    IncidentNotification,
    IncidentResponseAction,
    IncidentResponsePlan,
    IncidentTimelineEntry,
    NotificationFiling,
    PersonalDataBreach,
    PostIncidentReview,
    ReportingAuthority,
    ReportingObligationTemplate,
    SecurityEvent,
)

_LIFECYCLE_READONLY = ("workflow_state", "reference", "created_at", "updated_at")


class IncidentTimelineEntryInline(admin.TabularInline):
    model = IncidentTimelineEntry
    extra = 0
    # Append-only : the ledger is corrected by appending, never by editing.
    can_delete = False
    readonly_fields = ("occurred_at", "recorded_at", "entry_type", "summary", "source", "author")


class IncidentResponseActionInline(admin.TabularInline):
    model = IncidentResponseAction
    extra = 0
    readonly_fields = ("reference",)


class IncidentEvidenceInline(admin.TabularInline):
    model = IncidentEvidence
    extra = 0
    readonly_fields = ("reference", "workflow_state", "content_hash", "sealed_at")
    show_change_link = True


class IncidentNotificationInline(admin.TabularInline):
    model = IncidentNotification
    extra = 0
    readonly_fields = ("reference", "workflow_state", "due_at", "first_submitted_at", "late_by")
    show_change_link = True


@admin.register(Incident)
class IncidentAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "title", "severity", "category", "workflow_state", "detected_at")
    list_filter = ("workflow_state", "severity", "category", "is_exercise", "personal_data_involved")
    search_fields = ("reference", "title", "summary")
    readonly_fields = _LIFECYCLE_READONLY + (
        "declared_at", "triaged_at", "contained_at", "eradicated_at",
        "recovered_at", "closed_at", "initial_severity",
    )
    inlines = [
        IncidentTimelineEntryInline,
        IncidentResponseActionInline,
        IncidentEvidenceInline,
        IncidentNotificationInline,
    ]


@admin.register(SecurityEvent)
class SecurityEventAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "title", "event_class", "triage_decision", "workflow_state", "detected_at")
    list_filter = ("workflow_state", "event_class", "triage_decision", "detection_source")
    search_fields = ("reference", "title", "description")
    readonly_fields = _LIFECYCLE_READONLY + ("assessed_at", "assessed_by", "triage_decision")


@admin.register(IncidentResponsePlan)
class IncidentResponsePlanAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "name", "workflow_state", "effective_from", "review_date")
    list_filter = ("workflow_state",)
    search_fields = ("reference", "name", "purpose")
    readonly_fields = _LIFECYCLE_READONLY + ("last_exercise_date",)


@admin.register(IncidentEvidence)
class IncidentEvidenceAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "title", "evidence_type", "workflow_state", "legal_hold", "retention_until")
    list_filter = ("workflow_state", "evidence_type", "legal_hold", "hash_algorithm")
    search_fields = ("reference", "title", "storage_location")
    # The acquisition metadata is write-once once sealed. Leaving it editable
    # here would be the one path around that guard.
    readonly_fields = _LIFECYCLE_READONLY + (
        "content_hash", "hash_algorithm", "collected_at", "collection_method",
        "sealed_at", "last_integrity_check_at", "last_integrity_check_ok",
    )


@admin.register(EvidenceCustodyEvent)
class EvidenceCustodyEventAdmin(admin.ModelAdmin):
    list_display = ("evidence", "action", "occurred_at", "actor", "source")
    list_filter = ("action", "source")
    search_fields = ("evidence__reference", "counterparty", "notes")

    def has_change_permission(self, request, obj=None):
        # Append-only ledger : a custody chain that can be rewritten is not one.
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IncidentTimelineEntry)
class IncidentTimelineEntryAdmin(admin.ModelAdmin):
    list_display = ("incident", "occurred_at", "entry_type", "summary", "source")
    list_filter = ("entry_type", "source")
    search_fields = ("incident__reference", "summary", "detail")

    def has_change_permission(self, request, obj=None):
        # Corrections are appended as a new entry pointing at the superseded one.
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IncidentResponseAction)
class IncidentResponseActionAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "incident", "action_type", "status", "owner", "due_at")
    list_filter = ("action_type", "status")
    search_fields = ("reference", "title", "description")


@admin.register(PostIncidentReview)
class PostIncidentReviewAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "incident", "workflow_state", "scheduled_date", "effectiveness_verdict")
    list_filter = ("workflow_state", "root_cause_method", "effectiveness_verdict")
    search_fields = ("reference", "root_cause", "detection_gap")
    readonly_fields = _LIFECYCLE_READONLY


@admin.register(IncidentNotification)
class IncidentNotificationAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "incident", "regime", "workflow_state", "due_at", "first_submitted_at", "late_by")
    list_filter = ("workflow_state", "regime", "recipient_kind", "no_fixed_deadline")
    search_fields = ("reference", "recipient_name", "obligation_reference")
    # `late_by` and `first_submitted_at` are write-once on purpose : a later
    # anchor correction must never silently un-breach a filed obligation.
    readonly_fields = _LIFECYCLE_READONLY + (
        "anchor_at", "due_at", "first_submitted_at", "late_by", "sent_at", "decided_at",
    )


@admin.register(NotificationFiling)
class NotificationFilingAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "notification", "submitted_at", "channel", "outcome")
    list_filter = ("channel", "outcome", "is_correction")
    search_fields = ("reference", "external_reference", "subject")

    def has_delete_permission(self, request, obj=None):
        # The filing log is what proves the notification was made.
        return False


@admin.register(PersonalDataBreach)
class PersonalDataBreachAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "incident", "controller_role", "workflow_state", "high_risk_to_rights")
    list_filter = ("workflow_state", "controller_role", "special_categories", "article_34_exemption")
    search_fields = ("reference", "nature", "register_entry_reference")
    readonly_fields = _LIFECYCLE_READONLY + ("qualified_by", "qualified_at")


@admin.register(ReportingAuthority)
class ReportingAuthorityAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "name", "authority_type", "jurisdiction_country", "workflow_state")
    list_filter = ("workflow_state", "authority_type", "jurisdiction_country")
    search_fields = ("reference", "name", "short_name")
    readonly_fields = _LIFECYCLE_READONLY


@admin.register(ReportingObligationTemplate)
class ReportingObligationTemplateAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "name", "regime", "authority", "clock_hours", "workflow_state")
    list_filter = ("workflow_state", "regime", "recipient_kind", "no_fixed_deadline")
    search_fields = ("reference", "name", "legal_reference")
    readonly_fields = _LIFECYCLE_READONLY

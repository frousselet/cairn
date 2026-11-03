# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from documents.models import AcknowledgementCampaign, Policy, PolicyAcknowledgement, PolicyVersion


@admin.register(Policy)
class PolicyAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "title", "document_type", "owner", "workflow_state", "next_review_date")
    list_filter = ("document_type", "workflow_state")
    search_fields = ("reference", "title")


@admin.register(PolicyVersion)
class PolicyVersionAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "policy", "version_label", "workflow_state", "approved_by", "effective_from")
    list_filter = ("workflow_state",)
    search_fields = ("reference", "policy__title", "version_label")
    readonly_fields = ("approved_by", "approved_at", "superseded_at", "superseded_by", "file_sha256")


@admin.register(AcknowledgementCampaign)
class AcknowledgementCampaignAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "name", "policy_version", "due_date", "workflow_state")
    list_filter = ("workflow_state",)


@admin.register(PolicyAcknowledgement)
class PolicyAcknowledgementAdmin(SimpleHistoryAdmin):
    """Evidence rows : readable, never editable here (RG-DOC-16)."""

    list_display = ("campaign", "user", "status", "acknowledged_at")
    list_filter = ("status",)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

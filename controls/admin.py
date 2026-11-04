# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from controls.models import Control, ControlTest, ControlTestEvidence, ControlTestRun


@admin.register(Control)
class ControlAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "name", "theme", "owner", "workflow_state", "effectiveness")
    list_filter = ("theme", "nature", "workflow_state", "effectiveness")
    search_fields = ("reference", "name")
    readonly_fields = ("effectiveness", "effectiveness_updated_at")


@admin.register(ControlTest)
class ControlTestAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "name", "control", "method", "frequency_months", "next_due_date", "workflow_state")
    list_filter = ("method", "workflow_state")
    search_fields = ("reference", "name", "control__name")
    readonly_fields = ("next_due_date", "activated_on", "last_reminded_at")


@admin.register(ControlTestRun)
class ControlTestRunAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "test", "performed_by", "performed_on", "result", "workflow_state")
    list_filter = ("result", "workflow_state")
    search_fields = ("reference", "test__name")
    readonly_fields = ("reviewed_by", "reviewed_at")


@admin.register(ControlTestEvidence)
class ControlTestEvidenceAdmin(SimpleHistoryAdmin):
    """Evidence rows : readable, never editable here (RG-CTL-13)."""

    list_display = ("original_filename", "run", "size", "sha256", "uploaded_at")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

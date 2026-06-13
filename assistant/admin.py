"""Admin registration for Ask Cairn feedback, with a JSON export action.

The export produces the structured set of selected feedback that can be handed
to an LLM (Claude Code or other) to improve the assistant.
"""

import json

from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from assistant.models import AssistantFeedback


@admin.register(AssistantFeedback)
class AssistantFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "rating", "language", "short_question",
        "user", "has_comment", "provider", "model_name",
    )
    list_filter = ("rating", "language", "provider", "created_at")
    search_fields = ("question", "comment", "summary")
    date_hierarchy = "created_at"
    readonly_fields = (
        "id", "created_at", "user", "question", "language", "rating",
        "comment", "summary", "results", "degraded", "refused_tools",
        "provider", "model_name",
    )
    actions = ["export_as_json"]

    @admin.display(description=_("Question"))
    def short_question(self, obj):
        return (obj.question or "")[:80]

    @admin.display(boolean=True, description=_("Comment"))
    def has_comment(self, obj):
        return bool(obj.comment)

    @admin.action(description=_("Export selected feedback as JSON"))
    def export_as_json(self, request, queryset):
        payload = {
            "count": queryset.count(),
            "feedback": [obj.as_export_dict() for obj in queryset],
        }
        response = HttpResponse(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
        response["Content-Disposition"] = 'attachment; filename="assistant_feedback.json"'
        return response

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

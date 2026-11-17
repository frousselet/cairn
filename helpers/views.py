# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View


#: A help key is the identifier of a page ("context.scope_list").
MAX_HELPER_KEY_LENGTH = 100
#: Far above the number of pages that carry a help; a bound, so the list a
#: reader keeps cannot be grown without end by posting made-up keys.
MAX_DISMISSED_HELPERS = 500


class DismissHelperView(LoginRequiredMixin, View):
    """Keep, for the current user, that a help is hidden or shown again.

    The body is ``{"key": "...", "dismissed": true}``; ``dismissed`` may be
    left out (hidden) and ``false`` brings the help back.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        key = data.get("key")
        key = key.strip() if isinstance(key, str) else ""
        if not key:
            return JsonResponse({"error": "Missing key"}, status=400)
        if len(key) > MAX_HELPER_KEY_LENGTH:
            return JsonResponse({"error": "Invalid key"}, status=400)
        hidden = data.get("dismissed", True)
        if not isinstance(hidden, bool):
            return JsonResponse({"error": "Invalid value"}, status=400)

        dismissed = request.user.dismissed_helpers
        if not isinstance(dismissed, list):
            dismissed = []

        if hidden and key not in dismissed:
            if len(dismissed) >= MAX_DISMISSED_HELPERS:
                return JsonResponse({"error": "Too many keys"}, status=400)
            dismissed = [*dismissed, key]
        elif not hidden and key in dismissed:
            dismissed = [item for item in dismissed if item != key]
        else:
            return JsonResponse({"status": "ok", "dismissed": hidden})

        request.user.dismissed_helpers = dismissed
        request.user.save(update_fields=["dismissed_helpers"])
        return JsonResponse({"status": "ok", "dismissed": hidden})


class SaveSortPreferenceView(LoginRequiredMixin, View):
    """Save the sort preference for a specific list view."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        view_key = data.get("view", "").strip()
        sort_field = data.get("sort", "").strip()
        order = data.get("order", "asc").strip()

        if not view_key or not sort_field:
            return JsonResponse({"error": "Missing view or sort"}, status=400)
        if order not in ("asc", "desc"):
            return JsonResponse({"error": "Invalid order"}, status=400)

        prefs = request.user.table_preferences
        if not isinstance(prefs, dict):
            prefs = {}

        prefs[view_key] = {"sort": sort_field, "order": order}
        request.user.table_preferences = prefs
        request.user.save(update_fields=["table_preferences"])

        return JsonResponse({"status": "ok"})


class SaveColumnPreferenceView(LoginRequiredMixin, View):
    """Save the column layout (order + hidden) for a specific list view."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        view_key = (data.get("view") or "").strip()
        order = data.get("order")
        hidden = data.get("hidden")
        if not view_key:
            return JsonResponse({"error": "Missing view"}, status=400)
        if not isinstance(order, list) or not isinstance(hidden, list):
            return JsonResponse({"error": "Invalid layout"}, status=400)

        # Keep only string keys; cap length to guard against junk payloads.
        order = [str(k) for k in order][:100]
        hidden = [str(k) for k in hidden][:100]

        prefs = request.user.column_preferences
        if not isinstance(prefs, dict):
            prefs = {}
        prefs[view_key] = {"order": order, "hidden": hidden}
        request.user.column_preferences = prefs
        request.user.save(update_fields=["column_preferences"])

        return JsonResponse({"status": "ok"})

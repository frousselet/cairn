import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View


class DismissHelperView(LoginRequiredMixin, View):
    """Persist the dismissal of a help banner for the current user."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        key = data.get("key", "").strip()
        if not key:
            return JsonResponse({"error": "Missing key"}, status=400)

        dismissed = request.user.dismissed_helpers
        if not isinstance(dismissed, list):
            dismissed = []

        if key not in dismissed:
            dismissed.append(key)
            request.user.dismissed_helpers = dismissed
            request.user.save(update_fields=["dismissed_helpers"])

        return JsonResponse({"status": "ok"})


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

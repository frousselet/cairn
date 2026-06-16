"""Generic lazy-loaded history panel endpoint for any lifecycle element.

Returns the rendered timeline partial consumed by the off-canvas history panel.
A single endpoint for every entity, addressed by ``app_label / model / pk`` like
:class:`core.workflow_views.WorkflowTransitionView`, so detail pages pay for the
(potentially expensive) diff computation only when the panel is opened.
"""

from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views import View

from context.models.base import BaseModel
from core.history import DEFAULT_HISTORY_LIMIT, build_timeline, extra_source_for


class HistoryPartialView(LoginRequiredMixin, View):
    """GET the rendered history timeline for one element (HTMX target)."""

    def get(self, request, app_label, model, pk):
        try:
            model_class = apps.get_model(app_label, model)
        except LookupError:
            raise Http404
        if not (isinstance(model_class, type) and issubclass(model_class, BaseModel)):
            raise Http404
        if not hasattr(model_class, "history"):
            raise Http404
        obj = get_object_or_404(model_class, pk=pk)

        user = request.user
        if not user.is_superuser:
            # Read permission, derived the same way as the workflow layer.
            if not user.has_perm(f"{obj.workflow_perm_namespace}.read"):
                raise PermissionDenied
            # Scope guard (mirrors ScopeFilterMixin for scoped models).
            allowed_scopes = user.get_allowed_scope_ids()
            if allowed_scopes is not None and hasattr(obj, "scopes"):
                obj_scopes = set(obj.scopes.values_list("id", flat=True))
                if obj_scopes and not (obj_scopes & set(allowed_scopes)):
                    raise Http404

        entries = build_timeline(
            obj, limit=DEFAULT_HISTORY_LIMIT, extra=extra_source_for(obj)
        )
        return render(
            request,
            "includes/history_timeline.html",
            {"history_records": entries},
        )

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import logging

from django.utils.translation import gettext as _
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from context.models import Scope
from core.scoping import filter_queryset_by_scopes
from core.history import (
    DEFAULT_HISTORY_LIMIT,
    MAX_HISTORY_LIMIT,
    build_timeline,
    extra_source_for,
)

logger = logging.getLogger(__name__)


class LifecycleAPIMixin:
    """Lifecycle support for ViewSets: a ``?workflow_state=`` list filter and a
    ``/transition/`` action (GET lists the caller's allowed steps, POST performs
    one through the lifecycle service)."""

    def get_queryset(self):
        """Support filtering any lifecycle entity list by ``?workflow_state=``."""
        qs = super().get_queryset()
        raw = self.request.query_params.get("workflow_state") if self.request else None
        if raw:
            try:
                qs.model._meta.get_field("workflow_state")
            except Exception:
                return qs
            states = [s for s in raw.split(",") if s]
            if states:
                qs = qs.filter(workflow_state__in=states)
        return qs

    def _lifecycle_transition(self, request, obj, lifecycle):
        """Handle GET/POST transition for an entity on the standardised engine."""
        from django.core.exceptions import ValidationError
        from core.lifecycle import LifecycleError, TransitionNotAllowedError
        from core.transition_messages import transition_error_detail

        current = obj.workflow_state or lifecycle.initial_step.code

        if request.method == "GET":
            transitions = obj.available_transitions(user=request.user)
            return Response({
                "workflow": lifecycle.name,
                "workflow_state": current,
                "allowed_transitions": [
                    {
                        "target": t.target,
                        "verb": str(t.label),
                        "action": "update",
                        "requires_comment": t.requires_comment,
                    }
                    for t in transitions
                ],
            })

        target = request.data.get("target_state")
        comment = request.data.get("comment") or None
        if not target:
            return Response(
                {"detail": "target_state is required."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        try:
            obj.transition_to(target, request.user, comment=comment, enforce_permission=True)
        except TransitionNotAllowedError as exc:
            raise PermissionDenied(transition_error_detail(exc))
        except (LifecycleError, ValidationError) as exc:
            return Response(
                {"detail": transition_error_detail(exc)},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="transition")
    def transition(self, request, **kwargs):
        """GET: list the caller's allowed lifecycle transitions. POST: perform one.

        Lists / performs the transition through the lifecycle service, so the API
        reflects the real step graph. The endpoint is gated by the module
        permission (read for GET, update for POST) and the per-transition role /
        permission is enforced inside ``_lifecycle_transition``.
        """
        obj = self.get_object()
        return self._lifecycle_transition(request, obj, obj.get_lifecycle())


class HistoryAPIMixin:
    """Add a /history/ action returning the unified, normalized timeline.

    Delegates to :func:`core.history.build_timeline` so the API, the UI panel
    and the MCP tools share one classifier: field diffs, approval events and
    lifecycle transitions (with comments where a dedicated log exists) are
    merged into one reverse-chronological stream. Supports ``?limit=`` and
    ``?offset=`` query parameters.
    """

    history_limit = DEFAULT_HISTORY_LIMIT

    @action(detail=True, methods=["get"])
    def history(self, request, **kwargs):
        obj = self.get_object()
        try:
            limit = int(request.query_params.get("limit", self.history_limit))
        except (TypeError, ValueError):
            limit = self.history_limit
        limit = max(1, min(limit, MAX_HISTORY_LIMIT))
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
        except (TypeError, ValueError):
            offset = 0

        entries = build_timeline(obj, limit=limit + offset, extra=extra_source_for(obj))
        page = entries[offset:offset + limit]
        return Response({
            "limit": limit,
            "offset": offset,
            "has_more": len(entries) > offset + limit,
            "results": [e.as_dict() for e in page],
        })


def restrict_serializer_relations(serializer, user, *, keep_held=True):
    """Make the relations a serializer writes point at what `user` may select.

    The related fields of a serializer accept any identifier of their model :
    a caller restricted to one scope could link their record to the record of
    another (and read its name back in the answer), or file a new record
    under a scope they are not given. Each writable relation to a scoped
    model now accepts what the caller may select (`core.scoping.selectable`),
    plus what the record already holds, so that sending a record back as it
    was read never fails. A caller limited to some scopes files what they
    create under one of them : the `scopes` of a new record cannot be empty.

    `keep_held` is for an update : it costs a query per relation to many, so
    a read (which validates nothing) does without.
    """
    from rest_framework import serializers

    from core.scoping import held_by, is_restricted, resolve_scope_lookup, selectable

    if not is_restricted(user):
        return serializer
    target = getattr(serializer, "child", serializer)
    fields = getattr(target, "fields", None)
    if fields is None:
        return serializer
    instance = getattr(serializer, "instance", None)
    if instance is not None and not hasattr(instance, "_meta"):
        instance = None  # a list of records : each relation is checked by reach alone
    creating = instance is None
    for name, field in fields.items():
        if field.read_only:
            continue
        relation = getattr(field, "child_relation", field)
        if not isinstance(relation, serializers.RelatedField):
            if isinstance(field, serializers.BaseSerializer):
                restrict_serializer_relations(field, user, keep_held=keep_held)
            continue
        queryset = getattr(relation, "queryset", None)
        if queryset is None:
            continue
        queryset = queryset.all()
        lookup = resolve_scope_lookup(queryset.model)
        if lookup is None:
            continue
        source = field.source if field.source and field.source != "*" else name
        held = held_by(instance, source) if keep_held else ()
        relation.queryset = selectable(user, queryset, keep=held)
        if creating and lookup == "id" and source == "scopes" and relation is not field:
            field.allow_empty = False
            field.required = True
    return serializer


class ReachableRelationsAPIMixin:
    """The relations written through an API class stay within the caller's reach.

    Every serializer the class builds goes through
    :func:`restrict_serializer_relations`. `ScopeFilterAPIMixin` includes it;
    a class that serves an unscoped model but links it to scoped records (a
    Trust Center entry published from a document) carries it on its own.
    """

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if user is not None:
            restrict_serializer_relations(
                serializer, user, keep_held=getattr(request, "method", "") in ("PUT", "PATCH"),
            )
        return serializer


class ScopeFilterAPIMixin(ReachableRelationsAPIMixin):
    """Filter queryset by the user's allowed scopes (DRF ViewSets).

    Works for:
    - ViewSets with ``scope_parent_lookup`` attribute → filter via parent FK path
    - Models with a ``scopes`` M2M → filter on scopes__id
    - Models declaring ``scope_parent_lookup`` → filter via the parent's scopes
    - Scope model itself → filter on id

    Every viewset serving a model with a path to the scopes carries it :
    ``core/tests/test_scoping.py`` fails on one that does not.
    """

    scope_parent_lookup = None

    #: ``(model, url kwarg)`` of the record a nested resource hangs under
    #: (``/roles/<role_pk>/responsibilities/``). The parent named by the URL is
    #: fetched within the user's scopes before any handler runs : without it a
    #: child could be created under the record of another scope.
    scope_parent = None

    def initial(self, request, *args, **kwargs):
        # Authentication and permissions first : an anonymous or unauthorised
        # request is refused before a record is looked for.
        super().initial(request, *args, **kwargs)
        if self.scope_parent is not None:
            from core.scoping import get_scoped_object_or_404

            model, kwarg = self.scope_parent
            self.parent_record = get_scoped_object_or_404(request.user, model, pk=kwargs[kwarg])

    def _within_scopes(self, qs):
        user = self.request.user

        if not user.is_authenticated or user.is_superuser:
            return qs

        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs

        return filter_queryset_by_scopes(
            qs, scope_ids, explicit=getattr(self, "scope_parent_lookup", None)
        )

    def get_queryset(self):
        return self._within_scopes(super().get_queryset())

    def filter_queryset(self, queryset):
        """Restrict a queryset the viewset built on its own.

        A viewset that writes its own ``get_queryset`` (a nested resource
        filtering on its parent) does not go through the one above. Every
        list and every single-record lookup of DRF passes here : the scopes
        are applied at this point for those viewsets.
        """
        queryset = super().filter_queryset(queryset)
        if type(self).get_queryset is ScopeFilterAPIMixin.get_queryset:
            return queryset
        return self._within_scopes(queryset)


class BatchCreateMixin:
    """Add a batch/ endpoint to create multiple objects in a single request."""

    batch_max_items = 100

    @action(detail=False, methods=["post"], url_path="batch")
    def batch_create(self, request):
        items = request.data.get("items", [])

        if not isinstance(items, list):
            return Response(
                {"error": "The 'items' field must be a list."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        if len(items) > self.batch_max_items:
            return Response(
                {"error": f"Maximum {self.batch_max_items} items per batch."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        results = []
        created_count = 0
        error_count = 0

        for index, item_data in enumerate(items):
            serializer = self.get_serializer(data=item_data)
            if serializer.is_valid():
                try:
                    instance = serializer.save(
                        **self._get_batch_create_kwargs(request)
                    )
                    results.append({
                        "index": index,
                        "status": "created",
                        "id": str(instance.pk),
                        "reference": getattr(instance, "reference", None),
                    })
                    created_count += 1
                except Exception as e:
                    results.append({
                        "index": index,
                        "status": "error",
                        "errors": {"non_field_errors": [_("This item could not be created.")]},
                    })
                    error_count += 1
            else:
                results.append({
                    "index": index,
                    "status": "error",
                    "errors": serializer.errors,
                })
                error_count += 1

        return Response({
            "status": "completed" if error_count == 0 else "completed_with_errors",
            "total": len(items),
            "created": created_count,
            "errors": error_count,
            "results": results,
        })

    def _get_batch_create_kwargs(self, request):
        """Extra kwargs passed to serializer.save() for each batch item."""
        kwargs = {}
        if hasattr(self, "perform_create"):
            # Check if the viewset sets created_by
            model = self.get_queryset().model
            if hasattr(model, "created_by"):
                kwargs["created_by"] = request.user
        return kwargs

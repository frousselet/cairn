# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""
MCP tool definitions covering all Cairn API functionality.

Each tool maps to one or more API endpoints and performs operations
using the Django ORM directly, respecting the user's permissions.
"""

import json
from functools import wraps

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from core.scoping import filter_queryset_by_scopes
from mcp.server import InvalidParamsError


# ── Permission helpers ─────────────────────────────────────

def require_perm(codename):
    """Decorator that checks user permission before executing tool handler."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(user, arguments):
            if not user.is_superuser and not user.has_perm(codename):
                return _error(f"Permission denied: {codename}")
            return fn(user, arguments)
        # Exposed so the reference-documentation generator can state which
        # permission each MCP tool requires, without re-deriving it by hand.
        wrapper.required_perm = codename
        return wrapper
    return decorator


def _error(message):
    return {
        "content": [{"type": "text", "text": json.dumps({"error": message}, ensure_ascii=False)}],
        "isError": True,
    }


def _serialize_obj(obj, fields=None):
    """Simple serialization of a model instance to dict.

    Handles regular fields, FKs (returns PK string), M2M / reverse FK managers
    (returns list of PK strings), datetimes (ISO format), and JSONField dicts.
    """
    if fields is None:
        fields = [f.name for f in obj._meta.fields]
    data = {}
    for field_name in fields:
        val = getattr(obj, field_name, None)
        if val is None:
            data[field_name] = None
            continue
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        elif hasattr(val, "pk"):
            val = str(val.pk)
        elif hasattr(val, "all") and callable(val.all):
            # ManyRelatedManager (M2M) or reverse-FK manager: expand to PK list
            try:
                val = [str(item.pk) for item in val.all()]
            except (AttributeError, TypeError):
                val = None
        elif isinstance(val, (list, dict, set, bool, int, float)):
            if isinstance(val, set):
                val = list(val)
        else:
            val = str(val)
        data[field_name] = val
    return data


def _serialize_qs(qs, fields=None, limit=50, offset=0):
    """Serialize a queryset to list of dicts."""
    qs = qs[offset:offset + limit]
    return [_serialize_obj(obj, fields) for obj in qs]


def _get_model(app_label, model_name):
    return apps.get_model(app_label, model_name)


def _filter_by_scopes(qs, user, model=None, parent_lookup=None):
    """Apply scope-based filtering to a queryset.

    Resolution is delegated to ``core.scoping`` so a model declaring
    ``scope_parent_lookup`` is filtered here exactly as it is on the web and
    DRF surfaces. Before that, this returned child rows unfiltered.
    """
    if user.is_superuser:
        return qs
    scope_ids = user.get_allowed_scope_ids()
    if scope_ids is None:
        return qs
    return filter_queryset_by_scopes(qs, scope_ids, explicit=parent_lookup)


def _apply_filters(qs, arguments, allowed_filters):
    """Apply simple equality filters from arguments."""
    for key in allowed_filters:
        val = arguments.get(key)
        if val is not None:
            qs = qs.filter(**{key: val})
    return qs


def _apply_search(qs, arguments, search_fields):
    """Apply text search across multiple fields."""
    search = arguments.get("search")
    if search and search_fields:
        q = Q()
        for field in search_fields:
            q |= Q(**{f"{field}__icontains": search})
        qs = qs.filter(q)
    return qs


# ── Generic CRUD helpers ───────────────────────────────────

def _list_handler(model_class, fields, search_fields=None, filters=None, scope_filtered=True,
                  queryset_filter=None):
    """Create a generic list handler.

    ``queryset_filter`` is an optional ``(qs, arguments) -> qs`` hook applied
    after the standard equality filters, for derived filters the generic
    equality machinery cannot express (e.g. "contract expired").
    """
    def handler(user, arguments):
        qs = model_class.objects.all()
        if scope_filtered:
            qs = _filter_by_scopes(qs, user)
        if search_fields:
            qs = _apply_search(qs, arguments, search_fields)
        if filters:
            qs = _apply_filters(qs, arguments, filters)
        if queryset_filter:
            qs = queryset_filter(qs, arguments)
        limit = min(int(arguments.get("limit", 25)), 100)
        offset = int(arguments.get("offset", 0))
        total = qs.count()
        items = _serialize_qs(qs, fields, limit=limit, offset=offset)
        return {"total": total, "items": items, "limit": limit, "offset": offset}
    return handler


def _get_handler(model_class, fields, scope_filtered=True):
    """Create a generic get-by-id handler."""
    def handler(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if scope_filtered:
            qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
            if not qs.exists():
                return _error("Access denied: object is outside your allowed scopes.")
        return _serialize_obj(obj, fields)
    return handler


def _resolve_model_field(model_class, field_name):
    """Resolve a Django model field by name, accepting both 'foo' and 'foo_id'.

    Returns the field object, or None if unknown.
    """
    try:
        return model_class._meta.get_field(field_name)
    except Exception:
        if field_name.endswith("_id"):
            try:
                return model_class._meta.get_field(field_name[:-3])
            except Exception:
                return None
        return None


def _fk_kwarg_name(model_class, field_name):
    """Return the kwarg name to use when constructing model_class.

    For ForeignKey fields, Django's __init__ refuses raw PK values when the
    kwarg key is the field name ('type=12'); it only accepts the descriptor
    suffix form ('type_id=12'). This helper rewrites 'type' to 'type_id' for
    every FK so the MCP layer can keep exposing the natural attribute name.
    """
    from django.db.models import ForeignKey
    field = _resolve_model_field(model_class, field_name)
    if isinstance(field, ForeignKey) and not field_name.endswith("_id"):
        return field_name + "_id"
    return field_name


def _coerce_field_value(model_class, field_name, value):
    """Coerce a value to the correct Python type for a Django model field.

    MCP arguments arrive as strings/JSON; this ensures integer fields get ints,
    boolean fields get bools, and JSON fields get parsed dicts/lists.
    """
    if value is None:
        return value
    field = _resolve_model_field(model_class, field_name)
    if field is None:
        return value
    from django.db.models import (
        IntegerField, PositiveIntegerField, PositiveSmallIntegerField,
        SmallIntegerField, BigIntegerField, BooleanField, FloatField,
        JSONField, ForeignKey, AutoField,
    )
    int_types = (IntegerField, PositiveIntegerField, PositiveSmallIntegerField,
                 SmallIntegerField, BigIntegerField)
    # ForeignKey: coerce the PK value to the related model's PK type
    if isinstance(field, ForeignKey):
        related_pk = field.related_model._meta.pk
        if isinstance(related_pk, (AutoField,) + int_types):
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        return value
    if isinstance(field, int_types):
        try:
            return int(value)
        except (ValueError, TypeError):
            # For IntegerChoices fields, accept text labels (e.g., "medium" -> 2)
            if hasattr(field, 'choices') and field.choices:
                value_lower = str(value).lower()
                for choice_val, choice_label in field.choices:
                    if value_lower == str(choice_label).lower():
                        return choice_val
            return value
    if isinstance(field, BooleanField):
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    if isinstance(field, FloatField):
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    if isinstance(field, JSONField) and isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


TIMESTAMP_OVERRIDE_PERM = "system.data_import.override_dates"


def _parse_iso_datetime(value):
    """Parse a date/date-time string leniently; return a datetime or None.

    Accepts full ISO 8601 (microseconds and a ``Z`` or ``+hh:mm`` offset, as
    Django/DRF exports emit) then the common ``YYYY-MM-DD[ HH:MM[:SS]]`` forms.
    """
    from datetime import datetime

    candidate = str(value).strip()
    if not candidate:
        return None
    iso = candidate[:-1] + "+00:00" if candidate.endswith("Z") else candidate
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def _apply_timestamp_override(obj, model_class, data, user):
    """Preserve ``created_at`` / ``updated_at`` from the request when permitted.

    Bulk migration from a legacy tool needs the original timestamps. They are
    applied via a post-save ``.update()`` (bypassing ``auto_now`` /
    ``auto_now_add``) only for a user holding ``system.data_import.override_dates``
    (or a superuser); otherwise the supplied values are ignored so ordinary
    callers can never rewrite audit timestamps.

    Returns ``None`` when no timestamp was supplied, or a status string so the
    caller can tell what happened: ``"applied"`` (dates written) or
    ``"ignored_no_permission"`` (dates supplied but the caller lacks the
    permission, so they were dropped).
    """
    if not data:
        return None
    model_fields = {f.name for f in model_class._meta.fields}
    supplied = [
        f for f in ("created_at", "updated_at")
        if data.get(f) and f in model_fields
    ]
    if not supplied:
        return None
    if not (getattr(user, "is_superuser", False) or user.has_perm(TIMESTAMP_OVERRIDE_PERM)):
        return "ignored_no_permission"
    from django.conf import settings

    updates = {}
    for field_name in supplied:
        parsed = _parse_iso_datetime(data.get(field_name))
        if parsed is None:
            continue
        if settings.USE_TZ and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed)
        updates[field_name] = parsed
    if updates:
        model_class.objects.filter(pk=obj.pk).update(**updates)
        for field_name, value in updates.items():
            setattr(obj, field_name, value)
        return "applied"
    return None


def _create_handler(model_class, writable_fields, scope_filtered=True, m2m_fields=None,
                    pre_clean=None):
    """Create a generic create handler.

    ``pre_clean`` runs on the unsaved instance just before ``full_clean()``.
    It exists for models whose ``clean()`` reads a value that ``save()``
    derives : validating before the derivation makes the rule fail on a field
    the caller never supplied and cannot supply. The web form and the DRF
    serializer both close that gap explicitly; without this hook the MCP tool
    is the only surface that cannot create the row at all.
    """
    m2m_fields = m2m_fields or {}

    def handler(user, arguments):
        kwargs = {}
        m2m_values = {}
        for field_name in writable_fields:
            if field_name in arguments:
                if field_name in m2m_fields:
                    m2m_values[field_name] = arguments[field_name]
                else:
                    target = _fk_kwarg_name(model_class, field_name)
                    kwargs[target] = _coerce_field_value(
                        model_class, field_name, arguments[field_name])
        if hasattr(model_class, "created_by"):
            kwargs["created_by"] = user
        try:
            obj = model_class(**kwargs)
            if pre_clean is not None:
                pre_clean(obj)
            obj.full_clean()
            obj.save()
            # Set M2M fields after save
            for param_name, ids in m2m_values.items():
                m2m_attr = m2m_fields[param_name]
                getattr(obj, m2m_attr).set(ids)
            ts_status = _apply_timestamp_override(obj, model_class, arguments, user)
        except (ValidationError, Exception) as e:
            return _error(str(e))
        fields = [f.name for f in model_class._meta.fields]
        result = _serialize_obj(obj, fields)
        if ts_status == "ignored_no_permission":
            result["warning"] = (
                "created_at / updated_at were ignored: this account lacks the "
                "system.data_import.override_dates permission."
            )
        return result
    return handler


def _batch_create_handler(model_class, writable_fields, scope_filtered=True, m2m_fields=None,
                          pre_clean=None):
    """Create a generic batch create/upsert handler (non-atomic: partial success).

    When the caller supplies ``match_on`` (a list of writable field names), each
    item is first looked up by those fields: an existing match is UPDATED in
    place (idempotent re-import), otherwise a fresh object is CREATED. Without
    ``match_on`` every item is created (legacy behaviour). This lets a partially
    failed import be replayed without producing duplicates.
    """
    m2m_fields = m2m_fields or {}

    def _split_values(item_data):
        """Split a raw item into scalar/FK ``kwargs`` and deferred m2m values."""
        kwargs = {}
        m2m_values = {}
        for field_name in writable_fields:
            if field_name in item_data:
                if field_name in m2m_fields:
                    m2m_values[field_name] = item_data[field_name]
                else:
                    target = _fk_kwarg_name(model_class, field_name)
                    kwargs[target] = _coerce_field_value(
                        model_class, field_name, item_data[field_name])
        return kwargs, m2m_values

    def handler(user, arguments):
        items = arguments.get("items", [])
        if not isinstance(items, list) or not items:
            return _error("'items' must be a non-empty array of objects.")
        if len(items) > 500:
            return _error("Batch size limited to 500 items.")

        match_on = arguments.get("match_on") or []
        if match_on:
            if not isinstance(match_on, list) or not all(
                    isinstance(f, str) for f in match_on):
                return _error("'match_on' must be an array of field names.")
            unknown = [f for f in match_on if f not in writable_fields]
            if unknown:
                return _error(
                    "match_on fields must be writable fields; unknown: "
                    + ", ".join(unknown))
            if any(f in m2m_fields for f in match_on):
                return _error("match_on does not support many-to-many fields.")

        results = []
        created_count = 0
        updated_count = 0
        error_count = 0
        timestamps_ignored = 0
        for idx, item_data in enumerate(items):
            try:
                if not isinstance(item_data, dict):
                    raise ValidationError(
                        f"Expected an object, got {type(item_data).__name__}.")

                existing = None
                if match_on:
                    missing = [f for f in match_on if item_data.get(f) in (None, "")]
                    if missing:
                        raise ValidationError(
                            "Missing match_on value(s): " + ", ".join(missing))
                    lookup = {
                        _fk_kwarg_name(model_class, f): _coerce_field_value(
                            model_class, f, item_data[f])
                        for f in match_on
                    }
                    matches = list(model_class.objects.filter(**lookup)[:2])
                    if len(matches) > 1:
                        raise ValidationError(
                            "match_on matched multiple existing records; "
                            "use a more specific key.")
                    if matches:
                        existing = matches[0]
                        if scope_filtered and not _filter_by_scopes(
                                model_class.objects.filter(pk=existing.pk),
                                user).exists():
                            raise ValidationError(
                                "Matches a record outside your allowed scopes.")

                kwargs, m2m_values = _split_values(item_data)

                if existing is not None:
                    obj = existing
                    for target, value in kwargs.items():
                        setattr(obj, target, value)
                    if pre_clean is not None:
                        pre_clean(obj)
                    obj.full_clean()
                    obj.save()
                    for param_name, ids in m2m_values.items():
                        getattr(obj, m2m_fields[param_name]).set(ids)
                    ts_status = _apply_timestamp_override(obj, model_class, item_data, user)
                    entry = {
                        "index": idx,
                        "status": "updated",
                        "id": str(obj.pk),
                        "reference": getattr(obj, "reference", None),
                    }
                    if ts_status == "ignored_no_permission":
                        entry["timestamps"] = "ignored_no_permission"
                        timestamps_ignored += 1
                    results.append(entry)
                    updated_count += 1
                else:
                    if hasattr(model_class, "created_by"):
                        kwargs["created_by"] = user
                    obj = model_class(**kwargs)
                    if pre_clean is not None:
                        pre_clean(obj)
                    obj.full_clean()
                    obj.save()
                    for param_name, ids in m2m_values.items():
                        getattr(obj, m2m_fields[param_name]).set(ids)
                    ts_status = _apply_timestamp_override(obj, model_class, item_data, user)
                    entry = {
                        "index": idx,
                        "status": "created",
                        "id": str(obj.pk),
                        "reference": getattr(obj, "reference", None),
                    }
                    if ts_status == "ignored_no_permission":
                        entry["timestamps"] = "ignored_no_permission"
                        timestamps_ignored += 1
                    results.append(entry)
                    created_count += 1
            except (ValidationError, Exception) as e:
                results.append({
                    "index": idx,
                    "status": "error",
                    "errors": str(e),
                })
                error_count += 1
        summary = {
            "status": "completed" if error_count == 0 else "completed_with_errors",
            "total": len(items),
            "created": created_count,
            "updated": updated_count,
            "errors": error_count,
            "results": results,
        }
        if timestamps_ignored:
            summary["timestamps_ignored"] = timestamps_ignored
            summary["warning"] = (
                f"created_at / updated_at were ignored on {timestamps_ignored} "
                "item(s): this account lacks the system.data_import.override_dates "
                "permission."
            )
        return summary
    return handler


def _update_handler(model_class, writable_fields, scope_filtered=True, m2m_fields=None):
    """Create a generic update handler."""
    m2m_fields = m2m_fields or {}

    def handler(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if scope_filtered:
            qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
            if not qs.exists():
                return _error("Access denied: object is outside your allowed scopes.")
        changed_fields = set()
        m2m_values = {}
        for field_name in writable_fields:
            if field_name in arguments:
                if field_name in m2m_fields:
                    m2m_values[field_name] = arguments[field_name]
                    changed_fields.add(field_name)
                else:
                    target = _fk_kwarg_name(model_class, field_name)
                    setattr(obj, target, _coerce_field_value(
                        model_class, field_name, arguments[field_name]))
                    changed_fields.add(field_name)
        try:
            obj.full_clean()
            obj.save()
            # Set M2M fields after save
            for param_name, ids in m2m_values.items():
                m2m_attr = m2m_fields[param_name]
                getattr(obj, m2m_attr).set(ids)
        except (ValidationError, Exception) as e:
            return _error(str(e))
        fields = [f.name for f in model_class._meta.fields]
        return _serialize_obj(obj, fields)
    return handler


def _delete_handler(model_class, scope_filtered=True):
    """Create a generic delete handler."""
    def handler(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if scope_filtered:
            qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
            if not qs.exists():
                return _error("Access denied: object is outside your allowed scopes.")
        if getattr(obj, "is_deletable", True) is False:
            return _error(
                f"Cannot delete {model_class.__name__}: it is in the "
                f"'{getattr(obj, 'workflow_state', '')}' lifecycle state and is not deletable."
            )
        obj.delete()
        return {"deleted": True, "id": str(pk)}
    return handler


def _transition_handler(model_class, perm_namespace, scope_filtered=True):
    """Create a generic lifecycle transition handler.

    The required permission depends on the transition being performed (e.g.
    ``.update`` to submit, ``.approve`` to validate), so it is checked here via
    the workflow definition rather than at tool registration.
    """
    def handler(user, arguments):
        pk = arguments.get("id")
        target = arguments.get("target_state")
        comment = arguments.get("comment") or None
        if not pk:
            raise InvalidParamsError("id is required.")
        if not target:
            raise InvalidParamsError("target_state is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if scope_filtered:
            qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
            if not qs.exists():
                return _error("Access denied: object is outside your allowed scopes.")

        # transition_to runs the validation, application (incl. the per-transition
        # role / permission) and history through the lifecycle service.
        from core.lifecycle import LifecycleError

        current = obj.workflow_state
        try:
            obj.transition_to(target, user, comment=comment, enforce_permission=True)
        except LifecycleError as e:
            return _error(str(e))
        return {
            "id": str(pk),
            "previous_state": current,
            "workflow_state": obj.workflow_state,
        }
    return handler


def _allowed_transitions_handler(model_class, perm_namespace, scope_filtered=True):
    """Create a handler listing the lifecycle transitions the caller may perform."""
    def handler(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if scope_filtered:
            qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
            if not qs.exists():
                return _error("Access denied: object is outside your allowed scopes.")

        # List the steps the caller may move to from the current step (the
        # per-transition role / permission is resolved by available_transitions).
        lifecycle = obj.get_lifecycle()
        current = obj.workflow_state or lifecycle.initial_step.code
        transitions = obj.available_transitions(user=user)
        return {
            "id": str(pk),
            "workflow_state": current,
            "workflow": lifecycle.name,
            "allowed_transitions": [
                {
                    "target": t.target,
                    "verb": str(t.label),
                    "action": "update",
                    "requires_comment": t.requires_comment,
                }
                for t in transitions
            ],
        }
    return handler


def _history_handler(model_class, scope_filtered=True):
    """Create a handler returning an entity's unified change/transition timeline."""
    def handler(user, arguments):
        from core.history import (
            DEFAULT_HISTORY_LIMIT,
            MAX_HISTORY_LIMIT,
            build_timeline,
            extra_source_for,
        )

        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if scope_filtered:
            qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
            if not qs.exists():
                return _error("Access denied: object is outside your allowed scopes.")

        try:
            limit = int(arguments.get("limit", DEFAULT_HISTORY_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_HISTORY_LIMIT
        limit = max(1, min(limit, MAX_HISTORY_LIMIT))
        try:
            offset = max(0, int(arguments.get("offset", 0)))
        except (TypeError, ValueError):
            offset = 0

        entries = build_timeline(obj, limit=limit + offset, extra=extra_source_for(obj))
        page = entries[offset:offset + limit]
        return {
            "limit": limit,
            "offset": offset,
            "has_more": len(entries) > offset + limit,
            "results": [e.as_dict() for e in page],
        }
    return handler


# ── Schema helpers ─────────────────────────────────────────

def _list_schema(extra_props=None):
    props = {
        "search": {"type": "string", "description": "Text search query"},
        "limit": {"type": "integer", "description": "Max items to return (default 25, max 100)"},
        "offset": {"type": "integer", "description": "Offset for pagination"},
    }
    if extra_props:
        props.update(extra_props)
    return {"type": "object", "properties": props}


def _id_schema():
    return {
        "type": "object",
        "properties": {"id": {"type": "string", "description": "UUID of the object"}},
        "required": ["id"],
    }


def _obj_schema(properties, required=None):
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _html_field(label):
    """Return a field override dict indicating an HTML rich-text field."""
    return {"type": "string", "description": f"{label} (HTML rich text)"}


# Common override for entities that only have a description rich-text field.
_HTML_DESC = {"description": _html_field("Description")}


# ── Tool registration ──────────────────────────────────────

def register_all_tools(server):
    """Register all MCP tools on the given McpServer instance."""
    _register_help_tool(server)
    _register_context_tools(server)
    _register_assets_tools(server)
    _register_compliance_tools(server)
    _register_risks_tools(server)
    _register_incidents_tools(server)
    _register_accounts_tools(server)
    _register_reports_tools(server)
    _register_trust_center_tools(server)
    _register_assistant_tools(server)


# ── Assistant Tool ────────────────────────────────────────

def _register_assistant_tools(server):
    """Register the Ask Cairn natural-language assistant tool.

    No dedicated permission: the routing model reveals nothing by itself, and
    every data access inside the loop goes through the regular read tools,
    whose @require_perm decorators run with the calling user.
    """

    def ask_assistant(user, arguments):
        # Lazy imports: the assistant app is optional at runtime and must not
        # influence MCP registry import time.
        from assistant.engine import AssistantEngine
        from assistant.providers import AssistantError

        question = (arguments.get("question") or "").strip()
        if not question:
            return _error("question is required")
        language = arguments.get("language") or "en"
        try:
            outcome = AssistantEngine(user, language=language).ask(question)
        except AssistantError as exc:
            return _error(f"Assistant unavailable: {exc.__class__.__name__}")
        return outcome.as_dict()

    server.register_tool(
        "ask_assistant",
        "Ask Cairn's natural-language assistant a read-only question about GRC data "
        "(e.g. 'Which decisions were made at the last management review?'). Requires "
        "the optional AI assistant to be enabled (AI_ASSISTANT_ENABLED). The answer "
        "cites real records; data access enforces the caller's permissions.",
        {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Natural-language question"},
                "language": {"type": "string", "description": "ISO language code for the answer (default en)"},
            },
            "required": ["question"],
        },
        ask_assistant,
    )

    from assistant.models import AssistantFeedback

    feedback_list_handler = _list_handler(
        AssistantFeedback,
        ["id", "created_at", "user_id", "question", "language", "rating",
         "comment", "summary", "results", "degraded", "refused_tools",
         "provider", "model_name", "is_resolved"],
        search_fields=["question", "comment", "summary"],
        filters=["rating", "language", "provider", "user_id", "is_resolved"],
        scope_filtered=False,
    )

    def list_assistant_feedback(user, arguments):
        # Corrected feedback is excluded by default so an improvement LLM only
        # sees still-open items; pass include_resolved=true to see everything.
        args = dict(arguments or {})
        include = str(args.pop("include_resolved", "")).lower() in ("1", "true", "yes")
        if not include:
            args.setdefault("is_resolved", False)
        return feedback_list_handler(user, args)

    server.register_tool(
        "list_assistant_feedback",
        "List user feedback on Ask Cairn answers (thumbs up/down and optional "
        "comment), with the original question, language and the LLM response. "
        "Read-only; for quality analysis. Feedback already marked corrected is "
        "excluded unless include_resolved=true.",
        _list_schema({
            "rating": {"type": "string", "description": "Filter by rating: 'up' or 'down'"},
            "language": {"type": "string", "description": "Filter by interface language code"},
            "provider": {"type": "string", "description": "Filter by LLM provider"},
            "user_id": {"type": "string", "description": "Filter by user ID"},
            "include_resolved": {"type": "boolean", "description": "Include feedback already marked corrected (default false)"},
        }),
        require_perm("system.assistant_feedback.read")(list_assistant_feedback),
    )

    _register_semantic_requirement_tool(server)


SEMANTIC_REQUIREMENT_FIELDS = [
    "id", "reference", "requirement_number", "name",
    "compliance_status", "description", "guidance",
]


def _register_semantic_requirement_tool(server):
    """Meaning-based requirement search (embeddings + in-Python cosine)."""

    def semantic_search_requirements(user, arguments):
        from django.conf import settings

        if not settings.AI_ASSISTANT_SEMANTIC_ENABLED:
            return {"total": 0, "items": []}
        query = (arguments.get("query") or arguments.get("search") or "").strip()
        if not query:
            return {"total": 0, "items": []}
        limit = max(1, min(int(arguments.get("limit", 5) or 5), 20))

        from assistant.models import SemanticIndex
        from assistant.providers import AssistantError
        from assistant.semantic import embed_query, rank_object_ids
        from compliance.models import Requirement

        try:
            vector = embed_query(query)
        except AssistantError:
            return _error("Semantic search is unavailable.")
        if not vector:
            return {"total": 0, "items": []}
        ids = rank_object_ids(vector, SemanticIndex.REQUIREMENT, limit)
        by_id = {r.pk: r for r in Requirement.objects.filter(pk__in=ids)}
        ordered = [by_id[i] for i in ids if i in by_id]
        items = [_serialize_obj(r, SEMANTIC_REQUIREMENT_FIELDS) for r in ordered]
        return {"total": len(items), "items": items}

    server.register_tool(
        "semantic_search_requirements",
        "Find framework requirements / controls by MEANING using embeddings "
        "(language-agnostic). Use for conceptual / topic questions when an exact "
        "reference is not given. Read-only; requires the semantic index to be "
        "built (AI_ASSISTANT_SEMANTIC_ENABLED).",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic or concept to search for"},
                "limit": {"type": "integer", "description": "Max results (default 5, max 20)"},
            },
            "required": ["query"],
        },
        require_perm("compliance.requirement.read")(semantic_search_requirements),
    )


# ── Help Tool ─────────────────────────────────────────────

def _register_help_tool(server):
    """Register the MCP help tool that describes how to use the Cairn MCP server."""

    HELP_TEXT = """\
# Cairn MCP Server - Usage Guide

Cairn is a Governance, Risk & Compliance (GRC) platform. This MCP server
exposes its full API as tools organized by module.

Call `help` with a topic for detailed field-level documentation:
  context, assets, compliance, risks, incidents, batch, workflow, permissions, examples, users

## Modules

| Module | Prefix | Description |
|--------|--------|-------------|
| Context | context.* | Organizational context: scopes, issues, stakeholders, objectives, SWOT, roles, activities, sites, indicators |
| Assets | assets.* | Asset management: essential assets, support assets, dependencies, groups, suppliers |
| Compliance | compliance.* | Compliance: frameworks, sections, requirements, assessments, findings, action plans, mappings |
| Risks | risks.* | Risk management: criteria, assessments, risks, treatment plans, threats, vulnerabilities, ISO 27005 |
| Incidents | incidents.* | Incident management: security events, incidents, response plans, response actions, chronology, evidence and chain of custody, post-incident reviews, notification obligations and filings, personal data breaches, reporting authorities and obligation templates |
| Accounts | system.* | Users, groups, permissions, access logs, company settings |
| Reports | compliance.report.* | SOA and audit report generation |

## Tool Naming Convention

Every entity follows a consistent CRUD pattern:

| Operation | Tool pattern | Description |
|-----------|-------------|-------------|
| List | `list_{entity}s` | Paginated list. Params: search, limit (default 50), offset, plus entity-specific filters |
| Get | `get_{entity}` | Get one by ID. Param: id (UUID) |
| Create | `create_{entity}` | Create one. Returns the created object with all fields |
| Batch Create / Upsert | `batch_create_{entity}s` | Create or upsert up to 500 items. Params: items (array); optional match_on (field names) to update-on-match instead of duplicating. Non-atomic: valid items are applied even if others fail |
| Update | `update_{entity}` | Update by ID. Param: id + only the fields to change (partial update) |
| Delete | `delete_{entity}` | Delete by ID. Param: id |
| Transition | `transition_{entity}` | Move to a lifecycle step. Params: id, target_state, optional comment |

## Key Concepts

### UUIDs
All domain objects use UUID primary keys (e.g. "550e8400-e29b-41d4-a716-446655440000").
Foreign key fields expect UUID strings.
Exception: SupplierType uses integer auto-increment IDs.

### Scopes
Scopes represent organizational boundaries (departments, subsidiaries, projects).
Most entities have a `scopes` M2M field (array of scope UUIDs).
Users only see objects within their assigned scopes (unless superuser).
Always pass scopes when creating scoped entities, or they will be invisible to non-superusers.

### Lifecycle
Each entity moves through a lifecycle of steps (e.g. draft -> pending -> validated
-> archived). Use `transition_{entity}(id, target_state)` to move it; the move is
validated against the entity's lifecycle (legal step, required permission /
mandatory comment). `{entity}_allowed_transitions(id)` lists the legal next steps.

### References
Most entities auto-generate a unique reference on creation (e.g. RISK-1, REQT-42, SUPP-3).
References are read-only and sequential. Reference prefixes by entity:
  Scope=SCOP, Issue=ISSU, Stakeholder=STKH, Objective=OBJT, SwotAnalysis=SWOT,
  Role=ROLE, Activity=ACTV, Site=SITE, Indicator=INDI,
  EssentialAsset=EAST, SupportAsset=SAST, AssetDependency=ADEP, AssetGroup=AGRP,
  Supplier=SUPP, SupplierType=SPTY, SupplierDependency=SDEP,
  SupplierSubprocessor=SSPR, Contract=CTRT,
  Certificate=CERT,
  SiteAssetDependency=SADP, SiteSupplierDependency=SSDP,
  Framework=FRMW, Section=SECT, Requirement=REQT, ComplianceAssessment=CASS,
  Finding=(NCMAJ/NCMIN/OBS/OA/STR per type), ActionPlan=ACTPL,
  RiskCriteria=RCRT, RiskAssessment=RASS, Risk=RISK,
  RiskTreatmentPlan=RTPL, Threat=THRT, Vulnerability=VULN, ISO27005Risk=I27R,
  Incident=INCD, SecurityEvent=EVNT, IncidentResponsePlan=IRPL,
  IncidentResponseAction=IRAC, IncidentEvidence=EVID, PostIncidentReview=PIRV,
  IncidentNotification=INOT, NotificationFiling=NFIL, ReportingAuthority=RGAU,
  ReportingObligationTemplate=ROBT, PersonalDataBreach=PDBR
Read INCD twice: it is one letter-order away from the Indicator prefix, and the
two are visually confusable in a reference string and in a list column.
IncidentTimelineEntry and EvidenceCustodyEvent generate no reference at all.

### HTML Rich Text Fields
Fields marked "(HTML)" accept HTML rich text content.
Use standard HTML tags: <p>, <ul>, <li>, <strong>, <em>, <a>, <table>, <h3>, etc.

## Error Handling

- Permission denied: {"error": "Permission denied: <codename>"}
- Not found: {"error": "<Entity> not found."}
- Validation error: {"error": "<field details>"}
- All errors set isError: true in the response
"""

    TOPIC_CONTEXT = """\
# Context Module - Field Reference

## scope
Writable: name (required), description (HTML), type, status, effective_date, review_date, manager_ids
- type: draft | active | archived
- status: draft | active | archived
- manager_ids: array of user UUIDs (M2M, scope managers get automatic access)
- effective_date / review_date: ISO 8601 date (e.g. "2025-12-31")
Filters: type, status

## issue
Writable: name (required), description (HTML), type, category, impact_level, priority, status, owner_id, review_date, scopes
- type: internal | external
- category (internal): strategic | organizational | human_resources | technical | financial | cultural
- category (external): political | economic | social | technological | legal | environmental | competitive | regulatory
- impact_level: low | medium | high | critical
- priority: low | medium | high | critical
- status: identified | active | monitored | closed
Filters: type, category, priority, status

## stakeholder
Writable: name (required), type (required), category (required), description, contact_name, contact_email, contact_phone, influence_level (required), interest_level (required), status, review_date, scopes
- type: internal | external
- category: executive_management | employees | customers | suppliers | partners | regulators | shareholders | insurers | public | competitors | unions | auditors | other
- influence_level: low | medium | high
- interest_level: low | medium | high
- status: active | inactive
Filters: type, category, influence_level, interest_level, status

## expectation (nested under stakeholder)
Writable: stakeholder_id (required), name (required), description, type, priority
- type: requirement | expectation | need
- priority: low | medium | high | critical
Filters: stakeholder_id, type, priority

## objective
Writable: name (required), description (HTML), type, category, priority, status, target_date, owner_id, linked_issues, scopes
- type: security | compliance | business | other
- category: confidentiality | integrity | availability | compliance | operational | strategic
- priority: low | medium | high | critical
- status: draft | active | achieved | not_achieved | cancelled
- linked_issues: array of issue UUIDs (M2M)
Filters: type, priority, status

## swot_analysis
Writable: name (required), description (HTML), scope_id, status, scopes
- status: draft | validated | archived
Filters: status

## swot_item
Writable: analysis_id (required), category (required), description (required), priority
- category: strength | weakness | opportunity | threat
- priority: low | medium | high | critical
Filters: analysis_id, category, priority

## swot_strategy
Writable: analysis_id (required), strategy_type (required), name (required), description (HTML), priority, status, target_date, owner_id, linked_items
- strategy_type: so | st | wo | wt (Strengths-Opportunities, Strengths-Threats, Weaknesses-Opportunities, Weaknesses-Threats)
- priority: low | medium | high | critical
- status: draft | active | archived
- linked_items: array of swot_item UUIDs (M2M)
Filters: analysis_id, strategy_type, priority, status

## role
Writable: name (required), description (HTML), type, status, holder_id, scopes
- type: governance | operational | support | control
- status: active | inactive
- holder_id: UUID of the user holding this role
Filters: type, status

## responsibility (nested under role)
Writable: role_id (required), name (required), description, raci_type
- raci_type: responsible | accountable | consulted | informed
Filters: role_id

## activity
Writable: name (required), description (HTML), type, status, owner_id, scopes
- type: core_business | support | management
- status: active | inactive | planned
Filters: type, status, owner_id

## site
Writable: name (required), description (HTML), type, status, address, city, country, latitude, longitude, scopes
- type: siege | bureau | usine | entrepot | datacenter | site_distant | autre
- status: draft | active | archived
Filters: type, status, country

## indicator
Writable: name (required), description (HTML), type, format, unit, frequency, collection_method, target_value, critical_threshold, critical_threshold_operator, status, objective_id, scopes
- type: organizational | technical
- format: number | boolean
- frequency: daily | weekly | monthly | quarterly | semi_annual | annual
- collection_method: manual | api | internal
- critical_threshold_operator: below | above | is_false | is_true
- status: active | inactive | draft
Filters: type, frequency, status, objective_id

## indicator_measurement
Writable: indicator_id (required), value (required), measured_at, measured_by_id, comment
Filters: indicator_id

## tag
Only 3 tools: list_tags, create_tag(name, color), delete_tag(id)
"""

    TOPIC_ASSETS = """\
# Assets Module - Field Reference

## essential_asset
Writable: name (required), description (HTML), type (required), category, owner_id (required), custodian_id,
  confidentiality_level, integrity_level, availability_level,
  confidentiality_justification, integrity_justification, availability_justification,
  max_tolerable_downtime, recovery_time_objective, recovery_point_objective,
  data_classification, personal_data, personal_data_categories, regulatory_constraints,
  related_activities, status, review_date, tags, scopes
- type: business_process | information
- category (process): core_process | support_process | management_process
- category (info): strategic_data | operational_data | personal_data | financial_data | technical_data | legal_data | research_data | commercial_data
- confidentiality/integrity/availability_level: integer 0-4 OR text: negligible | low | medium | high | critical
- data_classification: public | internal | confidential | restricted | secret
- personal_data: boolean
- status: identified | active | under_review | decommissioned
- tags: array of tag UUIDs (M2M)
Filters: type, category, status, owner_id, data_classification, personal_data
Ref prefix: EAST

## support_asset
Writable: name (required), description (HTML), type (required), category, owner_id (required), custodian_id,
  location, manufacturer, model_name, serial_number, software_version,
  ip_address, hostname, operating_system,
  acquisition_date, end_of_life_date, warranty_expiry_date, contract_reference,
  exposure_level, environment, parent_asset_id, status, review_date, tags, scopes
- type: hardware | software | network | person | service | paper
- category (hardware): server | workstation | laptop | mobile_device | network_equipment | storage | peripheral | iot_device | removable_media | other_hardware
- category (software): operating_system | database | application | middleware | security_tool | development_tool | saas_application | other_software
- category (network): lan | wan | wifi | vpn | internet_link | firewall_zone | dmz | other_network
- category (person): internal_staff | contractor | external_provider | administrator | developer | other_person
- category (service): cloud_service | hosting_service | managed_service | telecom_service | outsourced_service | other_service
- category (paper): archive | printed_document | form | other_paper
- Physical locations are modelled as `context.Site` (use create_site / list_sites). The `site` type was removed from SupportAsset; existing rows were converted to Site by migration assets.0029.
- exposure_level: internal | exposed | internet_facing | dmz
- environment: production | staging | development | test | disaster_recovery
- status: in_stock | deployed | active | under_maintenance | decommissioned | disposed
Read-only computed: inherited_confidentiality, inherited_integrity, inherited_availability (inherited from essential assets via dependencies)
Filters: type, category, status, environment, exposure_level, owner_id
Ref prefix: SAST

## asset_dependency
Links an essential asset to a support asset.
Writable: essential_asset_id (required), support_asset_id (required), dependency_type (required), criticality (required), description (HTML)
- dependency_type: runs_on | stored_in | transmitted_by | managed_by | hosted_at | protected_by | other
- criticality: low | medium | high | critical
Read-only: is_single_point_of_failure (auto-detected), redundancy_level
Filters: essential_asset_id, support_asset_id, dependency_type, criticality
Ref prefix: ADEP

## asset_valuation
DIC valuation record for an essential asset.
Writable: essential_asset_id (required), evaluation_date, confidentiality_level (0-4), integrity_level (0-4), availability_level (0-4), justification, context
Creating a valuation automatically updates the essential asset's DIC levels.
Filters: essential_asset_id

## asset_group
Writable: name (required), description, type, members (array of support_asset UUIDs), owner_id, status, tags, scopes
- type: hardware | software | network | person | service | paper
- status: active | inactive
Filters: type, status, owner_id
Ref prefix: AGRP

## supplier
Writable: name (required), description (HTML), type, criticality, parent_company_id, owner_id (required),
  contact_name, contact_email, contact_phone, website, address, country, latitude, longitude,
  contract_reference, contract_start_date, contract_end_date, status, notes (HTML), tags, scopes
- type: INTEGER (SupplierType ID, NOT a UUID). Use list_supplier_types to get valid IDs.
- parent_company_id: UUID of another supplier this one is a subsidiary (filiale) of.
- criticality: low | medium | high | critical
- status: active | under_evaluation | suspended | archived
Special tools: update_supplier_logo(id, image_url) - fetches and stores logo from URL
Filters: type, criticality, status, owner_id, country
Ref prefix: SUPP

## supplier_type
Writable: name (required), description
Ref prefix: SPTY (integer PK, not UUID)

## supplier_dependency
Links a support asset to a supplier.
Writable: support_asset_id (required), supplier_id (required), dependency_type (required), criticality (required), description (HTML), redundancy_level
Read-only: is_single_point_of_failure (auto-detected by the SPOF detection service).
- dependency_type: provides | hosts | manages | develops | supports | licenses | maintains | other
- criticality: low | medium | high | critical
- redundancy_level: none | partial | full
Filters: support_asset_id, supplier_id, dependency_type, criticality
Ref prefix: SDEP

## supplier_subprocessor
Links a supplier (délégataire) to another supplier engaged as its sub-processor (sous-délégataire). Models the supply-chain / GDPR Art. 28 sub-processing chain.
Writable: supplier_id (required), subprocessor_id (required, must differ from supplier_id), purpose, criticality, status, start_date, end_date, description (HTML)
- criticality: low | medium | high | critical
- status: active | suspended | terminated
Filters: supplier_id, subprocessor_id, criticality, status
Ref prefix: SSPR

## site_asset_dependency
Links a site to a support asset.
Writable: support_asset_id (required), site_id (required), dependency_type (required), criticality (required), description (HTML), redundancy_level
Read-only: is_single_point_of_failure (auto-detected by the SPOF detection service).
- dependency_type: located_at | hosted_at | deployed_at | other
- criticality: low | medium | high | critical
- redundancy_level: none | partial | full
Filters: support_asset_id, site_id, dependency_type, criticality
Ref prefix: SADP

## site_supplier_dependency
Links a site to a supplier.
Writable: site_id (required), supplier_id (required), dependency_type (required), criticality (required), description (HTML), redundancy_level
Read-only: is_single_point_of_failure (auto-detected by the SPOF detection service).
- dependency_type: provides | hosts | manages | develops | supports | licenses | maintains | other
- criticality: low | medium | high | critical
- redundancy_level: none | partial | full
Filters: site_id, supplier_id, dependency_type, criticality
Ref prefix: SSDP

## supplier_requirement
Writable: supplier_id (required), title (required), description, requirement_id (FK to compliance requirement, optional), compliance_status, evidence, due_date
- compliance_status: not_assessed | compliant | partially_compliant | non_compliant
Filters: supplier_id, compliance_status

## supplier_requirement_review
Writable: supplier_requirement_id (required), review_date, reviewer_id, result, comment, evidence_file
- result: not_assessed | compliant | partially_compliant | non_compliant
Filters: supplier_requirement_id, result

## supplier_contact
Writable: supplier_id (required), name (required), profession, service, email, phone, role
Filters: supplier_id, role
"""

    TOPIC_COMPLIANCE = """\
# Compliance Module - Field Reference

## framework
Writable: name (required), short_name, description (HTML), type, category, version_label, source_url, publication_date, effective_date, owner_id, status, scopes, is_mandatory (bool), is_applicable (bool), applicability_justification, applicability_managed_by_risks (bool)
- type: standard | law | regulation | contract | internal_policy | industry_framework | other
- category: information_security | privacy | risk_management | business_continuity | cloud_security | sector_specific | it_governance | quality | contractual | internal | other
- status: draft | active | under_review | deprecated | archived
- applicability_managed_by_risks: when true, each requirement's is_applicable is derived automatically from its linked risks (applicable iff at least one active risk is linked); the requirement applicability fields become read-only.
Filters: type, category, status, is_mandatory, is_applicable, applicability_managed_by_risks
Ref prefix: FRMW

## section
Writable: framework_id (required), name (required), description, order (integer for sorting), parent_section_id (UUID for nesting)
Sections form a tree: use parent_section_id to nest (e.g. "A.5" under "A").
Filters: framework_id, parent_section_id
Ref prefix: SECT

## requirement
Writable: framework_id (required), section_id, requirement_number, name (required), description (HTML, required), guidance (HTML),
  type, category, is_applicable (bool), applicability_justification,
  compliance_status, compliance_level (0-100), compliance_evidence (HTML), compliance_finding (HTML),
  (is_applicable / applicability_justification are read-only and auto-derived when the framework has applicability_managed_by_risks enabled),
  owner_id, priority, target_date, linked_assets (M2M), linked_stakeholder_expectations (M2M), linked_risks (M2M, required - pass [] if none),
  status, tags
- type: mandatory | recommended | optional
- category: organizational | technical | physical | legal | human | other
- compliance_status: not_assessed | evaluated | non_compliant | partially_compliant | major_non_conformity | minor_non_conformity | observation | improvement_opportunity | compliant | strength | not_applicable
- priority: low | medium | high | critical
- status: active | deprecated | superseded
Filters: framework_id, section_id, type, compliance_status, priority, is_applicable
Ref prefix: REQT

## requirement_mapping
Maps requirements across frameworks.
Writable: source_requirement_id (required), target_requirement_id (required), mapping_type (required), coverage_level, notes
- mapping_type: equivalent | partial_overlap | includes | included_by | related
- coverage_level: full | partial | minimal
Filters: source_requirement_id, target_requirement_id, mapping_type

## compliance_assessment (custom CRUD)
Writable: name (required), description (HTML), limitations (HTML), assessment_start_date, assessment_end_date, status, assessor_id, framework_ids (array of framework UUIDs)
- status: draft | planned | in_progress | completed | closed | cancelled
- framework_ids: when set, assessment_results are auto-created for all requirements in those frameworks
Read-only computed: overall_compliance_level, total_requirements, compliant_count, major_non_conformity_count, minor_non_conformity_count, observation_count, improvement_opportunity_count, strength_count, not_applicable_count

Assessment status transitions:
  draft -> planned -> in_progress -> completed -> closed
  draft -> cancelled
  planned -> cancelled
  (completed and closed are terminal - cannot go back)

## assessment_result (custom CRUD)
Writable: assessment_id (required), requirement_id (required), compliance_status, compliance_level (0-100), finding (HTML), auditor_recommendations (HTML), evidence (HTML), assessed_by_id, assessed_at
- compliance_status: same 11-value enum as Requirement.compliance_status: not_assessed | evaluated | non_compliant | partially_compliant | major_non_conformity | minor_non_conformity | observation | improvement_opportunity | compliant | strength | not_applicable. Audit statuses map onto the conformance averages via the table in docs/specs/m3-compliance/requirement.md.
Updating a result auto-recalculates the assessment's aggregate counts.

## finding (custom CRUD)
Writable: assessment_id (required), finding_type (required), description (HTML, required), evidence (HTML), recommendation (HTML), assessor_id, requirement_ids (M2M array)
- finding_type: major_nc | minor_nc | observation | improvement | strength
Reference auto-generated per type: NCMAJ-x, NCMIN-x, OBS-x, OA-x, STR-x
Creating/updating/deleting findings auto-applies to linked assessment_results.

## action_plan
Writable: name (required), description (HTML), gap_description (HTML), remediation_plan (HTML), priority, target_date, progress_percentage (0-100), owner_id, assignees (M2M user UUIDs), requirements (M2M requirement UUIDs)
- priority: low | medium | high | critical
- status is READ-ONLY - use action_plan_transition tool to change it (see help topic "workflow")
Filters: status, priority, owner_id, requirement_id
Ref prefix: ACTPL

## Special compliance tools
- get_framework_compliance_summary(framework_id) - returns per-section compliance stats
- generate_soa_report(framework_id, title) - Statement of Applicability PDF
- generate_audit_report(assessment_id, title) - Audit report PDF
- list_reports / delete_report(id) - manage generated reports
"""

    TOPIC_RISKS = """\
# Risks Module - Field Reference

## risk_criteria
Defines evaluation scales (likelihood/impact) and risk level thresholds.
Writable: name (required), description (HTML), methodology, status, scopes
- methodology: iso27005 | ebios_rm
- status: draft | active | archived
After creating criteria, add scale_levels and risk_levels.
Filters: status
Ref prefix: RCRT

## scale_level
Writable: criteria_id (required), scale_type (required), level (required, integer 1-5), name (required), description, color
- scale_type: likelihood | impact
Example: create 5 likelihood levels (1=Very Low to 5=Very High) and 5 impact levels.
Filters: criteria_id

## risk_level
Writable: criteria_id (required), level (required, integer), name (required), color (hex, e.g. "#ff0000"), min_score, max_score, treatment_required (bool), description
Example: level 1 "Low" (green, min=1 max=5), level 4 "Critical" (red, min=16 max=25)
Filters: criteria_id

## risk_assessment
Writable: name (required), description (HTML), risk_criteria_id, methodology, assessment_date, assessor_id, status, scopes
- methodology: iso27005 | ebios_rm
- status: draft | in_progress | completed | validated | archived
Filters: status, assessor_id, risk_criteria_id
Ref prefix: RASS

## risk
Writable: name (required), description (HTML), assessment_id (required),
  status, priority, treatment_decision, risk_source_type,
  initial_likelihood (int), initial_impact (int),
  current_likelihood (int), current_impact (int),
  residual_likelihood (int), residual_impact (int),
  risk_owner_id, justification (HTML)
- status: identified | analyzed | evaluated | treatment_planned | treatment_in_progress | treated | accepted | closed | monitoring
- priority: low | medium | high | critical
- treatment_decision: accept | mitigate | transfer | avoid | not_decided
- risk_source_type: iso27005_analysis | ebios_strategic | ebios_operational | incident | audit | compliance | manual
- likelihood/impact values: integers matching scale_level.level (typically 1-5)
Read-only computed: current_risk_level (from criteria matrix)
Filters: assessment_id, status, treatment_decision, priority, risk_owner_id
Ref prefix: RISK

## risk_treatment_plan
Writable: name (required), description (HTML), risk_id (required), owner_id, target_date, status, progress_percentage (0-100), expected_residual_likelihood (int), expected_residual_impact (int)
- status: planned | in_progress | completed | cancelled | overdue
After creating, add treatment_actions.
Filters: risk_id, status, owner_id
Ref prefix: RTPL

## treatment_action
Writable: treatment_plan_id (required), name (required), description (HTML), responsible_id (user UUID), due_date, status, completion_date
- status: planned | in_progress | completed | cancelled
Filters: treatment_plan_id, status

## risk_acceptance
Writable: risk_id (required), accepted_by_id (required), justification (HTML), conditions, valid_until (date), status
- status: active | expired | revoked | renewed
Filters: risk_id, status, accepted_by_id

## threat
Writable: name (required), description (HTML), type, source, category, status, scopes
- type: deliberate | accidental | environmental | other
- source: human_internal | human_external | natural | technical | other
- category: malware | social_engineering | unauthorized_access | denial_of_service | data_breach | physical_attack | espionage | fraud | sabotage | human_error | system_failure | network_failure | power_failure | natural_disaster | fire | water_damage | theft | vandalism | supply_chain | insider_threat | ransomware | apt
- status: active | inactive
Filters: type, source, status
Ref prefix: THRT

## vulnerability
Writable: name (required), description (HTML), category, severity, affected_asset_types (array), affected_assets (M2M support_asset UUIDs), cve_references, remediation_guidance (HTML), is_from_catalog (bool), status, tags, scopes
- category: configuration_weakness | missing_patch | design_flaw | coding_error | weak_authentication | insufficient_logging | lack_of_encryption | physical_vulnerability | organizational_weakness | human_factor | obsolescence | insufficient_backup | network_exposure | third_party_dependency
- severity: low | medium | high | critical
- status: identified | confirmed | mitigated | accepted | closed
Filters: category, severity, status
Ref prefix: VULN

## iso27005_risk
Combines threat + vulnerability + impact for ISO 27005 analysis.
Writable: assessment_id (required), threat_id (required), vulnerability_id (required),
  threat_likelihood (int 1-5), vulnerability_exposure (int 1-5),
  impact_confidentiality (int 1-5), impact_integrity (int 1-5), impact_availability (int 1-5),
  existing_controls (HTML), risk_id (optional, link to a Risk entity), description (HTML)
Read-only computed:
  combined_likelihood = max(threat_likelihood, vulnerability_exposure)
  max_impact = max(impact_confidentiality, impact_integrity, impact_availability)
  risk_level = combined_likelihood * max_impact (mapped to risk_level thresholds)
Filters: assessment_id, threat_id, vulnerability_id
Ref prefix: I27R

## Risk-Requirement linking tools
- list_risk_requirements(risk_id) - list requirements linked to a risk
- list_requirement_risks(requirement_id) - list risks linked to a requirement
- link_risk_requirements(risk_id, requirement_ids) - add links (additive)
- unlink_risk_requirements(risk_id, requirement_ids) - remove links
- set_risk_requirements(risk_id, requirement_ids) - replace all links
"""

    TOPIC_INCIDENTS = """\
# Incidents Module - Field Reference

Six permission features govern this module, and there is no seventh:
incidents.incident, incidents.event, incidents.response_plan,
incidents.evidence, incidents.notification, incidents.review. Each carries
create / read / update / delete plus validate (incident, event, review) or
approve (response_plan, evidence, notification).

Three rules cut across every entity here:
- Phase timestamps are stamped by lifecycle transitions and are never writable:
  declared_at, triaged_at, contained_at, eradicated_at, recovered_at, closed_at
  (incident), assessed_at and triage_decision (security event), sealed_at,
  last_integrity_check_at / _ok (evidence), decided_at, sent_at,
  first_submitted_at, late_by (notification), qualified_at (breach),
  held_at and effectiveness_reviewed_at (review). A decision is a transition,
  never a field write: use transition_{entity}(id, target_state, comment).
- Three ledgers are append-only and have no update and no delete tool:
  incident_timeline_entry, evidence_custody_event, notification_filing.
- Binary payloads are neither readable nor writable through MCP: the evidence
  artefact itself and the stored proof-of-filing bytes.

## incident
Writable: title (required), summary, description, category, severity, detection_source,
  is_exercise, tlp, confidentiality_impact, integrity_impact, availability_impact,
  personal_data_involved, occurred_at, detected_at (required), awareness_at,
  awareness_justification, outage_duration, estimated_cost, no_obligation_justification,
  is_significant, significance_determined_at, significance_justification,
  cross_border_impact, cross_border_justification, suspected_malicious,
  suspected_malicious_justification, response_plan_id, reporter_id,
  incident_manager_id, parent_incident_id, origin_supplier_id, scope_ids,
  affected_supplier_ids, affected_essential_asset_ids, affected_support_asset_ids,
  affected_site_ids, affected_activity_ids, threat_ids,
  exploited_vulnerability_ids, realised_risk_ids, linked_requirement_ids
- category: malware | social_engineering | unauthorized_access | denial_of_service | data_breach | physical_attack | espionage | fraud | sabotage | human_error | system_failure | network_failure | power_failure | natural_disaster | fire | water_damage | theft | vandalism | supply_chain | insider_threat | ransomware | apt | other
- severity: low | medium | high | critical
- detection_source: internal_monitoring | soc_alert | employee_report | customer_report | supplier_notification | authority_notification | researcher | audit | penetration_test | threat_intel | other
- tlp: clear | green | amber | amber_strict | red
- detected_at is the technical clock (mean-time-to-detect); awareness_at is the
  legal clock (GDPR Art. 33(1), NIS2 Art. 23) and defaults to detected_at. A gap
  between the two must carry awareness_justification.
- A cross_border_impact or suspected_malicious verdict must carry its justification.
Read-only: initial_severity (fixed at triage), the six phase timestamps,
  awareness_gap, time_to_contain, time_to_recover, severity_raised_since_triage
Filters: category, severity, detection_source, tlp, is_exercise, personal_data_involved, is_significant, workflow_state, incident_manager_id, response_plan_id, parent_incident_id
Ref prefix: INCD

## security_event
The A.6.8 register: what was observed, before anyone decided what it is.
Writable: title (required), description, event_class, category, detection_source,
  source_reference, occurred_at, detected_at (required), reported_at (required),
  is_anonymous, reporter_id, reporter_label, reported_by_supplier_id,
  duplicate_of_id, assessed_by_id, assessment_notes, scope_ids,
  affected_support_asset_ids, affected_essential_asset_ids, affected_site_ids
- event_class: event | weakness | incident (governs which promotion targets are legal)
- category: same threat taxonomy as incident.category
- detection_source: same list as incident.detection_source
- reporter_label carries an external or non-user reporter; is_anonymous marks the
  anonymous channel A.6.8 requires.
Read-only: triage_decision, assessed_at, incident_id, vulnerability_id (all set
  by the triage transitions), reporting_delay_hours
Special tool: declare_incident_from_event(id, comment, ...) - promotes an event
  under assessment into a new incident as one atomic act. Never create the
  incident and update the event separately.
Filters: event_class, category, detection_source, is_anonymous, triage_decision, workflow_state, incident_id, reported_by_supplier_id
Ref prefix: EVNT

## incident_response_plan
Writable: name (required), purpose, procedure (HTML), classification_scale (HTML),
  escalation_matrix (HTML), reporting_channels (HTML), evidence_procedure (HTML),
  lessons_learned_procedure (HTML), applicable_regimes, owner_id, approved_by_id,
  approved_at, effective_from, review_date, scope_ids, responsible_role_ids,
  linked_requirement_ids
- applicable_regimes: array of regime codes (see the notification regime list below)
Read-only: last_exercise_date, is_in_force, is_review_overdue, is_exercise_overdue
Filters: workflow_state, owner_id, approved_by_id
Ref prefix: IRPL

## incident_response_action
Operational step under an incident. Runs no lifecycle, so there is no
transition_incident_response_action tool: status is a plain column.
Writable: incident_id (required), action_type (required), title (required),
  description, status, owner_id, performed_by_id, due_at, started_at,
  completed_at, outcome, effectiveness
- action_type: containment | eradication | recovery | evidence_collection | communication | escalation | workaround | other
- status: planned | in_progress | done | blocked | cancelled
- effectiveness: effective | partially_effective | not_effective
Filters: incident_id, action_type, status, owner_id, performed_by_id, effectiveness
Ref prefix: IRAC

## incident_timeline_entry
The incident chronology. APPEND-ONLY: create and read tools only, no update and
no delete. Correct a mistake by appending an entry of type correction that names
superseded_entry_id and states correction_reason.
Tools: create_incident_timeline_entry, list_incident_timeline_entries,
  get_incident_timeline_entry, get_incident_timeline_entry_history
Writable at create: incident_id (required), occurred_at (required),
  summary (required, max 500 chars), detail, entry_type, is_evidence,
  related_action_id, related_evidence_id, superseded_entry_id, correction_reason
- entry_type: observation | action | decision | communication | escalation | evidence | external_input | correction | system
- author is always the calling account; source is always manual; recorded_at is
  stamped on insert. occurred_at may be backdated: the chronology reads in the
  order things happened.
Permission: incidents.incident.update to append, incidents.incident.read to list.
Filters: incident_id, entry_type, source, is_evidence, author_id
No reference prefix: entries are identified by UUID.

## incident_evidence
A.5.28 artefact register. Scoped through its incident (incident__scopes).
Writable: incident_id (required), title (required), evidence_type (required),
  description, tlp, collected_at, collected_by_id, collection_method,
  source_support_asset_id, source_description, content_hash, hash_algorithm,
  original_filename, file_size, storage_location, legal_hold, retention_until,
  admissibility_notes
- evidence_type: disk_image | memory_dump | log_extract | network_capture | screenshot | email | document | database_export | malware_sample | physical_device | witness_statement | other
- hash_algorithm: sha256 | sha512 | sha1 | md5
- tlp: clear | green | amber | amber_strict | red (defaults to red)
- The acquisition metadata (content_hash, hash_algorithm, collected_at,
  collected_by, collection_method and the artefact itself) is FROZEN once the
  item is sealed: an update naming any of them is refused, field by field.
- The artefact bytes are never uploaded or downloaded through MCP. An item above
  the deployment's inline cap is registered by reference: leave the file empty,
  record storage_location, file_size and content_hash.
Read-only: sealed_at, last_integrity_check_at, last_integrity_check_ok,
  destruction_authorised_by, has_file, is_registered_by_reference, is_sealed,
  retention_expired, is_destroyable
Special tool: verify_evidence_integrity(id, notes) - measures the artefact and
  appends the verdict to the custody ledger. Three outcomes, never collapsed:
  match | mismatch | not_verifiable. Never assert a verdict by writing content_hash.
Filters: incident_id, evidence_type, hash_algorithm, tlp, legal_hold, workflow_state, collected_by_id
Ref prefix: EVID

## evidence_custody_event
The chain of custody. APPEND-ONLY: create and read tools only, no update and no
delete. Correct a mistake by appending a further act that says what the earlier
one got wrong.
Tools: create_evidence_custody_event, list_evidence_custody_events,
  get_evidence_custody_event, get_evidence_custody_event_history
Writable at create: evidence_id (required), action (required),
  occurred_at (required), counterparty, counterparty_organisation, location,
  hash_at_event, notes
- action: collected | sealed | transferred | accessed | copied | analysed | integrity_verified | released | returned | destroyed
- transferred, released, returned and destroyed each require a named
  counterparty: a handover to an organisation with no named individual is not a
  handover.
- actor is always the calling account; source is always manual on an
  MCP-created row (the lifecycle appends its own rows with source lifecycle).
Permission: incidents.evidence.update to append, incidents.evidence.read to list.
Filters: evidence_id, action, source, integrity_ok, actor_id
No reference prefix: rows are identified by UUID.

## post_incident_review
Writable: incident_id (required, one review per incident), response_plan_id,
  scheduled_date, facilitator_id, root_cause_method, root_cause,
  contributing_factors, detection_gap, containment_assessment, what_went_well,
  what_failed, recurrence_likelihood, similar_incidents_checked,
  risk_reassessment_required, response_plan_update_required, training_required,
  effectiveness_review_date, effectiveness_verdict, effectiveness_reviewed_by_id,
  effectiveness_notes, participant_ids, raised_finding_ids,
  corrective_action_plan_ids, failed_control_ids, control_to_strengthen_ids,
  identified_risk_ids, identified_vulnerability_ids, isms_change_ids
- root_cause_method: five_whys | ishikawa | fault_tree | timeline_analysis | barrier_analysis | other
- recurrence_likelihood: low | medium | high | critical
- effectiveness_verdict: effective | partially_effective | not_effective
Read-only: held_at, effectiveness_reviewed_at, is_effectiveness_overdue, scopes
  (kept aligned with the reviewed incident, never set directly)
Filters: incident_id, root_cause_method, recurrence_likelihood, effectiveness_verdict, workflow_state, facilitator_id
Ref prefix: PIRV

## incident_notification
One regulatory or contractual duty owed for one incident. Scoped through its
incident (incident__scopes).
Writable: incident_id (required), regime (required), recipient_kind (required),
  authority_id, recipient_stakeholder_id, recipient_supplier_id, recipient_name,
  obligation_reference, content_requirements, clock_anchor, deadline_hours,
  no_fixed_deadline, depends_on_id, channel, content, decision_rationale,
  acknowledgement_reference, acknowledged_at, proof_evidence_id
- regime: gdpr_art33_authority | gdpr_art34_data_subject | gdpr_art33_2_controller | nis2_early_warning | nis2_notification | nis2_intermediate | nis2_final | nis2_recipients | dora_initial | dora_intermediate | dora_final | eprivacy | cra | sector_regulator | law_enforcement | cert_csirt | contractual_customer | contractual_supplier | insurer | internal_management | public_communication | other
- recipient_kind: supervisory_authority | csirt | competent_authority | financial_regulator | law_enforcement | data_subject | customer | controller | supplier | insurer | internal | public
- clock_anchor: occurred_at | detected_at | awareness_at | significance_determined_at | previous_stage
- channel: portal | email | postal | phone | api | in_person | public_notice
- The decision (required / not_required) is a TRANSITION with a mandatory
  comment, not a field write. decision_rationale carries the reasoning.
- content and channel are frozen once the obligation has been sent: an amendment
  is a further filing, never an edit.
- The clock (anchor_at, due_at) is derived and freezes on the first filing.
Read-only: decision, decided_by, decided_at, sent_at, sent_by,
  first_submitted_at, late_by, anchor_at, due_at, source, template_id,
  recipient_display, deadline_bucket, is_overdue, was_filed_late, has_proof
Special tool: list_overdue_incident_notifications(...) - every duty past its
  deadline with no filing, with hours overdue and the incident manager.
Filters: incident_id, regime, recipient_kind, decision, channel, source, workflow_state, authority_id, template_id, no_fixed_deadline
Ref prefix: INOT

## notification_filing
One transmission against one obligation. APPEND-ONLY: create and read tools only,
no update and no delete. An amendment is a further filing.
Tools: create_notification_filing, list_notification_filings,
  get_notification_filing, get_notification_filing_history
Writable at create: notification_id (required), submitted_at, channel,
  recipient_name, subject, content, external_reference, is_correction,
  supersedes_id, comment
- channel: same list as incident_notification.channel
- The FIRST filing on an obligation runs through the lifecycle: it stamps
  sent_at, sent_by, first_submitted_at and late_by on the obligation, moves it
  to its sent step and narrates the act in the incident chronology. Later
  filings insert without disturbing any of it.
- The first filing is never a correction. supersedes_id implies is_correction
  and must point at a filing on the same obligation.
- was_late is computed at insert from the obligation's deadline and never again;
  submitted_by is always the calling account; submitted_at cannot be in the future.
Permission: incidents.notification.update to record, .read to list.
Filters: notification_id, channel, outcome, is_correction, was_late, submitted_by_id
Ref prefix: NFIL

## personal_data_breach
GDPR qualification of an incident. One per incident, scoped through it.
Writable: incident_id (required), controller_role, controller_supplier_id,
  lead_authority_id, cross_border_eu, nature, data_categories,
  data_subject_categories, approximate_data_subjects, approximate_records,
  special_categories, volume_is_estimate, dpo_contact, likely_consequences,
  measures_taken, high_risk_to_rights, high_risk_justification,
  article_34_exemption, article_34_exemption_justification,
  register_entry_reference
- controller_role: controller | joint_controller | processor
- article_34_exemption: none | encryption | subsequent_measures | disproportionate_effort
- data_categories and data_subject_categories are free-form arrays of strings.
Read-only: qualified_by, qualified_at, acts_as_processor, has_article_33_3_content
Filters: incident_id, controller_role, article_34_exemption, high_risk_to_rights, special_categories, cross_border_eu, workflow_state
Ref prefix: PDBR

## reporting_authority
Catalogue of the bodies filings go to. Carries no scopes and no parent: the CNIL
is the CNIL for every scope of the ISMS, so these rows are visible to every
holder of the read permission.
Writable: name (required), primary_regime (required), short_name, authority_type,
  additional_regimes, jurisdiction_country, portal_url, contact_email,
  contact_phone, notification_language, procedure
- authority_type: supervisory_authority | csirt | competent_authority | sector_regulator | financial_regulator | law_enforcement | other
- primary_regime / additional_regimes: regime codes (see incident_notification)
Permission: incidents.response_plan.* (the catalogue is part of the procedure).
Filters: authority_type, primary_regime, jurisdiction_country, workflow_state
Ref prefix: RGAU

## obligation_template
Catalogue rule that decides which obligations an incident raises, and on which
clock. Same tenancy note as reporting_authority.
Writable: name (required), regime (required), recipient_kind (required),
  authority_id, legal_reference, content_requirements, clock_anchor, clock_hours,
  no_fixed_deadline, depends_on_regime, jurisdiction_country, min_severity,
  requires_significant, requires_personal_data, requires_high_risk,
  requires_cross_border, controller_roles, applicable_categories, order
- regime / depends_on_regime / recipient_kind / clock_anchor: see incident_notification
- min_severity: low | medium | high | critical
- controller_roles: array of controller | joint_controller | processor
- applicable_categories: array of threat-taxonomy codes; empty means all
- no_fixed_deadline says the law imposes none. It is NOT the same as a clock that
  exists and has simply not started, and merging the two is how a real deadline
  disappears from a dashboard.
Permission: incidents.response_plan.*
Filters: regime, recipient_kind, authority_id, jurisdiction_country, min_severity, no_fixed_deadline, workflow_state
Ref prefix: ROBT

## Typical flow
1. create_security_event(title=..., detected_at=..., reported_at=..., scope_ids=[...])
2. transition_security_event(id=..., target_state="reported")
   then "under_assessment"
3. declare_incident_from_event(id="<event-uuid>", comment="Confirmed data exfiltration")
   -> returns the new incident, already declared, with the event linked to it
4. create_incident_timeline_entry(incident_id=..., occurred_at=..., summary=...)
   as the response runs
5. create_incident_evidence(incident_id=..., title=..., evidence_type="log_extract",
   content_hash=..., storage_location=...) then transition it to seal it
6. transition_incident(id=..., target_state=...) through triage, containment,
   eradication, recovery and closure : each step stamps its own timestamp
7. list_overdue_incident_notifications() to see what is late, then
   create_notification_filing(notification_id=..., content=...) to discharge it
8. create_post_incident_review(incident_id=...) and work it through its lifecycle
"""
    TOPIC_WORKFLOW = """\
# Workflow Reference

## Action Plan Workflow (Kanban)

Status values: new | to_define | to_validate | to_implement | implementation_to_validate | validated | closed | cancelled

### Forward transitions:
  new -> to_define (permission: compliance.action_plan.update)
  to_define -> to_validate (permission: compliance.action_plan.update)
  to_validate -> to_implement (permission: compliance.action_plan.validate)
  to_implement -> implementation_to_validate (permission: compliance.action_plan.implement)
  implementation_to_validate -> validated (permission: compliance.action_plan.validate)
  validated -> closed (permission: compliance.action_plan.close)

### Refusal transitions (comment MANDATORY):
  to_validate -> to_define (permission: compliance.action_plan.validate)
  implementation_to_validate -> to_implement (permission: compliance.action_plan.validate)

### Cancellation (comment recommended):
  Any status except closed/cancelled -> cancelled (permission: compliance.action_plan.cancel)

### Tools:
- action_plan_transition(action_plan_id, target_status, comment)
  Execute a transition. Returns {id, status, reference}.
  Example: action_plan_transition(action_plan_id="<uuid>", target_status="to_define")
  Example with refusal: action_plan_transition(action_plan_id="<uuid>", target_status="to_define", comment="Missing evidence, please complete section 3")

- action_plan_allowed_transitions(action_plan_id)
  Returns current_status and list of allowed next statuses with permission requirements.

- action_plan_transitions(action_plan_id)
  Returns full transition history (who, when, from/to status, comment, is_refusal).

- action_plan_kanban()
  Returns Kanban board: columns grouped by status with action plans and workflow rules.

### Typical action plan lifecycle:
1. create_action_plan(name="Remediate A.8.1", priority="high", owner_id="<uuid>", target_date="2025-06-30", requirements=["<req-uuid>"])
2. action_plan_transition(action_plan_id="<uuid>", target_status="to_define")
3. update_action_plan(id="<uuid>", remediation_plan="<html>", gap_description="<html>")
4. action_plan_transition(action_plan_id="<uuid>", target_status="to_validate")
5. action_plan_transition(action_plan_id="<uuid>", target_status="to_implement")   -- or refuse back to to_define
6. update_action_plan(id="<uuid>", progress_percentage=50)
7. action_plan_transition(action_plan_id="<uuid>", target_status="implementation_to_validate")
8. action_plan_transition(action_plan_id="<uuid>", target_status="validated")   -- or refuse back to to_implement
9. action_plan_transition(action_plan_id="<uuid>", target_status="closed")

## Compliance Assessment Workflow

Status values: draft | planned | in_progress | completed | closed | cancelled

### Transitions:
  draft -> planned
  draft -> cancelled
  planned -> in_progress
  planned -> cancelled
  in_progress -> completed
  completed -> closed

### Assessment lifecycle:
1. create_compliance_assessment(name="ISO 27001 Audit 2025", framework_ids=["<fw-uuid>"], assessor_id="<user-uuid>", status="draft")
   -> Auto-creates assessment_results for every requirement in the linked frameworks
2. update_compliance_assessment(id="<uuid>", status="planned", assessment_start_date="2025-04-01")
3. update_compliance_assessment(id="<uuid>", status="in_progress")
4. For each requirement: update_assessment_result(id="<result-uuid>", compliance_status="compliant", evidence="<html>")
   Or for non-conformities: create_finding(assessment_id="<uuid>", finding_type="major_nc", description="<html>", requirement_ids=["<req-uuid>"])
5. update_compliance_assessment(id="<uuid>", status="completed")
6. generate_audit_report(assessment_id="<uuid>", title="ISO 27001 Audit Report 2025")
7. update_compliance_assessment(id="<uuid>", status="closed")

## Lifecycle transitions (all lifecycle entities)

Each entity moves through a lifecycle of steps:
1. Create the entity (it starts on its lifecycle's initial step)
2. Call transition_{entity}(id="<uuid>", target_state="<step>") to advance it
   (e.g. draft -> pending -> validated -> archived)
3. {entity}_allowed_transitions(id="<uuid>") lists the legal next steps
4. A backward / refusal move may require a comment
"""

    TOPIC_BATCH = """\
# Batch Creation - Detailed Reference

## Endpoint
All entities support batch_create_{entity}s(items=[...])
Maximum: 500 items per call.

## Behavior
NON-ATOMIC: each item is processed independently.
Valid items are created even if others fail.
Use this for bulk import - do not worry about partial failures.

## Idempotent re-import (upsert)
Pass `match_on` (a list of writable field names) to make the call idempotent:
each item whose match_on values already exist is UPDATED in place instead of
being duplicated; otherwise it is created. This lets you safely REPLAY a batch
after a partial failure without creating duplicates. Many-to-many fields cannot
be used as a match key. Example:
  batch_create_suppliers(items=[{"name": "AWS", ...}], match_on=["name"])
Re-running the same call updates the existing "AWS" supplier rather than adding
a second one.

## Preserving legacy timestamps
Items may include `created_at` / `updated_at` (ISO 8601) to preserve original
dates from a source system. They are applied ONLY for a caller holding the
`system.data_import.override_dates` permission; otherwise they are silently
dropped and the response flags it (see `timestamps_ignored` / `warning` below).
Call `get_me()` first and check `can_override_import_dates` to know in advance.

## Request format
{"items": [{field1: value1, ...}, ...], "match_on": ["name"]}   // match_on optional

## Response format
{
  "status": "completed" | "completed_with_errors",
  "total": N,         // total items submitted
  "created": M,       // newly created
  "updated": U,       // updated via match_on (0 when match_on is omitted)
  "errors": E,        // failed items
  "timestamps_ignored": K,   // present only if created_at/updated_at were dropped
  "warning": "...",          // present only if timestamps were dropped
  "results": [
    {"index": 0, "status": "created", "id": "<uuid>", "reference": "REQT-1"},
    {"index": 1, "status": "updated", "id": "<uuid>", "reference": "REQT-2"},
    {"index": 2, "status": "error", "errors": "['name': ['This field is required.']]"}
  ]
}

## Example: Populate ISO 27001 Annex A

Step 1 - Create framework:
  create_framework(name="ISO/IEC 27001:2022", type="standard", category="information_security")

Step 2 - Create sections:
  batch_create_sections(items=[
    {"framework_id": "<fw-uuid>", "name": "A.5 Organizational controls", "order": 1},
    {"framework_id": "<fw-uuid>", "name": "A.6 People controls", "order": 2},
    {"framework_id": "<fw-uuid>", "name": "A.7 Physical controls", "order": 3},
    {"framework_id": "<fw-uuid>", "name": "A.8 Technological controls", "order": 4}
  ])

Step 3 - Create requirements:
  batch_create_requirements(items=[
    {"framework_id": "<fw-uuid>", "section_id": "<a5-uuid>", "requirement_number": "A.5.1", "name": "Policies for information security", "description": "...", "type": "mandatory", "linked_risks": []},
    {"framework_id": "<fw-uuid>", "section_id": "<a5-uuid>", "requirement_number": "A.5.2", "name": "Information security roles and responsibilities", "description": "...", "type": "mandatory", "linked_risks": []},
    ...
  ])

## Example: Populate threat catalog

  batch_create_threats(items=[
    {"name": "Ransomware attack", "type": "deliberate", "source": "human_external", "category": "ransomware"},
    {"name": "Phishing campaign", "type": "deliberate", "source": "human_external", "category": "social_engineering"},
    {"name": "Power outage", "type": "environmental", "source": "technical", "category": "power_failure"},
    {"name": "Accidental data deletion", "type": "accidental", "source": "human_internal", "category": "human_error"},
    ...
  ])

## Example: Populate risk register

  batch_create_risks(items=[
    {"assessment_id": "<ra-uuid>", "name": "Data breach via phishing", "status": "identified", "priority": "high", "initial_likelihood": 4, "initial_impact": 5, "treatment_decision": "mitigate"},
    {"assessment_id": "<ra-uuid>", "name": "Service disruption from power failure", "status": "identified", "priority": "medium", "initial_likelihood": 2, "initial_impact": 3, "treatment_decision": "transfer"},
    ...
  ])

## Example: Populate suppliers

  batch_create_suppliers(items=[
    {"name": "AWS", "type": 1, "criticality": "critical", "owner_id": "<user-uuid>", "status": "active", "country": "US"},
    {"name": "OVHcloud", "type": 1, "criticality": "high", "owner_id": "<user-uuid>", "status": "active", "country": "FR"},
    ...
  ])
  Note: "type" is an integer SupplierType ID. Call list_supplier_types() first
  to get IDs (create the type with create_supplier_type if it does not exist).

## Provisioning owners / reviewers first
Entities like suppliers require an existing `owner_id`. If the person has no
account yet, create one with `create_user(email=..., last_name=..., groups=[...])`
(invitation flow, no password) and use the returned id as `owner_id`. See the
`users` topic (help(topic="users")).
"""

    TOPIC_PERMISSIONS = """\
# Permissions Reference

## Permission format
All permissions follow: module.feature.action

## Actions
- read: view/list entities
- create: create new entities
- update: modify existing entities
- delete: remove entities
- approve: validate / archive in the lifecycle (the permission gating those transitions)

## Special action plan permissions
- compliance.action_plan.validate: approve or refuse at validation stages
- compliance.action_plan.implement: submit implementation for validation
- compliance.action_plan.close: close a validated action plan
- compliance.action_plan.cancel: cancel an action plan

## Module permissions

### Context (context.*)
context.scope.read/create/update/delete/approve
context.issue.read/create/update/delete/approve
context.stakeholder.read/create/update/delete/approve
context.objective.read/create/update/delete/approve
context.swot.read/create/update/delete/approve
context.role.read/create/update/delete/approve
context.activity.read/create/update/delete/approve
context.site.read/create/update/delete/approve
context.indicator.read/create/update/delete/approve

### Assets (assets.*)
assets.essential_asset.read/create/update/delete/approve
assets.support_asset.read/create/update/delete/approve
assets.dependency.read/create/update/delete
assets.group.read/create/update/delete/approve
assets.supplier.read/create/update/delete/approve
assets.supplier_dependency.read/create/update/delete
assets.contract.read/create/update/delete/approve
assets.certificate.read/create/update/delete/approve

### Compliance (compliance.*)
compliance.framework.read/create/update/delete/approve
compliance.section.read/create/update/delete
compliance.requirement.read/create/update/delete/approve
compliance.assessment.read/create/update/delete/approve
compliance.action_plan.read/create/update/delete/approve/validate/implement/close/cancel
compliance.report.read/create/delete

### Risks (risks.*)
risks.criteria.read/create/update/delete
risks.assessment.read/create/update/delete/approve
risks.risk.read/create/update/delete/approve
risks.treatment.read/create/update/delete/approve
risks.acceptance.read/create/update/delete
risks.threat.read/create/update/delete/approve
risks.vulnerability.read/create/update/delete/approve
risks.iso27005.read/create/update/delete

### System
system.config.read/update
system.users.read
system.logs.read

## System roles (predefined groups)
- Super Admin: all permissions
- Admin: all permissions except system config
- RSSI/DPO: read/create/update/approve on all modules
- Auditeur: read on all modules, create/update on compliance
- Contributeur: read/create/update on assigned scopes
- Lecteur: read-only on assigned scopes

Superusers bypass all permission checks.
Use list_permissions() to see all available codenames.
"""

    TOPIC_EXAMPLES = """\
# End-to-End Examples

## Example 1: Full compliance audit workflow

### Step 1: Set up the framework (one-time)
  create_framework(name="ISO/IEC 27001:2022", type="standard", category="information_security", status="active")
  -> returns {id: "<fw-uuid>", reference: "FRMW-1", ...}

  batch_create_sections(items=[
    {"framework_id": "<fw-uuid>", "name": "A.5 Organizational controls", "order": 1},
    {"framework_id": "<fw-uuid>", "name": "A.6 People controls", "order": 2}
  ])
  -> returns section UUIDs

  batch_create_requirements(items=[
    {"framework_id": "<fw-uuid>", "section_id": "<a5-uuid>", "requirement_number": "A.5.1", "name": "Policies for information security", "description": "A set of policies for information security shall be defined, approved by management, published, communicated to and acknowledged by relevant personnel and relevant interested parties.", "type": "mandatory", "linked_risks": []},
    ...93 requirements total...
  ])

### Step 2: Create and run the assessment
  create_compliance_assessment(name="Annual ISO 27001 Audit 2025", framework_ids=["<fw-uuid>"], assessor_id="<auditor-uuid>", status="draft")
  -> auto-creates 93 assessment_results (one per requirement)

  update_compliance_assessment(id="<assess-uuid>", status="planned", assessment_start_date="2025-04-01", assessment_end_date="2025-04-30")
  update_compliance_assessment(id="<assess-uuid>", status="in_progress")

### Step 3: Record assessment results
  list_assessment_results(assessment_id="<assess-uuid>", limit=100)
  -> returns 93 results, each with requirement_id and status "not_assessed"

  For each requirement, update its result:
  update_assessment_result(id="<result-uuid>", compliance_status="compliant", evidence="<p>Policy document v3.2 reviewed. Last update: 2025-01-15.</p>")

  For non-conformities, create findings:
  create_finding(assessment_id="<assess-uuid>", finding_type="major_nc", description="<p>No documented policy for mobile device management.</p>", evidence="<p>Interview with IT manager confirmed no policy exists.</p>", recommendation="<p>Draft and approve a mobile device policy within 30 days.</p>", requirement_ids=["<req-a5.1-uuid>"])

### Step 4: Create remediation action plans
  create_action_plan(name="Draft mobile device policy", gap_description="<p>No documented mobile device management policy.</p>", remediation_plan="<p>1. Draft policy based on ISO 27001 A.8.1<br>2. Review with CISO<br>3. Approve and publish</p>", priority="high", owner_id="<ciso-uuid>", target_date="2025-05-30", requirements=["<req-a5.1-uuid>"])

  action_plan_transition(action_plan_id="<ap-uuid>", target_status="to_define")
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="to_validate")
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="to_implement")
  update_action_plan(id="<ap-uuid>", progress_percentage=100)
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="implementation_to_validate")
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="validated")
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="closed")

### Step 5: Finalize
  update_compliance_assessment(id="<assess-uuid>", status="completed")
  generate_audit_report(assessment_id="<assess-uuid>", title="ISO 27001 Audit Report 2025")
  update_compliance_assessment(id="<assess-uuid>", status="closed")

## Example 2: Full risk assessment workflow

### Step 1: Define risk criteria
  create_risk_criteria(name="Standard 5x5 Matrix", methodology="iso27005", status="active")

  batch_create_scale_levels(items=[
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 1, "name": "Very Low", "description": "Less than once every 5 years", "color": "#4caf50"},
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 2, "name": "Low", "description": "Once every 2-5 years", "color": "#8bc34a"},
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 3, "name": "Medium", "description": "Once per year", "color": "#ff9800"},
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 4, "name": "High", "description": "Once per quarter", "color": "#f44336"},
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 5, "name": "Very High", "description": "Monthly or more", "color": "#b71c1c"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 1, "name": "Negligible", "color": "#4caf50"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 2, "name": "Minor", "color": "#8bc34a"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 3, "name": "Moderate", "color": "#ff9800"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 4, "name": "Major", "color": "#f44336"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 5, "name": "Catastrophic", "color": "#b71c1c"}
  ])

  batch_create_risk_levels(items=[
    {"criteria_id": "<rc-uuid>", "level": 1, "name": "Low", "color": "#4caf50", "min_score": 1, "max_score": 5, "treatment_required": false},
    {"criteria_id": "<rc-uuid>", "level": 2, "name": "Medium", "color": "#ff9800", "min_score": 6, "max_score": 12, "treatment_required": true},
    {"criteria_id": "<rc-uuid>", "level": 3, "name": "High", "color": "#f44336", "min_score": 13, "max_score": 19, "treatment_required": true},
    {"criteria_id": "<rc-uuid>", "level": 4, "name": "Critical", "color": "#b71c1c", "min_score": 20, "max_score": 25, "treatment_required": true}
  ])

### Step 2: Create assessment and risks
  create_risk_assessment(name="Annual Risk Assessment 2025", risk_criteria_id="<rc-uuid>", methodology="iso27005", status="in_progress", assessor_id="<user-uuid>")

  batch_create_risks(items=[
    {"assessment_id": "<ra-uuid>", "name": "Ransomware encrypts production data", "status": "identified", "priority": "critical", "initial_likelihood": 4, "initial_impact": 5, "current_likelihood": 3, "current_impact": 5, "treatment_decision": "mitigate", "risk_owner_id": "<ciso-uuid>"},
    {"assessment_id": "<ra-uuid>", "name": "Employee data leak via phishing", "status": "identified", "priority": "high", "initial_likelihood": 4, "initial_impact": 4, "current_likelihood": 3, "current_impact": 4, "treatment_decision": "mitigate"},
    {"assessment_id": "<ra-uuid>", "name": "Power failure at primary DC", "status": "identified", "priority": "medium", "initial_likelihood": 2, "initial_impact": 4, "current_likelihood": 2, "current_impact": 2, "treatment_decision": "transfer"}
  ])

### Step 3: Create treatment plans
  create_risk_treatment_plan(name="Anti-ransomware measures", risk_id="<risk1-uuid>", owner_id="<it-uuid>", target_date="2025-09-30", status="planned")

  batch_create_treatment_actions(items=[
    {"treatment_plan_id": "<rtp-uuid>", "name": "Deploy EDR on all endpoints", "responsible_id": "<it-uuid>", "due_date": "2025-06-30", "status": "planned"},
    {"treatment_plan_id": "<rtp-uuid>", "name": "Implement immutable backups", "responsible_id": "<it-uuid>", "due_date": "2025-07-31", "status": "planned"},
    {"treatment_plan_id": "<rtp-uuid>", "name": "Conduct ransomware response drill", "responsible_id": "<ciso-uuid>", "due_date": "2025-09-15", "status": "planned"}
  ])

### Step 4: Link risks to requirements
  link_risk_requirements(risk_id="<risk1-uuid>", requirement_ids=["<req-a8.7-uuid>", "<req-a8.13-uuid>"])

### Step 5: Finalize
  update_risk_assessment(id="<ra-uuid>", status="completed")
  approve_risk_assessment(id="<ra-uuid>")
"""

    TOPIC_USERS = """\
# Users, provisioning & self capabilities

## Who am I / what may I do
get_me() returns the current account plus capability flags:
- can_override_import_dates : may preserve created_at / updated_at on import
  (needs system.data_import.override_dates). Check this BEFORE relying on legacy
  timestamps - without it, supplied dates are silently dropped.
- can_create_users : may provision users (needs system.users.create).

## Provisioning a user (invitation flow)
Many entities require an owner_id / reviewer pointing to an existing user. If
the person has no account yet:
  create_user(email="jane@corp.example", last_name="Doe", first_name="Jane",
              groups=["Contributeur"])
- No password is accepted. The account is created with an unusable password and
  the response returns an `activation_url` the invitee opens to set their first
  credential. The account can be referenced as an owner immediately.
- `groups` are role / group NAMES that must already exist. Call list_groups() to
  see them (the 6 system roles: Super Administrateur, Administrateur, RSSI / DPO,
  Auditeur, Contributeur, Lecteur).
- `user_type` is "human" (default) or "robot" (service account).
- Requires the system.users.create permission.
Read users with list_users() / get_user(id).

## Finding a tool by exact name
Every tool listed by help / this guide is registered under its exact name (e.g.
list_supplier_types, create_user). If a fuzzy tool search does not surface a
tool, call it by its exact name directly - the name here is authoritative.
"""

    ALL_TOPICS = {
        "context": TOPIC_CONTEXT,
        "assets": TOPIC_ASSETS,
        "compliance": TOPIC_COMPLIANCE,
        "risks": TOPIC_RISKS,
        "incidents": TOPIC_INCIDENTS,
        "batch": TOPIC_BATCH,
        "workflow": TOPIC_WORKFLOW,
        "permissions": TOPIC_PERMISSIONS,
        "examples": TOPIC_EXAMPLES,
        "users": TOPIC_USERS,
    }

    def help_handler(user, arguments):
        topic = arguments.get("topic", "").strip().lower()
        if not topic:
            return HELP_TEXT

        result = ALL_TOPICS.get(topic)
        if not result:
            for key, value in ALL_TOPICS.items():
                if topic in key or key in topic:
                    result = value
                    break
        if not result:
            available = ", ".join(sorted(ALL_TOPICS.keys()))
            result = f"Unknown topic '{topic}'. Available topics: {available}\n\nCall help without a topic for the full guide."
        return result

    server.register_tool(
        "help",
        "Get usage documentation for the Cairn MCP server. "
        "Call without arguments for the full guide, or with a topic for focused help. "
        "Topics: context, assets, compliance, risks, incidents, batch, workflow, permissions, examples, users",
        {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional topic: context, assets, compliance, risks, incidents, batch, workflow, permissions, examples, users",
                },
            },
        },
        help_handler,
    )


# ── Context Module ─────────────────────────────────────────

def _register_context_tools(server):
    Scope = _get_model("context", "Scope")
    Issue = _get_model("context", "Issue")
    Stakeholder = _get_model("context", "Stakeholder")
    StakeholderExpectation = _get_model("context", "StakeholderExpectation")
    Objective = _get_model("context", "Objective")
    SwotAnalysis = _get_model("context", "SwotAnalysis")
    SwotItem = _get_model("context", "SwotItem")
    Role = _get_model("context", "Role")
    Responsibility = _get_model("context", "Responsibility")
    Activity = _get_model("context", "Activity")
    Site = _get_model("context", "Site")
    Indicator = _get_model("context", "Indicator")
    IndicatorMeasurement = _get_model("context", "IndicatorMeasurement")
    Tag = _get_model("context", "Tag")

    scope_fields = ["id", "reference", "name", "description", "workflow_state",
                    "parent_scope_id", "icon",
                    "boundaries", "justification_exclusions",
                    "geographic_scope", "organizational_scope", "technical_scope",
                    "included_sites", "excluded_sites", "managers", "manager_names",
                    "effective_date", "review_date",
                    "version", "created_at"]
    scope_writable = ["name", "description", "icon",
                      "boundaries", "justification_exclusions",
                      "geographic_scope", "organizational_scope", "technical_scope",
                      "effective_date", "review_date", "parent_scope_id",
                      "manager_ids", "included_site_ids", "excluded_site_ids"]

    _register_crud(server, "scope", Scope, "context.scope",
                   list_fields=scope_fields,
                   writable_fields=scope_writable,
                   search_fields=["name", "description"],
                   filters=["workflow_state", "parent_scope_id"],
                   required_fields=["name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "boundaries": _html_field("Boundaries and exclusions"),
                       "justification_exclusions": _html_field("Justification for exclusions"),
                       "geographic_scope": _html_field("Geographic scope"),
                       "organizational_scope": _html_field("Organizational scope"),
                       "technical_scope": _html_field("Technical scope"),
                       "icon": {"type": "string", "description": "Bootstrap Icons class (e.g. bi-building, bi-globe)."},
                       "effective_date": {"type": "string", "description": "Effective date (ISO 8601, e.g. 2025-01-15)"},
                       "review_date": {"type": "string", "description": "Review date (ISO 8601, e.g. 2025-06-15)"},
                       "parent_scope_id": {"type": "string", "description": "UUID of the parent scope (for nested perimeters)."},
                       "manager_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of user UUIDs to assign as scope managers.",
                       },
                       "included_site_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Sites explicitly included in this scope.",
                       },
                       "excluded_site_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Sites explicitly excluded from this scope.",
                       },
                   },
                   m2m_fields={
                       "manager_ids": "managers",
                       "included_site_ids": "included_sites",
                       "excluded_site_ids": "excluded_sites",
                   })

    issue_fields = ["id", "reference", "scopes", "name", "description", "type", "category",
                    "impact_level", "trend", "source", "related_stakeholders",
                    "review_date", "status", "created_at"]
    issue_writable = ["name", "description", "type", "category", "impact_level",
                      "trend", "source", "review_date", "status",
                      "scope_ids", "related_stakeholder_ids"]

    _register_crud(server, "issue", Issue, "context.issue",
                   list_fields=issue_fields,
                   writable_fields=issue_writable,
                   search_fields=["name", "description"],
                   filters=["type", "category", "impact_level", "status"],
                   required_fields=["name", "type", "category", "impact_level"],
                   m2m_fields={"scope_ids": "scopes",
                               "related_stakeholder_ids": "related_stakeholders"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Issue type.",
                           "enum": ["internal", "external"],
                       },
                       "category": {
                           "type": "string",
                           "description": "Issue category.",
                           "enum": [
                               "strategic", "organizational", "human_resources",
                               "technical", "financial", "cultural",
                               "political", "economic", "social", "technological",
                               "legal", "environmental", "competitive", "regulatory",
                           ],
                       },
                       "impact_level": {
                           "type": "string",
                           "description": "Impact level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "trend": {
                           "type": "string",
                           "description": "Issue trend over time.",
                           "enum": ["improving", "stable", "degrading"],
                       },
                       "source": {
                           "type": "string",
                           "description": "Where the issue was identified (PESTEL workshop, audit, etc.).",
                       },
                       "review_date": {
                           "type": "string",
                           "description": "Next review date (YYYY-MM-DD).",
                       },
                       "status": {
                           "type": "string",
                           "description": "Issue status.",
                           "enum": ["identified", "active", "monitored", "closed"],
                       },
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of scope UUIDs this issue belongs to (RG-01).",
                       },
                       "related_stakeholder_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of stakeholder UUIDs related to this issue.",
                       },
                   })

    stakeholder_fields = ["id", "reference", "scopes", "name", "description", "type", "category",
                          "contact_name", "contact_email", "contact_phone",
                          "influence_level", "interest_level",
                          "review_date", "status",
                          "created_at"]
    stakeholder_writable = ["name", "description", "type", "category",
                            "contact_name", "contact_email", "contact_phone",
                            "influence_level", "interest_level", "review_date", "status",
                            "scope_ids"]

    _register_crud(server, "stakeholder", Stakeholder, "context.stakeholder",
                   list_fields=stakeholder_fields,
                   writable_fields=stakeholder_writable,
                   search_fields=["name", "description"],
                   filters=["type", "category", "status"],
                   required_fields=["name", "type", "category", "influence_level", "interest_level"],
                   m2m_fields={"scope_ids": "scopes"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Stakeholder type.",
                           "enum": ["internal", "external"],
                       },
                       "category": {
                           "type": "string",
                           "description": "Stakeholder category.",
                           "enum": [
                               "executive_management", "employees", "customers",
                               "suppliers", "partners", "regulators", "shareholders",
                               "insurers", "public", "competitors", "unions",
                               "auditors", "other",
                           ],
                       },
                       "influence_level": {
                           "type": "string",
                           "description": "Influence level.",
                           "enum": ["low", "medium", "high"],
                       },
                       "interest_level": {
                           "type": "string",
                           "description": "Interest level.",
                           "enum": ["low", "medium", "high"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Stakeholder status.",
                           "enum": ["active", "inactive"],
                       },
                   })

    expectation_fields = ["id", "description", "type", "priority",
                          "stakeholder_id", "created_at"]
    expectation_writable = ["description", "type", "priority", "stakeholder_id"]

    _register_crud(server, "expectation", StakeholderExpectation, "context.expectation",
                   list_fields=expectation_fields,
                   writable_fields=expectation_writable,
                   search_fields=["description"],
                   filters=["stakeholder_id", "type"],
                   scope_filtered=False,
                   required_fields=["description", "type", "priority", "stakeholder_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Expectation type.",
                           "enum": ["requirement", "expectation", "need"],
                       },
                       "priority": {
                           "type": "string",
                           "description": "Priority level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                   })

    objective_fields = ["id", "reference", "scopes", "name", "description", "category", "type",
                        "target_value", "current_value", "unit",
                        "measurement_method", "measurement_frequency",
                        "status", "progress_percentage", "target_date", "owner_id", "owner_name",
                        "related_issues", "related_stakeholders",
                        "parent_objective_id", "review_date",
                        "created_at"]
    objective_writable = ["name", "description", "category", "type",
                          "target_value", "current_value", "unit",
                          "measurement_method", "measurement_frequency",
                          "status", "progress_percentage", "target_date",
                          "owner_id", "parent_objective_id", "review_date",
                          "scope_ids", "related_issue_ids", "related_stakeholder_ids"]

    _register_crud(server, "objective", Objective, "context.objective",
                   list_fields=objective_fields,
                   writable_fields=objective_writable,
                   search_fields=["name", "description"],
                   filters=["category", "type", "status"],
                   required_fields=["name", "category", "type", "owner_id"],
                   m2m_fields={"scope_ids": "scopes",
                               "related_issue_ids": "related_issues",
                               "related_stakeholder_ids": "related_stakeholders"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "owner_id": {"type": "string", "description": "UUID of the objective owner (user)"},
                       "category": {
                           "type": "string",
                           "description": "Objective category.",
                           "enum": [
                               "confidentiality", "integrity", "availability",
                               "compliance", "operational", "strategic",
                           ],
                       },
                       "type": {
                           "type": "string",
                           "description": "Objective type.",
                           "enum": ["security", "compliance", "business", "other"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Objective status. To set 'achieved' you must also pass progress_percentage=100.",
                           "enum": ["draft", "active", "achieved", "not_achieved", "cancelled"],
                       },
                       "progress_percentage": {
                           "type": "integer",
                           "description": "Progress percentage (0-100). Required to be 100 when status=achieved.",
                           "minimum": 0,
                           "maximum": 100,
                       },
                       "measurement_frequency": {
                           "type": "string",
                           "description": "How often the objective is measured.",
                           "enum": ["continuous", "daily", "weekly", "monthly",
                                    "quarterly", "biannual", "annual", "on_demand"],
                       },
                       "target_value": {"type": "string", "description": "Target value (free-form, e.g. '95%' or '< 30 days')"},
                       "current_value": {"type": "string", "description": "Current value (free-form, same format as target_value)"},
                       "unit": {"type": "string", "description": "Unit of measure (e.g. '%', 'days')"},
                       "measurement_method": {"type": "string", "description": "How the objective is measured."},
                       "target_date": {"type": "string", "description": "Target date (ISO 8601, e.g. 2025-12-31)"},
                       "review_date": {"type": "string", "description": "Next review date (ISO 8601)."},
                       "parent_objective_id": {"type": "string", "description": "Parent objective UUID (for objective hierarchies)."},
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of scope UUIDs this objective belongs to (RG-01).",
                       },
                       "related_issue_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of issue UUIDs addressed by this objective.",
                       },
                       "related_stakeholder_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of stakeholder UUIDs related to this objective.",
                       },
                   })

    swot_fields = ["id", "reference", "scopes", "name", "description", "analysis_date",
                   "workflow_state", "validated_by_id", "validated_at", "review_date",
                   "created_at"]
    swot_writable = ["name", "description", "analysis_date",
                     "review_date", "scope_ids"]

    _register_crud(server, "swot_analysis", SwotAnalysis, "context.swot",
                   list_fields=swot_fields,
                   writable_fields=swot_writable,
                   search_fields=["name", "description"],
                   filters=["workflow_state"],
                   required_fields=["name", "analysis_date"],
                   m2m_fields={"scope_ids": "scopes"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "analysis_date": {"type": "string", "description": "Analysis date in ISO 8601 format (e.g. 2025-06-15)"},
                       "review_date": {"type": "string", "description": "Next review date (ISO 8601)."},
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of scope UUIDs this SWOT belongs to (RG-01).",
                       },
                   })

    swot_item_fields = ["id", "quadrant", "description", "impact_level",
                        "related_issues", "related_objectives",
                        "order", "swot_analysis_id", "created_at"]
    swot_item_writable = ["quadrant", "description", "impact_level", "order",
                          "swot_analysis_id",
                          "related_issue_ids", "related_objective_ids"]

    _register_crud(server, "swot_item", SwotItem, "context.swot",
                   list_fields=swot_item_fields,
                   writable_fields=swot_item_writable,
                   search_fields=["description"],
                   filters=["swot_analysis_id", "quadrant"],
                   scope_filtered=False,
                   required_fields=["quadrant", "description", "swot_analysis_id"],
                   m2m_fields={"related_issue_ids": "related_issues",
                               "related_objective_ids": "related_objectives"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "quadrant": {
                           "type": "string",
                           "description": "SWOT quadrant.",
                           "enum": ["strength", "weakness", "opportunity", "threat"],
                       },
                       "impact_level": {
                           "type": "string",
                           "description": "Impact level.",
                           "enum": ["low", "medium", "high"],
                       },
                       "swot_analysis_id": {"type": "string", "description": "UUID of the parent SWOT analysis"},
                       "related_issue_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Issues this item connects to.",
                       },
                       "related_objective_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Objectives this item informs.",
                       },
                   })

    SwotStrategy = _get_model("context", "SwotStrategy")
    swot_strategy_fields = ["id", "quadrant", "description", "order",
                            "swot_analysis_id", "created_at"]
    swot_strategy_writable = ["quadrant", "description", "order",
                              "swot_analysis_id"]

    _register_crud(server, "swot_strategy", SwotStrategy, "context.swot",
                   list_fields=swot_strategy_fields,
                   writable_fields=swot_strategy_writable,
                   search_fields=["description"],
                   filters=["swot_analysis_id", "quadrant"],
                   scope_filtered=False,
                   required_fields=["quadrant", "description", "swot_analysis_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "quadrant": {
                           "type": "string",
                           "description": "Strategy quadrant.",
                           "enum": ["so", "st", "wo", "wt"],
                       },
                       "swot_analysis_id": {"type": "string", "description": "UUID of the parent SWOT analysis"},
                   })

    role_fields = ["id", "reference", "scopes", "name", "description", "type",
                   "assigned_users", "is_mandatory", "source_standard", "status",
                   "created_at"]
    role_writable = ["name", "description", "type", "is_mandatory", "source_standard",
                     "status", "scope_ids", "assigned_user_ids"]

    _register_crud(server, "role", Role, "context.role",
                   list_fields=role_fields,
                   writable_fields=role_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status"],
                   required_fields=["name", "type"],
                   m2m_fields={"scope_ids": "scopes",
                               "assigned_user_ids": "assigned_users"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Role type.",
                           "enum": ["governance", "operational", "support", "control"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Role status.",
                           "enum": ["active", "inactive"],
                       },
                       "is_mandatory": {
                           "type": "boolean",
                           "description": "Whether this role is mandatory (enables the 'mandatory role without assigned user' compliance alert).",
                       },
                       "source_standard": {
                           "type": "string",
                           "description": "Standard or regulation that requires this role (e.g. 'ISO 27001:2022 §5.3').",
                       },
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of scope UUIDs this role belongs to (RG-01).",
                       },
                       "assigned_user_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "UUIDs of users assigned to this role.",
                       },
                   })

    activity_fields = ["id", "reference", "scopes", "name", "description", "type", "criticality",
                       "owner_id", "owner_name", "parent_activity_id",
                       "related_stakeholders", "related_objectives", "essential_assets",
                       "status", "created_at"]
    activity_writable = ["name", "description", "type", "criticality", "owner_id",
                         "status", "parent_activity_id", "scope_ids",
                         "related_stakeholder_ids", "related_objective_ids",
                         "linked_essential_asset_ids"]

    _register_crud(server, "activity", Activity, "context.activity",
                   list_fields=activity_fields,
                   writable_fields=activity_writable,
                   search_fields=["name", "description"],
                   filters=["type", "criticality", "status"],
                   required_fields=["name", "type", "criticality", "owner_id"],
                   m2m_fields={"scope_ids": "scopes",
                               "related_stakeholder_ids": "related_stakeholders",
                               "related_objective_ids": "related_objectives",
                               "linked_essential_asset_ids": "essential_assets"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "owner_id": {"type": "string", "description": "UUID of the activity owner (user)"},
                       "parent_activity_id": {"type": "string", "description": "Parent activity UUID (must share at least one scope)."},
                       "type": {
                           "type": "string",
                           "description": "Activity type.",
                           "enum": ["core_business", "support", "management"],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Activity status.",
                           "enum": ["active", "inactive", "planned"],
                       },
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of scope UUIDs this activity belongs to (RG-01).",
                       },
                       "related_stakeholder_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Stakeholders involved in this activity.",
                       },
                       "related_objective_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Objectives this activity contributes to.",
                       },
                       "linked_essential_asset_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Essential assets supporting this activity (uses the reverse manager of EssentialAsset.related_activities).",
                       },
                   })

    site_fields = ["id", "reference", "scopes", "name", "description", "type", "workflow_state",
                   "address", "parent_site_id", "created_at"]
    site_writable = ["name", "description", "type", "address",
                     "parent_site_id", "scope_ids"]

    _register_crud(server, "site", Site, "context.site",
                   list_fields=site_fields,
                   writable_fields=site_writable,
                   search_fields=["name", "description"],
                   filters=["type", "workflow_state", "parent_site_id"],
                   required_fields=["name"],
                   m2m_fields={"scope_ids": "scopes"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Site type.",
                           "enum": [
                               "headquarters", "office", "factory", "warehouse",
                               "datacenter", "remote", "other",
                           ],
                       },
                       "parent_site_id": {
                           "type": "string",
                           "description": "UUID of the parent site (for site hierarchies). Cycles are rejected.",
                       },
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this site belongs to.",
                       },
                   })

    # Tags (simple CRUD, no approve)
    server.register_tool(
        "list_tags",
        "List all tags",
        _list_schema({"search": {"type": "string"}}),
        require_perm("context.scope.read")(
            _list_handler(Tag, ["id", "name", "color", "created_at"], ["name"], scope_filtered=False)
        ),
    )
    server.register_tool(
        "create_tag",
        "Create a tag",
        _obj_schema({"name": {"type": "string"}, "color": {"type": "string"}}, ["name"]),
        require_perm("context.scope.create")(
            _create_handler(Tag, ["name", "color"], scope_filtered=False)
        ),
    )
    server.register_tool(
        "delete_tag",
        "Delete a tag",
        _id_schema(),
        require_perm("context.scope.delete")(
            _delete_handler(Tag, scope_filtered=False)
        ),
    )

    # Indicator (scoped, with approve)
    indicator_fields = ["id", "reference", "scopes", "name", "description", "indicator_type",
                        "collection_method", "format", "unit", "current_value",
                        "expected_level", "critical_threshold_operator",
                        "critical_threshold_value", "critical_threshold_min",
                        "critical_threshold_max", "review_frequency",
                        "first_review_date", "status", "is_internal",
                        "internal_source", "internal_source_parameter",
                        "owner_id", "linked_objectives", "linked_requirements",
                        "created_at"]
    indicator_writable = ["name", "description", "indicator_type", "collection_method",
                          "format", "unit", "expected_level",
                          "critical_threshold_operator", "critical_threshold_value",
                          "critical_threshold_min", "critical_threshold_max",
                          "review_frequency", "first_review_date", "status",
                          "is_internal", "internal_source", "internal_source_parameter",
                          "owner_id",
                          "scope_ids",
                          "linked_objective_ids", "linked_requirement_ids"]

    _register_crud(server, "indicator", Indicator, "context.indicator",
                   list_fields=indicator_fields,
                   writable_fields=indicator_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["indicator_type", "status", "format", "collection_method"],
                   required_fields=["name", "indicator_type", "format",
                                    "review_frequency", "first_review_date"],
                   m2m_fields={"scope_ids": "scopes",
                               "linked_objective_ids": "linked_objectives",
                               "linked_requirement_ids": "linked_requirements"},
                   field_overrides={
                       "first_review_date": {
                           "type": "string",
                           "description": "First review date (ISO 8601, e.g. 2026-06-30). Required.",
                       },
                       "owner_id": {
                           "type": "string",
                           "description": "UUID of the user accountable for measuring and reviewing this indicator.",
                       },
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this indicator belongs to.",
                       },
                       "linked_objective_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Objectives this indicator measures progress against (ISO 27001 §6.2 / §9.1).",
                       },
                       "linked_requirement_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Compliance requirements this indicator measures the satisfaction of.",
                       },
                       "description": _html_field("Description"),
                       "indicator_type": {
                           "type": "string",
                           "description": "Indicator type.",
                           "enum": ["organizational", "technical"],
                       },
                       "collection_method": {
                           "type": "string",
                           "description": "Data collection method.",
                           "enum": ["manual", "api", "internal"],
                       },
                       "format": {
                           "type": "string",
                           "description": "Indicator format.",
                           "enum": ["number", "boolean"],
                       },
                       "review_frequency": {
                           "type": "string",
                           "description": "Review frequency.",
                           "enum": ["daily", "weekly", "monthly", "quarterly", "semi_annual", "annual"],
                       },
                       "critical_threshold_operator": {
                           "type": "string",
                           "description": "Critical threshold operator.",
                           "enum": ["below", "above", "is_false", "is_true"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Indicator status.",
                           "enum": ["active", "inactive", "draft"],
                       },
                       "is_internal": {"type": "boolean", "description": "Whether this is an internal predefined indicator."},
                       "internal_source": {
                           "type": "string",
                           "description": "Predefined indicator source (only for internal indicators).",
                           "enum": [
                               "global_compliance_rate", "framework_compliance_rate",
                               "objective_progress", "risk_treatment_rate",
                               "approved_scopes_rate", "mandatory_roles_coverage",
                           ],
                       },
                   })

    # Indicator measurements (child of Indicator, no approve)
    measurement_fields = ["id", "indicator_id", "value", "recorded_at",
                          "recorded_by_id", "notes"]
    measurement_writable = ["indicator_id", "value", "recorded_at",
                            "recorded_by_id", "notes"]

    _register_crud(server, "indicator_measurement", IndicatorMeasurement,
                   "context.indicator",
                   list_fields=measurement_fields,
                   writable_fields=measurement_writable,
                   search_fields=["notes"],
                   filters=["indicator_id"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["indicator_id", "value"],
                   field_overrides={
                       "indicator_id": {"type": "string", "description": "UUID of the indicator this measurement belongs to (required)."},
                       "value": {"type": "string", "description": "Measured value (number or boolean as string)."},
                       "recorded_at": {"type": "string", "description": "Measurement timestamp (ISO 8601). Defaults to the current time if omitted; backdate historical measurements by passing an earlier datetime."},
                       "recorded_by_id": {"type": "string", "description": "UUID of the user recording the measurement."},
                       "notes": {"type": "string", "description": "Free-form notes."},
                   })

    # Responsibility (child of Role, no approve)
    responsibility_fields = ["id", "role_id", "description", "raci_type",
                             "related_activity_id", "created_at"]
    responsibility_writable = ["role_id", "description", "raci_type",
                               "related_activity_id"]

    _register_crud(server, "responsibility", Responsibility, "context.role",
                   list_fields=responsibility_fields,
                   writable_fields=responsibility_writable,
                   search_fields=["description"],
                   filters=["role_id", "raci_type"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["role_id", "description", "raci_type"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "raci_type": {
                           "type": "string",
                           "description": "RACI responsibility type.",
                           "enum": ["responsible", "accountable", "consulted", "informed"],
                       },
                   })


# ── Assets Module ──────────────────────────────────────────

def _register_assets_tools(server):
    EssentialAsset = _get_model("assets", "EssentialAsset")
    SupportAsset = _get_model("assets", "SupportAsset")
    AssetDependency = _get_model("assets", "AssetDependency")
    AssetGroup = _get_model("assets", "AssetGroup")
    Contract = _get_model("assets", "Contract")
    Certificate = _get_model("assets", "Certificate")
    Supplier = _get_model("assets", "Supplier")
    SupplierDependency = _get_model("assets", "SupplierDependency")
    SupplierSubprocessor = _get_model("assets", "SupplierSubprocessor")
    SiteAssetDependency = _get_model("assets", "SiteAssetDependency")
    SiteSupplierDependency = _get_model("assets", "SiteSupplierDependency")
    AssetValuation = _get_model("assets", "AssetValuation")
    SupplierType = _get_model("assets", "SupplierType")
    SupplierTypeRequirement = _get_model("assets", "SupplierTypeRequirement")
    SupplierRequirement = _get_model("assets", "SupplierRequirement")
    SupplierRequirementReview = _get_model("assets", "SupplierRequirementReview")
    SupplierContact = _get_model("assets", "SupplierContact")

    ea_fields = ["id", "reference", "scopes", "name", "description", "type", "category",
                 "owner_id", "owner_name", "custodian_id", "status",
                 "confidentiality_level", "integrity_level", "availability_level",
                 "confidentiality_justification", "integrity_justification",
                 "availability_justification",
                 "max_tolerable_downtime", "recovery_time_objective", "recovery_point_objective",
                 "data_classification", "personal_data", "personal_data_categories",
                 "regulatory_constraints", "related_activities", "review_date",
                 "created_at"]
    ea_writable = ["name", "description", "type", "category", "status",
                   "confidentiality_level", "integrity_level", "availability_level",
                   "confidentiality_justification", "integrity_justification",
                   "availability_justification",
                   "max_tolerable_downtime", "recovery_time_objective", "recovery_point_objective",
                   "data_classification", "personal_data", "personal_data_categories",
                   "regulatory_constraints", "review_date",
                   "owner_id", "custodian_id",
                   "scope_ids", "related_activity_ids"]

    _register_crud(server, "essential_asset", EssentialAsset, "assets.essential_asset",
                   list_fields=ea_fields,
                   writable_fields=ea_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["type", "category", "status"],
                   required_fields=["name", "type", "category", "owner_id"],
                   m2m_fields={"scope_ids": "scopes",
                               "related_activity_ids": "related_activities"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Essential asset type.",
                           "enum": ["business_process", "information"],
                       },
                       "category": {
                           "type": "string",
                           "description": "Essential asset category.",
                           "enum": [
                               "core_process", "support_process", "management_process",
                               "strategic_data", "operational_data", "personal_data",
                               "financial_data", "technical_data", "legal_data",
                               "research_data", "commercial_data",
                           ],
                       },
                       "status": {
                           "type": "string",
                           "description": "Essential asset status.",
                           "enum": ["identified", "active", "under_review", "decommissioned"],
                       },
                       "confidentiality_level": {
                           "type": ["integer", "string"],
                           "description": "Confidentiality level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2.",
                       },
                       "integrity_level": {
                           "type": ["integer", "string"],
                           "description": "Integrity level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2.",
                       },
                       "availability_level": {
                           "type": ["integer", "string"],
                           "description": "Availability level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2.",
                       },
                       "confidentiality_justification": {"type": "string", "description": "Why this confidentiality level was chosen."},
                       "integrity_justification": {"type": "string", "description": "Why this integrity level was chosen."},
                       "availability_justification": {"type": "string", "description": "Why this availability level was chosen."},
                       "max_tolerable_downtime": {"type": "string", "description": "Max tolerable downtime (MTD), free form e.g. '4 hours'."},
                       "recovery_time_objective": {"type": "string", "description": "Recovery Time Objective (RTO), free form."},
                       "recovery_point_objective": {"type": "string", "description": "Recovery Point Objective (RPO), free form."},
                       "data_classification": {
                           "type": "string",
                           "description": "Data classification label.",
                           "enum": ["public", "internal", "confidential", "secret", "restricted"],
                       },
                       "personal_data": {
                           "type": "boolean",
                           "description": "Whether this asset contains personal data.",
                       },
                       "personal_data_categories": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "GDPR categories of personal data (free-form list).",
                       },
                       "regulatory_constraints": {"type": "string", "description": "Applicable regulatory constraints."},
                       "review_date": {"type": "string", "description": "Next review date (ISO 8601)."},
                       "owner_id": {"type": "string", "description": "UUID of the asset owner (user)"},
                       "custodian_id": {"type": "string", "description": "UUID of the asset custodian (user)"},
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this asset belongs to (RG-01).",
                       },
                       "related_activity_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Business activities this asset supports.",
                       },
                   })

    sa_fields = ["id", "reference", "scopes", "name", "description", "type", "category",
                 "owner_id", "owner_name", "custodian_id", "supplier_id",
                 "location", "manufacturer", "model_name", "serial_number",
                 "software_version", "operating_system",
                 "hostname", "ip_address",
                 "acquisition_date", "end_of_life_date", "warranty_expiry_date",
                 "contract_reference",
                 "exposure_level", "environment",
                 "parent_asset_id",
                 "status",
                 "inherited_confidentiality", "inherited_integrity", "inherited_availability",
                 "review_date",
                 "created_at"]
    sa_writable = ["name", "description", "type", "category", "status",
                   "location", "manufacturer", "model_name", "serial_number",
                   "software_version", "operating_system",
                   "hostname", "ip_address",
                   "acquisition_date", "end_of_life_date", "warranty_expiry_date",
                   "contract_reference",
                   "exposure_level", "environment",
                   "review_date",
                   "owner_id", "custodian_id", "supplier_id", "parent_asset_id",
                   "scope_ids"]

    _register_crud(server, "support_asset", SupportAsset, "assets.support_asset",
                   list_fields=sa_fields,
                   writable_fields=sa_writable,
                   search_fields=["reference", "name", "description", "hostname", "ip_address"],
                   filters=["type", "category", "status", "environment", "exposure_level"],
                   required_fields=["name", "type", "category", "owner_id"],
                   m2m_fields={"scope_ids": "scopes"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": (
                               "Support asset type. Physical locations live in `context.Site`, "
                               "not here: the legacy `site` type was removed (migration assets.0029 "
                               "converted existing rows to Site)."
                           ),
                           "enum": ["hardware", "software", "network", "person", "service", "paper"],
                       },
                       "category": {
                           "type": "string",
                           "description": (
                               "Support asset category. Must match the type. "
                               "Hardware: server, workstation, laptop, mobile_device, network_equipment, storage, peripheral, iot_device, removable_media, other_hardware. "
                               "Software: operating_system, database, application, middleware, security_tool, development_tool, saas_application, other_software. "
                               "Network: lan, wan, wifi, vpn, internet_link, firewall_zone, dmz, other_network. "
                               "Person: internal_staff, contractor, external_provider, administrator, developer, other_person. "
                               "Service: cloud_service, hosting_service, managed_service, telecom_service, outsourced_service, other_service. "
                               "Paper: archive, printed_document, form, other_paper."
                           ),
                       },
                       "status": {
                           "type": "string",
                           "description": "Support asset status.",
                           "enum": ["in_stock", "deployed", "active", "under_maintenance", "decommissioned", "disposed"],
                       },
                       "exposure_level": {
                           "type": "string",
                           "description": "Exposure level (network reachability).",
                           "enum": ["internet", "extranet", "intranet", "isolated"],
                       },
                       "environment": {
                           "type": "string",
                           "description": "Environment hosting this asset.",
                           "enum": ["production", "preproduction", "test", "development", "training"],
                       },
                       "location": {"type": "string", "description": "Physical or logical location of the asset."},
                       "manufacturer": {"type": "string", "description": "Manufacturer / vendor."},
                       "model_name": {"type": "string", "description": "Model or version designation."},
                       "serial_number": {"type": "string", "description": "Serial number."},
                       "software_version": {"type": "string", "description": "Software version."},
                       "operating_system": {"type": "string", "description": "Operating system."},
                       "acquisition_date": {"type": "string", "description": "Acquisition date (ISO 8601)."},
                       "end_of_life_date": {"type": "string", "description": "End-of-life date (ISO 8601)."},
                       "warranty_expiry_date": {"type": "string", "description": "Warranty expiry (ISO 8601)."},
                       "contract_reference": {"type": "string", "description": "Procurement / support contract reference."},
                       "review_date": {"type": "string", "description": "Next review date (ISO 8601)."},
                       "owner_id": {"type": "string", "description": "UUID of the asset owner (user)"},
                       "custodian_id": {"type": "string", "description": "UUID of the asset custodian (user)"},
                       "supplier_id": {"type": "string", "description": "UUID of the supplier that provides / hosts / maintains this asset."},
                       "parent_asset_id": {"type": "string", "description": "UUID of the parent support asset (must share at least one scope)."},
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this asset belongs to (RG-01).",
                       },
                   })

    dep_fields = ["id", "essential_asset_id", "support_asset_id", "dependency_type",
                  "criticality", "redundancy_level",
                  "is_single_point_of_failure", "created_at"]
    dep_writable = ["essential_asset_id", "support_asset_id", "dependency_type",
                    "criticality", "redundancy_level", "description"]

    _register_crud(server, "asset_dependency", AssetDependency, "assets.dependency",
                   list_fields=dep_fields,
                   writable_fields=dep_writable,
                   search_fields=[],
                   filters=["essential_asset_id", "support_asset_id", "dependency_type", "criticality"],
                   scope_filtered=False,
                   required_fields=["essential_asset_id", "support_asset_id", "dependency_type", "criticality"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "dependency_type": {
                           "type": "string",
                           "description": "Type of dependency between essential and support asset.",
                           "enum": ["runs_on", "stored_in", "transmitted_by", "managed_by", "hosted_at", "protected_by", "other"],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "redundancy_level": {
                           "type": "string",
                           "description": "Redundancy level for this dependency.",
                           "enum": ["none", "partial", "full"],
                       },
                   })

    ag_fields = ["id", "reference", "scopes", "name", "description", "type",
                 "owner_id", "members", "status", "created_at"]
    ag_writable = ["name", "description", "type", "status", "owner_id",
                   "scope_ids", "member_ids"]

    _register_crud(server, "asset_group", AssetGroup, "assets.group",
                   list_fields=ag_fields,
                   writable_fields=ag_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status"],
                   required_fields=["name", "type"],
                   m2m_fields={"scope_ids": "scopes", "member_ids": "members"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Asset group type (matches SupportAsset.type).",
                           "enum": ["hardware", "software", "network", "person", "service", "paper"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Asset group status.",
                           "enum": ["active", "inactive"],
                       },
                       "owner_id": {"type": "string", "description": "UUID of the group owner (user)"},
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this asset group belongs to (RG-01).",
                       },
                       "member_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "UUIDs of support assets to include in this group.",
                       },
                   })

    contract_fields = ["id", "reference", "label", "status",
                       "start_date", "end_date", "amount", "currency",
                       "scopes", "suppliers", "clients", "parent", "supersedes",
                       "file_name", "notes", "created_at"]
    contract_writable = ["label", "status", "start_date", "end_date",
                         "amount", "currency", "notes", "parent_id",
                         "supersedes_id",
                         "scope_ids", "supplier_ids", "client_ids"]

    _register_crud(server, "contract", Contract, "assets.contract",
                   list_fields=contract_fields,
                   writable_fields=contract_writable,
                   search_fields=["reference", "label", "notes"],
                   filters=["status"],
                   required_fields=["scope_ids"],
                   m2m_fields={
                       "scope_ids": "scopes",
                       "supplier_ids": "suppliers",
                       "client_ids": "clients",
                   },
                   field_overrides={
                       "notes": _html_field("Notes"),
                       "status": {
                           "type": "string",
                           "description": "Contract status.",
                           "enum": ["draft", "signing", "active", "under_review", "expired", "archived"],
                       },
                       "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)."},
                       "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)."},
                       "amount": {"type": "number", "description": "Contract value."},
                       "currency": {"type": "string", "description": "ISO 4217 currency code (e.g. EUR)."},
                       "parent_id": {
                           "type": "string",
                           "description": "UUID of the contract this one amends (avenant); omit for a top-level contract.",
                       },
                       "supersedes_id": {
                           "type": "string",
                           "description": "UUID of the contract or amendment this one cancels and replaces.",
                       },
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this contract belongs to (RG-01). At least one is required.",
                       },
                       "supplier_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "UUIDs of supplier parties (use list_suppliers).",
                       },
                       "client_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "UUIDs of client parties: customer stakeholders (use list_stakeholders).",
                       },
                   })
    # NB: the attached PDF (Contract.file_content) cannot be uploaded through MCP
    # (binary payloads are out of scope for the JSON transport). Attach or replace
    # the document via the web UI; list_/get_contract expose file_name only.

    certificate_fields = ["id", "reference", "label", "framework",
                          "status", "certificate_number", "issuer",
                          "issue_date", "expiry_date", "scope_statement",
                          "scopes", "sites", "supersedes",
                          "file_name", "notes", "created_at"]
    certificate_writable = ["label", "status",
                           "certificate_number", "issuer", "issue_date",
                           "expiry_date", "scope_statement", "notes",
                           "framework_id", "supersedes_id", "scope_ids", "site_ids"]

    _register_crud(server, "certificate", Certificate, "assets.certificate",
                   list_fields=certificate_fields,
                   writable_fields=certificate_writable,
                   search_fields=["reference", "label", "issuer", "certificate_number", "notes"],
                   filters=["status"],
                   required_fields=["scope_ids", "framework_id"],
                   m2m_fields={
                       "scope_ids": "scopes",
                       "site_ids": "sites",
                   },
                   field_overrides={
                       "notes": _html_field("Notes"),
                       "framework_id": {
                           "type": "string",
                           "description": "UUID of the framework (référentiel) this certificate "
                                          "attests compliance to (use list_frameworks). Required.",
                       },
                       "status": {
                           "type": "string",
                           "description": "Certificate lifecycle status.",
                           "enum": ["draft", "assessment", "certified", "under_renewal", "suspended", "expired", "archived"],
                       },
                       "certificate_number": {"type": "string", "description": "Official certificate number from the certification body."},
                       "issuer": {"type": "string", "description": "Certification body that issued the certificate (e.g. AFNOR, BSI)."},
                       "issue_date": {"type": "string", "description": "Issue date (YYYY-MM-DD)."},
                       "expiry_date": {"type": "string", "description": "Expiry date (YYYY-MM-DD)."},
                       "scope_statement": {"type": "string", "description": "Perimeter covered by the certificate (free text)."},
                       "supersedes_id": {
                           "type": "string",
                           "description": "UUID of the previous certificate this one renews and replaces.",
                       },
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this certificate belongs to (RG-01). At least one is required.",
                       },
                       "site_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "UUIDs of sites covered by the certified perimeter (use list_sites).",
                       },
                   })
    # NB: the attached PDF (Certificate.file_content) cannot be uploaded through
    # MCP (binary payloads are out of scope for the JSON transport). Attach or
    # replace the document via the web UI; list_/get_certificate expose
    # file_name only.

    sup_fields = ["id", "reference", "scopes", "name", "description", "type", "type_name",
                  "criticality", "parent_company_id", "parent_company_name",
                  "status", "contact_name", "contact_email", "contact_phone",
                  "website", "address", "country", "latitude", "longitude",
                  "contract_reference", "contract_start_date", "contract_end_date",
                  "is_contract_expired", "next_review_date", "is_review_due",
                  "logo", "logo_16", "logo_32", "logo_64",
                  "notes", "owner_id", "owner_name", "created_at"]
    sup_writable = ["name", "description", "type", "criticality", "parent_company_id", "status",
                    "contact_name", "contact_email", "contact_phone",
                    "website", "address", "country", "latitude", "longitude",
                    "contract_reference", "contract_start_date", "contract_end_date",
                    "next_review_date", "notes", "owner_id", "scope_ids"]

    _sup_field_overrides = {
        "description": _html_field("Description"),
        "notes": _html_field("Notes"),
        "latitude": {"type": "number", "description": "Latitude of the supplier address (WGS84)."},
        "longitude": {"type": "number", "description": "Longitude of the supplier address (WGS84)."},
        "type": {"type": "integer", "description": "ID of a SupplierType. Use list_supplier_types to get valid IDs."},
        "criticality": {
            "type": "string",
            "description": "Supplier criticality.",
            "enum": ["low", "medium", "high", "critical"],
        },
        "status": {
            "type": "string",
            "description": "Supplier status.",
            "enum": ["active", "under_evaluation", "suspended", "archived"],
        },
        "owner_id": {"type": "string", "description": "UUID of the supplier owner (user)"},
        "parent_company_id": {
            "type": "string",
            "description": "UUID of the parent company (another supplier) this supplier "
                           "is a subsidiary of. Use list_suppliers to get valid IDs.",
        },
        "next_review_date": {
            "type": "string",
            "description": "Date of the next scheduled supplier review (ISO 8601, YYYY-MM-DD).",
        },
        "scope_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Scopes this supplier belongs to (RG-01).",
        },
    }

    def _supplier_expired_filter(qs, arguments):
        """Filter to suppliers whose contract has expired (mirrors
        ``Supplier.is_contract_expired``: active supplier, past contract end)."""
        val = arguments.get("expired")
        if str(val).lower() in ("true", "1", "yes"):
            from django.utils import timezone

            from assets.constants import SupplierStatus
            qs = qs.filter(
                status=SupplierStatus.ACTIVE,
                contract_end_date__isnull=False,
                contract_end_date__lte=timezone.now().date(),
            )
        return qs

    _register_crud(server, "supplier", Supplier, "assets.supplier",
                   list_fields=sup_fields,
                   writable_fields=sup_writable,
                   search_fields=["reference", "name", "description", "contact_name"],
                   filters=["type", "criticality", "status"],
                   required_fields=["name", "owner_id"],
                   m2m_fields={"scope_ids": "scopes"},
                   field_overrides=_sup_field_overrides,
                   list_queryset_filter=_supplier_expired_filter,
                   list_extra_filter_props={
                       "expired": {
                           "type": "boolean",
                           "description": "If true, only suppliers whose contract has expired "
                                          "(active suppliers with a contract end date in the past).",
                       },
                   })

    # Custom tool: update supplier logo with automatic variant generation
    server.register_tool(
        "update_supplier_logo",
        "Update a supplier's logo. Provide EITHER a base64 data URI via 'logo' OR a public "
        "image URL via 'image_url'. The image is resized to 128x128 and 64x64, 32x32, 16x16 "
        "variants are generated automatically.",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "UUID of the supplier"},
                "logo": {"type": "string", "description": "Base64 data URI of the logo image (e.g. 'data:image/png;base64,...')"},
                "image_url": {"type": "string", "description": "Public URL of an image to download as the logo"},
            },
            "required": ["id"],
        },
        require_perm("assets.supplier.update")(
            _update_supplier_logo_handler
        ),
    )

    # Override create_supplier to support image_url
    create_sup_props = {f: _sup_field_overrides.get(f, {"type": "string", "description": f}) for f in sup_writable}
    create_sup_props["image_url"] = {
        "type": "string",
        "description": "Public URL of an image to use as the supplier logo (PNG, JPG, WebP, etc.). "
                       "The image is downloaded, resized to 128x128, and size variants are generated.",
    }
    _sup_ts_desc = (
        "Optional ISO 8601 date-time to preserve from a legacy system on bulk "
        "import. Requires the 'system.data_import.override_dates' permission; "
        "ignored without it."
    )
    create_sup_props["created_at"] = {"type": "string", "description": _sup_ts_desc}
    create_sup_props["updated_at"] = {"type": "string", "description": _sup_ts_desc}
    server.register_tool(
        "create_supplier",
        "Create a new supplier. Optionally provide 'image_url' (a public URL pointing to an "
        "image file) to set the supplier logo. The image will be downloaded, resized to 128x128, "
        "and 64x64, 32x32, 16x16 variants will be generated automatically. "
        "Prefer 'image_url' over 'update_supplier_logo' when the logo is available as a URL.",
        _obj_schema(create_sup_props),
        require_perm("assets.supplier.create")(
            _create_supplier_handler(Supplier, sup_writable)
        ),
    )

    # Override update_supplier to support image_url
    update_sup_props = {"id": {"type": "string", "description": "UUID of the object to update"}}
    for f in sup_writable:
        update_sup_props[f] = _sup_field_overrides.get(f, {"type": "string", "description": f})
    update_sup_props["image_url"] = {
        "type": "string",
        "description": "Public URL of an image to use as the supplier logo (PNG, JPG, WebP, etc.). "
                       "The image is downloaded, resized to 128x128, and size variants are generated.",
    }
    server.register_tool(
        "update_supplier",
        "Update an existing supplier. Optionally provide 'image_url' (a public URL pointing to "
        "an image file) to set or replace the supplier logo. The image will be downloaded, "
        "resized to 128x128, and 64x64, 32x32, 16x16 variants will be generated automatically. "
        "Prefer 'image_url' over 'update_supplier_logo' when the logo is available as a URL.",
        _obj_schema(update_sup_props, ["id"]),
        require_perm("assets.supplier.update")(
            _update_supplier_with_logo_handler(Supplier, sup_writable)
        ),
    )

    sd_fields = ["id", "reference", "support_asset_id", "support_asset_name",
                 "supplier_id", "supplier_name", "dependency_type",
                 "criticality", "description",
                 "is_single_point_of_failure", "redundancy_level",
                 "created_at"]
    sd_writable = ["support_asset_id", "supplier_id", "dependency_type",
                   "criticality", "description", "redundancy_level"]

    _register_crud(server, "supplier_dependency", SupplierDependency, "assets.supplier_dependency",
                   list_fields=sd_fields,
                   writable_fields=sd_writable,
                   search_fields=["description"],
                   filters=["support_asset_id", "supplier_id", "dependency_type", "criticality"],
                   scope_filtered=False,
                   required_fields=["support_asset_id", "supplier_id", "dependency_type", "criticality"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "dependency_type": {
                           "type": "string",
                           "description": "Type of supplier dependency.",
                           "enum": [
                               "provides", "hosts", "manages",
                               "develops", "supports", "licenses", "maintains", "other",
                           ],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "redundancy_level": {
                           "type": "string",
                           "description": "Redundancy level (operator-set).",
                           "enum": ["none", "partial", "full"],
                       },
                   })

    # Supplier sub-processors (sous-délégataires): a supplier -> subprocessor link
    ssp_fields = ["id", "reference", "supplier_id", "supplier_name",
                  "subprocessor_id", "subprocessor_name",
                  "purpose", "criticality", "status",
                  "start_date", "end_date", "description", "created_at"]
    ssp_writable = ["supplier_id", "subprocessor_id", "purpose",
                    "criticality", "status", "start_date", "end_date", "description"]

    _register_crud(server, "supplier_subprocessor", SupplierSubprocessor,
                   "assets.supplier",
                   list_fields=ssp_fields,
                   writable_fields=ssp_writable,
                   search_fields=["reference", "purpose", "supplier__name",
                                  "subprocessor__name"],
                   filters=["supplier_id", "subprocessor_id", "criticality", "status"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["supplier_id", "subprocessor_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "supplier_id": {
                           "type": "string",
                           "description": "UUID of the supplier (délégataire) engaging the "
                                          "sub-processor. Use list_suppliers to get valid IDs.",
                       },
                       "subprocessor_id": {
                           "type": "string",
                           "description": "UUID of the supplier engaged as a sub-processor "
                                          "(must differ from supplier_id).",
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality of the sub-processing engagement.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Status of the sub-processing engagement.",
                           "enum": ["active", "suspended", "terminated"],
                       },
                   })

    # Site-asset dependencies (has approve)
    sad_fields = ["id", "reference", "support_asset_id", "site_id", "dependency_type",
                  "criticality", "description", "is_single_point_of_failure",
                  "redundancy_level", "created_at"]
    sad_writable = ["support_asset_id", "site_id", "dependency_type", "criticality",
                    "description", "redundancy_level"]

    _register_crud(server, "site_asset_dependency", SiteAssetDependency, "assets.dependency",
                   list_fields=sad_fields,
                   writable_fields=sad_writable,
                   search_fields=["description"],
                   filters=["support_asset_id", "site_id", "dependency_type", "criticality"],
                   scope_filtered=False,
                   required_fields=["support_asset_id", "site_id", "dependency_type", "criticality"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "dependency_type": {
                           "type": "string",
                           "description": "Type of site-asset dependency.",
                           "enum": ["located_at", "hosted_at", "deployed_at", "other"],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "redundancy_level": {
                           "type": "string",
                           "description": "Redundancy level.",
                           "enum": ["none", "partial", "full"],
                       },
                   })

    # Site-supplier dependencies (has approve)
    ssd_fields = ["id", "reference", "site_id", "site_name", "supplier_id", "supplier_name",
                  "dependency_type",
                  "criticality", "description", "is_single_point_of_failure",
                  "redundancy_level", "created_at"]
    ssd_writable = ["site_id", "supplier_id", "dependency_type", "criticality",
                    "description", "redundancy_level"]

    _register_crud(server, "site_supplier_dependency", SiteSupplierDependency,
                   "assets.supplier_dependency",
                   list_fields=ssd_fields,
                   writable_fields=ssd_writable,
                   search_fields=["description"],
                   filters=["site_id", "supplier_id", "dependency_type", "criticality"],
                   scope_filtered=False,
                   required_fields=["site_id", "supplier_id", "dependency_type", "criticality"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "dependency_type": {
                           "type": "string",
                           "description": "Type of site-supplier dependency.",
                           "enum": ["provides", "hosts", "manages", "develops", "supports", "licenses", "maintains", "other"],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "redundancy_level": {
                           "type": "string",
                           "description": "Redundancy level.",
                           "enum": ["none", "partial", "full"],
                       },
                   })

    # Asset valuations (no approve)
    av_fields = ["id", "essential_asset_id", "evaluation_date",
                 "confidentiality_level", "integrity_level", "availability_level",
                 "evaluated_by_id", "justification", "context", "created_at"]
    av_writable = ["essential_asset_id", "evaluation_date",
                   "confidentiality_level", "integrity_level", "availability_level",
                   "evaluated_by_id", "justification", "context"]

    _register_crud(server, "asset_valuation", AssetValuation,
                   "assets.essential_asset",
                   list_fields=av_fields,
                   writable_fields=av_writable,
                   search_fields=["justification"],
                   filters=["essential_asset_id"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["essential_asset_id"],
                   field_overrides={
                       "justification": _html_field("Justification"),
                       "context": _html_field("Context"),
                       "confidentiality_level": {
                           "type": "integer",
                           "description": "Confidentiality level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical).",
                           "enum": [0, 1, 2, 3, 4],
                       },
                       "integrity_level": {
                           "type": "integer",
                           "description": "Integrity level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical).",
                           "enum": [0, 1, 2, 3, 4],
                       },
                       "availability_level": {
                           "type": "integer",
                           "description": "Availability level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical).",
                           "enum": [0, 1, 2, 3, 4],
                       },
                       "evaluation_date": {"type": "string", "description": "Evaluation date (ISO 8601, e.g. 2025-01-15)"},
                       "evaluated_by_id": {"type": "string", "description": "UUID of the evaluator (user)"},
                   })

    # Supplier types (config, no approve)
    st_fields = ["id", "reference", "name", "description", "created_at"]
    st_writable = ["name", "description"]

    _register_crud(server, "supplier_type", SupplierType, "assets.config",
                   list_fields=st_fields,
                   writable_fields=st_writable,
                   search_fields=["name", "description"],
                   filters=[],
                   scope_filtered=False,
                   has_approve=False,
                   field_overrides=_HTML_DESC)

    # Supplier type requirements (config, no approve)
    str_fields = ["id", "supplier_type_id", "title", "description", "created_at"]
    str_writable = ["supplier_type_id", "title", "description"]

    _register_crud(server, "supplier_type_requirement", SupplierTypeRequirement,
                   "assets.config",
                   list_fields=str_fields,
                   writable_fields=str_writable,
                   search_fields=["title", "description"],
                   filters=["supplier_type_id"],
                   scope_filtered=False,
                   has_approve=False,
                   field_overrides=_HTML_DESC)

    # Supplier requirements (no approve)
    sr_fields = ["id", "supplier_id", "source_type_requirement_id", "requirement_id",
                 "title", "description", "compliance_status", "evidence",
                 "due_date", "verified_at", "verified_by_id", "created_at"]
    sr_writable = ["supplier_id", "source_type_requirement_id", "requirement_id",
                   "title", "description", "compliance_status", "evidence", "due_date"]

    _register_crud(server, "supplier_requirement", SupplierRequirement,
                   "assets.supplier",
                   list_fields=sr_fields,
                   writable_fields=sr_writable,
                   search_fields=["title", "description"],
                   filters=["supplier_id", "compliance_status"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["supplier_id", "title"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "evidence": _html_field("Evidence"),
                       "compliance_status": {
                           "type": "string",
                           "description": "Compliance status of the supplier requirement.",
                           "enum": ["not_assessed", "compliant", "partially_compliant", "non_compliant"],
                       },
                   })

    # Supplier requirement reviews (no approve)
    srr_fields = ["id", "supplier_requirement_id", "review_date", "reviewer_id",
                  "result", "comment", "created_at"]
    srr_writable = ["supplier_requirement_id", "review_date", "reviewer_id",
                    "result", "comment"]

    _register_crud(server, "supplier_requirement_review", SupplierRequirementReview,
                   "assets.supplier",
                   list_fields=srr_fields,
                   writable_fields=srr_writable,
                   search_fields=["comment"],
                   filters=["supplier_requirement_id", "result"],
                   scope_filtered=False,
                   has_approve=False,
                   field_overrides={
                       "comment": _html_field("Comment"),
                   })

    # Supplier contacts (people attached to a supplier; no approve)
    sc_fields = ["id", "supplier_id", "name", "profession", "service",
                 "email", "phone", "role", "created_at", "updated_at"]
    sc_writable = ["supplier_id", "name", "profession", "service",
                   "email", "phone", "role"]

    _register_crud(server, "supplier_contact", SupplierContact,
                   "assets.supplier",
                   list_fields=sc_fields,
                   writable_fields=sc_writable,
                   search_fields=["name", "profession", "service", "email", "phone", "role"],
                   filters=["supplier_id", "role"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["supplier_id", "name"])


# ── Compliance Module ──────────────────────────────────────

def _register_compliance_tools(server):
    Framework = _get_model("compliance", "Framework")
    Section = _get_model("compliance", "Section")
    Requirement = _get_model("compliance", "Requirement")
    ComplianceAssessment = _get_model("compliance", "ComplianceAssessment")
    AssessmentResult = _get_model("compliance", "AssessmentResult")
    RequirementMapping = _get_model("compliance", "RequirementMapping")
    ComplianceActionPlan = _get_model("compliance", "ComplianceActionPlan")

    fw_fields = ["id", "reference", "scopes", "name", "short_name", "description", "type",
                 "category", "framework_version",
                 "publication_date", "effective_date", "expiry_date",
                 "issuing_body", "jurisdiction", "url",
                 "is_mandatory", "is_applicable", "applicability_justification",
                 "applicability_managed_by_risks",
                 "owner_id", "related_stakeholders",
                 "compliance_level", "last_assessment_date",
                 "status", "review_date", "logo_32",
                 "created_at"]
    fw_writable = ["name", "short_name", "description", "type", "category",
                   "framework_version",
                   "publication_date", "effective_date", "expiry_date",
                   "issuing_body", "jurisdiction", "url",
                   "is_mandatory", "is_applicable", "applicability_justification",
                   "applicability_managed_by_risks",
                   "status", "review_date", "owner_id", "logo",
                   "scope_ids", "related_stakeholder_ids"]

    _register_crud(server, "framework", Framework, "compliance.framework",
                   list_fields=fw_fields,
                   writable_fields=fw_writable,
                   search_fields=["reference", "name", "short_name", "description"],
                   filters=["type", "category", "status",
                            "is_mandatory", "is_applicable",
                            "applicability_managed_by_risks"],
                   required_fields=["name"],
                   m2m_fields={"scope_ids": "scopes",
                               "related_stakeholder_ids": "related_stakeholders"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "applicability_justification": _html_field("Applicability justification"),
                       "type": {
                           "type": "string",
                           "description": "Framework type.",
                           "enum": [
                               "standard", "law", "regulation", "contract",
                               "internal_policy", "industry_framework", "other",
                           ],
                       },
                       "category": {
                           "type": "string",
                           "description": "Framework category.",
                           "enum": [
                               "information_security", "privacy", "risk_management",
                               "business_continuity", "cloud_security", "sector_specific",
                               "it_governance", "quality", "contractual", "internal", "other",
                           ],
                       },
                       "status": {
                           "type": "string",
                           "description": "Framework status.",
                           "enum": ["draft", "active", "under_review", "deprecated", "archived"],
                       },
                       "framework_version": {"type": "string", "description": "Version of the framework (e.g. '2022')."},
                       "publication_date": {"type": "string", "description": "Publication date (ISO 8601)."},
                       "effective_date": {"type": "string", "description": "Effective date (ISO 8601)."},
                       "expiry_date": {"type": "string", "description": "Expiry date (ISO 8601)."},
                       "issuing_body": {"type": "string", "description": "Standards body or regulator that issued the framework."},
                       "jurisdiction": {"type": "string", "description": "Jurisdiction the framework applies to."},
                       "url": {"type": "string", "description": "Official link to the framework."},
                       "is_mandatory": {
                           "type": "boolean",
                           "description": "Whether the framework is mandatory (drives RC-05 non-compliance alert).",
                       },
                       "is_applicable": {
                           "type": "boolean",
                           "description": "Whether the framework applies to the organisation (drives Statement of Applicability inclusion).",
                       },
                       "applicability_managed_by_risks": {
                           "type": "boolean",
                           "description": (
                               "When true, each requirement's applicability is derived "
                               "automatically from its linked risks: applicable when at "
                               "least one active (reportable) risk is linked, not "
                               "applicable otherwise. The requirement fields "
                               "is_applicable / applicability_justification then become "
                               "read-only (writes are ignored)."
                           ),
                       },
                       "review_date": {"type": "string", "description": "Next review date (ISO 8601)."},
                       "owner_id": {"type": "string", "description": "UUID of the framework owner (user)"},
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this framework applies to (RG-01).",
                       },
                       "related_stakeholder_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Stakeholders interested in this framework.",
                       },
                   })

    # Framework compliance summary (special tool)
    @require_perm("compliance.framework.read")
    def framework_compliance_summary(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            framework = Framework.objects.get(pk=pk)
        except Framework.DoesNotExist:
            return _error("Framework not found.")
        sections = framework.sections.filter(parent_section__isnull=True)
        section_data = [{
            "id": str(s.id), "reference": s.reference,
            "name": s.name, "compliance_level": float(s.compliance_level),
        } for s in sections]
        reqs = framework.requirements.filter(is_applicable=True)
        by_status = {}
        for req in reqs.values("compliance_status"):
            st = req["compliance_status"]
            by_status[st] = by_status.get(st, 0) + 1
        return {
            "compliance_level": float(framework.compliance_level),
            "sections": section_data,
            "by_status": by_status,
            "total_requirements": reqs.count(),
        }

    server.register_tool(
        "get_framework_compliance_summary",
        "Get compliance summary for a framework, including section-level compliance and status distribution",
        _id_schema(),
        framework_compliance_summary,
    )

    sec_fields = ["id", "reference", "name", "description", "order", "compliance_level",
                  "framework_id", "parent_section_id", "created_at"]
    sec_writable = ["reference", "name", "description", "order",
                    "framework_id", "parent_section_id"]

    _register_crud(server, "section", Section, "compliance.section",
                   list_fields=sec_fields,
                   writable_fields=sec_writable,
                   search_fields=["reference", "name"],
                   filters=["framework_id", "parent_section_id"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["name", "framework_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "reference": {
                           "type": "string",
                           "description": (
                               "Section reference / number within the framework "
                               "(e.g. 'A.5', '6.1.2'). Auto-generated as SEC-N if omitted; "
                               "unique per framework when non-empty."
                           ),
                       },
                   })

    req_fields = ["id", "reference", "requirement_number", "name", "description",
                  "guidance", "type", "category",
                  "compliance_status", "compliance_level",
                  "compliance_evidence", "compliance_finding",
                  "priority", "is_applicable", "applicability_justification",
                  "target_date", "last_assessment_date", "last_assessed_by_id",
                  "owner_id", "status",
                  "framework_id", "section_id",
                  "linked_assets", "linked_stakeholder_expectations",
                  "created_at"]
    req_writable = ["requirement_number", "name", "description", "guidance", "type",
                    "category", "compliance_status", "compliance_level",
                    "priority", "is_applicable", "applicability_justification",
                    "compliance_evidence", "compliance_finding",
                    "target_date", "status",
                    "framework_id", "section_id", "owner_id",
                    "linked_asset_ids", "linked_stakeholder_expectation_ids"]

    _register_crud(server, "requirement", Requirement, "compliance.requirement",
                   list_fields=req_fields,
                   writable_fields=req_writable,
                   search_fields=["reference", "requirement_number", "name", "description"],
                   filters=["framework_id", "section_id", "requirement_number",
                            "compliance_status", "type", "category", "priority",
                            "is_applicable", "status"],
                   scope_filtered=False,
                   required_fields=["name", "description", "type", "framework_id"],
                   m2m_fields={
                       "linked_asset_ids": "linked_assets",
                       "linked_stakeholder_expectation_ids": "linked_stakeholder_expectations",
                   },
                   field_overrides={
                       "description": _html_field("Description"),
                       "guidance": _html_field("Implementation recommendations"),
                       "compliance_evidence": _html_field("Compliance evidence"),
                       "compliance_finding": _html_field("Finding"),
                       "applicability_justification": _html_field("Applicability justification"),
                       "type": {
                           "type": "string",
                           "description": "Requirement type.",
                           "enum": ["mandatory", "recommended", "optional"],
                       },
                       "category": {
                           "type": "string",
                           "description": "Requirement category.",
                           "enum": ["organizational", "technical", "physical",
                                    "legal", "human", "other"],
                       },
                       "compliance_status": {
                           "type": "string",
                           "description": "Compliance status.",
                           "enum": [
                               "not_assessed", "evaluated",
                               "non_compliant", "partially_compliant",
                               "major_non_conformity", "minor_non_conformity",
                               "observation", "improvement_opportunity",
                               "compliant", "strength", "not_applicable",
                           ],
                       },
                       "priority": {
                           "type": "string",
                           "description": "Priority level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Requirement lifecycle status.",
                           "enum": ["active", "deprecated", "superseded"],
                       },
                       "is_applicable": {
                           "type": "boolean",
                           "description": (
                               "Whether this requirement is applicable. Ignored when the "
                               "framework has applicability_managed_by_risks enabled: "
                               "applicability is then derived from linked risks."
                           ),
                       },
                       "target_date": {"type": "string", "description": "Target date for implementation (ISO 8601)."},
                       "owner_id": {"type": "string", "description": "UUID of the requirement owner (user)"},
                       "linked_asset_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Essential assets this requirement protects.",
                       },
                       "linked_stakeholder_expectation_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Stakeholder expectations satisfied by this requirement.",
                       },
                   })

    ca_fields = ["id", "reference", "scopes", "frameworks",
                 "name", "description", "limitations",
                 "assessment_start_date", "assessment_end_date", "status",
                 "assessor_id",
                 "overall_compliance_level", "total_requirements",
                 "compliant_count", "major_non_conformity_count",
                 "minor_non_conformity_count", "observation_count",
                 "improvement_opportunity_count", "strength_count",
                 "evaluated_count", "not_assessed_count", "not_applicable_count",
                 "created_at"]
    ca_writable = ["name", "description", "limitations",
                   "assessment_start_date", "assessment_end_date",
                   "status", "assessor_id"]

    # Use generic list/get/delete/approve for compliance_assessment
    ca_filter_props = {"status": {"type": "string", "description": "Filter by status"}}
    server.register_tool(
        "list_compliance_assessments",
        "List compliance assessments with optional search and filters",
        _list_schema(ca_filter_props),
        require_perm("compliance.assessment.read")(
            _list_handler(ComplianceAssessment, ca_fields, ["name", "description"], ["status"])
        ),
    )
    server.register_tool(
        "get_compliance_assessment",
        "Get a compliance assessment by ID",
        _id_schema(),
        require_perm("compliance.assessment.read")(
            _get_handler(ComplianceAssessment, ca_fields)
        ),
    )
    server.register_tool(
        "delete_compliance_assessment",
        "Delete a compliance assessment",
        _id_schema(),
        require_perm("compliance.assessment.delete")(
            _delete_handler(ComplianceAssessment)
        ),
    )

    # Custom create handler with framework_ids M2M support
    def _create_compliance_assessment(user, arguments):
        """Create a new compliance assessment, optionally linking frameworks.

        Parameters
        ----------
        name : str (required)
            Assessment name.
        description : str
            Context and objectives (HTML rich text).
        limitations : str
            Limitations (HTML rich text).
        assessment_start_date : str
            Start date (ISO 8601).
        assessment_end_date : str
            End date (ISO 8601).
        status : str
            Assessment status (draft, planned, in_progress, completed, closed).
        assessor_id : str
            UUID of the lead assessor.
        framework_ids : list[str]
            List of framework UUIDs to link. Assessment results will be
            automatically created for all requirements in these frameworks.
        """
        framework_ids = arguments.pop("framework_ids", None)
        scope_ids = arguments.pop("scope_ids", None)
        kwargs = {}
        for field_name in ca_writable:
            if field_name in arguments:
                target = _fk_kwarg_name(ComplianceAssessment, field_name)
                kwargs[target] = _coerce_field_value(
                    ComplianceAssessment, field_name, arguments[field_name])
        kwargs["created_by"] = user
        try:
            obj = ComplianceAssessment(**kwargs)
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        if framework_ids:
            frameworks = Framework.objects.filter(pk__in=framework_ids)
            if frameworks.count() != len(framework_ids):
                found = set(str(f.pk) for f in frameworks)
                missing = [fid for fid in framework_ids if fid not in found]
                return _error(f"Frameworks not found: {missing}")
            obj.frameworks.set(frameworks)
            obj.sync_results(user)
        if scope_ids:
            obj.scopes.set(scope_ids)
        fields = [f.name for f in ComplianceAssessment._meta.fields] + ["scopes", "frameworks"]
        return _serialize_obj(obj, fields)

    ca_create_props = {}
    for f in ca_writable:
        ca_create_props[f] = _HTML_DESC.get(f, {"type": "string", "description": f})
    ca_create_props["framework_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of framework UUIDs to link to this assessment",
    }
    ca_create_props["scope_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of scope UUIDs this assessment covers (RG-01).",
    }
    server.register_tool(
        "create_compliance_assessment",
        "Create a new compliance assessment",
        _obj_schema(ca_create_props),
        require_perm("compliance.assessment.create")(_create_compliance_assessment),
    )

    # Custom update handler with framework_ids M2M support
    def _update_compliance_assessment(user, arguments):
        """Update a compliance assessment, optionally changing linked frameworks.

        Parameters
        ----------
        id : str (required)
            UUID of the assessment to update.
        framework_ids : list[str]
            Replace the linked frameworks. Assessment results are
            automatically synced (created / removed) to match.

        All other writable fields (name, description, etc.) are optional.
        """
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = ComplianceAssessment.objects.get(pk=pk)
        except ComplianceAssessment.DoesNotExist:
            return _error("ComplianceAssessment not found.")
        qs = _filter_by_scopes(ComplianceAssessment.objects.filter(pk=pk), user)
        if not qs.exists():
            return _error("Access denied: object is outside your allowed scopes.")
        framework_ids = arguments.pop("framework_ids", None)
        scope_ids = arguments.pop("scope_ids", None)
        new_status = arguments.pop("status", None)
        changed_fields = set()
        for field_name in ca_writable:
            if field_name in arguments:
                target = _fk_kwarg_name(ComplianceAssessment, field_name)
                setattr(obj, target, _coerce_field_value(
                    ComplianceAssessment, field_name, arguments[field_name]))
                changed_fields.add(field_name)
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        # Use transition_to() for status changes to enforce workflow rules
        # and trigger side-effects (e.g. reset EVALUATED on COMPLETED)
        if new_status and new_status != obj.status:
            try:
                obj.transition_to(new_status)
            except ValueError as e:
                return _error(str(e))
        if framework_ids is not None:
            frameworks = Framework.objects.filter(pk__in=framework_ids)
            if frameworks.count() != len(framework_ids):
                found = set(str(f.pk) for f in frameworks)
                missing = [fid for fid in framework_ids if fid not in found]
                return _error(f"Frameworks not found: {missing}")
            obj.frameworks.set(frameworks)
            obj.sync_results(user)
        if scope_ids is not None:
            obj.scopes.set(scope_ids)
        fields = [f.name for f in ComplianceAssessment._meta.fields] + ["scopes", "frameworks"]
        return _serialize_obj(obj, fields)

    ca_update_props = {"id": {"type": "string", "description": "UUID of the assessment to update"}}
    for f in ca_writable:
        ca_update_props[f] = _HTML_DESC.get(f, {"type": "string", "description": f})
    ca_update_props["framework_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of framework UUIDs to link (replaces existing links)",
    }
    ca_update_props["scope_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of scope UUIDs (replaces existing scopes).",
    }
    server.register_tool(
        "update_compliance_assessment",
        "Update an existing compliance assessment",
        _obj_schema(ca_update_props, ["id"]),
        require_perm("compliance.assessment.update")(_update_compliance_assessment),
    )

    ar_fields = ["id", "assessment_id", "requirement_id", "compliance_status",
                 "compliance_level", "finding", "auditor_recommendations",
                 "evidence", "assessed_by_id", "assessed_at"]
    ar_writable = ["assessment_id", "requirement_id", "compliance_status",
                   "compliance_level", "finding", "auditor_recommendations",
                   "evidence", "assessed_by_id", "assessed_at"]
    ar_overrides = {
        "finding": _html_field("Finding"),
        "auditor_recommendations": _html_field("Auditor recommendations"),
        "evidence": _html_field("Evidence"),
        "assessed_by_id": {"type": "string", "description": "UUID of the assessor (user)"},
        "assessed_at": {"type": "string", "description": "Assessment date-time in ISO 8601 format (e.g. 2025-01-15T10:30:00Z)"},
        "compliance_status": {
            "type": "string",
            "description": (
                "Compliance status. Same 11-value enum as Requirement.compliance_status: "
                "the 5 conformance-oriented values (not_assessed, non_compliant, "
                "partially_compliant, compliant, not_applicable) plus the 6 audit-oriented "
                "values (evaluated, major_non_conformity, minor_non_conformity, observation, "
                "improvement_opportunity, strength). See docs/specs/m3-compliance/requirement.md "
                "for the audit -> conformance mapping used by RC-01 / RC-02 averages."
            ),
            "enum": [
                "not_assessed", "evaluated",
                "non_compliant", "partially_compliant",
                "major_non_conformity", "minor_non_conformity",
                "observation", "improvement_opportunity",
                "compliant", "strength",
                "not_applicable",
            ],
        },
    }

    # List and get use generic handlers (no side-effects needed)
    ar_filter_props = {
        "assessment_id": {"type": "string", "description": "Filter by assessment_id"},
        "requirement_id": {"type": "string", "description": "Filter by requirement_id"},
        "compliance_status": {"type": "string", "description": "Filter by compliance_status"},
    }
    server.register_tool(
        "list_assessment_results",
        "List assessment results with optional search and filters",
        _list_schema(ar_filter_props),
        require_perm("compliance.assessment.read")(
            _list_handler(AssessmentResult, ar_fields, [],
                          ["assessment_id", "requirement_id", "compliance_status"],
                          scope_filtered=False)
        ),
    )
    server.register_tool(
        "get_assessment_result",
        "Get an assessment result by ID",
        _id_schema(),
        require_perm("compliance.assessment.read")(
            _get_handler(AssessmentResult, ar_fields, scope_filtered=False)
        ),
    )

    # Custom create with recalculate_counts()
    def _create_assessment_result(user, arguments):
        kwargs = {}
        for field_name in ar_writable:
            if field_name in arguments:
                kwargs[field_name] = _coerce_field_value(
                    AssessmentResult, field_name, arguments[field_name])
        try:
            obj = AssessmentResult(**kwargs)
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        obj.assessment.recalculate_counts()
        return _serialize_obj(obj, ar_fields)

    ar_create_props = {}
    for f in ar_writable:
        ar_create_props[f] = ar_overrides.get(f, {"type": "string", "description": f})
    server.register_tool(
        "create_assessment_result",
        "Create a new assessment result",
        _obj_schema(ar_create_props),
        require_perm("compliance.assessment.create")(_create_assessment_result),
    )

    # Custom update with recalculate_counts()
    def _update_assessment_result(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = AssessmentResult.objects.get(pk=pk)
        except AssessmentResult.DoesNotExist:
            return _error("AssessmentResult not found.")
        for field_name in ar_writable:
            if field_name in arguments:
                setattr(obj, field_name, _coerce_field_value(
                    AssessmentResult, field_name, arguments[field_name]))
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        obj.assessment.recalculate_counts()
        return _serialize_obj(obj, ar_fields)

    ar_update_props = {"id": {"type": "string", "description": "UUID of the result to update"}}
    for f in ar_writable:
        ar_update_props[f] = ar_overrides.get(f, {"type": "string", "description": f})
    server.register_tool(
        "update_assessment_result",
        "Update an existing assessment result",
        _obj_schema(ar_update_props, ["id"]),
        require_perm("compliance.assessment.update")(_update_assessment_result),
    )

    # Custom delete with recalculate_counts()
    def _delete_assessment_result(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = AssessmentResult.objects.get(pk=pk)
        except AssessmentResult.DoesNotExist:
            return _error("AssessmentResult not found.")
        assessment = obj.assessment
        obj.delete()
        assessment.recalculate_counts()
        return {"deleted": True, "id": str(pk)}

    server.register_tool(
        "delete_assessment_result",
        "Delete an assessment result",
        _id_schema(),
        require_perm("compliance.assessment.delete")(_delete_assessment_result),
    )

    rm_fields = ["id", "source_requirement_id", "target_requirement_id",
                 "mapping_type", "coverage_level", "description", "created_at"]
    rm_writable = ["source_requirement_id", "target_requirement_id",
                   "mapping_type", "coverage_level", "description", "justification"]

    _register_crud(server, "requirement_mapping", RequirementMapping, "compliance.mapping",
                   list_fields=rm_fields,
                   writable_fields=rm_writable,
                   search_fields=["description"],
                   filters=["source_requirement_id", "target_requirement_id", "mapping_type"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["source_requirement_id", "target_requirement_id", "mapping_type"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "justification": _html_field("Justification"),
                       "mapping_type": {
                           "type": "string",
                           "description": "Type of mapping between requirements.",
                           "enum": ["equivalent", "partial_overlap", "includes", "included_by", "related"],
                       },
                       "coverage_level": {
                           "type": "string",
                           "description": "Coverage level of the mapping.",
                           "enum": ["full", "partial", "minimal"],
                       },
                   })

    ap_fields = ["id", "reference", "scopes", "name", "description",
                 "gap_description", "remediation_plan",
                 "priority", "status", "is_overdue",
                 "start_date", "target_date", "completion_date",
                 "cost_estimate", "progress_percentage",
                 "owner_id", "assignees", "requirements", "findings", "risks",
                 "originating_review_id",
                 "created_at"]
    ap_writable = ["name", "description", "gap_description", "remediation_plan",
                   "priority", "start_date", "target_date", "completion_date",
                   "cost_estimate", "progress_percentage", "owner_id",
                   "originating_review_id",
                   "scope_ids", "assignee_ids", "requirement_ids",
                   "finding_ids", "risk_ids"]

    _register_crud(server, "action_plan", ComplianceActionPlan, "compliance.action_plan",
                   list_fields=ap_fields,
                   writable_fields=ap_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "priority"],
                   required_fields=["name", "gap_description", "remediation_plan",
                                    "priority", "target_date", "owner_id"],
                   m2m_fields={
                       "scope_ids": "scopes",
                       "assignee_ids": "assignees",
                       "requirement_ids": "requirements",
                       "finding_ids": "findings",
                       "risk_ids": "risks",
                   },
                   field_overrides={
                       "description": _html_field("Description"),
                       "gap_description": _html_field("Gap description"),
                       "remediation_plan": _html_field("Remediation plan"),
                       "priority": {
                           "type": "string",
                           "description": "Priority level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "status": {
                           "type": "string",
                           "description": (
                               "Action plan status. Use action_plan_transition tool to change status "
                               "through the workflow instead of setting directly."
                           ),
                           "enum": [
                               "new", "to_define", "to_validate", "to_implement",
                               "implementation_to_validate", "validated", "closed", "cancelled",
                           ],
                       },
                       "owner_id": {"type": "string", "description": "UUID of the action plan owner (user)"},
                       "originating_review_id": {"type": "string", "description": "UUID of the management review that spawned this plan (optional)."},
                       "start_date": {"type": "string", "description": "Start date (ISO 8601)."},
                       "target_date": {"type": "string", "description": "Target completion date (ISO 8601, e.g. 2025-12-31)"},
                       "completion_date": {"type": "string", "description": "Actual completion date (ISO 8601). Auto-set when transitioning to CLOSED."},
                       "cost_estimate": {"type": "number", "description": "Estimated cost of the action plan."},
                       "progress_percentage": {"type": "integer", "description": "Progress percentage (0-100)"},
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this plan applies to.",
                       },
                       "assignee_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "UUIDs of assignees (users) for this plan.",
                       },
                       "requirement_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Compliance requirements this plan addresses.",
                       },
                       "finding_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Audit findings this plan addresses.",
                       },
                       "risk_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Risks this plan helps mitigate.",
                       },
                   })

    # Action plan transition tool
    def _action_plan_transition(user, arguments):
        """Transition an action plan to a new status in the Kanban workflow.

        Workflow (forward):
          new → to_define → to_validate → to_implement
          → implementation_to_validate → validated → closed

        Refusals (backward, comment mandatory):
          to_validate → to_define
          implementation_to_validate → to_implement

        Cancellation (comment recommended):
          Any status except closed/cancelled → cancelled

        Parameters
        ----------
        action_plan_id : str (required)
            UUID of the action plan.
        target_status : str (required)
            Target status. Must be an allowed transition from the current
            status. Use action_plan_allowed_transitions to check first.
        comment : str
            Comment explaining the transition. Mandatory for refusals
            (backward transitions). Recommended for cancellations.
        """
        from compliance.constants import (
            ACTION_PLAN_TRANSITION_PERMISSIONS,
            ActionPlanStatus,
        )

        pk = arguments.get("action_plan_id")
        target = arguments.get("target_status")
        comment = arguments.get("comment", "")
        if not pk or not target:
            raise InvalidParamsError("action_plan_id and target_status are required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            return _error("Action plan not found.")

        # Check per-transition permission (same logic as the UI view)
        transition_key = (ap.status, target)
        if target == ActionPlanStatus.CANCELLED:
            required_perm = "compliance.action_plan.cancel"
        else:
            required_perm = ACTION_PLAN_TRANSITION_PERMISSIONS.get(transition_key)
        if required_perm and not user.is_superuser and not user.has_perm(required_perm):
            return _error(
                f"Permission denied: you need '{required_perm}' to transition "
                f"from '{ap.status}' to '{target}'."
            )

        # Build helpful error context on failure
        allowed = ap.get_allowed_transitions()
        if target not in allowed:
            allowed_str = ", ".join(str(s) for s in allowed) if allowed else "none (terminal status)"
            return _error(
                f"Cannot transition from '{ap.status}' to '{target}'. "
                f"Allowed transitions from '{ap.status}': {allowed_str}."
            )

        try:
            ap.transition_to(target, user, comment)
        except ValueError as e:
            return _error(str(e))
        return {"id": str(ap.pk), "status": ap.status, "reference": ap.reference}

    server.register_tool(
        "action_plan_transition",
        "Transition an action plan to a new Kanban status. "
        "Forward flow: new → to_define → to_validate → to_implement → "
        "implementation_to_validate → validated → closed. "
        "Refusals (require comment): to_validate → to_define, "
        "implementation_to_validate → to_implement. "
        "Cancellation: any non-terminal status → cancelled.",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
            "target_status": {
                "type": "string",
                "description": "Target status to transition to",
                "enum": ["new", "to_define", "to_validate", "to_implement",
                         "implementation_to_validate", "validated", "closed", "cancelled"],
            },
            "comment": {"type": "string", "description": "Comment explaining the transition. Mandatory for refusals (backward transitions). Recommended for cancellations."},
        }, ["action_plan_id", "target_status"]),
        require_perm("compliance.action_plan.update")(_action_plan_transition),
    )

    # Action plan transition history tool
    def _action_plan_transitions(user, arguments):
        """List transition history for an action plan."""
        pk = arguments.get("action_plan_id")
        if not pk:
            raise InvalidParamsError("action_plan_id is required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            return _error("Action plan not found.")
        transitions = ap.transitions.select_related("performed_by").all()[:50]
        return [
            {
                "id": str(t.pk),
                "from_status": t.from_status,
                "to_status": t.to_status,
                "performed_by": t.performed_by.display_name,
                "comment": t.comment,
                "is_refusal": t.is_refusal,
                "created_at": t.created_at.isoformat(),
            }
            for t in transitions
        ]

    server.register_tool(
        "action_plan_transitions",
        "List transition history for an action plan",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
        }, ["action_plan_id"]),
        require_perm("compliance.action_plan.read")(_action_plan_transitions),
    )

    # Action plan kanban tool
    def _action_plan_kanban(user, arguments):
        """Get action plans grouped by status for kanban view.

        Returns a dict with:
        - columns: action plans grouped by status
        - workflow_rules: allowed transitions, refusals, and cancellable statuses
        """
        from compliance.constants import (
            ACTION_PLAN_TRANSITIONS,
            ACTION_PLAN_REFUSAL_TRANSITIONS,
            ACTION_PLAN_CANCELLABLE_STATUSES,
            ActionPlanStatus as APS,
        )
        qs = ComplianceActionPlan.objects.all()
        columns = {}
        for status_choice in APS:
            plans = qs.filter(workflow_state=status_choice.value)
            columns[status_choice.value] = [
                {"id": str(p.pk), "reference": p.reference, "name": p.name,
                 "priority": p.priority, "status": p.status,
                 "owner": str(p.owner) if p.owner_id else "",
                 "assignees": [
                     {"id": str(u.pk), "name": u.display_name}
                     for u in p.assignees.all()
                 ],
                 "target_date": str(p.target_date) if p.target_date else "",
                 "progress_percentage": p.progress_percentage,
                 "is_overdue": p.is_overdue}
                for p in plans
            ]
        # Build workflow rules so LLM knows which transitions are valid
        transitions = {}
        for from_s, to_list in ACTION_PLAN_TRANSITIONS.items():
            key = from_s.value if hasattr(from_s, "value") else from_s
            targets = [s.value if hasattr(s, "value") else s for s in to_list]
            # Add cancellation if applicable
            if from_s in ACTION_PLAN_CANCELLABLE_STATUSES:
                targets.append(APS.CANCELLED.value)
            transitions[key] = targets
        refusals = {
            (from_s.value if hasattr(from_s, "value") else from_s): (
                to_s.value if hasattr(to_s, "value") else to_s
            )
            for from_s, to_s in ACTION_PLAN_REFUSAL_TRANSITIONS.items()
        }
        return {
            "columns": columns,
            "workflow_rules": {
                "allowed_transitions": transitions,
                "refusal_transitions": refusals,
                "refusal_transitions_require_comment": True,
            },
        }

    server.register_tool(
        "action_plan_kanban",
        "Get action plans grouped by status for kanban board, "
        "including workflow transition rules",
        _obj_schema({}, []),
        require_perm("compliance.action_plan.read")(_action_plan_kanban),
    )

    # Unified To do / Doing / Done board across modules
    def _kanban_board(user, arguments):
        """Get the unified To do / Doing / Done board.

        Aggregates action plans, treatment actions, audits (compliance
        assessments) and risk assessments into three columns. Only the entity
        types the user is allowed to read are included, and cancelled / archived
        items are omitted. The board is read-only.
        """
        from core.kanban import build_kanban_columns, serialize_card

        columns = build_kanban_columns(user)
        return {
            "columns": [
                {
                    "key": col["key"],
                    "label": col["label"],
                    "count": col["count"],
                    "cards": [serialize_card(c) for c in col["cards"]],
                }
                for col in columns
            ]
        }

    server.register_tool(
        "kanban_board",
        "Get the unified To do / Doing / Done board aggregating action plans, "
        "treatment actions, audits and risk assessments (read-only)",
        _obj_schema({}, []),
        _kanban_board,
    )

    # Action plan allowed transitions tool
    def _action_plan_allowed_transitions(user, arguments):
        """Get the list of allowed transitions for a specific action plan.

        Returns the current status, allowed target statuses, which ones
        are refusals (require comment), and which is cancellation.
        Useful to check before calling action_plan_transition.
        """
        from compliance.constants import (
            ACTION_PLAN_REFUSAL_TRANSITIONS,
            ACTION_PLAN_TRANSITION_PERMISSIONS,
            ActionPlanStatus,
        )
        pk = arguments.get("action_plan_id")
        if not pk:
            raise InvalidParamsError("action_plan_id is required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            return _error("Action plan not found.")

        allowed = ap.get_allowed_transitions()
        transitions = []
        for target in allowed:
            target_val = target.value if hasattr(target, "value") else target
            transition_key = (ap.status, target_val)
            if target_val == ActionPlanStatus.CANCELLED:
                perm = "compliance.action_plan.cancel"
            else:
                perm = ACTION_PLAN_TRANSITION_PERMISSIONS.get(transition_key)
            has_perm = user.is_superuser or not perm or user.has_perm(perm)
            is_refusal = ACTION_PLAN_REFUSAL_TRANSITIONS.get(ap.status) == target
            transitions.append({
                "target_status": target_val,
                "label": ActionPlanStatus(target_val).label,
                "is_refusal": is_refusal,
                "is_cancellation": target_val == ActionPlanStatus.CANCELLED,
                "comment_required": is_refusal,
                "required_permission": perm or None,
                "user_has_permission": has_perm,
            })
        return {
            "action_plan_id": str(ap.pk),
            "reference": ap.reference,
            "current_status": ap.status,
            "allowed_transitions": transitions,
        }

    server.register_tool(
        "action_plan_allowed_transitions",
        "Get allowed status transitions for an action plan, "
        "including permission checks and refusal/cancellation flags. "
        "Call this before action_plan_transition to know what is possible.",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
        }, ["action_plan_id"]),
        require_perm("compliance.action_plan.read")(_action_plan_allowed_transitions),
    )

    # ── Action Plan Comments ──
    ActionPlanComment = _get_model("compliance", "ActionPlanComment")

    @require_perm("compliance.action_plan.read")
    def _list_action_plan_comments(user, arguments):
        """List comments on an action plan, including threaded replies."""
        pk = arguments.get("action_plan_id")
        if not pk:
            raise InvalidParamsError("action_plan_id is required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            raise InvalidParamsError("Action plan not found.")
        comments = (
            ap.comments.filter(parent__isnull=True)
            .select_related("author")
            .prefetch_related("replies__author")
        )
        result = []
        for c in comments:
            entry = {
                "id": str(c.id),
                "author": c.author.display_name,
                "content": c.content,
                "created_at": c.created_at.isoformat(),
                "replies": [
                    {
                        "id": str(r.id),
                        "author": r.author.display_name,
                        "content": r.content,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in c.replies.all()
                ],
            }
            result.append(entry)
        return result

    server.register_tool(
        "list_action_plan_comments",
        "List comments on an action plan with threaded replies",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
        }, ["action_plan_id"]),
        _list_action_plan_comments,
    )

    @require_perm("compliance.action_plan.update")
    def _create_action_plan_comment(user, arguments):
        """Create a comment or reply on an action plan."""
        pk = arguments.get("action_plan_id")
        content = arguments.get("content")
        if not pk or not content:
            raise InvalidParamsError("action_plan_id and content are required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            raise InvalidParamsError("Action plan not found.")

        parent = None
        parent_id = arguments.get("parent_id")
        if parent_id:
            try:
                parent = ActionPlanComment.objects.get(pk=parent_id, action_plan=ap)
            except ActionPlanComment.DoesNotExist:
                raise InvalidParamsError("Parent comment not found.")
            if parent.parent_id is not None:
                parent = parent.parent

        comment = ActionPlanComment.objects.create(
            action_plan=ap,
            author=user,
            content=content,
            parent=parent,
        )
        return {
            "id": str(comment.id),
            "author": user.display_name,
            "content": comment.content,
            "parent_id": str(parent.id) if parent else None,
            "created_at": comment.created_at.isoformat(),
        }

    server.register_tool(
        "create_action_plan_comment",
        "Create a comment or reply on an action plan",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
            "content": {"type": "string", "description": "Comment text"},
            "parent_id": {"type": "string", "description": "UUID of parent comment (for replies, optional)"},
        }, ["action_plan_id", "content"]),
        _create_action_plan_comment,
    )

    Finding = _get_model("compliance", "Finding")
    fi_fields = ["id", "reference", "assessment_id", "assessment_name", "source",
                 "finding_type",
                 "description", "recommendation", "evidence",
                 "assessor_id", "assessor_name",
                 "effectiveness_reviewed_at", "effectiveness_reviewed_by_id",
                 "effectiveness_reviewed_by_name", "effectiveness_verdict",
                 "created_at"]
    fi_writable = ["assessment_id", "source", "finding_type", "description",
                   "recommendation", "evidence", "assessor_id",
                   "effectiveness_reviewed_at", "effectiveness_reviewed_by_id",
                   "effectiveness_verdict"]

    fi_field_overrides = {
        "description": _html_field("Finding description"),
        "recommendation": _html_field("Recommendation"),
        "evidence": _html_field("Evidence presented"),
        "assessor_id": {
            "type": "string",
            "description": (
                "UUID of the user who raised the nonconformity. Required when "
                "source is 'audit', optional otherwise."
            ),
        },
        "source": {
            "type": "string",
            "description": (
                "What surfaced the nonconformity. 'audit' additionally requires "
                "assessment_id and assessor_id."
            ),
            "enum": ["audit", "incident", "management_review", "monitoring", "complaint"],
        },
        "effectiveness_verdict": {
            "type": "string",
            "description": (
                "ISO 27001 clause 10.2 d) : whether the corrective action worked. "
                "Requires effectiveness_reviewed_at."
            ),
            "enum": ["effective", "partially_effective", "not_effective"],
        },
        "finding_type": {
            "type": "string",
            "description": (
                "Type of finding. Allowed values: "
                "major_nc (Major non-conformity, ref NCMAJ-x), "
                "minor_nc (Minor non-conformity, ref NCMIN-x), "
                "observation (Observation, ref OBS-x), "
                "improvement (Improvement opportunity, ref OA-x), "
                "strength (Strength, ref STR-x)"
            ),
            "enum": ["major_nc", "minor_nc", "observation", "improvement", "strength"],
        },
    }

    # Use generic list/get/delete for finding
    fi_filter_props = {
        "assessment_id": {"type": "string", "description": "Filter by assessment_id"},
        "finding_type": {"type": "string", "description": "Filter by finding_type"},
        "source": {"type": "string", "description": "Filter by source"},
        "effectiveness_verdict": {
            "type": "string", "description": "Filter by effectiveness_verdict"
        },
    }
    server.register_tool(
        "list_findings",
        "List findings with optional search and filters",
        _list_schema(fi_filter_props),
        require_perm("compliance.finding.read")(
            _list_handler(Finding, fi_fields, ["reference", "description"],
                          ["assessment_id", "finding_type", "source",
                           "effectiveness_verdict"], scope_filtered=True)
        ),
    )
    server.register_tool(
        "get_finding",
        "Get a finding by ID",
        _id_schema(),
        require_perm("compliance.finding.read")(
            _get_handler(Finding, fi_fields, scope_filtered=True)
        ),
    )
    def _delete_finding(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = Finding.objects.get(pk=pk)
        except Finding.DoesNotExist:
            return _error("Finding not found.")
        assessment = obj.assessment
        obj.delete()
        assessment.apply_findings_to_results()
        return {"deleted": True, "id": str(pk)}

    server.register_tool(
        "delete_finding",
        "Delete a finding",
        _id_schema(),
        require_perm("compliance.finding.delete")(_delete_finding),
    )

    # Custom create handler with requirement_ids M2M support
    def _create_finding(user, arguments):
        """Create an audit finding, optionally linking requirements.

        Parameters
        ----------
        assessment_id : str (required)
            UUID of the compliance assessment.
        finding_type : str (required)
            Type of finding: major_nc, minor_nc, observation, improvement, strength.
        description : str (required)
            Finding description (HTML rich text).
        recommendation : str
            Auditor recommendation (HTML rich text).
        evidence : str
            Evidence presented (HTML rich text).
        assessor_id : str
            UUID of the assessor (user).
        requirement_ids : list[str]
            List of requirement UUIDs to link to this finding.
        """
        requirement_ids = arguments.pop("requirement_ids", None)
        kwargs = {}
        for field_name in fi_writable:
            if field_name in arguments:
                kwargs[field_name] = _coerce_field_value(
                    Finding, field_name, arguments[field_name])
        kwargs["created_by"] = user
        try:
            obj = Finding(**kwargs)
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        if requirement_ids:
            reqs = Requirement.objects.filter(pk__in=requirement_ids)
            if reqs.count() != len(requirement_ids):
                found = set(str(r.pk) for r in reqs)
                missing = [rid for rid in requirement_ids if rid not in found]
                return _error(f"Requirements not found: {missing}")
            obj.requirements.set(reqs)
        # Propagate finding to assessment results and recalculate counts
        obj.assessment.apply_findings_to_results()
        fields = [f.name for f in Finding._meta.fields]
        return _serialize_obj(obj, fields)

    fi_create_props = {}
    for f in fi_writable:
        fi_create_props[f] = fi_field_overrides.get(f, {"type": "string", "description": f})
    fi_create_props["requirement_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of requirement UUIDs to link to this finding",
    }
    server.register_tool(
        "create_finding",
        "Create a new audit finding",
        _obj_schema(fi_create_props),
        require_perm("compliance.finding.create")(_create_finding),
    )

    # Custom update handler with requirement_ids M2M support
    def _update_finding(user, arguments):
        """Update an audit finding, optionally changing linked requirements.

        Parameters
        ----------
        id : str (required)
            UUID of the finding to update.
        requirement_ids : list[str]
            Replace the linked requirements (pass empty list to clear).

        All other writable fields are optional.
        """
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = Finding.objects.get(pk=pk)
        except Finding.DoesNotExist:
            return _error("Finding not found.")
        requirement_ids = arguments.pop("requirement_ids", None)
        changed_fields = set()
        for field_name in fi_writable:
            if field_name in arguments:
                setattr(obj, field_name, _coerce_field_value(
                    Finding, field_name, arguments[field_name]))
                changed_fields.add(field_name)
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        if requirement_ids is not None:
            reqs = Requirement.objects.filter(pk__in=requirement_ids)
            if requirement_ids and reqs.count() != len(requirement_ids):
                found = set(str(r.pk) for r in reqs)
                missing = [rid for rid in requirement_ids if rid not in found]
                return _error(f"Requirements not found: {missing}")
            obj.requirements.set(reqs)
        # Propagate finding changes to assessment results and recalculate counts
        obj.assessment.apply_findings_to_results()
        fields = [f.name for f in Finding._meta.fields]
        return _serialize_obj(obj, fields)

    fi_update_props = {"id": {"type": "string", "description": "UUID of the finding to update"}}
    for f in fi_writable:
        fi_update_props[f] = fi_field_overrides.get(f, {"type": "string", "description": f})
    fi_update_props["requirement_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of requirement UUIDs to link (replaces existing links)",
    }
    server.register_tool(
        "update_finding",
        "Update an existing audit finding",
        _obj_schema(fi_update_props, ["id"]),
        require_perm("compliance.finding.update")(_update_finding),
    )


# ── Risks Module ───────────────────────────────────────────

def _register_risks_tools(server):
    RiskAssessment = _get_model("risks", "RiskAssessment")
    RiskCriteria = _get_model("risks", "RiskCriteria")
    ScaleLevel = _get_model("risks", "ScaleLevel")
    RiskLevel = _get_model("risks", "RiskLevel")
    Risk = _get_model("risks", "Risk")
    RiskTreatmentPlan = _get_model("risks", "RiskTreatmentPlan")
    TreatmentAction = _get_model("risks", "TreatmentAction")
    RiskAcceptance = _get_model("risks", "RiskAcceptance")
    Threat = _get_model("risks", "Threat")
    Vulnerability = _get_model("risks", "Vulnerability")
    ISO27005Risk = _get_model("risks", "ISO27005Risk")

    ra_fields = ["id", "reference", "scopes", "name", "description", "methodology",
                 "status", "assessment_date", "next_review_date",
                 "risk_criteria_id", "assessor_id",
                 "validated_by_id", "validated_at", "summary",
                 "created_at"]
    ra_writable = ["name", "description", "methodology", "status",
                   "assessment_date", "next_review_date",
                   "risk_criteria_id", "assessor_id", "summary",
                   "scope_ids"]

    _register_crud(server, "risk_assessment", RiskAssessment, "risks.assessment",
                   list_fields=ra_fields,
                   writable_fields=ra_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "methodology"],
                   required_fields=["name"],
                   m2m_fields={"scope_ids": "scopes"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "summary": _html_field("Summary"),
                       "methodology": {
                           "type": "string",
                           "description": "Risk assessment methodology. Default: iso27005.",
                           "enum": ["iso27005", "ebios_rm"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Risk assessment status.",
                           "enum": ["draft", "in_progress", "completed", "validated", "archived"],
                       },
                       "assessment_date": {"type": "string", "description": "Assessment date (ISO 8601, e.g. 2025-06-15)"},
                       "next_review_date": {"type": "string", "description": "Next review date (ISO 8601)."},
                       "risk_criteria_id": {"type": "string", "description": "UUID of the risk criteria to use"},
                       "assessor_id": {"type": "string", "description": "UUID of the assessor (user)"},
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this assessment covers (RG-01).",
                       },
                   })

    rc_fields = ["id", "scopes", "name", "description", "risk_matrix",
                 "acceptance_threshold", "is_default", "workflow_state", "created_at"]
    rc_writable = ["name", "description", "risk_matrix",
                   "acceptance_threshold", "is_default", 
                   "scope_ids"]

    _register_crud(server, "risk_criteria", RiskCriteria, "risks.criteria",
                   list_fields=rc_fields,
                   writable_fields=rc_writable,
                   search_fields=["name", "description"],
                   filters=["workflow_state"],
                   has_approve=False,
                   m2m_fields={"scope_ids": "scopes"},
                   field_overrides={
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes these criteria apply to (RG-01).",
                       },
                       "description": _html_field("Description"),
                       "risk_matrix": {
                           "type": "object",
                           "description": (
                               "Risk matrix as JSON object mapping 'likelihood,impact' to risk level. "
                               "Example for a 5x5 matrix: {\"1,1\": 1, \"1,2\": 2, ..., \"5,5\": 5}. "
                               "Can be omitted - the matrix will be auto-built from scale levels "
                               "and risk levels via rebuild_risk_matrix()."
                           ),
                       },
                       "acceptance_threshold": {
                           "type": "integer",
                           "description": "Risk level at or below which risks are automatically acceptable (default 0).",
                       },
                       "is_default": {
                           "type": "boolean",
                           "description": "Whether this is the default risk criteria.",
                       },
                   })

    # Scale levels (child of RiskCriteria, no approve)
    sl_fields = ["id", "criteria_id", "scale_type", "level", "name",
                 "description", "color"]
    sl_writable = ["criteria_id", "scale_type", "level", "name",
                   "description", "color"]

    _register_crud(server, "scale_level", ScaleLevel, "risks.criteria",
                   list_fields=sl_fields,
                   writable_fields=sl_writable,
                   search_fields=["name", "description"],
                   filters=["criteria_id", "scale_type"],
                   scope_filtered=False,
                   has_approve=False,
                   field_overrides={
                       "description": _html_field("Description"),
                       "criteria_id": {
                           "type": "string",
                           "description": "UUID of the parent RiskCriteria.",
                       },
                       "scale_type": {
                           "type": "string",
                           "description": "Type of scale.",
                           "enum": ["likelihood", "impact"],
                       },
                       "level": {
                           "type": "integer",
                           "description": "Numeric level (e.g. 1-5). Must be unique per criteria + scale_type.",
                       },
                   })

    # Risk levels (child of RiskCriteria, no approve)
    rl_fields = ["id", "criteria_id", "level", "name", "description",
                 "color", "requires_treatment"]
    rl_writable = ["criteria_id", "level", "name", "description",
                   "color", "requires_treatment"]

    _register_crud(server, "risk_level", RiskLevel, "risks.criteria",
                   list_fields=rl_fields,
                   writable_fields=rl_writable,
                   search_fields=["name", "description"],
                   filters=["criteria_id", "requires_treatment"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["criteria_id", "level", "name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "criteria_id": {"type": "string", "description": "UUID of the parent RiskCriteria."},
                       "level": {"type": "integer", "description": "Numeric risk level (e.g. 1-5). Must be unique per criteria."},
                       "color": {"type": "string", "description": "Color hex code (e.g. #ff0000)"},
                       "requires_treatment": {"type": "boolean", "description": "Whether this risk level requires treatment."},
                   })

    risk_fields = ["id", "reference", "name", "description",
                   "risk_source", "source_entity_id", "source_entity_type",
                   "status", "priority",
                   "initial_likelihood", "initial_impact", "initial_risk_level",
                   "current_likelihood", "current_impact", "current_risk_level",
                   "residual_likelihood", "residual_impact", "residual_risk_level",
                   "impact_confidentiality", "impact_integrity", "impact_availability",
                   "treatment_decision", "treatment_justification",
                   "review_date",
                   "affected_essential_assets", "affected_support_assets",
                   "linked_requirements",
                   "assessment_id", "risk_owner_id",
                   "created_at"]
    risk_writable = ["name", "description", "status", "priority",
                     "risk_source", "source_entity_id", "source_entity_type",
                     "initial_likelihood", "initial_impact",
                     "current_likelihood", "current_impact",
                     "residual_likelihood", "residual_impact",
                     "impact_confidentiality", "impact_integrity", "impact_availability",
                     "treatment_decision", "treatment_justification",
                     "review_date",
                     "assessment_id", "risk_owner_id",
                     "affected_essential_asset_ids", "affected_support_asset_ids",
                     "linked_requirement_ids"]

    _register_crud(server, "risk", Risk, "risks.risk",
                   list_fields=risk_fields,
                   writable_fields=risk_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "priority", "assessment_id", "risk_source"],
                   scope_filtered=False,
                   required_fields=["name", "assessment_id"],
                   m2m_fields={
                       "affected_essential_asset_ids": "affected_essential_assets",
                       "affected_support_asset_ids": "affected_support_assets",
                       "linked_requirement_ids": "linked_requirements",
                   },
                   field_overrides={
                       "description": _html_field("Description"),
                       "treatment_justification": _html_field("Treatment justification"),
                       "status": {
                           "type": "string",
                           "description": "Risk status.",
                           "enum": [
                               "identified", "analyzed", "evaluated",
                               "treatment_planned", "treatment_in_progress",
                               "treated", "accepted", "closed", "monitoring",
                           ],
                       },
                       "priority": {
                           "type": "string",
                           "description": "Risk priority.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "risk_source": {
                           "type": "string",
                           "description": "How this risk entered the register (manual, consolidated from an analysis, etc.).",
                           "enum": ["iso27005_analysis", "ebios_strategic", "ebios_operational",
                                    "incident", "audit", "compliance", "manual"],
                       },
                       "source_entity_id": {"type": "string", "description": "UUID of the source entity (ISO 27005 analysis, EBIOS scenario, ...) when risk_source is not 'manual'."},
                       "source_entity_type": {"type": "string", "description": "Class name of the source entity (e.g. 'ISO27005Risk', 'OperationalScenario')."},
                       "treatment_decision": {
                           "type": "string",
                           "description": "Treatment decision.",
                           "enum": ["accept", "mitigate", "transfer", "avoid", "not_decided"],
                       },
                       "impact_confidentiality": {"type": "boolean", "description": "Whether this risk impacts confidentiality."},
                       "impact_integrity": {"type": "boolean", "description": "Whether this risk impacts integrity."},
                       "impact_availability": {"type": "boolean", "description": "Whether this risk impacts availability."},
                       "review_date": {"type": "string", "description": "Next review date (ISO 8601)."},
                       "initial_likelihood": {"type": "integer", "description": "Initial likelihood level (matching scale levels, e.g. 1-5)"},
                       "initial_impact": {"type": "integer", "description": "Initial impact level (matching scale levels, e.g. 1-5)"},
                       "current_likelihood": {"type": "integer", "description": "Current likelihood level (matching scale levels, e.g. 1-5)"},
                       "current_impact": {"type": "integer", "description": "Current impact level (matching scale levels, e.g. 1-5)"},
                       "residual_likelihood": {"type": "integer", "description": "Residual likelihood level (matching scale levels, e.g. 1-5)"},
                       "residual_impact": {"type": "integer", "description": "Residual impact level (matching scale levels, e.g. 1-5)"},
                       "risk_owner_id": {"type": "string", "description": "UUID of the risk owner (user)"},
                       "affected_essential_asset_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Essential assets affected by this risk.",
                       },
                       "affected_support_asset_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Support assets affected by this risk.",
                       },
                       "linked_requirement_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Compliance requirements linked to this risk.",
                       },
                   })

    tp_fields = ["id", "reference", "name", "description", "treatment_type", "status",
                 "expected_residual_likelihood", "expected_residual_impact",
                 "cost_estimate", "start_date", "target_date", "completion_date",
                 "progress_percentage", "risk_id", "created_at"]
    tp_writable = ["name", "description", "treatment_type", "status",
                   "expected_residual_likelihood", "expected_residual_impact",
                   "cost_estimate", "start_date", "target_date", "completion_date",
                   "progress_percentage", "risk_id", "owner_id"]

    _register_crud(server, "risk_treatment_plan", RiskTreatmentPlan, "risks.treatment",
                   list_fields=tp_fields,
                   writable_fields=tp_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "risk_id"],
                   scope_filtered=False,
                   required_fields=["name", "risk_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "treatment_type": {
                           "type": "string",
                           "description": "Treatment strategy type.",
                           "enum": ["mitigate", "transfer", "avoid"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Treatment plan status.",
                           "enum": ["planned", "in_progress", "completed", "cancelled", "overdue"],
                       },
                       "expected_residual_likelihood": {"type": "integer", "description": "Expected residual likelihood (matching scale levels, e.g. 1-5)"},
                       "expected_residual_impact": {"type": "integer", "description": "Expected residual impact (matching scale levels, e.g. 1-5)"},
                       "owner_id": {"type": "string", "description": "UUID of the treatment plan owner (user)"},
                   })

    # Treatment actions (child of RiskTreatmentPlan, no approve)
    ta_fields = ["id", "treatment_plan_id", "description", "owner_id",
                 "target_date", "completion_date", "status", "order", "created_at"]
    ta_writable = ["treatment_plan_id", "description", "owner_id",
                   "target_date", "completion_date", "status", "order"]

    _register_crud(server, "treatment_action", TreatmentAction, "risks.treatment",
                   list_fields=ta_fields,
                   writable_fields=ta_writable,
                   search_fields=["description"],
                   filters=["treatment_plan_id", "status"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["treatment_plan_id", "description"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "status": {
                           "type": "string",
                           "description": "Action status.",
                           "enum": ["planned", "in_progress", "completed", "cancelled"],
                       },
                       "owner_id": {"type": "string", "description": "UUID of the action owner (user)"},
                   })

    acc_fields = ["id", "reference", "risk_id", "status", "justification", "conditions",
                  "valid_until", "review_date",
                  "accepted_by_id", "accepted_at", "risk_level_at_acceptance",
                  "created_at"]
    acc_writable = ["risk_id", "justification", "conditions", "valid_until",
                    "review_date", "accepted_by_id"]

    _register_crud(server, "risk_acceptance", RiskAcceptance, "risks.acceptance",
                   list_fields=acc_fields,
                   writable_fields=acc_writable,
                   search_fields=["justification"],
                   filters=["risk_id", "status"],
                   scope_filtered=False,
                   has_approve=True,
                   required_fields=["risk_id", "justification"],
                   field_overrides={
                       "justification": _html_field("Justification"),
                       "conditions": _html_field("Conditions"),
                       "status": {
                           "type": "string",
                           "description": "Acceptance status.",
                           "enum": ["active", "expired", "revoked", "renewed"],
                       },
                       "valid_until": {"type": "string", "description": "Last day the acceptance remains in force (ISO 8601)."},
                       "review_date": {"type": "string", "description": "Date the acceptance should be reviewed (ISO 8601)."},
                       "accepted_by_id": {"type": "string", "description": "UUID of the user who accepted the risk"},
                   })

    threat_fields = ["id", "reference", "scopes", "name", "description", "type",
                     "origin", "category", "typical_likelihood",
                     "is_from_catalog", "status", "created_at"]
    threat_writable = ["name", "description", "type", "origin", "category",
                       "typical_likelihood", "is_from_catalog", "status",
                       "scope_ids"]

    _register_crud(server, "threat", Threat, "risks.threat",
                   list_fields=threat_fields,
                   writable_fields=threat_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["type", "status", "is_from_catalog"],
                   m2m_fields={"scope_ids": "scopes"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Threat type.",
                           "enum": ["deliberate", "accidental", "environmental", "other"],
                       },
                       "origin": {
                           "type": "string",
                           "description": "Threat origin.",
                           "enum": ["human_internal", "human_external", "natural", "technical", "other"],
                       },
                       "category": {
                           "type": "string",
                           "description": "Threat category.",
                           "enum": [
                               "malware", "social_engineering", "unauthorized_access",
                               "denial_of_service", "data_breach", "physical_attack",
                               "espionage", "fraud", "sabotage", "human_error",
                               "system_failure", "network_failure", "power_failure",
                               "natural_disaster", "fire", "water_damage", "theft",
                               "vandalism", "supply_chain", "insider_threat",
                               "ransomware", "apt", "other",
                           ],
                       },
                       "typical_likelihood": {
                           "type": "integer",
                           "description": "Typical likelihood level (integer, e.g. 1-5).",
                       },
                       "is_from_catalog": {
                           "type": "boolean",
                           "description": "Whether this threat comes from a predefined ISO 27005 catalog.",
                       },
                       "status": {
                           "type": "string",
                           "description": "Threat status.",
                           "enum": ["active", "inactive"],
                       },
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this threat applies to (RG-01).",
                       },
                   })

    vuln_fields = ["id", "reference", "scopes", "name", "description", "category",
                   "severity", "status", "affected_asset_types", "affected_assets",
                   "cve_references", "is_from_catalog",
                   "remediation_guidance", "created_at"]
    vuln_writable = ["name", "description", "category", "severity", "status",
                     "affected_asset_types", "cve_references", "is_from_catalog",
                     "remediation_guidance",
                     "scope_ids", "affected_asset_ids"]

    _register_crud(server, "vulnerability", Vulnerability, "risks.vulnerability",
                   list_fields=vuln_fields,
                   writable_fields=vuln_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["category", "severity", "status", "is_from_catalog"],
                   m2m_fields={"scope_ids": "scopes",
                               "affected_asset_ids": "affected_assets"},
                   field_overrides={
                       "description": _html_field("Description"),
                       "remediation_guidance": _html_field("Remediation guidance"),
                       "category": {
                           "type": "string",
                           "description": "Vulnerability category.",
                           "enum": [
                               "configuration_weakness", "missing_patch", "design_flaw",
                               "coding_error", "weak_authentication", "insufficient_logging",
                               "lack_of_encryption", "physical_vulnerability",
                               "organizational_weakness", "human_factor", "obsolescence",
                               "insufficient_backup", "network_exposure",
                               "third_party_dependency",
                           ],
                       },
                       "severity": {
                           "type": "string",
                           "description": "Vulnerability severity.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Vulnerability status.",
                           "enum": ["identified", "confirmed", "mitigated", "accepted", "closed"],
                       },
                       "affected_asset_types": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Support asset types this vulnerability affects (free-form list).",
                       },
                       "cve_references": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of CVE identifiers (e.g. 'CVE-2024-1234').",
                       },
                       "is_from_catalog": {
                           "type": "boolean",
                           "description": "Whether this vulnerability comes from a predefined catalog.",
                       },
                       "scope_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Scopes this vulnerability applies to (RG-01).",
                       },
                       "affected_asset_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "UUIDs of support assets affected by this vulnerability.",
                       },
                   })

    iso_fields = ["id", "reference", "assessment_id", "threat_id", "vulnerability_id",
                  "affected_essential_assets", "affected_support_assets",
                  "threat_likelihood", "vulnerability_exposure",
                  "combined_likelihood",
                  "impact_confidentiality", "impact_integrity",
                  "impact_availability", "max_impact",
                  "risk_level", "existing_controls", "risk_id",
                  "description", "created_at"]
    iso_writable = ["assessment_id", "threat_id", "vulnerability_id",
                    "threat_likelihood", "vulnerability_exposure",
                    "impact_confidentiality", "impact_integrity",
                    "impact_availability",
                    "existing_controls", "risk_id", "description",
                    "affected_essential_asset_ids", "affected_support_asset_ids"]

    _register_crud(server, "iso27005_risk", ISO27005Risk, "risks.iso27005",
                   list_fields=iso_fields,
                   writable_fields=iso_writable,
                   search_fields=["description"],
                   filters=["assessment_id", "threat_id", "vulnerability_id"],
                   scope_filtered=False,
                   has_approve=True,
                   m2m_fields={
                       "affected_essential_asset_ids": "affected_essential_assets",
                       "affected_support_asset_ids": "affected_support_assets",
                   },
                   field_overrides={
                       "description": _html_field("Description"),
                       "existing_controls": _html_field("Existing controls"),
                       "affected_essential_asset_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Essential assets impacted by this triplet.",
                       },
                       "affected_support_asset_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "Support assets impacted by this triplet.",
                       },
                       "threat_likelihood": {
                           "type": "integer",
                           "description": (
                               "Threat likelihood level (integer matching a scale level, e.g. 1-5). "
                               "combined_likelihood is auto-computed as max(threat_likelihood, vulnerability_exposure)."
                           ),
                       },
                       "vulnerability_exposure": {
                           "type": "integer",
                           "description": (
                               "Vulnerability exposure level (integer matching a scale level, e.g. 1-5). "
                               "combined_likelihood is auto-computed as max(threat_likelihood, vulnerability_exposure)."
                           ),
                       },
                       "impact_confidentiality": {
                           "type": "integer",
                           "description": "Confidentiality impact level (integer matching a scale level, e.g. 1-5).",
                       },
                       "impact_integrity": {
                           "type": "integer",
                           "description": "Integrity impact level (integer matching a scale level, e.g. 1-5).",
                       },
                       "impact_availability": {
                           "type": "integer",
                           "description": "Availability impact level (integer matching a scale level, e.g. 1-5).",
                       },
                   })

    # ── ISO 27005 → Risk consolidation ────────────────────────
    # The EBIOS workshop W4 exposes a dedicated consolidate tool that
    # materialises a scenario into a Risk in the unified register and
    # preserves the source link (source_entity_id / source_entity_type).
    # The QA report (CAIRN-RSK-02) noted that no equivalent existed for
    # ISO 27005 analyses, forcing manual create-then-attach. This tool
    # closes the gap and is idempotent.

    from risks.constants import RiskSourceType as _RiskSourceTypeIso
    _Risk_for_iso = _get_model("risks", "Risk")

    def _consolidate_iso27005_risk(user, arguments):
        analysis_id = arguments.get("id")
        if not analysis_id:
            raise InvalidParamsError("id is required.")
        try:
            analysis = ISO27005Risk.objects.get(pk=analysis_id)
        except ISO27005Risk.DoesNotExist:
            return _error(f"ISO27005Risk not found: {analysis_id}")
        if analysis.risk_id:
            return {
                "status": "already_consolidated",
                "risk_id": str(analysis.risk_id),
                "risk_reference": analysis.risk.reference,
            }
        risk = _Risk_for_iso.objects.create(
            assessment=analysis.assessment,
            name=f"{analysis.threat.name} × {analysis.vulnerability.name}"[:255],
            description=analysis.description,
            risk_source=_RiskSourceTypeIso.ISO27005_ANALYSIS,
            source_entity_id=analysis.pk,
            source_entity_type="risks.ISO27005Risk",
            initial_likelihood=analysis.combined_likelihood,
            initial_impact=analysis.max_impact,
            current_likelihood=analysis.combined_likelihood,
            current_impact=analysis.max_impact,
            impact_confidentiality=bool(analysis.impact_confidentiality),
            impact_integrity=bool(analysis.impact_integrity),
            impact_availability=bool(analysis.impact_availability),
            criteria_snapshot=analysis.criteria_snapshot,
            created_by=user,
        )
        risk.affected_essential_assets.set(analysis.affected_essential_assets.all())
        risk.affected_support_assets.set(analysis.affected_support_assets.all())
        analysis.risk = risk
        analysis.save(update_fields=["risk"])
        return {
            "status": "consolidated",
            "risk_id": str(risk.pk),
            "risk_reference": risk.reference,
        }

    server.register_tool(
        "consolidate_iso27005_risk",
        (
            "Materialise an ISO 27005 analysis (threat × vulnerability) into a Risk "
            "in the unified register. Idempotent: returns the existing Risk if the "
            "analysis has already been consolidated. The source link is preserved "
            "via source_entity_id / source_entity_type on the resulting Risk."
        ),
        _id_schema(),
        require_perm("risks.risk.create")(_consolidate_iso27005_risk),
    )

    # ── Risk ↔ Requirement linking tools ──────────────────────
    #
    # These tools manage the many-to-many relationship between risks and
    # compliance requirements (Risk.linked_requirements / Requirement.linked_risks).
    #
    # Available operations:
    #   - list_risk_requirements     : list all requirements linked to a risk
    #   - list_requirement_risks     : list all risks linked to a requirement
    #   - link_risk_requirements     : attach one or more requirements to a risk
    #   - unlink_risk_requirements   : detach one or more requirements from a risk
    #   - set_risk_requirements      : replace the full set of linked requirements on a risk
    #
    # All operations respect the standard permission model
    # (risks.risk.read / risks.risk.update).

    Requirement = _get_model("compliance", "Requirement")

    req_link_fields = [
        "id", "reference", "requirement_number", "name",
        "compliance_status", "framework_id",
    ]

    risk_link_fields = [
        "id", "reference", "name", "current_risk_level",
        "priority", "status",
    ]

    # -- list_risk_requirements: list requirements linked to a given risk --
    def _list_risk_requirements(user, arguments):
        """Return all compliance requirements linked to a specific risk.

        Parameters
        ----------
        risk_id : str (required)
            UUID of the risk whose linked requirements should be returned.

        Returns
        -------
        dict
            ``{"risk_id": "<uuid>", "total": <int>, "items": [...]}``.
            Each item contains: id, reference, requirement_number, name,
            compliance_status, and framework_id.
        """
        risk_id = arguments.get("risk_id")
        if not risk_id:
            raise InvalidParamsError("risk_id is required.")
        try:
            risk = Risk.objects.get(pk=risk_id)
        except Risk.DoesNotExist:
            return _error("Risk not found.")
        reqs = risk.linked_requirements.all()
        items = [_serialize_obj(r, req_link_fields) for r in reqs]
        return {"risk_id": str(risk_id), "total": len(items), "items": items}

    server.register_tool(
        "list_risk_requirements",
        (
            "List all compliance requirements linked to a risk. "
            "Returns requirement id, reference, number, name, compliance_status "
            "and framework_id for each linked requirement."
        ),
        _obj_schema(
            {"risk_id": {"type": "string", "description": "UUID of the risk"}},
            required=["risk_id"],
        ),
        require_perm("risks.risk.read")(_list_risk_requirements),
    )

    # -- list_requirement_risks: list risks linked to a given requirement --
    def _list_requirement_risks(user, arguments):
        """Return all risks linked to a specific compliance requirement.

        Parameters
        ----------
        requirement_id : str (required)
            UUID of the requirement whose linked risks should be returned.

        Returns
        -------
        dict
            ``{"requirement_id": "<uuid>", "total": <int>, "items": [...]}``.
            Each item contains: id, reference, name, current_risk_level,
            priority, and status.
        """
        req_id = arguments.get("requirement_id")
        if not req_id:
            raise InvalidParamsError("requirement_id is required.")
        try:
            req = Requirement.objects.get(pk=req_id)
        except Requirement.DoesNotExist:
            return _error("Requirement not found.")
        risks = req.linked_risks.all()
        items = [_serialize_obj(r, risk_link_fields) for r in risks]
        return {"requirement_id": str(req_id), "total": len(items), "items": items}

    server.register_tool(
        "list_requirement_risks",
        (
            "List all risks linked to a compliance requirement. "
            "Returns risk id, reference, name, current_risk_level, priority "
            "and status for each linked risk."
        ),
        _obj_schema(
            {"requirement_id": {"type": "string", "description": "UUID of the requirement"}},
            required=["requirement_id"],
        ),
        require_perm("compliance.requirement.read")(_list_requirement_risks),
    )

    # -- link_risk_requirements: add requirements to a risk --
    def _link_risk_requirements(user, arguments):
        """Add one or more requirements to a risk's linked requirements.

        This is an *additive* operation: existing links are preserved and
        the supplied requirement_ids are added on top.

        Parameters
        ----------
        risk_id : str (required)
            UUID of the risk to link requirements to.
        requirement_ids : list[str] (required)
            List of requirement UUIDs to attach.

        Returns
        -------
        dict
            ``{"risk_id": "<uuid>", "added": <int>, "total": <int>}``
            where *added* is the number of newly created links and *total*
            is the resulting count of linked requirements.
        """
        risk_id = arguments.get("risk_id")
        req_ids = arguments.get("requirement_ids", [])
        if not risk_id:
            raise InvalidParamsError("risk_id is required.")
        if not req_ids:
            raise InvalidParamsError("requirement_ids is required and must be a non-empty list.")
        try:
            risk = Risk.objects.get(pk=risk_id)
        except Risk.DoesNotExist:
            return _error("Risk not found.")
        from core.lifecycle import linkable_states
        if risk.is_terminal_state:
            return _error(
                f"Risk is in the terminal '{risk.workflow_state}' lifecycle state "
                "and cannot gain new links."
            )
        existing = set(str(pk) for pk in risk.linked_requirements.values_list("pk", flat=True))
        reqs = Requirement.objects.filter(pk__in=req_ids)
        if reqs.count() != len(req_ids):
            found = set(str(r.pk) for r in reqs)
            missing = [rid for rid in req_ids if rid not in found]
            return _error(f"Requirements not found: {missing}")
        allowed = linkable_states(Requirement)
        not_linkable = sorted(
            str(r.pk) for r in reqs
            if r.workflow_state not in allowed and str(r.pk) not in existing
        )
        if not_linkable:
            return _error(
                f"Requirements not in a linkable lifecycle state: {not_linkable}"
            )
        risk.linked_requirements.add(*reqs)
        added = len(set(req_ids) - existing)
        total = risk.linked_requirements.count()
        return {"risk_id": str(risk_id), "added": added, "total": total}

    server.register_tool(
        "link_risk_requirements",
        (
            "Link one or more compliance requirements to a risk. "
            "This is additive - existing links are preserved. "
            "Provide a risk_id and a list of requirement_ids to attach."
        ),
        _obj_schema(
            {
                "risk_id": {"type": "string", "description": "UUID of the risk"},
                "requirement_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of requirement UUIDs to link to the risk",
                },
            },
            required=["risk_id", "requirement_ids"],
        ),
        require_perm("risks.risk.update")(_link_risk_requirements),
    )

    # -- unlink_risk_requirements: remove requirements from a risk --
    def _unlink_risk_requirements(user, arguments):
        """Remove one or more requirements from a risk's linked requirements.

        Only the specified links are removed; other existing links remain
        untouched.

        Parameters
        ----------
        risk_id : str (required)
            UUID of the risk to unlink requirements from.
        requirement_ids : list[str] (required)
            List of requirement UUIDs to detach.

        Returns
        -------
        dict
            ``{"risk_id": "<uuid>", "removed": <int>, "total": <int>}``
            where *removed* is the number of links that were actually
            deleted and *total* is the resulting count.
        """
        risk_id = arguments.get("risk_id")
        req_ids = arguments.get("requirement_ids", [])
        if not risk_id:
            raise InvalidParamsError("risk_id is required.")
        if not req_ids:
            raise InvalidParamsError("requirement_ids is required and must be a non-empty list.")
        try:
            risk = Risk.objects.get(pk=risk_id)
        except Risk.DoesNotExist:
            return _error("Risk not found.")
        existing = set(str(pk) for pk in risk.linked_requirements.values_list("pk", flat=True))
        removed = len(existing & set(req_ids))
        risk.linked_requirements.remove(*Requirement.objects.filter(pk__in=req_ids))
        total = risk.linked_requirements.count()
        return {"risk_id": str(risk_id), "removed": removed, "total": total}

    server.register_tool(
        "unlink_risk_requirements",
        (
            "Remove one or more compliance requirements from a risk. "
            "Only the specified links are removed; other links are preserved. "
            "Provide a risk_id and a list of requirement_ids to detach."
        ),
        _obj_schema(
            {
                "risk_id": {"type": "string", "description": "UUID of the risk"},
                "requirement_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of requirement UUIDs to unlink from the risk",
                },
            },
            required=["risk_id", "requirement_ids"],
        ),
        require_perm("risks.risk.update")(_unlink_risk_requirements),
    )

    # -- set_risk_requirements: replace all linked requirements on a risk --
    def _set_risk_requirements(user, arguments):
        """Replace the entire set of linked requirements on a risk.

        All previous links are removed and replaced by the supplied list.
        Pass an empty list to clear all links.

        Parameters
        ----------
        risk_id : str (required)
            UUID of the risk whose requirements should be replaced.
        requirement_ids : list[str] (required)
            Complete list of requirement UUIDs that should be linked.
            Pass ``[]`` to remove all links.

        Returns
        -------
        dict
            ``{"risk_id": "<uuid>", "total": <int>}`` with the resulting
            number of linked requirements.
        """
        risk_id = arguments.get("risk_id")
        req_ids = arguments.get("requirement_ids", [])
        if not risk_id:
            raise InvalidParamsError("risk_id is required.")
        if not isinstance(req_ids, list):
            raise InvalidParamsError("requirement_ids must be a list.")
        try:
            risk = Risk.objects.get(pk=risk_id)
        except Risk.DoesNotExist:
            return _error("Risk not found.")
        if req_ids:
            from core.lifecycle import linkable_states
            if risk.is_terminal_state:
                return _error(
                    f"Risk is in the terminal '{risk.workflow_state}' lifecycle state "
                    "and cannot gain new links."
                )
            reqs = Requirement.objects.filter(pk__in=req_ids)
            if reqs.count() != len(req_ids):
                found = set(str(r.pk) for r in reqs)
                missing = [rid for rid in req_ids if rid not in found]
                return _error(f"Requirements not found: {missing}")
            existing = set(
                str(pk) for pk in risk.linked_requirements.values_list("pk", flat=True)
            )
            allowed = linkable_states(Requirement)
            not_linkable = sorted(
                str(r.pk) for r in reqs
                if r.workflow_state not in allowed and str(r.pk) not in existing
            )
            if not_linkable:
                return _error(
                    f"Requirements not in a linkable lifecycle state: {not_linkable}"
                )
            risk.linked_requirements.set(reqs)
        else:
            risk.linked_requirements.clear()
        total = risk.linked_requirements.count()
        return {"risk_id": str(risk_id), "total": total}

    server.register_tool(
        "set_risk_requirements",
        (
            "Replace the full set of linked requirements on a risk. "
            "All previous links are removed and replaced by the supplied list. "
            "Pass an empty requirement_ids list to clear all links."
        ),
        _obj_schema(
            {
                "risk_id": {"type": "string", "description": "UUID of the risk"},
                "requirement_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Complete list of requirement UUIDs to link. "
                        "Pass an empty list to remove all links."
                    ),
                },
            },
            required=["risk_id", "requirement_ids"],
        ),
        require_perm("risks.risk.update")(_set_risk_requirements),
    )

    # ── RiskTreatmentPlan ↔ ComplianceActionPlan linking tools ─
    #
    # These tools manage the many-to-many relationship between risk
    # treatment plans and compliance action plans
    # (RiskTreatmentPlan.related_action_plans /
    #  ComplianceActionPlan.related_treatment_plans).
    #
    # Available operations:
    #   - list_treatment_plan_action_plans : list all action plans linked
    #     to a treatment plan
    #   - link_treatment_plan_action_plans : attach action plans (additive)
    #   - unlink_treatment_plan_action_plans : detach selected action plans
    #   - set_treatment_plan_action_plans : replace the full set of links

    ComplianceActionPlan = _get_model("compliance", "ComplianceActionPlan")

    action_plan_link_fields = [
        "id", "reference", "name", "status", "priority",
        "progress_percentage", "owner_id",
    ]

    def _list_treatment_plan_action_plans(user, arguments):
        """Return all compliance action plans linked to a treatment plan."""
        plan_id = arguments.get("treatment_plan_id")
        if not plan_id:
            raise InvalidParamsError("treatment_plan_id is required.")
        try:
            plan = RiskTreatmentPlan.objects.get(pk=plan_id)
        except RiskTreatmentPlan.DoesNotExist:
            return _error("Treatment plan not found.")
        items = [
            _serialize_obj(ap, action_plan_link_fields)
            for ap in plan.related_action_plans.all()
        ]
        return {"treatment_plan_id": str(plan_id), "total": len(items), "items": items}

    server.register_tool(
        "list_treatment_plan_action_plans",
        (
            "List all compliance action plans linked to a risk treatment plan. "
            "Returns action plan id, reference, name, status, priority, "
            "progress_percentage and owner_id for each link."
        ),
        _obj_schema(
            {"treatment_plan_id": {"type": "string", "description": "UUID of the treatment plan"}},
            required=["treatment_plan_id"],
        ),
        require_perm("risks.treatment.read")(_list_treatment_plan_action_plans),
    )

    def _link_treatment_plan_action_plans(user, arguments):
        """Attach action plans to a treatment plan. Additive: existing links are preserved."""
        plan_id = arguments.get("treatment_plan_id")
        ap_ids = arguments.get("action_plan_ids", [])
        if not plan_id:
            raise InvalidParamsError("treatment_plan_id is required.")
        if not ap_ids:
            raise InvalidParamsError(
                "action_plan_ids is required and must be a non-empty list."
            )
        try:
            plan = RiskTreatmentPlan.objects.get(pk=plan_id)
        except RiskTreatmentPlan.DoesNotExist:
            return _error("Treatment plan not found.")
        from core.lifecycle import linkable_states
        if plan.is_terminal_state:
            return _error(
                f"Treatment plan is in the terminal '{plan.workflow_state}' lifecycle "
                "state and cannot gain new links."
            )
        existing = set(
            str(pk) for pk in plan.related_action_plans.values_list("pk", flat=True)
        )
        action_plans = ComplianceActionPlan.objects.filter(pk__in=ap_ids)
        if action_plans.count() != len(ap_ids):
            found = set(str(ap.pk) for ap in action_plans)
            missing = [aid for aid in ap_ids if aid not in found]
            return _error(f"Action plans not found: {missing}")
        allowed = linkable_states(ComplianceActionPlan)
        not_linkable = sorted(
            str(ap.pk) for ap in action_plans
            if ap.workflow_state not in allowed and str(ap.pk) not in existing
        )
        if not_linkable:
            return _error(
                f"Action plans not in a linkable lifecycle state: {not_linkable}"
            )
        plan.related_action_plans.add(*action_plans)
        added = len(set(ap_ids) - existing)
        total = plan.related_action_plans.count()
        return {"treatment_plan_id": str(plan_id), "added": added, "total": total}

    server.register_tool(
        "link_treatment_plan_action_plans",
        (
            "Link one or more compliance action plans to a risk treatment plan. "
            "This is additive - existing links are preserved. "
            "Provide a treatment_plan_id and a list of action_plan_ids to attach."
        ),
        _obj_schema(
            {
                "treatment_plan_id": {"type": "string", "description": "UUID of the treatment plan"},
                "action_plan_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of compliance action plan UUIDs to link",
                },
            },
            required=["treatment_plan_id", "action_plan_ids"],
        ),
        require_perm("risks.treatment.update")(_link_treatment_plan_action_plans),
    )

    def _unlink_treatment_plan_action_plans(user, arguments):
        """Remove specified action plans from a treatment plan. Other links remain."""
        plan_id = arguments.get("treatment_plan_id")
        ap_ids = arguments.get("action_plan_ids", [])
        if not plan_id:
            raise InvalidParamsError("treatment_plan_id is required.")
        if not ap_ids:
            raise InvalidParamsError(
                "action_plan_ids is required and must be a non-empty list."
            )
        try:
            plan = RiskTreatmentPlan.objects.get(pk=plan_id)
        except RiskTreatmentPlan.DoesNotExist:
            return _error("Treatment plan not found.")
        existing = set(
            str(pk) for pk in plan.related_action_plans.values_list("pk", flat=True)
        )
        removed = len(existing & set(ap_ids))
        plan.related_action_plans.remove(
            *ComplianceActionPlan.objects.filter(pk__in=ap_ids)
        )
        total = plan.related_action_plans.count()
        return {"treatment_plan_id": str(plan_id), "removed": removed, "total": total}

    server.register_tool(
        "unlink_treatment_plan_action_plans",
        (
            "Remove one or more compliance action plans from a risk treatment plan. "
            "Only the specified links are removed; other links are preserved."
        ),
        _obj_schema(
            {
                "treatment_plan_id": {"type": "string", "description": "UUID of the treatment plan"},
                "action_plan_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of compliance action plan UUIDs to unlink",
                },
            },
            required=["treatment_plan_id", "action_plan_ids"],
        ),
        require_perm("risks.treatment.update")(_unlink_treatment_plan_action_plans),
    )

    def _set_treatment_plan_action_plans(user, arguments):
        """Replace the entire set of action plans on a treatment plan."""
        plan_id = arguments.get("treatment_plan_id")
        ap_ids = arguments.get("action_plan_ids", [])
        if not plan_id:
            raise InvalidParamsError("treatment_plan_id is required.")
        if not isinstance(ap_ids, list):
            raise InvalidParamsError("action_plan_ids must be a list.")
        try:
            plan = RiskTreatmentPlan.objects.get(pk=plan_id)
        except RiskTreatmentPlan.DoesNotExist:
            return _error("Treatment plan not found.")
        if ap_ids:
            from core.lifecycle import linkable_states
            if plan.is_terminal_state:
                return _error(
                    f"Treatment plan is in the terminal '{plan.workflow_state}' "
                    "lifecycle state and cannot gain new links."
                )
            action_plans = ComplianceActionPlan.objects.filter(pk__in=ap_ids)
            if action_plans.count() != len(ap_ids):
                found = set(str(ap.pk) for ap in action_plans)
                missing = [aid for aid in ap_ids if aid not in found]
                return _error(f"Action plans not found: {missing}")
            existing = set(
                str(pk) for pk in plan.related_action_plans.values_list("pk", flat=True)
            )
            allowed = linkable_states(ComplianceActionPlan)
            not_linkable = sorted(
                str(ap.pk) for ap in action_plans
                if ap.workflow_state not in allowed and str(ap.pk) not in existing
            )
            if not_linkable:
                return _error(
                    f"Action plans not in a linkable lifecycle state: {not_linkable}"
                )
            plan.related_action_plans.set(action_plans)
        else:
            plan.related_action_plans.clear()
        total = plan.related_action_plans.count()
        return {"treatment_plan_id": str(plan_id), "total": total}

    server.register_tool(
        "set_treatment_plan_action_plans",
        (
            "Replace the full set of compliance action plans linked to a "
            "risk treatment plan. All previous links are removed and replaced "
            "by the supplied list. Pass an empty action_plan_ids list to clear "
            "all links."
        ),
        _obj_schema(
            {
                "treatment_plan_id": {"type": "string", "description": "UUID of the treatment plan"},
                "action_plan_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Complete list of compliance action plan UUIDs to link. "
                        "Pass an empty list to remove all links."
                    ),
                },
            },
            required=["treatment_plan_id", "action_plan_ids"],
        ),
        require_perm("risks.treatment.update")(_set_treatment_plan_action_plans),
    )

    # ── EBIOS RM Foundation (workshops W0 and W1) ──────────────
    #
    # Tools cover the study framework (W0), workshop progress tracking, the
    # security baseline (W1) and its feared events and baseline gaps. The
    # post_save signal on RiskAssessment already creates one StudyFramework,
    # one SecurityBaseline and six EbiosWorkshopProgress rows when an
    # assessment with methodology=ebios_rm is saved - the create_* tools
    # below are typically only needed for edge cases (manual recreation
    # after a deletion, or a fresh iteration).

    StudyFramework = _get_model("risks", "StudyFramework")
    EbiosWorkshopProgress = _get_model("risks", "EbiosWorkshopProgress")
    SecurityBaseline = _get_model("risks", "SecurityBaseline")
    FearedEvent = _get_model("risks", "FearedEvent")
    BaselineGap = _get_model("risks", "BaselineGap")

    sf_fields = [
        "id", "reference", "assessment_id", "mission_statement",
        "business_perimeter", "technical_perimeter", "temporal_perimeter",
        "financial_envelope", "assumptions", "constraints",
        "expected_deliverables", "status", "created_at", "updated_at",
    ]
    sf_writable = [
        "assessment_id", "mission_statement", "business_perimeter",
        "technical_perimeter", "temporal_perimeter", "financial_envelope",
        "assumptions", "constraints", "expected_deliverables", "status",
    ]
    _register_crud(
        server, "ebios_study_framework", StudyFramework, "risks.ebios_assessment",
        list_fields=sf_fields,
        writable_fields=sf_writable,
        search_fields=["reference", "mission_statement", "business_perimeter"],
        filters=["assessment_id", "status"],
        scope_filtered=False,
        has_approve=False,
        required_fields=["assessment_id"],
        field_overrides={
            "mission_statement": _html_field("Mission statement"),
            "business_perimeter": _html_field("Business perimeter"),
            "technical_perimeter": _html_field("Technical perimeter"),
            "status": {
                "type": "string",
                "description": "Study framework status: draft, validated.",
            },
        },
    )

    wp_fields = [
        "id", "reference", "assessment_id", "workshop_number",
        "iteration_type", "iteration_number", "status", "started_at",
        "validated_by_id", "validated_at", "rejection_reason",
        "deliverables_summary", "notes", "created_at", "updated_at",
    ]
    wp_writable = [
        "assessment_id", "workshop_number", "iteration_type",
        "iteration_number", "status", "started_at",
        "deliverables_summary", "notes",
    ]
    _register_crud(
        server, "ebios_workshop", EbiosWorkshopProgress, "risks.ebios_assessment",
        list_fields=wp_fields,
        writable_fields=wp_writable,
        search_fields=["reference", "notes"],
        filters=[
            "assessment_id", "workshop_number", "iteration_type",
            "iteration_number", "status",
        ],
        scope_filtered=False,
        has_approve=False,
        required_fields=["assessment_id", "workshop_number"],
        field_overrides={
            "workshop_number": {
                "type": "integer",
                "description": "Workshop number 0..5 (0=study framework, 1=baseline, 5=treatment).",
            },
            "iteration_type": {
                "type": "string",
                "description": "Iteration type: strategic (annual) or operational (semestrial).",
            },
            "iteration_number": {
                "type": "integer",
                "description": "Iteration number (starts at 1).",
            },
            "status": {
                "type": "string",
                "description": "Workshop status: not_started, in_progress, under_review, validated, rejected.",
            },
        },
    )

    sb_fields = [
        "id", "reference", "assessment_id", "dic_summary", "status",
        "created_at", "updated_at",
    ]
    sb_writable = ["assessment_id", "dic_summary", "status"]
    _register_crud(
        server, "ebios_security_baseline", SecurityBaseline, "risks.ebios_baseline",
        list_fields=sb_fields,
        writable_fields=sb_writable,
        search_fields=["reference", "dic_summary"],
        filters=["assessment_id", "status"],
        scope_filtered=False,
        has_approve=True,
        required_fields=["assessment_id"],
        field_overrides={
            "dic_summary": _html_field("DIC needs summary"),
            "status": {
                "type": "string",
                "description": "Baseline status: draft, in_progress, completed.",
            },
        },
    )

    fe_fields = [
        "id", "reference", "baseline_id", "essential_asset_id", "name",
        "description", "dic_criterion", "gravity_level",
        "gravity_justification", "order", "created_at", "updated_at",
    ]
    fe_writable = [
        "baseline_id", "essential_asset_id", "name", "description",
        "dic_criterion", "gravity_level", "gravity_justification",
        "business_impacts", "order",
    ]
    _register_crud(
        server, "ebios_feared_event", FearedEvent, "risks.ebios_baseline",
        list_fields=fe_fields,
        writable_fields=fe_writable,
        search_fields=["reference", "name", "description"],
        filters=["baseline_id", "essential_asset_id", "dic_criterion"],
        scope_filtered=False,
        has_approve=False,
        required_fields=["baseline_id", "essential_asset_id", "name", "dic_criterion"],
        field_overrides={
            "description": _html_field("Description"),
            "gravity_justification": _html_field("Gravity justification"),
            "dic_criterion": {
                "type": "string",
                "description": "DIC criterion impaired: confidentiality, integrity, availability.",
            },
            "gravity_level": {
                "type": "integer",
                "description": "Gravity level on the assessment impact scale (e.g. 1-4 or 1-5).",
            },
            "business_impacts": {
                "type": "object",
                "description": (
                    "Optional business impact breakdown. Accepts a JSON object with keys "
                    "such as financial, legal, reputation, operational, human, environmental."
                ),
            },
        },
    )

    bg_fields = [
        "id", "reference", "baseline_id", "reference_source",
        "linked_requirement_id", "description", "severity", "status",
        "recommended_remediation", "order", "created_at", "updated_at",
    ]
    bg_writable = [
        "baseline_id", "reference_source", "linked_requirement_id",
        "description", "severity", "recommended_remediation", "status",
        "order",
    ]
    _register_crud(
        server, "ebios_baseline_gap", BaselineGap, "risks.ebios_baseline",
        list_fields=bg_fields,
        writable_fields=bg_writable,
        search_fields=["reference", "reference_source", "description"],
        filters=["baseline_id", "linked_requirement_id", "severity", "status"],
        scope_filtered=False,
        has_approve=False,
        required_fields=["baseline_id", "reference_source", "description"],
        field_overrides={
            "description": _html_field("Description"),
            "recommended_remediation": _html_field("Recommended remediation"),
            "severity": {
                "type": "string",
                "description": "Severity: low, medium, high, critical.",
            },
            "status": {
                "type": "string",
                "description": "Gap status: identified, accepted, in_remediation, remediated.",
            },
        },
    )

    # ── EBIOS RM Workshop 2 (risk sources, objectives, SR/OV pairs) ────
    #
    # The risk source threat_level is auto-computed at save() from
    # (motivation_level, resources_level, activity_level) via the ANSSI
    # Grid A. The criteria_snapshot freezes the grid used so future edits
    # to the assessment's RiskCriteria do not silently rewrite historical
    # scores. SR/OV pair priority_score is the max of (risk_source.threat_level,
    # relevance_weight).

    RiskSource = _get_model("risks", "RiskSource")
    TargetedObjective = _get_model("risks", "TargetedObjective")
    RiskSourceObjectivePair = _get_model("risks", "RiskSourceObjectivePair")

    rsrc_fields = [
        "id", "reference", "assessment_id", "name", "description", "category",
        "motivation_level", "motivation_description", "resources_level",
        "activity_level", "threat_level", "is_retained",
        "retention_justification", "is_from_catalog",
        "created_at", "updated_at",
    ]
    rsrc_writable = [
        "assessment_id", "name", "description", "category",
        "motivation_level", "motivation_description", "resources_level",
        "activity_level", "is_retained", "retention_justification",
        "is_from_catalog",
    ]
    _register_crud(
        server, "ebios_risk_source", RiskSource, "risks.ebios_risk_source",
        list_fields=rsrc_fields,
        writable_fields=rsrc_writable,
        search_fields=["reference", "name", "description", "motivation_description"],
        filters=["assessment_id", "category", "is_retained", "is_from_catalog", "threat_level"],
        scope_filtered=False,
        has_approve=True,
        required_fields=["assessment_id", "name"],
        field_overrides={
            "description": _html_field("Description"),
            "motivation_description": _html_field("Motivation description"),
            "retention_justification": _html_field("Retention justification"),
            "category": {
                "type": "string",
                "description": "ANSSI risk source category: state, organized_crime, terrorist, activist, competitor, employee, service_provider, amateur, natural, other.",
            },
            "motivation_level": {
                "type": "integer",
                "description": "1 (low) to 4 (very strong). Drives the ANSSI threat level Grid A.",
            },
            "resources_level": {
                "type": "integer",
                "description": "1 (limited) to 4 (unlimited). Drives the ANSSI threat level Grid A.",
            },
            "activity_level": {
                "type": "integer",
                "description": "Observed activity 1 to 4. Activity >= 3 majorates the threat level by one (capped at V4).",
            },
        },
    )

    tov_fields = [
        "id", "reference", "risk_source_id", "name", "description", "category",
        "is_retained", "order", "created_at", "updated_at",
    ]
    tov_writable = [
        "risk_source_id", "name", "description", "category", "is_retained", "order",
    ]
    _register_crud(
        server, "ebios_targeted_objective", TargetedObjective, "risks.ebios_risk_source",
        list_fields=tov_fields,
        writable_fields=tov_writable,
        search_fields=["reference", "name", "description"],
        filters=["risk_source_id", "category", "is_retained"],
        scope_filtered=False,
        has_approve=False,
        required_fields=["risk_source_id", "name"],
        field_overrides={
            "description": _html_field("Description"),
            "category": {
                "type": "string",
                "description": "ANSSI objective category: lucrative, strategic, terrorist, ideological, revenge, ludic, other.",
            },
        },
    )

    sov_fields = [
        "id", "reference", "assessment_id", "risk_source_id",
        "targeted_objective_id", "relevance", "relevance_justification",
        "priority_score", "is_retained", "retention_justification",
        "created_at", "updated_at",
    ]
    sov_writable = [
        "assessment_id", "risk_source_id", "targeted_objective_id",
        "relevance", "relevance_justification", "is_retained",
        "retention_justification",
    ]
    _register_crud(
        server, "ebios_sr_ov_pair", RiskSourceObjectivePair, "risks.ebios_risk_source",
        list_fields=sov_fields,
        writable_fields=sov_writable,
        search_fields=["reference", "relevance_justification", "retention_justification"],
        filters=["assessment_id", "risk_source_id", "targeted_objective_id", "relevance", "is_retained"],
        scope_filtered=False,
        has_approve=True,
        required_fields=["assessment_id", "risk_source_id", "targeted_objective_id"],
        field_overrides={
            "relevance_justification": _html_field("Relevance justification"),
            "retention_justification": _html_field("Retention justification"),
            "relevance": {
                "type": "string",
                "description": "SR/OV relevance: low, medium, high, critical. Combined with risk_source.threat_level to produce priority_score.",
            },
        },
    )

    # ── EBIOS RM Workshop 3 (ecosystem, strategic scenarios) ──────────
    #
    # EcosystemStakeholder.threat_level is auto-computed at save() as
    # (dependency * penetration) / (maturity * trust). threat_zone is
    # derived from threat_level via DEFAULT_ECOSYSTEM_THRESHOLDS, both
    # overridable through RiskCriteria.risk_matrix["ebios_ecosystem_thresholds"].
    # StrategicScenario.risk_level is computed via the assessment risk
    # matrix (likelihood x gravity).

    EcosystemStakeholder = _get_model("risks", "EcosystemStakeholder")
    StrategicScenario = _get_model("risks", "StrategicScenario")
    AttackPathStep = _get_model("risks", "AttackPathStep")

    ecos_fields = [
        "id", "reference", "assessment_id", "stakeholder_id", "supplier_id",
        "name", "description", "category", "dependency", "penetration",
        "maturity", "trust", "threat_level", "threat_zone",
        "is_attack_vector", "attack_vector_justification",
        "created_at", "updated_at",
    ]
    ecos_writable = [
        "assessment_id", "stakeholder_id", "supplier_id", "name", "description",
        "category", "dependency", "penetration", "maturity", "trust",
        "is_attack_vector", "attack_vector_justification",
    ]
    _register_crud(
        server, "ebios_ecosystem_stakeholder", EcosystemStakeholder, "risks.ebios_ecosystem",
        list_fields=ecos_fields,
        writable_fields=ecos_writable,
        search_fields=["reference", "name", "description", "attack_vector_justification"],
        filters=["assessment_id", "category", "threat_zone", "is_attack_vector"],
        scope_filtered=False,
        has_approve=True,
        required_fields=["assessment_id", "name"],
        field_overrides={
            "description": _html_field("Description"),
            "attack_vector_justification": _html_field("Attack vector justification"),
            "category": {
                "type": "string",
                "description": "Ecosystem category: supplier, partner, subcontractor, customer, regulator, shared_infrastructure, client_employee, other.",
            },
            "dependency": {
                "type": "integer",
                "description": "Organisation dependency on the stakeholder (1..4). Numerator in (D*P)/(M*T).",
            },
            "penetration": {
                "type": "integer",
                "description": "Stakeholder penetration into the ecosystem (1..4). Numerator in (D*P)/(M*T).",
            },
            "maturity": {
                "type": "integer",
                "description": "Stakeholder cyber maturity (1..4). Denominator in (D*P)/(M*T).",
            },
            "trust": {
                "type": "integer",
                "description": "Trust placed in the stakeholder (1..4). Denominator in (D*P)/(M*T).",
            },
        },
    )

    ssc_fields = [
        "id", "reference", "assessment_id", "name", "description",
        "sr_ov_pair_id", "gravity_level", "likelihood_level", "risk_level",
        "is_retained", "consolidated_risk_id",
        "created_at", "updated_at",
    ]
    ssc_writable = [
        "assessment_id", "name", "description", "sr_ov_pair_id",
        "gravity_level", "gravity_justification", "likelihood_level",
        "likelihood_justification", "existing_security_measures",
        "is_retained", "retention_justification", "consolidated_risk_id",
    ]
    _register_crud(
        server, "ebios_strategic_scenario", StrategicScenario, "risks.ebios_strategic",
        list_fields=ssc_fields,
        writable_fields=ssc_writable,
        search_fields=[
            "reference", "name", "description",
            "gravity_justification", "likelihood_justification",
        ],
        filters=["assessment_id", "sr_ov_pair_id", "is_retained", "risk_level"],
        scope_filtered=False,
        has_approve=True,
        required_fields=["assessment_id", "name", "sr_ov_pair_id"],
        field_overrides={
            "description": _html_field("Description"),
            "gravity_justification": _html_field("Gravity justification"),
            "likelihood_justification": _html_field("Likelihood justification"),
            "existing_security_measures": _html_field("Existing security measures"),
            "gravity_level": {
                "type": "integer",
                "description": "Gravity on the assessment impact scale. Combined with likelihood via the matrix to compute risk_level.",
            },
            "likelihood_level": {
                "type": "integer",
                "description": "Likelihood on the assessment likelihood scale. Combined with gravity via the matrix to compute risk_level.",
            },
        },
    )

    aps_fields = [
        "id", "reference", "scenario_id", "order", "stakeholder_id",
        "description", "action_type", "difficulty",
        "created_at", "updated_at",
    ]
    aps_writable = [
        "scenario_id", "order", "stakeholder_id", "description",
        "action_type", "difficulty",
    ]
    _register_crud(
        server, "ebios_attack_path_step", AttackPathStep, "risks.ebios_strategic",
        list_fields=aps_fields,
        writable_fields=aps_writable,
        search_fields=["reference", "description"],
        filters=["scenario_id", "stakeholder_id", "action_type", "difficulty"],
        scope_filtered=False,
        has_approve=False,
        required_fields=["scenario_id", "description"],
        field_overrides={
            "description": _html_field("Description"),
            "action_type": {
                "type": "string",
                "description": "Action type: initial_access, reconnaissance, lateral_movement, privilege_escalation, data_exfiltration, disruption, manipulation, persistence, other.",
            },
            "difficulty": {
                "type": "string",
                "description": "Difficulty: trivial, easy, moderate, difficult, very_difficult.",
            },
            "order": {
                "type": "integer",
                "description": "Position of the step in the attack path (unique per scenario).",
            },
        },
    )

    # ── EBIOS RM Workshop 4 (MITRE ATT&CK, operational scenarios) ─────
    #
    # MitreAttackTechnique is the read-only Enterprise Matrix catalogue,
    # seeded via risks/migrations/0022 and refreshable through the
    # management command refresh_mitre_attack. OperationalScenario inherits
    # gravity from its parent strategic scenario by default and computes
    # risk_level via the assessment risk matrix. AttackTechnique requires
    # at least a MITRE FK or a custom_name (enforced via full_clean).
    #
    # The custom consolidate_ebios_operational_scenario_to_risk tool
    # materialises an OperationalScenario into the unified risk register
    # (idempotent: returns the existing Risk if already consolidated).

    MitreAttackTechnique = _get_model("risks", "MitreAttackTechnique")
    OperationalScenario = _get_model("risks", "OperationalScenario")
    AttackTechnique = _get_model("risks", "AttackTechnique")

    mitre_fields = [
        "id", "mitre_id", "name", "description", "tactic",
        "parent_technique_id", "version", "url", "is_active",
        "created_at", "updated_at",
    ]
    server.register_tool(
        "list_mitre_attack_techniques",
        "List MITRE ATT&CK techniques (Enterprise Matrix). Filterable by tactic, mitre_id and active flag.",
        _list_schema({
            "tactic": {"type": "string", "description": "Filter by tactic (e.g. initial_access)."},
            "mitre_id": {"type": "string", "description": "Exact MITRE identifier (e.g. T1566.001)."},
            "is_active": {"type": "string", "description": "Filter by active flag (true/false)."},
        }),
        require_perm("risks.ebios_operational.read")(
            _list_handler(
                MitreAttackTechnique,
                mitre_fields,
                search_fields=["mitre_id", "name", "description"],
                filters=["tactic", "mitre_id", "is_active"],
                scope_filtered=False,
            )
        ),
    )
    server.register_tool(
        "get_mitre_attack_technique",
        "Get a MITRE ATT&CK technique by ID.",
        _id_schema(),
        require_perm("risks.ebios_operational.read")(
            _get_handler(MitreAttackTechnique, mitre_fields, scope_filtered=False)
        ),
    )

    op_fields = [
        "id", "reference", "assessment_id", "strategic_scenario_id", "name",
        "description", "gravity_level", "gravity_inherited",
        "gravity_override_justification", "likelihood_v",
        "likelihood_justification", "risk_level", "existing_controls",
        "consolidated_risk_id", "mitre_version",
        "created_at", "updated_at",
    ]
    op_writable = [
        "assessment_id", "strategic_scenario_id", "name", "description",
        "gravity_level", "gravity_inherited", "gravity_override_justification",
        "likelihood_v", "likelihood_justification", "existing_controls",
        "mitre_version",
    ]
    _register_crud(
        server, "ebios_operational_scenario", OperationalScenario,
        "risks.ebios_operational",
        list_fields=op_fields,
        writable_fields=op_writable,
        search_fields=[
            "reference", "name", "description",
            "gravity_override_justification", "likelihood_justification",
        ],
        filters=[
            "assessment_id", "strategic_scenario_id",
            "likelihood_v", "gravity_inherited", "risk_level",
        ],
        scope_filtered=False,
        has_approve=True,
        required_fields=["assessment_id", "name", "strategic_scenario_id"],
        field_overrides={
            "description": _html_field("Description"),
            "gravity_override_justification": _html_field("Gravity override justification"),
            "likelihood_justification": _html_field("Likelihood justification"),
            "existing_controls": _html_field("Existing controls"),
            "likelihood_v": {
                "type": "integer",
                "description": "ANSSI operational likelihood V1..V4 stored as integer 1..4 (M4bis Annex B).",
            },
            "gravity_inherited": {
                "type": "string",
                "description": "true when gravity_level is inherited from the parent strategic scenario; set to false and supply gravity_override_justification to override.",
            },
        },
    )

    at_fields = [
        "id", "reference", "scenario_id", "order", "mitre_technique_id",
        "custom_name", "description", "targeted_support_asset_id",
        "difficulty", "detection_difficulty", "created_at", "updated_at",
    ]
    at_writable = [
        "scenario_id", "order", "mitre_technique_id", "custom_name",
        "description", "targeted_support_asset_id", "difficulty",
        "detection_difficulty",
    ]
    _register_crud(
        server, "ebios_attack_technique", AttackTechnique,
        "risks.ebios_operational",
        list_fields=at_fields,
        writable_fields=at_writable,
        search_fields=["reference", "custom_name", "description"],
        filters=[
            "scenario_id", "mitre_technique_id",
            "targeted_support_asset_id", "difficulty", "detection_difficulty",
        ],
        scope_filtered=False,
        has_approve=False,
        required_fields=["scenario_id", "description"],
        field_overrides={
            "description": _html_field("Description"),
            "difficulty": {
                "type": "string",
                "description": "Difficulty: trivial, easy, moderate, difficult, very_difficult.",
            },
            "detection_difficulty": {
                "type": "string",
                "description": "Detection difficulty: trivial, easy, moderate, difficult, very_difficult.",
            },
            "order": {
                "type": "integer",
                "description": "Position of the technique in the operational sequence (unique per scenario).",
            },
        },
    )

    # Custom consolidate tool
    from risks.constants import RiskSourceType as _RiskSourceType
    Risk = _get_model("risks", "Risk")

    def _consolidate_operational_scenario(user, arguments):
        scenario_id = arguments.get("id")
        if not scenario_id:
            raise InvalidParamsError("id is required.")
        try:
            scenario = OperationalScenario.objects.get(pk=scenario_id)
        except OperationalScenario.DoesNotExist:
            return _error(f"OperationalScenario not found: {scenario_id}")
        if scenario.consolidated_risk_id:
            return {
                "status": "already_consolidated",
                "risk_id": str(scenario.consolidated_risk_id),
                "risk_reference": scenario.consolidated_risk.reference,
            }
        risk = Risk.objects.create(
            assessment=scenario.assessment,
            name=scenario.name,
            description=scenario.description,
            risk_source=_RiskSourceType.EBIOS_OPERATIONAL,
            source_entity_id=scenario.pk,
            source_entity_type="risks.OperationalScenario",
            initial_likelihood=scenario.likelihood_v,
            initial_impact=scenario.gravity_level,
            current_likelihood=scenario.likelihood_v,
            current_impact=scenario.gravity_level,
            criteria_snapshot=scenario.criteria_snapshot,
            created_by=user,
        )
        risk.affected_support_assets.set(scenario.targeted_support_assets.all())
        scenario.consolidated_risk = risk
        scenario.save(update_fields=["consolidated_risk"])
        return {
            "status": "consolidated",
            "risk_id": str(risk.pk),
            "risk_reference": risk.reference,
        }

    server.register_tool(
        "consolidate_ebios_operational_scenario_to_risk",
        (
            "Materialise an EBIOS operational scenario into a Risk in the unified register. "
            "Idempotent: returns the existing Risk if the scenario has already been consolidated."
        ),
        _id_schema(),
        require_perm("risks.risk.create")(_consolidate_operational_scenario),
    )

    # ── EBIOS RM Workshop 5 (summary, PACS) ───────────────────────────
    #
    # EbiosSummary is auto-created by the post_save signal on ebios_rm
    # assessments. PACSMeasure links to RiskTreatmentPlans, BaselineGaps
    # and Requirements so the PACS doubles as a treatment roadmap and a
    # traceability matrix. The custom capture_ebios_risk_mappings tool
    # snapshots the assessment risk register into before / after slots.

    EbiosSummary = _get_model("risks", "EbiosSummary")
    PACSMeasure = _get_model("risks", "PACSMeasure")

    summary_fields = [
        "id", "reference", "assessment_id", "residual_risk_strategy",
        "monitoring_plan", "pacs_summary", "next_strategic_cycle_date",
        "next_operational_cycle_date", "validated_by_id", "validated_at",
        "status", "created_at", "updated_at",
    ]
    summary_writable = [
        "assessment_id", "residual_risk_strategy", "monitoring_plan",
        "pacs_summary", "next_strategic_cycle_date",
        "next_operational_cycle_date", "status",
    ]
    _register_crud(
        server, "ebios_summary", EbiosSummary, "risks.ebios_summary",
        list_fields=summary_fields,
        writable_fields=summary_writable,
        search_fields=[
            "reference", "residual_risk_strategy",
            "monitoring_plan", "pacs_summary",
        ],
        filters=["assessment_id", "status"],
        scope_filtered=False,
        has_approve=True,
        required_fields=["assessment_id"],
        field_overrides={
            "residual_risk_strategy": _html_field("Residual risk strategy"),
            "monitoring_plan": _html_field("Monitoring plan"),
            "pacs_summary": _html_field("PACS summary"),
            "status": {
                "type": "string",
                "description": "Summary status: draft, in_progress, under_review, validated.",
            },
        },
    )

    pacs_fields = [
        "id", "reference", "summary_id", "name", "description",
        "measure_type", "owner_id", "start_date", "target_date",
        "completion_date", "cost_estimate", "expected_gain", "priority",
        "status", "progress_percentage", "order",
        "created_at", "updated_at",
    ]
    pacs_writable = [
        "summary_id", "name", "description", "measure_type", "owner_id",
        "start_date", "target_date", "completion_date", "cost_estimate",
        "expected_gain", "priority", "status", "progress_percentage", "order",
    ]
    _register_crud(
        server, "ebios_pacs_measure", PACSMeasure, "risks.ebios_summary",
        list_fields=pacs_fields,
        writable_fields=pacs_writable,
        search_fields=["reference", "name", "description", "expected_gain"],
        filters=["summary_id", "measure_type", "priority", "status", "owner_id"],
        scope_filtered=False,
        has_approve=False,
        required_fields=["summary_id", "name"],
        field_overrides={
            "description": _html_field("Description"),
            "expected_gain": _html_field("Expected gain"),
            "measure_type": {
                "type": "string",
                "description": "PACS measure type: governance, protection, defense, resilience, awareness.",
            },
            "priority": {
                "type": "string",
                "description": "Priority: low, medium, high, critical.",
            },
            "status": {
                "type": "string",
                "description": "Status: planned, in_progress, completed, cancelled, overdue.",
            },
            "progress_percentage": {
                "type": "integer",
                "description": "Progress in percent (0 to 100).",
            },
        },
    )

    # Custom tool: capture the risk register snapshots into the summary.
    def _capture_ebios_risk_mappings(user, arguments):
        summary_id = arguments.get("id")
        if not summary_id:
            raise InvalidParamsError("id is required.")
        try:
            summary = EbiosSummary.objects.get(pk=summary_id)
        except EbiosSummary.DoesNotExist:
            return _error(f"EbiosSummary not found: {summary_id}")
        capture_before = arguments.get("capture_before", True)
        capture_after = arguments.get("capture_after", True)
        if isinstance(capture_before, str):
            capture_before = capture_before.lower() in ("1", "true", "yes")
        if isinstance(capture_after, str):
            capture_after = capture_after.lower() in ("1", "true", "yes")
        summary.capture_risk_mappings(
            capture_before=bool(capture_before),
            capture_after=bool(capture_after),
        )
        summary.refresh_from_db()
        return {
            "id": str(summary.pk),
            "reference": summary.reference,
            "risk_mapping_before": summary.risk_mapping_before,
            "risk_mapping_after": summary.risk_mapping_after,
        }

    server.register_tool(
        "capture_ebios_risk_mappings",
        (
            "Snapshot the assessment's risk register into the EbiosSummary "
            "before / after JSON slots so the cartography can render the "
            "treatment effect. Pass capture_before / capture_after to scope "
            "the update; both default to true."
        ),
        {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "UUID of the EbiosSummary to update."},
                "capture_before": {
                    "type": "string",
                    "description": "Update risk_mapping_before (default true).",
                },
                "capture_after": {
                    "type": "string",
                    "description": "Update risk_mapping_after (default true).",
                },
            },
            "required": ["id"],
        },
        require_perm("risks.ebios_summary.update")(_capture_ebios_risk_mappings),
    )


# ── Incidents Module ──────────────────────────────────────

# Enum values below are copied from `incidents/constants.py` (and, for the three
# shared taxonomies, from `context`, `risks` and `compliance`). They are spelled
# out rather than derived so the JSON schema an MCP client caches stays a
# literal contract; a divergence is caught by the model's own `full_clean()`.
_INC_TLP = ["clear", "green", "amber", "amber_strict", "red"]
_INC_CRITICALITY = ["low", "medium", "high", "critical"]
_INC_DETECTION_SOURCES = [
    "internal_monitoring", "soc_alert", "employee_report", "customer_report",
    "supplier_notification", "authority_notification", "researcher", "audit",
    "penetration_test", "threat_intel", "other",
]
_INC_THREAT_CATEGORIES = [
    "malware", "social_engineering", "unauthorized_access", "denial_of_service",
    "data_breach", "physical_attack", "espionage", "fraud", "sabotage",
    "human_error", "system_failure", "network_failure", "power_failure",
    "natural_disaster", "fire", "water_damage", "theft", "vandalism",
    "supply_chain", "insider_threat", "ransomware", "apt", "other",
]
_INC_EFFECTIVENESS = ["effective", "partially_effective", "not_effective"]
_INC_REGIMES = [
    "gdpr_art33_authority", "gdpr_art34_data_subject", "gdpr_art33_2_controller",
    "nis2_early_warning", "nis2_notification", "nis2_intermediate", "nis2_final",
    "nis2_recipients", "dora_initial", "dora_intermediate", "dora_final",
    "eprivacy", "cra", "sector_regulator", "law_enforcement", "cert_csirt",
    "contractual_customer", "contractual_supplier", "insurer",
    "internal_management", "public_communication", "other",
]
_INC_RECIPIENT_KINDS = [
    "supervisory_authority", "csirt", "competent_authority",
    "financial_regulator", "law_enforcement", "data_subject", "customer",
    "controller", "supplier", "insurer", "internal", "public",
]
_INC_CLOCK_ANCHORS = [
    "occurred_at", "detected_at", "awareness_at", "significance_determined_at",
    "previous_stage",
]
_INC_CHANNELS = ["portal", "email", "postal", "phone", "api", "in_person", "public_notice"]
_INC_CUSTODY_ACTIONS = [
    "collected", "sealed", "transferred", "accessed", "copied", "analysed",
    "integrity_verified", "released", "returned", "destroyed",
]


def _incident_child_parent(parent_field, parent_model, user, arguments):
    """Resolve and scope-check the parent a child row is being appended to.

    ``_create_handler`` validates the foreign key exists, never that the caller
    may see what it points at. The three append-only ledgers get their own
    create handlers, so the check lives here rather than being reproduced in
    each of them.
    """
    pk = arguments.get(f"{parent_field}_id")
    if not pk:
        raise InvalidParamsError(f"{parent_field}_id is required.")
    try:
        parent = parent_model.objects.get(pk=pk)
    except (parent_model.DoesNotExist, ValueError, ValidationError):
        return None, _error(f"{parent_model.__name__} not found.")
    if not _filter_by_scopes(parent_model.objects.filter(pk=parent.pk), user).exists():
        return None, _error("Access denied: object is outside your allowed scopes.")
    return parent, None


def _register_append_only_reads(server, entity_name, plural, model_class, perm_prefix,
                                list_fields, search_fields=None, filters=None):
    """Register the read half of an append-only ledger: list, get, history.

    Deliberately no ``update_*`` and no ``delete_*``: ``save()`` on an existing
    row and ``delete()`` both raise ``LifecycleProtectedError`` on these three
    models, so registering those tools would advertise an operation that can
    only ever fail. The create half is bespoke (the actor is forced to the
    caller), so it is registered by ``_register_incidents_tools`` itself.
    """
    display_name = entity_name.replace("_", " ")
    filter_props = {f: {"type": "string", "description": f"Filter by {f}"} for f in (filters or [])}
    server.register_tool(
        f"list_{plural}",
        f"List {display_name}s with optional search and filters. Append-only "
        f"ledger: there is no update or delete tool for it.",
        _list_schema(filter_props),
        require_perm(f"{perm_prefix}.read")(
            _list_handler(model_class, list_fields, search_fields, filters, True)
        ),
    )
    server.register_tool(
        f"get_{entity_name}",
        f"Get a {display_name} by ID",
        _id_schema(),
        require_perm(f"{perm_prefix}.read")(_get_handler(model_class, list_fields, True)),
    )
    server.register_tool(
        f"get_{entity_name}_history",
        f"Return the change history of a {display_name}. On an append-only "
        f"ledger this is the tamper-detection surface: a row whose trail shows "
        f"more writes than the design allows has been altered outside the "
        f"supported paths.",
        _obj_schema(
            {
                "id": {"type": "string", "description": f"UUID of the {display_name}"},
                "limit": {"type": "integer", "description": "Max entries (default 100, max 500)."},
                "offset": {"type": "integer", "description": "Entries to skip (pagination)."},
            },
            required=["id"],
        ),
        require_perm(f"{perm_prefix}.read")(_history_handler(model_class, True)),
    )


def _unjudged_verdict_fields(obj):
    """Tri-state verdict fields still unanswered on ``obj``.

    ``Incident.is_significant`` / ``.cross_border_impact`` /
    ``.suspected_malicious`` and ``PersonalDataBreach.high_risk_to_rights`` are
    ``BooleanField(null=True, default=None)`` **without** ``blank=True``. That
    is deliberate: each is a judgement with three states, and the third is *not
    yet judged*. ``BooleanField.formfield()`` forces ``required=False`` and
    ``ModelForm._get_validation_exclusions()`` drops such a field from
    ``full_clean()`` while it is unset, which is why the web form happily opens
    an incident carrying no NIS2 verdict.

    ``_create_handler``, ``_batch_create_handler`` and ``_update_handler`` call
    ``full_clean()`` with no exclusions. Without this list every
    ``create_incident`` would be refused with *This field cannot be blank*
    unless the caller invented all three verdicts on the spot, and every
    ``update_incident`` on an incident opened from the web UI would be refused
    for the same reason. Worse, an invented ``cross_border_impact`` immediately
    forces ``cross_border_justification``: a written justification for a
    judgement nobody made. The MCP surface therefore validates exactly what the
    form validates, and the verdicts stay reachable as ordinary writable fields
    once somebody has actually taken them.
    """
    return [
        f.name
        for f in obj._meta.fields
        if f.null and not f.blank and not f.is_relation
        and getattr(obj, f.attname) is None
    ]


def _verdict_create_handler(model_class, writable_fields, m2m_fields=None):
    """``_create_handler`` with the unanswered tri-state verdicts left unvalidated."""
    m2m_fields = m2m_fields or {}

    def handler(user, arguments):
        kwargs = {}
        m2m_values = {}
        for field_name in writable_fields:
            if field_name in arguments:
                if field_name in m2m_fields:
                    m2m_values[field_name] = arguments[field_name]
                else:
                    kwargs[_fk_kwarg_name(model_class, field_name)] = _coerce_field_value(
                        model_class, field_name, arguments[field_name])
        if hasattr(model_class, "created_by"):
            kwargs["created_by"] = user
        try:
            obj = model_class(**kwargs)
            obj.full_clean(exclude=_unjudged_verdict_fields(obj))
            obj.save()
            for param_name, ids in m2m_values.items():
                getattr(obj, m2m_fields[param_name]).set(ids)
            ts_status = _apply_timestamp_override(obj, model_class, arguments, user)
        except (ValidationError, Exception) as e:
            return _error(str(e))
        result = _serialize_obj(obj, [f.name for f in model_class._meta.fields])
        if ts_status == "ignored_no_permission":
            result["warning"] = (
                "created_at / updated_at were ignored: this account lacks the "
                "system.data_import.override_dates permission."
            )
        return result
    return handler


def _verdict_update_handler(model_class, writable_fields, m2m_fields=None):
    """``_update_handler`` with the unanswered tri-state verdicts left unvalidated."""
    m2m_fields = m2m_fields or {}

    def handler(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if not _filter_by_scopes(model_class.objects.filter(pk=pk), user).exists():
            return _error("Access denied: object is outside your allowed scopes.")
        m2m_values = {}
        for field_name in writable_fields:
            if field_name in arguments:
                if field_name in m2m_fields:
                    m2m_values[field_name] = arguments[field_name]
                else:
                    setattr(obj, _fk_kwarg_name(model_class, field_name),
                            _coerce_field_value(model_class, field_name,
                                                arguments[field_name]))
        try:
            obj.full_clean(exclude=_unjudged_verdict_fields(obj))
            obj.save()
            for param_name, ids in m2m_values.items():
                getattr(obj, m2m_fields[param_name]).set(ids)
        except (ValidationError, Exception) as e:
            return _error(str(e))
        return _serialize_obj(obj, [f.name for f in model_class._meta.fields])
    return handler


def _verdict_batch_create_handler(model_class, writable_fields, m2m_fields=None):
    """``_batch_create_handler`` built on the two handlers above.

    Same contract: non-atomic, ``match_on`` turns an item into an idempotent
    upsert, and the summary reports created / updated / error counts.
    """
    create = _verdict_create_handler(model_class, writable_fields, m2m_fields)
    update = _verdict_update_handler(model_class, writable_fields, m2m_fields)
    m2m_fields = m2m_fields or {}

    def handler(user, arguments):
        items = arguments.get("items", [])
        if not isinstance(items, list) or not items:
            return _error("'items' must be a non-empty array of objects.")
        if len(items) > 500:
            return _error("Batch size limited to 500 items.")
        match_on = arguments.get("match_on") or []
        if match_on:
            if not isinstance(match_on, list) or not all(isinstance(f, str) for f in match_on):
                return _error("'match_on' must be an array of field names.")
            unknown = [f for f in match_on if f not in writable_fields]
            if unknown:
                return _error(
                    "match_on fields must be writable fields; unknown: " + ", ".join(unknown))
            if any(f in m2m_fields for f in match_on):
                return _error("match_on does not support many-to-many fields.")

        results = []
        counts = {"created": 0, "updated": 0, "errors": 0}
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                results.append({"index": idx, "status": "error",
                                "errors": f"Expected an object, got {type(item).__name__}."})
                counts["errors"] += 1
                continue
            existing = None
            if match_on:
                missing = [f for f in match_on if item.get(f) in (None, "")]
                if missing:
                    results.append({"index": idx, "status": "error",
                                    "errors": "Missing match_on value(s): " + ", ".join(missing)})
                    counts["errors"] += 1
                    continue
                lookup = {
                    _fk_kwarg_name(model_class, f): _coerce_field_value(model_class, f, item[f])
                    for f in match_on
                }
                matches = list(_filter_by_scopes(model_class.objects.filter(**lookup), user)[:2])
                if len(matches) > 1:
                    results.append({"index": idx, "status": "error",
                                    "errors": "match_on matched multiple existing records; "
                                              "use a more specific key."})
                    counts["errors"] += 1
                    continue
                existing = matches[0] if matches else None
            if existing is not None:
                outcome = update(user, {**item, "id": str(existing.pk)})
                status = "updated"
            else:
                outcome = create(user, item)
                status = "created"
            if isinstance(outcome, dict) and outcome.get("isError"):
                # `_error()` wraps the message in a JSON envelope; unwrap it so a
                # per-item error reads the same here as in `_batch_create_handler`.
                raw = outcome["content"][0]["text"]
                try:
                    raw = json.loads(raw).get("error", raw)
                except (json.JSONDecodeError, AttributeError, TypeError):
                    pass
                results.append({"index": idx, "status": "error", "errors": raw})
                counts["errors"] += 1
                continue
            entry = {"index": idx, "status": status, "id": outcome.get("id"),
                     "reference": outcome.get("reference")}
            if outcome.get("warning"):
                entry["timestamps"] = "ignored_no_permission"
            results.append(entry)
            counts[status] += 1
        return {
            "status": "completed" if counts["errors"] == 0 else "completed_with_errors",
            "total": len(items),
            "created": counts["created"],
            "updated": counts["updated"],
            "errors": counts["errors"],
            "results": results,
        }
    return handler


def _register_verdict_write_tools(server, entity_name, model_class, perm_prefix,
                                  writable_fields, m2m_fields=None):
    """Re-register create / batch_create / update over the generic ones.

    Same shape as the supplier tools, which re-register ``create_supplier`` and
    ``update_supplier`` after ``_register_crud`` to add the logo fetch. Only the
    handler changes: the schemas ``_register_crud`` published stay in place, so
    the tool contract an MCP client already cached is untouched.
    """
    for suffix, factory, action in (
        (f"create_{entity_name}", _verdict_create_handler, "create"),
        (f"batch_create_{entity_name}s", _verdict_batch_create_handler, "create"),
        (f"update_{entity_name}", _verdict_update_handler, "update"),
    ):
        published = server.get_tool(suffix)
        server.register_tool(
            suffix, published["description"], published["inputSchema"],
            require_perm(f"{perm_prefix}.{action}")(
                factory(model_class, writable_fields, m2m_fields)
            ),
        )


def _register_incidents_tools(server):
    """Register the module 6 (incidents) tool family.

    Every entity is registered with ``scope_filtered=True``. The four scoped
    parents carry their own ``scopes`` M2M; the seven child entities declare
    ``scope_parent_lookup`` on the model, which ``core.scoping`` resolves for
    the MCP layer exactly as it does for the web and DRF surfaces. The two
    catalogue entities (``ReportingAuthority``, ``ReportingObligationTemplate``)
    declare neither, so the lookup resolves to ``None`` and the flag is a no-op
    on them: the CNIL is the CNIL for every scope of the ISMS.
    """
    Incident = _get_model("incidents", "Incident")
    SecurityEvent = _get_model("incidents", "SecurityEvent")
    IncidentResponsePlan = _get_model("incidents", "IncidentResponsePlan")
    IncidentResponseAction = _get_model("incidents", "IncidentResponseAction")
    IncidentTimelineEntry = _get_model("incidents", "IncidentTimelineEntry")
    IncidentEvidence = _get_model("incidents", "IncidentEvidence")
    EvidenceCustodyEvent = _get_model("incidents", "EvidenceCustodyEvent")
    PostIncidentReview = _get_model("incidents", "PostIncidentReview")
    IncidentNotification = _get_model("incidents", "IncidentNotification")
    NotificationFiling = _get_model("incidents", "NotificationFiling")
    ReportingAuthority = _get_model("incidents", "ReportingAuthority")
    ReportingObligationTemplate = _get_model("incidents", "ReportingObligationTemplate")
    PersonalDataBreach = _get_model("incidents", "PersonalDataBreach")

    # ── Incident ───────────────────────────────────────────

    incident_fields = [
        "id", "reference", "workflow_state", "scopes", "title", "summary",
        "description", "category", "severity", "initial_severity",
        "detection_source", "is_exercise", "tlp",
        "confidentiality_impact", "integrity_impact", "availability_impact",
        "personal_data_involved",
        "occurred_at", "detected_at", "awareness_at", "awareness_justification",
        "declared_at", "triaged_at", "contained_at", "eradicated_at",
        "recovered_at", "closed_at",
        "outage_duration", "estimated_cost", "no_obligation_justification",
        "is_significant", "significance_determined_at", "significance_justification",
        "cross_border_impact", "cross_border_justification",
        "suspected_malicious", "suspected_malicious_justification",
        "response_plan_id", "response_plan_name",
        "reporter_id", "reporter_name",
        "incident_manager_id", "incident_manager_name",
        "parent_incident_id", "parent_incident_reference",
        "origin_supplier_id", "origin_supplier_name",
        "affected_suppliers", "affected_essential_assets", "affected_support_assets",
        "affected_sites", "affected_activities", "threats",
        "exploited_vulnerabilities", "realised_risks", "linked_requirements",
        "awareness_gap", "time_to_contain", "time_to_recover",
        "severity_raised_since_triage",
        "created_at",
    ]
    incident_writable = [
        "title", "summary", "description", "category", "severity",
        "detection_source", "is_exercise", "tlp",
        "confidentiality_impact", "integrity_impact", "availability_impact",
        "personal_data_involved",
        "occurred_at", "detected_at", "awareness_at", "awareness_justification",
        "outage_duration", "estimated_cost", "no_obligation_justification",
        "is_significant", "significance_determined_at", "significance_justification",
        "cross_border_impact", "cross_border_justification",
        "suspected_malicious", "suspected_malicious_justification",
        "response_plan_id", "reporter_id", "incident_manager_id",
        "parent_incident_id", "origin_supplier_id",
        "scope_ids", "affected_supplier_ids", "affected_essential_asset_ids",
        "affected_support_asset_ids", "affected_site_ids", "affected_activity_ids",
        "threat_ids", "exploited_vulnerability_ids", "realised_risk_ids",
        "linked_requirement_ids",
    ]

    _register_crud(
        server, "incident", Incident, "incidents.incident",
        list_fields=incident_fields,
        writable_fields=incident_writable,
        search_fields=["reference", "title", "summary", "description"],
        filters=["category", "severity", "detection_source", "tlp", "is_exercise",
                 "personal_data_involved", "is_significant", "workflow_state",
                 "incident_manager_id", "response_plan_id", "parent_incident_id"],
        required_fields=["title", "detected_at"],
        m2m_fields={
            "scope_ids": "scopes",
            "affected_supplier_ids": "affected_suppliers",
            "affected_essential_asset_ids": "affected_essential_assets",
            "affected_support_asset_ids": "affected_support_assets",
            "affected_site_ids": "affected_sites",
            "affected_activity_ids": "affected_activities",
            "threat_ids": "threats",
            "exploited_vulnerability_ids": "exploited_vulnerabilities",
            "realised_risk_ids": "realised_risks",
            "linked_requirement_ids": "linked_requirements",
        },
        field_overrides={
            "title": {"type": "string", "description": "Short title of the incident."},
            "summary": {"type": "string", "description": "One-paragraph executive summary, for management review and external communication."},
            "description": {"type": "string", "description": "Full narrative of the incident."},
            "category": {
                "type": "string",
                "description": "Incident category. Reuses the threat taxonomy: an incident is a threat that materialised.",
                "enum": _INC_THREAT_CATEGORIES,
            },
            "severity": {
                "type": "string",
                "description": "Severity, read through the response plan's classification scale.",
                "enum": _INC_CRITICALITY,
            },
            "detection_source": {
                "type": "string",
                "description": "How the incident came to light.",
                "enum": _INC_DETECTION_SOURCES,
            },
            "tlp": {
                "type": "string",
                "description": "Traffic Light Protocol handling caveat for the incident file and its evidence.",
                "enum": _INC_TLP,
            },
            "is_exercise": {"type": "boolean", "description": "Simulation or tabletop run through the real process. Exercises never generate notification obligations."},
            "confidentiality_impact": {"type": "boolean", "description": "Confidentiality was impacted."},
            "integrity_impact": {"type": "boolean", "description": "Integrity was impacted."},
            "availability_impact": {"type": "boolean", "description": "Availability was impacted."},
            "personal_data_involved": {"type": "boolean", "description": "Personal data was, or may have been, affected. Setting it forces the GDPR Art. 33 obligation and the breach record."},
            "occurred_at": {"type": "string", "description": "Best estimate of when the incident began (ISO 8601 date-time)."},
            "detected_at": {"type": "string", "description": "Technical detection (ISO 8601 date-time). Base of the mean-time-to-detect KPI."},
            "awareness_at": {"type": "string", "description": "The legal clock anchor (GDPR Art. 33(1), NIS2 Art. 23), ISO 8601. Defaults to the detection time when left empty."},
            "awareness_justification": {"type": "string", "description": "Why legal awareness postdates technical detection. Mandatory whenever the two differ."},
            "outage_duration": {"type": "string", "description": "Measured service interruption, as a duration (e.g. '04:30:00' or '1 02:00:00')."},
            "estimated_cost": {"type": "string", "description": "Estimated cost of the incident (decimal)."},
            "no_obligation_justification": {"type": "string", "description": "Why nothing is owed to anyone. Mandatory when triage produced no notification obligation."},
            "is_significant": {"type": "boolean", "description": "NIS2 Art. 23(3) significance verdict. Deliberately separate from severity."},
            "significance_determined_at": {"type": "string", "description": "When significance was determined (ISO 8601). Usable as a statutory clock anchor in its own right."},
            "significance_justification": {"type": "string", "description": "Reasoning behind the significance verdict."},
            "cross_border_impact": {"type": "boolean", "description": "Entities or users in more than one Member State are affected."},
            "cross_border_justification": {"type": "string", "description": "Reasoning behind the cross-border verdict. Mandatory once the verdict is set."},
            "suspected_malicious": {"type": "boolean", "description": "NIS2 Art. 23(4)(a): whether the incident is suspected to result from a malicious act."},
            "suspected_malicious_justification": {"type": "string", "description": "Reasoning behind the malicious-act verdict. Mandatory once the verdict is set."},
            "response_plan_id": {"type": "string", "description": "UUID of the incident response plan this incident is handled under. Use list_incident_response_plans to get valid IDs."},
            "reporter_id": {"type": "string", "description": "UUID of the user who reported it. Use list_users to get valid IDs."},
            "incident_manager_id": {"type": "string", "description": "UUID of the single accountable responder (A.5.24). Use list_users to get valid IDs."},
            "parent_incident_id": {"type": "string", "description": "UUID of the major incident this one belongs to, or the merge target. Use list_incidents to get valid IDs."},
            "origin_supplier_id": {"type": "string", "description": "UUID of the third party whose breach or outage caused this. Use list_suppliers to get valid IDs."},
            "scope_ids": {"type": "array", "items": {"type": "string"}, "description": "Scopes this incident belongs to (RG-01). Every child row inherits its tenancy from here."},
            "affected_supplier_ids": {"type": "array", "items": {"type": "string"}, "description": "Suppliers impacted or notified downstream (not the cause: that is origin_supplier_id)."},
            "affected_essential_asset_ids": {"type": "array", "items": {"type": "string"}, "description": "Essential assets affected. Use list_essential_assets."},
            "affected_support_asset_ids": {"type": "array", "items": {"type": "string"}, "description": "Support assets affected. Use list_support_assets."},
            "affected_site_ids": {"type": "array", "items": {"type": "string"}, "description": "Sites affected. Use list_sites."},
            "affected_activity_ids": {"type": "array", "items": {"type": "string"}, "description": "Business activities halted. Use list_activities."},
            "threat_ids": {"type": "array", "items": {"type": "string"}, "description": "The threats that materialised. Use list_threats."},
            "exploited_vulnerability_ids": {"type": "array", "items": {"type": "string"}, "description": "Vulnerabilities exploited. Use list_vulnerabilities."},
            "realised_risk_ids": {"type": "array", "items": {"type": "string"}, "description": "Registered risks that actually materialised. Use list_risks."},
            "linked_requirement_ids": {"type": "array", "items": {"type": "string"}, "description": "Controls in play. Use list_requirements."},
        },
    )
    # The three NIS2 verdicts are tri-state and start unjudged; see
    # `_unjudged_verdict_fields` for why the generic handlers cannot open or
    # edit an incident that has not taken them yet.
    _register_verdict_write_tools(
        server, "incident", Incident, "incidents.incident",
        incident_writable,
        m2m_fields={
            "scope_ids": "scopes",
            "affected_supplier_ids": "affected_suppliers",
            "affected_essential_asset_ids": "affected_essential_assets",
            "affected_support_asset_ids": "affected_support_assets",
            "affected_site_ids": "affected_sites",
            "affected_activity_ids": "affected_activities",
            "threat_ids": "threats",
            "exploited_vulnerability_ids": "exploited_vulnerabilities",
            "realised_risk_ids": "realised_risks",
            "linked_requirement_ids": "linked_requirements",
        },
    )

    # ── SecurityEvent ──────────────────────────────────────

    event_fields = [
        "id", "reference", "workflow_state", "scopes", "title", "description",
        "event_class", "category", "detection_source", "source_reference",
        "occurred_at", "detected_at", "reported_at",
        "reporter_id", "reporter_name", "reporter_label", "is_anonymous",
        "assessed_by_id", "assessed_by_name", "assessed_at", "assessment_notes",
        "triage_decision",
        "incident_id", "incident_reference",
        "vulnerability_id", "vulnerability_reference",
        "duplicate_of_id", "duplicate_of_reference",
        "reported_by_supplier_id", "reported_by_supplier_name",
        "affected_support_assets", "affected_essential_assets", "affected_sites",
        "reporting_delay_hours",
        "created_at",
    ]
    event_writable = [
        "title", "description", "event_class", "category", "detection_source",
        "source_reference", "occurred_at", "detected_at", "reported_at",
        "is_anonymous", "reporter_id", "reporter_label",
        "reported_by_supplier_id", "duplicate_of_id",
        "assessed_by_id", "assessment_notes",
        "scope_ids", "affected_support_asset_ids", "affected_essential_asset_ids",
        "affected_site_ids",
    ]

    _register_crud(
        server, "security_event", SecurityEvent, "incidents.event",
        list_fields=event_fields,
        writable_fields=event_writable,
        search_fields=["reference", "title", "description", "source_reference"],
        filters=["event_class", "category", "detection_source", "is_anonymous",
                 "triage_decision", "workflow_state", "incident_id",
                 "reported_by_supplier_id"],
        required_fields=["title", "detected_at", "reported_at"],
        m2m_fields={
            "scope_ids": "scopes",
            "affected_support_asset_ids": "affected_support_assets",
            "affected_essential_asset_ids": "affected_essential_assets",
            "affected_site_ids": "affected_sites",
        },
        field_overrides={
            "title": {"type": "string", "description": "Short title of the observation."},
            "description": {"type": "string", "description": "What was observed, in the reporter's own words. Never rewritten on promotion."},
            "event_class": {
                "type": "string",
                "description": "What kind of occurrence this is. Governs which promotion targets are legal.",
                "enum": ["event", "weakness", "incident"],
            },
            "category": {
                "type": "string",
                "description": "Provisional classification, refined on promotion.",
                "enum": _INC_THREAT_CATEGORIES,
            },
            "detection_source": {
                "type": "string",
                "description": "How the event came to light.",
                "enum": _INC_DETECTION_SOURCES,
            },
            "source_reference": {"type": "string", "description": "SIEM alert id, ticket number or CERT bulletin reference."},
            "occurred_at": {"type": "string", "description": "Best estimate of when the occurrence started (ISO 8601)."},
            "detected_at": {"type": "string", "description": "When it was detected (ISO 8601). Base of the mean-time-to-detect KPI."},
            "reported_at": {"type": "string", "description": "When it reached the incident response function (ISO 8601)."},
            "is_anonymous": {"type": "boolean", "description": "Reported through the anonymous channel A.6.8 requires."},
            "reporter_id": {"type": "string", "description": "UUID of the reporting user. Use list_users to get valid IDs."},
            "reporter_label": {"type": "string", "description": "Identity of an external or non-user reporter: a customer, a researcher, an anonymous line."},
            "reported_by_supplier_id": {"type": "string", "description": "UUID of the supplier that notified us (NIS2 supply chain, GDPR Art. 33(2)). Use list_suppliers."},
            "duplicate_of_id": {"type": "string", "description": "UUID of the earlier security event this one repeats. Use list_security_events."},
            "assessed_by_id": {"type": "string", "description": "UUID of the user who performed the A.5.25 assessment. Use list_users."},
            "assessment_notes": {"type": "string", "description": "The reasoning behind the triage decision. An undocumented assessment is not an assessment."},
            "scope_ids": {"type": "array", "items": {"type": "string"}, "description": "Scopes this event belongs to (RG-01). A promoted incident inherits them."},
            "affected_support_asset_ids": {"type": "array", "items": {"type": "string"}, "description": "Support assets involved. Use list_support_assets."},
            "affected_essential_asset_ids": {"type": "array", "items": {"type": "string"}, "description": "Essential assets involved. Use list_essential_assets."},
            "affected_site_ids": {"type": "array", "items": {"type": "string"}, "description": "Sites involved. Use list_sites."},
        },
    )

    # ── IncidentResponsePlan ───────────────────────────────

    plan_fields = [
        "id", "reference", "workflow_state", "scopes", "name", "purpose",
        "procedure", "classification_scale", "escalation_matrix",
        "reporting_channels", "evidence_procedure", "lessons_learned_procedure",
        "applicable_regimes",
        "owner_id", "owner_name", "approved_by_id", "approved_by_name",
        "approved_at", "effective_from", "review_date", "last_exercise_date",
        "responsible_roles", "linked_requirements",
        "is_in_force", "is_review_overdue", "is_exercise_overdue",
        "created_at",
    ]
    plan_writable = [
        "name", "purpose", "procedure", "classification_scale",
        "escalation_matrix", "reporting_channels", "evidence_procedure",
        "lessons_learned_procedure", "applicable_regimes",
        "owner_id", "approved_by_id", "approved_at", "effective_from",
        "review_date", "scope_ids", "responsible_role_ids", "linked_requirement_ids",
    ]

    _register_crud(
        server, "incident_response_plan", IncidentResponsePlan, "incidents.response_plan",
        list_fields=plan_fields,
        writable_fields=plan_writable,
        search_fields=["reference", "name", "purpose", "procedure"],
        filters=["workflow_state", "owner_id", "approved_by_id"],
        required_fields=["name"],
        m2m_fields={
            "scope_ids": "scopes",
            "responsible_role_ids": "responsible_roles",
            "linked_requirement_ids": "linked_requirements",
        },
        field_overrides={
            "name": {"type": "string", "description": "Name of the response plan."},
            "purpose": {"type": "string", "description": "What the plan is for."},
            "procedure": _html_field("Response procedure"),
            "classification_scale": _html_field("What low / medium / high / critical mean in this organisation's terms"),
            "escalation_matrix": _html_field("Who is escalated to, at which severity, within which delay"),
            "reporting_channels": _html_field("How events and weaknesses are reported, including the anonymous channel A.6.8 requires"),
            "evidence_procedure": _html_field("Identification, collection, acquisition and preservation of evidence (A.5.28)"),
            "lessons_learned_procedure": _html_field("How knowledge gained from incidents strengthens controls (A.5.27)"),
            "applicable_regimes": {
                "type": "array",
                "items": {"type": "string", "enum": _INC_REGIMES},
                "description": "Regulatory regimes this plan is built to satisfy. Triage instantiates one notification obligation per applicable regime.",
            },
            "owner_id": {"type": "string", "description": "UUID of the plan owner. Use list_users to get valid IDs."},
            "approved_by_id": {"type": "string", "description": "UUID of the approver. Use list_users to get valid IDs."},
            "approved_at": {"type": "string", "description": "Approval date (ISO 8601 date)."},
            "effective_from": {"type": "string", "description": "Date the plan takes effect (ISO 8601 date)."},
            "review_date": {"type": "string", "description": "Next review date (ISO 8601 date)."},
            "scope_ids": {"type": "array", "items": {"type": "string"}, "description": "Scopes this plan covers (RG-01)."},
            "responsible_role_ids": {"type": "array", "items": {"type": "string"}, "description": "Roles accountable under this plan. Use list_roles."},
            "linked_requirement_ids": {"type": "array", "items": {"type": "string"}, "description": "Requirements this plan satisfies. Use list_requirements."},
        },
    )

    # ── IncidentResponseAction ─────────────────────────────

    action_fields = [
        "id", "reference", "incident_id", "incident_reference", "action_type",
        "title", "description", "status",
        "owner_id", "owner_name", "performed_by_id", "performed_by_name",
        "due_at", "started_at", "completed_at", "outcome", "effectiveness",
        "is_overdue", "execution_duration",
        "created_at",
    ]
    action_writable = [
        "incident_id", "action_type", "title", "description", "status",
        "owner_id", "performed_by_id", "due_at", "started_at", "completed_at",
        "outcome", "effectiveness",
    ]

    _register_crud(
        server, "incident_response_action", IncidentResponseAction, "incidents.incident",
        list_fields=action_fields,
        writable_fields=action_writable,
        search_fields=["reference", "title", "description", "outcome"],
        filters=["incident_id", "action_type", "status", "owner_id",
                 "performed_by_id", "effectiveness"],
        has_approve=False,
        required_fields=["incident_id", "action_type", "title"],
        field_overrides={
            "incident_id": {"type": "string", "description": "UUID of the parent incident. Use list_incidents to get valid IDs."},
            "action_type": {
                "type": "string",
                "description": "Which ISO 27035 response step this action belongs to.",
                "enum": ["containment", "eradication", "recovery", "evidence_collection",
                         "communication", "escalation", "workaround", "other"],
            },
            "title": {"type": "string", "description": "What is being done, in the imperative."},
            "description": {"type": "string", "description": "The command to run, the runbook section, the person to call."},
            "status": {
                "type": "string",
                "description": "Operational progress. A plain status column, not a lifecycle state.",
                "enum": ["planned", "in_progress", "done", "blocked", "cancelled"],
            },
            "owner_id": {"type": "string", "description": "UUID of the user accountable for the step. Use list_users."},
            "performed_by_id": {"type": "string", "description": "UUID of the user who actually executed it. Use list_users."},
            "due_at": {"type": "string", "description": "Due date-time (ISO 8601). Drives the escalation sweep."},
            "started_at": {"type": "string", "description": "Execution start (ISO 8601)."},
            "completed_at": {"type": "string", "description": "Execution end (ISO 8601)."},
            "outcome": {"type": "string", "description": "What the action actually achieved. A containment step marked done with no stated outcome is not evidence of containment."},
            "effectiveness": {
                "type": "string",
                "description": "Whether the step worked, assessed during the post-incident review (A.5.27).",
                "enum": _INC_EFFECTIVENESS,
            },
        },
    )

    # ── IncidentEvidence ───────────────────────────────────

    evidence_fields = [
        "id", "reference", "workflow_state",
        "incident_id", "incident_reference", "incident_name",
        "title", "description", "evidence_type",
        "collected_at", "collected_by_id", "collected_by_name",
        "collection_method",
        "source_support_asset_id", "source_support_asset_reference",
        "source_description", "storage_location",
        "original_filename", "file_size", "content_hash", "hash_algorithm",
        "sealed_at", "last_integrity_check_at", "last_integrity_check_ok",
        "tlp", "legal_hold", "retention_until", "admissibility_notes",
        "destruction_authorised_by_id", "destruction_authorised_by_name",
        "has_file", "is_registered_by_reference", "is_sealed",
        "retention_expired", "is_destroyable",
        "created_at",
    ]
    evidence_writable = [
        "incident_id", "title", "description", "evidence_type", "tlp",
        "collected_at", "collected_by_id", "collection_method",
        "source_support_asset_id", "source_description",
        "content_hash", "hash_algorithm", "original_filename", "file_size",
        "storage_location", "legal_hold", "retention_until", "admissibility_notes",
    ]

    _register_crud(
        server, "incident_evidence", IncidentEvidence, "incidents.evidence",
        list_fields=evidence_fields,
        writable_fields=evidence_writable,
        search_fields=["reference", "title", "description", "storage_location",
                       "original_filename", "content_hash"],
        filters=["incident_id", "evidence_type", "hash_algorithm", "tlp",
                 "legal_hold", "workflow_state", "collected_by_id"],
        required_fields=["incident_id", "title", "evidence_type"],
        field_overrides={
            "incident_id": {"type": "string", "description": "UUID of the parent incident. Use list_incidents to get valid IDs."},
            "title": {"type": "string", "description": "Name of the artefact."},
            "description": {"type": "string", "description": "What the artefact is and why it matters."},
            "evidence_type": {
                "type": "string",
                "description": "Kind of artefact.",
                "enum": ["disk_image", "memory_dump", "log_extract", "network_capture",
                         "screenshot", "email", "document", "database_export",
                         "malware_sample", "physical_device", "witness_statement", "other"],
            },
            "tlp": {
                "type": "string",
                "description": "Traffic Light Protocol handling caveat. Defaults to red.",
                "enum": _INC_TLP,
            },
            "collected_at": {"type": "string", "description": "Acquisition date-time (ISO 8601). Frozen once the item is sealed."},
            "collected_by_id": {"type": "string", "description": "UUID of the user who acquired it. Frozen once sealed. Use list_users."},
            "collection_method": {"type": "string", "description": "How it was acquired. Frozen once sealed."},
            "source_support_asset_id": {"type": "string", "description": "UUID of the support asset the artefact came from. Use list_support_assets."},
            "source_description": {"type": "string", "description": "Free-text description of the source when no asset is recorded."},
            "content_hash": {"type": "string", "description": "Hex digest of the artefact. Frozen once sealed. Never assert a verification verdict by writing here: call verify_evidence_integrity."},
            "hash_algorithm": {
                "type": "string",
                "description": "Digest algorithm the content hash was measured with. Frozen once sealed.",
                "enum": ["sha256", "sha512", "sha1", "md5"],
            },
            "original_filename": {"type": "string", "description": "Filename the artefact was acquired under."},
            "file_size": {"type": "integer", "description": "Size of the artefact in bytes."},
            "storage_location": {"type": "string", "description": "Where the artefact actually is, for an item registered by reference."},
            "legal_hold": {"type": "boolean", "description": "Under legal hold: destruction is refused while set."},
            "retention_until": {"type": "string", "description": "Retention expiry date (ISO 8601 date)."},
            "admissibility_notes": {"type": "string", "description": "Notes bearing on the artefact's admissibility."},
        },
    )

    # ── PostIncidentReview ─────────────────────────────────

    review_fields = [
        "id", "reference", "workflow_state", "scopes",
        "incident_id", "incident_reference", "incident_title",
        "response_plan_id", "response_plan_name",
        "scheduled_date", "held_at", "facilitator_id", "facilitator_name",
        "participants", "root_cause_method", "root_cause",
        "contributing_factors", "detection_gap", "containment_assessment",
        "what_went_well", "what_failed", "recurrence_likelihood",
        "similar_incidents_checked", "risk_reassessment_required",
        "response_plan_update_required", "training_required",
        "effectiveness_review_date", "effectiveness_reviewed_at",
        "effectiveness_reviewed_by_id", "effectiveness_reviewed_by_name",
        "effectiveness_verdict", "effectiveness_notes",
        "raised_findings", "corrective_action_plans", "failed_controls",
        "controls_to_strengthen", "identified_risks",
        "identified_vulnerabilities", "isms_changes",
        "is_effectiveness_overdue",
        "created_at",
    ]
    review_writable = [
        "incident_id", "response_plan_id", "scheduled_date", "facilitator_id",
        "root_cause_method", "root_cause", "contributing_factors",
        "detection_gap", "containment_assessment", "what_went_well",
        "what_failed", "recurrence_likelihood", "similar_incidents_checked",
        "risk_reassessment_required", "response_plan_update_required",
        "training_required", "effectiveness_review_date",
        "effectiveness_verdict", "effectiveness_reviewed_by_id",
        "effectiveness_notes",
        "participant_ids", "raised_finding_ids", "corrective_action_plan_ids",
        "failed_control_ids", "control_to_strengthen_ids",
        "identified_risk_ids", "identified_vulnerability_ids", "isms_change_ids",
    ]

    _register_crud(
        server, "post_incident_review", PostIncidentReview, "incidents.review",
        list_fields=review_fields,
        writable_fields=review_writable,
        search_fields=["reference", "root_cause", "what_went_well", "what_failed"],
        filters=["incident_id", "root_cause_method", "recurrence_likelihood",
                 "effectiveness_verdict", "workflow_state", "facilitator_id"],
        required_fields=["incident_id"],
        m2m_fields={
            "participant_ids": "participants",
            "raised_finding_ids": "raised_findings",
            "corrective_action_plan_ids": "corrective_action_plans",
            "failed_control_ids": "failed_controls",
            "control_to_strengthen_ids": "controls_to_strengthen",
            "identified_risk_ids": "identified_risks",
            "identified_vulnerability_ids": "identified_vulnerabilities",
            "isms_change_ids": "isms_changes",
        },
        field_overrides={
            "incident_id": {"type": "string", "description": "UUID of the incident being reviewed (one review per incident). Use list_incidents."},
            "response_plan_id": {"type": "string", "description": "UUID of the response plan the incident was handled under. Use list_incident_response_plans."},
            "scheduled_date": {"type": "string", "description": "Date the review is scheduled for (ISO 8601 date)."},
            "facilitator_id": {"type": "string", "description": "UUID of the user facilitating the review. Use list_users."},
            "root_cause_method": {
                "type": "string",
                "description": "Root cause analysis method used.",
                "enum": ["five_whys", "ishikawa", "fault_tree", "timeline_analysis",
                         "barrier_analysis", "other"],
            },
            "root_cause": {"type": "string", "description": "The root cause as determined by the analysis."},
            "contributing_factors": {"type": "string", "description": "Factors that contributed without being the root cause."},
            "detection_gap": {"type": "string", "description": "Why detection took as long as it did."},
            "containment_assessment": {"type": "string", "description": "How well containment worked."},
            "what_went_well": {"type": "string", "description": "What the response got right."},
            "what_failed": {"type": "string", "description": "What the response got wrong."},
            "recurrence_likelihood": {
                "type": "string",
                "description": "Likelihood the incident recurs.",
                "enum": _INC_CRITICALITY,
            },
            "similar_incidents_checked": {"type": "boolean", "description": "Whether the register was checked for similar incidents (A.5.27)."},
            "risk_reassessment_required": {"type": "boolean", "description": "A risk reassessment is owed."},
            "response_plan_update_required": {"type": "boolean", "description": "The response plan needs updating."},
            "training_required": {"type": "boolean", "description": "Training or awareness action is owed."},
            "effectiveness_review_date": {"type": "string", "description": "Date the effectiveness of the corrective actions is to be re-checked (ISO 8601 date)."},
            "effectiveness_verdict": {
                "type": "string",
                "description": "ISO 27001 clause 10.2 d): did the corrective action actually work.",
                "enum": _INC_EFFECTIVENESS,
            },
            "effectiveness_reviewed_by_id": {"type": "string", "description": "UUID of the user who assessed effectiveness. Use list_users."},
            "effectiveness_notes": {"type": "string", "description": "Reasoning behind the effectiveness verdict."},
            "participant_ids": {"type": "array", "items": {"type": "string"}, "description": "Users who took part in the review. Use list_users."},
            "raised_finding_ids": {"type": "array", "items": {"type": "string"}, "description": "Findings raised by the review. Use list_findings."},
            "corrective_action_plan_ids": {"type": "array", "items": {"type": "string"}, "description": "Corrective action plans opened. Use list_action_plans."},
            "failed_control_ids": {"type": "array", "items": {"type": "string"}, "description": "Requirements whose control failed. Use list_requirements."},
            "control_to_strengthen_ids": {"type": "array", "items": {"type": "string"}, "description": "Requirements whose control must be strengthened. Use list_requirements."},
            "identified_risk_ids": {"type": "array", "items": {"type": "string"}, "description": "Risks identified by the review. Use list_risks."},
            "identified_vulnerability_ids": {"type": "array", "items": {"type": "string"}, "description": "Vulnerabilities identified by the review. Use list_vulnerabilities."},
            "isms_change_ids": {"type": "array", "items": {"type": "string"}, "description": "ISMS changes triggered by the review."},
        },
    )

    # ── ReportingAuthority (catalogue) ─────────────────────

    authority_fields = [
        "id", "reference", "workflow_state", "name", "short_name", "display_name",
        "authority_type", "primary_regime", "additional_regimes",
        "jurisdiction_country", "portal_url", "contact_email", "contact_phone",
        "notification_language", "procedure", "default_recipient_kind",
        "created_at",
    ]
    authority_writable = [
        "name", "short_name", "authority_type", "primary_regime",
        "additional_regimes", "jurisdiction_country", "portal_url",
        "contact_email", "contact_phone", "notification_language", "procedure",
    ]

    _register_crud(
        server, "reporting_authority", ReportingAuthority, "incidents.response_plan",
        list_fields=authority_fields,
        writable_fields=authority_writable,
        search_fields=["reference", "name", "short_name", "jurisdiction_country"],
        filters=["authority_type", "primary_regime", "jurisdiction_country",
                 "workflow_state"],
        required_fields=["name", "primary_regime"],
        field_overrides={
            "name": {"type": "string", "description": "Full name of the body."},
            "short_name": {"type": "string", "description": "Common abbreviation (e.g. CNIL, ANSSI)."},
            "authority_type": {
                "type": "string",
                "description": "Kind of body.",
                "enum": ["supervisory_authority", "csirt", "competent_authority",
                         "sector_regulator", "financial_regulator", "law_enforcement",
                         "other"],
            },
            "primary_regime": {
                "type": "string",
                "description": "The regime this body is primarily the recipient for.",
                "enum": _INC_REGIMES,
            },
            "additional_regimes": {
                "type": "array",
                "items": {"type": "string", "enum": _INC_REGIMES},
                "description": "Further regimes this body also receives filings under.",
            },
            "jurisdiction_country": {"type": "string", "description": "Country whose jurisdiction the body exercises."},
            "portal_url": {"type": "string", "description": "URL of the online filing portal."},
            "contact_email": {"type": "string", "description": "Contact email address."},
            "contact_phone": {"type": "string", "description": "Contact phone number."},
            "notification_language": {"type": "string", "description": "Language filings must be written in (e.g. fr, en)."},
            "procedure": {"type": "string", "description": "How a filing is actually made with this body."},
        },
    )

    # ── ReportingObligationTemplate (catalogue) ────────────

    template_fields = [
        "id", "reference", "workflow_state", "name",
        "authority_id", "authority_name", "regime", "recipient_kind",
        "legal_reference", "content_requirements",
        "clock_anchor", "clock_hours", "no_fixed_deadline", "clock_summary",
        "depends_on_regime", "jurisdiction_country", "min_severity",
        "requires_significant", "requires_personal_data", "requires_high_risk",
        "requires_cross_border", "controller_roles", "applicable_categories",
        "order", "created_at",
    ]
    template_writable = [
        "name", "authority_id", "regime", "recipient_kind", "legal_reference",
        "content_requirements", "clock_anchor", "clock_hours",
        "no_fixed_deadline", "depends_on_regime", "jurisdiction_country",
        "min_severity", "requires_significant", "requires_personal_data",
        "requires_high_risk", "requires_cross_border", "controller_roles",
        "applicable_categories", "order",
    ]

    _register_crud(
        server, "obligation_template", ReportingObligationTemplate, "incidents.response_plan",
        list_fields=template_fields,
        writable_fields=template_writable,
        search_fields=["reference", "name", "legal_reference", "content_requirements"],
        filters=["regime", "recipient_kind", "authority_id", "jurisdiction_country",
                 "min_severity", "no_fixed_deadline", "workflow_state"],
        required_fields=["name", "regime", "recipient_kind"],
        field_overrides={
            "name": {"type": "string", "description": "Name of the catalogue rule."},
            "authority_id": {"type": "string", "description": "UUID of the body the filing goes to. Use list_reporting_authoritys to get valid IDs."},
            "regime": {
                "type": "string",
                "description": "The regulatory regime this rule instantiates.",
                "enum": _INC_REGIMES,
            },
            "recipient_kind": {
                "type": "string",
                "description": "Who the notification is owed to.",
                "enum": _INC_RECIPIENT_KINDS,
            },
            "legal_reference": {"type": "string", "description": "The article the duty comes from (e.g. 'GDPR Art. 33(1)')."},
            "content_requirements": {"type": "string", "description": "What the law requires the filing to contain."},
            "clock_anchor": {
                "type": "string",
                "description": "Which incident timestamp the statutory clock runs from.",
                "enum": _INC_CLOCK_ANCHORS,
            },
            "clock_hours": {"type": "integer", "description": "Hours from the anchor to the deadline (e.g. 72 for GDPR Art. 33)."},
            "no_fixed_deadline": {"type": "boolean", "description": "The regime imposes no fixed deadline. Distinct from a clock that has simply not started."},
            "depends_on_regime": {
                "type": "string",
                "description": "The sibling regime whose first filing anchors this staged obligation.",
                "enum": _INC_REGIMES,
            },
            "jurisdiction_country": {"type": "string", "description": "Country this rule applies in."},
            "min_severity": {
                "type": "string",
                "description": "Severity floor below which the obligation is not raised.",
                "enum": _INC_CRITICALITY,
            },
            "requires_significant": {"type": "boolean", "description": "Only raised when the incident is NIS2-significant."},
            "requires_personal_data": {"type": "boolean", "description": "Only raised when personal data is involved."},
            "requires_high_risk": {"type": "boolean", "description": "Only raised when the breach is high risk to rights and freedoms."},
            "requires_cross_border": {"type": "boolean", "description": "Only raised when the incident is cross-border."},
            "controller_roles": {
                "type": "array",
                "items": {"type": "string", "enum": ["controller", "joint_controller", "processor"]},
                "description": "GDPR controller roles this rule applies to.",
            },
            "applicable_categories": {
                "type": "array",
                "items": {"type": "string", "enum": _INC_THREAT_CATEGORIES},
                "description": "Incident categories this rule applies to. Empty means all.",
            },
            "order": {"type": "integer", "description": "Display / generation order within the catalogue."},
        },
    )

    # ── IncidentNotification ───────────────────────────────

    notification_fields = [
        "id", "reference", "workflow_state",
        "incident_id", "incident_reference", "incident_name",
        "regime", "recipient_kind",
        "recipient_stakeholder_id", "recipient_supplier_id", "recipient_name",
        "recipient_display",
        "authority_id", "authority_name", "template_id", "template_name",
        "obligation_reference", "content_requirements",
        "clock_anchor", "deadline_hours", "no_fixed_deadline",
        "anchor_at", "due_at", "deadline_bucket",
        "depends_on_id", "depends_on_reference",
        "decision", "decision_rationale", "decided_by_id", "decided_by_name",
        "decided_at",
        "channel", "content", "sent_at", "sent_by_id", "sent_by_name",
        "first_submitted_at", "late_by", "was_filed_late", "is_overdue",
        "acknowledgement_reference", "acknowledged_at",
        "proof_filename", "has_proof", "proof_evidence_id",
        "source", "created_at",
    ]
    notification_writable = [
        "incident_id", "regime", "recipient_kind", "authority_id",
        "recipient_stakeholder_id", "recipient_supplier_id", "recipient_name",
        "obligation_reference", "content_requirements", "clock_anchor",
        "deadline_hours", "no_fixed_deadline", "depends_on_id",
        "channel", "content", "decision_rationale",
        "acknowledgement_reference", "acknowledged_at", "proof_evidence_id",
    ]

    _register_crud(
        server, "incident_notification", IncidentNotification, "incidents.notification",
        list_fields=notification_fields,
        writable_fields=notification_writable,
        search_fields=["reference", "recipient_name", "obligation_reference",
                       "content", "acknowledgement_reference"],
        filters=["incident_id", "regime", "recipient_kind", "decision", "channel",
                 "source", "workflow_state", "authority_id", "template_id",
                 "no_fixed_deadline"],
        required_fields=["incident_id", "regime", "recipient_kind"],
        field_overrides={
            "incident_id": {"type": "string", "description": "UUID of the parent incident. Use list_incidents to get valid IDs."},
            "regime": {
                "type": "string",
                "description": "The regulatory regime this obligation arises under.",
                "enum": _INC_REGIMES,
            },
            "recipient_kind": {
                "type": "string",
                "description": "Who the notification is owed to.",
                "enum": _INC_RECIPIENT_KINDS,
            },
            "authority_id": {"type": "string", "description": "UUID of the body the filing goes to. Use list_reporting_authoritys."},
            "recipient_stakeholder_id": {"type": "string", "description": "UUID of the stakeholder recipient. Use list_stakeholders."},
            "recipient_supplier_id": {"type": "string", "description": "UUID of the supplier recipient. Use list_suppliers."},
            "recipient_name": {"type": "string", "description": "Free-text recipient, when it is none of the three modelled kinds."},
            "obligation_reference": {"type": "string", "description": "The article the duty comes from, snapshotted from the template."},
            "content_requirements": {"type": "string", "description": "What the law requires this filing to contain, snapshotted from the template."},
            "clock_anchor": {
                "type": "string",
                "description": "Which incident timestamp the statutory clock runs from. Frozen once the obligation has been filed.",
                "enum": _INC_CLOCK_ANCHORS,
            },
            "deadline_hours": {"type": "integer", "description": "Hours from the anchor to the deadline. Frozen once filed."},
            "no_fixed_deadline": {"type": "boolean", "description": "The regime imposes no fixed deadline."},
            "depends_on_id": {"type": "string", "description": "UUID of the obligation whose first filing anchors this one's clock. Use list_incident_notifications."},
            "channel": {
                "type": "string",
                "description": "How the notification is transmitted.",
                "enum": _INC_CHANNELS,
            },
            "content": {"type": "string", "description": "The text that is filed. Frozen once the obligation has been sent: an amendment is a further filing."},
            "decision_rationale": {"type": "string", "description": "Why the obligation is required, or why it is not. The decision itself is a transition, not a field write."},
            "acknowledgement_reference": {"type": "string", "description": "Reference the recipient returned on acknowledgement."},
            "acknowledged_at": {"type": "string", "description": "When the recipient acknowledged (ISO 8601)."},
            "proof_evidence_id": {"type": "string", "description": "UUID of the evidence item holding the proof of filing. Use list_incident_evidences."},
        },
        # `IncidentNotification.clean()` reads `due_at`, which `save()` derives
        # from the anchor. Validating before that derivation fails on a field the
        # caller never supplies, so every obligation carrying a statutory delay -
        # the GDPR Art. 33(1) 72-hour case included - was uncreatable through MCP
        # while the form and the serializer both created it. They each close the
        # same gap explicitly; this is the same closure for the generic handler.
        pre_clean=lambda obj: obj._recompute_clock(None),
    )

    # ── PersonalDataBreach ─────────────────────────────────

    breach_fields = [
        "id", "reference", "workflow_state",
        "incident_id", "incident_reference", "incident_title",
        "controller_role", "controller_supplier_id", "controller_supplier_name",
        "lead_authority_id", "lead_authority_name", "cross_border_eu",
        "nature", "data_categories", "special_categories",
        "data_subject_categories", "approximate_data_subjects",
        "approximate_records", "volume_is_estimate", "dpo_contact",
        "likely_consequences", "measures_taken",
        "high_risk_to_rights", "high_risk_justification",
        "article_34_exemption", "article_34_exemption_justification",
        "register_entry_reference", "qualified_by_id", "qualified_by_name",
        "qualified_at", "acts_as_processor", "has_article_33_3_content",
        "created_at",
    ]
    breach_writable = [
        "incident_id", "controller_role", "controller_supplier_id",
        "lead_authority_id", "cross_border_eu", "nature", "data_categories",
        "data_subject_categories", "approximate_data_subjects",
        "approximate_records", "special_categories", "volume_is_estimate",
        "dpo_contact", "likely_consequences", "measures_taken",
        "high_risk_to_rights", "high_risk_justification",
        "article_34_exemption", "article_34_exemption_justification",
        "register_entry_reference",
    ]

    _register_crud(
        server, "personal_data_breach", PersonalDataBreach, "incidents.notification",
        list_fields=breach_fields,
        writable_fields=breach_writable,
        search_fields=["reference", "nature", "likely_consequences",
                       "measures_taken", "register_entry_reference"],
        filters=["incident_id", "controller_role", "article_34_exemption",
                 "high_risk_to_rights", "special_categories", "cross_border_eu",
                 "workflow_state"],
        required_fields=["incident_id"],
        field_overrides={
            "incident_id": {"type": "string", "description": "UUID of the incident this breach record qualifies (one per incident). Use list_incidents."},
            "controller_role": {
                "type": "string",
                "description": "The organisation's GDPR role for this processing.",
                "enum": ["controller", "joint_controller", "processor"],
            },
            "controller_supplier_id": {"type": "string", "description": "UUID of the controller we act as processor for. Use list_suppliers."},
            "lead_authority_id": {"type": "string", "description": "UUID of the lead supervisory authority. Use list_reporting_authoritys."},
            "cross_border_eu": {"type": "boolean", "description": "Data subjects in more than one Member State are affected."},
            "nature": {"type": "string", "description": "Nature of the breach (GDPR Art. 33(3)(a))."},
            "data_categories": {"type": "array", "items": {"type": "string"}, "description": "Categories of personal data affected (free-form list)."},
            "special_categories": {"type": "boolean", "description": "Art. 9 special-category data is involved."},
            "data_subject_categories": {"type": "array", "items": {"type": "string"}, "description": "Categories of data subject affected (free-form list)."},
            "approximate_data_subjects": {"type": "integer", "description": "Approximate number of data subjects concerned."},
            "approximate_records": {"type": "integer", "description": "Approximate number of personal data records concerned."},
            "volume_is_estimate": {"type": "boolean", "description": "The two counts are estimates rather than measured figures."},
            "dpo_contact": {"type": "string", "description": "Contact point for the DPO (GDPR Art. 33(3)(b))."},
            "likely_consequences": {"type": "string", "description": "Likely consequences of the breach (GDPR Art. 33(3)(c))."},
            "measures_taken": {"type": "string", "description": "Measures taken or proposed (GDPR Art. 33(3)(d))."},
            "high_risk_to_rights": {"type": "boolean", "description": "High risk to the rights and freedoms of natural persons (GDPR Art. 34(1))."},
            "high_risk_justification": {"type": "string", "description": "Reasoning behind the high-risk verdict."},
            "article_34_exemption": {
                "type": "string",
                "description": "Ground relied on to omit the communication to data subjects (GDPR Art. 34(3)).",
                "enum": ["none", "encryption", "subsequent_measures", "disproportionate_effort"],
            },
            "article_34_exemption_justification": {"type": "string", "description": "Reasoning behind the Art. 34(3) exemption."},
            "register_entry_reference": {"type": "string", "description": "Reference of the matching entry in the Art. 33(5) internal breach register."},
        },
    )
    # `high_risk_to_rights` is tri-state and starts unjudged: same reason.
    _register_verdict_write_tools(
        server, "personal_data_breach", PersonalDataBreach, "incidents.notification",
        breach_writable,
    )

    # ── Append-only ledgers: read tools ────────────────────
    #
    # These three refuse both `save()` on an existing row and `delete()`, so no
    # update or delete tool is registered for them. Their create tools are
    # bespoke: the actor is always the calling account and the row's `source` is
    # always `manual`, neither of which an agent may assert for itself.

    timeline_fields = [
        "id", "incident_id", "incident_reference", "occurred_at", "recorded_at",
        "entry_type", "summary", "detail", "source",
        "author_id", "author_name",
        "related_action_id", "related_action_reference",
        "related_evidence_id", "related_evidence_reference",
        "superseded_entry_id", "correction_reason", "is_superseded",
        "is_evidence", "created_at",
    ]
    _register_append_only_reads(
        server, "incident_timeline_entry", "incident_timeline_entries",
        IncidentTimelineEntry, "incidents.incident",
        list_fields=timeline_fields,
        search_fields=["summary", "detail", "correction_reason"],
        filters=["incident_id", "entry_type", "source", "is_evidence", "author_id"],
    )

    custody_fields = [
        "id", "evidence_id", "evidence_reference", "evidence_name",
        "incident_reference", "action", "occurred_at", "recorded_at",
        "actor_id", "actor_name", "counterparty", "counterparty_organisation",
        "location", "hash_at_event", "integrity_ok", "verification_outcome",
        "notes", "source", "created_at",
    ]
    _register_append_only_reads(
        server, "evidence_custody_event", "evidence_custody_events",
        EvidenceCustodyEvent, "incidents.evidence",
        list_fields=custody_fields,
        search_fields=["counterparty", "counterparty_organisation", "location", "notes"],
        filters=["evidence_id", "action", "source", "integrity_ok", "actor_id"],
    )

    filing_fields = [
        "id", "reference", "notification_id", "notification_reference",
        "incident_reference", "regime", "submitted_at", "channel",
        "recipient_name", "external_reference", "subject", "content",
        "outcome", "acknowledged_at", "is_correction", "was_late",
        "supersedes_id", "supersedes_reference", "is_superseded",
        "submitted_by_id", "submitted_by_name",
        "proof_filename", "has_proof", "created_at",
    ]
    _register_append_only_reads(
        server, "notification_filing", "notification_filings",
        NotificationFiling, "incidents.notification",
        list_fields=filing_fields,
        search_fields=["reference", "recipient_name", "external_reference",
                       "subject", "content"],
        filters=["notification_id", "channel", "outcome", "is_correction",
                 "was_late", "submitted_by_id"],
    )

    # ── Append-only ledgers: create tools ──────────────────

    def create_incident_timeline_entry(user, arguments):
        incident, err = _incident_child_parent(
            "incident", Incident, user, arguments)
        if err:
            return err
        entry = IncidentTimelineEntry(
            incident=incident,
            author=user,
            source="manual",
        )
        for field_name in ("occurred_at", "entry_type", "summary", "detail",
                           "is_evidence", "related_action_id",
                           "related_evidence_id", "superseded_entry_id",
                           "correction_reason"):
            if field_name in arguments:
                setattr(entry, field_name, _coerce_field_value(
                    IncidentTimelineEntry, field_name, arguments[field_name]))
        try:
            entry.full_clean()
            entry.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        return _serialize_obj(entry, timeline_fields)

    server.register_tool(
        "create_incident_timeline_entry",
        "Append one entry to an incident's chronology. The chronology is "
        "append-only: there is no update and no delete tool. A mistake is "
        "corrected by appending a further entry of type 'correction' that names "
        "the entry it supersedes and states why. The author is always the "
        "calling account and the source is always 'manual'.",
        _obj_schema(
            {
                "incident_id": {"type": "string", "description": "UUID of the incident. Use list_incidents to get valid IDs."},
                "occurred_at": {"type": "string", "description": "Real-world time of the act being narrated (ISO 8601). May be backdated: the chronology reads in the order things happened."},
                "summary": {"type": "string", "description": "The one-line entry, exported verbatim (max 500 characters)."},
                "detail": {"type": "string", "description": "The full account: commands run, output observed, people spoken to."},
                "entry_type": {
                    "type": "string",
                    "description": "Kind of entry.",
                    "enum": ["observation", "action", "decision", "communication",
                             "escalation", "evidence", "external_input",
                             "correction", "system"],
                },
                "is_evidence": {"type": "boolean", "description": "Include this entry verbatim in generated regulatory filings and in the incident file."},
                "related_action_id": {"type": "string", "description": "UUID of the response action this entry narrates. Use list_incident_response_actions."},
                "related_evidence_id": {"type": "string", "description": "UUID of the evidence item this entry narrates. Use list_incident_evidences."},
                "superseded_entry_id": {"type": "string", "description": "UUID of the earlier entry this one corrects. Requires entry_type 'correction' and a correction_reason."},
                "correction_reason": {"type": "string", "description": "Why the earlier entry was wrong. A correction with no stated reason is a rewrite."},
            },
            required=["incident_id", "occurred_at", "summary"],
        ),
        # Appending to the chronology is a create, not an update : the entry
        # is a new row and the ledger refuses every post-insert write. The DRF
        # route and the spec both say `.create`; this was the outlier.
        require_perm("incidents.incident.create")(create_incident_timeline_entry),
    )

    def create_evidence_custody_event(user, arguments):
        evidence, err = _incident_child_parent(
            "evidence", IncidentEvidence, user, arguments)
        if err:
            return err
        event = EvidenceCustodyEvent(
            evidence=evidence,
            actor=user,
            source="manual",
        )
        for field_name in ("action", "occurred_at", "counterparty",
                           "counterparty_organisation", "location",
                           "hash_at_event", "notes"):
            if field_name in arguments:
                setattr(event, field_name, _coerce_field_value(
                    EvidenceCustodyEvent, field_name, arguments[field_name]))
        try:
            event.full_clean()
            event.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        return _serialize_obj(event, custody_fields)

    server.register_tool(
        "create_evidence_custody_event",
        "Record one handling act on an evidence item. The chain of custody is "
        "append-only: there is no update and no delete tool, and a mistake is "
        "corrected by appending a further act that states what the earlier one "
        "got wrong. The actor is always the calling account and the source is "
        "always 'manual'. Do not use this to assert an integrity verdict: call "
        "verify_evidence_integrity, which measures the artefact itself.",
        _obj_schema(
            {
                "evidence_id": {"type": "string", "description": "UUID of the evidence item. Use list_incident_evidences to get valid IDs."},
                "action": {
                    "type": "string",
                    "description": "The handling act being attested. transferred, released, returned and destroyed each require a named counterparty.",
                    "enum": _INC_CUSTODY_ACTIONS,
                },
                "occurred_at": {"type": "string", "description": "Real-world time of the act (ISO 8601). This is the ledger's ordering key."},
                "counterparty": {"type": "string", "description": "Named individual on the other side of the act. A handover to an organisation with no named individual is not a handover."},
                "counterparty_organisation": {"type": "string", "description": "Organisation the counterparty belongs to."},
                "location": {"type": "string", "description": "Where the act took place."},
                "hash_at_event": {"type": "string", "description": "Digest recorded at the time of the act, when one was measured by hand."},
                "notes": {"type": "string", "description": "Free-text account of the act."},
            },
            required=["evidence_id", "action", "occurred_at"],
        ),
        require_perm("incidents.evidence.update")(create_evidence_custody_event),
    )

    def create_notification_filing(user, arguments):
        notification, err = _incident_child_parent(
            "notification", IncidentNotification, user, arguments)
        if err:
            return err
        supersedes = None
        supersedes_id = arguments.get("supersedes_id")
        if supersedes_id:
            try:
                supersedes = NotificationFiling.objects.get(pk=supersedes_id)
            except (NotificationFiling.DoesNotExist, ValueError, ValidationError):
                return _error("NotificationFiling not found (supersedes_id).")
        submitted_at = arguments.get("submitted_at")
        if submitted_at:
            submitted_at = _parse_iso_datetime(submitted_at)
            if submitted_at is None:
                return _error("submitted_at is not a valid ISO 8601 date-time.")
            from django.conf import settings
            if settings.USE_TZ and timezone.is_naive(submitted_at):
                submitted_at = timezone.make_aware(submitted_at)
        try:
            # `record_filing` is the model's own entry point: the first filing
            # runs through `transition_to()`, which is what stamps sent_at,
            # sent_by, first_submitted_at and late_by, moves the obligation to
            # its sent step and narrates the act in the incident chronology.
            # Every later filing inserts without disturbing those frozen values.
            filing = notification.record_filing(
                user,
                submitted_at=submitted_at,
                channel=arguments.get("channel"),
                subject=arguments.get("subject", ""),
                content=arguments.get("content"),
                recipient_name=arguments.get("recipient_name", ""),
                external_reference=arguments.get("external_reference", ""),
                is_correction=bool(arguments.get("is_correction", False)),
                supersedes=supersedes,
                comment=arguments.get("comment") or None,
            )
        except (ValidationError, Exception) as e:
            return _error(str(e))
        if filing is None:
            return _error("The filing was not recorded.")
        return _serialize_obj(filing, filing_fields)

    server.register_tool(
        "create_notification_filing",
        "Record that a notification obligation was actually transmitted. The "
        "filing log is append-only: there is no update and no delete tool, and "
        "an amendment is a further filing, never a rewrite. The first filing on "
        "an obligation runs through the lifecycle and freezes its lateness "
        "verdict; later filings insert without disturbing it. The submitter is "
        "always the calling account.",
        _obj_schema(
            {
                "notification_id": {"type": "string", "description": "UUID of the obligation being discharged. Use list_incident_notifications to get valid IDs."},
                "submitted_at": {"type": "string", "description": "When the transmission was made (ISO 8601). Defaults to now. Cannot be in the future."},
                "channel": {
                    "type": "string",
                    "description": "How it was transmitted. Defaults to the obligation's channel, then to 'portal'.",
                    "enum": _INC_CHANNELS,
                },
                "recipient_name": {"type": "string", "description": "Who it was transmitted to. Defaults to the obligation's recipient."},
                "subject": {"type": "string", "description": "Subject line of the transmission."},
                "content": {"type": "string", "description": "What was actually transmitted, verbatim."},
                "external_reference": {"type": "string", "description": "Reference the portal or recipient returned."},
                "is_correction": {"type": "boolean", "description": "This filing corrects an earlier one. The first filing on an obligation is never a correction."},
                "supersedes_id": {"type": "string", "description": "UUID of the filing this one replaces, on the same obligation. Implies is_correction."},
                "comment": {"type": "string", "description": "Comment carried into the lifecycle transition performed by a first filing."},
            },
            required=["notification_id"],
        ),
        require_perm("incidents.notification.update")(create_notification_filing),
    )

    # ── Bespoke tools ──────────────────────────────────────

    _PROMOTION_OVERRIDES = (
        "title", "summary", "description", "category", "severity", "tlp",
        "is_exercise", "personal_data_involved", "awareness_at",
        "awareness_justification", "incident_manager_id", "response_plan_id",
    )

    def declare_incident_from_event(user, arguments):
        if not user.is_superuser and not user.has_perm("incidents.incident.create"):
            return _error("Permission denied: incidents.incident.create")
        pk = arguments.get("id")
        comment = arguments.get("comment")
        if not pk:
            raise InvalidParamsError("id is required.")
        if not comment or not str(comment).strip():
            raise InvalidParamsError(
                "comment is required: promoting an event to an incident is a "
                "transition that records why the assessment concluded so.")
        try:
            event = SecurityEvent.objects.get(pk=pk)
        except (SecurityEvent.DoesNotExist, ValueError, ValidationError):
            return _error("SecurityEvent not found.")
        if not _filter_by_scopes(SecurityEvent.objects.filter(pk=event.pk), user).exists():
            return _error("Access denied: object is outside your allowed scopes.")

        overrides = {}
        for field_name in _PROMOTION_OVERRIDES:
            if field_name in arguments and arguments[field_name] is not None:
                target = _fk_kwarg_name(Incident, field_name)
                overrides[target] = _coerce_field_value(
                    Incident, field_name, arguments[field_name])

        from core.lifecycle import LifecycleError

        previous_state = event.workflow_state
        try:
            incident = event.promote_to_incident(
                user, str(comment), enforce_permission=True, **overrides)
        except (LifecycleError, ValidationError, Exception) as e:
            return _error(str(e))
        return {
            "event": {
                "id": str(event.pk),
                "reference": event.reference,
                "previous_state": previous_state,
                "workflow_state": event.workflow_state,
                "triage_decision": event.triage_decision,
            },
            "incident": _serialize_obj(incident, incident_fields),
        }

    server.register_tool(
        "declare_incident_from_event",
        "Promote an assessed security event into an incident, as one atomic "
        "act. Creates the incident in draft, carries over the event's title, "
        "description, detection source, timestamps, reporter, scopes and "
        "affected assets, declares it through its lifecycle, links the event to "
        "it and moves the event to its confirmed-incident step. Requires both "
        "incidents.event.validate (via the transition) and "
        "incidents.incident.create. The event must be under assessment. Optional "
        "arguments override the values carried across.",
        _obj_schema(
            {
                "id": {"type": "string", "description": "UUID of the security event to promote. Use list_security_events to get valid IDs."},
                "comment": {"type": "string", "description": "Why the assessment concluded this is an incident. Mandatory: the transition records it."},
                "title": {"type": "string", "description": "Override the incident title (defaults to the event's)."},
                "summary": {"type": "string", "description": "Executive summary for the new incident."},
                "description": {"type": "string", "description": "Override the incident description (defaults to the event's)."},
                "category": {"type": "string", "description": "Override the incident category.", "enum": _INC_THREAT_CATEGORIES},
                "severity": {"type": "string", "description": "Severity of the new incident.", "enum": _INC_CRITICALITY},
                "tlp": {"type": "string", "description": "Handling caveat for the new incident.", "enum": _INC_TLP},
                "is_exercise": {"type": "boolean", "description": "The new incident is an exercise. Exercises raise no notification obligation."},
                "personal_data_involved": {"type": "boolean", "description": "Personal data was, or may have been, affected."},
                "awareness_at": {"type": "string", "description": "Legal awareness anchor for the new incident (ISO 8601)."},
                "awareness_justification": {"type": "string", "description": "Why legal awareness postdates technical detection. Mandatory whenever the two differ."},
                "incident_manager_id": {"type": "string", "description": "UUID of the accountable responder. Use list_users."},
                "response_plan_id": {"type": "string", "description": "UUID of the response plan to handle it under. Use list_incident_response_plans."},
            },
            required=["id", "comment"],
        ),
        require_perm("incidents.event.validate")(declare_incident_from_event),
    )

    def verify_evidence_integrity(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            item = IncidentEvidence.objects.get(pk=pk)
        except (IncidentEvidence.DoesNotExist, ValueError, ValidationError):
            return _error("IncidentEvidence not found.")
        if not _filter_by_scopes(IncidentEvidence.objects.filter(pk=item.pk), user).exists():
            return _error("Access denied: object is outside your allowed scopes.")
        try:
            outcome = item.verify_integrity(user, notes=arguments.get("notes", "") or "")
        except (ValidationError, Exception) as e:
            return _error(str(e))
        return {
            "id": str(item.pk),
            "reference": item.reference,
            "outcome": outcome,
            "content_hash": item.content_hash,
            "hash_algorithm": item.hash_algorithm,
            "last_integrity_check_at": (
                item.last_integrity_check_at.isoformat()
                if item.last_integrity_check_at else None
            ),
            "last_integrity_check_ok": item.last_integrity_check_ok,
        }

    server.register_tool(
        "verify_evidence_integrity",
        "Re-measure an evidence artefact and append the result to its chain of "
        "custody. Returns one of three outcomes, which are never collapsed into "
        "each other: 'match' (the artefact was read and its digest equals the "
        "recorded content hash), 'mismatch' (it was read and the digest differs, "
        "which is a permanent chain-of-custody break) and 'not_verifiable' (the "
        "item is registered by reference, or the file is missing or unreadable, "
        "which is a claim about the storage and not about the artefact). The "
        "digest is measured, never asserted by the caller.",
        _obj_schema(
            {
                "id": {"type": "string", "description": "UUID of the evidence item. Use list_incident_evidences to get valid IDs."},
                "notes": {"type": "string", "description": "Optional note recorded on the custody row (why the check was run, who asked for it)."},
            },
            required=["id"],
        ),
        require_perm("incidents.evidence.update")(verify_evidence_integrity),
    )

    def list_overdue_incident_notifications(user, arguments):
        qs = IncidentNotification.objects.select_related("incident", "authority")
        qs = _filter_by_scopes(qs, user)
        for key in ("incident_id", "regime", "recipient_kind", "authority_id"):
            value = arguments.get(key)
            if value is not None:
                qs = qs.filter(**{key: value})
        # Narrow in the database on the (due_at, workflow_state) index, then let
        # the model's own `is_overdue` be the authority: it is the single
        # definition of the question, and it never hardcodes a step code here.
        qs = qs.filter(due_at__lt=timezone.now(), sent_at__isnull=True).order_by("due_at")
        overdue = [obligation for obligation in qs if obligation.is_overdue]

        limit = min(int(arguments.get("limit", 25)), 100)
        offset = int(arguments.get("offset", 0))
        now = timezone.now()
        items = []
        for obligation in overdue[offset:offset + limit]:
            incident = obligation.incident
            items.append({
                "id": str(obligation.pk),
                "reference": obligation.reference,
                "workflow_state": obligation.workflow_state,
                "regime": obligation.regime,
                "recipient_kind": obligation.recipient_kind,
                "recipient": obligation.recipient_display,
                "authority_name": obligation.authority_name,
                "due_at": obligation.due_at.isoformat() if obligation.due_at else None,
                "hours_overdue": round(
                    (now - obligation.due_at).total_seconds() / 3600, 1
                ) if obligation.due_at else None,
                "decision": obligation.decision,
                "incident_id": str(obligation.incident_id),
                "incident_reference": obligation.incident_reference,
                "incident_title": obligation.incident_name,
                "incident_severity": incident.severity if incident else None,
                "incident_manager": (
                    incident.incident_manager_name if incident else ""
                ),
            })
        return {
            "total": len(overdue),
            "items": items,
            "limit": limit,
            "offset": offset,
        }

    server.register_tool(
        "list_overdue_incident_notifications",
        "List every notification obligation whose statutory deadline has passed "
        "with no filing recorded: the 'are we late' question answered in one "
        "call. Returns the obligation, its regime and recipient, the deadline, "
        "how many hours it is overdue, and the incident it belongs to with its "
        "manager. Obligations with no deadline, already filed, or in a terminal "
        "step are excluded.",
        _obj_schema({
            "incident_id": {"type": "string", "description": "Restrict to one incident."},
            "regime": {"type": "string", "description": "Restrict to one regulatory regime.", "enum": _INC_REGIMES},
            "recipient_kind": {"type": "string", "description": "Restrict to one kind of recipient.", "enum": _INC_RECIPIENT_KINDS},
            "authority_id": {"type": "string", "description": "Restrict to one reporting authority."},
            "limit": {"type": "integer", "description": "Max items to return (default 25, max 100)"},
            "offset": {"type": "integer", "description": "Offset for pagination"},
        }),
        require_perm("incidents.notification.read")(list_overdue_incident_notifications),
    )


# ── Accounts Module ────────────────────────────────────────

def _register_accounts_tools(server):
    User = _get_model("accounts", "User")
    Group = _get_model("accounts", "Group")
    Permission = _get_model("accounts", "Permission")
    AccessLog = _get_model("accounts", "AccessLog")

    # List users
    server.register_tool(
        "list_users",
        "List users with optional search",
        _list_schema({
            "is_active": {"type": "boolean", "description": "Filter by active status"},
        }),
        require_perm("system.users.read")(
            _list_handler(User,
                          ["id", "email", "first_name", "last_name", "job_title",
                           "department", "is_active", "last_login", "created_at"],
                          search_fields=["email", "first_name", "last_name"],
                          filters=["is_active"],
                          scope_filtered=False)
        ),
    )

    # Get user
    server.register_tool(
        "get_user",
        "Get detailed information about a user",
        _id_schema(),
        require_perm("system.users.read")(
            _get_handler(User,
                         ["id", "email", "first_name", "last_name", "job_title",
                          "department", "phone", "language", "timezone",
                          "is_active", "last_login", "created_at", "updated_at"],
                         scope_filtered=False)
        ),
    )

    # Create a user (invitation flow: no password crosses the MCP boundary)
    def create_user(user, arguments):
        from django.core.exceptions import ValidationError

        from accounts.invitations import build_activation_url, provision_user

        email = (arguments.get("email") or "").strip()
        last_name = (arguments.get("last_name") or "").strip()
        if not email or not last_name:
            return _error("email and last_name are required.")
        groups = arguments.get("groups") or []
        if groups and not isinstance(groups, list):
            return _error("groups must be an array of role/group names.")
        try:
            new_user = provision_user(
                email=email,
                last_name=last_name,
                first_name=(arguments.get("first_name") or ""),
                user_type=(arguments.get("user_type") or "human"),
                job_title=(arguments.get("job_title") or ""),
                department=(arguments.get("department") or ""),
                phone=(arguments.get("phone") or ""),
                language=(arguments.get("language") or None),
                group_names=groups,
                created_by=user,
            )
        except ValidationError as exc:
            return _error("; ".join(exc.messages))
        return {
            "id": str(new_user.pk),
            "email": new_user.email,
            "display_name": new_user.display_name,
            "activation_url": build_activation_url(new_user),
        }

    server.register_tool(
        "create_user",
        "Provision a new user via the invitation flow so it can be referenced as "
        "an owner / reviewer. No password is accepted: the account is created "
        "with an unusable password and the response returns an 'activation_url' "
        "the invitee follows to set their first credential. 'groups' are role / "
        "group names that must already exist (use list_groups). Requires the "
        "system.users.create permission.",
        _obj_schema(
            {
                "email": {"type": "string", "description": "Email address (login identifier). Must be unique."},
                "last_name": {"type": "string", "description": "Last name (required)."},
                "first_name": {"type": "string", "description": "First name."},
                "user_type": {
                    "type": "string",
                    "description": "Account type: 'human' (default) or 'robot' (service account).",
                    "enum": ["human", "robot"],
                },
                "job_title": {"type": "string", "description": "Job title."},
                "department": {"type": "string", "description": "Department."},
                "phone": {"type": "string", "description": "Phone number."},
                "language": {"type": "string", "description": "Preferred UI language code, e.g. 'en' or 'fr'."},
                "groups": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Role / group names to assign (must already exist).",
                },
            },
            ["email", "last_name"],
        ),
        require_perm("system.users.create")(create_user),
    )

    # Get current user info
    def get_me(user, arguments):
        data = _serialize_obj(user, ["id", "email", "first_name", "last_name",
                                     "job_title", "department", "language", "timezone",
                                     "theme_preference"])
        # Surface the caller's own capabilities so a client can tell, before an
        # import, whether it may override created_at / updated_at (RG: the
        # timestamp override is silently ignored without this permission).
        data["is_superuser"] = bool(getattr(user, "is_superuser", False))
        data["can_override_import_dates"] = bool(
            data["is_superuser"] or user.has_perm(TIMESTAMP_OVERRIDE_PERM)
        )
        data["can_create_users"] = bool(
            data["is_superuser"] or user.has_perm("system.users.create")
        )
        return data

    server.register_tool(
        "get_me",
        "Get information about the currently authenticated user, including "
        "capability flags: 'can_override_import_dates' (may set created_at / "
        "updated_at on import) and 'can_create_users'.",
        {"type": "object", "properties": {}},
        get_me,
    )

    # ── Saved filters (per-user list filters; own + shared) ──
    SavedFilter = _get_model("accounts", "SavedFilter")
    _sf_fields = ["id", "view_key", "name", "query", "is_shared", "owner_id", "created_at", "updated_at"]

    def list_saved_filters(user, arguments):
        from django.db.models import Q

        qs = SavedFilter.objects.filter(Q(owner=user) | Q(is_shared=True))
        view_key = arguments.get("view_key")
        if view_key:
            qs = qs.filter(view_key=view_key)
        return {"items": _serialize_qs(qs, _sf_fields, limit=100)}

    def create_saved_filter(user, arguments):
        name = (arguments.get("name") or "").strip()
        view_key = (arguments.get("view_key") or "").strip()
        if not name or not view_key:
            return _error("name and view_key are required")
        obj = SavedFilter.objects.create(
            owner=user,
            view_key=view_key,
            name=name,
            query=arguments.get("query") or "",
            is_shared=bool(arguments.get("is_shared")),
        )
        return _serialize_obj(obj, _sf_fields)

    def delete_saved_filter(user, arguments):
        obj = SavedFilter.objects.filter(pk=arguments.get("id"), owner=user).first()
        if not obj:
            return _error("Saved filter not found (or not owned by you)")
        obj.delete()
        return {"deleted": True}

    server.register_tool(
        "list_saved_filters",
        "List the current user's saved list filters (own + shared). Optional view_key "
        "(e.g. 'context.issue') narrows to one list.",
        _list_schema({"view_key": {"type": "string", "description": "List key, e.g. context.issue"}}),
        list_saved_filters,
    )
    server.register_tool(
        "create_saved_filter",
        "Save a named list filter for the current user. `query` is the list's filter "
        "query string; `view_key` is the list key (e.g. context.issue).",
        _obj_schema(
            {
                "view_key": {"type": "string", "description": "List key, e.g. context.issue"},
                "name": {"type": "string", "description": "Filter name"},
                "query": {"type": "string", "description": "Filter query string"},
                "is_shared": {"type": "boolean", "description": "Share with everyone (default false)"},
            },
            ["view_key", "name"],
        ),
        create_saved_filter,
    )
    server.register_tool(
        "delete_saved_filter",
        "Delete one of the current user's saved list filters by id.",
        _id_schema(),
        delete_saved_filter,
    )

    # Update current user profile
    def update_me(user, arguments):
        from accounts.constants import ThemePreference

        editable = ["first_name", "last_name", "phone", "language", "timezone", "theme_preference"]
        valid_themes = {choice.value for choice in ThemePreference}
        changed = []
        for field in editable:
            if field not in arguments:
                continue
            value = arguments[field]
            if field == "theme_preference" and value not in valid_themes:
                raise InvalidParamsError(
                    "theme_preference must be one of: " + ", ".join(sorted(valid_themes))
                )
            setattr(user, field, value)
            changed.append(field)
        if changed:
            user.save(update_fields=changed + ["updated_at"])
        return _serialize_obj(user, ["id", "email", "first_name", "last_name",
                                     "job_title", "department", "language", "timezone",
                                     "theme_preference"])

    server.register_tool(
        "update_me",
        "Update the currently authenticated user's profile (self-service). Accepts first_name, last_name, phone, language, timezone, theme_preference.",
        {
            "type": "object",
            "properties": {
                "first_name": {"type": "string", "description": "First name."},
                "last_name": {"type": "string", "description": "Last name."},
                "phone": {"type": "string", "description": "Phone number."},
                "language": {"type": "string", "description": "Interface language code (empty for auto, 'fr', 'en')."},
                "timezone": {"type": "string", "description": "IANA timezone, e.g. 'Europe/Paris'."},
                "theme_preference": {
                    "type": "string",
                    "enum": ["system", "light", "dark"],
                    "description": "Display theme. 'system' follows the OS preference.",
                },
            },
        },
        update_me,
    )

    # ── Dashboard widget layout (own-data) ────────────────────

    def get_dashboard_layout(user, arguments):
        """Return the authenticated user's resolved home-dashboard widget layout
        together with the catalogue of available widgets and their allowed sizes."""
        from core.dashboard import DASHBOARD_WIDGETS, resolve_layout

        return {
            "layout": resolve_layout(user.dashboard_layout),
            "widgets": [
                {
                    "id": w.id,
                    "title": str(w.title),
                    "category": str(w.category),
                    "sizes": list(w.sizes),
                    "default_size": w.default_size,
                    "default_zone": w.default_zone,
                    "multiple": w.multiple,
                    "description": str(w.description),
                }
                for w in DASHBOARD_WIDGETS
            ],
        }

    server.register_tool(
        "get_dashboard_layout",
        (
            "Get the currently authenticated user's home-dashboard widget layout "
            "(ordered list of {key, id, size, visible, zone, params}) and the "
            "catalogue of available widgets with their allowed sizes. `id` is the "
            "widget type and `key` is the per-instance id. A size is a 'WxH' tile "
            "token: width W in 1..4 quarter-columns (1=1/4 .. 4=full width) by "
            "height H in 1..4 fixed row units, e.g. '2x1' or '4x2'. A widget with "
            "`multiple: true` (e.g. 'indicator') can appear several times, each "
            "instance carrying its own `params` (the indicator widget takes "
            "`{indicator: <id>, show_chart: bool}`)."
        ),
        {"type": "object", "properties": {}},
        get_dashboard_layout,
    )

    def update_dashboard_layout(user, arguments):
        """Replace the authenticated user's home-dashboard widget layout.

        Parameters
        ----------
        layout : list of objects
            Ordered widget instances ``{"key", "id", "size", "visible", "zone",
            "params"}``. The payload is sanitised against the widget registry:
            unknown ids are dropped, invalid sizes fall back to the widget
            default, params are normalised, any missing singleton widget is
            appended with its defaults, and ``multiple`` widgets keep every
            instance (each with a unique key). The stored, normalised layout is
            returned.
        """
        from core.dashboard import sanitize_layout

        layout = arguments.get("layout")
        if not isinstance(layout, list):
            raise InvalidParamsError("layout must be a list of widget entries.")
        normalised = sanitize_layout(layout)
        user.dashboard_layout = normalised
        user.save(update_fields=["dashboard_layout"])
        return {"layout": normalised}

    server.register_tool(
        "update_dashboard_layout",
        (
            "Replace the currently authenticated user's home-dashboard widget "
            "layout. Pass `layout` as an ordered list of {key, id, size, visible, "
            "zone, params} instances; use get_dashboard_layout first to discover "
            "widget ids, allowed sizes and which widgets are 'multiple'. Give each "
            "instance of a 'multiple' widget a distinct key. The payload is "
            "sanitised against the registry."
        ),
        _obj_schema(
            {
                "layout": {
                    "type": "array",
                    "description": "Ordered widget instances {key, id, size, visible, zone, params}.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": (
                                    "Per-instance id. Required to keep several instances of a "
                                    "'multiple' widget distinct; for singletons it equals the id."
                                ),
                            },
                            "id": {"type": "string", "description": "Widget type id."},
                            "size": {
                                "type": "string",
                                "description": (
                                    "Tile size as a 'WxH' token: width W in 1..4 "
                                    "quarter-columns (1=1/4 .. 4=full width) by height "
                                    "H in 1..4 fixed row units, e.g. '2x1' or '4x2'. "
                                    "Allowed values are per-widget; an out-of-set size "
                                    "is clamped to the widget default. Used in the main "
                                    "zone (ignored in the rail)."
                                ),
                            },
                            "zone": {
                                "type": "string",
                                "enum": ["main", "rail"],
                                "description": "Which zone the widget lives in: 'main' area or the 'rail' side column.",
                            },
                            "visible": {"type": "boolean", "description": "Whether the widget shows on the dashboard."},
                            "params": {
                                "type": "object",
                                "description": (
                                    "Per-instance parameters (widget-type specific). "
                                    "'indicator' takes {indicator: <id>, show_chart: bool}; "
                                    "'compliance_by_framework' and 'active_objectives' take "
                                    "{sort: default|value_desc|value_asc|name|manual, order: "
                                    "[ids]}; 'overall_compliance' takes {show_target: bool, "
                                    "target: 0..100}. Sanitised against the widget; ignored "
                                    "for widgets that take no params."
                                ),
                            },
                        },
                        "required": ["id"],
                    },
                },
            },
            required=["layout"],
        ),
        update_dashboard_layout,
    )

    # ── Notifications (own-data) ──────────────────────────────

    def list_notifications(user, arguments):
        """List the authenticated user's own in-app notifications.

        Parameters
        ----------
        unread_only : bool (optional, default false)
            Only return notifications that have not been read yet.
        limit : int (optional, default 20, max 100)
            Maximum number of notifications to return (most recent first).
        """
        qs = user.notifications.all()
        if arguments.get("unread_only"):
            qs = qs.filter(is_read=False)
        limit = min(int(arguments.get("limit", 20) or 20), 100)
        items = [
            {
                "id": str(n.pk),
                "type": n.notification_type,
                "title": n.title,
                "message": n.message,
                "actor": n.actor.display_name if n.actor else "",
                "target_url": n.target_url,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in qs[:limit]
        ]
        return {
            "notifications": items,
            "unread": user.notifications.filter(is_read=False).count(),
        }

    server.register_tool(
        "list_notifications",
        (
            "List the currently authenticated user's in-app notifications "
            "(most recent first), with the unread count. "
            "Set unread_only=true to only return unread notifications."
        ),
        _obj_schema(
            {
                "unread_only": {"type": "boolean", "description": "Only unread notifications."},
                "limit": {"type": "integer", "description": "Max results (default 20, max 100)."},
            }
        ),
        list_notifications,
    )

    def mark_notification_read(user, arguments):
        """Mark one of the authenticated user's notifications as read."""
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        from accounts.models import Notification

        try:
            notification = user.notifications.get(pk=pk)
        except (Notification.DoesNotExist, ValueError):
            return _error("Notification not found.")
        notification.mark_read()
        return {"id": str(notification.pk), "is_read": True}

    server.register_tool(
        "mark_notification_read",
        "Mark one of the authenticated user's notifications as read.",
        _obj_schema(
            {"id": {"type": "string", "description": "UUID of the notification"}},
            required=["id"],
        ),
        mark_notification_read,
    )

    def mark_all_notifications_read(user, arguments):
        """Mark all of the authenticated user's notifications as read."""
        from django.utils import timezone as _tz

        updated = user.notifications.filter(is_read=False).update(
            is_read=True, read_at=_tz.now()
        )
        return {"marked_read": updated}

    server.register_tool(
        "mark_all_notifications_read",
        "Mark all of the authenticated user's unread notifications as read.",
        {"type": "object", "properties": {}},
        mark_all_notifications_read,
    )

    # List groups
    server.register_tool(
        "list_groups",
        "List all groups",
        _list_schema(),
        require_perm("system.groups.read")(
            _list_handler(Group,
                          ["id", "name", "description", "is_system", "created_at"],
                          search_fields=["name"],
                          scope_filtered=False)
        ),
    )

    # Get group details
    @require_perm("system.groups.read")
    def get_group(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            group = Group.objects.get(pk=pk)
        except Group.DoesNotExist:
            return _error("Group not found.")
        perms = list(group.permissions.values_list("codename", flat=True))
        user_count = group.users.count()
        return {
            "id": str(group.id),
            "name": group.name,
            "description": group.description,
            "is_system": group.is_system,
            "permissions": perms,
            "user_count": user_count,
            "created_at": group.created_at.isoformat(),
        }

    server.register_tool(
        "get_group",
        "Get group details including permissions",
        _id_schema(),
        get_group,
    )

    # List permissions
    server.register_tool(
        "list_permissions",
        "List all available permissions",
        _list_schema({
            "module": {"type": "string", "description": "Filter by module (context, assets, compliance, risks, system)"},
        }),
        require_perm("system.groups.read")(
            _list_handler(Permission,
                          ["id", "codename", "name", "module", "feature", "action"],
                          search_fields=["codename", "name"],
                          filters=["module", "feature"],
                          scope_filtered=False)
        ),
    )

    # List access logs
    server.register_tool(
        "list_access_logs",
        "List access logs (authentication events)",
        _list_schema({
            "event_type": {"type": "string", "description": "Filter by event type"},
            "user_id": {"type": "string", "description": "Filter by user ID"},
        }),
        require_perm("system.audit_trail.read")(
            _list_handler(AccessLog,
                          ["id", "timestamp", "user_id", "email_attempted",
                           "event_type", "ip_address", "failure_reason"],
                          search_fields=["email_attempted"],
                          filters=["event_type", "user_id"],
                          scope_filtered=False)
        ),
    )


# ── Custom supplier handlers (with image_url support) ─────

def _apply_logo_from_url(obj, image_url):
    """Download image from *image_url*, set logo and variants on *obj*."""
    from helpers.image_utils import download_image_to_data_uri, generate_image_variants

    logo_uri = download_image_to_data_uri(image_url)
    variants = generate_image_variants(logo_uri)
    obj.logo = logo_uri
    obj.logo_16 = variants[16]
    obj.logo_32 = variants[32]
    obj.logo_64 = variants[64]


def _create_supplier_handler(model_class, writable_fields):
    """Create handler for supplier that supports image_url."""
    def handler(user, arguments):
        image_url = arguments.pop("image_url", None)
        kwargs = {}
        for field_name in writable_fields:
            if field_name in arguments:
                kwargs[field_name] = _coerce_field_value(
                    model_class, field_name, arguments[field_name])
        if hasattr(model_class, "created_by"):
            kwargs["created_by"] = user
        try:
            obj = model_class(**kwargs)
            if image_url:
                _apply_logo_from_url(obj, image_url)
            obj.full_clean()
            obj.save()
            ts_status = _apply_timestamp_override(obj, model_class, arguments, user)
        except (ValueError, ValidationError, Exception) as e:
            return _error(str(e))
        fields = [f.name for f in model_class._meta.fields]
        result = _serialize_obj(obj, fields)
        if ts_status == "ignored_no_permission":
            result["warning"] = (
                "created_at / updated_at were ignored: this account lacks the "
                "system.data_import.override_dates permission."
            )
        return result
    return handler


def _update_supplier_with_logo_handler(model_class, writable_fields):
    """Update handler for supplier that supports image_url."""
    def handler(user, arguments):
        image_url = arguments.pop("image_url", None)
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
        if not qs.exists():
            return _error("Access denied: object is outside your allowed scopes.")
        changed_fields = set()
        for field_name in writable_fields:
            if field_name in arguments:
                setattr(obj, field_name, _coerce_field_value(
                    model_class, field_name, arguments[field_name]))
                changed_fields.add(field_name)
        if image_url:
            try:
                _apply_logo_from_url(obj, image_url)
            except ValueError as e:
                return _error(str(e))
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        fields = [f.name for f in model_class._meta.fields]
        return _serialize_obj(obj, fields)
    return handler


def _update_supplier_logo_handler(user, arguments):
    """Update a supplier's logo and generate size variants."""
    from helpers.image_utils import download_image_to_data_uri, generate_image_variants

    pk = arguments.get("id")
    logo_uri = arguments.get("logo")
    image_url = arguments.get("image_url")
    if not pk:
        raise InvalidParamsError("id is required.")
    if not logo_uri and not image_url:
        raise InvalidParamsError("Either 'logo' (base64 data URI) or 'image_url' is required.")

    Supplier = apps.get_model("assets", "Supplier")
    try:
        supplier = Supplier.objects.get(pk=pk)
    except Supplier.DoesNotExist:
        return _error("Supplier not found.")

    qs = _filter_by_scopes(Supplier.objects.filter(pk=pk), user)
    if not qs.exists():
        return _error("Access denied: object is outside your allowed scopes.")

    # Resolve logo data URI from URL if provided.
    if image_url and not logo_uri:
        try:
            logo_uri = download_image_to_data_uri(image_url)
        except ValueError as e:
            return _error(str(e))

    try:
        variants = generate_image_variants(logo_uri)
    except Exception as e:
        return _error(f"Invalid image data: {e}")

    supplier.logo = logo_uri
    supplier.logo_16 = variants[16]
    supplier.logo_32 = variants[32]
    supplier.logo_64 = variants[64]

    try:
        supplier.full_clean()
        supplier.save()
    except (ValidationError, Exception) as e:
        return _error(str(e))

    fields = [f.name for f in Supplier._meta.fields]
    return _serialize_obj(supplier, fields)


# ── Generic CRUD registration helper ──────────────────────

def _register_crud(server, entity_name, model_class, perm_prefix,
                   list_fields, writable_fields, search_fields=None,
                   filters=None, scope_filtered=True, has_approve=True,
                   field_overrides=None, required_fields=None,
                   m2m_fields=None, list_queryset_filter=None,
                   list_extra_filter_props=None, pre_clean=None):
    """Register list, get, create, update, delete (and optionally approve) tools for an entity.

    ``list_queryset_filter`` / ``list_extra_filter_props`` add a derived list
    filter (a ``(qs, arguments) -> qs`` hook plus its JSON-schema properties)
    that the generic equality filters cannot express.
    """

    display_name = entity_name.replace("_", " ")
    filter_props = {}
    for f in (filters or []):
        filter_props[f] = {"type": "string", "description": f"Filter by {f}"}
    if list_extra_filter_props:
        filter_props.update(list_extra_filter_props)

    # List
    server.register_tool(
        f"list_{entity_name}s",
        f"List {display_name}s with optional search and filters",
        _list_schema(filter_props),
        require_perm(f"{perm_prefix}.read")(
            _list_handler(model_class, list_fields, search_fields, filters, scope_filtered,
                          queryset_filter=list_queryset_filter)
        ),
    )

    # Get
    server.register_tool(
        f"get_{entity_name}",
        f"Get a {display_name} by ID",
        _id_schema(),
        require_perm(f"{perm_prefix}.read")(
            _get_handler(model_class, list_fields, scope_filtered)
        ),
    )

    # Create
    overrides = field_overrides or {}
    create_props = {}
    for f in writable_fields:
        create_props[f] = overrides.get(f, {"type": "string", "description": f})
    # Optional legacy timestamps for bulk migration. Applied only for callers
    # holding "system.data_import.override_dates" (ignored otherwise).
    _ts_desc = (
        "Optional ISO 8601 date-time to preserve from a legacy system on bulk "
        "import (e.g. 2023-05-12T09:00:00Z). Requires the "
        "'system.data_import.override_dates' permission; ignored without it."
    )
    model_field_names = {f.name for f in model_class._meta.fields}
    for ts in ("created_at", "updated_at"):
        if ts in model_field_names:
            create_props.setdefault(ts, {"type": "string", "description": _ts_desc})
    server.register_tool(
        f"create_{entity_name}",
        f"Create a new {display_name}",
        _obj_schema(create_props, required_fields),
        require_perm(f"{perm_prefix}.create")(
            _create_handler(model_class, writable_fields, scope_filtered, m2m_fields,
                            pre_clean=pre_clean)
        ),
    )

    # Batch Create / Upsert
    server.register_tool(
        f"batch_create_{entity_name}s",
        f"Create or upsert multiple {display_name}s in one call (max 500). "
        f"Non-atomic: valid items are applied even if others fail. "
        f"Pass 'match_on' (a list of field names, e.g. [\"name\"]) to make the "
        f"call idempotent: each item whose match_on values already exist is "
        f"UPDATED in place instead of duplicated, so a failed import can be "
        f"safely replayed. Returns per-item status (created / updated / error) "
        f"with created, updated and error counts.",
        {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": _obj_schema(create_props, required_fields),
                    "description": f"Array of {display_name} objects to create or upsert (max 500).",
                },
                "match_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional business key: list of writable field names used "
                        "to find an existing record (e.g. [\"name\"]). When an item "
                        "matches, it is updated; otherwise it is created. Omit for "
                        "create-only behaviour. Many-to-many fields are not allowed."
                    ),
                },
            },
            "required": ["items"],
        },
        require_perm(f"{perm_prefix}.create")(
            _batch_create_handler(model_class, writable_fields, scope_filtered, m2m_fields,
                                  pre_clean=pre_clean)
        ),
    )

    # Update
    update_props = {"id": {"type": "string", "description": "UUID of the object to update"}}
    for f in writable_fields:
        update_props[f] = overrides.get(f, {"type": "string", "description": f})
    server.register_tool(
        f"update_{entity_name}",
        f"Update an existing {display_name}",
        _obj_schema(update_props, ["id"]),
        require_perm(f"{perm_prefix}.update")(
            _update_handler(model_class, writable_fields, scope_filtered, m2m_fields)
        ),
    )

    # Delete
    server.register_tool(
        f"delete_{entity_name}",
        f"Delete a {display_name}",
        _id_schema(),
        require_perm(f"{perm_prefix}.delete")(
            _delete_handler(model_class, scope_filtered)
        ),
    )

    # Lifecycle transitions
    if has_approve:
        transition_tool = f"transition_{entity_name}"
        if transition_tool not in server._tools:
            server.register_tool(
                transition_tool,
                f"Change the lifecycle state of a {display_name} "
                f"(e.g. draft -> pending -> validated -> archived). The transition is "
                f"validated against the entity's workflow: required permission, "
                f"mandatory comment, and side effects (owner notification on submit, "
                f"validation stamping).",
                _obj_schema(
                    {
                        "id": {"type": "string", "description": f"UUID of the {display_name}"},
                        "target_state": {
                            "type": "string",
                            "description": "Target lifecycle state code (see <entity>_allowed_transitions).",
                        },
                        "comment": {
                            "type": "string",
                            "description": "Comment, mandatory for transitions that require one.",
                        },
                    },
                    required=["id", "target_state"],
                ),
                require_perm(f"{perm_prefix}.read")(
                    _transition_handler(model_class, perm_prefix, scope_filtered)
                ),
            )

        allowed_tool = f"{entity_name}_allowed_transitions"
        if allowed_tool not in server._tools:
            server.register_tool(
                allowed_tool,
                f"List the lifecycle transitions the caller may perform on a "
                f"{display_name} from its current state.",
                _id_schema(),
                require_perm(f"{perm_prefix}.read")(
                    _allowed_transitions_handler(model_class, perm_prefix, scope_filtered)
                ),
            )

    # History (unified change / transition timeline)
    if hasattr(model_class, "history"):
        history_tool = f"get_{entity_name}_history"
        if history_tool not in server._tools:
            server.register_tool(
                history_tool,
                f"Return the change history of a {display_name}: field-level diffs, "
                f"approval events and lifecycle transitions (with comments where "
                f"recorded) merged into one reverse-chronological timeline.",
                _obj_schema(
                    {
                        "id": {"type": "string", "description": f"UUID of the {display_name}"},
                        "limit": {"type": "integer", "description": "Max entries (default 100, max 500)."},
                        "offset": {"type": "integer", "description": "Entries to skip (pagination)."},
                    },
                    required=["id"],
                ),
                require_perm(f"{perm_prefix}.read")(
                    _history_handler(model_class, scope_filtered)
                ),
            )


# ── Reports Module ────────────────────────────────────────

def _register_reports_tools(server):
    Report = _get_model("reports", "Report")

    report_fields = [
        "id", "report_type", "name", "status", "file_name",
        "created_at", "created_by",
    ]

    # List reports
    @require_perm("reports.report.read")
    def list_reports(user, arguments):
        qs = Report.objects.all().order_by("-created_at")
        report_type = arguments.get("report_type")
        if report_type:
            qs = qs.filter(report_type=report_type)
        limit = min(int(arguments.get("limit", 50)), 200)
        offset = int(arguments.get("offset", 0))
        total = qs.count()
        items = _serialize_qs(qs, report_fields, limit, offset)
        return {"total": total, "items": items, "limit": limit, "offset": offset}

    server.register_tool(
        "list_reports",
        "List generated reports, optionally filtered by report_type",
        {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "description": "Filter by report type (e.g. 'soa')",
                },
                "limit": {"type": "integer", "description": "Max results (default 50)"},
                "offset": {"type": "integer", "description": "Offset for pagination"},
            },
        },
        list_reports,
    )

    # Generate SoA report
    @require_perm("reports.report.create")
    def generate_soa_report(user, arguments):
        framework_ids = arguments.get("framework_ids")
        if not framework_ids:
            raise InvalidParamsError("framework_ids is required (list of UUIDs).")

        Framework = _get_model("compliance", "Framework")
        frameworks = Framework.objects.filter(id__in=framework_ids)
        if not frameworks.exists():
            return _error("No frameworks found for given IDs.")

        from reports.constants import ReportStatus, ReportType
        from reports.generators import generate_soa_pdf

        fw_names = ", ".join(fw.short_name or fw.name for fw in frameworks)
        report_name = f"Statement of Applicability - {fw_names}"

        try:
            filename, pdf_bytes = generate_soa_pdf(frameworks, user)
            report = Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=user,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(frameworks)
        except Exception:
            report = Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=user,
            )

        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_soa_report",
        "Generate a Statement of Applicability (SoA) PDF report for one or more frameworks",
        {
            "type": "object",
            "properties": {
                "framework_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of framework UUIDs to include in the SoA",
                },
            },
            "required": ["framework_ids"],
        },
        generate_soa_report,
    )

    # Generate audit report
    @require_perm("reports.report.create")
    def generate_audit_report(user, arguments):
        assessment_id = arguments.get("assessment_id")
        if not assessment_id:
            raise InvalidParamsError("assessment_id is required (UUID).")

        ComplianceAssessment = _get_model("compliance", "ComplianceAssessment")
        try:
            assessment = ComplianceAssessment.objects.get(pk=assessment_id)
        except ComplianceAssessment.DoesNotExist:
            return _error("Assessment not found.")

        from compliance.constants import AssessmentStatus
        if assessment.status not in (AssessmentStatus.COMPLETED, AssessmentStatus.CLOSED):
            return _error("The assessment must be completed or closed to generate a report.")

        from reports.constants import ReportStatus, ReportType
        from reports.generators import generate_audit_report_pdf

        report_name = f"Audit report - {assessment.reference} : {assessment.name}"

        try:
            filename, pdf_bytes = generate_audit_report_pdf(assessment, user)
            report = Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=user,
                assessment=assessment,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(assessment.frameworks.all())
        except Exception:
            report = Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=user,
                assessment=assessment,
            )

        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_audit_report",
        "Generate an audit report PDF for a completed or closed compliance assessment",
        {
            "type": "object",
            "properties": {
                "assessment_id": {
                    "type": "string",
                    "description": "UUID of the compliance assessment (must be completed or closed)",
                },
            },
            "required": ["assessment_id"],
        },
        generate_audit_report,
    )

    # Generate risk register
    @require_perm("risks.export.read")
    def generate_risk_register(user, arguments):
        """Generate an Excel export of the risk register.

        Parameters
        ----------
        scope_ids : list[str], optional
            Restrict the export to risks whose assessment has at least one of
            these scopes. If omitted, the export is filtered by the user's
            allowed scopes (or unfiltered for superusers).
        assessment_id : str, optional
            Restrict the export to risks belonging to this assessment.
        status : str, optional
            Filter by risk status.
        priority : str, optional
            Filter by risk priority.
        """
        Risk = _get_model("risks", "Risk")
        qs = Risk.objects.all()

        # Scope filtering: explicit scope_ids wins; otherwise apply user scopes.
        scope_ids = arguments.get("scope_ids")
        if scope_ids:
            qs = qs.filter(assessment__scopes__id__in=scope_ids).distinct()
        elif not user.is_superuser:
            user_scopes = user.get_allowed_scope_ids()
            if user_scopes is not None:
                qs = qs.filter(assessment__scopes__id__in=user_scopes).distinct()

        assessment_id = arguments.get("assessment_id")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        status_filter = arguments.get("status")
        if status_filter:
            qs = qs.filter(workflow_state=status_filter)
        priority = arguments.get("priority")
        if priority:
            qs = qs.filter(priority=priority)

        from reports.constants import ReportStatus, ReportType
        from reports.generators import generate_risk_register_xlsx

        try:
            filename, content = generate_risk_register_xlsx(qs, user)
            report = Report.objects.create(
                report_type=ReportType.RISK_REGISTER,
                name=f"Risk register - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                status=ReportStatus.COMPLETED,
                created_by=user,
                file_content=content,
                file_name=filename,
            )
        except Exception as exc:
            Report.objects.create(
                report_type=ReportType.RISK_REGISTER,
                name="Risk register",
                status=ReportStatus.FAILED,
                created_by=user,
            )
            return _error(f"Failed to generate risk register: {exc}")

        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_risk_register",
        (
            "Generate an Excel (.xlsx) export of the risk register. "
            "Optional filters: scope_ids, assessment_id, status, priority. "
            "When omitted, scope filtering falls back to the user's allowed "
            "scopes. The generated file is persisted as a Report."
        ),
        {
            "type": "object",
            "properties": {
                "scope_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Restrict to risks under these scope UUIDs.",
                },
                "assessment_id": {
                    "type": "string",
                    "description": "Restrict to risks under this assessment UUID.",
                },
                "status": {"type": "string", "description": "Filter by risk status."},
                "priority": {"type": "string", "description": "Filter by risk priority."},
            },
        },
        generate_risk_register,
    )

    # Generate ISO 27005 report (DOCX)
    @require_perm("risks.export.read")
    def generate_iso27005_report(user, arguments):
        """Generate an ISO 27005 risk assessment report (DOCX).

        Parameters
        ----------
        assessment_id : str (required)
            UUID of the RiskAssessment to export. Scope access is enforced.
        """
        assessment_id = arguments.get("assessment_id")
        if not assessment_id:
            raise InvalidParamsError("assessment_id is required.")

        RiskAssessment = _get_model("risks", "RiskAssessment")
        try:
            assessment = RiskAssessment.objects.get(pk=assessment_id)
        except RiskAssessment.DoesNotExist:
            return _error("Assessment not found.")

        # Scope check: superuser bypasses; otherwise the assessment must
        # share at least one scope with the user.
        if not user.is_superuser:
            scope_ids = user.get_allowed_scope_ids()
            if scope_ids is not None:
                if not assessment.scopes.filter(id__in=scope_ids).exists():
                    return _error("Access denied: assessment outside your allowed scopes.")

        from reports.constants import ReportStatus, ReportType
        from reports.iso27005_report import generate_iso27005_report_docx

        try:
            filename, content = generate_iso27005_report_docx(assessment, user)
            report = Report.objects.create(
                report_type=ReportType.ISO27005_REPORT,
                name=f"ISO 27005 report - {assessment.reference} - "
                     f"{timezone.now().strftime('%Y-%m-%d %H:%M')}",
                status=ReportStatus.COMPLETED,
                created_by=user,
                file_content=content,
                file_name=filename,
            )
        except Exception as exc:
            Report.objects.create(
                report_type=ReportType.ISO27005_REPORT,
                name=f"ISO 27005 report - {assessment.reference}",
                status=ReportStatus.FAILED,
                created_by=user,
            )
            return _error(f"Failed to generate ISO 27005 report: {exc}")

        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_iso27005_report",
        (
            "Generate an ISO 27005 risk assessment DOCX report for a single "
            "assessment. The report covers context, criteria, threats, "
            "vulnerabilities, analyses, consolidated risks, treatment plans "
            "and acceptances. Persisted as a Report."
        ),
        {
            "type": "object",
            "properties": {
                "assessment_id": {
                    "type": "string",
                    "description": "UUID of the RiskAssessment to export.",
                },
            },
            "required": ["assessment_id"],
        },
        generate_iso27005_report,
    )

    # Delete report
    @require_perm("reports.report.delete")
    def delete_report(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            report = Report.objects.get(pk=pk)
        except Report.DoesNotExist:
            return _error("Report not found.")
        report.delete()
        return {"deleted": True}

    server.register_tool(
        "delete_report",
        "Delete a generated report",
        _id_schema(),
        delete_report,
    )

    # Download report content (base64) - CAIRN-RPT-01
    @require_perm("reports.report.read")
    def download_report(user, arguments):
        import base64
        import os
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            report = Report.objects.get(pk=pk)
        except Report.DoesNotExist:
            return _error("Report not found.")
        if not report.file_content:
            return _error(
                "Report has no content (status may be 'failed' or 'pending')."
            )
        content_types = {
            ".pdf": "application/pdf",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        ext = os.path.splitext(report.file_name or "")[1].lower()
        content_type = content_types.get(ext, "application/octet-stream")
        raw = bytes(report.file_content)
        return {
            "id": str(report.pk),
            "file_name": report.file_name,
            "content_type": content_type,
            "size_bytes": len(raw),
            "content_base64": base64.b64encode(raw).decode("ascii"),
        }

    server.register_tool(
        "download_report",
        (
            "Retrieve the binary content of a previously generated report. "
            "Returns the file as a base64-encoded string along with its "
            "content type, size and original filename. Use list_reports first "
            "to discover available report IDs."
        ),
        _id_schema(),
        download_report,
    )

    # Generate management review (PPTX)
    @require_perm("reports.report.create")
    def generate_management_review_pptx_tool(user, arguments):
        scope_ids = arguments.get("scope_ids")
        period_start = arguments.get("period_start")
        period_end = arguments.get("period_end")
        from datetime import date as date_type
        if period_start:
            period_start = date_type.fromisoformat(period_start)
        if period_end:
            period_end = date_type.fromisoformat(period_end)
        from reports.constants import ReportStatus, ReportType
        from reports.management_review import generate_management_review_pptx

        report_name = "Management review - Presentation"
        try:
            filename, file_bytes = generate_management_review_pptx(
                user, scope_ids,
                period_start=period_start, period_end=period_end,
            )
            report = Report.objects.create(
                report_type=ReportType.MANAGEMENT_REVIEW_PPTX,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=user,
                file_content=file_bytes,
                file_name=filename,
            )
        except Exception:
            report = Report.objects.create(
                report_type=ReportType.MANAGEMENT_REVIEW_PPTX,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=user,
            )
        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_management_review_pptx",
        "Generate a management review presentation (PowerPoint) covering ISO 27001 clause 9.3 inputs: action plans, issues, stakeholders, security performance, risks, and improvement opportunities",
        {
            "type": "object",
            "properties": {
                "scope_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of scope UUIDs to filter data. Omit to include all data.",
                },
                "period_start": {
                    "type": "string",
                    "description": "Start of the review period (YYYY-MM-DD). Omit to include all past data.",
                },
                "period_end": {
                    "type": "string",
                    "description": "End of the review period (YYYY-MM-DD). Defaults to today.",
                },
            },
        },
        generate_management_review_pptx_tool,
    )

    # Generate management review (DOCX)
    @require_perm("reports.report.create")
    def generate_management_review_docx_tool(user, arguments):
        scope_ids = arguments.get("scope_ids")
        period_start = arguments.get("period_start")
        period_end = arguments.get("period_end")
        from datetime import date as date_type
        if period_start:
            period_start = date_type.fromisoformat(period_start)
        if period_end:
            period_end = date_type.fromisoformat(period_end)
        from reports.constants import ReportStatus, ReportType
        from reports.management_review import generate_management_review_docx

        report_name = "Management review - Minutes"
        try:
            filename, file_bytes = generate_management_review_docx(
                user, scope_ids,
                period_start=period_start, period_end=period_end,
            )
            report = Report.objects.create(
                report_type=ReportType.MANAGEMENT_REVIEW_DOCX,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=user,
                file_content=file_bytes,
                file_name=filename,
            )
        except Exception:
            report = Report.objects.create(
                report_type=ReportType.MANAGEMENT_REVIEW_DOCX,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=user,
            )
        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_management_review_docx",
        "Generate a management review meeting minutes document (Word) covering ISO 27001 clause 9.3 inputs: action plans, issues, stakeholders, security performance, risks, and improvement opportunities",
        {
            "type": "object",
            "properties": {
                "scope_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of scope UUIDs to filter data. Omit to include all data.",
                },
                "period_start": {
                    "type": "string",
                    "description": "Start of the review period (YYYY-MM-DD). Omit to include all past data.",
                },
                "period_end": {
                    "type": "string",
                    "description": "End of the review period (YYYY-MM-DD). Defaults to today.",
                },
            },
        },
        generate_management_review_docx_tool,
    )

    # ═══════════════════════════════════════════════════════════════
    # Persistent management reviews (ISO 27001:2022 clause 9.3)
    # ═══════════════════════════════════════════════════════════════

    MR_FIELDS = [
        "id", "reference", "title", "description",
        "frequency", "period_start", "period_end",
        "planned_date", "held_date", "location", "status",
        "facilitator", "approver", "next_review_date",
        "summary", "created_at", "updated_at",
    ]

    @require_perm("reports.management_review.read")
    def list_management_reviews(user, arguments):
        """List management reviews with optional filters."""
        MR = _get_model("reports", "ManagementReview")
        qs = MR.objects.all()
        status_filter = arguments.get("status")
        if status_filter:
            qs = qs.filter(workflow_state=status_filter)
        scope_id = arguments.get("scope_id")
        if scope_id:
            qs = qs.filter(scopes__id=scope_id)
        qs = qs.order_by("-planned_date")
        return _serialize_qs(
            qs, fields=MR_FIELDS,
            limit=int(arguments.get("limit", 50)),
            offset=int(arguments.get("offset", 0)),
        )

    server.register_tool(
        "list_management_reviews",
        "List management reviews (ISO 27001:2022 clause 9.3). Filter by status or scope.",
        {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "planned|in_preparation|held|closed|cancelled"},
                "scope_id": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
        list_management_reviews,
    )

    @require_perm("reports.management_review.read")
    def get_management_review(user, arguments):
        MR = _get_model("reports", "ManagementReview")
        review_id = arguments.get("id")
        if not review_id:
            return _error("id is required")
        try:
            review = MR.objects.get(pk=review_id)
        except MR.DoesNotExist:
            return _error(f"Management review {review_id} not found")
        data = _serialize_obj(review, MR_FIELDS)
        data["decisions_count"] = review.decisions.count()
        data["isms_changes_count"] = review.isms_changes.count()
        data["participants_count"] = review.participants.count()
        data["has_snapshot"] = review.has_snapshot
        return data

    server.register_tool(
        "get_management_review",
        "Get a management review by ID.",
        {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
        get_management_review,
    )

    @require_perm("reports.management_review.create")
    def create_management_review(user, arguments):
        MR = _get_model("reports", "ManagementReview")
        User = _get_model("accounts", "User")
        required = ["title", "frequency", "period_start", "period_end", "planned_date", "facilitator_id"]
        for field in required:
            if not arguments.get(field):
                return _error(f"{field} is required")
        try:
            facilitator = User.objects.get(pk=arguments["facilitator_id"])
        except User.DoesNotExist:
            return _error("facilitator not found")
        review = MR.objects.create(
            title=arguments["title"],
            description=arguments.get("description", ""),
            frequency=arguments["frequency"],
            period_start=arguments["period_start"],
            period_end=arguments["period_end"],
            planned_date=arguments["planned_date"],
            location=arguments.get("location", ""),
            facilitator=facilitator,
            created_by=user,
        )
        scope_ids = arguments.get("scope_ids") or []
        if scope_ids:
            review.scopes.set(scope_ids)
        return _serialize_obj(review, MR_FIELDS)

    server.register_tool(
        "create_management_review",
        "Create a management review (ISO 27001:2022 clause 9.3).",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "frequency": {"type": "string", "description": "quarterly|semiannual|annual|exceptional"},
                "period_start": {"type": "string", "description": "YYYY-MM-DD"},
                "period_end": {"type": "string", "description": "YYYY-MM-DD"},
                "planned_date": {"type": "string", "description": "YYYY-MM-DD"},
                "location": {"type": "string"},
                "facilitator_id": {"type": "string"},
                "scope_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "frequency", "period_start", "period_end", "planned_date", "facilitator_id"],
        },
        create_management_review,
    )

    @require_perm("reports.management_review.update")
    def transition_management_review(user, arguments):
        MR = _get_model("reports", "ManagementReview")
        review_id = arguments.get("id")
        target = arguments.get("target_status")
        comment = arguments.get("comment", "")
        if not review_id or not target:
            return _error("id and target_status are required")
        try:
            review = MR.objects.get(pk=review_id)
        except MR.DoesNotExist:
            return _error("review not found")
        if target == "closed" and not user.has_perm("reports.management_review.approve"):
            return _error("Closure requires approve permission")
        try:
            review.transition_to(target, user, comment=comment)
        except ValueError as exc:
            return _error(str(exc))
        if review.status == "closed":
            from reports.management_review import gather_management_review_data
            from reports.management_review_views import _serialize_snapshot
            try:
                scope_ids = list(review.scopes.values_list("id", flat=True))
                data = gather_management_review_data(
                    user, scope_ids=scope_ids,
                    period_start=review.period_start,
                    period_end=review.period_end,
                )
                review.take_snapshot(_serialize_snapshot(data))
            except Exception:
                pass
        return _serialize_obj(review, MR_FIELDS)

    server.register_tool(
        "transition_management_review",
        "Transition a management review to a new status (planned -> in_preparation -> held -> closed, or cancelled).",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "target_status": {"type": "string"},
                "comment": {"type": "string"},
            },
            "required": ["id", "target_status"],
        },
        transition_management_review,
    )

    @require_perm("reports.management_review.read")
    def export_management_review(user, arguments):
        """Return a base64-encoded export (DOCX or PPTX) of a management review."""
        import base64 as _b64
        MR = _get_model("reports", "ManagementReview")
        review_id = arguments.get("id")
        fmt = arguments.get("format", "docx")
        try:
            review = MR.objects.get(pk=review_id)
        except MR.DoesNotExist:
            return _error("review not found")
        scope_ids = list(review.scopes.values_list("id", flat=True))
        from reports.management_review import (
            generate_management_review_docx,
            generate_management_review_pptx,
        )
        gen = generate_management_review_pptx if fmt == "pptx" else generate_management_review_docx
        try:
            filename, data = gen(
                user, scope_ids=scope_ids,
                period_start=review.period_start,
                period_end=review.period_end,
                review=review,
            )
        except Exception as exc:
            return _error(f"Export failed: {exc}")
        return {
            "filename": filename,
            "format": fmt,
            "content_base64": _b64.b64encode(data).decode("ascii"),
            "size_bytes": len(data),
        }

    server.register_tool(
        "export_management_review",
        "Export a management review as DOCX (meeting minutes) or PPTX (presentation). Returns base64-encoded content.",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "format": {"type": "string", "description": "docx|pptx", "default": "docx"},
            },
            "required": ["id"],
        },
        export_management_review,
    )

    DECISION_FIELDS = [
        "id", "reference", "review", "category", "input_clause",
        "title", "description", "owner", "due_date", "priority",
        "status", "linked_action_plan", "created_at", "updated_at",
    ]

    @require_perm("reports.management_review.read")
    def list_management_review_decisions(user, arguments):
        D = _get_model("reports", "ManagementReviewDecision")
        qs = D.objects.all()
        review_id = arguments.get("review_id")
        if review_id:
            qs = qs.filter(review_id=review_id)
        status_filter = arguments.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return _serialize_qs(qs, fields=DECISION_FIELDS,
                             limit=int(arguments.get("limit", 50)),
                             offset=int(arguments.get("offset", 0)))

    server.register_tool(
        "list_management_review_decisions",
        "List decisions (ISO 27001:2022 clause 9.3.3 outputs). Filter by review or status.",
        {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
        list_management_review_decisions,
    )

    @require_perm("reports.management_review.update")
    def create_management_review_decision(user, arguments):
        D = _get_model("reports", "ManagementReviewDecision")
        MR = _get_model("reports", "ManagementReview")
        User = _get_model("accounts", "User")
        review_id = arguments.get("review_id")
        if not review_id:
            return _error("review_id is required")
        try:
            review = MR.objects.get(pk=review_id)
        except MR.DoesNotExist:
            return _error("review not found")
        owner = None
        if arguments.get("owner_id"):
            try:
                owner = User.objects.get(pk=arguments["owner_id"])
            except User.DoesNotExist:
                return _error("owner not found")
        decision = D.objects.create(
            review=review,
            category=arguments.get("category", "improvement"),
            input_clause=arguments.get("input_clause", ""),
            title=arguments.get("title", ""),
            description=arguments.get("description", ""),
            rationale=arguments.get("rationale", ""),
            owner=owner,
            due_date=arguments.get("due_date") or None,
            priority=arguments.get("priority", "medium"),
            status=arguments.get("status", "pending"),
        )
        return _serialize_obj(decision, DECISION_FIELDS)

    server.register_tool(
        "create_management_review_decision",
        "Record a decision from a management review (ISO 27001:2022 clause 9.3.3).",
        {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "category": {"type": "string", "description": "improvement|isms_change|resource_allocation|risk_acceptance|objective_adjustment|policy_update|other"},
                "input_clause": {"type": "string", "description": "9.3.2 clause letter: a|b|c|d1|d2|d3|d4|e|f|g"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "rationale": {"type": "string"},
                "owner_id": {"type": "string"},
                "due_date": {"type": "string"},
                "priority": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["review_id", "title", "description"],
        },
        create_management_review_decision,
    )

    @require_perm("reports.management_review.update")
    def promote_decision_to_action_plan(user, arguments):
        """Create a ComplianceActionPlan from a decision and link them."""
        D = _get_model("reports", "ManagementReviewDecision")
        AP = _get_model("compliance", "ComplianceActionPlan")
        decision_id = arguments.get("decision_id")
        if not user.has_perm("compliance.action_plan.create"):
            return _error("Missing compliance.action_plan.create permission")
        try:
            decision = D.objects.get(pk=decision_id)
        except D.DoesNotExist:
            return _error("decision not found")
        if decision.linked_action_plan_id:
            return _error("Decision already linked to an action plan")
        plan = AP.objects.create(
            name=decision.title,
            description=decision.description,
            gap_description=decision.description,
            remediation_plan=decision.rationale or decision.description,
            priority=decision.priority,
            owner=decision.owner or user,
            target_date=decision.due_date,
            originating_review=decision.review,
            created_by=user,
        )
        plan.scopes.set(decision.review.scopes.all())
        decision.linked_action_plan = plan
        if decision.status == "pending":
            decision.status = "in_progress"
        decision.save(update_fields=["linked_action_plan", "status", "updated_at"])
        return {"action_plan_id": str(plan.pk), "action_plan_reference": plan.reference}

    server.register_tool(
        "promote_decision_to_action_plan",
        "Create a ComplianceActionPlan from a management review decision.",
        {
            "type": "object",
            "properties": {"decision_id": {"type": "string"}},
            "required": ["decision_id"],
        },
        promote_decision_to_action_plan,
    )

    ISMS_CHANGE_FIELDS = [
        "id", "reference", "review", "change_type", "title",
        "description", "owner", "status", "target_date", "implemented_at",
        "created_at", "updated_at",
    ]

    @require_perm("reports.management_review.read")
    def list_isms_changes(user, arguments):
        C = _get_model("reports", "IsmsChange")
        qs = C.objects.all()
        review_id = arguments.get("review_id")
        if review_id:
            qs = qs.filter(review_id=review_id)
        return _serialize_qs(qs, fields=ISMS_CHANGE_FIELDS,
                             limit=int(arguments.get("limit", 50)),
                             offset=int(arguments.get("offset", 0)))

    server.register_tool(
        "list_isms_changes",
        "List ISMS changes decided during management reviews (ISO 27001:2022 clause 9.3.3).",
        {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
        list_isms_changes,
    )

    @require_perm("reports.management_review.update")
    def create_isms_change(user, arguments):
        C = _get_model("reports", "IsmsChange")
        MR = _get_model("reports", "ManagementReview")
        User = _get_model("accounts", "User")
        review_id = arguments.get("review_id")
        owner_id = arguments.get("owner_id")
        if not review_id or not owner_id:
            return _error("review_id and owner_id are required")
        try:
            review = MR.objects.get(pk=review_id)
            owner = User.objects.get(pk=owner_id)
        except (MR.DoesNotExist, User.DoesNotExist):
            return _error("review or owner not found")
        change = C.objects.create(
            review=review,
            change_type=arguments.get("change_type", "other"),
            title=arguments.get("title", ""),
            description=arguments.get("description", ""),
            impact_analysis=arguments.get("impact_analysis", ""),
            affected_policies=arguments.get("affected_policies", ""),
            owner=owner,
            status=arguments.get("status", "proposed"),
            target_date=arguments.get("target_date") or None,
        )
        return _serialize_obj(change, ISMS_CHANGE_FIELDS)

    server.register_tool(
        "create_isms_change",
        "Record an ISMS change decided during a management review.",
        {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "change_type": {"type": "string", "description": "scope|policy|control|organization|resource|process|other"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "impact_analysis": {"type": "string"},
                "affected_policies": {"type": "string"},
                "owner_id": {"type": "string"},
                "status": {"type": "string"},
                "target_date": {"type": "string"},
            },
            "required": ["review_id", "title", "description", "owner_id"],
        },
        create_isms_change,
    )

    FEEDBACK_FIELDS = [
        "id", "reference", "stakeholder", "channel", "received_date",
        "subject", "content", "sentiment", "severity", "status",
        "created_at", "updated_at",
    ]

    @require_perm("reports.management_review.update")
    def set_participant_signature(user, arguments):
        """Set a base64 PNG/JPEG signature on a participant.

        Non-eIDAS qualified signature. Any user with management_review.update
        can sign on behalf of participants.
        """
        P = _get_model("reports", "ManagementReviewParticipant")
        participant_id = arguments.get("participant_id")
        data_uri = arguments.get("signature_data_uri", "")
        if not participant_id or not data_uri.startswith("data:image/"):
            return _error("participant_id and a valid signature_data_uri (data:image/...) are required")
        try:
            participant = P.objects.get(pk=participant_id)
        except P.DoesNotExist:
            return _error("participant not found")
        participant.signature_data = data_uri
        participant.attended = True
        participant.save(update_fields=["signature_data", "attended"])
        return {
            "participant_id": str(participant.pk),
            "signed": True,
            "attended": participant.attended,
        }

    server.register_tool(
        "set_participant_signature",
        "Attach a graphical signature (data URI) to a participant for DOCX embedding.",
        {
            "type": "object",
            "properties": {
                "participant_id": {"type": "string"},
                "signature_data_uri": {
                    "type": "string",
                    "description": "Data URI, e.g. data:image/png;base64,iVBORw0KGgo...",
                },
            },
            "required": ["participant_id", "signature_data_uri"],
        },
        set_participant_signature,
    )

    @require_perm("context.stakeholder_feedback.read")
    def list_stakeholder_feedback(user, arguments):
        F = _get_model("context", "StakeholderFeedback")
        qs = F.objects.all()
        stakeholder_id = arguments.get("stakeholder_id")
        if stakeholder_id:
            qs = qs.filter(stakeholder_id=stakeholder_id)
        status_filter = arguments.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return _serialize_qs(qs, fields=FEEDBACK_FIELDS,
                             limit=int(arguments.get("limit", 50)),
                             offset=int(arguments.get("offset", 0)))

    server.register_tool(
        "list_stakeholder_feedback",
        "List formal stakeholder feedback (ISO 27001:2022 clause 9.3.2.e).",
        {
            "type": "object",
            "properties": {
                "stakeholder_id": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
        list_stakeholder_feedback,
    )

    @require_perm("context.stakeholder_feedback.create")
    def create_stakeholder_feedback(user, arguments):
        F = _get_model("context", "StakeholderFeedback")
        S = _get_model("context", "Stakeholder")
        stakeholder_id = arguments.get("stakeholder_id")
        if not stakeholder_id:
            return _error("stakeholder_id is required")
        try:
            stakeholder = S.objects.get(pk=stakeholder_id)
        except S.DoesNotExist:
            return _error("stakeholder not found")
        feedback = F.objects.create(
            stakeholder=stakeholder,
            channel=arguments.get("channel", "other"),
            received_date=arguments.get("received_date"),
            subject=arguments.get("subject", ""),
            content=arguments.get("content", ""),
            sentiment=arguments.get("sentiment", ""),
            severity=arguments.get("severity", ""),
            status=arguments.get("status", "new"),
            response=arguments.get("response", ""),
            created_by=user,
        )
        scope_ids = arguments.get("scope_ids") or []
        if scope_ids:
            feedback.scopes.set(scope_ids)
        return _serialize_obj(feedback, FEEDBACK_FIELDS)

    server.register_tool(
        "create_stakeholder_feedback",
        "Record formal feedback from an interested party (ISO 27001:2022 clause 9.3.2.e).",
        {
            "type": "object",
            "properties": {
                "stakeholder_id": {"type": "string"},
                "channel": {"type": "string", "description": "survey|meeting|complaint|email|audit|incident|other"},
                "received_date": {"type": "string"},
                "subject": {"type": "string"},
                "content": {"type": "string"},
                "sentiment": {"type": "string"},
                "severity": {"type": "string"},
                "status": {"type": "string"},
                "response": {"type": "string"},
                "scope_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["stakeholder_id", "received_date", "subject", "content"],
        },
        create_stakeholder_feedback,
    )

    # ── Company Settings ───────────────────────────────────

    company_fields = ["id", "name", "app_name", "assistant_name", "address", "accent_color", "use_logo_as_app_brand", "updated_at"]

    @require_perm("system.config.read")
    def get_company_settings(user, arguments):
        CompanySettings = _get_model("accounts", "CompanySettings")
        instance = CompanySettings.get()
        return _serialize_obj(instance, company_fields)

    server.register_tool(
        "get_company_settings",
        "Get the company settings (name, application name, AI assistant name, address, accent colour, whether the company logo replaces the Cairn logo)",
        {"type": "object", "properties": {}},
        get_company_settings,
    )

    @require_perm("system.config.update")
    def update_company_settings(user, arguments):
        CompanySettings = _get_model("accounts", "CompanySettings")
        instance = CompanySettings.get()
        if "name" in arguments:
            instance.name = arguments["name"]
        if "app_name" in arguments:
            instance.app_name = arguments["app_name"]
        if "assistant_name" in arguments:
            instance.assistant_name = arguments["assistant_name"]
        if "address" in arguments:
            instance.address = arguments["address"]
        if "accent_color" in arguments:
            raw = (arguments["accent_color"] or "").strip()
            if raw and not raw.startswith("#"):
                raw = "#" + raw
            valid = not raw or (
                len(raw) == 7 and raw[0] == "#"
                and all(c in "0123456789abcdefABCDEF" for c in raw[1:])
            )
            if not valid:
                raise ValueError("accent_color must be a 6-digit hex colour, e.g. #1E3A8A")
            instance.accent_color = raw.upper()
        if "use_logo_as_app_brand" in arguments:
            instance.use_logo_as_app_brand = bool(arguments["use_logo_as_app_brand"])
        instance.save()
        return _serialize_obj(instance, company_fields)

    server.register_tool(
        "update_company_settings",
        "Update company settings (name, application name, AI assistant name, address, accent colour, and/or whether the company logo replaces the Cairn logo)",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Company name",
                },
                "app_name": {
                    "type": "string",
                    "description": "Custom application name shown in the sidebar and tab titles (defaults to Cairn when empty)",
                },
                "assistant_name": {
                    "type": "string",
                    "description": "Custom name for the AI assistant shown in the command palette, its answers and the sidebar (defaults to Ask Cairn when empty)",
                },
                "address": {
                    "type": "string",
                    "description": "Company address (multi-line)",
                },
                "accent_color": {
                    "type": "string",
                    "description": "Accent colour as a 6-digit hex code (e.g. #1E3A8A) used throughout the app; empty string resets to the Cairn navy",
                },
                "use_logo_as_app_brand": {
                    "type": "boolean",
                    "description": (
                        "When true, the company logo replaces the Cairn logo across "
                        "the application (sidebar, page headers); the About dialog "
                        "always keeps the Cairn logo. Requires a company logo to be set."
                    ),
                },
            },
        },
        update_company_settings,
    )


# ── Trust Center Module ───────────────────────────────────

def _register_trust_center_tools(server):
    TrustCenterSettings = _get_model("trust_center", "TrustCenterSettings")
    TrustCenterCertification = _get_model("trust_center", "TrustCenterCertification")
    TrustCenterSubprocessor = _get_model("trust_center", "TrustCenterSubprocessor")
    TrustCenterMeasure = _get_model("trust_center", "TrustCenterMeasure")
    TrustCenterDocument = _get_model("trust_center", "TrustCenterDocument")

    settings_fields = [
        "id", "is_published", "headline", "intro", "contact_email",
        "show_compliance_percentages", "theme_accent", "custom_domain", "updated_at",
    ]
    settings_writable = [
        "is_published", "headline", "intro", "contact_email",
        "show_compliance_percentages", "theme_accent", "custom_domain",
    ]

    @require_perm("trust_center.settings.read")
    def get_trust_center_settings(user, arguments):
        return _serialize_obj(TrustCenterSettings.get(), settings_fields)

    server.register_tool(
        "get_trust_center_settings",
        "Get the public Trust Center settings (publication switch, headline, intro, "
        "security contact, theme).",
        {"type": "object", "properties": {}},
        get_trust_center_settings,
    )

    @require_perm("trust_center.settings.update")
    def update_trust_center_settings(user, arguments):
        instance = TrustCenterSettings.get()
        for field_name in settings_writable:
            if field_name in arguments:
                setattr(instance, field_name, arguments[field_name])
        try:
            instance.full_clean()
        except ValidationError as exc:
            return _error(str(exc))
        instance.save()
        return _serialize_obj(instance, settings_fields)

    server.register_tool(
        "update_trust_center_settings",
        "Update the public Trust Center settings. Set is_published=true to expose the "
        "public page and API; false takes the whole Trust Center offline (404).",
        {
            "type": "object",
            "properties": {
                "is_published": {"type": "boolean", "description": "Master switch: expose the public Trust Center page and API."},
                "headline": {"type": "string", "description": "Public hero headline."},
                "intro": {"type": "string", "description": "Public introduction paragraph."},
                "contact_email": {"type": "string", "description": "Public security contact email."},
                "show_compliance_percentages": {"type": "boolean", "description": "Show numeric compliance percentages on certifications."},
                "theme_accent": {"type": "string", "description": "Accent colour as a hex value, e.g. #1E3A8A."},
                "custom_domain": {"type": "string", "description": "Informational custom domain (routing is configured via the TRUST_CENTER_HOST env var)."},
            },
        },
        update_trust_center_settings,
    )

    _register_crud(
        server,
        "trust_center_certification",
        TrustCenterCertification,
        "trust_center.certification",
        list_fields=[
            "id", "reference", "framework", "public_label", "public_description",
            "show_percentage", "display_order", "workflow_state",
        ],
        writable_fields=[
            "framework", "public_label", "public_description",
            "show_percentage", "display_order",
        ],
        search_fields=["public_label", "public_description"],
        required_fields=["framework", "public_label"],
        scope_filtered=False,
        field_overrides={
            "framework": {"type": "string", "description": "UUID of the source compliance framework."},
            "show_percentage": {"type": "boolean", "description": "Show this certification's compliance percentage."},
            "display_order": {"type": "integer", "description": "Ascending sort order."},
        },
    )

    _register_crud(
        server,
        "trust_center_subprocessor",
        TrustCenterSubprocessor,
        "trust_center.subprocessor",
        list_fields=[
            "id", "reference", "supplier", "public_name", "purpose",
            "public_country", "public_website", "display_order", "workflow_state",
        ],
        writable_fields=[
            "supplier", "public_name", "purpose", "public_country",
            "public_website", "display_order",
        ],
        search_fields=["public_name", "purpose", "public_country"],
        required_fields=["supplier", "public_name"],
        scope_filtered=False,
        field_overrides={
            "supplier": {"type": "string", "description": "UUID of the source supplier."},
            "display_order": {"type": "integer", "description": "Ascending sort order."},
        },
    )

    _register_crud(
        server,
        "trust_center_measure",
        TrustCenterMeasure,
        "trust_center.measure",
        list_fields=[
            "id", "reference", "title", "description", "icon", "category",
            "display_order", "workflow_state",
        ],
        writable_fields=["title", "description", "icon", "category", "display_order"],
        search_fields=["title", "description"],
        required_fields=["title"],
        scope_filtered=False,
        field_overrides={
            "category": {"type": "string", "description": "One of: organizational, technical, physical."},
            "icon": {"type": "string", "description": "Bootstrap Icons name, e.g. bi-shield-check."},
            "display_order": {"type": "integer", "description": "Ascending sort order."},
        },
    )

    _register_crud(
        server,
        "trust_center_document",
        TrustCenterDocument,
        "trust_center.document",
        list_fields=[
            "id", "reference", "title", "description", "access", "requires_nda",
            "report", "file_name", "display_order", "workflow_state",
        ],
        writable_fields=[
            "title", "description", "access", "requires_nda", "report", "display_order",
        ],
        search_fields=["title", "description"],
        required_fields=["title"],
        scope_filtered=False,
        field_overrides={
            "access": {"type": "string", "description": "Access level: 'public' (direct download) or 'gated' (request + approval)."},
            "requires_nda": {"type": "boolean", "description": "Whether a gated document requires NDA acceptance."},
            "report": {"type": "string", "description": "UUID of the source generated report (required when creating via the API/MCP)."},
            "display_order": {"type": "integer", "description": "Ascending sort order."},
        },
    )

    # Document requests are read-only via MCP (they originate from the public
    # form); the only mutations are approve / reject, which carry side effects.
    DocumentRequest = _get_model("trust_center", "DocumentRequest")
    dr_fields = [
        "id", "reference", "document", "email", "requester_name", "company",
        "reason", "nda_accepted", "workflow_state", "reviewed_by", "reviewed_at",
        "decision_note", "download_count", "download_link_expires_at", "created_at",
    ]

    server.register_tool(
        "list_trust_center_document_requests",
        "List Trust Center gated-document access requests (optionally filter by workflow_state).",
        _list_schema({
            "workflow_state": {
                "type": "string",
                "description": "Filter by state: pending, approved, rejected.",
            }
        }),
        require_perm("trust_center.document_request.read")(
            _list_handler(
                DocumentRequest, dr_fields,
                search_fields=["email", "requester_name", "company"],
                filters=["workflow_state"], scope_filtered=False,
            )
        ),
    )

    server.register_tool(
        "get_trust_center_document_request",
        "Get a Trust Center document request by ID.",
        _id_schema(),
        require_perm("trust_center.document_request.read")(
            _get_handler(DocumentRequest, dr_fields, scope_filtered=False)
        ),
    )

    @require_perm("trust_center.document_request.approve")
    def approve_document_request(user, arguments):
        from django.conf import settings as _dj_settings
        from django.urls import reverse as _reverse

        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = DocumentRequest.objects.get(pk=pk)
        except DocumentRequest.DoesNotExist:
            return _error("Document request not found.")
        try:
            obj.transition_to("approved", user, enforce_permission=True)
        except Exception as exc:
            return _error(str(exc))
        obj.reviewed_by = user
        obj.reviewed_at = timezone.now()
        obj.save(update_fields=["reviewed_by", "reviewed_at", "updated_at"])
        token = obj.issue_download_link(_dj_settings.TRUST_CENTER_DOWNLOAD_TTL)
        from trust_center.notifications import send_gated_link_email

        send_gated_link_email(obj, _reverse("trust_center:gated-download", kwargs={"token": token}))
        return _serialize_obj(obj, dr_fields)

    server.register_tool(
        "approve_trust_center_document_request",
        "Approve a gated-document request: issues a time-limited signed download "
        "link and emails it to the requester.",
        _id_schema(),
        approve_document_request,
    )

    @require_perm("trust_center.document_request.approve")
    def reject_document_request(user, arguments):
        pk = arguments.get("id")
        comment = arguments.get("comment") or ""
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = DocumentRequest.objects.get(pk=pk)
        except DocumentRequest.DoesNotExist:
            return _error("Document request not found.")
        try:
            obj.transition_to("rejected", user, comment=comment, enforce_permission=True)
        except Exception as exc:
            return _error(str(exc))
        obj.reviewed_by = user
        obj.reviewed_at = timezone.now()
        if comment:
            obj.decision_note = comment
        obj.save(update_fields=["reviewed_by", "reviewed_at", "decision_note", "updated_at"])
        return _serialize_obj(obj, dr_fields)

    server.register_tool(
        "reject_trust_center_document_request",
        "Reject a pending gated-document request, or revoke access for an approved "
        "one. A comment is required.",
        _obj_schema(
            {
                "id": {"type": "string", "description": "UUID of the request"},
                "comment": {"type": "string", "description": "Reason (required)"},
            },
            required=["id", "comment"],
        ),
        reject_document_request,
    )

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Single source of truth for resolving a model's path to `context.Scope`.

Scope tenancy used to be answered in four places, each with its own copy of
the same three-branch decision. Two of them (`ScopeFilterMixin` and
`ScopeFilterAPIMixin`) grew support for a `scope_parent_lookup`, so a child
row could inherit its parent's scopes. The other two - the generic workflow
transition and history endpoints - and the MCP list layer did not, and fell
through to "no filtering" for any model without its own `scopes` M2M. A
child row was therefore readable, transitionable and fully auditable from
outside its scope.

Resolution happens here so a model that declares `scope_parent_lookup` is
honoured by every surface at once, and so a future surface has one function
to call rather than a pattern to reproduce.
"""
from django.apps import apps


def resolve_scope_lookup(model, explicit=None):
    """Return the ORM path from `model` to scope ids, or None when unscoped.

    `explicit` lets a view or viewset override the model-level declaration,
    preserving the historical behaviour of the two mixins.
    """
    if explicit:
        return explicit
    Scope = apps.get_model("context", "Scope")
    if model is Scope or getattr(model, "_meta", None) and model._meta.label == "context.Scope":
        return "id"
    lookup = getattr(model, "scope_parent_lookup", None)
    if lookup:
        return lookup
    if any(f.name == "scopes" for f in model._meta.many_to_many):
        return "scopes"
    return None


def filter_queryset_by_scopes(qs, scope_ids, explicit=None):
    """Restrict `qs` to rows reachable from `scope_ids`."""
    lookup = resolve_scope_lookup(qs.model, explicit)
    if lookup is None:
        return qs
    if lookup == "id":
        return qs.filter(id__in=scope_ids)
    return qs.filter(**{f"{lookup}__id__in": scope_ids}).distinct()


def object_in_scopes(obj, scope_ids):
    """Whether `obj` is visible to a user allowed `scope_ids`.

    An object that carries no scope at all stays visible. That is deliberate
    and matches the guard this replaces : scoping restricts what has been
    filed under a perimeter, it does not hide records nobody has filed yet.
    """
    model = type(obj)
    lookup = resolve_scope_lookup(model)
    if lookup is None:
        return True
    base = model._default_manager.filter(pk=obj.pk)
    if lookup == "id":
        return base.filter(id__in=scope_ids).exists()
    if not base.filter(**{f"{lookup}__isnull": False}).exists():
        return True
    return base.filter(**{f"{lookup}__id__in": scope_ids}).exists()

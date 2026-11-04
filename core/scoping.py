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
from django.db.models import Q


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
    """Restrict `qs` to rows reachable from `scope_ids`.

    A model whose parent relation is optional sets `scope_parent_optional`.
    Without it the join is an INNER JOIN and every row with no parent is
    dropped, which for a register holding parentless rows means hiding them
    from everyone but a superuser. With it, parentless rows stay visible,
    matching `object_in_scopes`.
    """
    lookup = resolve_scope_lookup(qs.model, explicit)
    if lookup is None:
        return qs
    if lookup == "id":
        return qs.filter(id__in=scope_ids)
    alternates = _alternate_lookups(qs.model, explicit)
    matches = Q(**{f"{lookup}__id__in": scope_ids})
    for alternate in alternates:
        matches |= Q(**{f"{alternate}__id__in": scope_ids})
    if getattr(qs.model, "scope_parent_optional", False):
        # Parentless rows stay visible, but only when no alternate parent
        # files them either : a row reachable through an alternate parent is
        # scoped by that parent.
        orphan = Q(**{f"{lookup}__isnull": True})
        for alternate in alternates:
            orphan &= Q(**{f"{alternate}__isnull": True})
        matches |= orphan
    return qs.filter(matches).distinct()


def _alternate_lookups(model, explicit=None):
    """Extra parent paths of a row that may be filed under one of several
    parents (``scope_parent_alternates``), e.g. a nonconformity raised by an
    audit, an incident or a control test. Ignored when a surface passes an
    explicit lookup."""
    if explicit:
        return ()
    return tuple(getattr(model, "scope_parent_alternates", ()) or ())


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
    lookups = (lookup, *_alternate_lookups(model))
    filed = Q()
    for path in lookups:
        filed |= Q(**{f"{path}__isnull": False})
    if not base.filter(filed).exists():
        return True
    reachable = Q()
    for path in lookups:
        reachable |= Q(**{f"{path}__id__in": scope_ids})
    return base.filter(reachable).exists()

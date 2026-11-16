# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django import template

register = template.Library()


def _scope_index(context):
    """``{pk: (name, parent_pk)}`` for every scope, read once per request.

    A scope cell prints the ancestors of each selection root; walking
    ``parent_scope`` cost one query per level, per row of the list. The whole
    tree is a few short rows, so it is read once and shared by every cell of
    the page.
    """
    from context.models import Scope

    request = context.get("request") if context is not None else None
    index = getattr(request, "_scope_name_index", None)
    if index is None:
        index = {
            pk: (name, parent_id)
            for pk, name, parent_id in Scope.objects.values_list("pk", "name", "parent_scope_id")
        }
        if request is not None:
            request._scope_name_index = index
    return index


def _selection_roots(scopes, context=None):
    """Return breadcrumb segments for selection roots only."""
    scope_list = list(scopes)
    scope_ids = {s.pk for s in scope_list}
    index = None

    crumbs = []
    for s in scope_list:
        if s.parent_scope_id in scope_ids:
            continue
        ancestors = []
        if s.parent_scope_id:
            if index is None:
                index = _scope_index(context)
            parent_id, seen = s.parent_scope_id, set()
            # ``seen`` guards against a cycle left in the data.
            while parent_id in index and parent_id not in seen:
                seen.add(parent_id)
                name, parent_id = index[parent_id]
                ancestors.insert(0, name)
        crumbs.append(ancestors + [s.name])

    return scope_list, crumbs


@register.inclusion_tag("widgets/grouped_scope_badges.html", takes_context=True)
def grouped_scope_badges(context, scopes):
    """Render scope breadcrumb pills, showing only selection roots.

    Since checking a parent automatically checks all descendants,
    child scopes whose parent is also in the list are redundant.
    Only *selection roots* (scopes whose parent is NOT in the list)
    are displayed, each as a breadcrumb pill with ancestor context.
    """
    _, crumbs = _selection_roots(scopes, context)
    return {"crumbs": crumbs}


@register.inclusion_tag("widgets/scope_popover.html", takes_context=True)
def scope_popover(context, scopes):
    """Render a compact count badge with a click-to-expand popover.

    Designed for table cells: shows « 3 » as a small pill, and on click
    reveals a floating panel listing the scope breadcrumb pills.
    """
    scope_list, crumbs = _selection_roots(scopes, context)
    return {"count": len(scope_list), "crumbs": crumbs}

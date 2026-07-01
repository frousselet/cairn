"""Shared UI template tags for Cairn.

This module provides the canonical, reusable presentation primitives used
across the whole product. Templates SHOULD NOT reinvent these patterns
inline. New patterns belong here.

Loaded with: ``{% load ui %}``.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterable

from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext, gettext_lazy as _
from django.views.generic.detail import BaseDetailView

from core.navigation import NAV_TREE

register = template.Library()


@register.simple_tag
def static_v(path):
    """Like ``{% static %}`` but appends the file's mtime as a ``?v=`` cache-buster.

    The project does not hash static filenames, so an edited JS / CSS asset would
    otherwise stay cached in the browser. Appending the modification time makes
    every change take effect on the next load. Falls back to the plain static URL
    if the file cannot be located.
    """
    import os

    from django.contrib.staticfiles import finders
    from django.templatetags.static import static as static_url

    url = static_url(path)
    try:
        found = finders.find(path)
        if found:
            url += ("&" if "?" in url else "?") + "v=" + str(int(os.path.getmtime(found)))
    except Exception:
        pass
    return url


# ───────────────────────── Module accents ──────────────────────────────────
#
# Editorial signal for each business module. Used by {% page_header %}
# to render a 4 px left accent bar plus a subtle tinted band so users
# get an immediate "where am I" cue on top of the calm neutral canvas.
#
# The values are validated identifiers; the actual colours live in CSS
# variables (--module-accent-* / --module-accent-*-soft) defined in
# templates/base.html so light + dark mode can each tune the hue.

MODULE_ACCENTS = {
    "risks", "compliance", "assets", "context",
    "reports", "accounts", "helpers", "dashboard",
    "trust-center",
}


# ───────────────────────── Illustrations ───────────────────────────────────
#
# Editorial line-art SVGs for empty states. The style is deliberate:
# stroke-only (no fill), 1.5 px stroke weight, currentColor for the
# base lines + var(--accent) for the one element that carries meaning.
# Recognisable but abstract: shields, folders, scrolls, seals, networks,
# calendars, buildings, magnifiers. They speak audit-grade tooling, not
# consumer mascots, and they inherit text colour so they work in both
# light and dark mode without overrides.

ILLUSTRATIONS = {
    "shield": """
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
            <path d="M50 12 L78 22 V46 C78 64 66 78 50 86 C34 78 22 64 22 46 V22 Z"
                  opacity=".25" fill="currentColor" stroke="none"/>
            <path d="M50 12 L78 22 V46 C78 64 66 78 50 86 C34 78 22 64 22 46 V22 Z"/>
            <path d="M40 50 L48 58 L62 42" stroke="var(--accent)" stroke-width="2"/>
        </svg>
    """,
    "folder-check": """
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
            <path d="M14 30 H38 L46 38 H86 V80 H14 Z"
                  opacity=".25" fill="currentColor" stroke="none"/>
            <path d="M14 30 H38 L46 38 H86 V80 H14 Z"/>
            <path d="M40 58 L48 66 L62 50" stroke="var(--accent)" stroke-width="2"/>
        </svg>
    """,
    "scroll": """
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
            <rect x="22" y="18" width="56" height="68" rx="4"
                  opacity=".25" fill="currentColor" stroke="none"/>
            <rect x="22" y="18" width="56" height="68" rx="4"/>
            <line x1="32" y1="34" x2="68" y2="34"/>
            <line x1="32" y1="46" x2="68" y2="46"/>
            <line x1="32" y1="58" x2="58" y2="58"/>
            <line x1="32" y1="70" x2="50" y2="70" stroke="var(--accent)" stroke-width="2"/>
        </svg>
    """,
    "seal": """
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
            <circle cx="50" cy="42" r="22"
                    opacity=".25" fill="currentColor" stroke="none"/>
            <circle cx="50" cy="42" r="22"/>
            <circle cx="50" cy="42" r="13" stroke="var(--accent)" stroke-width="2"/>
            <path d="M38 74 L32 92 L44 86 L50 92 L56 86 L68 92 L62 74"/>
        </svg>
    """,
    "network": """
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
            <line x1="50" y1="26" x2="50" y2="78"/>
            <line x1="50" y1="26" x2="22" y2="62"/>
            <line x1="50" y1="26" x2="78" y2="62"/>
            <line x1="22" y1="62" x2="78" y2="62" stroke="var(--accent)" stroke-width="2"/>
            <circle cx="50" cy="22" r="6" fill="currentColor" opacity=".15"/>
            <circle cx="50" cy="22" r="6"/>
            <circle cx="22" cy="62" r="6" fill="currentColor" opacity=".15"/>
            <circle cx="22" cy="62" r="6"/>
            <circle cx="78" cy="62" r="6" fill="currentColor" opacity=".15"/>
            <circle cx="78" cy="62" r="6"/>
            <circle cx="50" cy="82" r="6" fill="var(--accent)" opacity=".15"/>
            <circle cx="50" cy="82" r="6" stroke="var(--accent)" stroke-width="2"/>
        </svg>
    """,
    "calendar": """
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
            <rect x="18" y="22" width="64" height="62" rx="4"
                  opacity=".25" fill="currentColor" stroke="none"/>
            <rect x="18" y="22" width="64" height="62" rx="4"/>
            <line x1="18" y1="38" x2="82" y2="38"/>
            <line x1="32" y1="14" x2="32" y2="28"/>
            <line x1="68" y1="14" x2="68" y2="28"/>
            <circle cx="50" cy="60" r="7" fill="var(--accent)" opacity=".2"/>
            <circle cx="50" cy="60" r="7" stroke="var(--accent)" stroke-width="2"/>
        </svg>
    """,
    "building": """
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
            <path d="M22 32 L50 14 L78 32 V84 H22 Z"
                  opacity=".25" fill="currentColor" stroke="none"/>
            <path d="M22 32 L50 14 L78 32"/>
            <rect x="22" y="32" width="56" height="52"/>
            <rect x="34" y="44" width="8" height="10"/>
            <rect x="58" y="44" width="8" height="10"/>
            <rect x="34" y="60" width="8" height="10"/>
            <rect x="58" y="60" width="8" height="10"/>
            <rect x="44" y="70" width="12" height="14" stroke="var(--accent)" stroke-width="2"/>
        </svg>
    """,
    "search-chart": """
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
            <circle cx="42" cy="42" r="22"
                    opacity=".25" fill="currentColor" stroke="none"/>
            <circle cx="42" cy="42" r="22"/>
            <polyline points="30,52 38,42 46,46 56,32" stroke="var(--accent)" stroke-width="2"/>
            <line x1="58" y1="58" x2="76" y2="76"/>
        </svg>
    """,
}


@register.simple_tag
def illustration(name, *, size="6rem"):
    """Render an editorial line-art SVG by name.

    Usage::

        {% illustration "shield" %}
        {% illustration "scroll" size="8rem" %}

    Returns an empty string for unknown names (graceful degrade).
    """
    svg = ILLUSTRATIONS.get(name)
    if not svg:
        return ""
    return mark_safe(
        f'<span class="fw-illustration" style="--illustration-size:{size}">{svg}</span>'
    )


# ───────────────────────── Badge registry ──────────────────────────────────
#
# A semantic enum value (e.g. "approved", "high", "critical") is mapped to:
#   - variant: one of success | warning | danger | info | accent | secondary
#   - icon:    Bootstrap Icon name without the "bi-" prefix
#   - label:   user-facing localized text (overridable at call site)
#
# Callers that pass a `type=` argument get this mapping for free.
# Callers that pass explicit variant/icon/label override the registry.

BADGE_REGISTRY: dict[str, dict[str, tuple[str, str, object]]] = {
    "approval": {
        "approved": ("success", "check-circle", _("Approved")),
        "pending": ("warning", "clock", _("Pending approval")),
        "rejected": ("danger", "x-circle", _("Rejected")),
    },
    "severity": {
        "low": ("info", "info-circle", _("Low")),
        "medium": ("info", "circle", _("Medium")),
        "high": ("warning", "exclamation-triangle", _("High")),
        "critical": ("danger", "exclamation-octagon", _("Critical")),
    },
    "risk": {
        "negligible": ("secondary", "circle", _("Negligible")),
        "low": ("info", "circle", _("Low")),
        "moderate": ("info", "circle-fill", _("Moderate")),
        "high": ("warning", "exclamation-triangle", _("High")),
        "critical": ("danger", "exclamation-octagon", _("Critical")),
    },
    "status": {
        # Generic workflow statuses that show up across the app
        "draft": ("secondary", "pencil", _("Draft")),
        "new": ("secondary", "circle", _("New")),
        "planned": ("info", "calendar-check", _("Planned")),
        "in_progress": ("warning", "play-circle", _("In progress")),
        "in_preparation": ("info", "hourglass-split", _("In preparation")),
        "under_review": ("info", "eye", _("Under review")),
        "to_define": ("secondary", "three-dots", _("To define")),
        "active": ("success", "check-circle", _("Active")),
        "validated": ("success", "check-circle", _("Validated")),
        "approved": ("success", "check-circle", _("Approved")),
        "closed": ("success", "lock", _("Closed")),
        "held": ("success", "check-circle", _("Held")),
        "completed": ("success", "check-circle", _("Completed")),
        "rejected": ("danger", "x-circle", _("Rejected")),
        "cancelled": ("danger", "x-octagon", _("Cancelled")),
        "overdue": ("danger", "alarm", _("Overdue")),
        "archived": ("secondary", "archive", _("Archived")),
    },
}


def _resolve_badge(value: str, type_: str | None) -> tuple[str, str, object | None]:
    if not type_:
        return ("secondary", "circle", None)
    bucket = BADGE_REGISTRY.get(type_, {})
    return bucket.get(str(value), ("secondary", "circle", None))


# ───────────────────────── Tags ────────────────────────────────────────────


@register.inclusion_tag("components/badge.html")
def badge(value=None, *, type=None, variant=None, icon=None, label=None, classes=""):
    """Render a semantic status badge.

    Two calling styles:

    Registry: ``{% badge risk.priority type="severity" %}``
        Looks up (variant, icon, label) in BADGE_REGISTRY[type][value].

    Explicit: ``{% badge variant="success" icon="check" label=my_label %}``
        Use to bypass the registry. ``value`` is optional and ignored.

    Parameters can be mixed - explicit arguments always win over the
    registry lookup. ``label`` defaults to the registry label (translated)
    when omitted; pass ``label=value`` to fall back to the raw value.
    """
    reg_variant, reg_icon, reg_label = _resolve_badge(value, type)
    final_variant = variant or reg_variant
    final_icon = icon or reg_icon
    final_label = label if label is not None else (reg_label if reg_label is not None else value)
    return {
        "variant": final_variant,
        "icon": final_icon,
        "label": final_label,
        "classes": classes,
    }


@register.inclusion_tag("components/progress_bar.html")
def progress_bar(pct, *, scheme="progress", variant=None, title=None, count=None, total=None):
    """Render a standard progress bar (1rem tall, percentage inside, min 60px).

    pct      : percentage value (0-100); rounded for display and width.
    scheme   : colour scheme when ``variant`` is not given -
               "progress" (>=100 success, >=50 info, else warning) or
               "score" (>=80 success, >=50 warning, else danger).
    variant  : explicit Bootstrap colour (e.g. "info") to bypass the scheme.
    title    : tooltip on the track; if omitted and ``count``/``total`` are
               given, defaults to ``"count/total"``.
    Light bars (info / warning) get dark, semibold text for contrast.
    """
    try:
        value = float(pct) if pct is not None else 0
    except (TypeError, ValueError):
        value = 0
    if variant is None:
        if scheme == "score":
            variant = "success" if value >= 80 else "warning" if value >= 50 else "danger"
        else:
            variant = "success" if value >= 100 else "info" if value >= 50 else "warning"
    if title is None and count is not None and total is not None:
        title = f"{count}/{total}"
    return {
        "pct": round(value),
        "variant": variant,
        "text_dark": variant in ("info", "warning"),
        "title": title,
    }


@register.inclusion_tag("components/empty_state.html")
def empty_state(*, icon=None, illustration=None, title=None, message=None, cta_url=None, cta_label=None, colspan=None):
    """Render a standardized empty state.

    Use inside a ``<tbody>`` by setting ``colspan`` to the number of
    columns; otherwise render at block level.

    By default (no ``icon`` and no ``illustration``), only the title +
    message + optional CTA render - the brand-default plain variant.
    Pass ``icon="folder-check"`` to add a Bootstrap Icon, or
    ``illustration="shield"`` (any key in ``ILLUSTRATIONS``) to render
    the editorial line-art illustration - reserve those for empty states
    that benefit from extra character.
    """
    illustration_svg = None
    if illustration and illustration in ILLUSTRATIONS:
        illustration_svg = mark_safe(ILLUSTRATIONS[illustration])
    return {
        "icon": icon,
        "illustration_svg": illustration_svg,
        "title": title,
        "message": message,
        "cta_url": cta_url,
        "cta_label": cta_label,
        "colspan": colspan,
    }


@register.inclusion_tag("components/kpi_card.html")
def kpi_card(*, icon, value, label, variant="accent", trend=None, trend_label=None, href=None):
    """Render a KPI / stat card.

    ``variant`` selects the colored icon background: accent | success |
    warning | danger | info | secondary.

    ``trend`` is an optional numeric delta. ``trend_label`` describes
    what the delta is relative to (e.g. "vs last month").
    """
    trend_direction = None
    if trend is not None:
        try:
            t = float(trend)
            trend_direction = "up" if t > 0 else "down" if t < 0 else "flat"
        except (TypeError, ValueError):
            trend_direction = None
    return {
        "icon": icon,
        "value": value,
        "label": label,
        "variant": variant,
        "trend": trend,
        "trend_label": trend_label,
        "trend_direction": trend_direction,
        "href": href,
    }


@register.inclusion_tag("components/filter_chip.html", takes_context=True)
def filter_chip(context, *, label, param, value, count=None, icon=None, variant="accent"):
    """Render a single filter chip that toggles a query parameter.

    The chip is active when the current request has ``?<param>=<value>``.
    Clicking the chip toggles the param off (adds if absent, removes if
    present), preserving all other query parameters.
    """
    request = context.get("request")
    current = ""
    if request is not None:
        current = str(request.GET.get(param, ""))
    is_active = current == str(value)
    # Build the toggled URL by mutating only this param
    if request is not None:
        qs = request.GET.copy()
        if is_active:
            qs.pop(param, None)
        else:
            qs[param] = str(value)
        qs.pop("page", None)
        url = f"{request.path}?{qs.urlencode()}" if qs else request.path
    else:
        url = "#"
    return {
        "label": label,
        "url": url,
        "is_active": is_active,
        "count": count,
        "icon": icon,
        "variant": variant,
    }


@register.tag(name="page_header")
def do_page_header(parser, token):
    """Block tag that renders a standardized page header.

    Usage::

        {% page_header "Risk register" subtitle="ISO 27005" %}
          <a href="..." class="btn btn-primary">...</a>
        {% endpage_header %}

    The block content is injected into the right-hand action slot.
    """
    bits = token.split_contents()[1:]
    title_expr = None
    kwargs = {}
    for bit in bits:
        if "=" in bit:
            k, v = bit.split("=", 1)
            kwargs[k.strip()] = parser.compile_filter(v.strip())
        else:
            if title_expr is None:
                title_expr = parser.compile_filter(bit)
    nodelist = parser.parse(("endpage_header",))
    parser.delete_first_token()
    return PageHeaderNode(title_expr, kwargs, nodelist)


class PageHeaderNode(template.Node):
    def __init__(self, title_expr, kwargs, nodelist):
        self.title_expr = title_expr
        self.kwargs = kwargs
        self.nodelist = nodelist

    def render(self, context):
        title = self.title_expr.resolve(context) if self.title_expr else ""
        resolved_kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}
        actions_html = self.nodelist.render(context).strip()
        accent = resolved_kwargs.get("accent")
        if accent is not None:
            accent = str(accent)
            if accent not in MODULE_ACCENTS:
                accent = None
        # The eyebrow renders as a breadcrumb that mirrors the sidebar tree.
        # Preferred form: `nav="<list-url-name>"` resolves the menu ancestry
        # from core.navigation.NAV_TREE (section / group as non-clickable
        # crumbs, the leaf list as a link), then appends the parent crumb
        # (parent_label/parent_url) for nested entities and the item's
        # reference (or title) as the final, current crumb. On the list page
        # itself the leaf is the current crumb and nothing is appended.
        # Legacy form (eyebrow_url / breadcrumb) is kept as a fallback; with
        # neither, it falls back to the plain eyebrow.
        eyebrow = resolved_kwargs.get("eyebrow")
        eyebrow_url = resolved_kwargs.get("eyebrow_url")
        parent_label = resolved_kwargs.get("parent_label")
        parent_url = resolved_kwargs.get("parent_url")
        extra = resolved_kwargs.get("breadcrumb") or []
        nav = resolved_kwargs.get("nav")
        reference = resolved_kwargs.get("reference")
        crumbs = None
        if nav and nav in NAV_TREE:
            section, group, leaf_label = NAV_TREE[nav]
            request = context.get("request")
            try:
                list_url = reverse(nav)
            except NoReverseMatch:
                list_url = None
            on_list_page = bool(request and list_url and request.path == list_url)
            crumbs = []
            if section:
                crumbs.append({"label": gettext(section), "url": None})
            if group:
                # The assistant's group label is the configurable brand name
                # (ASSISTANT_NAME, default "Ask Cairn") so the breadcrumb matches
                # the renamed sidebar group.
                if nav.startswith("assistant:"):
                    group_label = context.get("ASSISTANT_NAME") or gettext(group)
                else:
                    group_label = gettext(group)
                crumbs.append({"label": group_label, "url": None})
            if on_list_page:
                crumbs.append({"label": gettext(leaf_label), "url": None})
            else:
                crumbs.append({"label": gettext(leaf_label), "url": list_url})
                if parent_label:
                    crumbs.append({"label": parent_label, "url": parent_url})
                # Self-nested entities (e.g. scopes) pass their ancestor chain
                # as `breadcrumb`, inserted between the list and the current item.
                crumbs.extend(extra)
                final = reference or title
                if final:
                    crumbs.append({"label": final, "url": None})
        elif eyebrow_url or parent_label or extra:
            crumbs = []
            if eyebrow:
                crumbs.append({"label": eyebrow, "url": eyebrow_url})
            if parent_label:
                crumbs.append({"label": parent_label, "url": parent_url})
            crumbs.extend(extra)
        # On detail pages, surface who last touched the object and when, shown in
        # the header just before the action buttons. The "who" comes from the
        # latest simple-history record (history_user); the "when" from the
        # object's updated_at (falling back to the record's history_date).
        # Gated on BaseDetailView so lists, forms and other pages never show it.
        modified_by = None
        modified_at = None
        obj = context.get("object")
        if obj is not None and isinstance(context.get("view"), BaseDetailView) and hasattr(obj, "history"):
            try:
                last = obj.history.first()
            except Exception:
                last = None
            if last is not None:
                modified_by = getattr(last, "history_user", None)
                modified_at = getattr(obj, "updated_at", None) or getattr(last, "history_date", None)
        with context.push(
            title=title,
            subtitle=resolved_kwargs.get("subtitle"),
            reference=resolved_kwargs.get("reference"),
            icon=resolved_kwargs.get("icon"),
            logo=resolved_kwargs.get("logo"),
            accent=accent,
            eyebrow=eyebrow,
            crumbs=crumbs,
            modified_by=modified_by,
            modified_at=modified_at,
            # When set, the bar renders in its compact (collapsed) form from the
            # start and stays there - used by full-height pages (e.g. the
            # dependency graph) that do not scroll, to reclaim vertical space.
            compact=bool(resolved_kwargs.get("compact")),
            actions_html=mark_safe(actions_html) if actions_html else "",
        ):
            tpl = context.template.engine.get_template("components/page_header.html")
            return tpl.render(context)


@register.tag(name="sidebar_card")
def do_sidebar_card(parser, token):
    """Block tag that renders a sidebar card for 2-column detail pages.

    Usage::

        {% sidebar_card "Status" icon="info-circle" %}
          ...sidebar body...
        {% endsidebar_card %}
    """
    bits = token.split_contents()[1:]
    title_expr = None
    kwargs = {}
    for bit in bits:
        if "=" in bit:
            k, v = bit.split("=", 1)
            kwargs[k.strip()] = parser.compile_filter(v.strip())
        else:
            if title_expr is None:
                title_expr = parser.compile_filter(bit)
    nodelist = parser.parse(("endsidebar_card",))
    parser.delete_first_token()
    return SidebarCardNode(title_expr, kwargs, nodelist)


class SidebarCardNode(template.Node):
    def __init__(self, title_expr, kwargs, nodelist):
        self.title_expr = title_expr
        self.kwargs = kwargs
        self.nodelist = nodelist

    def render(self, context):
        title = self.title_expr.resolve(context) if self.title_expr else ""
        resolved_kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}
        body_html = self.nodelist.render(context)
        with context.push(
            title=title,
            icon=resolved_kwargs.get("icon"),
            sticky=resolved_kwargs.get("sticky", True),
            body_html=mark_safe(body_html),
        ):
            tpl = context.template.engine.get_template("components/sidebar_card.html")
            return tpl.render(context)


@register.inclusion_tag("components/confirm_delete.html")
def confirm_delete(*, url, name=None, label=None, classes="btn btn-sm btn-outline-danger", icon="trash"):
    """Render a delete button + confirmation modal pair.

    Usage::

        {% confirm_delete url=risk.delete_url name=risk.reference label=_("Delete") %}

    The button opens an inline modal that requires the user to type the
    object name (or just click confirm if ``name`` is empty). Submission
    is HTMX-driven (DELETE verb) so the row can be swapped out.
    """
    modal_id = f"confirm-del-{uuid.uuid4().hex[:8]}"
    return {
        "url": url,
        "name": name,
        "label": label or _("Delete"),
        "classes": classes,
        "icon": icon,
        "modal_id": modal_id,
    }


@register.inclusion_tag("components/bulk_actions_bar.html")
def bulk_actions_bar(*, target_id, actions, label=None):
    """Render a floating bulk-actions bar.

    ``target_id`` is the id of the container holding row checkboxes
    (the bar listens for change events on it). ``actions`` is an
    iterable of dicts with: ``label``, ``url``, ``variant`` (one of
    primary | danger | success | secondary), ``icon``, ``confirm``
    (optional confirmation message).
    """
    return {
        "target_id": target_id,
        "actions": actions,
        "label": label or _("selected"),
    }


@dataclass(frozen=True)
class Step:
    """Lightweight step descriptor for the {% stepper %} tag.

    ``state`` is one of: done | current | next | future.
    """

    value: str
    label: str
    state: str


@register.inclusion_tag("components/stepper.html")
def stepper(
    *,
    steps,
    transition_url=None,
    next_status=None,
    cancelled=None,
    can_cancel=False,
    can_refuse=False,
    refusal=None,
    transition_modal_callback=None,
    entity_id=None,
):
    """Render the canonical workflow stepper.

    Required:

    * ``steps``: iterable of objects (Step dataclass or dict) with
      ``value``, ``label``, ``state`` keys. The ``state`` decides the
      visual treatment.
    * ``transition_url``: URL to POST status transitions to.

    Optional branch state (archived / cancelled) rendered on the same
    line as the main flow, detached by a gap with no connector:

    * ``cancelled``: a step descriptor for the branch state.
    * ``can_cancel``: whether the user may trigger the transition.
    * ``transition_modal_callback`` + ``entity_id``: name and argument
      of the JS callback opening the comment modal.

    Optional refusal:

    * ``can_refuse`` + ``refusal``: dict with ``status`` and ``label``.
    """
    container_id = f"stepper-{uuid.uuid4().hex[:8]}"
    return {
        "container_id": container_id,
        "steps": list(steps) if steps is not None else [],
        "transition_url": transition_url,
        "next_status": next_status,
        "cancelled": cancelled,
        "can_cancel": can_cancel,
        "can_refuse": can_refuse,
        "refusal": refusal,
        "transition_modal_callback": transition_modal_callback,
        "entity_id": entity_id,
    }


def build_steps(definitions: Iterable[tuple[str, object]], current_value: str, terminal_values: Iterable[str] = ()) -> list[Step]:
    """Helper for views: turn ``[(value, label), ...]`` into ``[Step, ...]``.

    States are inferred from the position of ``current_value`` in the
    sequence. Values in ``terminal_values`` (other than the one matching
    ``current_value``) are skipped from automatic "next" promotion so
    that closed/cancelled pills don't accidentally get a transition
    button.
    """
    defs = list(definitions)
    terminal = set(terminal_values)
    try:
        current_index = next(i for i, (v, _label) in enumerate(defs) if v == current_value)
    except StopIteration:
        current_index = -1
    result: list[Step] = []
    next_promoted = False
    for i, (value, label) in enumerate(defs):
        if i < current_index:
            state = "done"
        elif i == current_index:
            state = "current"
        elif not next_promoted and value not in terminal:
            state = "next"
            next_promoted = True
        else:
            state = "future"
        result.append(Step(value=value, label=str(label), state=state))
    return result

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Shared UI template tags for Cairn.

This module provides the canonical, reusable presentation primitives used
across the whole product. Templates SHOULD NOT reinvent these patterns
inline. New patterns belong here.

Loaded with: ``{% load ui %}``.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Iterable

from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext, gettext_lazy as _, pgettext_lazy
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
# static/css/cairn/00-tokens.css so light + dark mode can each tune the hue.

MODULE_ACCENTS = {
    "risks", "compliance", "assets", "context",
    "incidents", "reports", "accounts", "helpers", "dashboard",
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
    # One ordinal scale for priority, criticality, severity and impact, so a
    # "High" reads the same whatever field carries it.
    "level": {
        "negligible": ("secondary", "circle", _("Negligible")),
        "low": ("secondary", "arrow-down", _("Low")),
        "medium": ("info", "dash", _("Medium")),
        "high": ("warning", "arrow-up", _("High")),
        "critical": ("danger", "exclamation-octagon", _("Critical")),
    },
    "compliance": {
        "compliant": ("success", "check-circle", _("Compliant")),
        "strength": ("success", "star", pgettext_lazy("compliance", "Strength")),
        "partially_compliant": ("warning", "circle-half", _("Partially compliant")),
        "observation": ("warning", "eye", pgettext_lazy("compliance", "Observation")),
        "improvement_opportunity": ("warning", "lightbulb", _("Improvement opportunity")),
        "minor_non_conformity": ("danger", "exclamation-circle", _("Minor non-conformity")),
        "major_non_conformity": ("danger", "exclamation-octagon", _("Major non-conformity")),
        "non_compliant": ("danger", "x-circle", _("Non-compliant")),
        "evaluated": ("info", "calendar-check", _("Evaluation planned")),
        "not_assessed": ("secondary", "circle", _("Not assessed")),
        "not_applicable": ("secondary", "slash-circle", _("Not applicable")),
    },
    # Risk treatment posture: an undecided risk is the one that needs action.
    "treatment_decision": {
        "not_decided": ("danger", "question-circle", _("Not decided")),
        "accept": ("warning", "check2", _("Accept")),
        "mitigate": ("accent", "tools", _("Mitigate")),
        "transfer": ("info", "arrow-left-right", _("Transfer")),
        "avoid": ("success", "slash-circle", _("Avoid")),
    },
    # EBIOS RM 1-4 scales (gravity, likelihood, threat level, risk level).
    "ebios_scale": {
        "1": ("info", "circle", None),
        "2": ("info", "circle-fill", None),
        "3": ("warning", "exclamation-triangle", None),
        "4": ("danger", "exclamation-octagon", None),
    },
    "threat_zone": {
        "control": ("success", "shield-check", _("Control zone")),
        "monitoring": ("warning", "eye", _("Monitoring zone")),
        "danger": ("danger", "exclamation-octagon", _("Danger zone")),
    },
    # Categories, not statuses: they keep the identity colour (semantic
    # colours are reserved for statuses).
    "methodology": {
        "iso27005": ("accent", "diagram-2", _("ISO 27005")),
        "ebios_rm": ("accent", "diagram-2", _("EBIOS RM")),
    },
    "dic": {
        "confidentiality": ("accent", "lock", _("Confidentiality")),
        "integrity": ("accent", "check2-square", _("Integrity")),
        "availability": ("accent", "lightning", _("Availability")),
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
        "inactive": ("secondary", "pause-circle", _("Inactive")),
        "not_started": ("secondary", "circle", _("Not started")),
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
    reg_variant, _reg_icon, reg_label = _resolve_badge(value, type)
    final_variant = variant or reg_variant
    # Every badge is a dot pill; an icon replaces the dot only when the caller
    # asks for one, so the same value reads the same wherever it appears.
    final_icon = icon or None
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


# ═════════════════════════ Layout & content primitives ═════════════════════
#
# The building blocks of every detail page and content card. Each one owns
# its markup and CSS (static/css/cairn/10-framework.css) so templates compose
# them instead of re-typing card / dl / badge markup. The catalogue, with
# usage and anatomy, is docs/sdk/ui-components.md; /styleguide/ renders them.

_DASH_HTML = '<span class="ui-dash" aria-label="{label}">-</span>'


def _dash():
    return mark_safe(_DASH_HTML.format(label=gettext("Not set")))


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if hasattr(value, "exists") and callable(value.exists):  # a QuerySet / manager
        try:
            return not value.exists()
        except TypeError:
            return False
    try:
        return len(value) == 0
    except TypeError:
        return False


@register.simple_tag
def dash():
    """The single "no value" marker: ``{% dash %}``.

    Always use it (or ``|or_dash``) for an empty field, never a bare "-",
    "N/A" or "None", so empty values read the same on every page and are
    announced as "Not set" to screen readers.
    """
    return _dash()


@register.filter
def or_dash(value):
    """``{{ obj.start_date|or_dash }}``: the value, or the dash when empty."""
    if _is_blank(value):
        return _dash()
    return value


# ───────────────────────── Slots ───────────────────────────────────────────


class SlotNode(template.Node):
    """A named region of a container tag: ``{% slot rail %}...{% endslot %}``.

    Renders nothing in place. The enclosing container (``detail_layout``,
    ``section_card``) collects its top-level slots and renders each one in
    the right spot of its own markup.
    """

    def __init__(self, name, nodelist):
        self.name = name
        self.nodelist = nodelist

    def render(self, context):
        return ""


@register.tag(name="slot")
def do_slot(parser, token):
    bits = token.split_contents()
    if len(bits) != 2:
        raise template.TemplateSyntaxError("{% slot %} takes exactly one name, e.g. {% slot actions %}")
    nodelist = parser.parse(("endslot",))
    parser.delete_first_token()
    return SlotNode(bits[1], nodelist)


def _parse_tag(parser, token, end=None):
    """Split a tag into compiled positional args, kwargs and (optionally) its body."""
    args, kwargs = [], {}
    for bit in token.split_contents()[1:]:
        if "=" in bit and not bit.startswith(("'", '"', "_(")):
            k, v = bit.split("=", 1)
            kwargs[k.strip()] = parser.compile_filter(v.strip())
        else:
            args.append(parser.compile_filter(bit))
    nodelist = None
    if end:
        nodelist = parser.parse((end,))
        parser.delete_first_token()
    return args, kwargs, nodelist


def _render_with_slots(nodelist, context):
    """Render a body, returning (main_html, {slot_name: html})."""
    slots = {}
    parts = []
    for node in nodelist:
        if isinstance(node, SlotNode):
            slots[node.name] = node.nodelist.render(context).strip()
        else:
            parts.append(node.render_annotated(context))
    return "".join(parts).strip(), slots


class _ComponentNode(template.Node):
    """Base for block components: resolve args, render body + slots, render a template."""

    template_name = ""

    def __init__(self, args, kwargs, nodelist):
        self.args = args
        self.kwargs = kwargs
        self.nodelist = nodelist

    def get_context(self, args, kwargs, body, slots):  # pragma: no cover - abstract
        raise NotImplementedError

    def render(self, context):
        args = [a.resolve(context) for a in self.args]
        kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}
        body, slots = _render_with_slots(self.nodelist, context) if self.nodelist is not None else ("", {})
        values = self.get_context(args, kwargs, body, slots)
        if values is None:
            return ""
        with context.push(**values):
            return context.template.engine.get_template(self.template_name).render(context)


# ───────────────────────── Detail layout ───────────────────────────────────


class DetailLayoutNode(_ComponentNode):
    template_name = "components/detail_layout.html"

    def get_context(self, args, kwargs, body, slots):
        return {
            "main_html": mark_safe(body),
            "rail_html": mark_safe(slots.get("rail", "")),
            "rail_label": kwargs.get("rail_label") or _("Key figures"),
        }


@register.tag(name="detail_layout")
def do_detail_layout(parser, token):
    """The detail page body: main column plus an optional key-figures rail.

    Usage::

        {% detail_layout %}
          {% slot rail %}
            {% kpi_tile _("Expiry date") certificate.expiry_date icon="calendar-check" tone="success" %}
          {% endslot %}
          {% section_card _("Description") icon="text-left" %}...{% endsection_card %}
        {% enddetail_layout %}

    Below 1800 px the rail sits above the content as a wrapping row of
    tiles; from 1800 px it becomes a sticky right-hand column.
    """
    args, kwargs, nodelist = _parse_tag(parser, token, "enddetail_layout")
    return DetailLayoutNode(args, kwargs, nodelist)


# ───────────────────────── KPI tile ────────────────────────────────────────

KPI_TONES = ("accent", "success", "warning", "danger", "info", "neutral")


@register.inclusion_tag("components/kpi_tile.html")
def kpi_tile(label, value=None, *, icon=None, tone="accent", href=None, suffix=None, size=None):
    """One key figure, for a list rail or a detail rail.

    ``tone`` is one of accent | success | warning | danger | info | neutral.
    ``size`` is "lg" for a number and "sm" for a word or a date; it is
    inferred from the value when omitted. An empty value renders the dash.
    """
    if tone not in KPI_TONES:
        tone = "neutral" if tone in ("secondary", "muted") else "accent"
    if size not in ("lg", "sm"):
        size = "lg" if isinstance(value, (int, float)) and not isinstance(value, bool) else "sm"
    return {
        "label": label,
        "value": _dash() if _is_blank(value) else value,
        "icon": icon,
        "tone": tone,
        "href": href,
        "suffix": suffix,
        "size": size,
    }


# ───────────────────────── Section card ────────────────────────────────────


class SectionCardNode(_ComponentNode):
    template_name = "components/section_card.html"

    def get_context(self, args, kwargs, body, slots):
        if not body and kwargs.get("hide_empty"):
            return None
        title = args[0] if args else kwargs.get("title")
        return {
            "title": title,
            "icon": kwargs.get("icon"),
            "count": kwargs.get("count"),
            "card_id": kwargs.get("id"),
            "collapsible": bool(kwargs.get("collapsible")),
            "open": kwargs.get("open", True),
            "flush": bool(kwargs.get("flush")),
            "body_html": mark_safe(body),
            "actions_html": mark_safe(slots.get("actions", "")),
            "footer_html": mark_safe(slots.get("footer", "")),
        }


@register.tag(name="section_card")
def do_section_card(parser, token):
    """A titled content card: the unit every detail page is built from.

    Usage::

        {% section_card _("Linked risks") icon="exclamation-triangle" count=risks|length %}
          {% slot actions %}<button class="btn btn-sm btn-secondary">...</button>{% endslot %}
          ...body...
        {% endsection_card %}

    Options: ``count`` (a pill after the title), ``collapsible=True`` with
    ``open=False`` (a native ``<details>``), ``flush=True`` (no body padding,
    for a table that runs edge to edge), ``hide_empty=True`` (render nothing
    when the body is empty), ``id``. Slots: ``actions`` (right of the
    title), ``footer``.
    """
    args, kwargs, nodelist = _parse_tag(parser, token, "endsection_card")
    return SectionCardNode(args, kwargs, nodelist)


@register.inclusion_tag("components/subhead.html")
def subhead(label, *, icon=None):
    """A divider title inside a card: ``{% subhead _("Certified scope") icon="diagram-3" %}``."""
    return {"label": label, "icon": icon}


# ───────────────────────── Overview rows ───────────────────────────────────


class OverviewNode(_ComponentNode):
    template_name = "components/overview.html"

    def get_context(self, args, kwargs, body, slots):
        if not body:
            return None
        return {"body_html": mark_safe(body)}


@register.tag(name="overview")
def do_overview(parser, token):
    """The icon-led summary rows at the top of a detail page.

    Usage::

        {% overview %}
          {% ov_row "journal-bookmark" _("Framework") %}<a href="...">{{ framework }}</a>{% endov_row %}
          {% ov_row "award" _("Certification body") %}{{ certificate.issuer }}{% endov_row %}
        {% endoverview %}

    A row whose body renders empty is dropped, so optional facts need no
    surrounding ``{% if %}``.
    """
    args, kwargs, nodelist = _parse_tag(parser, token, "endoverview")
    return OverviewNode(args, kwargs, nodelist)


class OvRowNode(_ComponentNode):
    template_name = "components/ov_row.html"

    def get_context(self, args, kwargs, body, slots):
        if not body:
            return None
        return {
            "icon": args[0] if args else kwargs.get("icon"),
            "label": args[1] if len(args) > 1 else kwargs.get("label"),
            "lead": bool(kwargs.get("lead")),
            "rich": bool(kwargs.get("rich")),
            "body_html": mark_safe(body),
        }


@register.tag(name="ov_row")
def do_ov_row(parser, token):
    """One overview row: ``{% ov_row icon label lead=False rich=False %}value{% endov_row %}``.

    ``label`` is not displayed (the icon stands for it) but names the row
    for assistive technology. ``lead`` enlarges the row (the description);
    ``rich`` styles a rich-text value.
    """
    args, kwargs, nodelist = _parse_tag(parser, token, "endov_row")
    return OvRowNode(args, kwargs, nodelist)


# ───────────────────────── Metadata list ───────────────────────────────────


class MetaListNode(_ComponentNode):
    template_name = "components/meta_list.html"

    def get_context(self, args, kwargs, body, slots):
        if not body:
            return None
        cols = kwargs.get("cols")
        return {"body_html": mark_safe(body), "cols": cols if cols in (2, 3, "2", "3") else None}


@register.tag(name="meta_list")
def do_meta_list(parser, token):
    """A label / value list (``<dl>``): ``{% meta_list cols=2 %}...{% endmeta_list %}``."""
    args, kwargs, nodelist = _parse_tag(parser, token, "endmeta_list")
    return MetaListNode(args, kwargs, nodelist)


class MetaItemNode(_ComponentNode):
    template_name = "components/meta_item.html"

    def get_context(self, args, kwargs, body, slots):
        label = args[0] if args else kwargs.get("label")
        if self.nodelist is None:
            value = args[1] if len(args) > 1 else kwargs.get("value")
            html = _dash() if _is_blank(value) else value
        else:
            html = mark_safe(body) if body else _dash()
        if kwargs.get("hide_empty") and (self.nodelist is not None and not body):
            return None
        return {"label": label, "value_html": html, "wide": bool(kwargs.get("wide"))}


@register.tag(name="meta_item")
def do_meta_item(parser, token):
    """One label / value pair of a ``meta_list``.

    Two forms::

        {% meta_item _("Start date") plan.start_date %}            {# value inline #}
        {% meta_item _("Owner") %}{% user_badge plan.owner %}{% endmeta_item %}

    An empty value renders the dash. ``wide=True`` spans every column of a
    multi-column list; ``hide_empty=True`` drops an empty block item.
    """
    bits = token.split_contents()
    positional = [b for b in bits[1:] if not ("=" in b and not b.startswith(("'", '"', "_(")))]
    end = None if len(positional) >= 2 else "endmeta_item"
    args, kwargs, nodelist = _parse_tag(parser, token, end)
    return MetaItemNode(args, kwargs, nodelist)


@register.inclusion_tag("components/record_card.html", takes_context=True)
def record_card(context, obj):
    """The traceability card closing every detail page.

    Reference, version, author and the creation / last-change dates of a
    ``BaseModel``: the audit metadata, always in the same place and order.
    """
    return {"obj": obj, "request": context.get("request")}


# ───────────────────────── References & tags ───────────────────────────────


@register.inclusion_tag("components/ref_link.html")
def ref_link(obj, *, url=None, preview_url=None, label=None, reference=None):
    """A linked element: its reference pill, then its name as a link.

    ``url`` navigates; ``preview_url`` opens the element in the drawer
    instead (HTMX). ``label`` defaults to ``obj.name`` then ``str(obj)``.
    """
    if label is None:
        label = getattr(obj, "name", None) or str(obj)
    if reference is None:
        reference = getattr(obj, "reference", "")
    return {"reference": reference, "label": label, "url": url, "preview_url": preview_url}


_HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def tag_colors(color: str | None) -> tuple[str, str]:
    """Return a safe (background, foreground) pair for a tag colour.

    Only a ``#rgb`` / ``#rrggbb`` value is ever written into a style
    attribute (anything else falls back to the neutral token), and the
    label colour is chosen by relative luminance so a pale tag keeps a
    legible, AA-contrasted label.
    """
    if not color or not _HEX_COLOR.match(color):
        return "var(--surface-subtle)", "var(--text-secondary)"
    hexv = color[1:]
    if len(hexv) == 3:
        hexv = "".join(c * 2 for c in hexv)
    r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    lum = 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
    # Contrast against white vs. near-black (#161312); pick the stronger one.
    on_white = 1.05 / (lum + 0.05)
    on_dark = (lum + 0.05) / (0.0067 + 0.05)
    return color, ("#ffffff" if on_white >= on_dark else "#161312")


@register.inclusion_tag("components/tag_list.html")
def tag_list(tags, *, dash=False):
    """The tags of an element as coloured pills: ``{% tag_list obj.tags.all %}``.

    ``dash=True`` renders the dash when there is no tag (use it in a
    ``meta_item``); otherwise an empty list renders nothing.
    """
    items = []
    for tag in tags or []:
        bg, fg = tag_colors(getattr(tag, "color", None))
        items.append({"name": getattr(tag, "name", str(tag)), "bg": bg, "fg": fg})
    return {"items": items, "show_dash": dash and not items, "dash_html": _dash()}


# ───────────────────────── Choice badge ────────────────────────────────────

# Field name -> registry type, so {% choice_badge obj "priority" %} needs no type=.
CHOICE_BADGE_TYPES = {
    "priority": "level",
    "criticality": "level",
    "severity": "level",
    "impact_level": "level",
    "compliance_status": "compliance",
    "treatment_decision": "treatment_decision",
    "threat_zone": "threat_zone",
    "methodology": "methodology",
    "dic_criterion": "dic",
}


@register.inclusion_tag("components/badge.html")
def choice_badge(obj, field, *, type=None, icon=None, classes=""):
    """The badge of a choice field, labelled with its display value.

    ``{% choice_badge plan "priority" %}`` reads ``plan.priority`` for the
    tone (through ``BADGE_REGISTRY``) and ``plan.get_priority_display()``
    for the label, so the label is always the translated choice label and
    the colour the registry's, never a per-template ``{% if %}`` chain.
    """
    value = getattr(obj, field, None)
    display = getattr(obj, f"get_{field}_display", None)
    label = display() if callable(display) else value
    if _is_blank(value):
        return {"variant": "", "icon": None, "label": "", "classes": classes, "empty": True, "dash_html": _dash()}
    reg_variant, reg_icon, _reg_label = _resolve_badge(value, type or CHOICE_BADGE_TYPES.get(field))
    return {"variant": reg_variant, "icon": icon if icon is not None else None, "label": label, "classes": classes}


# ───────────────────────── Navigation helpers ──────────────────────────────


@register.simple_tag(takes_context=True)
def back_url(context, default="/"):
    """The page the user came from, for a Cancel / Back link.

    The ``Referer`` only when it points at this host (anything else is
    attacker-controllable and would turn the link into an open redirect),
    else ``default``. Usage: ``<a href="{% back_url list_url %}">``.
    """
    from django.utils.http import url_has_allowed_host_and_scheme

    request = context.get("request")
    if request is None:
        return default
    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return referer
    return default


@register.filter
def badge_variant(value, type_):
    """The registry tone of a value, e.g. for a KPI tile: ``{{ plan.priority|badge_variant:"level" }}``.

    Returns a ``kpi_tile`` tone (secondary maps to neutral).
    """
    variant = _resolve_badge(value, type_)[0]
    return {"secondary": "neutral", "dark": "neutral"}.get(variant, variant)

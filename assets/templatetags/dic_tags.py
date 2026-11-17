# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django import template
from django.utils.html import format_html

from core.templatetags.ui import BADGE_REGISTRY, _dash

register = template.Library()

# DIC level (0-4) -> key of the shared ordinal "level" scale, so a CIA level
# reads with the same tone as a priority or a criticality of the same rank.
DIC_LEVEL_KEYS = {
    0: "negligible",
    1: "low",
    2: "medium",
    3: "high",
    4: "critical",
}


@register.filter
def dic_badge(value):
    """Render a DIC level as the framework's ``.badge-dot`` pill.

    The pill shows the numeric level; its tone and its (translated) label come
    from the ``level`` scale of ``BADGE_REGISTRY``. The label is the tooltip
    and is also announced to screen readers. An empty value renders the dash.
    """
    try:
        level = int(value)
    except (TypeError, ValueError):
        return _dash()
    variant, _icon, label = BADGE_REGISTRY["level"].get(
        DIC_LEVEL_KEYS.get(level, ""), ("secondary", "circle", "?")
    )
    return format_html(
        '<span class="badge-dot {}" title="{}">{}<span class="visually-hidden"> {}</span></span>',
        variant, label, level, label,
    )


@register.filter
def dic_level(value):
    """Render a DIC level with its word, for a place that has room for it.

    A scale shows its words, not only its number : "3" tells nothing to who
    does not know the scale, "High" does. The compact numeric pill
    (``dic_badge``) stays for a table cell holding the three levels. A level
    that is not set reads "Not assessed" : it is a state of the asset, not a
    missing value.
    """
    from django.utils.translation import gettext as _

    try:
        level = int(value)
    except (TypeError, ValueError):
        return format_html('<span class="badge-dot secondary">{}</span>', _("Not assessed"))
    variant, _icon, label = BADGE_REGISTRY["level"].get(
        DIC_LEVEL_KEYS.get(level, ""), ("secondary", "circle", "?")
    )
    return format_html('<span class="badge-dot {}">{}</span>', variant, label)

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django import template
from django.utils.safestring import mark_safe

from core.colors import fill_under_white, ink_on_dark, ink_on_light
from trust_center.sanitizers import (
    clean_html,
    clean_svg,
    logo_href,
    logo_html,
)

register = template.Library()


@register.filter(name="tc_logo")
def tc_logo(value):
    """Render a logo (data-URI image or inline SVG) safely as HTML."""
    return mark_safe(logo_html(value))  # noqa: S308 - sanitized by logo_html


@register.filter(name="tc_logo_href")
def tc_logo_href(value):
    """Return a logo as a safe href/src value (data-URI or URL), else empty."""
    return logo_href(value)


@register.filter(name="safe_svg")
def safe_svg(markup):
    """Sanitize raw SVG markup and mark it safe for inline rendering.

    Use ONLY on the public Trust Center, where logos come from internal models
    and must not carry active content. Returns an empty string for non-SVG or
    unsafe input.
    """
    return mark_safe(clean_svg(markup or ""))  # noqa: S308 - sanitized by clean_svg


@register.filter(name="safe_html")
def safe_html(markup):
    """Sanitize admin-authored rich text for safe public rendering."""
    return mark_safe(clean_html(markup or ""))  # noqa: S308 - sanitized by clean_html


# The accent the Trust Center falls back to when none is set : the Cairn navy.
DEFAULT_ACCENT = "#1E3A8A"


@register.filter(name="accent_ink")
def accent_ink(colour, theme="light"):
    """The Trust Center accent as *text* on the given theme (``light`` / ``dark``).

    The administrator picks any colour; links, icons and figures drawn in it
    must still read on the page (WCAG 1.4.3). Hue and saturation are kept, the
    lightness goes only as far as 4.5:1 asks.
    """
    colour = colour or DEFAULT_ACCENT
    return ink_on_dark(colour) if theme == "dark" else ink_on_light(colour)


@register.filter(name="accent_fill")
def accent_fill(colour):
    """The accent as the hero's background : deepened, if need be, until its
    white text reads on it."""
    return fill_under_white(colour or DEFAULT_ACCENT)

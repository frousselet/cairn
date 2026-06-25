from django import template
from django.utils.safestring import mark_safe

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

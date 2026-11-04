# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Template tags of module 8 (controls)."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def controls_rich(value):
    """A control's rich-text description, sanitized at render time.

    The description of a control created from a requirement starts as the
    requirement's own rich text (RG-CTL-05), so it is never trusted as is.
    """
    from trust_center.sanitizers import clean_html

    return mark_safe(clean_html(value or ""))  # noqa: S308 - sanitized by clean_html

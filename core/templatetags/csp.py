# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""``{% csp_nonce %}`` : the nonce an inline script needs to run (core/csp.py).

Loaded as a builtin (see ``TEMPLATES`` in the settings), so every template has
it without a ``{% load %}``, including the ones rendered with a context of
their own : form widgets, inclusion tags, fragments rendered to a string.
"""

from django import template

from core.csp import current_nonce

register = template.Library()


@register.simple_tag
def csp_nonce():
    return current_nonce()

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django import template
from django.utils.translation import get_language

from helpers.models import HelpContent

register = template.Library()


def help_for(key, language):
    """The help of ``key`` in ``language``, falling back to its base language, then to English."""
    language = language or "en"
    wanted = [language, language[:2], "en"]
    found = {row.language: row for row in HelpContent.objects.filter(key=key, language__in=wanted)}
    return next((found[code] for code in wanted if code in found), None)


@register.inclusion_tag("includes/help_modal.html", takes_context=True)
def help_modal(context, key):
    """The help of a page : what the page is for, in plain words.

    Shown open until the reader hides it; a hidden help leaves a *Help on this
    page* button in its place, so what was closed on the first day can be read
    again on the tenth. The choice is kept per reader
    (``User.dismissed_helpers``).
    """
    content = help_for(key, get_language())

    dismissed = False
    request = context.get("request")
    if request and hasattr(request, "user") and request.user.is_authenticated:
        dismissed_helpers = getattr(request.user, "dismissed_helpers", None)
        if isinstance(dismissed_helpers, list) and key in dismissed_helpers:
            dismissed = True

    return {
        "help_content": content,
        "modal_id": key.replace(".", "-"),
        "helper_key": key,
        "dismissed": dismissed,
    }

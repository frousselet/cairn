# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Template tags of module 7 (documents)."""

from django import template

register = template.Library()


def pending_acknowledgements(user):
    """The rows ``user`` still has to acknowledge : pending, in a running campaign.

    Scope-independent on purpose : a user always sees their own requests
    (RG-DOC-22), whatever perimeter their groups allow.
    """
    from documents.constants import CAMPAIGN_RUNNING, AcknowledgementStatus
    from documents.models import PolicyAcknowledgement

    return PolicyAcknowledgement.objects.filter(
        user=user,
        status=AcknowledgementStatus.PENDING,
        campaign__workflow_state=CAMPAIGN_RUNNING,
    )


@register.simple_tag(takes_context=True)
def pending_acknowledgement_count(context):
    """``{% pending_acknowledgement_count as n %}`` : the badge of the user menu."""
    request = context.get("request")
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return 0
    return pending_acknowledgements(user).count()


@register.filter
def clean_rich(value):
    """A version's rich text, sanitized again at render time (README §9.3)."""
    from django.utils.safestring import mark_safe

    from trust_center.sanitizers import clean_html

    return mark_safe(clean_html(value or ""))  # noqa: S308 - sanitized by clean_html

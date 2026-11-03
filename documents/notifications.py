# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Notifications of module 7 (README §7).

Same contract as ``accounts.notifications`` : one in-app row per recipient,
rendered in the recipient's language, created in the surrounding transaction,
email + WebSocket delivery scheduled on commit (a rolled-back transition sends
nothing). No new notification model.
"""

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from accounts.constants import NotificationType
from accounts.models import Notification


def _send(recipients, notification_type, target, url, render, actor=None):
    """Create one notification per active, distinct recipient; ``render()`` -> (title, message)."""
    created, seen = [], set()
    for recipient in recipients:
        if recipient is None or not recipient.is_active or recipient.pk in seen:
            continue
        if actor is not None and recipient.pk == actor.pk:
            continue
        seen.add(recipient.pk)
        with translation.override(recipient.language or settings.LANGUAGE_CODE):
            title, message = render()
        created.append(Notification.objects.create(
            recipient=recipient, actor=actor, notification_type=notification_type,
            title=title, message=message, target=target, target_url=url,
        ))
    if created:
        from accounts.notifications import _deliver

        transaction.on_commit(lambda: _deliver(created))
    return created


def notify_acknowledgement_requested(campaign, users, actor=None):
    version = campaign.policy_version
    url = reverse("documents:acknowledge-list")

    def render():
        return (
            _("To acknowledge : %(title)s") % {"title": version.policy.title},
            _("Please read and acknowledge %(title)s version %(label)s before %(due)s.") % {
                "title": version.policy.title, "label": version.version_label,
                "due": campaign.due_date.isoformat(),
            },
        )

    return _send(users, NotificationType.ACKNOWLEDGEMENT_REQUESTED, campaign, url, render, actor=actor)


def notify_acknowledgement_reminder(acknowledgement):
    campaign = acknowledgement.campaign
    version = campaign.policy_version
    url = reverse("documents:acknowledge-list")

    def render():
        return (
            _("Reminder : %(title)s to acknowledge") % {"title": version.policy.title},
            _("%(title)s version %(label)s is waiting for your acknowledgement (due %(due)s).") % {
                "title": version.policy.title, "label": version.version_label,
                "due": campaign.due_date.isoformat(),
            },
        )

    return _send([acknowledgement.user], NotificationType.ACKNOWLEDGEMENT_REMINDER, campaign, url, render)


def notify_version_in_force(version, actor=None):
    policy = version.policy
    recipients = [policy.owner] if policy.owner else []
    url = reverse("documents:policy-detail", kwargs={"pk": policy.pk})

    def render():
        return (
            _("%(title)s : version %(label)s in force") % {"title": policy.title, "label": version.version_label},
            _("Version %(label)s of %(title)s was approved and is now in force.") % {
                "label": version.version_label, "title": policy.title,
            },
        )

    return _send(recipients, NotificationType.POLICY_VERSION_IN_FORCE, policy, url, render, actor=actor)


def notify_review(policy, overdue, recipients):
    url = reverse("documents:policy-detail", kwargs={"pk": policy.pk})
    kind = NotificationType.POLICY_REVIEW_OVERDUE if overdue else NotificationType.POLICY_REVIEW_DUE

    def render():
        if overdue:
            return (
                _("Review overdue : %(title)s") % {"title": policy.title},
                _("%(title)s was due for review on %(date)s.") % {"title": policy.title, "date": policy.next_review_date.isoformat()},
            )
        return (
            _("Review due : %(title)s") % {"title": policy.title},
            _("%(title)s is due for review on %(date)s.") % {"title": policy.title, "date": policy.next_review_date.isoformat()},
        )

    return _send(recipients, kind, policy, url, render)

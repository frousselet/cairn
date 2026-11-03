# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The daily ``documents_sweep`` command (README §7) : review reminders and
acknowledgement reminders, each sent once."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from accounts.constants import NotificationType
from accounts.models import Group, Notification
from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from documents.constants import (
    ACKNOWLEDGEMENT_REMINDER_DAYS,
    CAMPAIGN_RUNNING,
    POLICY_RETIRED,
    REVIEW_REMINDER_DAYS,
)
from documents.models import AcknowledgementCampaign, PolicyAcknowledgement
from documents.tests.factories import (
    AcknowledgementCampaignFactory,
    PolicyFactory,
    PolicyVersionFactory,
    put_in_force,
)

pytestmark = pytest.mark.django_db


def _sweep(*args):
    out = StringIO()
    call_command("documents_sweep", *args, stdout=out)
    return out.getvalue()


def _active_policy(**kwargs):
    version = put_in_force(PolicyVersionFactory(policy=PolicyFactory(**kwargs)))
    policy = version.policy
    policy.refresh_from_db()
    return policy


def _of(kind, user=None):
    qs = Notification.objects.filter(notification_type=kind)
    return qs.filter(recipient=user) if user is not None else qs


class TestReviewReminders:
    def test_due_within_the_window_notifies_the_owner_once(self):
        today = timezone.localdate()
        policy = _active_policy(next_review_override=today + timedelta(days=REVIEW_REMINDER_DAYS - 1))
        _sweep()
        assert _of(NotificationType.POLICY_REVIEW_DUE, policy.owner).count() == 1
        _sweep()
        assert _of(NotificationType.POLICY_REVIEW_DUE, policy.owner).count() == 1

    def test_outside_the_window_sends_nothing(self):
        _active_policy(next_review_override=timezone.localdate() + timedelta(days=REVIEW_REMINDER_DAYS + 5))
        _sweep()
        assert not _of(NotificationType.POLICY_REVIEW_DUE).exists()

    def test_overdue_notifies_owner_and_approvers_in_scope_once(self):
        scope, elsewhere = ScopeFactory(), ScopeFactory()
        policy = _active_policy(next_review_override=timezone.localdate() - timedelta(days=2))
        policy.scopes.set([scope])
        approver = UserFactory()
        Group.objects.get(name="RSSI / DPO").users.add(approver)
        _sweep()
        overdue = _of(NotificationType.POLICY_REVIEW_OVERDUE)
        recipients = set(overdue.values_list("recipient_id", flat=True))
        assert policy.owner.pk in recipients
        assert approver.pk in recipients
        count = overdue.count()
        _sweep()
        assert _of(NotificationType.POLICY_REVIEW_OVERDUE).count() == count

    def test_overdue_skips_approvers_restricted_to_other_scopes(self):
        from documents.notifications import review_overdue_recipients

        scope, elsewhere = ScopeFactory(), ScopeFactory()
        policy = _active_policy(next_review_override=timezone.localdate() - timedelta(days=2))
        policy.scopes.set([scope])
        restricted_group = Group.objects.create(name="Approvers elsewhere")
        restricted_group.permissions.set(
            Group.objects.get(name="RSSI / DPO").permissions.filter(codename="documents.policy.approve")
        )
        restricted_group.allowed_scopes.set([elsewhere])
        outsider = UserFactory()
        restricted_group.users.add(outsider)
        assert outsider not in review_overdue_recipients(policy)

    def test_draft_and_retired_documents_are_ignored(self):
        today = timezone.localdate()
        PolicyFactory(next_review_override=today - timedelta(days=2))
        retired = _active_policy(next_review_override=today - timedelta(days=2))
        retired.transition_to(POLICY_RETIRED, retired.owner, comment="Gone")
        _sweep()
        assert not _of(NotificationType.POLICY_REVIEW_OVERDUE).exists()

    def test_dry_run_sends_nothing(self):
        _active_policy(next_review_override=timezone.localdate() - timedelta(days=2))
        out = _sweep("--dry-run")
        assert "Would send" in out
        assert not Notification.objects.filter(
            notification_type__in=[NotificationType.POLICY_REVIEW_DUE, NotificationType.POLICY_REVIEW_OVERDUE],
        ).exists()


class TestAcknowledgementReminders:
    def _campaign(self, users, due_in):
        policy = _active_policy()
        campaign = AcknowledgementCampaignFactory(
            policy_version=policy.version_in_force,
            due_date=timezone.localdate() + timedelta(days=60),
        )
        campaign.audience_users.set(users)
        campaign.transition_to(CAMPAIGN_RUNNING, policy.owner)
        # The request went out well before the window (the launch notice).
        PolicyAcknowledgement.objects.filter(campaign=campaign).update(
            requested_at=timezone.now() - timedelta(days=50),
        )
        AcknowledgementCampaign.objects.filter(pk=campaign.pk).update(
            due_date=timezone.localdate() + timedelta(days=due_in),
        )
        campaign.refresh_from_db()
        return campaign

    def test_reminds_pending_rows_in_the_window_once(self):
        pending, done = UserFactory(), UserFactory()
        campaign = self._campaign([pending, done], due_in=ACKNOWLEDGEMENT_REMINDER_DAYS - 2)
        campaign.acknowledgements.get(user=done).acknowledge(done)
        _sweep()
        assert _of(NotificationType.ACKNOWLEDGEMENT_REMINDER, pending).count() == 1
        assert not _of(NotificationType.ACKNOWLEDGEMENT_REMINDER, done).exists()
        assert campaign.acknowledgements.get(user=pending).last_reminded_at is not None
        _sweep()
        assert _of(NotificationType.ACKNOWLEDGEMENT_REMINDER, pending).count() == 1

    def test_reminds_again_the_day_after_the_due_date(self):
        user = UserFactory()
        campaign = self._campaign([user], due_in=ACKNOWLEDGEMENT_REMINDER_DAYS - 2)
        _sweep()
        assert _of(NotificationType.ACKNOWLEDGEMENT_REMINDER, user).count() == 1
        AcknowledgementCampaign.objects.filter(pk=campaign.pk).update(
            due_date=timezone.localdate() - timedelta(days=1),
        )
        # The previous reminder was sent before the (new) due date.
        PolicyAcknowledgement.objects.filter(campaign=campaign).update(
            last_reminded_at=timezone.now() - timedelta(days=3),
        )
        _sweep()
        assert _of(NotificationType.ACKNOWLEDGEMENT_REMINDER, user).count() == 2
        _sweep()
        assert _of(NotificationType.ACKNOWLEDGEMENT_REMINDER, user).count() == 2

    def test_nothing_before_the_window(self):
        user = UserFactory()
        self._campaign([user], due_in=ACKNOWLEDGEMENT_REMINDER_DAYS + 10)
        _sweep()
        assert not _of(NotificationType.ACKNOWLEDGEMENT_REMINDER).exists()

    def test_a_row_requested_inside_the_window_is_not_reminded_before_due(self):
        user = UserFactory()
        campaign = self._campaign([user], due_in=3)
        PolicyAcknowledgement.objects.filter(campaign=campaign).update(requested_at=timezone.now())
        _sweep()
        assert not _of(NotificationType.ACKNOWLEDGEMENT_REMINDER).exists()

    def test_closed_campaigns_are_ignored(self):
        user = UserFactory()
        campaign = self._campaign([user], due_in=2)
        from documents.constants import CAMPAIGN_CLOSED

        campaign.transition_to(CAMPAIGN_CLOSED, None)
        _sweep()
        assert not _of(NotificationType.ACKNOWLEDGEMENT_REMINDER).exists()

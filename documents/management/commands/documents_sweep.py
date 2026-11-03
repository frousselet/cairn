# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Daily sweep of module 7 (documents) : review and acknowledgement reminders.

Designed to be run once a day by cron, like the other deadline sweeps (see
docs/technical/operations.md). It changes no lifecycle state : overdue is
always derived from the date (RG-DOC-12), so the sweep only tells people.

- ``POLICY_REVIEW_DUE`` : an active document whose next review falls within
  ``REVIEW_REMINDER_DAYS``; sent to the owner once per review cycle.
- ``POLICY_REVIEW_OVERDUE`` : an active document whose next review has passed;
  sent once per cycle to the owner and the holders of
  ``documents.policy.approve`` whose perimeter reaches the document.
- ``ACKNOWLEDGEMENT_REMINDER`` : a pending row of a running campaign, once
  ``ACKNOWLEDGEMENT_REMINDER_DAYS`` before the due date and once the day after
  it, ``last_reminded_at`` recording each so a rerun sends nothing twice.

"Active" and "running" come from the lifecycles (``reportable()`` and the
step constants), never a literal. Idempotent : running it twice the same day
sends nothing the second time.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.constants import NotificationType
from core.lifecycle import reportable
from documents.constants import (
    ACKNOWLEDGEMENT_REMINDER_DAYS,
    CAMPAIGN_RUNNING,
    REVIEW_REMINDER_DAYS,
    AcknowledgementStatus,
)
from documents.models import Policy, PolicyAcknowledgement
from documents.notifications import (
    already_notified,
    notify_acknowledgement_reminder,
    notify_review,
    review_overdue_recipients,
)


class Command(BaseCommand):
    help = (
        "Send the document review reminders (due within "
        f"{REVIEW_REMINDER_DAYS} days, overdue) and the acknowledgement reminders "
        f"({ACKNOWLEDGEMENT_REMINDER_DAYS} days before a campaign's due date and "
        "the day after it). Run daily."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the reminders that would be sent without sending anything.",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        dry_run = options["dry_run"]
        due, overdue = self._sweep_reviews(today, dry_run)
        reminded = self._sweep_acknowledgements(today, dry_run)
        verb = "Would send" if dry_run else "Sent"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {due} review-due, {overdue} review-overdue and "
            f"{reminded} acknowledgement reminder(s)."
        ))

    # --- Review cycle (RG-DOC-11 / RG-DOC-12) ------------------------------

    def _sweep_reviews(self, today, dry_run):
        due_count = overdue_count = 0
        active = (
            reportable(Policy.objects.filter(next_review_date__isnull=False))
            .select_related("owner")
            .order_by("next_review_date", "reference")
        )
        horizon = today + timedelta(days=REVIEW_REMINDER_DAYS)
        for policy in active.filter(next_review_date__gte=today, next_review_date__lte=horizon):
            # One reminder per cycle : the cycle is identified by its review
            # date, so a reminder sent inside this cycle's window counts.
            window_start = policy.next_review_date - timedelta(days=REVIEW_REMINDER_DAYS)
            if already_notified(policy, NotificationType.POLICY_REVIEW_DUE, window_start):
                continue
            if not policy.owner_id:
                continue
            due_count += 1
            self.stdout.write(f"  review due : {policy.reference} on {policy.next_review_date.isoformat()}")
            if not dry_run:
                notify_review(policy, overdue=False, recipients=[policy.owner])
        for policy in active.filter(next_review_date__lt=today):
            if already_notified(policy, NotificationType.POLICY_REVIEW_OVERDUE, policy.next_review_date):
                continue
            recipients = review_overdue_recipients(policy)
            if not recipients:
                continue
            overdue_count += 1
            self.stdout.write(
                f"  review overdue : {policy.reference} since {policy.next_review_date.isoformat()}"
            )
            if not dry_run:
                notify_review(policy, overdue=True, recipients=recipients)
        return due_count, overdue_count

    # --- Acknowledgement campaigns (README §7) -----------------------------

    def _sweep_acknowledgements(self, today, dry_run):
        count = 0
        rows = (
            PolicyAcknowledgement.objects.filter(
                status=AcknowledgementStatus.PENDING,
                campaign__workflow_state=CAMPAIGN_RUNNING,
            )
            .select_related("campaign__policy_version__policy", "user")
            .order_by("campaign__due_date", "pk")
        )
        now = timezone.now()
        for row in rows:
            if not self._reminder_due(row, today):
                continue
            count += 1
            self.stdout.write(
                f"  acknowledgement reminder : {row.campaign.reference} -> {row.user.email}"
            )
            if dry_run:
                continue
            if notify_acknowledgement_reminder(row):
                # Allowed while the row is pending (RG-DOC-16), the one field
                # the system may still touch.
                row.last_reminded_at = now
                row.save(update_fields=["last_reminded_at"])
        return count

    @staticmethod
    def _reminder_due(row, today):
        """The two reminder moments of a pending row : from
        ``ACKNOWLEDGEMENT_REMINDER_DAYS`` before the due date, and from the
        day after it. Each is sent once, ``last_reminded_at`` recording it."""
        due_date = row.campaign.due_date
        pre_start = due_date - timedelta(days=ACKNOWLEDGEMENT_REMINDER_DAYS)
        last = timezone.localdate(row.last_reminded_at) if row.last_reminded_at else None
        if today > due_date:
            return last is None or last <= due_date
        if pre_start <= today <= due_date:
            # A row requested inside the window was just told by the request
            # itself; a reminder on top of it would be noise.
            if timezone.localdate(row.requested_at) >= pre_start:
                return False
            return last is None or last < pre_start
        return False

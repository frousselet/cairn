# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Daily sweep of module 8 (controls) : test reminders and effectiveness.

Designed to be run once a day by cron, like the other deadline sweeps (see
docs/technical/operations.md). It changes no lifecycle state : overdue is
always derived from the date (RG-CTL-07), so the sweep only tells people and
keeps the derived effectiveness in step (RG-CTL-14).

- ``CONTROL_TEST_DUE`` : an active test whose next due date falls within
  ``TEST_DUE_REMINDER_DAYS``; sent once per cycle to the tester, else the
  control owner.
- ``CONTROL_TEST_OVERDUE`` : an active test whose next due date has passed;
  sent to the tester and the control owner once, then again every
  ``OVERDUE_REMINDER_INTERVAL_DAYS`` while it stays overdue.
- Every control that counts in reports has its effectiveness recomputed
  (idempotent, written only on change).

``ControlTest.last_reminded_at`` records each reminder, written with a
queryset ``update()`` : it is a system stamp, not an edit of the test, so it
neither bumps the version nor writes a history row, and never runs the
model's ``save()`` (which re-derives the due date). "Active" and "reportable"
come from the lifecycles (``reportable()``), never a literal. Idempotent :
running it twice the same day sends nothing the second time.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from controls.constants import OVERDUE_REMINDER_INTERVAL_DAYS, TEST_DUE_REMINDER_DAYS
from controls.models import Control, ControlTest
from controls.notifications import notify_test_due
from core.lifecycle import reportable


def due_reminder_needed(test, today):
    """Whether the "due soon" reminder of the test's current cycle is owed.

    The cycle is identified by its due date : a reminder sent on or after
    the start of this cycle's window already covered it. A validated run
    moves the due date forward, which opens a new cycle."""
    window_start = test.next_due_date - timedelta(days=TEST_DUE_REMINDER_DAYS)
    last = timezone.localdate(test.last_reminded_at) if test.last_reminded_at else None
    return last is None or last < window_start


def overdue_reminder_needed(test, today):
    """Whether an overdue reminder is owed : the first one (no reminder sent
    after the due date yet), then one every ``OVERDUE_REMINDER_INTERVAL_DAYS``."""
    last = timezone.localdate(test.last_reminded_at) if test.last_reminded_at else None
    if last is None or last <= test.next_due_date:
        return True
    return (today - last).days >= OVERDUE_REMINDER_INTERVAL_DAYS


def _has_recipient(test):
    return bool(test.tester_id or test.control.owner_id)


class Command(BaseCommand):
    help = (
        "Send the control test reminders (due within "
        f"{TEST_DUE_REMINDER_DAYS} days, overdue once then every "
        f"{OVERDUE_REMINDER_INTERVAL_DAYS} days) and recompute the effectiveness "
        "of every reportable control. Run daily."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the reminders and effectiveness changes without writing anything.",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        dry_run = options["dry_run"]
        due, overdue = self._sweep_tests(today, dry_run)
        changed = self._recompute_effectiveness(dry_run)
        verb = "Would send" if dry_run else "Sent"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {due} test-due and {overdue} test-overdue reminder(s); "
            f"{changed} control effectiveness value(s) {'would change' if dry_run else 'updated'}."
        ))

    # --- Reminders (README §7) ---------------------------------------------

    def _sweep_tests(self, today, dry_run):
        due_count = overdue_count = 0
        active = (
            reportable(ControlTest.objects.filter(next_due_date__isnull=False))
            .select_related("control__owner", "tester")
            .order_by("next_due_date", "reference")
        )
        horizon = today + timedelta(days=TEST_DUE_REMINDER_DAYS)
        now = timezone.now()
        for test in active.filter(next_due_date__gte=today, next_due_date__lte=horizon):
            if not due_reminder_needed(test, today) or not _has_recipient(test):
                continue
            due_count += 1
            self.stdout.write(f"  test due : {test.reference} on {test.next_due_date.isoformat()}")
            if not dry_run and notify_test_due(test, overdue=False):
                ControlTest.objects.filter(pk=test.pk).update(last_reminded_at=now)
        for test in active.filter(next_due_date__lt=today):
            if not overdue_reminder_needed(test, today) or not _has_recipient(test):
                continue
            overdue_count += 1
            self.stdout.write(f"  test overdue : {test.reference} since {test.next_due_date.isoformat()}")
            if not dry_run and notify_test_due(test, overdue=True):
                ControlTest.objects.filter(pk=test.pk).update(last_reminded_at=now)
        return due_count, overdue_count

    # --- Effectiveness (RG-CTL-14) -----------------------------------------

    def _recompute_effectiveness(self, dry_run):
        changed = 0
        for control in reportable(Control.objects.all()).order_by("reference"):
            if dry_run:
                if control.compute_effectiveness() != control.effectiveness:
                    changed += 1
                continue
            if control.recompute_effectiveness():
                changed += 1
                self.stdout.write(f"  effectiveness : {control.reference} -> {control.effectiveness}")
        return changed

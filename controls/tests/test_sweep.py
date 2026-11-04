# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The daily ``controls_sweep`` command (README §7) : test due / overdue
reminders, each sent once per cycle (overdue : once, then weekly), and the
recomputation of every reportable control's effectiveness."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from accounts.constants import NotificationType
from accounts.models import Notification
from controls.constants import (
    OVERDUE_REMINDER_INTERVAL_DAYS,
    TEST_DUE_REMINDER_DAYS,
    TEST_RETIRED,
    ControlEffectiveness,
    RunResult,
)
from controls.models import Control, ControlTest
from controls.tests.factories import active_test, implemented_control, validated_run

pytestmark = pytest.mark.django_db


def _sweep(*args):
    out = StringIO()
    call_command("controls_sweep", *args, stdout=out)
    return out.getvalue()


def _of(kind, user=None):
    qs = Notification.objects.filter(notification_type=kind)
    return qs.filter(recipient=user) if user is not None else qs


def _test_due_in(days, **kwargs):
    return active_test(first_due_date=timezone.localdate() + timedelta(days=days), **kwargs)


def _shift_reminder(test, days):
    """Pretend the last reminder went out ``days`` days ago."""
    ControlTest.objects.filter(pk=test.pk).update(
        last_reminded_at=timezone.now() - timedelta(days=days),
    )


class TestDueReminders:
    def test_due_within_the_window_notifies_the_tester_once(self):
        test = _test_due_in(TEST_DUE_REMINDER_DAYS - 1)
        _sweep()
        assert _of(NotificationType.CONTROL_TEST_DUE, test.tester).count() == 1
        test.refresh_from_db()
        assert test.last_reminded_at is not None
        _sweep()
        assert _of(NotificationType.CONTROL_TEST_DUE).count() == 1

    def test_outside_the_window_sends_nothing(self):
        _test_due_in(TEST_DUE_REMINDER_DAYS + 5)
        _sweep()
        assert not _of(NotificationType.CONTROL_TEST_DUE).exists()

    def test_falls_back_to_the_control_owner_without_a_tester(self):
        test = _test_due_in(3, tester=None)
        _sweep()
        assert _of(NotificationType.CONTROL_TEST_DUE, test.control.owner).count() == 1

    def test_a_new_cycle_is_reminded_again(self):
        test = _test_due_in(2)
        _sweep()
        # A validated run moves the due date a full frequency forward; the
        # next window opens long after the reminder that was sent.
        _shift_reminder(test, 200)
        ControlTest.objects.filter(pk=test.pk).update(next_due_date=timezone.localdate() + timedelta(days=5))
        _sweep()
        assert _of(NotificationType.CONTROL_TEST_DUE).count() == 2

    def test_draft_and_retired_tests_are_never_reminded(self):
        test = _test_due_in(2)
        test.transition_to(TEST_RETIRED, test.control.owner, comment="No longer relevant.")
        _sweep()
        assert not Notification.objects.filter(
            notification_type__in=[NotificationType.CONTROL_TEST_DUE, NotificationType.CONTROL_TEST_OVERDUE],
        ).exists()


class TestOverdueReminders:
    def test_overdue_notifies_tester_and_owner_then_weekly(self):
        test = _test_due_in(-30)
        _sweep()
        overdue = _of(NotificationType.CONTROL_TEST_OVERDUE)
        assert set(overdue.values_list("recipient_id", flat=True)) == {test.tester_id, test.control.owner_id}
        first = overdue.count()
        _sweep()
        assert _of(NotificationType.CONTROL_TEST_OVERDUE).count() == first
        _shift_reminder(test, OVERDUE_REMINDER_INTERVAL_DAYS - 1)
        _sweep()
        assert _of(NotificationType.CONTROL_TEST_OVERDUE).count() == first
        _shift_reminder(test, OVERDUE_REMINDER_INTERVAL_DAYS)
        _sweep()
        assert _of(NotificationType.CONTROL_TEST_OVERDUE).count() == first * 2

    def test_a_due_reminder_does_not_count_as_the_overdue_one(self):
        test = _test_due_in(1)
        _sweep()
        assert _of(NotificationType.CONTROL_TEST_DUE).count() == 1
        # Two days later the test is overdue : the reminder sent before the
        # due date was the "due soon" one, so the overdue one is still owed.
        ControlTest.objects.filter(pk=test.pk).update(
            next_due_date=timezone.localdate() - timedelta(days=1),
            last_reminded_at=timezone.now() - timedelta(days=2),
        )
        _sweep()
        assert _of(NotificationType.CONTROL_TEST_OVERDUE).exists()

    def test_last_reminded_at_is_written_without_a_history_row(self):
        test = _test_due_in(-2)
        before = test.history.count()
        version = test.version
        _sweep()
        test.refresh_from_db()
        assert test.last_reminded_at is not None
        assert test.history.count() == before
        assert test.version == version


class TestEffectivenessAndDryRun:
    def test_recomputes_a_stale_effectiveness(self):
        run = validated_run(result=RunResult.FAIL)
        control = run.test.control
        Control.objects.filter(pk=control.pk).update(effectiveness=ControlEffectiveness.EFFECTIVE)
        out = _sweep()
        control.refresh_from_db()
        assert control.effectiveness == ControlEffectiveness.NOT_EFFECTIVE
        assert "1 control effectiveness value(s) updated" in out

    def test_proposed_controls_are_left_alone(self):
        from controls.tests.factories import ControlFactory

        control = ControlFactory()
        Control.objects.filter(pk=control.pk).update(effectiveness=ControlEffectiveness.EFFECTIVE)
        _sweep()
        control.refresh_from_db()
        assert control.effectiveness == ControlEffectiveness.EFFECTIVE

    def test_dry_run_sends_and_writes_nothing(self):
        test = _test_due_in(-3)
        control = implemented_control()
        validated_run(test=active_test(control=control), result=RunResult.PASS)
        Control.objects.filter(pk=control.pk).update(effectiveness=ControlEffectiveness.NOT_TESTED)
        out = _sweep("--dry-run")
        assert "Would send 0 test-due and 1 test-overdue reminder(s)" in out
        assert "1 control effectiveness value(s) would change" in out
        assert not _of(NotificationType.CONTROL_TEST_OVERDUE).exists()
        test.refresh_from_db()
        assert test.last_reminded_at is None
        control.refresh_from_db()
        assert control.effectiveness == ControlEffectiveness.NOT_TESTED

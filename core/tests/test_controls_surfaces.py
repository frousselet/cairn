# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Module 8 on the platform surfaces (README §8) : global search, calendar,
dashboard widget, kanban tests and runs, predefined indicators and the
dashboard refresh registration."""

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Group
from accounts.tests.factories import UserFactory
from compliance.constants import FindingType
from context.constants import PREDEFINED_SOURCE_FORMAT, PredefinedIndicatorSource
from context.models import Indicator
from controls.constants import (
    CONTROL_PLANNED,
    RUN_IN_REVIEW,
    TEST_DUE_REMINDER_DAYS,
    TEST_RETIRED,
    RunResult,
)
from controls.models import Control, ControlTest, ControlTestRun
from controls.tests.factories import (
    ControlFactory,
    ControlTestFactory,
    ControlTestRunFactory,
    active_test,
    implemented_control,
    validated_run,
)
from core.dashboard import WIDGETS_BY_ID, default_layout
from core.kanban import DOING, TODO, build_kanban_columns
from core.signals import _get_dashboard_models
from core.views import ALL_CATEGORIES, CATEGORY_LABELS, controls_dashboard_context, get_calendar_events

pytestmark = pytest.mark.django_db


def _in_group(name, user=None):
    user = user or UserFactory()
    Group.objects.get(name=name).users.add(user)
    return user


def _due_in(days, **kwargs):
    return active_test(first_due_date=timezone.localdate() + timedelta(days=days), **kwargs)


def _cards(user, type_key, column=None):
    return [
        card
        for col in build_kanban_columns(user)
        if column is None or col["key"] == column
        for card in col["cards"]
        if card["type_key"] == type_key
    ]


# --- Global search -----------------------------------------------------------


class TestGlobalSearch:
    def _search(self, user, q):
        client = Client()
        client.force_login(user)
        return client.get(reverse("global-search"), {"q": q}).json()["results"]

    def test_finds_controls_and_tests(self):
        test = active_test(name="Zephyr login sample", control=implemented_control(name="Zephyr MFA"))
        groups = {g["label"]: g for g in self._search(UserFactory(is_superuser=True), "Zephyr")}
        assert groups["Controls"]["items"][0]["url"] == reverse("controls:control-detail", args=[test.control.pk])
        assert groups["Control tests"]["items"][0]["url"] == reverse("controls:controltest-detail", args=[test.pk])

    def test_hidden_without_the_read_permission(self):
        active_test(name="Zephyr login sample", control=implemented_control(name="Zephyr MFA"))
        labels = {g["label"] for g in self._search(UserFactory(), "Zephyr")}
        assert "Controls" not in labels and "Control tests" not in labels


# --- Calendar ----------------------------------------------------------------


class TestCalendar:
    def test_next_due_dates_of_active_tests_only(self):
        due = _due_in(5, name="Calendar active test")
        ControlTestFactory(name="Calendar draft test", control=implemented_control())
        retired = _due_in(5, name="Calendar retired test")
        retired.transition_to(TEST_RETIRED, retired.control.owner, comment="Gone")
        events = get_calendar_events(UserFactory(is_superuser=True), categories=["controls"])
        titles = {e["plain_title"] for e in events}
        assert titles == {str(due)}
        (event,) = events
        assert event["is_deadline"] and event["category"] == "controls"
        assert event["start"] == due.next_due_date.isoformat()
        assert event["url"] == reverse("controls:controltest-detail", args=[due.pk])
        assert event["responsible_pk"] == str(due.tester_id)

    def test_permission_gated(self):
        _due_in(5)
        assert get_calendar_events(UserFactory(), categories=["controls"]) == []
        assert len(get_calendar_events(_in_group("Lecteur"), categories=["controls"])) == 1

    def test_category_is_registered(self):
        assert "controls" in ALL_CATEGORIES and "controls" in CATEGORY_LABELS


# --- Dashboard widget --------------------------------------------------------


class TestDashboardWidget:
    def test_widget_is_registered_and_placed_by_default(self):
        widget = WIDGETS_BY_ID["controls"]
        assert widget.template == "dashboard/widgets/controls.html"
        assert "controls" in {entry["id"] for entry in default_layout()}

    def test_context_counts(self):
        today = timezone.localdate()
        effective = validated_run(result=RunResult.PASS).test.control
        failed_run = validated_run(result=RunResult.FAIL)
        planned = ControlFactory()
        planned.transition_to(CONTROL_PLANNED, planned.owner)
        ControlFactory()  # proposed : counted nowhere
        overdue = _due_in(-4)
        raised = validated_run(result=RunResult.PARTIAL)
        raised.raise_finding(UserFactory(), FindingType.OBSERVATION)

        ctx = controls_dashboard_context(UserFactory(is_superuser=True), today)
        # effective + failed + overdue's + raised's controls implemented, planned on top.
        assert ctx["controls_implemented_count"] == 4
        assert ctx["controls_reportable_count"] == 5
        # Tested : effective, failed (not effective), raised (partial).
        assert ctx["controls_tested_count"] == 3
        assert ctx["controls_effective_count"] == 1
        assert ctx["controls_effective_rate"] == 33
        assert ctx["controls_overdue_test_count"] == 1
        assert ctx["controls_overdue_tests"][0] == {"test": overdue, "days_late": 4}
        assert ctx["controls_runs_awaiting_finding"] == [failed_run]
        assert effective.pk != failed_run.test.control_id

    def test_context_is_permission_gated(self):
        validated_run(result=RunResult.FAIL)
        _due_in(-4)
        ctx = controls_dashboard_context(UserFactory(), timezone.localdate())
        assert ctx["controls_reportable_count"] == 0
        assert ctx["controls_overdue_test_count"] == 0
        assert ctx["controls_runs_awaiting_finding"] == []
        assert ctx["controls_effective_rate"] is None

    def test_home_renders_the_widget(self):
        _due_in(-4, name="Overdue quarterly access review")
        client = Client()
        client.force_login(UserFactory(is_superuser=True))
        body = client.get(reverse("home")).content.decode()
        assert "Overdue quarterly access review" in body
        assert "ctlw-stats" in body

    def test_models_refresh_the_dashboard(self):
        models = _get_dashboard_models()
        for model in (Control, ControlTest, ControlTestRun):
            assert model in models


# --- Kanban ------------------------------------------------------------------


class TestKanban:
    def test_my_tests_due_within_the_window_are_in_todo(self):
        tester = _in_group("Contributeur")
        due = _due_in(TEST_DUE_REMINDER_DAYS - 1, tester=tester)
        overdue = _due_in(-2, tester=tester)
        _due_in(TEST_DUE_REMINDER_DAYS + 10, tester=tester)  # not yet
        _due_in(2)  # someone else's
        cards = _cards(tester, "control_test", TODO)
        assert {c["reference"] for c in cards} == {due.reference, overdue.reference}
        assert next(c for c in cards if c["reference"] == overdue.reference)["is_overdue"]

    def test_owner_gets_the_tests_without_a_tester(self):
        owner = _in_group("Contributeur")
        test = _due_in(3, tester=None, control=implemented_control(owner=owner))
        assert [c["reference"] for c in _cards(owner, "control_test")] == [test.reference]

    def test_my_draft_runs_are_in_doing(self):
        performer = _in_group("Contributeur")
        test = active_test(tester=performer)
        run = ControlTestRunFactory(test=test, performed_by=performer)
        cards = _cards(performer, "control_test_run", DOING)
        assert [c["reference"] for c in cards] == [run.reference]
        assert cards[0]["url"] == reverse("controls:controltestrun-detail", args=[run.pk])

    def test_runs_to_review_for_an_approver_never_their_own(self):
        approver = _in_group("RSSI / DPO")
        other = ControlTestRunFactory(result=RunResult.PASS)
        other.transition_to(RUN_IN_REVIEW, other.performed_by)
        own = ControlTestRunFactory(test=active_test(tester=approver), performed_by=approver, result=RunResult.PASS)
        own.transition_to(RUN_IN_REVIEW, approver)
        cards = _cards(approver, "control_test_run", TODO)
        assert [c["reference"] for c in cards] == [other.reference]

    def test_superuser_never_reviews_their_own_run(self):
        admin = UserFactory(is_superuser=True)
        own = ControlTestRunFactory(test=active_test(tester=admin), performed_by=admin, result=RunResult.PASS)
        own.transition_to(RUN_IN_REVIEW, admin)
        assert own.reference not in {c["reference"] for c in _cards(admin, "control_test_run", TODO)}

    def test_contributor_cannot_review(self):
        contributor = _in_group("Contributeur")
        run = ControlTestRunFactory(result=RunResult.PASS)
        run.transition_to(RUN_IN_REVIEW, run.performed_by)
        assert _cards(contributor, "control_test_run", TODO) == []

    def test_no_permission_no_cards(self):
        user = UserFactory()
        _due_in(3, tester=user)
        assert _cards(user, "control_test") == []


# --- Predefined indicators ---------------------------------------------------


class TestPredefinedIndicators:
    def _value(self, source):
        return Indicator(name="x", is_internal=True, internal_source=source).compute_internal_value()

    def test_formats_are_declared(self):
        assert PREDEFINED_SOURCE_FORMAT[PredefinedIndicatorSource.CONTROL_EFFECTIVENESS_RATE] == ("number", "%")
        assert PREDEFINED_SOURCE_FORMAT[PredefinedIndicatorSource.CONTROL_TESTS_OVERDUE] == ("number", "")

    def test_effectiveness_rate_over_tested_reportable_controls(self):
        validated_run(result=RunResult.PASS)
        validated_run(result=RunResult.PASS)
        validated_run(result=RunResult.FAIL)
        implemented_control()  # not tested : out of the denominator
        assert self._value(PredefinedIndicatorSource.CONTROL_EFFECTIVENESS_RATE) == "66.7"

    def test_effectiveness_rate_with_nothing_tested(self):
        assert self._value(PredefinedIndicatorSource.CONTROL_EFFECTIVENESS_RATE) == "0"

    def test_tests_overdue(self):
        _due_in(-1)
        _due_in(10)
        retired = _due_in(-5)
        retired.transition_to(TEST_RETIRED, retired.control.owner, comment="Gone")
        assert self._value(PredefinedIndicatorSource.CONTROL_TESTS_OVERDUE) == "1"

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Module 7 on the platform surfaces (README §8) : global search, calendar,
dashboard widget, kanban acknowledgements, predefined indicators and the
dashboard refresh registration."""

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Group
from accounts.tests.factories import UserFactory
from context.constants import PREDEFINED_SOURCE_FORMAT, PredefinedIndicatorSource
from context.models import Indicator
from core.dashboard import WIDGETS_BY_ID, default_layout
from core.kanban import TODO, build_kanban_columns
from core.signals import _get_dashboard_models
from core.views import documents_dashboard_context, get_calendar_events
from documents.constants import (
    CAMPAIGN_CLOSED,
    CAMPAIGN_RUNNING,
    POLICY_RETIRED,
    VERSION_SUPERSEDED,
)
from documents.models import AcknowledgementCampaign, Policy, PolicyAcknowledgement, PolicyVersion
from documents.tests.factories import (
    AcknowledgementCampaignFactory,
    PolicyFactory,
    PolicyVersionFactory,
    put_in_force,
)

pytestmark = pytest.mark.django_db


def _active_policy(**kwargs):
    version = put_in_force(PolicyVersionFactory(policy=PolicyFactory(**kwargs)))
    policy = version.policy
    policy.refresh_from_db()
    return policy


def _running_campaign(users, due_in=30, policy=None):
    policy = policy or _active_policy()
    campaign = AcknowledgementCampaignFactory(
        policy_version=policy.version_in_force,
        due_date=timezone.localdate() + timedelta(days=due_in),
    )
    campaign.audience_users.set(users)
    campaign.transition_to(CAMPAIGN_RUNNING, policy.owner)
    return campaign


def _reader():
    user = UserFactory()
    Group.objects.get(name="Lecteur").users.add(user)
    return user


# --- Global search -----------------------------------------------------------


class TestGlobalSearch:
    def _search(self, user, q):
        client = Client()
        client.force_login(user)
        return client.get(reverse("global-search"), {"q": q}).json()["results"]

    def test_finds_documents_and_versions(self):
        policy = _active_policy(title="Zephyr acceptable use charter")
        groups = {g["label"]: g for g in self._search(UserFactory(is_superuser=True), "Zephyr")}
        assert "Documents" in groups
        assert groups["Documents"]["items"][0]["url"] == reverse("documents:policy-detail", args=[policy.pk])
        assert "Document versions" in groups
        version = policy.version_in_force
        assert groups["Document versions"]["items"][0]["url"] == reverse(
            "documents:policyversion-detail", args=[version.pk],
        )

    def test_hidden_without_the_read_permission(self):
        _active_policy(title="Zephyr charter")
        labels = {g["label"] for g in self._search(UserFactory(), "Zephyr")}
        assert "Documents" not in labels and "Document versions" not in labels


# --- Calendar ----------------------------------------------------------------


class TestCalendar:
    def test_review_dates_of_active_documents_only(self):
        today = timezone.localdate()
        active = _active_policy(title="Calendar active", next_review_override=today + timedelta(days=5))
        PolicyFactory(title="Calendar draft", next_review_override=today + timedelta(days=5))
        retired = _active_policy(title="Calendar retired", next_review_override=today + timedelta(days=5))
        retired.transition_to(POLICY_RETIRED, retired.owner, comment="Gone")
        events = get_calendar_events(UserFactory(is_superuser=True), categories=["documents"])
        titles = {e["plain_title"] for e in events}
        assert str(active) in titles
        assert not any("Calendar draft" in t or "Calendar retired" in t for t in titles)
        event = next(e for e in events if e["plain_title"] == str(active))
        assert event["is_deadline"] and event["category"] == "documents"
        assert event["url"] == reverse("documents:policy-detail", args=[active.pk])

    def test_campaign_due_dates_with_closed_ones_done(self):
        running = _running_campaign([UserFactory()])
        closed = _running_campaign([UserFactory()])
        closed.transition_to(CAMPAIGN_CLOSED, closed.created_by)
        AcknowledgementCampaignFactory(name="Draft campaign")
        events = {e["plain_title"]: e for e in get_calendar_events(
            UserFactory(is_superuser=True), categories=["documents"],
        )}
        assert events[str(running)]["is_done"] is False
        assert events[str(closed)]["is_done"] is True
        assert not any("Draft campaign" in t for t in events)

    def test_category_is_registered(self):
        from core.views import ALL_CATEGORIES, CATEGORY_LABELS

        assert "documents" in ALL_CATEGORIES and "documents" in CATEGORY_LABELS


# --- Dashboard widget --------------------------------------------------------


class TestDashboardWidget:
    def test_widget_is_registered_and_placed_by_default(self):
        widget = WIDGETS_BY_ID["documents"]
        assert widget.template == "dashboard/widgets/documents.html"
        assert "documents" in {entry["id"] for entry in default_layout()}

    def test_context_counts_overdue_without_version_and_campaigns(self):
        today = timezone.localdate()
        overdue = _active_policy(next_review_override=today - timedelta(days=3))
        _active_policy(next_review_override=today + timedelta(days=90))
        withdrawn = _active_policy()
        withdrawn.version_in_force.transition_to(VERSION_SUPERSEDED, withdrawn.owner, comment="Withdrawn")
        PolicyFactory()  # a draft : not counted anywhere
        ack_user = UserFactory()
        campaign = _running_campaign([ack_user, UserFactory()])
        campaign.acknowledgements.get(user=ack_user).acknowledge(ack_user)

        ctx = documents_dashboard_context(UserFactory(is_superuser=True), today)
        assert ctx["documents_overdue_count"] == 1
        assert ctx["documents_overdue"][0]["policy"] == overdue
        assert ctx["documents_overdue"][0]["days_late"] == 3
        assert ctx["documents_without_version_count"] == 1
        assert ctx["documents_without_version"] == [withdrawn]
        assert ctx["documents_running_campaign_count"] == 1
        row = ctx["documents_running_campaigns"][0]
        assert row["campaign"] == campaign and row["rate"] == 50
        assert row["acknowledged"] == 1 and row["pending"] == 1

    def test_context_is_permission_gated(self):
        _active_policy(next_review_override=timezone.localdate() - timedelta(days=3))
        _running_campaign([UserFactory()])
        ctx = documents_dashboard_context(UserFactory(), timezone.localdate())
        assert ctx["documents_overdue_count"] == 0
        assert ctx["documents_running_campaigns"] == []

    def test_home_renders_the_widget(self):
        _active_policy(title="Overdue access policy", next_review_override=timezone.localdate() - timedelta(days=3))
        client = Client()
        client.force_login(UserFactory(is_superuser=True))
        body = client.get(reverse("home")).content.decode()
        assert "Overdue access policy" in body
        assert "docw-stats" in body

    def test_models_refresh_the_dashboard(self):
        models = _get_dashboard_models()
        for model in (Policy, PolicyVersion, AcknowledgementCampaign, PolicyAcknowledgement):
            assert model in models


# --- Kanban ------------------------------------------------------------------


class TestKanbanAcknowledgements:
    def test_own_pending_row_is_in_todo_with_no_permission(self):
        user = UserFactory()  # no group, no permission : RG-DOC-17
        campaign = _running_campaign([user, UserFactory()])
        row = campaign.acknowledgements.get(user=user)
        cols = {c["key"]: c for c in build_kanban_columns(user)}
        cards = [c for c in cols[TODO]["cards"] if c["type_key"] == "acknowledgement"]
        assert len(cards) == 1
        assert cards[0]["url"] == reverse("documents:acknowledge", kwargs={"pk": row.pk})
        assert cards[0]["due_date"] == campaign.due_date

    def test_other_people_rows_and_done_rows_are_not_shown(self):
        user, other = UserFactory(), UserFactory()
        campaign = _running_campaign([user, other])
        campaign.acknowledgements.get(user=user).acknowledge(user)
        cards = [
            c for col in build_kanban_columns(user) for c in col["cards"]
            if c["type_key"] == "acknowledgement"
        ]
        assert cards == []

    def test_superuser_sees_only_their_own(self):
        admin = UserFactory(is_superuser=True)
        _running_campaign([UserFactory()])
        cards = [
            c for col in build_kanban_columns(admin) for c in col["cards"]
            if c["type_key"] == "acknowledgement"
        ]
        assert cards == []


# --- Predefined indicators ---------------------------------------------------


class TestPredefinedIndicators:
    def _indicator(self, source):
        return Indicator(name="x", is_internal=True, internal_source=source)

    def test_formats_are_declared(self):
        assert PREDEFINED_SOURCE_FORMAT[PredefinedIndicatorSource.POLICIES_OVERDUE_REVIEW] == ("number", "")
        assert PREDEFINED_SOURCE_FORMAT[PredefinedIndicatorSource.ACKNOWLEDGEMENT_RATE] == ("number", "%")

    def test_policies_overdue_review(self):
        today = timezone.localdate()
        _active_policy(next_review_override=today - timedelta(days=1))
        _active_policy(next_review_override=today + timedelta(days=10))
        PolicyFactory(next_review_override=today - timedelta(days=1))  # draft, not counted
        value = self._indicator(PredefinedIndicatorSource.POLICIES_OVERDUE_REVIEW).compute_internal_value()
        assert value == "1"

    def test_acknowledgement_rate_ignores_excused_and_draft_campaigns(self):
        a, b, c, d = UserFactory(), UserFactory(), UserFactory(), UserFactory()
        campaign = _running_campaign([a, b, c, d])
        campaign.acknowledgements.get(user=a).acknowledge(a)
        campaign.acknowledgements.get(user=b).excuse(campaign.created_by, "Left the company")
        draft = AcknowledgementCampaignFactory()
        draft.audience_users.set([UserFactory()])
        # 1 acknowledged / (4 rows - 1 excused) = 33.3 %
        value = self._indicator(PredefinedIndicatorSource.ACKNOWLEDGEMENT_RATE).compute_internal_value()
        assert value == "33.3"

    def test_acknowledgement_rate_with_nothing_to_count(self):
        assert self._indicator(PredefinedIndicatorSource.ACKNOWLEDGEMENT_RATE).compute_internal_value() == "0"


def test_reader_sees_the_widget_but_not_the_campaigns_without_permission():
    """Lecteur reads documents and campaigns (README §4); the context agrees."""
    _running_campaign([UserFactory()])
    ctx = documents_dashboard_context(_reader(), timezone.localdate())
    assert ctx["documents_running_campaign_count"] == 1

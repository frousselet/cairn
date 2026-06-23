"""Tests for the unified To do / Doing / Done Kanban board."""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from compliance.constants import ActionPlanStatus, AssessmentStatus
from compliance.tests.factories import (
    ComplianceActionPlanFactory,
    ComplianceAssessmentFactory,
)
from core.kanban import DOING, DONE, TODO, build_kanban_columns
from risks.constants import ActionStatus
from risks.constants import AssessmentStatus as RiskAssessmentStatus
from risks.tests.factories import RiskAssessmentFactory, TreatmentActionFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def superuser():
    return UserFactory(is_superuser=True)


@pytest.fixture
def client(superuser):
    c = Client()
    c.force_login(superuser)
    return c


def _columns_by_key(user):
    return {col["key"]: col for col in build_kanban_columns(user)}


def _column_of(cols, title):
    """Return the column key holding the card with the given title, or None."""
    for col in cols.values():
        if any(card["title"] == title for card in col["cards"]):
            return col["key"]
    return None


def _titles(cols):
    return {card["title"] for col in cols.values() for card in col["cards"]}


def test_columns_are_todo_doing_done(superuser):
    cols = build_kanban_columns(superuser)
    assert [c["key"] for c in cols] == [TODO, DOING, DONE]


def test_items_land_in_expected_columns(superuser):
    todo_ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
    doing_ap = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_IMPLEMENT)
    done_ap = ComplianceActionPlanFactory(status=ActionPlanStatus.CLOSED)
    doing_ta = TreatmentActionFactory(status=ActionStatus.IN_PROGRESS)
    todo_audit = ComplianceAssessmentFactory(status=AssessmentStatus.PLANNED)
    done_ra = RiskAssessmentFactory(status=RiskAssessmentStatus.VALIDATED)

    cols = _columns_by_key(superuser)
    assert _column_of(cols, todo_ap.name) == TODO
    assert _column_of(cols, doing_ap.name) == DOING
    assert _column_of(cols, done_ap.name) == DONE
    assert _column_of(cols, doing_ta.description) == DOING
    assert _column_of(cols, todo_audit.name) == TODO
    assert _column_of(cols, done_ra.name) == DONE


def test_cancelled_and_archived_are_excluded(superuser):
    ap = ComplianceActionPlanFactory(status=ActionPlanStatus.CANCELLED)
    audit = ComplianceAssessmentFactory(status=AssessmentStatus.CANCELLED)
    ta = TreatmentActionFactory(status=ActionStatus.CANCELLED)
    ra = RiskAssessmentFactory(status=RiskAssessmentStatus.ARCHIVED)

    titles = _titles(_columns_by_key(superuser))
    assert ap.name not in titles
    assert audit.name not in titles
    assert ta.description not in titles
    assert ra.name not in titles


def test_card_carries_type_and_status(superuser):
    ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
    cols = _columns_by_key(superuser)
    card = next(c for c in cols[TODO]["cards"] if c["title"] == ap.name)
    assert card["type_key"] == "action_plan"
    assert card["type_icon"]
    assert card["status_label"]
    assert card["url"].startswith("/")


def test_view_returns_200(client):
    ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
    response = client.get(reverse("kanban"))
    assert response.status_code == 200


def test_view_requires_login():
    response = Client().get(reverse("kanban"))
    assert response.status_code == 302


def test_json_endpoint(client):
    ComplianceActionPlanFactory(status=ActionPlanStatus.TO_IMPLEMENT)
    response = client.get(reverse("kanban-board"))
    assert response.status_code == 200
    payload = response.json()
    assert [c["key"] for c in payload["columns"]] == [TODO, DOING, DONE]


def test_permission_gating_hides_unreadable_types():
    """A user without any read permission sees an empty board."""
    user = UserFactory()
    ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
    cols = build_kanban_columns(user)
    assert sum(c["count"] for c in cols) == 0

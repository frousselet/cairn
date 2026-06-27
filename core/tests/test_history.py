"""Tests for the unified history computation core (core.history)."""

import pytest

from accounts.tests.factories import UserFactory
from context.constants import RaciType, RoleType
from context.models import Responsibility, Role
from context.tests.factories import IssueFactory, ScopeFactory
from core.history import (
    EntryKind,
    ExtraSource,
    HistoryEntry,
    build_entry,
    build_timeline,
    classify_record,
    extra_source_for,
)

pytestmark = pytest.mark.django_db


def _latest(obj):
    """Most recent historical record of an instance."""
    return obj.history.order_by("-history_date", "-history_id").first()


def test_classify_create():
    scope = ScopeFactory()
    record = _latest(scope)
    assert record.history_type == "+"
    assert classify_record(record) is EntryKind.CREATE


def test_classify_update_regular_field():
    scope = ScopeFactory(name="Before")
    scope.name = "After"
    scope.save()
    record = _latest(scope)
    assert classify_record(record) is EntryKind.UPDATE
    entry = build_entry(record)
    fields = {c.field_code for c in entry.changes}
    assert "name" in fields
    # Hidden fields never surface as ordinary edits.
    assert not fields & {"version", "is_approved", "approved_by_id"}


def test_classify_transition_forward():
    scope = ScopeFactory()  # draft
    user = UserFactory()
    scope.transition_to("definition", user)
    record = _latest(scope)
    assert classify_record(record) is EntryKind.TRANSITION
    entry = build_entry(record)
    assert entry.kind is EntryKind.TRANSITION
    assert entry.from_state == "draft"
    assert entry.to_state == "definition"
    assert entry.is_refusal is False


def test_build_entry_transition_refusal_is_backward():
    # The scope lifecycle is forward-only; a backward move (refusal) is exercised
    # on a default-workflow entity that allows sending back (pending -> draft).
    issue = IssueFactory()
    user = UserFactory()
    issue.transition_to("pending", user)
    issue.transition_to("draft", user)  # send back to draft = backward
    record = _latest(issue)
    entry = build_entry(record)
    assert entry.kind is EntryKind.TRANSITION
    assert entry.from_state == "pending"
    assert entry.to_state == "draft"
    assert entry.is_refusal is True


def test_classify_approval_only_change():
    """An approval-field-only change (no lifecycle move) is an APPROVAL event."""
    scope = ScopeFactory()
    u1, u2 = UserFactory(), UserFactory()
    # On the standardised engine, approval is independent of the lifecycle step:
    # flipping is_approved leaves workflow_state untouched.
    scope.is_approved = True
    scope.approved_by = u1
    scope.save()
    assert scope.workflow_state == "draft"
    # Now change only the approver, leaving is_approved/workflow_state untouched.
    scope.approved_by = u2
    scope.save()
    record = _latest(scope)
    assert classify_record(record) is EntryKind.APPROVAL
    entry = build_entry(record)
    assert entry.kind is EntryKind.APPROVAL
    assert entry.approved is True


def test_snapshot_renders_foreign_key_as_label_not_uuid():
    """A creation snapshot shows the creator's name, not their raw UUID."""
    user = UserFactory()
    scope = ScopeFactory(created_by=user)
    creation = scope.history.filter(history_type="+").first()
    entry = build_entry(creation)
    created_by = next((c for c in entry.snapshot if c.field_code == "created_by"), None)
    assert created_by is not None
    assert str(created_by.new) == str(user)
    assert str(user.pk) not in str(created_by.new)


def test_build_timeline_orders_desc_and_limits():
    scope = ScopeFactory()
    for i in range(5):
        scope.name = f"Name {i}"
        scope.save()
    timeline = build_timeline(scope, limit=3)
    assert len(timeline) == 3
    dates = [e.history_date for e in timeline]
    assert dates == sorted(dates, reverse=True)


def test_build_timeline_merges_extra_entries():
    scope = ScopeFactory()
    base = _latest(scope)
    extra = ExtraSource(entries=(
        HistoryEntry(
            history_id="x",
            history_date=base.history_date,
            kind=EntryKind.TRANSITION,
            from_state="draft",
            to_state="pending",
            entity_label="Child",
        ),
    ))
    timeline = build_timeline(scope, extra=extra)
    assert any(e.entity_label == "Child" for e in timeline)


def test_extra_source_suppresses_generic_transitions():
    scope = ScopeFactory()
    user = UserFactory()
    scope.transition_to("definition", user)  # generic transition record
    extra = ExtraSource(entries=(), suppress_generic_transitions=True)
    timeline = build_timeline(scope, extra=extra)
    assert all(e.kind is not EntryKind.TRANSITION for e in timeline)


def test_as_dict_transition_shape():
    scope = ScopeFactory()
    user = UserFactory()
    scope.transition_to("definition", user)
    entry = build_entry(_latest(scope))
    data = entry.as_dict()
    assert data["kind"] == "transition"
    assert data["from_state"] == "draft"
    assert data["to_state"] == "definition"
    assert "is_refusal" in data
    # history_date is serialized as an ISO string for API/MCP portability.
    assert isinstance(data["history_date"], str)


def test_as_dict_update_shape():
    scope = ScopeFactory(name="Before")
    scope.name = "After"
    scope.save()
    data = build_entry(_latest(scope)).as_dict()
    assert data["kind"] == "update"
    assert any(c["field_code"] == "name" for c in data["changes"])


def test_role_extra_source_merges_responsibility_history():
    role = Role.objects.create(name="Role A", type=RoleType.GOVERNANCE)
    Responsibility.objects.create(
        role=role, description="Do the thing", raci_type=RaciType.RESPONSIBLE
    )
    extra = extra_source_for(role)
    assert extra is not None
    labels = {str(e.entity_label) for e in extra.entries if e.entity_label}
    assert "Responsibility" in labels

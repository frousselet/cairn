"""Tests for the JSON-driven, DB-backed lifecycle framework."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.tests.factories import PermissionFactory, UserFactory
from core.lifecycle import (
    LIFECYCLE_REGISTRY,
    LifecycleError,
    StepKind,
    clear_lifecycle_cache,
    get_lifecycle,
    lifecycle_from_json,
    lifecycle_to_json,
)
from core.models import LifecycleDefinition


def test_round_trip_preserves_every_registered_lifecycle():
    """to_json -> from_json reproduces each built-in lifecycle exactly."""
    for name, lc in LIFECYCLE_REGISTRY.items():
        rebuilt = lifecycle_from_json(name, lifecycle_to_json(lc))
        assert [s.code for s in rebuilt.steps] == [s.code for s in lc.steps]
        assert rebuilt.layout == lc.layout
        assert {
            (s.code, s.kind, s.counts_in_reports, s.linkable, s.deletable) for s in rebuilt.steps
        } == {
            (s.code, s.kind, s.counts_in_reports, s.linkable, s.deletable) for s in lc.steps
        }
        assert {
            (t.source, t.target, t.requires_comment, t.permission_action) for t in rebuilt.transitions
        } == {
            (t.source, t.target, t.requires_comment, t.permission_action) for t in lc.transitions
        }


def test_from_json_enforces_draft_and_archived_bookends():
    with pytest.raises(LifecycleError):  # no draft
        lifecycle_from_json("x", {"steps": [
            {"code": "a", "kind": "intermediate"}, {"code": "archived", "kind": "archived"},
        ], "transitions": []})
    with pytest.raises(LifecycleError):  # no archived
        lifecycle_from_json("x", {"steps": [{"code": "draft", "kind": "draft"}], "transitions": []})
    with pytest.raises(LifecycleError):  # transition to a missing step
        lifecycle_from_json("x", {"steps": [
            {"code": "draft", "kind": "draft"}, {"code": "archived", "kind": "archived"},
        ], "transitions": [{"source": "draft", "target": "ghost"}]})


def test_wildcard_source_and_kind_parsing():
    lc = lifecycle_from_json("x", {"steps": [
        {"code": "draft", "kind": "draft"},
        {"code": "live", "kind": "intermediate", "counts_in_reports": True},
        {"code": "archived", "kind": "archived"},
    ], "transitions": [
        {"source": "draft", "target": "live", "label": "Start"},
        {"source": "*", "target": "archived", "label": "Archive"},
    ]})
    assert lc.initial_step.code == "draft"
    assert lc.step("live").counts_in_reports is True
    # "*" is the ANY sentinel: archivable from any state.
    assert lc.find_transition("live", "archived") is not None


@pytest.mark.django_db
def test_db_definition_overrides_the_code_default():
    """get_lifecycle prefers a DB row over the code registry, and reflects edits."""
    clear_lifecycle_cache()
    row = LifecycleDefinition.objects.get(name="support_asset")
    assert "servicing" not in {s.code for s in get_lifecycle("support_asset").steps}
    row.definition["steps"].insert(-1, {
        "code": "servicing", "label": "Servicing", "kind": "intermediate", "counts_in_reports": True,
    })
    row.definition["transitions"].append({"source": "active", "target": "servicing", "label": "Service"})
    row.is_customized = True
    row.save()  # clears the cache
    assert "servicing" in {s.code for s in get_lifecycle("support_asset").steps}


@pytest.mark.django_db
def test_invalid_definition_falls_back_to_code_default():
    clear_lifecycle_cache()
    row = LifecycleDefinition.objects.get(name="support_asset")
    row.definition = {"steps": [], "transitions": []}  # invalid: no draft/archived
    LifecycleDefinition.objects.filter(pk=row.pk).update(definition=row.definition)  # bypass save/clean
    clear_lifecycle_cache()
    # Falls back to the registry default rather than raising.
    assert get_lifecycle("support_asset").initial_step.code == "draft"


@pytest.mark.django_db
def test_model_clean_rejects_a_lifecycle_without_a_draft():
    obj = LifecycleDefinition(name="broken", definition={
        "steps": [{"code": "archived", "kind": "archived"}], "transitions": [],
    })
    with pytest.raises(ValidationError):
        obj.clean()


@pytest.mark.django_db
def test_admin_list_and_edit_render(client):
    user = UserFactory()
    from accounts.tests.factories import GroupFactory
    group = GroupFactory()
    group.permissions.add(PermissionFactory(codename="system.config.read", module="system", feature="config", action="read"))
    group.users.add(user)
    client.force_login(user)
    assert client.get(reverse("core:lifecycle-list")).status_code == 200
    resp = client.get(reverse("core:lifecycle-edit", kwargs={"name": "support_asset"}))
    assert resp.status_code == 200
    assert resp.context["preview"] is not None

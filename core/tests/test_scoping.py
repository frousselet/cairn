# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Scope tenancy must hold on every surface, including for child rows.

A model that inherits its scopes from a parent (`scope_parent_lookup`) used
to be filtered only on list and detail surfaces. The generic workflow
transition endpoint, the generic history endpoint and the MCP list layer all
guarded on the presence of a `scopes` M2M, which a child row does not have,
and fell through to returning everything. These tests pin the three.
"""
import pytest
from django.urls import reverse

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from context.tests.factories import ScopeFactory
from core.scoping import object_in_scopes, resolve_scope_lookup


def _user_limited_to(scope, *codenames):
    """A non-superuser whose only group restricts them to `scope`.

    Allowed scopes come from group membership : a group with an empty
    `allowed_scopes` means unrestricted, so the group must name the scope.
    `codenames` are granted so a test reaches the scope guard instead of
    stopping at the permission check before it.
    """
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.allowed_scopes.set([scope])
    for codename in codenames:
        group.permissions.add(PermissionFactory(codename=codename))
    group.users.add(user)
    return user


@pytest.fixture
def two_perimeters(db):
    """A requirement in each of two disjoint scopes, and a user seeing only one."""
    mine, theirs = ScopeFactory(), ScopeFactory()
    fw_mine = FrameworkFactory()
    fw_mine.scopes.set([mine])
    fw_theirs = FrameworkFactory()
    fw_theirs.scopes.set([theirs])
    return {
        "mine": mine,
        "theirs": theirs,
        "req_mine": RequirementFactory(framework=fw_mine),
        "req_theirs": RequirementFactory(framework=fw_theirs),
    }


def test_child_model_declares_its_path_to_scope():
    from compliance.models import Requirement

    assert resolve_scope_lookup(Requirement) == "framework__scopes"


@pytest.mark.django_db
def test_object_in_scopes_follows_the_parent(two_perimeters):
    mine = [two_perimeters["mine"].id]

    assert object_in_scopes(two_perimeters["req_mine"], mine)
    assert not object_in_scopes(two_perimeters["req_theirs"], mine)


@pytest.mark.django_db
def test_a_row_with_no_scope_at_all_stays_visible(two_perimeters):
    """Scoping restricts what has been filed under a perimeter.

    It does not hide records nobody has filed yet, which is the behaviour the
    previous guard had and which this must not silently change.
    """
    orphan = RequirementFactory(framework=FrameworkFactory())
    orphan.framework.scopes.clear()

    assert object_in_scopes(orphan, [two_perimeters["mine"].id])


@pytest.mark.django_db
def test_mcp_list_does_not_leak_child_rows_across_scopes(two_perimeters):
    from mcp.tools import _filter_by_scopes
    from compliance.models import Requirement

    user = _user_limited_to(two_perimeters["mine"])

    visible = _filter_by_scopes(Requirement.objects.all(), user)

    assert two_perimeters["req_mine"] in visible
    assert two_perimeters["req_theirs"] not in visible


@pytest.mark.django_db
def test_history_endpoint_refuses_an_out_of_scope_child(client, two_perimeters):
    # The read permission is granted on purpose : without it the view returns
    # 403 before it ever reaches the scope guard, and the test proves nothing.
    user = _user_limited_to(two_perimeters["mine"], "compliance.requirement.read")
    client.force_login(user)

    url = reverse(
        "history:partial",
        kwargs={
            "app_label": "compliance",
            "model": "requirement",
            "pk": two_perimeters["req_theirs"].pk,
        },
    )

    assert client.get(url).status_code == 404

    ours = reverse(
        "history:partial",
        kwargs={
            "app_label": "compliance",
            "model": "requirement",
            "pk": two_perimeters["req_mine"].pk,
        },
    )
    assert client.get(ours).status_code == 200


@pytest.mark.django_db
def test_workflow_transition_refuses_an_out_of_scope_child(client, two_perimeters):
    user = _user_limited_to(two_perimeters["mine"])
    client.force_login(user)

    url = reverse(
        "workflow:transition",
        kwargs={
            "app_label": "compliance",
            "model": "requirement",
            "pk": two_perimeters["req_theirs"].pk,
        },
    )
    before = two_perimeters["req_theirs"].workflow_state

    response = client.post(url, {"target_status": "pending"})

    two_perimeters["req_theirs"].refresh_from_db()
    assert response.status_code == 404
    assert two_perimeters["req_theirs"].workflow_state == before

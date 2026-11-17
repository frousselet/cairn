# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A lifecycle transition asks for the permission to change the record.

A transition names the permission it needs (``permission_action``), or the
roles and users it is restricted to. Twenty-two lifecycles declared neither on
any of their transitions, and such a transition was "open" : allowed to anyone
who could reach the record. On the generic transition endpoint, which checks
nothing else, and on the MCP transition tools, which ask for the read
permission only, a reader (or a user with no permission on the module at all)
could put a scope in force, activate an asset or accept a risk.

``core.lifecycle.user_can_perform`` now treats an undeclared transition as a
change of the record : it asks for ``.update`` (or ``.approve``, which implies
it) on the entity.
"""

import pytest
from django.apps import apps
from django.urls import reverse

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from assets.tests.factories import EssentialAssetFactory
from context.models.base import BaseModel
from context.tests.factories import ScopeFactory
from core.lifecycle import (
    DEFAULT_PERMISSION_ACTIONS,
    Transition,
    resolve_lifecycle,
    user_can_perform,
)

pytestmark = pytest.mark.django_db


def _user_with(*codenames):
    """A user of an unrestricted group holding exactly these permissions."""
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    group.users.add(user)
    return user


def _complete_scope(**kwargs):
    scope = ScopeFactory(boundaries="No exclusion.", **kwargs)
    scope.managers.add(UserFactory())
    return scope


class TestTheRule:
    def test_an_undeclared_transition_asks_for_update_or_approve(self):
        scope = ScopeFactory()
        move = resolve_lifecycle(scope).find_transition("draft", "definition")
        assert move.permission_action == "" and not move.is_restricted

        assert not user_can_perform(move, scope, _user_with())
        assert not user_can_perform(move, scope, _user_with("context.scope.read"))
        # The permission of another module is not the one asked for.
        assert not user_can_perform(move, scope, _user_with("assets.essential_asset.update"))
        assert user_can_perform(move, scope, _user_with("context.scope.update"))
        assert user_can_perform(move, scope, _user_with("context.scope.approve"))
        assert user_can_perform(move, scope, UserFactory(is_superuser=True))
        assert DEFAULT_PERMISSION_ACTIONS == ("update", "approve")

    def test_a_declared_permission_is_the_one_asked_for(self):
        scope = ScopeFactory()
        move = Transition("in_force", source="validation", permission_action="approve")

        assert not user_can_perform(move, scope, _user_with("context.scope.update"))
        assert user_can_perform(move, scope, _user_with("context.scope.approve"))

    def test_a_restriction_to_users_still_decides_alone(self):
        """The owner named by a restricted transition needs no other permission."""
        scope = ScopeFactory()
        owner = _user_with()
        move = Transition("in_force", source="validation", allowed_users=lambda instance: [owner])

        assert user_can_perform(move, scope, owner)
        assert not user_can_perform(move, scope, _user_with("context.scope.update"))

    def test_nobody_is_not_a_user(self):
        scope = ScopeFactory()
        move = resolve_lifecycle(scope).find_transition("draft", "definition")

        assert not user_can_perform(move, scope, None)

    def test_every_entity_can_still_be_moved_by_who_may_change_it(self):
        """The rule must lock nobody out : for each model whose lifecycle has an
        undeclared transition, the permission it now asks for exists."""
        from accounts.constants import PERMISSION_REGISTRY

        codenames = {
            f"{module}.{feature}.{action}"
            for module, features in PERMISSION_REGISTRY.items()
            for feature, spec in features.items()
            for action in spec.get("actions", [])
        }
        locked = []
        for model in apps.get_models():
            if not (isinstance(model, type) and issubclass(model, BaseModel)):
                continue
            lifecycle = resolve_lifecycle(model)
            if not any(not t.permission_action and not t.is_restricted for t in lifecycle.transitions):
                continue
            namespace = model().workflow_perm_namespace
            if not any(f"{namespace}.{action}" in codenames for action in DEFAULT_PERMISSION_ACTIONS):
                locked.append(f"{model._meta.label} ({namespace})")
        assert locked == []


class TestTheGenericEndpoint:
    def _url(self, obj):
        return reverse(
            "workflow:transition",
            kwargs={"app_label": obj._meta.app_label, "model": obj._meta.model_name, "pk": obj.pk},
        )

    def test_a_user_with_no_permission_on_scopes_cannot_put_one_in_force(self, client):
        scope = _complete_scope(workflow_state="validation")
        client.force_login(_user_with("assets.essential_asset.read"))

        client.post(self._url(scope), {"target_status": "in_force"})

        scope.refresh_from_db()
        assert scope.workflow_state == "validation"

    def test_a_reader_cannot_move_nor_archive_a_scope(self, client):
        scope = _complete_scope()
        client.force_login(_user_with("context.scope.read"))

        for target in ("definition", "archived"):
            client.post(self._url(scope), {"target_status": target})
            scope.refresh_from_db()
            assert scope.workflow_state == "draft"

    def test_a_reader_cannot_activate_an_asset(self, client):
        asset = EssentialAssetFactory(workflow_state="identified")
        client.force_login(_user_with("assets.essential_asset.read"))

        client.post(self._url(asset), {"target_status": "active"})

        asset.refresh_from_db()
        assert asset.workflow_state == "identified"

    def test_who_may_change_the_record_moves_it(self, client):
        scope = _complete_scope()
        client.force_login(_user_with("context.scope.read", "context.scope.update"))

        client.post(self._url(scope), {"target_status": "definition"})

        scope.refresh_from_db()
        assert scope.workflow_state == "definition"


class TestTheOtherSurfaces:
    def test_the_lifecycle_bar_offers_a_reader_no_move(self, client):
        scope = _complete_scope()
        client.force_login(_user_with("context.scope.read"))

        response = client.get(reverse("context:scope-detail", kwargs={"pk": scope.pk}))

        assert response.status_code == 200
        # No step of the bar is a button : the reader sees the path, not a move.
        assert "lc-step--action" not in response.content.decode()

    def test_the_lifecycle_bar_offers_an_editor_the_next_step(self, client):
        scope = _complete_scope()
        client.force_login(_user_with("context.scope.read", "context.scope.update"))

        html = client.get(reverse("context:scope-detail", kwargs={"pk": scope.pk})).content.decode()

        assert "lc-step--action" in html
        assert 'name="target_status" value="definition"' in html

    def test_the_mcp_transition_tool_refuses_a_reader(self):
        """The tool is registered with the read permission : the move itself asks more."""
        from mcp.tools import _transition_handler

        scope = _complete_scope()
        reader = _user_with("context.scope.read")

        result = _transition_handler(type(scope), "context.scope")(
            reader, {"id": str(scope.pk), "target_state": "definition"},
        )

        scope.refresh_from_db()
        assert scope.workflow_state == "draft"
        assert "error" in str(result).lower() or "not" in str(result).lower()

    def test_the_mcp_tool_lists_a_reader_no_move(self):
        from mcp.tools import _allowed_transitions_handler

        scope = _complete_scope()

        listed = _allowed_transitions_handler(type(scope), "context.scope")(
            _user_with("context.scope.read"), {"id": str(scope.pk)},
        )

        assert not listed.get("transitions")

    def test_the_rest_api_refuses_a_reader(self):
        from rest_framework.test import APIClient

        scope = _complete_scope()
        api = APIClient()
        api.force_authenticate(_user_with("context.scope.read"))

        response = api.post(
            f"/api/v1/context/scopes/{scope.pk}/transition/", {"target_state": "definition"}, format="json",
        )

        scope.refresh_from_db()
        assert response.status_code == 403
        assert scope.workflow_state == "draft"

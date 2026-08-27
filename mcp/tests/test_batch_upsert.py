# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""``batch_create_*`` supports an idempotent upsert via ``match_on`` so a
partially failed import can be replayed without creating duplicates."""

import pytest

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from assets.models import Supplier
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db

CREATE = "assets.supplier.create"
OVERRIDE = "system.data_import.override_dates"


def _server_user(perms):
    srv = McpServer()
    register_all_tools(srv)
    user = UserFactory()
    group = GroupFactory()
    for codename in perms:
        group.permissions.add(PermissionFactory(codename=codename))
    group.users.add(user)
    return srv, user


class TestBatchUpsert:
    def test_create_only_without_match_on_duplicates(self):
        srv, user = _server_user([CREATE])
        handler = srv.get_tool("batch_create_suppliers")["handler"]
        item = {"name": "Acme", "owner_id": str(user.pk), "criticality": "high"}
        handler(user, {"items": [item]})
        handler(user, {"items": [item]})
        # Without match_on, replaying the batch duplicates the row (the problem
        # match_on solves).
        assert Supplier.objects.filter(name="Acme").count() == 2

    def test_match_on_updates_instead_of_duplicating(self):
        srv, user = _server_user([CREATE])
        handler = srv.get_tool("batch_create_suppliers")["handler"]
        first = handler(user, {
            "items": [{"name": "Acme", "owner_id": str(user.pk), "criticality": "low"}],
            "match_on": ["name"],
        })
        assert first["created"] == 1 and first["updated"] == 0
        second = handler(user, {
            "items": [{"name": "Acme", "owner_id": str(user.pk), "criticality": "critical"}],
            "match_on": ["name"],
        })
        assert second["created"] == 0 and second["updated"] == 1
        assert Supplier.objects.filter(name="Acme").count() == 1
        assert Supplier.objects.get(name="Acme").criticality == "critical"

    def test_missing_match_on_value_errors_the_item(self):
        srv, user = _server_user([CREATE])
        handler = srv.get_tool("batch_create_suppliers")["handler"]
        out = handler(user, {
            "items": [{"owner_id": str(user.pk), "criticality": "low"}],
            "match_on": ["name"],
        })
        assert out["errors"] == 1
        assert out["created"] == 0

    def test_unknown_match_on_field_rejects_call(self):
        srv, user = _server_user([CREATE])
        handler = srv.get_tool("batch_create_suppliers")["handler"]
        out = handler(user, {
            "items": [{"name": "Acme", "owner_id": str(user.pk)}],
            "match_on": ["not_a_field"],
        })
        assert out.get("isError")

    def test_timestamps_ignored_is_flagged(self):
        srv, user = _server_user([CREATE])  # no override permission
        handler = srv.get_tool("batch_create_suppliers")["handler"]
        out = handler(user, {"items": [
            {"name": "Legacy", "owner_id": str(user.pk), "created_at": "2019-01-01"}
        ]})
        assert out["created"] == 1
        assert out["timestamps_ignored"] == 1
        assert "warning" in out

    def test_timestamps_not_flagged_with_permission(self):
        srv, user = _server_user([CREATE, OVERRIDE])
        handler = srv.get_tool("batch_create_suppliers")["handler"]
        out = handler(user, {"items": [
            {"name": "Legacy2", "owner_id": str(user.pk), "created_at": "2019-01-01"}
        ]})
        assert out["created"] == 1
        assert "timestamps_ignored" not in out

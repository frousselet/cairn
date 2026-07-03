"""The MCP create/batch tools may preserve legacy created_at/updated_at only
for a caller holding ``system.data_import.override_dates``."""

from datetime import date

import pytest
from django.utils import timezone

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from assets.models import Supplier
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db

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


class TestTimestampOverride:
    def test_created_at_preserved_with_permission(self):
        srv, user = _server_user(["assets.supplier.create", OVERRIDE])
        handler = srv.get_tool("create_supplier")["handler"]
        handler(user, {"name": "Legacy Co", "owner_id": str(user.pk),
                       "created_at": "2020-01-15T00:00:00Z"})
        supplier = Supplier.objects.get(name="Legacy Co")
        assert timezone.localtime(supplier.created_at).date() == date(2020, 1, 15)

    def test_created_at_ignored_without_permission(self):
        srv, user = _server_user(["assets.supplier.create"])
        handler = srv.get_tool("create_supplier")["handler"]
        handler(user, {"name": "Normal Co", "owner_id": str(user.pk),
                       "created_at": "2020-01-15T00:00:00Z"})
        supplier = Supplier.objects.get(name="Normal Co")
        # Left to auto_now_add (import date), not the supplied 2020 value.
        assert timezone.localtime(supplier.created_at).year >= 2026

    def test_batch_created_at_preserved_with_permission(self):
        srv, user = _server_user(["assets.supplier.create", OVERRIDE])
        handler = srv.get_tool("batch_create_suppliers")["handler"]
        out = handler(user, {"items": [
            {"name": "Batch Co", "owner_id": str(user.pk), "created_at": "2019-03-04"}
        ]})
        assert out["created"] == 1
        supplier = Supplier.objects.get(name="Batch Co")
        assert timezone.localtime(supplier.created_at).year == 2019

    def test_superuser_can_override(self):
        srv = McpServer()
        register_all_tools(srv)
        user = UserFactory(is_superuser=True)
        handler = srv.get_tool("create_supplier")["handler"]
        handler(user, {"name": "SU Co", "owner_id": str(user.pk), "created_at": "2018-06-01"})
        supplier = Supplier.objects.get(name="SU Co")
        assert timezone.localtime(supplier.created_at).year == 2018

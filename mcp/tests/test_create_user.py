"""The MCP ``create_user`` tool provisions accounts via the invitation flow
(unusable password, returned activation link) and is gated by
``system.users.create``. ``get_me`` surfaces the caller's capabilities."""

import pytest

from accounts.models import Group, User
from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db

CREATE = "system.users.create"
OVERRIDE = "system.data_import.override_dates"


def _server_user(perms=(), is_superuser=False):
    srv = McpServer()
    register_all_tools(srv)
    user = UserFactory(is_superuser=is_superuser)
    if perms:
        group = GroupFactory()
        for codename in perms:
            group.permissions.add(PermissionFactory(codename=codename))
        group.users.add(user)
    return srv, user


class TestCreateUser:
    def test_requires_permission(self):
        srv, user = _server_user()  # no permission
        handler = srv.get_tool("create_user")["handler"]
        out = handler(user, {"email": "new@corp.example", "last_name": "Doe"})
        assert out.get("isError")
        assert not User.objects.filter(email="new@corp.example").exists()

    def test_creates_invited_user_with_unusable_password(self):
        srv, user = _server_user([CREATE])
        handler = srv.get_tool("create_user")["handler"]
        out = handler(user, {"email": "jane@corp.example", "last_name": "Doe",
                             "first_name": "Jane"})
        assert "error" not in out
        created = User.objects.get(email="jane@corp.example")
        assert created.has_usable_password() is False
        assert created.created_by_id == user.pk
        assert out["id"] == str(created.pk)
        assert "activation_url" in out and out["activation_url"]

    def test_assigns_groups_by_name(self):
        srv, user = _server_user([CREATE])
        Group.objects.get_or_create(name="Contributeur")
        handler = srv.get_tool("create_user")["handler"]
        out = handler(user, {"email": "bob@corp.example", "last_name": "Ross",
                             "groups": ["Contributeur"]})
        assert not out.get("isError")
        created = User.objects.get(email="bob@corp.example")
        assert list(created.custom_groups.values_list("name", flat=True)) == ["Contributeur"]

    def test_unknown_group_is_rejected(self):
        srv, user = _server_user([CREATE])
        handler = srv.get_tool("create_user")["handler"]
        out = handler(user, {"email": "x@corp.example", "last_name": "X",
                             "groups": ["Nope-no-such-group"]})
        assert out.get("isError")
        assert not User.objects.filter(email="x@corp.example").exists()

    def test_duplicate_email_is_rejected(self):
        srv, user = _server_user([CREATE])
        UserFactory(email="dup@corp.example")
        handler = srv.get_tool("create_user")["handler"]
        out = handler(user, {"email": "dup@corp.example", "last_name": "Twin"})
        assert out.get("isError")

    def test_missing_required_fields(self):
        srv, user = _server_user([CREATE])
        handler = srv.get_tool("create_user")["handler"]
        out = handler(user, {"email": "noname@corp.example"})
        assert out.get("isError")


class TestGetMeCapabilities:
    def test_flags_false_without_permissions(self):
        srv, user = _server_user()
        handler = srv.get_tool("get_me")["handler"]
        out = handler(user, {})
        assert out["can_override_import_dates"] is False
        assert out["can_create_users"] is False
        assert out["is_superuser"] is False

    def test_flags_true_with_permissions(self):
        srv, user = _server_user([CREATE, OVERRIDE])
        handler = srv.get_tool("get_me")["handler"]
        out = handler(user, {})
        assert out["can_override_import_dates"] is True
        assert out["can_create_users"] is True

    def test_superuser_flags_true(self):
        srv, user = _server_user(is_superuser=True)
        handler = srv.get_tool("get_me")["handler"]
        out = handler(user, {})
        assert out["can_override_import_dates"] is True
        assert out["can_create_users"] is True

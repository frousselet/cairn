"""Tests for the notification DRF endpoints and MCP tools (own-data)."""

import pytest
from django.test import Client

from accounts.models import Notification
from accounts.notifications import notify_lifecycle_submitted
from accounts.tests.factories import UserFactory
from context.tests.factories import IssueFactory, ScopeFactory

pytestmark = pytest.mark.django_db


def _notified_user():
    """A user holding one notification (as manager of the issue's scope)."""
    user = UserFactory()
    scope = ScopeFactory()
    scope.managers.add(user)
    issue = IssueFactory()
    issue.scopes.set([scope])
    notify_lifecycle_submitted(issue, actor=UserFactory())
    return user, issue


class TestNotificationAPI:
    def _client(self, user):
        client = Client()
        client.force_login(user)
        return client

    def test_login_required(self):
        resp = Client().get("/api/v1/notifications/")
        assert resp.status_code in (401, 403)

    def test_lists_own_notifications_only(self):
        user, _ = _notified_user()
        other = UserFactory()
        resp = self._client(other).get("/api/v1/notifications/")
        assert resp.status_code == 200
        payload = resp.json()["data"]
        items = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
        assert items == []

        resp = self._client(user).get("/api/v1/notifications/")
        payload = resp.json()["data"]
        items = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
        assert len(items) == 1
        assert items[0]["is_read"] is False

    def test_unread_count(self):
        user, _ = _notified_user()
        resp = self._client(user).get("/api/v1/notifications/unread_count/")
        assert resp.status_code == 200
        assert resp.json()["data"]["unread"] == 1

    def test_mark_read(self):
        user, _ = _notified_user()
        notification = Notification.objects.get(recipient=user)
        resp = self._client(user).post(
            f"/api/v1/notifications/{notification.pk}/mark_read/"
        )
        assert resp.status_code == 200
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_cannot_mark_someone_elses_notification(self):
        user, _ = _notified_user()
        notification = Notification.objects.get(recipient=user)
        resp = self._client(UserFactory()).post(
            f"/api/v1/notifications/{notification.pk}/mark_read/"
        )
        assert resp.status_code == 404
        notification.refresh_from_db()
        assert notification.is_read is False

    def test_mark_all_read(self):
        user, _ = _notified_user()
        resp = self._client(user).post("/api/v1/notifications/mark_all_read/")
        assert resp.status_code == 200
        assert resp.json()["data"]["marked_read"] == 1
        assert not user.notifications.filter(is_read=False).exists()


class TestNotificationMCPTools:
    def setup_method(self):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        self.srv = McpServer()
        register_all_tools(self.srv)

    def _call(self, user, name, arguments=None):
        import json

        result = self.srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }), user)
        return json.loads(result["result"]["content"][0]["text"])

    def test_list_notifications(self):
        user, _ = _notified_user()
        result = self._call(user, "list_notifications")
        assert result["unread"] == 1
        assert len(result["notifications"]) == 1
        assert result["notifications"][0]["is_read"] is False

    def test_list_unread_only(self):
        user, _ = _notified_user()
        Notification.objects.filter(recipient=user).update(is_read=True)
        result = self._call(user, "list_notifications", {"unread_only": True})
        assert result["notifications"] == []
        assert result["unread"] == 0

    def test_mark_notification_read(self):
        user, _ = _notified_user()
        notification = Notification.objects.get(recipient=user)
        result = self._call(user, "mark_notification_read", {"id": str(notification.pk)})
        assert result["is_read"] is True
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_mark_someone_elses_notification_fails(self):
        user, _ = _notified_user()
        notification = Notification.objects.get(recipient=user)
        result = self._call(UserFactory(), "mark_notification_read", {"id": str(notification.pk)})
        assert "error" in result

    def test_mark_all_notifications_read(self):
        user, _ = _notified_user()
        result = self._call(user, "mark_all_notifications_read")
        assert result["marked_read"] == 1

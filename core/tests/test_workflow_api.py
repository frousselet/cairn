"""Tests for the lifecycle transition surfaces: DRF endpoint and MCP tools (phase 5).

Exercised through the Issue entity (default workflow, `context.issue` permissions).
"""

import json

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.tests.factories import IssueFactory

pytestmark = pytest.mark.django_db


def _data(response):
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


def _user_with_perms(*codenames):
    user = UserFactory()
    group = GroupFactory()
    for codename in codenames:
        module, feature, action = codename.split(".")
        perm = PermissionFactory(
            codename=codename, module=module, feature=feature, action=action,
        )
        group.permissions.add(perm)
    group.users.add(user)
    return user


class TestTransitionEndpoint:
    def setup_method(self):
        self.client = APIClient()
        self.superuser = UserFactory(is_superuser=True)

    def _url(self, issue):
        return f"/api/v1/context/issues/{issue.pk}/transition/"

    def test_get_lists_allowed_transitions(self):
        self.client.force_authenticate(self.superuser)
        issue = IssueFactory()
        response = self.client.get(self._url(issue))
        assert response.status_code == 200
        payload = _data(response)
        assert payload["workflow_state"] == "draft"
        assert [t["target"] for t in payload["allowed_transitions"]] == ["pending"]

    def test_get_filters_by_caller_permissions(self):
        user = _user_with_perms("context.issue.read", "context.issue.update")
        self.client.force_authenticate(user)
        issue = IssueFactory()
        issue.transition_to("pending")
        response = self.client.get(self._url(issue))
        targets = {t["target"] for t in _data(response)["allowed_transitions"]}
        # Send back to draft (update) yes; Validate (approve) filtered out.
        assert targets == {"draft"}

    def test_post_submits_draft(self):
        self.client.force_authenticate(self.superuser)
        issue = IssueFactory()
        response = self.client.post(
            self._url(issue), {"target_state": "pending"}, format="json",
        )
        assert response.status_code == 200
        issue.refresh_from_db()
        assert issue.workflow_state == "pending"

    def test_post_validate_requires_approve_permission(self):
        user = _user_with_perms("context.issue.read", "context.issue.update")
        self.client.force_authenticate(user)
        issue = IssueFactory()
        issue.transition_to("pending")
        response = self.client.post(
            self._url(issue), {"target_state": "validated"}, format="json",
        )
        assert response.status_code == 403
        issue.refresh_from_db()
        assert issue.workflow_state == "pending"

    def test_post_validate_stamps_approval(self):
        self.client.force_authenticate(self.superuser)
        issue = IssueFactory()
        issue.transition_to("pending")
        response = self.client.post(
            self._url(issue), {"target_state": "validated"}, format="json",
        )
        assert response.status_code == 200
        issue.refresh_from_db()
        assert issue.workflow_state == "validated"
        assert issue.is_approved is True
        assert issue.approved_by == self.superuser

    def test_post_illegal_transition_is_400(self):
        self.client.force_authenticate(self.superuser)
        issue = IssueFactory()
        response = self.client.post(
            self._url(issue), {"target_state": "validated"}, format="json",
        )
        assert response.status_code == 400
        issue.refresh_from_db()
        assert issue.workflow_state == "draft"

    def test_post_missing_target_is_400(self):
        self.client.force_authenticate(self.superuser)
        issue = IssueFactory()
        response = self.client.post(self._url(issue), {}, format="json")
        assert response.status_code == 400

    def test_list_filter_by_workflow_state(self):
        self.client.force_authenticate(self.superuser)
        IssueFactory()  # draft
        validated = IssueFactory(is_approved=True)
        response = self.client.get("/api/v1/context/issues/?workflow_state=validated")
        payload = _data(response)
        items = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
        assert [item["id"] for item in items] == [str(validated.pk)]


class TestTransitionMCPTools:
    def setup_method(self):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        self.srv = McpServer()
        register_all_tools(self.srv)
        self.superuser = UserFactory(is_superuser=True)

    def _call(self, user, name, arguments=None):
        result = self.srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }), user)
        return json.loads(result["result"]["content"][0]["text"])

    def test_generic_tools_are_registered(self):
        assert "transition_issue" in self.srv._tools
        assert "issue_allowed_transitions" in self.srv._tools
        assert "transition_risk" in self.srv._tools
        # Bespoke status-machine tools are not clobbered.
        assert "transition_management_review" in self.srv._tools
        assert "action_plan_allowed_transitions" in self.srv._tools

    def test_transition_happy_path(self):
        issue = IssueFactory()
        result = self._call(
            self.superuser, "transition_issue",
            {"id": str(issue.pk), "target_state": "pending"},
        )
        assert result["workflow_state"] == "pending"
        assert result["previous_state"] == "draft"
        issue.refresh_from_db()
        assert issue.workflow_state == "pending"

    def test_allowed_transitions(self):
        issue = IssueFactory()
        issue.transition_to("pending")
        result = self._call(
            self.superuser, "issue_allowed_transitions", {"id": str(issue.pk)},
        )
        assert result["workflow_state"] == "pending"
        assert {t["target"] for t in result["allowed_transitions"]} == {"draft", "validated"}

    def test_illegal_transition_errors(self):
        issue = IssueFactory()
        result = self._call(
            self.superuser, "transition_issue",
            {"id": str(issue.pk), "target_state": "archived"},
        )
        assert "error" in result

    def test_validate_requires_approve_permission(self):
        user = _user_with_perms("context.issue.read", "context.issue.update")
        issue = IssueFactory()
        issue.transition_to("pending")
        result = self._call(
            user, "transition_issue",
            {"id": str(issue.pk), "target_state": "validated"},
        )
        assert "error" in result
        issue.refresh_from_db()
        assert issue.workflow_state == "pending"

    def test_validate_with_permission_stamps(self):
        issue = IssueFactory()
        issue.transition_to("pending")
        result = self._call(
            self.superuser, "transition_issue",
            {"id": str(issue.pk), "target_state": "validated"},
        )
        assert result["workflow_state"] == "validated"
        issue.refresh_from_db()
        assert issue.is_approved is True
        assert issue.approved_by == self.superuser



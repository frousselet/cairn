"""Tests for the unified ``kanban_board`` MCP tool."""

import json

import pytest

from accounts.tests.factories import UserFactory
from compliance.constants import ActionPlanStatus
from compliance.tests.factories import ComplianceActionPlanFactory
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db


def _call_tool(srv, user, tool_name, arguments):
    result = srv.handle_request(json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }), user)
    raw = result["result"]["content"][0]["text"]
    return json.loads(raw)


class TestKanbanBoardTool:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_returns_three_columns(self):
        ComplianceActionPlanFactory(status=ActionPlanStatus.TO_IMPLEMENT)
        data = _call_tool(self.srv, self.user, "kanban_board", {})
        assert [c["key"] for c in data["columns"]] == ["todo", "doing", "done"]

    def test_card_is_serialisable(self):
        ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        data = _call_tool(self.srv, self.user, "kanban_board", {})
        todo = next(c for c in data["columns"] if c["key"] == "todo")
        assert todo["count"] >= 1
        card = todo["cards"][0]
        # due_date must be a plain string (or null), never a date object.
        assert card["due_date"] is None or isinstance(card["due_date"], str)
        assert card["type_key"]

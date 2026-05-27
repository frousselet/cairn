"""MCP tests for the risks module."""

import json

import pytest

from accounts.tests.factories import UserFactory
from mcp.server import McpServer
from mcp.tools import register_all_tools
from risks.models import RiskAcceptance
from risks.tests.factories import RiskFactory


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


class TestRiskAcceptanceApproveMCP:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def _make_acceptance(self):
        risk = RiskFactory()
        return RiskAcceptance.objects.create(
            risk=risk, justification="Approve me", status="active",
        )

    def test_approve_tool_is_registered(self):
        assert "approve_risk_acceptance" in self.srv._tools

    def test_approve_sets_approval_fields(self):
        acceptance = self._make_acceptance()
        assert acceptance.is_approved is False
        result = _call_tool(
            self.srv, self.user, "approve_risk_acceptance",
            {"id": str(acceptance.pk)},
        )
        assert "error" not in result, result
        acceptance.refresh_from_db()
        assert acceptance.is_approved is True
        assert acceptance.approved_by == self.user
        assert acceptance.approved_at is not None

    def test_approve_unknown_id_returns_error(self):
        import uuid
        result = _call_tool(
            self.srv, self.user, "approve_risk_acceptance",
            {"id": str(uuid.uuid4())},
        )
        assert "error" in result

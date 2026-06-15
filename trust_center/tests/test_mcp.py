import json

import pytest

from accounts.tests.factories import UserFactory
from compliance.tests.factories import FrameworkFactory
from mcp.server import McpServer
from mcp.tools import register_all_tools
from trust_center.constants import PublicationState
from trust_center.tests.factories import validate_framework

pytestmark = pytest.mark.django_db


def _call(srv, user, name, arguments):
    result = srv.handle_request(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        ),
        user,
    )
    raw = result["result"]["content"][0]["text"]
    return json.loads(raw)


class TestTrustCenterMcp:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def test_tools_registered(self):
        for name in [
            "get_trust_center_settings",
            "update_trust_center_settings",
            "create_trust_center_certification",
            "list_trust_center_certifications",
            "transition_trust_center_certification",
            "create_trust_center_subprocessor",
            "create_trust_center_measure",
            "create_trust_center_document",
        ]:
            assert name in self.srv._tools

    def test_settings_roundtrip(self):
        out = _call(
            self.srv,
            self.user,
            "update_trust_center_settings",
            {"is_published": True, "headline": "Trust", "theme_accent": "#1E3A8A"},
        )
        assert out["is_published"] is True
        assert out["headline"] == "Trust"
        got = _call(self.srv, self.user, "get_trust_center_settings", {})
        assert got["headline"] == "Trust"

    def test_invalid_theme_rejected(self):
        out = _call(
            self.srv,
            self.user,
            "update_trust_center_settings",
            {"theme_accent": "not-a-colour"},
        )
        assert "error" in json.dumps(out).lower()

    def test_create_and_publish_certification(self):
        fw = validate_framework(FrameworkFactory())
        created = _call(
            self.srv,
            self.user,
            "create_trust_center_certification",
            {"framework": str(fw.pk), "public_label": "ISO 27001"},
        )
        assert "error" not in created
        assert created["public_label"] == "ISO 27001"
        assert created["workflow_state"] == "draft"

        transitioned = _call(
            self.srv,
            self.user,
            "transition_trust_center_certification",
            {"id": created["id"], "target_state": PublicationState.PUBLISHED},
        )
        assert transitioned["workflow_state"] == PublicationState.PUBLISHED

        listed = _call(self.srv, self.user, "list_trust_center_certifications", {})
        assert any(row["id"] == created["id"] for row in listed["items"])

    def test_permission_denied_for_plain_user(self):
        plain = UserFactory()
        out = _call(
            self.srv, plain, "create_trust_center_measure", {"title": "X"}
        )
        assert "Permission denied" in json.dumps(out)

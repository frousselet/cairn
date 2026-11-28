# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""MCP Apps (``io.modelcontextprotocol/ui``) : the tools that name an app, the
``ui://`` resources, the structured result the app draws, and the heat map."""

import json

import pytest

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.tests.factories import ScopeFactory
from mcp.server import MODERN_PROTOCOL_VERSION, UI_EXTENSION, McpServer
from mcp.tools import register_all_tools
from mcp.ui_apps import MIME_TYPE

pytestmark = pytest.mark.django_db

UI = {"extensions": {UI_EXTENSION: {"mimeTypes": [MIME_TYPE]}}}


@pytest.fixture
def server():
    srv = McpServer()
    register_all_tools(srv)
    return srv


def _ask(server, user, method, params=None, capabilities=None):
    params = dict(params or {})
    params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientCapabilities": capabilities if capabilities is not None else {},
    }
    return server.handle_request({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, user)


def _risk(scope, likelihood, impact, **kwargs):
    from risks.tests.factories import RiskAssessmentFactory, RiskFactory

    assessment = kwargs.pop("assessment", None) or RiskAssessmentFactory(scope=scope)
    return RiskFactory(assessment=assessment, current_likelihood=likelihood, current_impact=impact, **kwargs)


class TestDeclaration:
    def test_the_extension_is_advertised(self, server):
        user = UserFactory(is_superuser=True)
        extensions = _ask(server, user, "server/discover")["result"]["capabilities"]["extensions"]
        assert extensions[UI_EXTENSION] == {"mimeTypes": [MIME_TYPE]}

    def test_a_tool_names_its_app_to_a_client_that_shows_apps(self, server):
        user = UserFactory(is_superuser=True)
        tools = {t["name"]: t for t in _ask(server, user, "tools/list", capabilities=UI)["result"]["tools"]}
        assert tools["get_risk_heatmap"]["_meta"]["ui"]["resourceUri"] == "ui://cairn/risk-heatmap"
        assert tools["get_framework_compliance_summary"]["_meta"]["ui"]["resourceUri"] == "ui://cairn/compliance-summary"
        assert "_meta" not in tools["list_risks"]
        plain = {t["name"]: t for t in _ask(server, user, "tools/list")["result"]["tools"]}
        assert "_meta" not in plain["get_risk_heatmap"]


class TestResources:
    @pytest.mark.parametrize("uri", ["ui://cairn/risk-heatmap", "ui://cairn/compliance-summary"])
    def test_an_app_is_a_self_contained_page(self, server, uri):
        user = UserFactory(is_superuser=True)
        result = _ask(server, user, "resources/read", {"uri": uri})["result"]
        (content,) = result["contents"]
        assert content["mimeType"] == MIME_TYPE and content["uri"] == uri
        html = content["text"]
        assert html.startswith("<!DOCTYPE html>")
        assert "ui/initialize" in html and "ui/notifications/initialized" in html
        assert "src=" not in html and "href=" not in html and "@import" not in html
        assert "innerHTML" not in html
        uris = {r["uri"] for r in _ask(server, user, "resources/list")["result"]["resources"]}
        assert uri in uris

    def test_an_app_speaks_the_language_of_its_reader(self, server):
        user = UserFactory(is_superuser=True, language="fr")
        html = _ask(server, user, "resources/read", {"uri": "ui://cairn/risk-heatmap"})["result"]["contents"][0]["text"]
        assert '<html lang="fr">' in html
        assert "Vraisemblance" in html

    def test_an_unknown_app_is_invalid_params(self, server):
        user = UserFactory(is_superuser=True)
        assert _ask(server, user, "resources/read", {"uri": "ui://cairn/nothing"})["error"]["code"] == -32602


class TestHeatmap:
    def test_the_result_is_structured_for_the_app(self, server):
        scope = ScopeFactory()
        _risk(scope, 5, 4)
        _risk(scope, 5, 4)
        _risk(scope, 1, 2)
        user = UserFactory(is_superuser=True)
        result = _ask(server, user, "tools/call", {"name": "get_risk_heatmap", "arguments": {}}, UI)["result"]
        data = result["structuredContent"]
        assert json.loads(result["content"][0]["text"]) == data
        assert data["rated"] == 3 and data["likelihood_max"] == 5 and data["impact_max"] == 5
        top = data["cells"][0]
        assert (top["likelihood"], top["impact"], top["count"]) == (5, 4, 2)

    def test_the_levels_are_those_of_the_risk_criteria(self, server):
        from risks.models import RiskCriteria, RiskLevel, ScaleLevel
        from risks.tests.factories import RiskAssessmentFactory, RiskFactory

        scope = ScopeFactory()
        criteria = RiskCriteria.objects.create(name="Voltara criteria", risk_matrix={"2,4": 3, "1,1": 1})
        criteria.scopes.add(scope)
        for level, name, colour in ((1, "Acceptable", "#4caf50"), (3, "Critical", "#b71c1c")):
            RiskLevel.objects.create(criteria=criteria, level=level, name=name, color=colour)
        for scale_type in ("likelihood", "impact"):
            for level in range(1, 5):
                ScaleLevel.objects.create(criteria=criteria, scale_type=scale_type, level=level, name=str(level))
        assessment = RiskAssessmentFactory(scope=scope, risk_criteria=criteria)
        RiskFactory(assessment=assessment, current_likelihood=2, current_impact=4)
        user = UserFactory(is_superuser=True)
        data = _ask(server, user, "tools/call", {"name": "get_risk_heatmap", "arguments": {}}, UI)[
            "result"]["structuredContent"]
        (cell,) = data["cells"]
        assert cell["level"] == 3
        levels = {level["level"]: level for level in data["levels"]}
        assert levels[3]["name"] == "Critical" and levels[3]["color"] == "#b71c1c"
        assert levels[3]["text_color"].startswith("#")
        assert (data["likelihood_max"], data["impact_max"]) == (4, 4)
        assert data["criteria"]["name"] == "Voltara criteria" and data["mixed_criteria"] is False

    def test_risks_under_several_criteria_carry_no_level(self, server):
        from risks.models import RiskCriteria
        from risks.tests.factories import RiskAssessmentFactory, RiskFactory

        scope = ScopeFactory()
        for name in ("First", "Second"):
            criteria = RiskCriteria.objects.create(name=name, risk_matrix={"3,3": 2})
            RiskFactory(assessment=RiskAssessmentFactory(scope=scope, risk_criteria=criteria),
                        current_likelihood=3, current_impact=3)
        user = UserFactory(is_superuser=True)
        data = _ask(server, user, "tools/call", {"name": "get_risk_heatmap", "arguments": {}}, UI)[
            "result"]["structuredContent"]
        assert data["mixed_criteria"] is True and data["levels"] == [] and data["criteria"] is None
        assert [cell["level"] for cell in data["cells"]] == [None]
        assert data["cells"][0]["count"] == 2

    def test_without_apps_the_result_stays_text(self, server):
        user = UserFactory(is_superuser=True)
        result = _ask(server, user, "tools/call", {"name": "get_risk_heatmap", "arguments": {}})["result"]
        assert "structuredContent" not in result

    def test_risks_out_of_reach_are_not_counted(self, server):
        mine, other = ScopeFactory(), ScopeFactory()
        _risk(mine, 3, 3)
        _risk(other, 4, 4)
        user = UserFactory()
        group = GroupFactory()
        group.permissions.add(PermissionFactory(codename="risks.risk.read"))
        group.allowed_scopes.add(mine)
        group.users.add(user)
        result = _ask(server, user, "tools/call", {"name": "get_risk_heatmap", "arguments": {}}, UI)["result"]
        data = result["structuredContent"]
        assert data["rated"] == 1
        assert [(c["likelihood"], c["impact"]) for c in data["cells"]] == [(3, 3)]

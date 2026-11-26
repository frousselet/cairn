# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Skills over MCP (``io.modelcontextprotocol/skills``) : the catalogue, its
wire format, the organization's skills replacing the shipped ones, and the
shipped skills naming only tools that exist."""

import hashlib
import json
import re

import pytest

from accounts.tests.factories import UserFactory
from mcp import skills
from mcp.models import McpSkill
from mcp.server import MODERN_PROTOCOL_VERSION, SKILLS_EXTENSION, McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db


def _rpc(method, params=None):
    params = dict(params or {})
    params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}


@pytest.fixture
def server():
    srv = McpServer()
    register_all_tools(srv)
    return srv


@pytest.fixture
def user():
    return UserFactory(is_superuser=True)


def _ask(server, user, method, params=None):
    return server.handle_request(_rpc(method, params), user)


def _organization_skill(name, *, state="validated", description="Our procedure.", body="# Steps\n\nDo it."):
    skill = McpSkill.objects.create(name=name, description=description, body=body)
    skill.workflow_state = state
    skill.save()
    return skill


class TestDiscovery:
    def test_the_extension_and_resources_are_declared(self, server, user):
        capabilities = _ask(server, user, "server/discover")["result"]["capabilities"]
        assert "resources" in capabilities
        assert capabilities["extensions"][SKILLS_EXTENSION] == {"directoryRead": True}


class TestShippedSkills:
    def test_each_entry_is_a_complete_manifest(self, server, user):
        result = _ask(server, user, "skills/list")["result"]
        assert result["resultType"] == "complete"
        assert result["ttlMs"] > 0 and result["cacheScope"] == "private"
        names = {entry["frontmatter"]["name"] for entry in result["skills"]}
        assert {"working-with-cairn", "iso27005-risk-analysis", "compliance-assessment"} <= names
        for entry in result["skills"]:
            assert entry["uri"] == f"skill://cairn/{entry['frontmatter']['name']}/SKILL.md"
            assert entry["frontmatter"]["description"]
            uris = [r["uri"] for r in entry["resources"]]
            assert entry["uri"] in uris
            for item in entry["resources"]:
                text = _ask(server, user, "resources/read", {"uri": item["uri"]})["result"]["contents"][0]["text"]
                raw = text.encode("utf-8")
                assert item["size"] == len(raw)
                assert item["digest"] == "sha256:" + hashlib.sha256(raw).hexdigest()

    def test_the_frontmatter_is_the_file_s(self, server, user):
        entry = _ask(server, user, "skills/get", {"uri": "skill://cairn/working-with-cairn/SKILL.md"})["result"]
        text = _ask(server, user, "resources/read", {"uri": entry["skill"]["uri"]})["result"]["contents"][0]["text"]
        assert skills.parse_skill_md(text)[0] == entry["skill"]["frontmatter"]
        assert entry["resultType"] == "complete" and entry["cacheScope"] == "private"

    def test_names_follow_the_agent_skills_rule(self):
        for name, skill in skills.catalogue().items():
            assert skills.name_problem(name) is None
            assert skill.frontmatter["name"] == name
            assert 1 <= len(skill.frontmatter["description"]) <= skills.DESCRIPTION_MAX

    def test_a_shipped_skill_names_only_tools_that_exist(self, server):
        from mcp.tests.test_guide import NOT_TOOLS, VERBS

        known = {tool["name"] for tool in server.iter_tools()}
        pattern = re.compile(r"\b(?:%s)_[a-z0-9_{}]+" % "|".join(VERBS))
        for skill in skills.catalogue().values():
            for file in skill.files:
                for word in pattern.findall(file.content.decode("utf-8")):
                    if "{" in word or word in NOT_TOOLS:
                        continue
                    assert word in known, f"{skill.name}/{file.path} names {word}, which is no tool"


class TestErrors:
    @pytest.mark.parametrize("method,uri", [
        ("skills/get", "skill://cairn/nothing/SKILL.md"),
        ("skills/get", "skill://cairn/working-with-cairn/other.md"),
        ("resources/read", "skill://cairn/working-with-cairn/../compliance-assessment/SKILL.md"),
        ("resources/read", "skill://cairn/nothing/SKILL.md"),
        ("resources/read", "file:///etc/passwd"),
        ("resources/directory/read", "skill://cairn/working-with-cairn/SKILL.md"),
        ("resources/directory/read", "skill://cairn/nothing"),
    ])
    def test_an_unknown_uri_is_invalid_params(self, server, user, method, uri):
        assert _ask(server, user, method, {"uri": uri})["error"]["code"] == -32602

    def test_a_skill_root_is_a_directory(self, server, user):
        result = _ask(server, user, "resources/directory/read", {"uri": "skill://cairn/working-with-cairn"})["result"]
        assert result["resultType"] == "complete"
        assert {"uri": "skill://cairn/working-with-cairn/SKILL.md", "name": "SKILL.md",
                "mimeType": "text/markdown"}.items() <= result["resources"][0].items()


class TestOrganizationSkills:
    def test_a_validated_skill_is_served(self, server, user):
        _organization_skill("supplier-onboarding", description="Onboard a supplier our way.")
        entry = _ask(server, user, "skills/get", {"uri": "skill://cairn/supplier-onboarding/SKILL.md"})["result"]
        assert entry["skill"]["frontmatter"] == {"name": "supplier-onboarding",
                                                 "description": "Onboard a supplier our way."}
        assert entry["skill"]["_meta"]["io.modelcontextprotocol.skills/origin"] == "organization"
        text = _ask(server, user, "resources/read", {"uri": entry["skill"]["uri"]})["result"]["contents"][0]["text"]
        assert text.endswith("# Steps\n\nDo it.\n")
        assert skills.parse_skill_md(text)[0] == entry["skill"]["frontmatter"]

    @pytest.mark.parametrize("state", ["draft", "pending", "archived"])
    def test_a_skill_not_validated_is_not_served(self, server, user, state):
        _organization_skill("supplier-onboarding", state=state)
        assert _ask(server, user, "skills/get", {"uri": "skill://cairn/supplier-onboarding/SKILL.md"})["error"]

    def test_it_replaces_the_shipped_skill_of_its_name(self, server, user):
        shipped = skills.catalogue()["working-with-cairn"].entry()
        _organization_skill("working-with-cairn", description="Our own rules.", body="Ask the CISO first.")
        listed = [e for e in _ask(server, user, "skills/list")["result"]["skills"]
                  if e["frontmatter"]["name"] == "working-with-cairn"]
        assert len(listed) == 1
        assert listed[0]["uri"] == shipped["uri"]
        assert listed[0]["resources"] != shipped["resources"]
        assert listed[0]["frontmatter"]["description"] == "Our own rules."

    def test_archiving_it_brings_the_shipped_skill_back(self, server, user):
        skill = _organization_skill("working-with-cairn", description="Our own rules.")
        skill.workflow_state = "archived"
        skill.save()
        entry = _ask(server, user, "skills/get", {"uri": "skill://cairn/working-with-cairn/SKILL.md"})["result"]
        assert entry["skill"]["_meta"]["io.modelcontextprotocol.skills/origin"] == "cairn"

    def test_a_description_that_reads_as_yaml_stays_text(self, server, user):
        tricky = 'Use it: when "asked" # not a comment\n- not a list'
        _organization_skill("tricky", description=tricky)
        entry = _ask(server, user, "skills/get", {"uri": "skill://cairn/tricky/SKILL.md"})["result"]["skill"]
        assert entry["frontmatter"]["description"] == tricky
        text = _ask(server, user, "resources/read", {"uri": entry["uri"]})["result"]["contents"][0]["text"]
        assert skills.parse_skill_md(text)[0]["description"] == tricky

    def test_resources_list_names_every_file(self, server, user):
        _organization_skill("supplier-onboarding")
        uris = {r["uri"] for r in _ask(server, user, "resources/list")["result"]["resources"]}
        assert "skill://cairn/supplier-onboarding/SKILL.md" in uris
        assert "skill://cairn/working-with-cairn/SKILL.md" in uris
        assert json.dumps(sorted(uris))


class TestWriteSurfaces:
    def test_the_rest_api_writes_and_validates(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        response = client.post("/api/v1/mcp/skills/", {"name": "supplier-onboarding", "description": "Our way.",
                                                     "body": "# Steps"}, content_type="application/json")
        assert response.status_code == 201, response.content
        data = response.json()
        assert data["status"] == "draft"
        assert data["uri"] == "skill://cairn/supplier-onboarding/SKILL.md"
        assert McpSkill.objects.get(pk=data["id"]).created_by == user
        refused = client.post("/api/v1/mcp/skills/", {"name": "Bad Name", "description": "x"},
                              content_type="application/json")
        assert refused.status_code == 400
        assert "name" in refused.json()["error"]

    def test_the_rest_api_needs_the_permission(self, client):
        client.force_login(UserFactory())
        assert client.get("/api/v1/mcp/skills/").status_code == 403

    def test_the_mcp_tools_write_a_draft_that_is_not_served(self, server, user):
        created = server.handle_request(_rpc("tools/call", {"name": "create_mcp_skill", "arguments": {
            "name": "supplier-onboarding", "description": "Our way.", "body": "Do it.",
        }}), user)["result"]
        assert created["isError"] is False
        assert McpSkill.objects.get(name="supplier-onboarding").workflow_state == "draft"
        assert "error" in _ask(server, user, "skills/get", {"uri": "skill://cairn/supplier-onboarding/SKILL.md"})

    def test_a_skill_without_instructions_cannot_be_submitted(self, user):
        from core.lifecycle import LifecycleError

        skill = McpSkill.objects.create(name="empty", description="Nothing yet.")
        with pytest.raises(LifecycleError):
            skill.transition_to("pending", user, enforce_permission=True)

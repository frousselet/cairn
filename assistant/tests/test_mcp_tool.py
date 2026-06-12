"""Tests for the ask_assistant MCP tool."""

import json

import pytest
from django.test import override_settings

from accounts.tests.factories import UserFactory
from assistant.catalog import TOOL_CATALOG
from assistant.engine import AskOutcome


def _get_tool():
    from mcp.api.views_mcp import get_mcp_server

    return get_mcp_server().get_tool("ask_assistant")


def test_ask_assistant_is_registered():
    tool = _get_tool()
    assert tool is not None
    assert "question" in tool["inputSchema"]["properties"]
    assert tool["inputSchema"]["required"] == ["question"]


def test_ask_assistant_not_in_its_own_catalog():
    assert "ask_assistant" not in TOOL_CATALOG


@pytest.mark.django_db
def test_missing_question_is_error():
    result = _get_tool()["handler"](UserFactory(), {})
    assert result["isError"] is True


@override_settings(AI_ASSISTANT_ENABLED=False)
@pytest.mark.django_db
def test_disabled_returns_error_envelope():
    result = _get_tool()["handler"](UserFactory(), {"question": "Quelles décisions ?"})
    assert result["isError"] is True
    payload = json.loads(result["content"][0]["text"])
    assert "AssistantDisabled" in payload["error"]


@pytest.mark.django_db
def test_happy_path_returns_outcome_dict(monkeypatch):
    class StubEngine:
        def __init__(self, user, language="en", client=None):
            pass

        def ask(self, question):
            return AskOutcome(question=question, language="en", summary="Done.")

    monkeypatch.setattr("assistant.engine.AssistantEngine", StubEngine)
    result = _get_tool()["handler"](UserFactory(), {"question": "Status ?"})
    assert result["summary"] == "Done."
    assert result["results"] == []

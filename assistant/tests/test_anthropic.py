"""Unit tests for the Anthropic (Claude) provider client (no real sockets)."""

import json

import httpx
import pytest
from django.test import override_settings

from assistant.providers.anthropic import AnthropicClient
from assistant.providers.base import (
    MalformedModelOutput,
    ModelNotAvailable,
    ServiceUnreachable,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


def _patch_post(monkeypatch, responses):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "payload": dict(json), "headers": dict(headers or {})})
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(httpx, "post", fake_post)
    return calls


def _client():
    return AnthropicClient(
        base_url="https://api.anthropic.com/v1",
        model="claude-opus-4-8",
        api_key="sk-ant-test",
    )


def test_chat_json_uses_forced_tool_and_returns_input(monkeypatch):
    payload = {"content": [{"type": "tool_use", "name": "plan", "input": {"steps": []}}]}
    calls = _patch_post(monkeypatch, [FakeResponse(payload=payload)])
    result = _client().chat_json(
        [
            {"role": "system", "content": "route this"},
            {"role": "user", "content": "hi"},
        ],
        {"type": "object"},
    )
    assert result == {"steps": []}
    call = calls[0]
    assert call["url"].endswith("/messages")
    # Native auth headers, not Bearer.
    assert call["headers"]["x-api-key"] == "sk-ant-test"
    assert call["headers"]["anthropic-version"] == "2023-06-01"
    body = call["payload"]
    assert body["model"] == "claude-opus-4-8"
    assert body["max_tokens"] >= 1
    # System prompt is hoisted to the top-level field, not a message.
    assert body["system"] == "route this"
    assert body["messages"] == [{"role": "user", "content": "hi"}]
    # Sampling params / thinking must NOT be sent (400 on the Opus family).
    assert "temperature" not in body
    assert "thinking" not in body
    # Structured output via forced tool use.
    assert body["tools"][0]["name"] == "plan"
    assert body["tools"][0]["input_schema"] == {"type": "object"}
    assert body["tool_choice"] == {"type": "tool", "name": "plan"}


def test_chat_json_without_tool_use_raises_malformed(monkeypatch):
    payload = {"content": [{"type": "text", "text": "no plan here"}]}
    _patch_post(monkeypatch, [FakeResponse(payload=payload)])
    with pytest.raises(MalformedModelOutput):
        _client().chat_json([{"role": "user", "content": "hi"}], {"type": "object"})


def test_chat_text_concatenates_text_blocks(monkeypatch):
    payload = {"content": [{"type": "text", "text": "  Two open "}, {"type": "text", "text": "risks.  "}]}
    _patch_post(monkeypatch, [FakeResponse(payload=payload)])
    assert _client().chat_text([{"role": "user", "content": "hi"}]) == "Two open risks."


@override_settings(AI_ASSISTANT_BASE_URL="", AI_ASSISTANT_MODEL="claude-opus-4-8")
def test_defaults_to_anthropic_endpoint(monkeypatch):
    payload = {"content": [{"type": "text", "text": "ok"}]}
    calls = _patch_post(monkeypatch, [FakeResponse(payload=payload)])
    AnthropicClient(api_key="sk-ant-test").chat_text([{"role": "user", "content": "hi"}])
    assert calls[0]["url"] == "https://api.anthropic.com/v1/messages"


def test_missing_api_key_raises_clear_error(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not hit the network without an API key")

    monkeypatch.setattr(httpx, "post", boom)
    client = AnthropicClient(base_url="https://api.anthropic.com/v1", model="m", api_key="")
    with pytest.raises(ServiceUnreachable) as exc:
        client.chat_text([{"role": "user", "content": "hi"}])
    assert "API key" in str(exc.value)


def test_auth_error_maps_to_unreachable_without_leaking(monkeypatch):
    _patch_post(monkeypatch, [FakeResponse(status_code=401, text="invalid x-api-key")])
    with pytest.raises(ServiceUnreachable) as exc:
        _client().chat_text([{"role": "user", "content": "hi"}])
    assert "sk-ant-test" not in str(exc.value)


def test_unknown_model_maps_to_model_not_available(monkeypatch):
    _patch_post(monkeypatch, [FakeResponse(status_code=404, text="model not found")])
    with pytest.raises(ModelNotAvailable):
        _client().chat_text([{"role": "user", "content": "hi"}])


def test_connect_error_maps_to_unreachable(monkeypatch):
    _patch_post(monkeypatch, [httpx.ConnectError("refused")])
    with pytest.raises(ServiceUnreachable):
        _client().chat_text([{"role": "user", "content": "hi"}])


def test_embed_is_unsupported(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("embed must not hit the network")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(ServiceUnreachable) as exc:
        _client().embed(["x"])
    assert "embeddings" in str(exc.value).lower()

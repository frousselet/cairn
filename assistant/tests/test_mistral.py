"""Unit tests for the Mistral provider client (no real sockets)."""

import json

import httpx
import pytest

from assistant.providers.base import (
    MalformedModelOutput,
    ModelNotAvailable,
    ServiceUnreachable,
)
from assistant.providers.mistral import MistralClient


class FakeResponse:
    def __init__(self, status_code=200, content="", text=""):
        self.status_code = status_code
        self._content = content
        self.text = text or json.dumps(
            {"choices": [{"message": {"content": content}}]}
        )

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


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
    return MistralClient(
        base_url="https://api.mistral.ai/v1",
        model="mistral-small-latest",
        api_key="sk-test",
    )


def test_chat_json_sends_schema_and_bearer(monkeypatch):
    calls = _patch_post(monkeypatch, [FakeResponse(content='{"steps": []}')])
    result = _client().chat_json([{"role": "user", "content": "hi"}], {"type": "object"})
    assert result == {"steps": []}
    call = calls[0]
    assert call["url"].endswith("/chat/completions")
    assert call["headers"]["Authorization"] == "Bearer sk-test"
    payload = call["payload"]
    assert payload["model"] == "mistral-small-latest"
    assert payload["temperature"] == 0
    assert payload["stream"] is False
    rf = payload["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["schema"] == {"type": "object"}
    assert rf["json_schema"]["strict"] is False


def test_chat_json_falls_back_to_json_object_on_422(monkeypatch):
    calls = _patch_post(
        monkeypatch,
        [FakeResponse(status_code=422, text="bad response_format"),
         FakeResponse(content='{"steps": []}')],
    )
    result = _client().chat_json([{"role": "user", "content": "hi"}], {"type": "object"})
    assert result == {"steps": []}
    assert calls[0]["payload"]["response_format"]["type"] == "json_schema"
    assert calls[1]["payload"]["response_format"] == {"type": "json_object"}


def test_chat_text_returns_stripped_content(monkeypatch):
    _patch_post(monkeypatch, [FakeResponse(content="  Two open risks.  ")])
    assert _client().chat_text([{"role": "user", "content": "hi"}]) == "Two open risks."


def test_auth_error_maps_to_unreachable_without_leaking(monkeypatch):
    _patch_post(monkeypatch, [FakeResponse(status_code=401, text="invalid api key")])
    with pytest.raises(ServiceUnreachable) as exc:
        _client().chat_text([{"role": "user", "content": "hi"}])
    assert "sk-test" not in str(exc.value)


def test_unknown_model_maps_to_model_not_available(monkeypatch):
    _patch_post(monkeypatch, [FakeResponse(status_code=404, text="model not found")])
    with pytest.raises(ModelNotAvailable):
        _client().chat_text([{"role": "user", "content": "hi"}])


def test_connect_error_maps_to_unreachable(monkeypatch):
    _patch_post(monkeypatch, [httpx.ConnectError("refused")])
    with pytest.raises(ServiceUnreachable):
        _client().chat_text([{"role": "user", "content": "hi"}])


def test_timeout_maps_to_unreachable(monkeypatch):
    _patch_post(monkeypatch, [httpx.ReadTimeout("slow")])
    with pytest.raises(ServiceUnreachable):
        _client().chat_text([{"role": "user", "content": "hi"}])


def test_non_json_content_raises_malformed_output(monkeypatch):
    _patch_post(monkeypatch, [FakeResponse(content="not json at all")])
    with pytest.raises(MalformedModelOutput):
        _client().chat_json([{"role": "user", "content": "hi"}], {"type": "object"})

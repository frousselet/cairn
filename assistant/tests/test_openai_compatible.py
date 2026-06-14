"""Unit tests specific to the generic OpenAI-compatible provider client.

The shared request/response handling is exercised through the Mistral
specialization in ``test_mistral.py``; this module covers the bits that differ
for the generic client: the default endpoint and the provider-neutral error
message.
"""

import json

import httpx
import pytest
from django.test import override_settings

from assistant.providers.base import ServiceUnreachable
from assistant.providers.openai_compatible import OpenAICompatibleClient


class FakeResponse:
    def __init__(self, status_code=200, content="", text=""):
        self.status_code = status_code
        self._content = content
        self.text = text or json.dumps({"choices": [{"message": {"content": content}}]})

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


@override_settings(AI_ASSISTANT_BASE_URL="", AI_ASSISTANT_MODEL="gpt-4o-mini")
def test_defaults_to_openai_endpoint(monkeypatch):
    calls = _patch_post(monkeypatch, [FakeResponse(content="hello")])
    client = OpenAICompatibleClient(api_key="sk-test")
    client.chat_text([{"role": "user", "content": "hi"}])
    assert calls[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert calls[0]["payload"]["model"] == "gpt-4o-mini"


@override_settings(AI_ASSISTANT_BASE_URL="https://my-gateway.example/v1")
def test_custom_base_url_is_honored(monkeypatch):
    calls = _patch_post(monkeypatch, [FakeResponse(content="hi")])
    OpenAICompatibleClient(api_key="sk-test").chat_text(
        [{"role": "user", "content": "hi"}]
    )
    assert calls[0]["url"] == "https://my-gateway.example/v1/chat/completions"


def test_missing_api_key_raises_clear_error(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not hit the network without an API key")

    monkeypatch.setattr(httpx, "post", boom)
    client = OpenAICompatibleClient(base_url="https://api.openai.com/v1", api_key="")
    with pytest.raises(ServiceUnreachable) as exc:
        client.chat_text([{"role": "user", "content": "hi"}])
    assert "API key" in str(exc.value)

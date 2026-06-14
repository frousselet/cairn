"""Tests for the provider factory ``get_client``."""

import pytest
from django.test import override_settings

from assistant.providers import ServiceUnreachable, get_client
from assistant.providers.anthropic import AnthropicClient
from assistant.providers.mistral import MistralClient
from assistant.providers.ollama import OllamaClient
from assistant.providers.openai_compatible import OpenAICompatibleClient


@override_settings(AI_ASSISTANT_PROVIDER="mistral")
def test_factory_returns_mistral_by_default():
    assert isinstance(get_client(), MistralClient)


@override_settings(AI_ASSISTANT_PROVIDER="ollama")
def test_factory_returns_ollama_when_selected():
    assert isinstance(get_client(), OllamaClient)


@override_settings(AI_ASSISTANT_PROVIDER="openai")
def test_factory_returns_openai_when_selected():
    client = get_client()
    assert isinstance(client, OpenAICompatibleClient)
    # The generic client must not be the Mistral specialization.
    assert not isinstance(client, MistralClient)


@override_settings(AI_ASSISTANT_PROVIDER="openai-compatible")
def test_factory_accepts_openai_compatible_alias():
    assert isinstance(get_client(), OpenAICompatibleClient)


@override_settings(AI_ASSISTANT_PROVIDER="anthropic")
def test_factory_returns_anthropic_when_selected():
    assert isinstance(get_client(), AnthropicClient)


@override_settings(AI_ASSISTANT_PROVIDER="claude")
def test_factory_accepts_claude_alias():
    assert isinstance(get_client(), AnthropicClient)


@override_settings(AI_ASSISTANT_PROVIDER="unknown")
def test_factory_rejects_unknown_provider():
    with pytest.raises(ServiceUnreachable):
        get_client()

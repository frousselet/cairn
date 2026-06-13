"""Tests for the provider factory ``get_client``."""

import pytest
from django.test import override_settings

from assistant.providers import ServiceUnreachable, get_client
from assistant.providers.mistral import MistralClient
from assistant.providers.ollama import OllamaClient


@override_settings(AI_ASSISTANT_PROVIDER="mistral")
def test_factory_returns_mistral_by_default():
    assert isinstance(get_client(), MistralClient)


@override_settings(AI_ASSISTANT_PROVIDER="ollama")
def test_factory_returns_ollama_when_selected():
    assert isinstance(get_client(), OllamaClient)


@override_settings(AI_ASSISTANT_PROVIDER="unknown")
def test_factory_rejects_unknown_provider():
    with pytest.raises(ServiceUnreachable):
        get_client()

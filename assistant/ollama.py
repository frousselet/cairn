"""Backward-compatibility re-exports.

The assistant backend moved to the pluggable ``assistant.providers`` package
(``mistral`` by default, ``ollama`` still selectable). This module keeps the
historical import paths working. ``OllamaUnreachable`` is an alias of the
provider-neutral ``ServiceUnreachable``.
"""

from assistant.providers.base import (
    AssistantDisabled,
    AssistantError,
    MalformedModelOutput,
    ModelNotAvailable,
    ServiceUnreachable,
    get_client,
)
from assistant.providers.ollama import OllamaClient

# Historical name kept for callers that catch the Ollama-specific exception.
OllamaUnreachable = ServiceUnreachable

__all__ = [
    "AssistantDisabled",
    "AssistantError",
    "MalformedModelOutput",
    "ModelNotAvailable",
    "OllamaClient",
    "OllamaUnreachable",
    "ServiceUnreachable",
    "get_client",
]

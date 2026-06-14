"""Mistral AI backend for the assistant (third-party, EU-hosted API).

Mistral exposes an OpenAI-compatible chat completions endpoint, so this client
is a thin specialization of :class:`OpenAICompatibleClient` that only pins the
Mistral defaults (base URL and provider label). All request/response handling
is shared with every other OpenAI-compatible backend.

Only the calling user's question and the compact, identifier-stripped record
fields produced by the read-only catalog tools leave the platform; ids and
UUIDs are scrubbed before the summary call (see ``engine._strip_identifiers``).
"""

from assistant.providers.openai_compatible import OpenAICompatibleClient


class MistralClient(OpenAICompatibleClient):
    PROVIDER_LABEL = "Mistral"
    DEFAULT_BASE_URL = "https://api.mistral.ai/v1"

"""Anthropic (Claude) backend for the assistant (native Messages API).

Claude is NOT OpenAI-compatible : it uses ``POST /v1/messages`` with an
``x-api-key`` header, a top-level ``system`` parameter, and a ``content`` block
list in the response. It therefore needs its own client rather than the shared
``OpenAICompatibleClient``.

Two operations are implemented: a chat completion constrained to a JSON Schema
for tool routing (done with forced tool use, the reliable structured-output
path on Claude) and a plain-text chat completion for the final summary
sentence. Embeddings are not provided : Anthropic has no embeddings endpoint,
so semantic search must use another provider (see ``embed``).

Only the calling user's question and the compact, identifier-stripped record
fields produced by the read-only catalog tools leave the platform; ids and
UUIDs are scrubbed before the summary call (see ``engine._strip_identifiers``).
"""

import logging

import httpx
from django.conf import settings

from assistant.providers.base import (
    BaseClient,
    MalformedModelOutput,
    ModelNotAvailable,
    ServiceUnreachable,
)

logger = logging.getLogger(__name__)


class AnthropicClient(BaseClient):
    PROVIDER_LABEL = "Claude"
    # Applied when neither the constructor argument nor
    # ``settings.AI_ASSISTANT_BASE_URL`` is set. The Messages endpoint is
    # ``{base_url}/messages`` (so the default resolves to
    # ``https://api.anthropic.com/v1/messages``).
    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    # Pinned API version sent on every request (Anthropic requirement).
    ANTHROPIC_VERSION = "2023-06-01"
    # Name of the synthetic tool used to force structured routing output.
    PLAN_TOOL_NAME = "plan"

    def __init__(self, base_url=None, model=None, api_key=None):
        self.base_url = (
            base_url or settings.AI_ASSISTANT_BASE_URL or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.model = model or settings.AI_ASSISTANT_MODEL
        self.api_key = api_key if api_key is not None else settings.AI_ASSISTANT_API_KEY
        self.timeout = httpx.Timeout(
            settings.AI_ASSISTANT_TIMEOUT,
            connect=settings.AI_ASSISTANT_CONNECT_TIMEOUT,
        )

    def _headers(self):
        if not self.api_key:
            raise ServiceUnreachable(
                f"{self.PROVIDER_LABEL} API key is not configured "
                "(set AI_ASSISTANT_API_KEY)."
            )
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    @staticmethod
    def _split_system(messages):
        """Split OpenAI-style messages into Claude's (system, messages) shape.

        Claude takes the system prompt as a top-level parameter, not as a
        message with ``role: "system"``; user/assistant turns stay in
        ``messages``.
        """
        system_parts = []
        chat = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if role == "system":
                if content:
                    system_parts.append(content)
            else:
                chat.append({"role": role, "content": content})
        return "\n\n".join(system_parts), chat

    def _base_payload(self, messages):
        system, chat = self._split_system(messages)
        # No temperature / thinking: both are rejected (HTTP 400) on the
        # current Opus family, which is the default model.
        payload = {
            "model": self.model,
            "max_tokens": settings.AI_ASSISTANT_MAX_TOKENS,
            "messages": chat,
        }
        if system:
            payload["system"] = system
        return payload

    def _post(self, payload):
        try:
            return httpx.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ServiceUnreachable(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ServiceUnreachable(str(exc)) from exc

    def _raise_for_status(self, resp):
        if resp.status_code in (401, 403):
            # Never surface the key or auth detail to the caller.
            logger.error(
                "%s authentication failed (HTTP %s)",
                self.PROVIDER_LABEL,
                resp.status_code,
            )
            raise ServiceUnreachable("authentication failed")
        if resp.status_code == 404:
            raise ModelNotAvailable(self.model)
        if resp.status_code >= 400:
            raise ServiceUnreachable(f"HTTP {resp.status_code}: {resp.text[:200]}")

    def _content_blocks(self, resp):
        try:
            blocks = resp.json()["content"]
        except (KeyError, TypeError, ValueError) as exc:
            raise MalformedModelOutput(resp.text[:200]) from exc
        if not isinstance(blocks, list):
            raise MalformedModelOutput(resp.text[:200])
        return blocks

    def chat_json(self, messages, json_schema, think=None):
        """Chat completion constrained to ``json_schema``; returns the parsed object.

        Uses forced tool use : a single ``plan`` tool whose ``input_schema`` is
        the routing schema, with ``tool_choice`` pinned to it. The model must
        emit a ``tool_use`` block whose ``input`` is the structured plan. The
        plan schema keeps a free-form ``arguments`` object, which Claude tool
        input schemas accept; server-side validation in the engine is the real
        safety net.
        """
        payload = self._base_payload(messages)
        payload["tools"] = [
            {
                "name": self.PLAN_TOOL_NAME,
                "description": "Return the execution plan for the question.",
                "input_schema": json_schema,
            }
        ]
        payload["tool_choice"] = {"type": "tool", "name": self.PLAN_TOOL_NAME}
        resp = self._post(payload)
        self._raise_for_status(resp)
        for block in self._content_blocks(resp):
            if block.get("type") == "tool_use" and block.get("name") == self.PLAN_TOOL_NAME:
                parsed = block.get("input")
                if not isinstance(parsed, dict):
                    raise MalformedModelOutput(str(parsed)[:200])
                return parsed
        raise MalformedModelOutput(resp.text[:200])

    def chat_text(self, messages):
        """Plain-text chat completion."""
        resp = self._post(self._base_payload(messages))
        self._raise_for_status(resp)
        text = "".join(
            block.get("text", "")
            for block in self._content_blocks(resp)
            if block.get("type") == "text"
        )
        return text.strip()

    def embed(self, texts):
        """Embeddings are unsupported : Anthropic has no embeddings endpoint."""
        raise ServiceUnreachable(
            "The Claude provider does not support embeddings (Anthropic has no "
            "embeddings API). Disable AI_ASSISTANT_SEMANTIC_ENABLED, or set "
            "AI_ASSISTANT_PROVIDER to a provider with embeddings for indexing."
        )

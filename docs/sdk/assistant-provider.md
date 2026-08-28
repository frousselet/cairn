# Adding an assistant provider

Ask Cairn talks to an LLM through a deliberately small interface, so the backend
is a runtime choice rather than a dependency of the engine. Four providers ship :
Mistral (the default), OpenAI and any OpenAI-compatible endpoint, Anthropic
Claude, and self-hosted Ollama.

## The contract

`assistant/providers/base.py` asks a backend for three operations, and nothing
else:

```python
class BaseClient:
    def chat_json(self, messages, json_schema, think=None):
        """Return the parsed object the model produced under the schema constraint."""

    def chat_text(self, messages):
        """Return a plain string."""

    def embed(self, texts):
        """Return one embedding vector (list[float]) per input string."""
```

`chat_json` drives tool routing : the engine asks the model which read-only
tools to call, constrained by a JSON Schema. `chat_text` produces the final
summary sentence. `embed` backs semantic requirement search and is optional : a
provider without embeddings (Claude, today) simply raises, and semantic search
is then configured against another provider or left off.

The engine depends on this surface alone, which is why adding a backend touches
no engine code.

## The failure vocabulary

Raise the right one. They are what the API turns into a stable `503` code, and
what tells an operator whether the problem is theirs or the provider's.

| Exception | Means |
| --- | --- |
| `ServiceUnreachable` | Cannot be reached, or returned a server error |
| `ModelNotAvailable` | The configured model is unknown to the backend |
| `MalformedModelOutput` | The response does not parse as expected |
| `AssistantDisabled` | The feature flag is off |

Swallowing a failure and returning an empty answer is the one thing not to do :
the assistant labels its summaries as AI-generated and cites real records, and a
silent degradation breaks that contract without telling anyone.

## Writing one

`assistant/providers/<name>.py`:

```python
class MyProviderClient(BaseClient):
    def __init__(self):
        self.base_url = settings.AI_ASSISTANT_BASE_URL or "https://api.example.com/v1"
        self.model = settings.AI_ASSISTANT_MODEL
        self.api_key = settings.AI_ASSISTANT_API_KEY

    def chat_json(self, messages, json_schema, think=None):
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json={"model": self.model, "messages": messages,
                      "response_format": {"type": "json_schema",
                                          "json_schema": json_schema}},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=httpx.Timeout(settings.AI_ASSISTANT_TIMEOUT,
                                      connect=settings.AI_ASSISTANT_CONNECT_TIMEOUT),
            )
        except httpx.RequestError as exc:
            raise ServiceUnreachable(str(exc)) from exc
        ...
```

Use `httpx`, which is already a dependency, and honour both timeouts. They are
separate on purpose : a provider that is down should fail in two seconds, while
one that is merely slow gets thirty. Ignoring them turns a provider outage into
a hung command palette.

Then add the branch to `get_client()` in `base.py`. Selection is by
`AI_ASSISTANT_PROVIDER`, lower-cased, and accepting an alias is fine
(`anthropic` and `claude` both resolve to the same client).

## Before shipping it

Update `.env.example` and the
[assistant specification](../specs/assistant/README.md) with the provider's
configuration and, importantly, **its data-egress properties**. Enabling the
assistant sends the question text and the compact record fields used for routing
to whoever runs the endpoint. An operator choosing a provider is making a data
protection decision, and the documentation is where they make it.

Regenerate the reference so any new setting appears:

```bash
python manage.py generate_docs
```

## Testing

`assistant/tests/`. Mock the HTTP layer; do not call a live provider in the
suite. Cover: a well-formed response parses; a connection error raises
`ServiceUnreachable`; an unknown model raises `ModelNotAvailable`; malformed
content raises `MalformedModelOutput`; and `get_client()` returns your client
for the provider string and its aliases.

## Checklist

- [ ] Client implements `chat_json`, `chat_text` and, if supported, `embed`
- [ ] Both timeouts honoured
- [ ] The four failure modes raise the right exception
- [ ] Branch added to `get_client()`
- [ ] `.env.example` and the assistant specification updated, egress described
- [ ] `generate_docs` re-run and committed
- [ ] Tests mock the transport and cover every failure mode

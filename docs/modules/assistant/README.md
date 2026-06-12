# Assistant module (Ask Cairn)

Optional natural-language question mode embedded in the command palette (Ctrl+K). A very small local LLM, served by an [Ollama](https://ollama.com/) sidecar, routes the user's question to a curated allowlist of read-only MCP tools executed in-process with the requesting user; the answer displays the real matching records as clickable cards plus a short AI-labeled summary sentence. Data never leaves the host.

Django app: `assistant/`. **No persistent entities, no migrations, no lifecycle workflow**: the feature is stateless (a future query audit log would be a separate decision).

## Pipeline

```
Question (palette or API)
  -> AssistantEngine.ask()
       1 planning call: Ollama /api/chat, grammar-constrained JSON output
       (format = JSON Schema; tool names restricted by enum to the catalog,
       at most AI_ASSISTANT_MAX_TOOL_ROUNDS steps; "$1.id" placeholders
       reference earlier steps)
       -> deterministic engine-side execution of the plan:
            sanitization (allowlist re-check, argument whitelist, limit
            clamp), placeholder resolution from the parent step's first
            record (with a one-shot retry without the status filter when
            the parent matches nothing), id-grounding check
            -> in-process execution through McpServer.get_tool() with the
               session user: existing @require_perm decorators and scope
               filters apply, nothing is bypassed
       -> 1 summary call (plain text, user's language, identifier-stripped
          data only)
  -> rendered partial: AI summary + record cards with links + disclaimer
```

Sequencing is deliberately NOT left to the model round after round: very
small models are unreliable at deciding mid-conversation whether to chain a
child call. They are good at one-shot constrained planning, so the engine
owns the execution order, the id plumbing and the fallbacks.

Key code: `assistant/engine.py` (loop), `assistant/catalog.py` (allowlist), `assistant/ollama.py` (client + error taxonomy), `assistant/prompts.py` (model-facing English prompts).

## Settings

| Setting | Env var | Default | Purpose |
| ------- | ------- | ------- | ------- |
| `AI_ASSISTANT_ENABLED` | `AI_ASSISTANT_ENABLED` | `False` | Feature flag; when off the palette behaves exactly as before |
| `AI_ASSISTANT_OLLAMA_URL` | `AI_ASSISTANT_OLLAMA_URL` | `http://ollama:11434` | Base URL of the Ollama service |
| `AI_ASSISTANT_MODEL` | `AI_ASSISTANT_MODEL` | `qwen3:1.7b` | Any Ollama chat model; pull it once on the sidecar |
| `AI_ASSISTANT_CONNECT_TIMEOUT` | same | `2` | Seconds; fast fail when the sidecar is absent |
| `AI_ASSISTANT_TIMEOUT` | same | `30` | Seconds per LLM call (CPU inference, cold load included) |
| `AI_ASSISTANT_MAX_TOOL_ROUNDS` | same | `3` | Hard cap on plan steps (also enforced in the plan JSON Schema) |
| `AI_ASSISTANT_ROUTING_THINK` | same | `False` | Chain-of-thought during planning (thinking models only); too slow on CPU-only hosts, useful with a GPU |
| `AI_ASSISTANT_MAX_RECORDS_PER_TOOL` | same | `5` | Limit clamp applied to every tool call |
| `AI_ASSISTANT_NUM_CTX` | same | `8192` | Ollama context window |

## Tool allowlist

Hard-coded in `assistant/catalog.py` (21 tools, strictly `list_*` / `get_*`). The routing JSON Schema constrains the tool name to this set at decoding time; the engine re-validates server-side. Permissions are those of the underlying MCP tools (nothing re-declared):

| Tool | Permission |
| ---- | ---------- |
| `list_management_reviews`, `get_management_review`, `list_management_review_decisions`, `list_isms_changes` | `reports.management_review.read` |
| `list_risks`, `get_risk` | `risks.risk.read` |
| `list_risk_treatment_plans` | `risks.treatment.read` |
| `list_risk_acceptances` | `risks.acceptance.read` |
| `list_action_plans`, `get_action_plan` | `compliance.action_plan.read` |
| `list_compliance_assessments` | `compliance.assessment.read` |
| `list_frameworks`, `get_framework_compliance_summary` | `compliance.framework.read` |
| `list_indicators`, `list_indicator_measurements` | `context.indicator.read` |
| `list_issues` | `context.issue.read` |
| `list_objectives` | `context.objective.read` |
| `list_scopes` | `context.scope.read` |
| `list_suppliers` | `assets.supplier.read` |
| `list_essential_assets` | `assets.essential_asset.read` |
| `list_support_assets` | `assets.support_asset.read` |

## Business rules

- **RG-AI-01 - Read-only surface**: the assistant can only reach tools in the catalog, all read-only. A model response naming any other tool is refused server-side (and is already impossible to decode through the constrained schema). Worst case is a useless answer, never a write or an unauthorized read.
- **RG-AI-02 - Bounded execution**: exactly two LLM calls per question (one plan, one summary) and at most `AI_ASSISTANT_MAX_TOOL_ROUNDS` tool executions (plus at most one deterministic parent retry without its status filter).
- **RG-AI-03 - AI output is labeled and escaped**: the summary sentence carries the AI badge and disclaimer, renders through Django autoescaping, and the cards are built server-side from ORM records; the model never produces URLs or markup.
- **RG-AI-04 - Permissions enforced by the platform**: every data access runs the regular MCP handler with the calling user; `@require_perm` denials surface as a neutral "some results were hidden" notice, never as data.
- **RG-AI-05 - Graceful degradation**: assistant disabled, Ollama unreachable or model not pulled produce friendly i18n states in the palette; normal search is never affected. A summary-stage failure keeps the record cards (degraded mode).
- **RG-AI-06 - Id grounding**: id-like arguments (`id`, `*_id`) must come from a `$N.id` placeholder resolved against an earlier step's results, or be pasted verbatim in the question. Literal ids from nowhere (typically copied from the prompt examples by the model) are refused without executing the tool.
- **RG-AI-07 - No identifiers in the summary**: the payload fed to the summary stage is recursively stripped of `id` / `*_id` keys and UUID-shaped values, and the prompt forbids citing identifiers; when the data lacks the requested information the model must say so and defer to the record cards.

## Prompt-injection posture

Record contents are user-authored data already visible to the requesting user. They re-enter the model only at the summary stage and can at most steer the wording of one sentence, which is rendered escaped and labeled as AI. Tools are read-only; there is no write or markup escalation path.

## Interfaces

| Surface | Path | Notes |
| ------- | ---- | ----- |
| Palette partial | `POST /api/assistant/ask/` (`assistant:ask`) | Session auth, returns the HTML partial, always 200 with error states inside |
| REST API | `POST /api/v1/assistant/ask/` | Session / JWT / OAuth; body `{"q": "...", "language": "fr"}`; 200 with `{summary, language, degraded, results, refused_tools}`; 503 + code (`assistant_disabled`, `assistant_unreachable`, `model_missing`, `model_error`); 400 on invalid `q` |
| MCP | `ask_assistant` tool | Same outcome shape; error envelope when unavailable |

## Operations

```bash
docker compose --profile ai up -d
docker compose exec ollama ollama pull qwen3:1.7b
# .env: AI_ASSISTANT_ENABLED=True, then restart web
```

Sizing: `qwen3:1.7b` needs roughly 2-4 GB of RAM at an 8k context, CPU-only. The first question after a model (re)load takes 10-20 extra seconds; warm questions take roughly 5-30 s for the plan, the tool executions and the summary. Any other Ollama model can be substituted via `AI_ASSISTANT_MODEL` without code changes.

### Choosing a model

Measured on the Voltara demo dataset (Docker on an Apple M3, CPU-only VM):

| Model | Size | Data accuracy | French phrasing | Verdict |
| ----- | ---- | ------------- | --------------- | ------- |
| `qwen3:1.7b` (default) | 1.4 GB | correct (plan-based engine) | occasional slips ("scépôle", "est responsable par") | best CPU-only choice; cosmetic risk only, records are always exact |
| `llama3.2:3b` | 2 GB | correct but weaker plans | also flawed ("la prêté à gérer"), verbose | not worth the extra weight |
| `qwen3:4b` and larger | 2.6+ GB | correct | clean French | needs accelerated inference; unusable in a CPU-only Docker VM (470 s, runner OOM at 8 GB) |

Rule of thumb: clean French phrasing starts around the 4B class, and that class needs a GPU-backed Ollama. On macOS, Docker containers cannot use the Metal GPU: install the native Ollama app on the host instead and point the web container at it:

```bash
# .env
AI_ASSISTANT_OLLAMA_URL=http://host.docker.internal:11434
AI_ASSISTANT_MODEL=qwen3:4b
```

(then do not start the `ai` compose profile, or its container would conflict on port 11434). On a Linux server with a GPU, add the standard GPU reservation to the `ollama` service. On pure CPU servers, keep `qwen3:1.7b`: the summary sentence may occasionally read clumsily, but the cards always show the exact records.

## Future work

- Semantic search over record contents (embeddings, pgvector) for fuzzy "find things about X" questions.
- Optional query audit log (persistent entity, would then follow the lifecycle/workflow conventions).
- Streaming the summary sentence into the palette.

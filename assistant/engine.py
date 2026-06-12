"""Bounded natural-language question engine.

Pipeline: one constrained planning call turns the question into a short plan
of read-only catalog tools (sequencing is NOT left to the model round after
round: tiny models are unreliable at it). The engine executes the plan
deterministically, resolving ``$N.id`` placeholders from earlier step
results, through the MCP registry with the session user (existing
``@require_perm`` decorators and scope filters apply, nothing is bypassed).
One final model call produces a short summary sentence from the collected,
identifier-stripped data.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from django.conf import settings

from assistant.catalog import TOOL_CATALOG, plan_schema
from assistant.ollama import (
    AssistantDisabled,
    MalformedModelOutput,
    OllamaClient,
    OllamaUnreachable,
)
from assistant.prompts import routing_prompt, summary_prompt

logger = logging.getLogger(__name__)

# Cap on the serialized tool result fed back to the summary model.
COMPACT_RESULT_MAX_CHARS = 2000

PERMISSION_DENIED = "permission_denied"
TOOL_ERROR = "tool_error"

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
PLACEHOLDER_RE = re.compile(r"^\$(\d+)\.id$")


@dataclass
class ToolRun:
    tool: str
    label: str
    icon: str
    arguments: dict
    records: list = field(default_factory=list)
    cards: list = field(default_factory=list)
    data: object = None
    error: str = None

    def compact_json(self):
        spec = TOOL_CATALOG[self.tool]
        if self.error:
            payload = {"error": self.error}
        elif self.records:
            payload = [spec.compact_record(r) for r in self.records]
        else:
            payload = self.data if self.data is not None else []
        text = json.dumps(payload, default=str, ensure_ascii=False)
        return text[:COMPACT_RESULT_MAX_CHARS]


@dataclass
class AskOutcome:
    question: str
    language: str
    summary: str = None
    degraded: bool = False
    tool_runs: list = field(default_factory=list)
    refused_tools: list = field(default_factory=list)

    @property
    def has_cards(self):
        return any(run.cards for run in self.tool_runs)

    @property
    def permission_denied(self):
        return any(run.error == PERMISSION_DENIED for run in self.tool_runs)

    def as_dict(self):
        return {
            "question": self.question,
            "language": self.language,
            "summary": self.summary,
            "degraded": self.degraded,
            "refused_tools": list(self.refused_tools),
            "results": [
                {
                    "tool": run.tool,
                    "label": run.label,
                    "error": run.error,
                    "records": run.cards,
                }
                for run in self.tool_runs
            ],
        }


def _system(content):
    return {"role": "system", "content": content}


def _user(content):
    return {"role": "user", "content": content}


def _strip_identifiers(payload):
    """Remove internal ids from the data fed to the summary stage.

    The routing rounds need record ids for child tool calls, but the summary
    model must never see them: a small model readily "answers" a question by
    citing a UUID when the real information is missing from the data.
    """
    if isinstance(payload, dict):
        return {
            key: _strip_identifiers(value)
            for key, value in payload.items()
            if not (key == "id" or key.endswith("_id"))
            and not (isinstance(value, str) and UUID_RE.fullmatch(value.lower()))
        }
    if isinstance(payload, list):
        return [
            _strip_identifiers(item)
            for item in payload
            if not (isinstance(item, str) and UUID_RE.fullmatch(item.lower()))
        ]
    return payload


def _extract_records(raw):
    """Normalize a tool result to a list of record dicts.

    Generic list handlers return ``{"total", "items", ...}``, the management
    review tools return a bare list, get handlers return a single dict, and
    aggregate tools (e.g. compliance summaries) return a plain dict.
    """
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        items = raw.get("items")
        if isinstance(items, list):
            return [r for r in items if isinstance(r, dict)]
        if raw.get("id"):
            return [raw]
    return []


class AssistantEngine:
    def __init__(self, user, language="en", client=None):
        self.user = user
        self.language = language or "en"
        self.client = client or OllamaClient()

    def ask(self, question):
        if not settings.AI_ASSISTANT_ENABLED:
            raise AssistantDisabled()
        outcome = AskOutcome(question=question, language=self.language)
        max_steps = settings.AI_ASSISTANT_MAX_TOOL_ROUNDS
        plan = self.client.chat_json(
            [_system(routing_prompt()), _user(question)],
            plan_schema(max_steps),
        )
        steps = [s for s in (plan.get("steps") or []) if isinstance(s, dict)]
        # Id grounding: literal id arguments may only carry ids returned by an
        # earlier step (covered by $N.id resolution) or pasted verbatim in the
        # question. Small models otherwise reuse ids from the prompt examples.
        known_ids = set(UUID_RE.findall(question.lower()))
        step_runs = {}
        for index, step in enumerate(steps[:max_steps], start=1):
            tool_name = step.get("tool")
            spec = TOOL_CATALOG.get(tool_name)
            if spec is None:
                # Unreachable through constrained decoding; kept as a guard.
                outcome.refused_tools.append(str(tool_name))
                continue
            args = self._sanitize_arguments(spec, step.get("arguments"))
            args = self._resolve_placeholders(args, index, step_runs, known_ids)
            if args is None or self._has_unknown_id(args, known_ids):
                outcome.refused_tools.append(spec.name)
                continue
            run = self._execute(spec, args)
            outcome.tool_runs.append(run)
            step_runs[index] = run
            known_ids.update(
                str(record["id"]).lower()
                for record in run.records
                if record.get("id")
            )
        self._summarize(outcome)
        return outcome

    def _resolve_placeholders(self, args, index, step_runs, known_ids):
        """Replace ``$N.id`` values with the first record id of step N.

        Resolved ids come straight from a tool result, so they are grounded
        by construction and recorded in ``known_ids``. Returns None when a
        placeholder cannot be resolved (unknown step, failed parent, or
        parent with no records even after the fallback).
        """
        resolved = {}
        for key, value in args.items():
            match = PLACEHOLDER_RE.match(value.strip()) if isinstance(value, str) else None
            if not match:
                resolved[key] = value
                continue
            ref = int(match.group(1))
            if not (1 <= ref < index) or ref not in step_runs:
                return None
            parent = step_runs[ref]
            if not parent.records:
                self._retry_parent_without_status(parent)
            if parent.error or not parent.records or not parent.records[0].get("id"):
                return None
            parent_id = str(parent.records[0]["id"])
            known_ids.add(parent_id.lower())
            resolved[key] = parent_id
        return resolved

    def _retry_parent_without_status(self, parent):
        """Re-run an empty parent step once without its status filter.

        The planner is taught to filter parents (e.g. status "closed") so the
        first record is deterministically the right one; when that filter
        matches nothing (e.g. reviews held but never closed), retrying
        unfiltered keeps the newest-first ordering meaningful.
        """
        if "status" not in parent.arguments or parent.error:
            return
        retry_args = {k: v for k, v in parent.arguments.items() if k != "status"}
        retry = self._execute(TOOL_CATALOG[parent.tool], retry_args)
        if retry.error or not retry.records:
            return
        parent.arguments = retry_args
        parent.records = retry.records
        parent.cards = retry.cards
        parent.data = retry.data

    @staticmethod
    def _has_unknown_id(args, known_ids):
        """True when an id-like argument carries a value never seen before."""
        return any(
            (key == "id" or key.endswith("_id"))
            and str(value).lower() not in known_ids
            for key, value in args.items()
        )

    def _sanitize_arguments(self, spec, arguments):
        args = {}
        for key, value in (arguments or {}).items():
            if key not in spec.allowed_args:
                continue
            if isinstance(value, (dict, list)) or value in (None, ""):
                continue
            args[key] = value
        max_records = settings.AI_ASSISTANT_MAX_RECORDS_PER_TOOL
        if "limit" in spec.allowed_args:
            try:
                requested = int(args.get("limit", max_records))
            except (TypeError, ValueError):
                requested = max_records
            args["limit"] = max(1, min(requested, max_records))
        return args

    def _execute(self, spec, args):
        from mcp.api.views_mcp import get_mcp_server

        run = ToolRun(tool=spec.name, label=str(spec.label), icon=spec.icon, arguments=args)
        tool_def = get_mcp_server().get_tool(spec.name)
        if tool_def is None:
            logger.error("Assistant tool %s missing from the MCP registry", spec.name)
            run.error = TOOL_ERROR
            return run
        try:
            raw = tool_def["handler"](self.user, args)
        except Exception:
            logger.exception("Assistant tool %s failed", spec.name)
            run.error = TOOL_ERROR
            return run
        if isinstance(raw, dict) and raw.get("isError"):
            message = ""
            try:
                message = json.loads(raw["content"][0]["text"]).get("error", "")
            except (KeyError, IndexError, TypeError, ValueError):
                pass
            run.error = (
                PERMISSION_DENIED if str(message).startswith("Permission denied") else TOOL_ERROR
            )
            return run
        run.data = raw
        run.records = _extract_records(raw)[: settings.AI_ASSISTANT_MAX_RECORDS_PER_TOOL]
        run.cards = [spec.build_card(record) for record in run.records]
        return run

    def _summarize(self, outcome):
        successful = [run for run in outcome.tool_runs if not run.error]
        if not successful:
            return
        data = {}
        for run in successful:
            text = run.compact_json() or "[]"
            try:
                data[run.tool] = _strip_identifiers(json.loads(text))
            except ValueError:
                # Truncated payload: pass the raw text through, scrubbed.
                data[run.tool] = UUID_RE.sub("", text.lower())
        if outcome.permission_denied:
            data["note"] = "Some data was not accessible to this user."
        messages = [
            _system(summary_prompt(outcome.language)),
            _user(
                f"Question: {outcome.question}\n"
                f"Data: {json.dumps(data, default=str, ensure_ascii=False)}"
            ),
        ]
        try:
            outcome.summary = self.client.chat_text(messages) or None
        except (OllamaUnreachable, MalformedModelOutput):
            logger.warning("Assistant summary generation failed", exc_info=True)
            outcome.degraded = True

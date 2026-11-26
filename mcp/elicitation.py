# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Confirmations and comments asked of the user in the middle of a tool call.

Under the ``2026-07-28`` revision a server does not send requests of its own :
``tools/call`` answers with an ``InputRequiredResult`` that holds a form
(``elicitation/create``, form mode), the client shows it to the user and
retries the call with the answer in ``inputResponses``, echoing the
``requestState`` it was given. Cairn uses it for two moments :

- deleting a record, which cannot be undone : the user confirms;
- a lifecycle transition that asks for a comment, or whose target step carries
  a ``confirm`` trigger : the user writes the comment or confirms, as the
  lifecycle bar of the web interface asks.

What is asked never replaces a check : the tool still enforces the permission,
the scopes and the lifecycle rules when it runs, and a client that does not
declare elicitation is served as before. The question is only put to someone
who may perform the action, about a record they can reach, so the form never
tells anything the tool would not.

``requestState`` binds the answer to the person, the tool, its arguments and
the question, under the instance's ``SECRET_KEY`` (HMAC) and for ten minutes :
a confirmation given for one call is refused on any other.
"""

import hashlib
import json
from dataclasses import dataclass, field

from django.core import signing
from django.utils import translation
from django.utils.translation import gettext as _

REQUEST_STATE_SALT = "mcp.elicitation.request-state"
REQUEST_STATE_MAX_AGE = 600  # seconds


@dataclass
class Elicitation:
    """A form to put to the user before a tool runs.

    ``key`` names the question in ``inputRequests``; ``properties`` and
    ``required`` are the flat JSON Schema of the form; ``apply`` turns the
    accepted content into the arguments the tool runs with, or ``None`` when
    the answer does not let it run (an unticked confirmation, an empty
    comment).
    """

    key: str
    message: str
    properties: dict
    required: list = field(default_factory=list)
    apply: object = None

    def as_input_request(self):
        return {
            "method": "elicitation/create",
            "params": {
                "mode": "form",
                "message": self.message,
                "requestedSchema": {
                    "type": "object",
                    "properties": self.properties,
                    "required": list(self.required),
                },
            },
        }


@dataclass
class Outcome:
    """What :func:`resolve` decided : ask, refuse, or run with ``arguments``."""

    arguments: dict = None
    input_required: dict = None
    refused: dict = None


def asks(builder):
    """Decorate a tool handler with the question ``builder(user, arguments)`` puts.

    ``functools.wraps`` (used by ``require_perm``) carries the attribute to the
    wrapper, so it may be applied under or over the permission decorator.
    """
    def decorator(handler):
        handler.mcp_elicit = builder
        return handler
    return decorator


def _language(user):
    return getattr(user, "language", "") or translation.get_language() or "en"


def _digest(arguments):
    encoded = json.dumps(arguments or {}, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _request_state(user, tool_name, arguments, key):
    return signing.dumps(
        {"u": str(user.pk), "t": tool_name, "a": _digest(arguments), "k": key},
        salt=REQUEST_STATE_SALT,
        compress=True,
    )


def _state_holds(state, user, tool_name, arguments, key):
    if not isinstance(state, str) or not state:
        return False
    try:
        payload = signing.loads(state, salt=REQUEST_STATE_SALT, max_age=REQUEST_STATE_MAX_AGE)
    except signing.BadSignature:
        return False
    return payload == {"u": str(user.pk), "t": tool_name, "a": _digest(arguments), "k": key}


def _refusal(message):
    return {
        "content": [{"type": "text", "text": json.dumps({"error": message}, ensure_ascii=False)}],
        "isError": True,
    }


def _may_perform(tool_def, user):
    codename = getattr(tool_def["handler"], "required_perm", None)
    if not codename:
        return True
    return user.is_superuser or user.has_perm(codename)


def resolve(tool_def, user, arguments, params):
    """Decide whether the call runs, is refused, or asks the user first."""
    if user is None or not _may_perform(tool_def, user):
        return Outcome(arguments=arguments)
    with translation.override(_language(user)):
        question = tool_def["elicit"](user, arguments)
    if question is None:
        return Outcome(arguments=arguments)

    tool_name = tool_def["name"]
    responses = params.get("inputResponses")
    answer = responses.get(question.key) if isinstance(responses, dict) else None
    state = params.get("requestState")
    if not isinstance(answer, dict) or not _state_holds(state, user, tool_name, arguments, question.key):
        return Outcome(input_required={
            "resultType": "input_required",
            "inputRequests": {question.key: question.as_input_request()},
            "requestState": _request_state(user, tool_name, arguments, question.key),
        })

    action = answer.get("action")
    with translation.override(_language(user)):
        if action != "accept":
            return Outcome(refused=_refusal(
                _("The user did not confirm : nothing was changed.")
            ))
        content = answer.get("content") if isinstance(answer.get("content"), dict) else {}
        updated = question.apply(dict(arguments), content)
        if updated is None:
            return Outcome(refused=_refusal(
                _("The user did not confirm : nothing was changed.")
            ))
    return Outcome(arguments=updated)


# ── Questions ─────────────────────────────────────────────


def _record_words(obj):
    return {"type": str(obj._meta.verbose_name), "name": str(obj)}


def _confirmed(arguments, content):
    return arguments if content.get("confirm") is True else None


def confirm_deletion(model_class, fetch):
    """The question put before ``model_class`` is deleted.

    ``fetch(user, model_class, pk)`` reads the record within the user's
    reach; a record out of reach asks nothing, and the tool answers it as an
    unknown one.
    """
    def builder(user, arguments):
        pk = arguments.get("id")
        if not pk:
            return None
        try:
            obj = fetch(user, model_class, pk)
        except (model_class.DoesNotExist, ValueError, TypeError):
            return None
        except Exception:  # noqa: BLE001 - a malformed identifier asks nothing; the tool refuses it
            return None
        if getattr(obj, "is_deletable", True) is False:
            return None
        return Elicitation(
            key="confirm_deletion",
            message=_("Delete the %(type)s %(name)s? This cannot be undone.") % _record_words(obj),
            properties={
                "confirm": {
                    "type": "boolean",
                    "title": _("Delete"),
                    "description": _("Tick to delete the record."),
                    "default": False,
                },
            },
            required=["confirm"],
            apply=_confirmed,
        )
    return builder


def confirm_transition(model_class, fetch, target_param="target_state"):
    """The question put before a lifecycle transition, when its rules ask one.

    ``target_param`` names the argument that carries the target step
    (``target_status`` for the management review tool).

    A transition that requires a comment asks for it (when the call carries
    none); a target step with a ``confirm`` trigger asks for a confirmation,
    with the message of the trigger. A transition the user may not perform,
    or that does not exist, asks nothing : the tool refuses it.
    """
    def builder(user, arguments):
        from core.lifecycle import user_can_perform

        pk = arguments.get("id")
        target = arguments.get(target_param)
        if not pk or not target:
            return None
        try:
            obj = fetch(user, model_class, pk)
        except Exception:  # noqa: BLE001 - unknown or malformed : the tool answers it
            return None
        lifecycle = obj.get_lifecycle()
        current = obj.workflow_state or lifecycle.initial_step.code
        if not lifecycle.has_step(target):
            return None
        transition = lifecycle.find_transition(current, target)
        if transition is None or not user_can_perform(transition, obj, user):
            return None

        needs_comment = transition.requires_comment and not str(arguments.get("comment") or "").strip()
        trigger = lifecycle.step(target).confirm_trigger
        if not needs_comment and trigger is None:
            return None

        step_label = str(lifecycle.step(target).label)
        custom = (trigger.config or {}).get("message") if trigger is not None else ""
        message = str(custom) if custom else _("Move the %(type)s %(name)s to %(step)s?") % {
            **_record_words(obj), "step": step_label,
        }

        if needs_comment:
            def apply(arguments, content):
                comment = str(content.get("comment") or "").strip()
                if not comment:
                    return None
                arguments["comment"] = comment
                return arguments

            return Elicitation(
                key="transition_comment",
                message=message,
                properties={
                    "comment": {
                        "type": "string",
                        "title": _("Comment"),
                        "description": _("Required by this transition, kept in the history of the record."),
                        "minLength": 1,
                    },
                },
                required=["comment"],
                apply=apply,
            )
        return Elicitation(
            key="confirm_transition",
            message=message,
            properties={
                "confirm": {
                    "type": "boolean",
                    "title": str(transition.label) or step_label,
                    "description": _("Tick to perform the transition."),
                    "default": False,
                },
            },
            required=["confirm"],
            apply=_confirmed,
        )
    return builder

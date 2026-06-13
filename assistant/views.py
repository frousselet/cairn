import uuid

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from assistant.engine import AssistantEngine
from assistant.models import AssistantFeedback
from assistant.providers import (
    AssistantDisabled,
    MalformedModelOutput,
    ModelNotAvailable,
    ServiceUnreachable,
)

QUESTION_MIN_LENGTH = 3
QUESTION_MAX_LENGTH = 500
COMMENT_MAX_LENGTH = 2000

# Key under which the last rendered answer is stashed in the session so that
# feedback is bound to the server-generated answer (faithful, not spoofable).
ANSWER_SESSION_KEY = "assistant_last_answer"

# Human-friendly names for the configured LLM backend, shown in the disclaimer.
PROVIDER_LABELS = {"mistral": "Mistral", "ollama": "Ollama"}


def _powered_by():
    """Return the "<Provider> <model>" label for the active backend."""
    provider = (settings.AI_ASSISTANT_PROVIDER or "").lower()
    label = PROVIDER_LABELS.get(provider, provider.title() or "AI")
    return f"{label} {settings.AI_ASSISTANT_MODEL}"


def _stash_answer(request, outcome):
    """Store the answer in the session and return its feedback token.

    Only successful answers (a summary or at least one record card) are
    stashed; the token is rendered in the partial and posted back with the
    rating so the feedback row carries the exact server-generated response.
    """
    if not (outcome.summary or outcome.has_cards):
        request.session.pop(ANSWER_SESSION_KEY, None)
        return None
    token = uuid.uuid4().hex
    request.session[ANSWER_SESSION_KEY] = {
        "token": token,
        "question": outcome.question,
        "language": outcome.language,
        "summary": outcome.summary or "",
        "results": [
            {"tool": run.tool, "label": str(run.label), "records": run.cards}
            for run in outcome.tool_runs
            if not run.error
        ],
        "degraded": outcome.degraded,
        "refused_tools": [str(t) for t in outcome.refused_tools],
        "provider": settings.AI_ASSISTANT_PROVIDER,
        "model_name": settings.AI_ASSISTANT_MODEL,
    }
    return token


class AskAssistantView(LoginRequiredMixin, View):
    """Answer a natural-language question with the palette HTML partial.

    Always returns 200 with the partial; error states are rendered inside it
    so the palette JavaScript keeps a single happy path.
    """

    http_method_names = ["post"]

    def post(self, request):
        question = (request.POST.get("q") or "").strip()
        context = {
            "model_name": settings.AI_ASSISTANT_MODEL,
            "powered_by": _powered_by(),
        }
        if not (QUESTION_MIN_LENGTH <= len(question) <= QUESTION_MAX_LENGTH):
            context["error_code"] = "invalid"
            return render(request, "assistant/_answer.html", context)
        engine = AssistantEngine(
            request.user,
            language=getattr(request, "LANGUAGE_CODE", "en"),
        )
        try:
            outcome = engine.ask(question)
            context["outcome"] = outcome
            context["feedback_token"] = _stash_answer(request, outcome)
        except AssistantDisabled:
            context["error_code"] = "disabled"
        except ModelNotAvailable:
            context["error_code"] = "model_missing"
        except ServiceUnreachable:
            context["error_code"] = "unreachable"
        except MalformedModelOutput:
            context["error_code"] = "model_error"
        return render(request, "assistant/_answer.html", context)


class AssistantFeedbackView(LoginRequiredMixin, View):
    """Record thumbs up/down (and an optional comment) on the last answer.

    The answer content is read from the session (stashed by AskAssistantView),
    not from the client, so the stored feedback faithfully reflects what the
    LLM produced. Returns a small confirmation partial.
    """

    http_method_names = ["post"]

    def post(self, request):
        token = (request.POST.get("answer_id") or "").strip()
        rating = (request.POST.get("rating") or "").strip()
        comment = (request.POST.get("comment") or "").strip()[:COMMENT_MAX_LENGTH]
        stashed = request.session.get(ANSWER_SESSION_KEY)
        valid = (
            rating in (AssistantFeedback.RATING_UP, AssistantFeedback.RATING_DOWN)
            and stashed
            and stashed.get("token") == token
        )
        if not valid:
            return render(request, "assistant/_feedback_done.html", {"error": True})
        AssistantFeedback.objects.create(
            user=request.user,
            question=stashed["question"],
            language=stashed.get("language", ""),
            rating=rating,
            comment=comment,
            summary=stashed.get("summary", ""),
            results=stashed.get("results", []),
            degraded=stashed.get("degraded", False),
            refused_tools=stashed.get("refused_tools", []),
            provider=stashed.get("provider", ""),
            model_name=stashed.get("model_name", ""),
        )
        # One feedback per answer: drop the stash to block double submission.
        request.session.pop(ANSWER_SESSION_KEY, None)
        return render(request, "assistant/_feedback_done.html", {"error": False})

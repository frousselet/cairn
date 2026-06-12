from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from assistant.engine import AssistantEngine
from assistant.ollama import (
    AssistantDisabled,
    MalformedModelOutput,
    ModelNotAvailable,
    OllamaUnreachable,
)

QUESTION_MIN_LENGTH = 3
QUESTION_MAX_LENGTH = 500


class AskAssistantView(LoginRequiredMixin, View):
    """Answer a natural-language question with the palette HTML partial.

    Always returns 200 with the partial; error states are rendered inside it
    so the palette JavaScript keeps a single happy path.
    """

    http_method_names = ["post"]

    def post(self, request):
        question = (request.POST.get("q") or "").strip()
        context = {"model_name": settings.AI_ASSISTANT_MODEL}
        if not (QUESTION_MIN_LENGTH <= len(question) <= QUESTION_MAX_LENGTH):
            context["error_code"] = "invalid"
            return render(request, "assistant/_answer.html", context)
        engine = AssistantEngine(
            request.user,
            language=getattr(request, "LANGUAGE_CODE", "en"),
        )
        try:
            context["outcome"] = engine.ask(question)
        except AssistantDisabled:
            context["error_code"] = "disabled"
        except ModelNotAvailable:
            context["error_code"] = "model_missing"
        except OllamaUnreachable:
            context["error_code"] = "unreachable"
        except MalformedModelOutput:
            context["error_code"] = "model_error"
        return render(request, "assistant/_answer.html", context)

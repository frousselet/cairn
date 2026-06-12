from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from assistant.api.serializers import AskRequestSerializer
from assistant.engine import AssistantEngine
from assistant.ollama import (
    AssistantDisabled,
    MalformedModelOutput,
    ModelNotAvailable,
    OllamaUnreachable,
)


class AskAssistantApiView(APIView):
    """POST /api/v1/assistant/ask/ : natural-language question endpoint."""

    def post(self, request):
        serializer = AskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        language = serializer.validated_data.get("language") or getattr(
            request, "LANGUAGE_CODE", "en"
        )
        engine = AssistantEngine(request.user, language=language)
        try:
            outcome = engine.ask(serializer.validated_data["q"])
        except AssistantDisabled:
            return self._unavailable("assistant_disabled", "The AI assistant is disabled.")
        except ModelNotAvailable as exc:
            return self._unavailable(
                "model_missing", f"Model not available on Ollama: {exc}"
            )
        except OllamaUnreachable:
            return self._unavailable(
                "assistant_unreachable", "The Ollama service is unreachable."
            )
        except MalformedModelOutput:
            return self._unavailable(
                "model_error", "The model could not produce a usable answer."
            )
        return Response(outcome.as_dict())

    @staticmethod
    def _unavailable(code, detail):
        return Response(
            {"code": code, "detail": detail},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

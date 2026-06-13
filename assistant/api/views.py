from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from assistant.api.serializers import AskRequestSerializer, AssistantFeedbackSerializer
from assistant.engine import AssistantEngine
from assistant.models import AssistantFeedback
from assistant.providers import (
    AssistantDisabled,
    MalformedModelOutput,
    ModelNotAvailable,
    ServiceUnreachable,
)

FEEDBACK_READ_PERM = "system.assistant_feedback.read"


class AssistantFeedbackPermission(BasePermission):
    """Any authenticated user may submit feedback; reading and exporting the
    collected feedback requires the system permission."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action == "create":
            return True
        return user.is_superuser or user.has_perm(FEEDBACK_READ_PERM)


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
                "model_missing", f"The configured model is not available: {exc}"
            )
        except ServiceUnreachable:
            return self._unavailable(
                "assistant_unreachable", "The AI service is unreachable."
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


class AssistantFeedbackViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Submit (create), list and export Ask Cairn answer feedback.

    Creating feedback is open to any authenticated user; listing, retrieving
    and exporting require ``system.assistant_feedback.read``. The ``export``
    action returns the full structured set ready to hand to an improvement LLM.
    """

    queryset = AssistantFeedback.objects.select_related("user").all()
    serializer_class = AssistantFeedbackSerializer
    permission_classes = [AssistantFeedbackPermission]
    filterset_fields = ["rating", "language", "provider"]
    search_fields = ["question", "comment", "summary"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user if user.is_authenticated else None)

    @action(detail=False, methods=["get"])
    def export(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        feedback = [obj.as_export_dict() for obj in queryset]
        return Response({"count": len(feedback), "feedback": feedback})

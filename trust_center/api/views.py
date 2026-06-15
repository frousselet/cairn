"""Internal (authenticated) management API for the Trust Center.

Behind ``IsAuthenticated`` + ``ModulePermission`` (module ``trust_center``).
Curators create / edit the link entities and drive their publication workflow
here; the public surface is served by ``public_views``.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api.permissions import ModulePermission
from core.workflow import PermissionDeniedError, WorkflowError
from trust_center.models import (
    TrustCenterCertification,
    TrustCenterDocument,
    TrustCenterMeasure,
    TrustCenterSettings,
    TrustCenterSubprocessor,
)
from trust_center.transition_messages import transition_error_detail

from .serializers import (
    CertificationSerializer,
    DocumentSerializer,
    MeasureSerializer,
    SubprocessorSerializer,
    TransitionSerializer,
    TrustCenterSettingsSerializer,
)


class TrustCenterSettingsView(APIView):
    """Retrieve / update the Trust Center settings singleton."""

    permission_classes = [ModulePermission]
    permission_module = "trust_center"
    permission_feature = "settings"

    def get(self, request):
        return Response(TrustCenterSettingsSerializer(TrustCenterSettings.get()).data)

    def put(self, request):
        instance = TrustCenterSettings.get()
        ser = TrustCenterSettingsSerializer(instance, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class _ManagedViewSet(viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "trust_center"
    custom_action_map = {"transition": "update"}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        obj = self.get_object()
        ser = TransitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj.transition_to(
                ser.validated_data["target_state"],
                request.user,
                comment=ser.validated_data.get("comment", ""),
                enforce_permission=True,
            )
        except PermissionDeniedError as exc:
            return Response(
                {"detail": transition_error_detail(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except WorkflowError as exc:
            return Response(
                {"detail": transition_error_detail(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.get_serializer(obj).data)


class CertificationViewSet(_ManagedViewSet):
    queryset = TrustCenterCertification.objects.select_related("framework").all()
    serializer_class = CertificationSerializer
    permission_feature = "certification"
    search_fields = ["public_label", "public_description"]
    ordering_fields = ["display_order", "public_label", "created_at"]


class SubprocessorViewSet(_ManagedViewSet):
    queryset = TrustCenterSubprocessor.objects.select_related("supplier").all()
    serializer_class = SubprocessorSerializer
    permission_feature = "subprocessor"
    search_fields = ["public_name", "purpose", "public_country"]
    ordering_fields = ["display_order", "public_name", "created_at"]


class MeasureViewSet(_ManagedViewSet):
    queryset = TrustCenterMeasure.objects.all()
    serializer_class = MeasureSerializer
    permission_feature = "measure"
    search_fields = ["title", "description"]
    ordering_fields = ["display_order", "title", "created_at"]


class DocumentViewSet(_ManagedViewSet):
    queryset = TrustCenterDocument.objects.select_related("report").all()
    serializer_class = DocumentSerializer
    permission_feature = "document"
    search_fields = ["title", "description"]
    ordering_fields = ["display_order", "title", "created_at"]

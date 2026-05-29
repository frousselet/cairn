from rest_framework import viewsets

from accounts.api.mixins import (
    ApprovableAPIMixin,
    BatchCreateMixin,
    HistoryAPIMixin,
)
from context.api.permissions import ContextPermission
from risks.api.views import CreatedByMixin
from risks.models import (
    BaselineGap,
    EbiosWorkshopProgress,
    FearedEvent,
    SecurityBaseline,
    StudyFramework,
)

from .filters import (
    BaselineGapFilter,
    EbiosWorkshopProgressFilter,
    FearedEventFilter,
    SecurityBaselineFilter,
    StudyFrameworkFilter,
)
from .serializers import (
    BaselineGapSerializer,
    EbiosWorkshopProgressSerializer,
    FearedEventSerializer,
    SecurityBaselineSerializer,
    StudyFrameworkSerializer,
)


class StudyFrameworkViewSet(
    HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        StudyFramework.objects.select_related("assessment")
        .prefetch_related("participants", "applicable_frameworks")
        .all()
    )
    serializer_class = StudyFrameworkSerializer
    filterset_class = StudyFrameworkFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_assessment"
    search_fields = ["reference", "mission_statement", "business_perimeter"]
    ordering_fields = ["reference", "status", "created_at"]


class EbiosWorkshopProgressViewSet(
    BatchCreateMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        EbiosWorkshopProgress.objects.select_related("assessment", "validated_by").all()
    )
    serializer_class = EbiosWorkshopProgressSerializer
    filterset_class = EbiosWorkshopProgressFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_assessment"
    search_fields = ["reference", "notes"]
    ordering_fields = [
        "reference",
        "workshop_number",
        "iteration_number",
        "status",
        "created_at",
    ]


class SecurityBaselineViewSet(
    ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        SecurityBaseline.objects.select_related("assessment")
        .prefetch_related(
            "business_values",
            "essential_assets",
            "support_assets",
            "baseline_references",
        )
        .all()
    )
    serializer_class = SecurityBaselineSerializer
    filterset_class = SecurityBaselineFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_baseline"
    search_fields = ["reference", "dic_summary"]
    ordering_fields = ["reference", "status", "created_at"]


class FearedEventViewSet(
    BatchCreateMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = FearedEvent.objects.select_related("baseline", "essential_asset").all()
    serializer_class = FearedEventSerializer
    filterset_class = FearedEventFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_baseline"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "order", "gravity_level", "created_at"]


class BaselineGapViewSet(
    BatchCreateMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        BaselineGap.objects.select_related("baseline", "linked_requirement")
        .prefetch_related("affected_support_assets")
        .all()
    )
    serializer_class = BaselineGapSerializer
    filterset_class = BaselineGapFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_baseline"
    search_fields = ["reference", "reference_source", "description"]
    ordering_fields = ["reference", "order", "severity", "status", "created_at"]

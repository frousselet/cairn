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
    RiskSource,
    RiskSourceObjectivePair,
    SecurityBaseline,
    StudyFramework,
    TargetedObjective,
)

from .filters import (
    BaselineGapFilter,
    EbiosWorkshopProgressFilter,
    FearedEventFilter,
    RiskSourceFilter,
    RiskSourceObjectivePairFilter,
    SecurityBaselineFilter,
    StudyFrameworkFilter,
    TargetedObjectiveFilter,
)
from .serializers import (
    BaselineGapSerializer,
    EbiosWorkshopProgressSerializer,
    FearedEventSerializer,
    RiskSourceObjectivePairSerializer,
    RiskSourceSerializer,
    SecurityBaselineSerializer,
    StudyFrameworkSerializer,
    TargetedObjectiveSerializer,
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


class RiskSourceViewSet(
    BatchCreateMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = RiskSource.objects.select_related("assessment").all()
    serializer_class = RiskSourceSerializer
    filterset_class = RiskSourceFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_risk_source"
    search_fields = ["reference", "name", "description", "motivation_description"]
    ordering_fields = [
        "reference",
        "name",
        "threat_level",
        "is_retained",
        "created_at",
    ]


class TargetedObjectiveViewSet(
    BatchCreateMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        TargetedObjective.objects.select_related("risk_source")
        .prefetch_related("targeted_essential_assets", "targeted_feared_events")
        .all()
    )
    serializer_class = TargetedObjectiveSerializer
    filterset_class = TargetedObjectiveFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_risk_source"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "order", "is_retained", "created_at"]


class RiskSourceObjectivePairViewSet(
    BatchCreateMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        RiskSourceObjectivePair.objects.select_related(
            "assessment", "risk_source", "targeted_objective"
        ).all()
    )
    serializer_class = RiskSourceObjectivePairSerializer
    filterset_class = RiskSourceObjectivePairFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_risk_source"
    search_fields = ["reference", "relevance_justification", "retention_justification"]
    ordering_fields = [
        "reference",
        "priority_score",
        "relevance",
        "is_retained",
        "created_at",
    ]

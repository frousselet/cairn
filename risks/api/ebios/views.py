from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.api.mixins import (
    ApprovableAPIMixin,
    BatchCreateMixin,
    HistoryAPIMixin,
)
from context.api.permissions import ContextPermission
from risks.api.views import CreatedByMixin
from risks.models import (
    AttackPathStep,
    BaselineGap,
    EbiosWorkshopProgress,
    EcosystemStakeholder,
    FearedEvent,
    RiskSource,
    RiskSourceObjectivePair,
    SecurityBaseline,
    StrategicScenario,
    StudyFramework,
    TargetedObjective,
)

from .filters import (
    AttackPathStepFilter,
    BaselineGapFilter,
    EbiosWorkshopProgressFilter,
    EcosystemStakeholderFilter,
    FearedEventFilter,
    RiskSourceFilter,
    RiskSourceObjectivePairFilter,
    SecurityBaselineFilter,
    StrategicScenarioFilter,
    StudyFrameworkFilter,
    TargetedObjectiveFilter,
)
from .serializers import (
    AttackPathStepSerializer,
    BaselineGapSerializer,
    EbiosWorkshopProgressSerializer,
    EcosystemStakeholderSerializer,
    FearedEventSerializer,
    RiskSourceObjectivePairSerializer,
    RiskSourceSerializer,
    SecurityBaselineSerializer,
    StrategicScenarioSerializer,
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


class EcosystemStakeholderViewSet(
    BatchCreateMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        EcosystemStakeholder.objects.select_related("assessment", "stakeholder", "supplier")
        .prefetch_related("accessible_support_assets")
        .all()
    )
    serializer_class = EcosystemStakeholderSerializer
    filterset_class = EcosystemStakeholderFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_ecosystem"
    search_fields = ["reference", "name", "description", "attack_vector_justification"]
    ordering_fields = [
        "reference",
        "name",
        "threat_level",
        "threat_zone",
        "is_attack_vector",
        "created_at",
    ]

    @action(detail=False, methods=["get"], url_path="graph")
    def graph(self, request):
        """Return the ecosystem graph as nodes + edges + zone metadata.

        Filter by `?assessment=<uuid>` to scope the graph to a single
        assessment (the only meaningful aggregation today).
        """
        qs = self.filter_queryset(self.get_queryset())
        nodes = []
        edges = []
        for stakeholder in qs.prefetch_related("accessible_support_assets"):
            nodes.append({
                "id": str(stakeholder.pk),
                "reference": stakeholder.reference,
                "name": stakeholder.name,
                "category": stakeholder.category,
                "threat_level": (
                    float(stakeholder.threat_level)
                    if stakeholder.threat_level is not None
                    else None
                ),
                "threat_zone": stakeholder.threat_zone,
                "is_attack_vector": stakeholder.is_attack_vector,
            })
            for asset in stakeholder.accessible_support_assets.all():
                edges.append({
                    "source": str(stakeholder.pk),
                    "target": str(asset.pk),
                    "target_kind": "support_asset",
                    "target_reference": asset.reference,
                })
        return Response({
            "nodes": nodes,
            "edges": edges,
            "zones": ["control", "monitoring", "danger"],
        })


class StrategicScenarioViewSet(
    BatchCreateMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        StrategicScenario.objects.select_related(
            "assessment", "sr_ov_pair", "consolidated_risk"
        )
        .prefetch_related("targeted_feared_events", "attack_path_steps")
        .all()
    )
    serializer_class = StrategicScenarioSerializer
    filterset_class = StrategicScenarioFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_strategic"
    search_fields = [
        "reference", "name", "description",
        "gravity_justification", "likelihood_justification",
    ]
    ordering_fields = [
        "reference",
        "name",
        "risk_level",
        "gravity_level",
        "likelihood_level",
        "is_retained",
        "created_at",
    ]


class AttackPathStepViewSet(
    BatchCreateMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = AttackPathStep.objects.select_related("scenario", "stakeholder").all()
    serializer_class = AttackPathStepSerializer
    filterset_class = AttackPathStepFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_strategic"
    search_fields = ["reference", "description"]
    ordering_fields = ["reference", "order", "action_type", "created_at"]

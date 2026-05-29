from collections import Counter, defaultdict

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.api.mixins import (
    ApprovableAPIMixin,
    BatchCreateMixin,
    HistoryAPIMixin,
)
from context.api.permissions import ContextPermission
from risks.api.views import CreatedByMixin
from risks.constants import MitreAttackTactic, RiskSourceType
from risks.models import (
    AttackPathStep,
    AttackTechnique,
    BaselineGap,
    EbiosSummary,
    EbiosWorkshopProgress,
    EcosystemStakeholder,
    FearedEvent,
    MitreAttackTechnique,
    OperationalScenario,
    PACSMeasure,
    Risk,
    RiskSource,
    RiskSourceObjectivePair,
    SecurityBaseline,
    StrategicScenario,
    StudyFramework,
    TargetedObjective,
)

from .filters import (
    AttackPathStepFilter,
    AttackTechniqueFilter,
    BaselineGapFilter,
    EbiosSummaryFilter,
    EbiosWorkshopProgressFilter,
    EcosystemStakeholderFilter,
    FearedEventFilter,
    MitreAttackTechniqueFilter,
    OperationalScenarioFilter,
    PACSMeasureFilter,
    RiskSourceFilter,
    RiskSourceObjectivePairFilter,
    SecurityBaselineFilter,
    StrategicScenarioFilter,
    StudyFrameworkFilter,
    TargetedObjectiveFilter,
)
from .serializers import (
    AttackPathStepSerializer,
    AttackTechniqueSerializer,
    BaselineGapSerializer,
    EbiosSummarySerializer,
    EbiosWorkshopProgressSerializer,
    EcosystemStakeholderSerializer,
    FearedEventSerializer,
    MitreAttackTechniqueSerializer,
    OperationalScenarioSerializer,
    PACSMeasureSerializer,
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


class MitreAttackTechniqueViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only catalogue of MITRE ATT&CK techniques (Enterprise Matrix).

    The catalogue is seeded once at install via
    `risks/migrations/0022_seed_mitre_attack_catalog.py` and can be refreshed
    by running `python manage.py refresh_mitre_attack <json>`. No mutating
    operation is exposed: clients reference techniques through their UUID
    or the natural `mitre_id`.
    """

    queryset = MitreAttackTechnique.objects.select_related("parent_technique").all()
    serializer_class = MitreAttackTechniqueSerializer
    filterset_class = MitreAttackTechniqueFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_operational"
    search_fields = ["mitre_id", "name", "description"]
    ordering_fields = ["mitre_id", "name", "tactic", "version"]


class OperationalScenarioViewSet(
    BatchCreateMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        OperationalScenario.objects.select_related(
            "assessment", "strategic_scenario", "consolidated_risk"
        )
        .prefetch_related("targeted_support_assets", "attack_techniques", "existing_measures")
        .all()
    )
    serializer_class = OperationalScenarioSerializer
    filterset_class = OperationalScenarioFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_operational"
    search_fields = [
        "reference", "name", "description",
        "gravity_override_justification", "likelihood_justification",
    ]
    ordering_fields = [
        "reference",
        "name",
        "risk_level",
        "likelihood_v",
        "gravity_level",
        "created_at",
    ]

    @action(detail=True, methods=["post"], url_path="consolidate")
    def consolidate(self, request, pk=None):
        """Create a Risk in the unified register from this operational scenario.

        The new risk inherits gravity, likelihood, support assets and a
        copy of the criteria_snapshot. Idempotent: if the scenario already
        carries a consolidated_risk, the existing Risk is returned with a
        200 status instead of being duplicated.
        """
        scenario = self.get_object()
        if scenario.consolidated_risk_id:
            from risks.api.serializers import RiskSerializer
            data = RiskSerializer(scenario.consolidated_risk).data
            return Response(
                {"status": "already_consolidated", "risk": data},
                status=status.HTTP_200_OK,
            )

        risk = Risk.objects.create(
            assessment=scenario.assessment,
            name=scenario.name,
            description=scenario.description,
            risk_source=RiskSourceType.EBIOS_OPERATIONAL,
            source_entity_id=scenario.pk,
            source_entity_type="risks.OperationalScenario",
            initial_likelihood=scenario.likelihood_v,
            initial_impact=scenario.gravity_level,
            current_likelihood=scenario.likelihood_v,
            current_impact=scenario.gravity_level,
            criteria_snapshot=scenario.criteria_snapshot,
            created_by=request.user,
        )
        risk.affected_support_assets.set(scenario.targeted_support_assets.all())
        scenario.consolidated_risk = risk
        scenario.save(update_fields=["consolidated_risk"])

        from risks.api.serializers import RiskSerializer
        return Response(
            {"status": "consolidated", "risk": RiskSerializer(risk).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="mitre-heatmap")
    def mitre_heatmap(self, request):
        """Return a MITRE ATT&CK heatmap of techniques used across scenarios.

        The result groups attack techniques by tactic and counts the usages
        per technique. Filter with `?assessment=<uuid>` to restrict the
        aggregation to a single assessment.
        """
        scenario_qs = self.filter_queryset(self.get_queryset())
        technique_qs = AttackTechnique.objects.filter(
            scenario__in=scenario_qs,
            mitre_technique__isnull=False,
        ).select_related("mitre_technique")

        counts = Counter()
        labels = {}
        tactic_for_tech = {}
        for technique in technique_qs:
            mid = technique.mitre_technique.mitre_id
            counts[mid] += 1
            labels[mid] = technique.mitre_technique.name
            tactic_for_tech[mid] = technique.mitre_technique.tactic

        grouped = defaultdict(list)
        for mid, count in counts.items():
            grouped[tactic_for_tech[mid]].append({
                "mitre_id": mid,
                "name": labels[mid],
                "count": count,
            })

        heatmap = []
        for tactic in MitreAttackTactic:
            heatmap.append({
                "tactic": tactic.value,
                "tactic_label": tactic.label,
                "techniques": sorted(
                    grouped.get(tactic.value, []),
                    key=lambda item: (-item["count"], item["mitre_id"]),
                ),
            })
        return Response({
            "heatmap": heatmap,
            "total_techniques": sum(counts.values()),
        })


class AttackTechniqueViewSet(
    BatchCreateMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = AttackTechnique.objects.select_related(
        "scenario", "mitre_technique", "targeted_support_asset",
    ).all()
    serializer_class = AttackTechniqueSerializer
    filterset_class = AttackTechniqueFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_operational"
    search_fields = ["reference", "custom_name", "description"]
    ordering_fields = ["reference", "order", "difficulty", "created_at"]


class EbiosSummaryViewSet(
    ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        EbiosSummary.objects.select_related("assessment", "validated_by")
        .prefetch_related("pacs_measures")
        .all()
    )
    serializer_class = EbiosSummarySerializer
    filterset_class = EbiosSummaryFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_summary"
    search_fields = ["reference", "residual_risk_strategy", "monitoring_plan", "pacs_summary"]
    ordering_fields = ["reference", "status", "created_at"]

    @action(detail=True, methods=["post"], url_path="capture-mappings")
    def capture_mappings(self, request, pk=None):
        """Capture the current risk register into the before / after JSON slots.

        Query params (POST body fields):
        - `capture_before` (bool, default true)
        - `capture_after` (bool, default true)
        """
        summary = self.get_object()
        capture_before = request.data.get("capture_before", True)
        capture_after = request.data.get("capture_after", True)
        # DRF parses JSON booleans natively; tolerate strings too.
        if isinstance(capture_before, str):
            capture_before = capture_before.lower() in ("1", "true", "yes")
        if isinstance(capture_after, str):
            capture_after = capture_after.lower() in ("1", "true", "yes")
        summary.capture_risk_mappings(
            capture_before=capture_before,
            capture_after=capture_after,
        )
        summary.refresh_from_db()
        serializer = self.get_serializer(summary)
        return Response(serializer.data)


class PACSMeasureViewSet(
    BatchCreateMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet
):
    queryset = (
        PACSMeasure.objects.select_related("summary", "owner")
        .prefetch_related(
            "linked_treatment_plans",
            "linked_baseline_gaps",
            "linked_requirements",
        )
        .all()
    )
    serializer_class = PACSMeasureSerializer
    filterset_class = PACSMeasureFilter
    permission_classes = [ContextPermission]
    permission_feature = "ebios_summary"
    search_fields = ["reference", "name", "description", "expected_gain"]
    ordering_fields = [
        "reference",
        "name",
        "priority",
        "status",
        "target_date",
        "order",
        "created_at",
    ]

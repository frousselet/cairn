from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"study-frameworks", views.StudyFrameworkViewSet)
router.register(r"workshops", views.EbiosWorkshopProgressViewSet)
router.register(r"baselines", views.SecurityBaselineViewSet)
router.register(r"feared-events", views.FearedEventViewSet)
router.register(r"baseline-gaps", views.BaselineGapViewSet)
router.register(r"risk-sources", views.RiskSourceViewSet)
router.register(r"targeted-objectives", views.TargetedObjectiveViewSet)
router.register(r"sr-ov-pairs", views.RiskSourceObjectivePairViewSet)
router.register(r"ecosystem-stakeholders", views.EcosystemStakeholderViewSet)
router.register(r"strategic-scenarios", views.StrategicScenarioViewSet)
router.register(r"attack-path-steps", views.AttackPathStepViewSet)
router.register(r"mitre-techniques", views.MitreAttackTechniqueViewSet)
router.register(r"operational-scenarios", views.OperationalScenarioViewSet)
router.register(r"attack-techniques", views.AttackTechniqueViewSet)
router.register(r"summaries", views.EbiosSummaryViewSet)
router.register(r"pacs-measures", views.PACSMeasureViewSet)


urlpatterns = [
    path("", include(router.urls)),
]

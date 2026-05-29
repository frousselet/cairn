import factory

from context.tests.factories import ScopeFactory
from risks.constants import (
    AcceptanceStatus,
    ActionStatus,
    AttackDifficulty,
    AttackPathActionType,
    BaselineGapStatus,
    DICCriterion,
    EbiosBaselineStatus,
    EbiosIterationType,
    EbiosStudyFrameworkStatus,
    EbiosWorkshopNumber,
    EbiosWorkshopStatus,
    EcosystemStakeholderCategory,
    Methodology,
    Relevance,
    RiskSourceCategory,
    Severity,
    TargetedObjectiveCategory,
    ThreatType,
    TreatmentPlanStatus,
    TreatmentType,
)
from risks.models import (
    AttackPathStep,
    BaselineGap,
    EbiosWorkshopProgress,
    EcosystemStakeholder,
    FearedEvent,
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskSource,
    RiskSourceObjectivePair,
    RiskTreatmentPlan,
    SecurityBaseline,
    StrategicScenario,
    StudyFramework,
    TargetedObjective,
    Threat,
    TreatmentAction,
    Vulnerability,
)
from risks.models.risk_criteria import RiskCriteria, RiskLevel, ScaleLevel


class RiskCriteriaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskCriteria

    name = factory.Sequence(lambda n: f"Criteria {n}")
    status = "active"

    @factory.post_generation
    def scope(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.scopes.add(extracted)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class ScaleLevelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScaleLevel

    criteria = factory.SubFactory(RiskCriteriaFactory)
    level = 1
    name = "Level"


class RiskLevelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskLevel

    criteria = factory.SubFactory(RiskCriteriaFactory)
    level = 1
    name = "Low"
    color = "#4caf50"


class RiskAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskAssessment

    reference = factory.Sequence(lambda n: f"RA-{n:03d}")
    name = factory.Sequence(lambda n: f"Assessment {n}")

    @factory.post_generation
    def scope(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.scopes.add(extracted)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class RiskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Risk

    assessment = factory.SubFactory(RiskAssessmentFactory)
    reference = factory.Sequence(lambda n: f"RSK-{n:03d}")
    name = factory.Sequence(lambda n: f"Risk {n}")


class ThreatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Threat

    name = factory.Sequence(lambda n: f"Threat {n}")
    type = ThreatType.DELIBERATE

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class VulnerabilityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vulnerability

    name = factory.Sequence(lambda n: f"Vulnerability {n}")
    severity = "medium"

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class RiskTreatmentPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskTreatmentPlan

    risk = factory.SubFactory(RiskFactory)
    name = factory.Sequence(lambda n: f"Treatment plan {n}")
    treatment_type = TreatmentType.MITIGATE
    status = TreatmentPlanStatus.PLANNED


class TreatmentActionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TreatmentAction

    treatment_plan = factory.SubFactory(RiskTreatmentPlanFactory)
    description = factory.Sequence(lambda n: f"Action {n}")
    status = ActionStatus.PLANNED
    order = factory.Sequence(lambda n: n)


class RiskAcceptanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskAcceptance

    risk = factory.SubFactory(RiskFactory)
    justification = factory.Sequence(lambda n: f"Justification {n}")
    status = AcceptanceStatus.ACTIVE


class ISO27005RiskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ISO27005Risk

    assessment = factory.SubFactory(RiskAssessmentFactory)
    threat = factory.SubFactory(ThreatFactory)
    vulnerability = factory.SubFactory(VulnerabilityFactory)


# EBIOS RM factories (workshops W0 and W1)

class EbiosAssessmentFactory(RiskAssessmentFactory):
    """RiskAssessment with methodology=ebios_rm.

    The post_save signal `bootstrap_ebios_artifacts` automatically creates
    one StudyFramework, one SecurityBaseline and six EbiosWorkshopProgress
    rows when the assessment is persisted.
    """

    methodology = Methodology.EBIOS_RM


class StudyFrameworkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudyFramework
        django_get_or_create = ("assessment",)

    assessment = factory.SubFactory(EbiosAssessmentFactory)
    mission_statement = factory.Sequence(lambda n: f"Mission {n}")
    status = EbiosStudyFrameworkStatus.DRAFT


class EbiosWorkshopProgressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EbiosWorkshopProgress
        django_get_or_create = (
            "assessment",
            "workshop_number",
            "iteration_type",
            "iteration_number",
        )

    assessment = factory.SubFactory(EbiosAssessmentFactory)
    workshop_number = EbiosWorkshopNumber.W0
    iteration_type = EbiosIterationType.STRATEGIC
    iteration_number = 1
    status = EbiosWorkshopStatus.NOT_STARTED


class SecurityBaselineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SecurityBaseline
        django_get_or_create = ("assessment",)

    assessment = factory.SubFactory(EbiosAssessmentFactory)
    status = EbiosBaselineStatus.DRAFT


class FearedEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FearedEvent

    baseline = factory.SubFactory(SecurityBaselineFactory)
    essential_asset = factory.SubFactory("assets.tests.factories.EssentialAssetFactory")
    name = factory.Sequence(lambda n: f"Feared event {n}")
    description = factory.Sequence(lambda n: f"Description {n}")
    dic_criterion = DICCriterion.CONFIDENTIALITY


class BaselineGapFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BaselineGap

    baseline = factory.SubFactory(SecurityBaselineFactory)
    reference_source = factory.Sequence(lambda n: f"ISO 27002 - A.{n}")
    description = factory.Sequence(lambda n: f"Gap {n}")
    severity = Severity.MEDIUM
    status = BaselineGapStatus.IDENTIFIED


class RiskSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskSource

    assessment = factory.SubFactory(EbiosAssessmentFactory)
    name = factory.Sequence(lambda n: f"Risk source {n}")
    category = RiskSourceCategory.ORGANIZED_CRIME
    motivation_level = 3
    resources_level = 3
    activity_level = 2


class TargetedObjectiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TargetedObjective

    risk_source = factory.SubFactory(RiskSourceFactory)
    name = factory.Sequence(lambda n: f"Objective {n}")
    category = TargetedObjectiveCategory.LUCRATIVE


class RiskSourceObjectivePairFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskSourceObjectivePair

    assessment = factory.SubFactory(EbiosAssessmentFactory)
    risk_source = factory.SubFactory(
        RiskSourceFactory,
        assessment=factory.SelfAttribute("..assessment"),
    )
    targeted_objective = factory.SubFactory(
        TargetedObjectiveFactory,
        risk_source=factory.SelfAttribute("..risk_source"),
    )
    relevance = Relevance.HIGH


class EcosystemStakeholderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EcosystemStakeholder

    assessment = factory.SubFactory(EbiosAssessmentFactory)
    name = factory.Sequence(lambda n: f"Stakeholder {n}")
    category = EcosystemStakeholderCategory.SUPPLIER
    dependency = 2
    penetration = 2
    maturity = 2
    trust = 2


class StrategicScenarioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StrategicScenario

    assessment = factory.SubFactory(EbiosAssessmentFactory)
    sr_ov_pair = factory.SubFactory(
        RiskSourceObjectivePairFactory,
        assessment=factory.SelfAttribute("..assessment"),
    )
    name = factory.Sequence(lambda n: f"Strategic scenario {n}")
    description = factory.Sequence(lambda n: f"Path {n}")
    gravity_level = 3
    likelihood_level = 2


class AttackPathStepFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AttackPathStep

    scenario = factory.SubFactory(StrategicScenarioFactory)
    order = factory.Sequence(lambda n: n)
    description = factory.Sequence(lambda n: f"Step {n}")
    action_type = AttackPathActionType.INITIAL_ACCESS
    difficulty = AttackDifficulty.MODERATE

import factory

from context.tests.factories import ScopeFactory
from risks.constants import (
    AcceptanceStatus,
    ActionStatus,
    ThreatType,
    TreatmentPlanStatus,
    TreatmentType,
)
from risks.models import (
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskTreatmentPlan,
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

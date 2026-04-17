import factory
from datetime import date, timedelta

from accounts.tests.factories import UserFactory
from reports.constants import (
    DecisionCategory,
    DecisionPriority,
    DecisionStatus,
    IsmsChangeStatus,
    IsmsChangeType,
    ManagementReviewFrequency,
    ManagementReviewStatus,
    ParticipantRole,
    ReportStatus,
    ReportType,
)
from reports.models import (
    IsmsChange,
    ManagementReview,
    ManagementReviewComment,
    ManagementReviewDecision,
    ManagementReviewParticipant,
    Report,
)


class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Report

    report_type = ReportType.SOA
    name = factory.Sequence(lambda n: f"Report {n}")
    status = ReportStatus.COMPLETED
    created_by = factory.SubFactory(UserFactory)


class ManagementReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ManagementReview

    title = factory.Sequence(lambda n: f"Management review {n}")
    frequency = ManagementReviewFrequency.ANNUAL
    period_start = date.today() - timedelta(days=365)
    period_end = date.today()
    planned_date = date.today()
    status = ManagementReviewStatus.PLANNED
    facilitator = factory.SubFactory(UserFactory)
    created_by = factory.SubFactory(UserFactory)


class ManagementReviewParticipantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ManagementReviewParticipant

    review = factory.SubFactory(ManagementReviewFactory)
    user = factory.SubFactory(UserFactory)
    role = ParticipantRole.CONTRIBUTOR


class ManagementReviewDecisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ManagementReviewDecision

    review = factory.SubFactory(ManagementReviewFactory)
    category = DecisionCategory.IMPROVEMENT
    title = factory.Sequence(lambda n: f"Decision {n}")
    description = "Test decision description"
    owner = factory.SubFactory(UserFactory)
    due_date = date.today() + timedelta(days=30)
    priority = DecisionPriority.MEDIUM
    status = DecisionStatus.PENDING


class IsmsChangeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IsmsChange

    review = factory.SubFactory(ManagementReviewFactory)
    change_type = IsmsChangeType.POLICY
    title = factory.Sequence(lambda n: f"ISMS change {n}")
    description = "Test change description"
    owner = factory.SubFactory(UserFactory)
    status = IsmsChangeStatus.PROPOSED


class ManagementReviewCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ManagementReviewComment

    review = factory.SubFactory(ManagementReviewFactory)
    author = factory.SubFactory(UserFactory)
    content = "Test comment"

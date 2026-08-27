# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""factory-boy factories for module 6.

Every factory produces a row in its lifecycle's `draft` step, which is what
`BaseModel._ensure_initial_step()` does on insert. A test that needs a record
further along must walk it there through `transition_to()` rather than passing
`workflow_state`: assigning the step directly would stick, but it would leave
no `core.LifecycleEvent` row, and the governance the module exists to provide
would be absent from the fixture the tests trust.
"""
import factory
from django.utils import timezone

from accounts.tests.factories import UserFactory
from incidents.constants import (
    AuthorityType,
    ClockAnchor,
    CustodyAction,
    DetectionSource,
    EvidenceType,
    NotificationRecipientKind,
    NotificationRegime,
    ResponseActionType,
    SecurityEventClass,
)
from incidents.models import (
    EvidenceCustodyEvent,
    Incident,
    IncidentEvidence,
    IncidentNotification,
    IncidentResponseAction,
    IncidentResponsePlan,
    IncidentTimelineEntry,
    NotificationFiling,
    PersonalDataBreach,
    PostIncidentReview,
    ReportingAuthority,
    ReportingObligationTemplate,
    SecurityEvent,
)


class IncidentResponsePlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IncidentResponsePlan
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Incident response plan {n}")
    purpose = "Handle information security incidents end to end."


class IncidentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Incident
        skip_postgeneration_save = True

    title = factory.Sequence(lambda n: f"Incident {n}")
    detected_at = factory.LazyFunction(timezone.now)
    detection_source = DetectionSource.INTERNAL_MONITORING


class SecurityEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SecurityEvent
        skip_postgeneration_save = True

    title = factory.Sequence(lambda n: f"Security event {n}")
    detected_at = factory.LazyFunction(timezone.now)
    reported_at = factory.LazyFunction(timezone.now)
    event_class = SecurityEventClass.EVENT
    detection_source = DetectionSource.EMPLOYEE_REPORT


class IncidentTimelineEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IncidentTimelineEntry
        skip_postgeneration_save = True

    incident = factory.SubFactory(IncidentFactory)
    occurred_at = factory.LazyFunction(timezone.now)
    summary = factory.Sequence(lambda n: f"Chronology line {n}")
    author = factory.SubFactory(UserFactory)


class IncidentResponseActionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IncidentResponseAction
        skip_postgeneration_save = True

    incident = factory.SubFactory(IncidentFactory)
    action_type = ResponseActionType.CONTAINMENT
    title = factory.Sequence(lambda n: f"Response action {n}")


class IncidentEvidenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IncidentEvidence
        skip_postgeneration_save = True

    incident = factory.SubFactory(IncidentFactory)
    title = factory.Sequence(lambda n: f"Evidence item {n}")
    evidence_type = EvidenceType.LOG_EXTRACT
    collected_at = factory.LazyFunction(timezone.now)


class EvidenceCustodyEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EvidenceCustodyEvent
        skip_postgeneration_save = True

    evidence = factory.SubFactory(IncidentEvidenceFactory)
    action = CustodyAction.ACCESSED
    occurred_at = factory.LazyFunction(timezone.now)
    actor = factory.SubFactory(UserFactory)


class PostIncidentReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PostIncidentReview
        skip_postgeneration_save = True

    incident = factory.SubFactory(IncidentFactory)


class ReportingAuthorityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportingAuthority
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Reporting authority {n}")
    authority_type = AuthorityType.SUPERVISORY_AUTHORITY
    primary_regime = NotificationRegime.GDPR_ART33_AUTHORITY


class ReportingObligationTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportingObligationTemplate
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Obligation template {n}")
    regime = NotificationRegime.GDPR_ART33_AUTHORITY
    recipient_kind = NotificationRecipientKind.SUPERVISORY_AUTHORITY
    clock_hours = 72


class IncidentNotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IncidentNotification
        skip_postgeneration_save = True

    incident = factory.SubFactory(IncidentFactory)
    regime = NotificationRegime.GDPR_ART33_AUTHORITY
    recipient_kind = NotificationRecipientKind.SUPERVISORY_AUTHORITY
    # The model refuses an obligation that is neither on a clock nor declared
    # deadline-free : "without undue delay" is a real regime, an unset delay
    # is a data error. 72 hours is the GDPR Art. 33(1) default.
    deadline_hours = 72
    clock_anchor = ClockAnchor.AWARENESS_AT


class NotificationFilingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationFiling
        skip_postgeneration_save = True

    notification = factory.SubFactory(IncidentNotificationFactory)
    submitted_at = factory.LazyFunction(timezone.now)


class PersonalDataBreachFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PersonalDataBreach
        skip_postgeneration_save = True

    incident = factory.SubFactory(IncidentFactory)

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""It is not an incident until a named person decides it is.

That single constraint is the whole point of the A.6.8 register. It turns the
promotion decision into an auditable, permissioned, comment-bearing lifecycle
transition instead of an implicit data entry, and it is the only way to answer
the question every ISO 27001 auditor asks : *show me the events you decided were
not incidents, and who decided*. A design that jumps straight to an incident
table with a status column cannot answer it at all, because the events that were
correctly dismissed leave no trace.
"""
import pytest

from accounts.tests.factories import UserFactory
from core.lifecycle import DomainRefusalError, TransitionNotAllowedError
from incidents.constants import EventTriageDecision, SecurityEventClass
from incidents.models import Incident, SecurityEvent
from incidents.tests.factories import SecurityEventFactory
from incidents.tests.helpers import (
    COMMENT,
    EVENT_ARCHIVED,
    EVENT_CONFIRMED_INCIDENT,
    EVENT_CONFIRMED_WEAKNESS,
    EVENT_DISCARDED,
    EVENT_DRAFT,
    EVENT_UNDER_ASSESSMENT,
    assessed_event,
    reported_event,
    walk,
)


@pytest.fixture
def assessor(db):
    return UserFactory()


# --- G-01 : an undocumented assessment is not an assessment -----------------


@pytest.mark.django_db
def test_leaving_the_assessment_requires_written_notes(assessor):
    """Rule : the reasoning behind the decision is the assessment.

    Enforced in ``transition_to`` rather than on the form, so the MCP tool and
    the API route are refused identically. The refusal also rolls back the
    vulnerability the promotion had already created, because the promotion is
    one atomic act.
    """
    from risks.models import Vulnerability

    event = reported_event(assessor)
    walk(event, EVENT_UNDER_ASSESSMENT, user=assessor)

    with pytest.raises(DomainRefusalError):
        event.promote_to_vulnerability(assessor, COMMENT, enforce_permission=False)

    assert Vulnerability.objects.count() == 0

    event.refresh_from_db()
    event.assessment_notes = (
        "Reproduced on the staging extranet; no exploitation observed."
    )
    event.save()
    vulnerability = event.promote_to_vulnerability(
        assessor, COMMENT, enforce_permission=False
    )

    assert event.workflow_state == EVENT_CONFIRMED_WEAKNESS
    assert Vulnerability.objects.filter(pk=vulnerability.pk).exists()


@pytest.mark.django_db
def test_the_mandatory_discard_comment_is_written_into_the_register_itself(assessor):
    """Rule : the assessment lives in the register, not only in the ledger.

    An auditor reading the event should not have to join the lifecycle history
    to find out why it was dismissed.
    """
    event = reported_event(assessor)
    walk(event, EVENT_UNDER_ASSESSMENT, user=assessor)
    reason = "Duplicate of the alert already assessed under EVNT-4."

    event.transition_to(EVENT_DISCARDED, assessor, comment=reason)

    assert reason in event.assessment_notes
    assert event.triage_decision == EventTriageDecision.NO_ACTION


# --- G-02 and G-03 : promotion is a real act with a real target -------------


@pytest.mark.django_db
def test_a_bare_promotion_transition_is_refused_without_the_incident(assessor):
    """Rule : the incident must exist before the event claims it does.

    The database half of the same rule is a ``CheckConstraint``, so neither a
    raw insert nor a ``QuerySet.update()`` can leave a promoted event pointing
    at nothing.
    """
    event = assessed_event(assessor)

    with pytest.raises(DomainRefusalError):
        event.transition_to(EVENT_CONFIRMED_INCIDENT, assessor, comment=COMMENT)


@pytest.mark.django_db
def test_promotion_creates_the_incident_and_declares_it_in_one_act(assessor):
    """Rule : the incident is created in draft and then transitioned.

    Assigning the step at insert would stick, but it would leave no
    ``core.LifecycleEvent`` : the incident would exist on the register with no
    recorded declaration, which is the evidence the register is for.
    """
    event = assessed_event(assessor)

    incident = event.promote_to_incident(
        assessor, "Confirmed lateral movement from the compromised host.",
        enforce_permission=False,
    )
    event.refresh_from_db()

    assert isinstance(incident, Incident)
    assert incident.workflow_state == "detected"
    assert incident.declared_at is not None
    assert event.workflow_state == EVENT_CONFIRMED_INCIDENT
    assert event.incident_id == incident.pk
    assert event.triage_decision == EventTriageDecision.INCIDENT


@pytest.mark.django_db
def test_the_original_report_is_never_rewritten_by_the_promotion(assessor):
    """Rule : the reporter's own words are part of the A.6.8 record."""
    event = assessed_event(
        assessor, description="The invoice attachment opened a black window."
    )

    event.promote_to_incident(assessor, COMMENT, enforce_permission=False)
    event.refresh_from_db()

    assert event.description == "The invoice attachment opened a black window."


@pytest.mark.django_db
def test_a_weakness_is_never_promoted_to_an_incident(assessor):
    """Rule : report the exploitation as a new event, linked by ``duplicate_of``.

    Rewriting the weakness would destroy its own reporting history and would
    measure the exploitation's reporting delay from the wrong detection.
    """
    weakness = assessed_event(assessor, event_class=SecurityEventClass.WEAKNESS)

    with pytest.raises(DomainRefusalError):
        weakness.promote_to_incident(assessor, COMMENT, enforce_permission=False)

    exploitation = assessed_event(
        assessor, event_class=SecurityEventClass.EVENT, duplicate_of=weakness
    )
    incident = exploitation.promote_to_incident(
        assessor, COMMENT, enforce_permission=False
    )

    assert incident is not None
    weakness.refresh_from_db()
    assert weakness.workflow_state == EVENT_UNDER_ASSESSMENT


# --- G-04 : a confirmed weakness lands in the vulnerability register --------


@pytest.mark.django_db
def test_recording_a_weakness_requires_the_vulnerability_it_becomes(assessor):
    """Rule : there is no parallel weakness table.

    Two weakness registers would be two answers to *what do we know is broken*.
    """
    event = assessed_event(assessor)

    with pytest.raises(DomainRefusalError):
        event.transition_to(EVENT_CONFIRMED_WEAKNESS, assessor, comment=COMMENT)

    vulnerability = event.promote_to_vulnerability(
        assessor, "Unauthenticated file upload on the extranet.",
        enforce_permission=False,
    )
    event.refresh_from_db()

    assert event.workflow_state == EVENT_CONFIRMED_WEAKNESS
    assert event.vulnerability_id == vulnerability.pk
    assert event.triage_decision == EventTriageDecision.WEAKNESS


# --- G-06 : one event never carries two verdicts ----------------------------


@pytest.mark.django_db
def test_an_event_that_already_carries_a_verdict_is_not_given_a_second(assessor):
    """Rule : the verdict column mirrors the step, and the pair must agree."""
    event = assessed_event(assessor)
    event.triage_decision = EventTriageDecision.WEAKNESS

    with pytest.raises(DomainRefusalError):
        event.transition_to(EVENT_CONFIRMED_INCIDENT, assessor, comment=COMMENT)


@pytest.mark.django_db
def test_reopening_a_discarded_event_clears_the_verdict_but_keeps_the_clock(assessor):
    """Rule : the original discard stays in the lifecycle history.

    ``assessed_at`` is write-once : reopening does not rewrite when the
    assessment began, and the reopening actor is recorded on the ledger.
    """
    event = assessed_event(assessor)
    started_at = event.assessed_at
    event.transition_to(EVENT_DISCARDED, assessor, comment="False positive.")

    event.transition_to(
        EVENT_UNDER_ASSESSMENT, assessor, comment="Reopened after a second report."
    )

    assert event.triage_decision == ""
    assert event.assessed_at == started_at
    assert event.assessed_by_id == assessor.pk


# --- The restore bookend ----------------------------------------------------


@pytest.mark.django_db
def test_an_event_that_entered_the_register_cannot_be_restored_to_draft(assessor):
    """Rule : archiving must not become a way of deleting an A.6.8 record.

    ``draft`` and ``reported`` are both deletable steps, so the restore edge is
    the one that has to be gated.
    """
    event = reported_event(assessor)
    event.transition_to(EVENT_ARCHIVED, assessor, comment=COMMENT)

    with pytest.raises(DomainRefusalError):
        event.transition_to(EVENT_DRAFT, assessor)


@pytest.mark.django_db
def test_an_event_that_never_reached_the_register_can_be_restored(assessor):
    """The counterpart : a draft nobody ever reported is still a draft."""
    event = SecurityEventFactory()

    walk(event, EVENT_ARCHIVED, EVENT_DRAFT, user=assessor)

    assert event.workflow_state == EVENT_DRAFT


# --- The permission half of the promotion decision --------------------------


@pytest.mark.django_db
def test_promotion_is_refused_to_a_user_who_does_not_hold_the_permission(assessor):
    """Rule : promotion carries ``permission_action="validate"``.

    Enforced by ``validate_transition`` on every surface that asks for it, so
    the same refusal reaches the web stepper, the API and MCP.
    """
    event = assessed_event(assessor)

    with pytest.raises(TransitionNotAllowedError):
        event.promote_to_incident(assessor, COMMENT, enforce_permission=True)

    event.refresh_from_db()
    assert event.workflow_state == EVENT_UNDER_ASSESSMENT
    assert Incident.objects.count() == 0


@pytest.mark.django_db
def test_promotion_goes_through_for_a_user_who_does_hold_it(db):
    """The other half : the gate is a permission check, not a blanket refusal."""
    approver = UserFactory(is_superuser=True)
    event = assessed_event(approver)

    incident = event.promote_to_incident(
        approver, "Confirmed as an incident.", enforce_permission=True
    )

    assert incident.workflow_state == "detected"
    event.refresh_from_db()
    assert event.workflow_state == EVENT_CONFIRMED_INCIDENT


@pytest.mark.django_db
def test_a_refused_promotion_leaves_no_half_created_incident(assessor):
    """Rule : promotion is one atomic act, not a sequence a user can abandon."""
    weakness = assessed_event(assessor, event_class=SecurityEventClass.WEAKNESS)

    with pytest.raises(DomainRefusalError):
        weakness.promote_to_incident(assessor, COMMENT, enforce_permission=False)

    assert Incident.objects.count() == 0
    weakness.refresh_from_db()
    assert weakness.incident_id is None


# --- The A.6.8 reporting delay ----------------------------------------------


@pytest.mark.django_db
def test_the_reporting_delay_is_derived_from_the_two_stamps(assessor):
    """The measurable quantity A.6.8's *as quickly as possible* is assessed against."""
    from datetime import timedelta

    from django.utils import timezone

    detected_at = timezone.now() - timedelta(hours=5)
    event = SecurityEventFactory(
        detected_at=detected_at, reported_at=detected_at + timedelta(hours=3)
    )

    assert event.reporting_delay == timedelta(hours=3)
    assert event.reporting_delay_hours == 3.0


@pytest.mark.django_db
def test_the_anonymous_channel_carries_no_reporter_identity(assessor):
    """Rule : the database, not a form, guarantees the channel is actually anonymous."""
    from django.core.exceptions import ValidationError

    event = SecurityEventFactory.build(is_anonymous=True, reporter_label="A. Dupont")

    with pytest.raises(ValidationError) as refusal:
        event.clean()
    assert "is_anonymous" in refusal.value.message_dict


@pytest.mark.django_db
def test_the_register_keeps_the_events_that_were_correctly_dismissed(assessor):
    """The question the entity exists to answer, asked the way an auditor asks it."""
    dismissed = assessed_event(assessor)
    dismissed.transition_to(
        EVENT_DISCARDED, assessor, comment="Benign scanner traffic."
    )
    promoted = assessed_event(assessor)
    promoted.promote_to_incident(assessor, COMMENT, enforce_permission=False)

    decisions = dict(
        SecurityEvent.objects.values_list("pk", "triage_decision")
    )

    assert decisions[dismissed.pk] == EventTriageDecision.NO_ACTION
    assert decisions[promoted.pk] == EventTriageDecision.INCIDENT
    assert SecurityEvent.objects.filter(workflow_state=EVENT_DISCARDED).count() == 1

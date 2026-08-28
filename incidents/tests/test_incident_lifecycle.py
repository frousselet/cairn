# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""What the A.5.26 incident file refuses, and what it stamps.

Every gate is tested twice : once proving it refuses, once proving it allows
when the condition is satisfied. A refusal test alone passes just as well
against a model that refuses everything, which is the failure mode a gate suite
is most likely to hide.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.tests.factories import UserFactory
from core.lifecycle import DomainRefusalError
from incidents.constants import NotificationChannel, TimelineEntrySource
from incidents.models import IncidentTimelineEntry
from incidents.tests.factories import IncidentFactory
from incidents.tests.helpers import (
    COMMENT,
    INCIDENT_ARCHIVED,
    INCIDENT_CONTAINED,
    INCIDENT_DETECTED,
    INCIDENT_DRAFT,
    INCIDENT_ERADICATED,
    INCIDENT_INVESTIGATING,
    INCIDENT_RECLASSIFIED,
    INCIDENT_RECOVERED,
    INCIDENT_TRIAGED,
    declared_incident,
    drafted_obligation,
    triaged_incident,
    walk,
)


@pytest.fixture
def responder(db):
    return UserFactory()


# --- G-01 : an incident is declared against a detection ----------------------


@pytest.mark.django_db
def test_declaring_an_incident_without_a_detection_timestamp_is_refused(responder):
    """Rule : an incident is declared against a detection, never in the abstract."""
    incident = IncidentFactory()
    incident.detected_at = None

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_DETECTED, responder)


@pytest.mark.django_db
def test_declaring_an_incident_with_a_detection_timestamp_is_allowed(responder):
    """The same move, with the timestamp the gate asks for, must go through."""
    incident = declared_incident(responder)

    assert incident.workflow_state == INCIDENT_DETECTED


@pytest.mark.django_db
def test_legal_awareness_cannot_precede_the_technical_detection(responder):
    """Rule : becoming legally aware before detecting is incoherent.

    The gate exists because ``awareness_at`` is editable and anchors every
    statutory deadline : an anchor before the detection that produced the record
    would push every deadline earlier than the facts allow.
    """
    incident = IncidentFactory()
    incident.awareness_at = incident.detected_at - timedelta(hours=6)

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_DETECTED, responder)

    incident.awareness_at = incident.detected_at + timedelta(hours=6)
    incident.awareness_justification = "The alert went unread over the weekend."
    incident.transition_to(INCIDENT_DETECTED, responder)

    assert incident.workflow_state == INCIDENT_DETECTED


# --- G-02 : triage completes the A.5.25 assessment ---------------------------


@pytest.mark.django_db
def test_triage_requires_a_named_incident_manager(responder):
    """Rule : the A.5.24 accountable responder is fixed at triage, not later."""
    incident = declared_incident(responder, incident_manager=None)
    incident.no_obligation_justification = "No regulatory regime applies."
    incident.save()

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_TRIAGED, responder)

    incident.incident_manager = responder
    incident.save()
    incident.transition_to(INCIDENT_TRIAGED, responder)

    assert incident.workflow_state == INCIDENT_TRIAGED


@pytest.mark.django_db
def test_triage_requires_a_severity_and_a_category(responder):
    """Rule : an incident with no classification has not been assessed."""
    incident = declared_incident(responder, incident_manager=responder)
    incident.no_obligation_justification = "No regulatory regime applies."
    incident.severity = ""

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_TRIAGED, responder)


@pytest.mark.django_db
def test_a_gap_between_detection_and_awareness_must_be_justified_before_triage(
    responder,
):
    """Rule : a legal awareness postdating the detection is justified in writing.

    Defensible - an alert unread over a weekend is a real thing - but only when
    the reason is written down at the time rather than reconstructed for an
    inspector two years later.
    """
    incident = declared_incident(responder, incident_manager=responder)
    incident.awareness_at = incident.detected_at + timedelta(hours=30)
    incident.no_obligation_justification = "No regulatory regime applies."
    incident.save()

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_TRIAGED, responder)

    incident.awareness_justification = (
        "The SOC alert was raised on Saturday and read on Monday morning."
    )
    incident.save()
    incident.transition_to(INCIDENT_TRIAGED, responder)

    assert incident.workflow_state == INCIDENT_TRIAGED


# --- G-04 : you cannot un-declare what a regulator has been told -------------


@pytest.mark.django_db
def test_an_incident_with_no_filing_can_still_be_reclassified(responder):
    """The honest off-ramp : it was declared, and it turned out not to be one."""
    incident = triaged_incident(responder)
    drafted_obligation(incident, responder)

    incident.transition_to(INCIDENT_RECLASSIFIED, responder, comment=COMMENT)

    assert incident.workflow_state == INCIDENT_RECLASSIFIED


@pytest.mark.django_db
def test_an_incident_already_notified_to_a_regulator_cannot_be_reclassified(responder):
    """Rule : a filed obligation makes the declaration a fact of record.

    Reclassifying afterwards would leave a regulator holding a notification for
    an incident the register says never happened.
    """
    incident = triaged_incident(responder)
    obligation = drafted_obligation(incident, responder)
    obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Initial notification under GDPR Art. 33(1).",
    )

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_RECLASSIFIED, responder, comment=COMMENT)


# --- G-07 : archiving is not a way of deleting a declared incident -----------


@pytest.mark.django_db
def test_an_incident_that_never_left_draft_can_be_restored(responder):
    """Draft is the one deletable step, and a never-declared row may return to it."""
    incident = IncidentFactory()
    walk(incident, INCIDENT_ARCHIVED, INCIDENT_DRAFT, user=responder)

    assert incident.workflow_state == INCIDENT_DRAFT


@pytest.mark.django_db
def test_a_declared_incident_cannot_be_restored_to_draft(responder):
    """Rule : archive then restore must not become a delete route.

    Draft is deletable. Without this gate, anyone able to archive could walk a
    declared incident back into the one step from which it can be destroyed.
    """
    incident = declared_incident(responder)
    incident.transition_to(INCIDENT_ARCHIVED, responder, comment=COMMENT)

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_DRAFT, responder)


# --- The phase stamps the lifecycle owns -------------------------------------


@pytest.mark.django_db
def test_each_phase_transition_stamps_its_own_clock(responder):
    """Rule : the process clocks are written by the lifecycle, never by a form."""
    incident = triaged_incident(responder)

    assert incident.declared_at is not None
    assert incident.triaged_at is not None
    assert incident.contained_at is None

    walk(incident, INCIDENT_INVESTIGATING, INCIDENT_CONTAINED, user=responder)

    assert incident.contained_at is not None


@pytest.mark.django_db
def test_a_stamp_already_set_is_never_rewritten_by_a_second_pass(responder):
    """Rule : the phase stamps are write-once (RG-INC-12).

    An incident that reopens and is contained a second time keeps the date it
    was first contained : that is the fact the containment KPI is measured on.
    """
    incident = triaged_incident(responder)
    walk(
        incident,
        INCIDENT_INVESTIGATING,
        INCIDENT_CONTAINED,
        INCIDENT_ERADICATED,
        INCIDENT_RECOVERED,
        user=responder,
    )
    first_contained_at = incident.contained_at

    incident.transition_to(INCIDENT_INVESTIGATING, responder, comment=COMMENT)
    walk(incident, INCIDENT_CONTAINED, user=responder)

    assert incident.contained_at == first_contained_at


@pytest.mark.django_db
def test_reopening_an_investigation_clears_only_the_recovery_stamp(responder):
    """Rule : a stamp is cleared by its own reopen edge and by nothing else.

    An incident that reopens is no longer recovered, so that stamp goes; the
    containment and eradication it genuinely went through stay on the record.
    """
    incident = triaged_incident(responder)
    walk(
        incident,
        INCIDENT_INVESTIGATING,
        INCIDENT_CONTAINED,
        INCIDENT_ERADICATED,
        INCIDENT_RECOVERED,
        user=responder,
    )

    incident.transition_to(INCIDENT_INVESTIGATING, responder, comment=COMMENT)

    assert incident.recovered_at is None
    assert incident.contained_at is not None
    assert incident.eradicated_at is not None


@pytest.mark.django_db
def test_triage_freezes_the_initial_severity_so_later_drift_is_visible(responder):
    """Rule : severity as fixed at triage is a column, not a history diff."""
    incident = triaged_incident(responder, severity="medium")

    assert incident.initial_severity == "medium"
    assert incident.severity_raised_since_triage is False

    incident.severity = "critical"
    incident.save()

    assert incident.initial_severity == "medium"
    assert incident.severity_raised_since_triage is True


# --- RG-INC-09 : the narrative and the state machine cannot diverge ----------


@pytest.mark.django_db
def test_every_attributed_transition_appends_exactly_one_chronology_line(responder):
    """Rule : a transition owes the chronology one line, written in its own transaction."""
    incident = declared_incident(
        responder,
        incident_manager=responder,
        no_obligation_justification="No regulatory regime applies.",
    )
    before = IncidentTimelineEntry.objects.filter(incident=incident).count()

    incident.transition_to(INCIDENT_TRIAGED, responder)

    entries = IncidentTimelineEntry.objects.filter(incident=incident)
    assert entries.count() == before + 1
    latest = entries.order_by("-recorded_at").first()
    assert latest.source == TimelineEntrySource.LIFECYCLE
    assert latest.author == responder


@pytest.mark.django_db
def test_an_unattributed_transition_appends_no_chronology_line(responder):
    """Rule : an unattributed line in the account a regulator reads is worse than none.

    The move itself is still recorded, with its null actor, in the immutable
    ``core.LifecycleEvent`` ledger.
    """
    incident = IncidentFactory()
    incident.transition_to(INCIDENT_DETECTED, None)

    assert IncidentTimelineEntry.objects.filter(incident=incident).count() == 0


@pytest.mark.django_db
def test_a_refused_transition_leaves_no_trace_at_all(responder):
    """Rule : the gates run inside the transition's own transaction.

    A triage refused on its last gate must roll back the stamps and the child
    rows the earlier part of the same transition produced.
    """
    incident = declared_incident(responder, incident_manager=responder)
    incident.awareness_at = incident.detected_at + timedelta(hours=12)
    incident.save()

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_TRIAGED, responder)

    incident.refresh_from_db()
    assert incident.workflow_state == INCIDENT_DETECTED
    assert incident.triaged_at is None
    assert incident.notifications.count() == 0


@pytest.mark.django_db
def test_the_awareness_gap_is_derived_once_for_every_surface(responder):
    """The quantity the justification has to account for, computed in one place."""
    incident = IncidentFactory()
    incident.awareness_at = incident.detected_at + timedelta(hours=9)

    assert incident.awareness_gap == timedelta(hours=9)


@pytest.mark.django_db
def test_the_containment_and_recovery_kpis_count_from_detection(responder):
    """Rule : the process KPIs are measured from technical detection.

    The legal clock is a different quantity anchored on a different field, and
    ``test_the_two_clocks`` is where that distinction is proved.
    """
    incident = triaged_incident(responder)
    walk(incident, INCIDENT_INVESTIGATING, INCIDENT_CONTAINED, user=responder)

    assert incident.time_to_contain == incident.contained_at - incident.detected_at
    assert incident.time_to_recover is None
    assert incident.contained_at <= timezone.now()

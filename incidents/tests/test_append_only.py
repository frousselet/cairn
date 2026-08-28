# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Three ledgers that are written to and never written over.

The chronology is the narrative a supervisory authority or a court reads. The
custody ledger is what turns a register of files into evidence. The filing log
is the proof handed to an inspector who asks *show me that you filed the 72-hour
notification*. None of the three is worth anything if a row can be quietly
improved after the fact, so all three refuse a post-insert write and refuse a
delete, and a mistake is corrected by **appending a row that points at the one
it supersedes**.

What that claim does and does not cover is stated in each model's docstring and
is not restated as a test : ``QuerySet.update()``, ``bulk_update()``, raw SQL and
a shell session never call ``save()``. ``HistoricalRecords`` is what turns that
prevention gap into detection. The honest claim is *prevented on every supported
path and detectable on the rest*.
"""
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.tests.factories import UserFactory
from core.lifecycle import LifecycleProtectedError
from incidents.constants import (
    CustodyAction,
    NotificationChannel,
    TimelineEntryKind,
    TimelineEntrySource,
)
from incidents.models import (
    EvidenceCustodyEvent,
    IncidentTimelineEntry,
    NotificationFiling,
)
from incidents.tests.factories import (
    IncidentFactory,
    IncidentTimelineEntryFactory,
)
from incidents.tests.helpers import drafted_obligation, sealed_evidence


@pytest.fixture
def responder(db):
    return UserFactory()


@pytest.fixture
def incident(db):
    return IncidentFactory()


# --- The chronology ---------------------------------------------------------


@pytest.mark.django_db
def test_a_chronology_entry_refuses_every_post_insert_write(incident, responder):
    """Rule : an account of an incident that can be rewritten is not evidence."""
    entry = IncidentTimelineEntryFactory(incident=incident, author=responder)

    entry.summary = "A tidier version of what happened."
    with pytest.raises(LifecycleProtectedError):
        entry.save()

    entry.refresh_from_db()
    assert entry.summary != "A tidier version of what happened."
    assert entry.version == 1, "a value other than 1 would itself be a signal"


@pytest.mark.django_db
def test_a_chronology_entry_is_never_deleted(incident, responder):
    """Rule : there is no delete route for a narrative line, on any surface."""
    entry = IncidentTimelineEntryFactory(incident=incident, author=responder)

    with pytest.raises(LifecycleProtectedError):
        entry.delete()

    assert IncidentTimelineEntry.objects.filter(pk=entry.pk).exists()


@pytest.mark.django_db
def test_a_correction_is_an_appended_entry_naming_the_one_it_supersedes(
    incident, responder
):
    """Rule : a factual error is fixed by appending, never by editing.

    The superseded entry is neither modified nor hidden : both rows stay in the
    chronology, and the correction states why the earlier one was wrong.
    """
    original = IncidentTimelineEntryFactory(
        incident=incident,
        author=responder,
        summary="EDR isolated WEB-PRD-02 at 10:42.",
    )

    correction = IncidentTimelineEntry.objects.create(
        incident=incident,
        occurred_at=original.occurred_at + timedelta(minutes=5),
        entry_type=TimelineEntryKind.CORRECTION,
        summary="EDR isolated WEB-PRD-03, not WEB-PRD-02.",
        author=responder,
        superseded_entry=original,
        correction_reason="The hostname in the earlier entry was transcribed wrongly.",
    )
    original.refresh_from_db()

    assert original.summary == "EDR isolated WEB-PRD-02 at 10:42."
    assert original.is_superseded is True
    assert correction.superseded_entry_id == original.pk
    assert IncidentTimelineEntry.objects.filter(incident=incident).count() == 2


@pytest.mark.django_db
def test_a_correction_with_no_stated_reason_is_a_rewrite(incident, responder):
    """Rule : a correction with no stated reason is a rewrite, and is refused."""
    original = IncidentTimelineEntryFactory(incident=incident, author=responder)
    correction = IncidentTimelineEntry(
        incident=incident,
        occurred_at=timezone.now(),
        entry_type=TimelineEntryKind.CORRECTION,
        summary="Restated.",
        author=responder,
        superseded_entry=original,
    )

    with pytest.raises(ValidationError) as refusal:
        correction.clean()
    assert "correction_reason" in refusal.value.message_dict


@pytest.mark.django_db
def test_an_entry_superseding_another_one_must_declare_itself_a_correction(
    incident, responder
):
    """The kind and the link are two halves of one statement, and must agree."""
    original = IncidentTimelineEntryFactory(incident=incident, author=responder)
    entry = IncidentTimelineEntry(
        incident=incident,
        occurred_at=timezone.now(),
        entry_type=TimelineEntryKind.OBSERVATION,
        summary="Restated.",
        author=responder,
        superseded_entry=original,
        correction_reason="The hostname was wrong.",
    )

    with pytest.raises(ValidationError) as refusal:
        entry.clean()
    assert "entry_type" in refusal.value.message_dict


@pytest.mark.django_db
def test_a_correction_must_name_the_entry_it_corrects(incident, responder):
    """A correction of nothing in particular corrects nothing."""
    entry = IncidentTimelineEntry(
        incident=incident,
        occurred_at=timezone.now(),
        entry_type=TimelineEntryKind.CORRECTION,
        summary="Restated.",
        author=responder,
        correction_reason="The hostname was wrong.",
    )

    with pytest.raises(ValidationError) as refusal:
        entry.clean()
    assert "superseded_entry" in refusal.value.message_dict


# --- The custody ledger -----------------------------------------------------


@pytest.mark.django_db
def test_a_custody_row_refuses_every_post_insert_write(incident, responder):
    """Rule : a chain of custody that can be rewritten is not a chain of custody."""
    evidence = sealed_evidence(incident, responder)
    row = EvidenceCustodyEvent.objects.filter(evidence=evidence).first()

    row.notes = "Seal number 44821, which I forgot to write down."
    with pytest.raises(LifecycleProtectedError):
        row.save()

    row.refresh_from_db()
    assert "44821" not in row.notes


@pytest.mark.django_db
def test_a_custody_row_is_never_deleted(incident, responder):
    """Rule : there is no delete route on any surface."""
    evidence = sealed_evidence(incident, responder)
    row = EvidenceCustodyEvent.objects.filter(evidence=evidence).first()

    with pytest.raises(LifecycleProtectedError):
        row.delete()

    assert EvidenceCustodyEvent.objects.filter(pk=row.pk).exists()


@pytest.mark.django_db
def test_a_custody_mistake_is_corrected_by_appending_a_further_act(
    incident, responder
):
    """Rule : the earlier row is never touched; a later row states what it got wrong.

    There is deliberately no supersession link here : the ledger reads in
    occurrence order, and the later row's notes are what an auditor reads.
    """
    evidence = sealed_evidence(incident, responder)
    original = EvidenceCustodyEvent.objects.filter(evidence=evidence).first()

    EvidenceCustodyEvent.objects.create(
        evidence=evidence,
        action=CustodyAction.ACCESSED,
        occurred_at=timezone.now(),
        actor=responder,
        notes="The seal number on the collection row was 44821, not 44812.",
        source=TimelineEntrySource.MANUAL,
    )
    original.refresh_from_db()

    assert original.version == 1
    assert EvidenceCustodyEvent.objects.filter(evidence=evidence).count() == 3


@pytest.mark.django_db
def test_a_custody_act_cannot_be_dated_before_the_last_recorded_one(
    incident, responder
):
    """Rule : a chain of custody cannot jump backwards.

    Equality is allowed on purpose : two acts genuinely occur in the same
    minute, and forcing a strict ordering would push operators into falsifying a
    timestamp to get a row saved.
    """
    evidence = sealed_evidence(incident, responder)
    latest = (
        EvidenceCustodyEvent.objects.filter(evidence=evidence)
        .order_by("-occurred_at")
        .first()
    )

    backdated = EvidenceCustodyEvent(
        evidence=evidence,
        action=CustodyAction.ACCESSED,
        occurred_at=latest.occurred_at - timedelta(hours=1),
        actor=responder,
    )
    with pytest.raises(ValidationError) as refusal:
        backdated.clean()
    assert "occurred_at" in refusal.value.message_dict

    simultaneous = EvidenceCustodyEvent(
        evidence=evidence,
        action=CustodyAction.ACCESSED,
        occurred_at=latest.occurred_at,
        actor=responder,
    )
    simultaneous.clean()


@pytest.mark.django_db
def test_a_handover_with_no_named_individual_is_not_a_handover(incident, responder):
    """Rule : the acts that move custody name the person on the other side."""
    evidence = sealed_evidence(incident, responder)

    row = EvidenceCustodyEvent(
        evidence=evidence,
        action=CustodyAction.TRANSFERRED,
        occurred_at=timezone.now(),
        actor=responder,
        counterparty_organisation="Forensics SARL",
    )
    with pytest.raises(ValidationError) as refusal:
        row.clean()
    assert "counterparty" in refusal.value.message_dict

    row.counterparty = "M. Da Silva"
    row.clean()


@pytest.mark.django_db
def test_a_verification_row_claiming_a_verdict_without_a_measurement_is_refused(
    incident, responder
):
    """Rule : the measured digest is what makes the ledger falsifiable.

    A row asserting *integrity verified, matched* with no digest asserts nothing
    anybody can check.
    """
    evidence = sealed_evidence(incident, responder)

    row = EvidenceCustodyEvent(
        evidence=evidence,
        action=CustodyAction.INTEGRITY_VERIFIED,
        occurred_at=timezone.now(),
        actor=responder,
        integrity_ok=True,
    )
    with pytest.raises(ValidationError) as refusal:
        row.clean()
    assert "hash_at_event" in refusal.value.message_dict


@pytest.mark.django_db
def test_an_unattributed_custody_act_is_refused(incident, responder):
    """Rule : an act attributed to nobody is not a chain of custody."""
    from core.lifecycle import DomainRefusalError

    evidence = sealed_evidence(incident, responder)

    with pytest.raises(DomainRefusalError):
        EvidenceCustodyEvent.record_lifecycle_act(
            evidence, action=CustodyAction.ACCESSED, actor=None
        )


# --- The filing log ---------------------------------------------------------


@pytest.mark.django_db
def test_a_filing_refuses_a_write_to_anything_but_the_three_completion_fields(
    incident, responder
):
    """Rule : what was transmitted is never rewritten.

    The exception is deliberately narrow : the recipient's answer arrives after
    the transmission, and what we said does not change because of it.
    """
    obligation = drafted_obligation(incident, responder)
    filing = obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Notification under GDPR Art. 33(1).",
    )

    filing.content = "A tidier account of what we meant to say."
    with pytest.raises(LifecycleProtectedError) as refusal:
        filing.save()
    assert "content" in str(refusal.value)

    filing.refresh_from_db()
    assert filing.content == "Notification under GDPR Art. 33(1)."


@pytest.mark.django_db
def test_a_filing_is_never_deleted(incident, responder):
    """Rule : the log is append-only, so there is no delete route at all."""
    obligation = drafted_obligation(incident, responder)
    filing = obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Notification under GDPR Art. 33(1).",
    )

    with pytest.raises(LifecycleProtectedError):
        filing.delete()

    assert NotificationFiling.objects.filter(pk=filing.pk).exists()


@pytest.mark.django_db
def test_a_supersession_chain_stays_inside_one_obligation(incident, responder):
    """A filing can only replace another filing on the same duty."""
    first_obligation = drafted_obligation(incident, responder)
    first = first_obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Notification under GDPR Art. 33(1).",
    )
    other_obligation = drafted_obligation(
        IncidentFactory(), responder, deadline_hours=24
    )
    other_obligation.record_filing(
        responder, channel=NotificationChannel.EMAIL, content="Another duty entirely."
    )

    stray = NotificationFiling(
        notification=other_obligation,
        submitted_at=timezone.now(),
        channel=NotificationChannel.EMAIL,
        is_correction=True,
        supersedes=first,
    )
    with pytest.raises(ValidationError) as refusal:
        stray.clean()
    assert "supersedes" in refusal.value.message_dict


@pytest.mark.django_db
def test_a_filing_cannot_be_recorded_in_the_future(incident, responder):
    """A transmission that has not happened yet is not a transmission."""
    obligation = drafted_obligation(incident, responder)

    filing = NotificationFiling(
        notification=obligation,
        submitted_at=timezone.now() + timedelta(hours=1),
        channel=NotificationChannel.PORTAL,
    )
    with pytest.raises(ValidationError) as refusal:
        filing.clean()
    assert "submitted_at" in refusal.value.message_dict

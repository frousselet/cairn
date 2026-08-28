# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The A.5.28 register, and the ledger that makes it evidence rather than files.

A register of artefacts answers *what did we acquire*. Only the chain of custody
answers *who held it, when, where, and did the hash still match*, which is the
half an auditor actually asks about.

Two rules are proved here and neither is decorative. **A handling act appends
exactly one row** : the ledger must not be padded with rows for moves that
handled nothing, because a ledger nobody trusts to be exact is a ledger nobody
reads. And **a verification that could not read the artefact is not a failure** :
a restored database paired with a lost media volume would otherwise write a
permanent chain-of-custody break into every evidence item in the platform on a
day when nothing was tampered with.
"""
import hashlib
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone

from accounts.tests.factories import UserFactory
from core.lifecycle import DomainRefusalError
from incidents.constants import CustodyAction, TimelineEntrySource
from incidents.models import EvidenceCustodyEvent, IncidentEvidence
from incidents.models.evidence import (
    VERIFICATION_MATCH,
    VERIFICATION_MISMATCH,
    VERIFICATION_NOT_VERIFIABLE,
)
from incidents.tests.factories import IncidentEvidenceFactory, IncidentFactory
from incidents.tests.helpers import (
    COMMENT,
    EVIDENCE_ANALYSED,
    EVIDENCE_ARCHIVED,
    EVIDENCE_COLLECTED,
    EVIDENCE_DESTROYED,
    EVIDENCE_DRAFT,
    EVIDENCE_RELEASED,
    EVIDENCE_RETAINED,
    EVIDENCE_SECURED,
    collected_evidence,
    retained_evidence,
    sealed_evidence,
    walk,
)

PAYLOAD = b"Feb 14 03:11:02 web-prd-02 sshd[2211]: Accepted publickey for root\n"
PAYLOAD_DIGEST = hashlib.sha256(PAYLOAD).hexdigest()


@pytest.fixture
def responder(db):
    return UserFactory()


@pytest.fixture
def incident(db):
    return IncidentFactory()


def ledger(evidence):
    return EvidenceCustodyEvent.objects.filter(evidence=evidence)


def actions(evidence):
    return list(ledger(evidence).values_list("action", flat=True))


# --- GE-01 : an acquisition is attributed, timed and sourced ----------------


@pytest.mark.django_db
def test_registering_an_acquisition_requires_a_named_acquirer(incident, responder):
    """Rule : an artefact attributed to nobody is not an acquisition."""
    evidence = IncidentEvidenceFactory(
        incident=incident, collected_by=None, source_description="WEB-PRD-02"
    )

    with pytest.raises(DomainRefusalError):
        evidence.transition_to(EVIDENCE_COLLECTED, responder)

    evidence.collected_by = responder
    evidence.save()
    evidence.transition_to(EVIDENCE_COLLECTED, responder)

    assert evidence.workflow_state == EVIDENCE_COLLECTED


@pytest.mark.django_db
def test_registering_an_acquisition_requires_a_collection_timestamp(
    incident, responder
):
    """Rule : the moment the artefact left the live system is part of the record."""
    evidence = IncidentEvidenceFactory(
        incident=incident,
        collected_by=responder,
        source_description="WEB-PRD-02",
        collected_at=None,
    )

    with pytest.raises(DomainRefusalError):
        evidence.transition_to(EVIDENCE_COLLECTED, responder)


@pytest.mark.django_db
def test_registering_an_acquisition_requires_a_stated_origin(incident, responder):
    """Rule : an artefact from nowhere in particular proves nothing about anywhere."""
    evidence = IncidentEvidenceFactory(
        incident=incident, collected_by=responder, source_description=""
    )

    with pytest.raises(DomainRefusalError):
        evidence.transition_to(EVIDENCE_COLLECTED, responder)

    evidence.source_description = "WEB-PRD-02, production web front end"
    evidence.save()
    evidence.transition_to(EVIDENCE_COLLECTED, responder)

    assert evidence.workflow_state == EVIDENCE_COLLECTED


# --- GE-02 : sealing needs a fingerprint and a method -----------------------


@pytest.mark.django_db
def test_sealing_requires_both_a_hash_and_a_stated_collection_method(
    incident, responder
):
    """Rule : an artefact with a perfect hash and no stated method is a file.

    Admissibility rests on how it was acquired : the tooling, the write blocker,
    the exact command line, whether the source was live or powered down.
    """
    evidence = collected_evidence(
        incident, responder, content_hash="a" * 64, collection_method=""
    )

    with pytest.raises(DomainRefusalError):
        evidence.transition_to(EVIDENCE_SECURED, responder)

    evidence.collection_method = "dd 8.32 through a Tableau T35u write blocker."
    evidence.save()
    evidence.transition_to(EVIDENCE_SECURED, responder)

    assert evidence.workflow_state == EVIDENCE_SECURED
    assert evidence.sealed_at is not None


@pytest.mark.django_db
def test_sealing_freezes_the_acquisition_metadata(incident, responder):
    """Rule : after the seal, what was acquired and how is no longer editable."""
    evidence = sealed_evidence(incident, responder)

    evidence.collection_method = "Actually we used a different tool."
    with pytest.raises(ValidationError) as refusal:
        evidence.save()
    assert "collection_method" in refusal.value.message_dict

    stored = IncidentEvidence.objects.get(pk=evidence.pk)
    stored.content_hash = "b" * 64
    with pytest.raises(ValidationError) as refusal:
        stored.save()
    assert "content_hash" in refusal.value.message_dict


@pytest.mark.django_db
def test_the_sealing_timestamp_is_written_once(incident, responder):
    """Rule : the transition stamps are the record of who decided what, and when."""
    evidence = sealed_evidence(incident, responder)

    stored = IncidentEvidence.objects.get(pk=evidence.pk)
    stored.sealed_at = timezone.now()
    with pytest.raises(ValidationError) as refusal:
        stored.save()
    assert "sealed_at" in refusal.value.message_dict


# --- The ledger : one row per handling act, and not one more ----------------


@pytest.mark.django_db
def test_each_handling_act_appends_exactly_one_ledger_row(incident, responder):
    """Rule : registering, sealing and examining are handling acts (RG-INC-22)."""
    evidence = collected_evidence(incident, responder, content_hash="c" * 64,
                                  collection_method="dd through a write blocker.")

    assert actions(evidence) == [CustodyAction.COLLECTED]

    evidence.transition_to(EVIDENCE_SECURED, responder)
    assert actions(evidence) == [CustodyAction.COLLECTED, CustodyAction.SEALED]

    evidence.transition_to(EVIDENCE_ANALYSED, responder)
    assert actions(evidence) == [
        CustodyAction.COLLECTED,
        CustodyAction.SEALED,
        CustodyAction.ANALYSED,
    ]


@pytest.mark.django_db
def test_an_automatic_ledger_row_is_marked_as_appended_by_the_lifecycle(
    incident, responder
):
    """The one thing the ledger must distinguish : what nobody typed."""
    evidence = sealed_evidence(incident, responder)
    seal = ledger(evidence).get(action=CustodyAction.SEALED)

    assert seal.source == TimelineEntrySource.LIFECYCLE
    assert seal.actor == responder
    assert seal.hash_at_event == evidence.content_hash
    assert seal.integrity_ok is None, "sealing measures, it does not verify"


@pytest.mark.django_db
def test_moving_into_retention_appends_no_ledger_row(incident, responder):
    """Rule : retention changes how the platform governs the item, not who holds it.

    There is deliberately no ``retained`` value in ``CustodyAction`` : both
    Retain edges are governance, and a ledger padded with rows for acts that
    handled nothing is a ledger nobody can read.
    """
    from_secured = sealed_evidence(incident, responder)
    before = ledger(from_secured).count()
    from_secured.transition_to(EVIDENCE_RETAINED, responder)

    assert ledger(from_secured).count() == before

    from_analysed = sealed_evidence(incident, responder)
    from_analysed.transition_to(EVIDENCE_ANALYSED, responder)
    before = ledger(from_analysed).count()
    from_analysed.transition_to(EVIDENCE_RETAINED, responder)

    assert ledger(from_analysed).count() == before


@pytest.mark.django_db
def test_the_archive_and_restore_bookends_append_no_ledger_row(incident, responder):
    """Rule : the bookends are governance, not custody."""
    evidence = IncidentEvidenceFactory(incident=incident, collected_by=responder)

    walk(evidence, EVIDENCE_ARCHIVED, EVIDENCE_DRAFT, user=responder)

    assert ledger(evidence).count() == 0


# --- GE-03 : a release goes to somebody -------------------------------------


@pytest.mark.django_db
def test_releasing_evidence_requires_the_person_taking_custody(incident, responder):
    """Rule : releasing an artefact to nobody in particular is not a release."""
    evidence = retained_evidence(incident, responder)

    with pytest.raises(DomainRefusalError):
        evidence.transition_to(EVIDENCE_RELEASED, responder, comment=COMMENT)

    evidence.transition_to(
        EVIDENCE_RELEASED,
        responder,
        comment=COMMENT,
        counterparty="Capitaine A. Morel",
        counterparty_organisation="Gendarmerie nationale, C3N",
    )

    assert evidence.workflow_state == EVIDENCE_RELEASED
    release = ledger(evidence).get(action=CustodyAction.RELEASED)
    assert release.counterparty == "Capitaine A. Morel"


# --- GE-04 : destruction is a permission, never an instruction --------------


@pytest.mark.django_db
def test_evidence_under_legal_hold_is_never_destroyed(incident, responder):
    """Rule : the hold blocks destruction outright, whatever the retention date."""
    evidence = retained_evidence(
        incident,
        responder,
        legal_hold=True,
        retention_until=timezone.localdate() - timedelta(days=1),
    )

    with pytest.raises(DomainRefusalError):
        evidence.transition_to(
            EVIDENCE_DESTROYED, responder, comment=COMMENT, counterparty="A. Morel"
        )


@pytest.mark.django_db
def test_destruction_requires_a_retention_date_that_has_actually_passed(
    incident, responder
):
    """Rule : the date must be set, and strictly in the past.

    Today is not *after* today. An item whose retention expires this evening is
    still in retention this morning.
    """
    evidence = retained_evidence(incident, responder, retention_until=None)

    with pytest.raises(DomainRefusalError):
        evidence.transition_to(
            EVIDENCE_DESTROYED, responder, comment=COMMENT, counterparty="A. Morel"
        )

    evidence.retention_until = timezone.localdate()
    evidence.save()
    with pytest.raises(DomainRefusalError):
        evidence.transition_to(
            EVIDENCE_DESTROYED, responder, comment=COMMENT, counterparty="A. Morel"
        )

    evidence.retention_until = timezone.localdate() - timedelta(days=1)
    evidence.save()
    evidence.transition_to(
        EVIDENCE_DESTROYED, responder, comment=COMMENT, counterparty="A. Morel"
    )

    assert evidence.workflow_state == EVIDENCE_DESTROYED


@pytest.mark.django_db
def test_destruction_requires_the_person_who_performed_it(incident, responder):
    """Rule : a disposal witnessed by nobody is not a disposal."""
    evidence = retained_evidence(
        incident, responder, retention_until=timezone.localdate() - timedelta(days=1)
    )

    with pytest.raises(DomainRefusalError):
        evidence.transition_to(EVIDENCE_DESTROYED, responder, comment=COMMENT)


@pytest.mark.django_db
def test_destruction_removes_the_artefact_and_keeps_the_record_of_it(
    incident, responder, settings, tmp_path
):
    """Rule : destruction is a transition, never a ``DELETE`` (RG-INC-24).

    The row, the fingerprint and the ledger survive the artefact. Erasing them
    would erase the proof that the organisation ever held the item, which is
    exactly the fact A.5.28 asks it to be able to show.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    evidence = IncidentEvidenceFactory(
        incident=incident,
        collected_by=responder,
        source_description="WEB-PRD-02",
        content_hash=PAYLOAD_DIGEST,
        collection_method="Log extract taken with journalctl, witnessed.",
        original_filename="auth.log",
        file_size=len(PAYLOAD),
        retention_until=timezone.localdate() - timedelta(days=1),
    )
    evidence.file.save("auth.log", ContentFile(PAYLOAD), save=True)
    walk(evidence, EVIDENCE_COLLECTED, EVIDENCE_SECURED, EVIDENCE_RETAINED,
         user=responder)

    evidence.transition_to(
        EVIDENCE_DESTROYED,
        responder,
        comment=COMMENT,
        counterparty="B. Nguyen",
        counterparty_organisation="Certified disposal service",
    )
    evidence.refresh_from_db()

    assert evidence.workflow_state == EVIDENCE_DESTROYED
    assert evidence.has_file is False
    assert evidence.content_hash == PAYLOAD_DIGEST
    assert evidence.original_filename == "auth.log"
    assert evidence.file_size == len(PAYLOAD)
    assert evidence.destruction_authorised_by == responder
    assert ledger(evidence).filter(action=CustodyAction.DESTROYED).count() == 1


# --- GE-05 : archiving is not a way of deleting a sealed artefact -----------


@pytest.mark.django_db
def test_an_unregistered_draft_evidence_row_can_be_restored(incident, responder):
    """A typo caught before the acquisition was registered is still a typo."""
    evidence = IncidentEvidenceFactory(incident=incident, collected_by=responder)

    walk(evidence, EVIDENCE_ARCHIVED, EVIDENCE_DRAFT, user=responder)

    assert evidence.workflow_state == EVIDENCE_DRAFT
    assert evidence.is_deletable is True


@pytest.mark.django_db
def test_a_registered_evidence_item_cannot_be_restored_to_draft(incident, responder):
    """Rule : draft is the one deletable step, and a sealed artefact never returns to it."""
    evidence = sealed_evidence(incident, responder)
    evidence.transition_to(EVIDENCE_ARCHIVED, responder, comment=COMMENT)

    with pytest.raises(DomainRefusalError):
        evidence.transition_to(EVIDENCE_DRAFT, responder)


# --- Integrity verification : three outcomes, never two ---------------------


@pytest.mark.django_db
def test_a_verification_that_matches_is_recorded_on_both_rows(
    incident, responder, settings, tmp_path
):
    """The conclusive success case : the artefact was read and the digest agrees."""
    settings.MEDIA_ROOT = str(tmp_path)
    evidence = IncidentEvidenceFactory(
        incident=incident,
        collected_by=responder,
        source_description="WEB-PRD-02",
        content_hash=PAYLOAD_DIGEST,
        collection_method="Log extract taken with journalctl, witnessed.",
    )
    evidence.file.save("auth.log", ContentFile(PAYLOAD), save=True)
    walk(evidence, EVIDENCE_COLLECTED, EVIDENCE_SECURED, user=responder)

    outcome = evidence.verify_integrity(responder)
    evidence.refresh_from_db()
    row = ledger(evidence).get(action=CustodyAction.INTEGRITY_VERIFIED)

    assert outcome == VERIFICATION_MATCH
    assert evidence.last_integrity_check_ok is True
    assert evidence.last_integrity_check_at is not None
    assert row.integrity_ok is True
    assert row.hash_at_event == PAYLOAD_DIGEST
    assert row.verification_outcome == VERIFICATION_MATCH


@pytest.mark.django_db
def test_a_verification_that_disagrees_is_a_chain_of_custody_break(
    incident, responder, settings, tmp_path
):
    """A mismatch is a permanent claim about the artefact, and is recorded as one."""
    settings.MEDIA_ROOT = str(tmp_path)
    evidence = IncidentEvidenceFactory(
        incident=incident,
        collected_by=responder,
        source_description="WEB-PRD-02",
        content_hash=hashlib.sha256(b"something else entirely").hexdigest(),
        collection_method="Log extract taken with journalctl, witnessed.",
    )
    evidence.file.save("auth.log", ContentFile(PAYLOAD), save=True)
    walk(evidence, EVIDENCE_COLLECTED, EVIDENCE_SECURED, user=responder)

    outcome = evidence.verify_integrity(responder)
    evidence.refresh_from_db()
    row = ledger(evidence).get(action=CustodyAction.INTEGRITY_VERIFIED)

    assert outcome == VERIFICATION_MISMATCH
    assert evidence.last_integrity_check_ok is False
    assert row.integrity_ok is False
    assert row.verification_outcome == VERIFICATION_MISMATCH


@pytest.mark.django_db
def test_a_verification_that_could_not_read_the_artefact_is_not_a_failure(
    incident, responder
):
    """Rule : *not verifiable* is a claim about the infrastructure (RG-INC-23).

    An item registered by reference - a seized device, a disk image in a vault -
    was never held by Cairn. Recording that as a mismatch would write a
    permanent break into the append-only ledger of every such item at once, on a
    day when nothing was tampered with, and the rows could never be removed.
    """
    evidence = sealed_evidence(incident, responder)
    assert evidence.is_registered_by_reference is True

    outcome = evidence.verify_integrity(responder)
    evidence.refresh_from_db()
    row = ledger(evidence).get(action=CustodyAction.INTEGRITY_VERIFIED)

    assert outcome == VERIFICATION_NOT_VERIFIABLE
    assert evidence.last_integrity_check_ok is None, "never checked, not broken"
    assert evidence.last_integrity_check_at is not None, "still a dated attempt"
    assert row.integrity_ok is None
    assert row.hash_at_event == ""
    assert row.verification_outcome == VERIFICATION_NOT_VERIFIABLE
    assert row.notes, "the row states why the read could not be completed"


@pytest.mark.django_db
def test_an_unreadable_artefact_never_overwrites_an_earlier_good_verdict(
    incident, responder, settings, tmp_path
):
    """The consequence that matters : a lost volume does not erase what was proved.

    ``last_integrity_check_ok`` is left untouched by an inconclusive attempt, so
    the register still says the last *conclusive* verification passed.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    evidence = IncidentEvidenceFactory(
        incident=incident,
        collected_by=responder,
        source_description="WEB-PRD-02",
        content_hash=PAYLOAD_DIGEST,
        collection_method="Log extract taken with journalctl, witnessed.",
    )
    evidence.file.save("auth.log", ContentFile(PAYLOAD), save=True)
    walk(evidence, EVIDENCE_COLLECTED, EVIDENCE_SECURED, user=responder)
    assert evidence.verify_integrity(responder) == VERIFICATION_MATCH

    evidence.file.storage.delete(evidence.file.name)

    assert evidence.verify_integrity(responder) == VERIFICATION_NOT_VERIFIABLE
    evidence.refresh_from_db()
    assert evidence.last_integrity_check_ok is True

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The omission is a governed state, not a missing row.

GDPR Art. 33(1) does not say *notify*. It says notify **unless** the breach is
unlikely to result in a risk to the rights and freedoms of natural persons. That
"unless" is a legal act taken under a derogation, and Art. 33(5) requires it to
be documented. So it is a terminal lifecycle step, reached through an
approve-gated, comment-bearing transition that stamps a named decider, a
timestamp and a written rationale. A boolean column carries none of that, and an
absent row carries less still.

The rest of this file is what has to be true before the register may claim a
notification was made : a channel, the text that was transmitted, a date that is
not in the future, and for a NIS2 early warning the two verdicts the article
itself asks the filing to state.
"""
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.tests.factories import UserFactory
from core.lifecycle import DomainRefusalError, LifecycleError
from incidents.constants import NotificationChannel, NotificationRegime
from incidents.models import IncidentNotification, IncidentTimelineEntry
from incidents.models.notification import NotificationDecision, ObligationSource
from incidents.tests.factories import IncidentFactory, IncidentNotificationFactory
from incidents.tests.helpers import (
    COMMENT,
    NOTIFICATION_ACKNOWLEDGED,
    NOTIFICATION_ARCHIVED,
    NOTIFICATION_ASSESSED,
    NOTIFICATION_DRAFT,
    NOTIFICATION_DRAFTED,
    NOTIFICATION_NOT_REQUIRED,
    NOTIFICATION_REQUIRED,
    NOTIFICATION_SENT,
    assessed_obligation,
    drafted_obligation,
    walk,
)

RATIONALE = (
    "The exported file was encrypted with a key held only offline, so the data "
    "is unintelligible to anyone who obtained it."
)


@pytest.fixture
def responder(db):
    return UserFactory()


@pytest.fixture
def incident(db):
    return IncidentFactory(detected_at=timezone.now() - timedelta(hours=4))


# --- The obligation is visible before anybody decides anything --------------


@pytest.mark.django_db
def test_an_obligation_nobody_has_answered_is_visible_rather_than_absent(
    incident, responder
):
    """Rule : *we considered it and concluded nothing was owed* is not *nobody looked*.

    The row sits in ``assessed`` (To decide), it is the loudest thing on the
    incident's notification card, and it blocks closure until somebody answers.
    """
    obligation = assessed_obligation(incident, responder)

    assert obligation.workflow_state == NOTIFICATION_ASSESSED
    assert obligation.is_undecided is True
    assert obligation.decided_at is None


# --- G-01 : the omission is a judgement, and a judgement has a reason -------


@pytest.mark.django_db
def test_deciding_not_to_notify_requires_a_written_rationale(incident, responder):
    """Rule : the Art. 33(1) justification is the sentence an inspector reads first."""
    obligation = assessed_obligation(incident, responder)

    with pytest.raises(LifecycleError):
        obligation.transition_to(NOTIFICATION_NOT_REQUIRED, responder, comment="   ")

    obligation.transition_to(NOTIFICATION_NOT_REQUIRED, responder, comment=RATIONALE)

    assert obligation.workflow_state == NOTIFICATION_NOT_REQUIRED
    assert obligation.decision == NotificationDecision.NOT_REQUIRED
    assert obligation.decision_rationale == RATIONALE
    assert obligation.decided_by_id == responder.pk
    assert obligation.decided_at is not None


@pytest.mark.django_db
def test_the_rationale_is_persisted_into_the_register_and_not_only_the_ledger(
    incident, responder
):
    """Rule : the omission is readable without joining the lifecycle history."""
    obligation = assessed_obligation(incident, responder)
    obligation.transition_to(NOTIFICATION_NOT_REQUIRED, responder, comment=RATIONALE)

    stored = IncidentNotification.objects.get(pk=obligation.pk)

    assert stored.decision_rationale == RATIONALE


@pytest.mark.django_db
def test_the_database_refuses_an_omission_with_no_rationale_too(incident):
    """Belt and braces : RG-INC-25 is also a ``CheckConstraint``.

    A ``QuerySet.update()`` that set the decision without the reason would be
    refused by the database rather than silently accepted.
    """
    obligation = IncidentNotificationFactory(incident=incident)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IncidentNotification.objects.filter(pk=obligation.pk).update(
                decision=NotificationDecision.NOT_REQUIRED, decision_rationale=""
            )


@pytest.mark.django_db
def test_reopening_a_decision_clears_the_verdict_and_keeps_the_fact_it_was_taken(
    incident, responder
):
    """Rule : ``decided_by`` and ``decided_at`` survive a reopening.

    They record that a decision was once taken, which is a fact, and the
    rationale that went with it stays readable in the register.
    """
    obligation = assessed_obligation(incident, responder)
    obligation.transition_to(NOTIFICATION_NOT_REQUIRED, responder, comment=RATIONALE)
    decided_at = obligation.decided_at

    obligation.transition_to(
        NOTIFICATION_ASSESSED, responder, comment="Reopened after the forensic report."
    )

    assert obligation.decision == NotificationDecision.UNDECIDED
    assert obligation.decided_at == decided_at
    assert obligation.decided_by_id == responder.pk
    assert obligation.decision_rationale == RATIONALE


@pytest.mark.django_db
def test_deciding_an_obligation_is_required_mirrors_the_step_onto_the_column(
    incident, responder
):
    """The column exists so filters, facets and the closure gate never read the lifecycle."""
    obligation = assessed_obligation(incident, responder)

    obligation.transition_to(NOTIFICATION_REQUIRED, responder, comment=COMMENT)

    assert obligation.decision == NotificationDecision.REQUIRED
    assert obligation.decided_by_id == responder.pk


# --- G-02 : a filing has a channel, a content and a date in the past --------


@pytest.mark.django_db
def test_recording_a_filing_requires_the_channel_it_went_through(incident, responder):
    """Rule : a filing with no channel is not a filing."""
    obligation = drafted_obligation(incident, responder)
    obligation.stage_filing_details(content="Notification under Art. 33(1).")

    with pytest.raises(DomainRefusalError):
        obligation.transition_to(NOTIFICATION_SENT, responder)

    obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Notification under Art. 33(1).",
    )

    assert obligation.workflow_state == NOTIFICATION_SENT


@pytest.mark.django_db
def test_recording_a_filing_requires_the_content_that_was_transmitted(
    incident, responder
):
    """Rule : the verbatim text is the field an inspector reads."""
    obligation = drafted_obligation(incident, responder)

    with pytest.raises(DomainRefusalError):
        obligation.record_filing(
            responder, channel=NotificationChannel.EMAIL, content="   "
        )

    assert obligation.filings.count() == 0


@pytest.mark.django_db
def test_a_filing_cannot_be_recorded_in_the_future(incident, responder):
    """A transmission that has not happened yet has not happened."""
    obligation = drafted_obligation(incident, responder)

    with pytest.raises(DomainRefusalError):
        obligation.record_filing(
            responder,
            channel=NotificationChannel.PORTAL,
            content="Notification under Art. 33(1).",
            submitted_at=timezone.now() + timedelta(hours=1),
        )


@pytest.mark.django_db
def test_a_filing_transition_leaves_exactly_one_filing_and_one_chronology_line(
    incident, responder
):
    """Rule : the transmission and its record are written in one transaction.

    Recorded here rather than left to the caller, so a transmission can never be
    recorded without the lateness verdict that goes with it, on any of the three
    write surfaces.
    """
    obligation = drafted_obligation(incident, responder)

    obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Notification under Art. 33(1).",
    )

    assert obligation.filings.count() == 1
    assert obligation.sent_by_id == responder.pk
    assert (
        IncidentTimelineEntry.objects.filter(
            incident=incident, summary__startswith="Notification filed"
        ).count()
        == 1
    )


# --- G-03 : NIS2 Art. 23(4)(a) asks two questions the record must answer ----


@pytest.mark.django_db
def test_a_nis2_early_warning_cannot_be_filed_while_its_verdicts_are_unknown(
    incident, responder
):
    """Rule : the three verdicts are compared to ``True``, never truth-tested.

    *Not yet determined* is not *no*. An early warning that cannot answer the
    article's own questions is not filed blank : the gate says so.
    """
    obligation = drafted_obligation(
        incident,
        responder,
        regime=NotificationRegime.NIS2_EARLY_WARNING,
        deadline_hours=24,
    )

    with pytest.raises(DomainRefusalError):
        obligation.record_filing(
            responder,
            channel=NotificationChannel.PORTAL,
            content="Early warning under NIS2 Art. 23(4)(a).",
        )

    incident.is_significant = True
    incident.suspected_malicious = False
    incident.suspected_malicious_justification = "No indicator of an intentional act."
    incident.cross_border_impact = False
    incident.cross_border_justification = "All affected users are in one Member State."
    incident.save()
    obligation.refresh_from_db()

    obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Early warning under NIS2 Art. 23(4)(a).",
    )

    assert obligation.workflow_state == NOTIFICATION_SENT


@pytest.mark.django_db
def test_a_recorded_no_is_a_verdict_and_unblocks_the_early_warning(
    incident, responder
):
    """The distinction the three-state flags exist for, stated on its own.

    Three recorded ``False`` answers satisfy the gate exactly as three ``True``
    ones do : what it refuses is silence.
    """
    incident.is_significant = False
    incident.suspected_malicious = False
    incident.suspected_malicious_justification = "Accidental misconfiguration."
    incident.cross_border_impact = False
    incident.cross_border_justification = "Single Member State."
    incident.save()
    obligation = drafted_obligation(
        incident,
        responder,
        regime=NotificationRegime.NIS2_EARLY_WARNING,
        deadline_hours=24,
    )

    obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Early warning under NIS2 Art. 23(4)(a).",
    )

    assert obligation.workflow_state == NOTIFICATION_SENT


# --- G-04 : an acknowledgement with no case number is not one ---------------


@pytest.mark.django_db
def test_recording_an_acknowledgement_requires_the_recipients_case_number(
    incident, responder
):
    """Rule : the receipt is what makes the acknowledgement provable."""
    obligation = drafted_obligation(incident, responder)
    obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Notification under Art. 33(1).",
    )

    with pytest.raises(DomainRefusalError):
        obligation.transition_to(NOTIFICATION_ACKNOWLEDGED, responder)

    obligation.acknowledgement_reference = "CNIL-2026-004821"
    obligation.save()
    obligation.transition_to(NOTIFICATION_ACKNOWLEDGED, responder)

    assert obligation.workflow_state == NOTIFICATION_ACKNOWLEDGED
    assert obligation.acknowledged_at is not None


# --- The staged clock actually starts at the filing --------------------------


@pytest.mark.django_db
def test_filing_the_earlier_stage_starts_the_dependent_obligations_clock(
    incident, responder
):
    """Rule : the NIS2 final report is due one month after *this* filing.

    Until the notification is transmitted, the final report has a real deadline
    that simply has not started, which is why it is rendered as pending rather
    than as deadline-free.
    """
    notification = drafted_obligation(
        incident,
        responder,
        regime=NotificationRegime.NIS2_NOTIFICATION,
        deadline_hours=72,
    )
    final_report = IncidentNotificationFactory(
        incident=incident,
        regime=NotificationRegime.NIS2_FINAL,
        deadline_hours=720,
        clock_anchor="previous_stage",
        depends_on=notification,
    )

    assert final_report.due_at is None

    notification.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Incident notification under NIS2 Art. 23(4)(b).",
    )
    final_report.refresh_from_db()
    notification.refresh_from_db()

    assert final_report.anchor_at == notification.first_submitted_at
    assert final_report.due_at == notification.first_submitted_at + timedelta(hours=720)


# --- Deadline shapes the register must never hold ---------------------------


@pytest.mark.django_db
def test_an_obligation_states_a_delay_or_declares_it_has_none_but_never_both(incident):
    """Rule : a fabricated 72 hours on a *without undue delay* duty is worse than none."""
    both = IncidentNotificationFactory.build(
        incident=incident, deadline_hours=72, no_fixed_deadline=True
    )
    with pytest.raises(ValidationError) as refusal:
        both.clean()
    assert "deadline_hours" in refusal.value.message_dict

    neither = IncidentNotificationFactory.build(
        incident=incident, deadline_hours=None, no_fixed_deadline=False
    )
    with pytest.raises(ValidationError) as refusal:
        neither.clean()
    assert "deadline_hours" in refusal.value.message_dict


# --- The restore bookend ----------------------------------------------------


@pytest.mark.django_db
def test_an_obligation_opened_for_decision_cannot_be_restored_to_draft(
    incident, responder
):
    """Rule : ``draft`` and ``assessed`` are deletable, so restore is the dangerous edge.

    Walking an obligation of record back into a deletable step is how the
    evidence that a regime was considered would disappear.
    """
    obligation = assessed_obligation(incident, responder)
    obligation.transition_to(NOTIFICATION_ARCHIVED, responder, comment=COMMENT)

    with pytest.raises(DomainRefusalError):
        obligation.transition_to(NOTIFICATION_DRAFT, responder)


@pytest.mark.django_db
def test_an_obligation_typed_in_by_hand_and_never_opened_stays_removable(
    incident, responder
):
    """A manual row created in error is not evidence of anything, and may go."""
    obligation = IncidentNotificationFactory(
        incident=incident, source=ObligationSource.MANUAL
    )

    walk(obligation, NOTIFICATION_ARCHIVED, NOTIFICATION_DRAFT, user=responder)
    obligation.delete()

    assert IncidentNotification.objects.filter(pk=obligation.pk).exists() is False


@pytest.mark.django_db
def test_an_overdue_obligation_is_derived_and_never_stored(responder):
    """Rule : lateness before a filing is a query, so it is right the instant
    the clock passes and there is no status column to fall out of date."""
    incident = IncidentFactory(detected_at=timezone.now() - timedelta(hours=100))
    obligation = assessed_obligation(incident, responder, deadline_hours=72)

    assert obligation.is_overdue is True

    walk(obligation, NOTIFICATION_REQUIRED, NOTIFICATION_DRAFTED, user=responder)
    obligation.record_filing(
        responder,
        channel=NotificationChannel.PORTAL,
        content="Notification under Art. 33(1).",
    )

    assert obligation.is_overdue is False, "a filed obligation is late, not overdue"
    assert obligation.was_filed_late is True

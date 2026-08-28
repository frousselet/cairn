# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Detection is an indicator. Awareness is the law.

``detected_at`` is when a control, a tool or a person saw something : it is the
base of mean-time-to-detect and it has no legal meaning at all. ``awareness_at``
is the point at which the organisation became aware within the meaning of GDPR
Art. 33(1) and NIS2 Art. 23, and **every** statutory deadline in the module
derives from it and from nothing else.

The tests below do not merely assert that a deadline is computed. They assert
that a deadline computed from the other timestamp would be a different date, so
an implementation that quietly anchored on detection could not pass them.
"""
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.tests.factories import UserFactory
from incidents.constants import ClockAnchor, NotificationRegime
from incidents.models.notification import DEADLINE_BUCKET_NO_DEADLINE, DEADLINE_BUCKET_PENDING
from incidents.tests.factories import (
    IncidentFactory,
    IncidentNotificationFactory,
    IncidentResponsePlanFactory,
)
from incidents.tests.helpers import triaged_incident

#: A 30-hour gap between the technical detection and the legal awareness. Wide
#: enough that a 72-hour deadline anchored on the wrong one lands on a
#: different day, which is the point of every assertion below.
GAP = timedelta(hours=30)


@pytest.fixture
def responder(db):
    return UserFactory()


@pytest.fixture
def detected_at():
    """A detection far enough in the past that a filing can be recorded after it."""
    return timezone.now() - timedelta(hours=200)


# --- The default ------------------------------------------------------------


@pytest.mark.django_db
def test_awareness_defaults_to_the_detection_timestamp(detected_at):
    """Rule : a blank legal anchor means the organisation became aware when it detected.

    True far more often than not, so the common case is correct with no operator
    action and the operator only has to act on the case where it is not.
    """
    incident = IncidentFactory(detected_at=detected_at, awareness_at=None)

    assert incident.awareness_at == detected_at


@pytest.mark.django_db
def test_a_stated_awareness_timestamp_is_never_overwritten_by_the_default(detected_at):
    """The back-fill fills a blank; it does not correct a stated fact."""
    incident = IncidentFactory(
        detected_at=detected_at,
        awareness_at=detected_at + GAP,
        awareness_justification="The supplier notification arrived on the Monday.",
    )

    assert incident.awareness_at == detected_at + GAP


# --- The gap is a claim, and a claim needs a reason --------------------------


@pytest.mark.django_db
def test_a_gap_between_detection_and_awareness_requires_a_written_justification(
    detected_at,
):
    """Rule : the gap is defensible, but only when written down at the time.

    A gap is what pushes a statutory deadline later, so it is exactly the field
    a supervisory-authority inspector attacks first.
    """
    incident = IncidentFactory(
        detected_at=detected_at, awareness_at=detected_at + GAP
    )

    with pytest.raises(ValidationError) as refusal:
        incident.clean()
    assert "awareness_justification" in refusal.value.message_dict

    incident.awareness_justification = "The SOC alert went unread over the weekend."
    incident.clean()


@pytest.mark.django_db
def test_awareness_before_detection_is_refused_outright(detected_at):
    """No justification makes an anchor earlier than the record that produced it."""
    incident = IncidentFactory(
        detected_at=detected_at, awareness_at=detected_at - timedelta(hours=1)
    )

    with pytest.raises(ValidationError) as refusal:
        incident.clean()
    assert "awareness_at" in refusal.value.message_dict


# --- Every deadline counts from awareness -----------------------------------


@pytest.mark.django_db
def test_a_statutory_deadline_counts_from_awareness_and_not_from_detection(
    detected_at,
):
    """Rule : the 72 hours of GDPR Art. 33(1) run from awareness.

    The assertion that matters is the last one : anchoring on the detection
    timestamp instead would produce a deadline 30 hours earlier, so this test
    cannot pass against an implementation that used the wrong field.
    """
    incident = IncidentFactory(
        detected_at=detected_at,
        awareness_at=detected_at + GAP,
        awareness_justification="Confirmed by the forensic provider on the Monday.",
    )

    obligation = IncidentNotificationFactory(
        incident=incident, deadline_hours=72, clock_anchor=ClockAnchor.AWARENESS_AT
    )

    assert obligation.anchor_at == incident.awareness_at
    assert obligation.due_at == incident.awareness_at + timedelta(hours=72)
    assert obligation.due_at != incident.detected_at + timedelta(hours=72)
    assert obligation.due_at - (incident.detected_at + timedelta(hours=72)) == GAP


@pytest.mark.django_db
def test_an_obligation_generated_at_triage_is_anchored_on_awareness(responder, detected_at):
    """The default is not a form default : a generated obligation carries it too.

    Generation is where most obligations come from, so an anchor that was right
    only when an operator typed it would be right almost nowhere.
    """
    plan = IncidentResponsePlanFactory(
        applicable_regimes=[NotificationRegime.GDPR_ART33_AUTHORITY]
    )
    incident = triaged_incident(
        responder,
        response_plan=plan,
        detected_at=detected_at,
        awareness_at=detected_at + GAP,
        awareness_justification="The supplier notified us 30 hours after our own alert.",
    )

    obligation = incident.notifications.get(
        regime=NotificationRegime.GDPR_ART33_AUTHORITY
    )

    assert obligation.clock_anchor == ClockAnchor.AWARENESS_AT
    assert obligation.anchor_at == incident.awareness_at
    assert obligation.due_at == incident.awareness_at + timedelta(hours=72)
    assert obligation.due_at != incident.detected_at + timedelta(hours=72)


@pytest.mark.django_db
def test_the_anchor_is_resolved_by_field_name_so_a_detection_anchor_is_honoured(
    detected_at,
):
    """The four incident anchors are the incident's own field names.

    A deployment whose regulator counts from technical detection says so on the
    obligation, and the resolution is a lookup with no mapping table to drift.
    """
    incident = IncidentFactory(
        detected_at=detected_at,
        awareness_at=detected_at + GAP,
        awareness_justification="Escalated to the DPO the following Monday.",
    )

    obligation = IncidentNotificationFactory(
        incident=incident, deadline_hours=24, clock_anchor=ClockAnchor.DETECTED_AT
    )

    assert obligation.anchor_at == incident.detected_at
    assert obligation.due_at == incident.detected_at + timedelta(hours=24)


@pytest.mark.django_db
def test_the_clock_follows_a_correction_of_the_anchor_while_no_filing_exists(
    detected_at,
):
    """Rule : facts change, and an unfiled deadline follows them.

    The freeze that stops this is the *first filing*, not the passage of time :
    see ``test_lateness_is_frozen``.
    """
    incident = IncidentFactory(detected_at=detected_at, awareness_at=None)
    obligation = IncidentNotificationFactory(incident=incident, deadline_hours=72)
    original_due_at = obligation.due_at

    incident.awareness_at = detected_at + GAP
    incident.awareness_justification = "Corrected after the forensic report."
    incident.save()
    obligation.refresh_from_db()
    obligation.save()

    assert obligation.anchor_at == detected_at + GAP
    assert obligation.due_at == original_due_at + GAP


# --- The three deadline buckets ---------------------------------------------


@pytest.mark.django_db
def test_an_obligation_with_no_statutory_deadline_is_never_given_a_fabricated_one(
    detected_at,
):
    """Rule : 'without undue delay' has no hours, so the register states none.

    GDPR Art. 33(2) and Art. 34(1) state no numeric limit. Inventing 72 hours
    for them would make the register say something the law does not.
    """
    incident = IncidentFactory(detected_at=detected_at)

    obligation = IncidentNotificationFactory(
        incident=incident,
        regime=NotificationRegime.GDPR_ART33_2_CONTROLLER,
        deadline_hours=None,
        no_fixed_deadline=True,
    )

    assert obligation.anchor_at is None
    assert obligation.due_at is None
    assert obligation.deadline_bucket == DEADLINE_BUCKET_NO_DEADLINE
    assert obligation.is_overdue is False


@pytest.mark.django_db
def test_a_staged_clock_that_has_not_started_is_pending_and_not_deadline_free(
    detected_at,
):
    """Rule : *no deadline in law* and *deadline not yet started* are two states.

    The NIS2 Art. 23(4)(d) final report is due one month after the incident
    notification is filed, not one month after awareness. Merging the two undated
    buckets is how a real deadline disappears from a dashboard.
    """
    incident = IncidentFactory(detected_at=detected_at)

    final_report = IncidentNotificationFactory(
        incident=incident,
        regime=NotificationRegime.NIS2_FINAL,
        deadline_hours=720,
        clock_anchor=ClockAnchor.PREVIOUS_STAGE,
    )

    assert final_report.due_at is None
    assert final_report.no_fixed_deadline is False
    assert final_report.deadline_bucket == DEADLINE_BUCKET_PENDING

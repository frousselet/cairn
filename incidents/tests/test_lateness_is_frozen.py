# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A breach that happened cannot stop having happened.

``Incident.awareness_at`` stays editable after triage, and it should : facts
change, a forensic report moves the date the organisation is held to have known.
But the moment a notification is filed, the deadline it was filed against
becomes a fact of record. Without the freeze, a six-hour correction of the
anchor would move ``due_at`` past a filing that was late when it was made, and
an obligation that breached the 72-hour limit of GDPR Art. 33(1) would quietly
stop having breached it, with nothing left in the record to show that it ever
did.

This is the single most audit-relevant property in the module, so it is tested
from both ends : the correction is applied, and the breach is still there.
"""
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.tests.factories import UserFactory
from incidents.constants import FilingOutcome, NotificationChannel
from incidents.models import IncidentNotification
from incidents.tests.factories import IncidentFactory
from incidents.tests.helpers import NOTIFICATION_SENT, drafted_obligation

#: The obligation was due 128 hours ago : a filing recorded now is unambiguously
#: late, and no rounding or timezone subtlety can make it otherwise.
AGE = timedelta(hours=200)
DEADLINE_HOURS = 72
EXPECTED_LATENESS = AGE - timedelta(hours=DEADLINE_HOURS)


@pytest.fixture
def responder(db):
    return UserFactory()


@pytest.fixture
def late_obligation(responder):
    """An obligation whose 72-hour deadline passed 128 hours ago, drafted and unfiled."""
    incident = IncidentFactory(detected_at=timezone.now() - AGE)
    return drafted_obligation(incident, responder, deadline_hours=DEADLINE_HOURS)


def file_it(obligation, user, **kwargs):
    kwargs.setdefault("channel", NotificationChannel.PORTAL)
    kwargs.setdefault("content", "Notification under GDPR Art. 33(1).")
    return obligation.record_filing(user, **kwargs)


# --- The verdict is taken once, at the filing --------------------------------


@pytest.mark.django_db
def test_the_first_filing_freezes_the_lateness_verdict(late_obligation, responder):
    """Rule : ``first_submitted_at`` and ``late_by`` are stamped by the first filing."""
    file_it(late_obligation, responder)
    late_obligation.refresh_from_db()

    assert late_obligation.workflow_state == NOTIFICATION_SENT
    assert late_obligation.first_submitted_at is not None
    assert late_obligation.was_filed_late is True
    # A second of tolerance : the stamp is `timezone.now()` inside the transition.
    assert abs(late_obligation.late_by - EXPECTED_LATENESS) < timedelta(seconds=5)


@pytest.mark.django_db
def test_a_filing_made_inside_the_deadline_records_no_breach(responder):
    """The other half of the rule : on time is recorded as on time.

    A freeze that stamped every filing as late would pass a refusal-only test
    just as well as the real implementation does.
    """
    incident = IncidentFactory(detected_at=timezone.now() - timedelta(hours=1))
    obligation = drafted_obligation(incident, responder, deadline_hours=DEADLINE_HOURS)

    file_it(obligation, responder)
    obligation.refresh_from_db()

    assert obligation.first_submitted_at is not None
    assert obligation.late_by is None
    assert obligation.was_filed_late is False


# --- The correction that must not un-breach anything -------------------------


@pytest.mark.django_db
def test_correcting_the_anchor_after_a_filing_cannot_un_breach_it(
    late_obligation, responder
):
    """Rule : the clock of a filed obligation never recomputes again (RG-INC-28).

    The correction here is exactly the one that would help : moving the legal
    awareness forward by 200 hours, which would put the deadline comfortably
    after the filing. The register must not accept the invitation.
    """
    file_it(late_obligation, responder)
    late_obligation.refresh_from_db()
    frozen_due_at = late_obligation.due_at
    frozen_lateness = late_obligation.late_by

    incident = late_obligation.incident
    incident.awareness_at = timezone.now()
    incident.awareness_justification = "Corrected after the forensic report."
    incident.save()

    reloaded = IncidentNotification.objects.get(pk=late_obligation.pk)
    reloaded.save()
    reloaded.refresh_from_db()

    assert reloaded.anchor_at == incident.detected_at
    assert reloaded.due_at == frozen_due_at
    assert reloaded.late_by == frozen_lateness
    assert reloaded.was_filed_late is True


@pytest.mark.django_db
def test_the_clock_of_a_filed_obligation_cannot_be_written_directly_either(
    late_obligation, responder
):
    """Rule : the freeze is not only *stop recomputing*, it is *refuse the write*.

    Otherwise the same un-breaching would be one ``obligation.due_at = ...``
    away on the API, the MCP update tool or the Django admin.
    """
    file_it(late_obligation, responder)

    obligation = IncidentNotification.objects.get(pk=late_obligation.pk)
    obligation.due_at = timezone.now() + timedelta(hours=72)
    with pytest.raises(ValidationError) as refusal:
        obligation.save()
    assert "due_at" in refusal.value.message_dict

    obligation = IncidentNotification.objects.get(pk=late_obligation.pk)
    obligation.anchor_at = timezone.now()
    with pytest.raises(ValidationError) as refusal:
        obligation.save()
    assert "anchor_at" in refusal.value.message_dict


@pytest.mark.django_db
def test_the_lateness_verdict_itself_cannot_be_erased(late_obligation, responder):
    """Rule : ``late_by`` and ``first_submitted_at`` are written once, on every path.

    The guard re-reads the stored row and compares field by field, so it covers
    the web form, the DRF serializer, the MCP update tool and the admin at once.
    """
    file_it(late_obligation, responder)

    obligation = IncidentNotification.objects.get(pk=late_obligation.pk)
    obligation.late_by = None
    with pytest.raises(ValidationError) as refusal:
        obligation.save()
    assert "late_by" in refusal.value.message_dict

    obligation = IncidentNotification.objects.get(pk=late_obligation.pk)
    obligation.first_submitted_at = timezone.now()
    with pytest.raises(ValidationError) as refusal:
        obligation.save()
    assert "first_submitted_at" in refusal.value.message_dict


@pytest.mark.django_db
def test_what_was_transmitted_is_not_rewritten_after_the_filing(
    late_obligation, responder
):
    """Rule : an amendment is a further filing, never an edit of what was sent."""
    file_it(late_obligation, responder)

    obligation = IncidentNotification.objects.get(pk=late_obligation.pk)
    obligation.content = "A tidier account of what we meant to say."
    with pytest.raises(ValidationError) as refusal:
        obligation.save()
    assert "content" in refusal.value.message_dict


# --- Further filings leave the frozen verdict alone --------------------------


@pytest.mark.django_db
def test_a_later_corrective_filing_does_not_move_the_frozen_verdict(
    late_obligation, responder
):
    """Rule : one obligation, one clock, one decision, one lateness verdict.

    GDPR Art. 33(4) phased provision is a further filing on the same obligation.
    A supplementary transmission made on time does not retrospectively make the
    first one punctual.
    """
    first = file_it(late_obligation, responder)
    late_obligation.refresh_from_db()
    frozen_lateness = late_obligation.late_by

    correction = late_obligation.record_filing(
        responder,
        channel=NotificationChannel.EMAIL,
        content="Supplementary information under Art. 33(4).",
        is_correction=True,
        supersedes=first,
    )
    late_obligation.refresh_from_db()

    assert late_obligation.filings.count() == 2
    assert late_obligation.late_by == frozen_lateness
    assert late_obligation.first_submitted_at == first.submitted_at
    assert correction.supersedes_id == first.pk
    assert first.is_superseded is True


@pytest.mark.django_db
def test_each_filing_carries_its_own_verdict_frozen_at_its_own_insert(
    late_obligation, responder
):
    """Rule : ``NotificationFiling.was_late`` is read off the obligation's frozen
    deadline at the moment of insert, and never recomputed.

    The obligation says whether the *duty* was discharged late; each filing says
    whether *that transmission* was.
    """
    first = file_it(late_obligation, responder)
    correction = late_obligation.record_filing(
        responder,
        channel=NotificationChannel.EMAIL,
        content="Supplementary information.",
        is_correction=True,
        supersedes=first,
    )

    assert first.was_late is True
    assert correction.was_late is True


@pytest.mark.django_db
def test_the_first_filing_is_never_a_correction(late_obligation, responder):
    """There is nothing to correct until something has been transmitted."""
    with pytest.raises(ValidationError):
        file_it(late_obligation, responder, is_correction=True)

    assert late_obligation.filings.count() == 0


# --- The narrow completion exception -----------------------------------------


@pytest.mark.django_db
def test_the_recipients_answer_may_be_recorded_once_and_only_once(
    late_obligation, responder
):
    """Rule : what we said is frozen; what they answered is completable.

    Exactly three fields move after the insert, each once, from its insert value
    to a set value : the outcome, the acknowledgement date and the case number.
    """
    from core.lifecycle import LifecycleProtectedError

    filing = file_it(late_obligation, responder)

    filing.record_outcome(
        outcome=FilingOutcome.ACKNOWLEDGED,
        acknowledged_at=timezone.now(),
        external_reference="CNIL-2026-004821",
    )
    filing.refresh_from_db()

    assert filing.outcome == FilingOutcome.ACKNOWLEDGED
    assert filing.external_reference == "CNIL-2026-004821"
    assert filing.version == 2

    with pytest.raises(LifecycleProtectedError):
        filing.record_outcome(external_reference="CNIL-2026-004822")

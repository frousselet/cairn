# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The GDPR qualification, and why ``controller_role`` is not a detail.

A controller owes Art. 33(1) to the supervisory authority and may owe Art. 34(1)
to the data subjects. A processor owes **neither** : it owes Art. 33(2) to its
controller, and nothing else. Filing with the supervisory authority as a
processor is not a harmless excess of zeal - it discloses a client's breach on
that client's behalf, without the client's decision, and it may pre-empt or
contradict the controller's own filing.

So the role is a generation input, and generation is re-run on confirmation
precisely because that is the moment the role stops being an assumption. The
other half of the file is the rule that a breach is **ruled out by a named
person through a transition**, never by unchecking a box : *"we considered it and
concluded it was not a personal data breach"* is exactly the sentence a
supervisory authority asks to see.
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.tests.factories import UserFactory
from core.lifecycle import DomainRefusalError
from incidents.constants import Art34Ground, ControllerRole, NotificationRegime
from incidents.models import PersonalDataBreach
from incidents.tests.factories import PersonalDataBreachFactory
from incidents.tests.helpers import (
    BREACH_ARCHIVED,
    BREACH_CONFIRMED,
    BREACH_DOCUMENTED,
    BREACH_DRAFT,
    BREACH_NOT_A_BREACH,
    BREACH_UNDER_QUALIFICATION,
    COMMENT,
    article_33_3_content,
    triaged_incident,
    walk,
)


@pytest.fixture
def dpo(db):
    return UserFactory()


@pytest.fixture
def incident(dpo):
    """A triaged incident that declared personal data, so its qualification exists."""
    return triaged_incident(
        dpo, personal_data_involved=True, no_obligation_justification=""
    )


def qualification(incident, **fields):
    breach = PersonalDataBreach.objects.get(incident=incident)
    for name, value in fields.items():
        setattr(breach, name, value)
    breach.save()
    return breach


# --- G-01 : the Art. 33(3)(a) to (d) minimum content ------------------------


@pytest.mark.django_db
def test_confirming_a_breach_requires_the_full_article_33_3_content(incident, dpo):
    """Rule : the four elements every Art. 33 filing is drafted from.

    Nature, DPO contact, likely consequences and measures taken. A record
    missing one of them is not one a notification can be written from.
    """
    breach = qualification(incident, high_risk_to_rights=False)

    with pytest.raises(DomainRefusalError):
        breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    for field, value in article_33_3_content().items():
        setattr(breach, field, value)
    breach.save()
    breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    assert breach.workflow_state == BREACH_CONFIRMED
    assert breach.has_article_33_3_content is True


@pytest.mark.django_db
def test_the_content_is_checked_again_on_the_reopen_edge(incident, dpo):
    """Rule : the gate sits on *every* edge into ``confirmed``.

    A record whose content has since been emptied is not one an amendment can be
    drafted from either.
    """
    breach = qualification(
        incident, high_risk_to_rights=False, **article_33_3_content()
    )
    walk(breach, BREACH_CONFIRMED, BREACH_DOCUMENTED, user=dpo, comment=COMMENT)

    breach.measures_taken = ""
    breach.save()

    with pytest.raises(DomainRefusalError):
        breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)


# --- G-02 : None is not a verdict -------------------------------------------


@pytest.mark.django_db
def test_confirming_a_breach_requires_the_article_34_determination(incident, dpo):
    """Rule : the DPO is made to say yes or no, in writing, because Art. 34(1)
    turns on it.

    ``None`` means *not yet determined*. It is not a match for anything and it is
    not the same answer as a recorded no.
    """
    breach = qualification(incident, **article_33_3_content())
    assert breach.high_risk_to_rights is None

    with pytest.raises(DomainRefusalError):
        breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    breach.high_risk_to_rights = False
    breach.high_risk_justification = "The exported data was pseudonymised."
    breach.save()
    breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    assert breach.workflow_state == BREACH_CONFIRMED


# --- G-04 : an exemption asserted with no reason is not an exemption --------


@pytest.mark.django_db
def test_an_article_34_exemption_must_carry_its_written_justification(incident, dpo):
    """Rule : the Art. 34(3) ground is recorded, never assumed.

    Refused by the transition gate, by ``clean()`` so the form says it first, and
    by a database ``CheckConstraint``.
    """
    breach = qualification(
        incident, high_risk_to_rights=True, **article_33_3_content()
    )
    # Set in memory only : the database constraint would refuse the row outright,
    # which is the third of the three guards and is asserted separately below.
    breach.article_34_exemption = Art34Ground.ENCRYPTION

    with pytest.raises(ValidationError) as refusal:
        breach.clean()
    assert "article_34_exemption_justification" in refusal.value.message_dict

    with pytest.raises(DomainRefusalError):
        breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PersonalDataBreach.objects.filter(pk=breach.pk).update(
                article_34_exemption=Art34Ground.ENCRYPTION,
                article_34_exemption_justification="",
            )

    breach.article_34_exemption_justification = (
        "The export was AES-256 encrypted and the key was never exposed."
    )
    breach.save()
    breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    assert breach.workflow_state == BREACH_CONFIRMED


# --- The verdict stamp ------------------------------------------------------


@pytest.mark.django_db
def test_the_qualification_stamp_records_the_first_pronouncement_only(incident, dpo):
    """Rule : a reopen never re-stamps (RG-INC-12).

    The stamp records when the qualification was first pronounced and by whom.
    Re-stamping would overwrite the first pronouncement with the last, which is
    exactly the fact an inspector asks about when an exclusion was reversed.
    """
    breach = qualification(
        incident, high_risk_to_rights=False, **article_33_3_content()
    )
    breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)
    first_verdict_at = breach.qualified_at

    breach.transition_to(
        BREACH_UNDER_QUALIFICATION, dpo, comment="Reopened after new forensics."
    )
    breach.transition_to(BREACH_CONFIRMED, UserFactory(), comment=COMMENT)

    assert breach.qualified_at == first_verdict_at
    assert breach.qualified_by_id == dpo.pk


@pytest.mark.django_db
def test_the_qualification_stamp_cannot_be_rewritten_by_a_direct_save(incident, dpo):
    """Rule : the guard re-reads the stored row, so it covers every write path."""
    from django.utils import timezone

    breach = qualification(
        incident, high_risk_to_rights=False, **article_33_3_content()
    )
    breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    stored = PersonalDataBreach.objects.get(pk=breach.pk)
    stored.qualified_at = timezone.now()
    with pytest.raises(ValidationError) as refusal:
        stored.save()
    assert "qualified_at" in refusal.value.message_dict


# --- Ruling a breach out is an act, never the absence of one ----------------


@pytest.mark.django_db
def test_clearing_the_personal_data_flag_never_deletes_the_qualification(
    incident, dpo
):
    """Rule : RG-INC-18. Unchecking a box leaves nothing at all.

    A breach is ruled out through the record's own ``not_a_breach`` transition :
    by a named person, with a mandatory comment, at a stamped time.
    """
    breach = PersonalDataBreach.objects.get(incident=incident)

    incident.personal_data_involved = False
    incident.save()

    assert PersonalDataBreach.objects.filter(pk=breach.pk).exists()

    breach.transition_to(
        BREACH_NOT_A_BREACH,
        dpo,
        comment="The affected export contained no data relating to an identified "
        "or identifiable natural person.",
    )

    assert breach.workflow_state == BREACH_NOT_A_BREACH
    assert breach.qualified_by_id == dpo.pk
    assert breach.qualified_at is not None


@pytest.mark.django_db
def test_opening_a_qualification_twice_returns_the_existing_record(incident, dpo):
    """Rule : reopening a ruled-out qualification is a deliberate transition.

    Never a side effect of somebody ticking the personal-data box again.
    """
    breach = PersonalDataBreach.objects.get(incident=incident)
    breach.transition_to(BREACH_NOT_A_BREACH, dpo, comment="Ruled out.")

    again = PersonalDataBreach.open_qualification(incident, dpo)

    assert again.pk == breach.pk
    assert again.workflow_state == BREACH_NOT_A_BREACH


# --- G-06 : the restore bookend ---------------------------------------------


@pytest.mark.django_db
def test_an_opened_qualification_cannot_be_restored_to_draft(incident, dpo):
    """Rule : ``draft`` and ``under_qualification`` are both deletable steps.

    Without the gate, archiving then restoring would destroy the GDPR
    qualification of a real incident.
    """
    breach = PersonalDataBreach.objects.get(incident=incident)
    breach.transition_to(BREACH_ARCHIVED, dpo, comment=COMMENT)

    with pytest.raises(DomainRefusalError):
        breach.transition_to(BREACH_DRAFT, dpo)


@pytest.mark.django_db
def test_a_qualification_that_was_never_opened_can_be_restored(dpo):
    """The counterpart : a row created in error is still removable."""
    incident = triaged_incident(dpo)
    breach = PersonalDataBreachFactory(incident=incident)

    walk(breach, BREACH_ARCHIVED, BREACH_DRAFT, user=dpo, comment=COMMENT)

    assert breach.workflow_state == BREACH_DRAFT


# --- Confirmation is what settles which obligations exist -------------------


@pytest.mark.django_db
def test_confirming_a_high_risk_breach_adds_the_article_34_obligation(incident, dpo):
    """Rule : the Art. 34 duty is added only on a verdict of exactly ``True``.

    A high-risk assessment nobody has made yet is not a high risk, and it is not
    a no either, which is why the obligation appears at confirmation rather than
    at triage.
    """
    assert (
        incident.notifications.filter(
            regime=NotificationRegime.GDPR_ART34_DATA_SUBJECT
        ).exists()
        is False
    )

    breach = qualification(
        incident, high_risk_to_rights=True, **article_33_3_content()
    )
    breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    assert incident.notifications.filter(
        regime=NotificationRegime.GDPR_ART34_DATA_SUBJECT
    ).exists()
    assert incident.notifications.filter(
        regime=NotificationRegime.GDPR_ART33_AUTHORITY
    ).exists()


@pytest.mark.django_db
def test_a_processor_owes_its_controller_and_not_the_supervisory_authority(dpo):
    """Rule : Art. 33(1) and Art. 33(2) are mutually exclusive, never cumulative.

    The capacity the organisation acted in is what decides which duty exists at
    all, and generation is re-run on confirmation because that is the moment the
    role becomes a settled fact.
    """
    incident = triaged_incident(dpo)
    breach = PersonalDataBreach.open_qualification(
        incident,
        dpo,
        controller_role=ControllerRole.PROCESSOR,
        high_risk_to_rights=False,
        **article_33_3_content(),
    )
    incident.personal_data_involved = True
    incident.save()

    breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    regimes = set(incident.notifications.values_list("regime", flat=True))
    assert NotificationRegime.GDPR_ART33_2_CONTROLLER in regimes
    assert NotificationRegime.GDPR_ART33_AUTHORITY not in regimes
    assert breach.acts_as_processor is True


@pytest.mark.django_db
def test_confirming_a_breach_a_second_time_generates_nothing_new(incident, dpo):
    """Rule : generation is idempotent on this edge too.

    An obligation already created at triage is found by an explicit lookup and
    left untouched, snapshot included.
    """
    breach = qualification(
        incident, high_risk_to_rights=True, **article_33_3_content()
    )
    breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)
    after_first = set(incident.notifications.values_list("pk", flat=True))

    breach.transition_to(BREACH_UNDER_QUALIFICATION, dpo, comment="Reopened.")
    breach.transition_to(BREACH_CONFIRMED, dpo, comment=COMMENT)

    assert set(incident.notifications.values_list("pk", flat=True)) == after_first


@pytest.mark.django_db
def test_the_documented_step_is_the_article_33_5_register_entry(incident, dpo):
    """Rule : Art. 33(5) asks the controller to document every breach, notified or not."""
    breach = qualification(
        incident, high_risk_to_rights=False, **article_33_3_content()
    )
    walk(breach, BREACH_CONFIRMED, BREACH_DOCUMENTED, user=dpo, comment=COMMENT)

    assert breach.workflow_state == BREACH_DOCUMENTED
    assert breach.counts_in_reports is True

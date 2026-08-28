# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Triage is what puts the regulatory duties on the register.

An obligation nobody has thought about must be **visible** rather than absent :
that is why the rows are instantiated at triage and not when somebody decides
to file. A design that creates the row only when the notification is drafted
cannot tell *we considered GDPR Art. 33 and concluded it did not apply* from
*nobody looked*, and that distinction is what an inspection turns on.

Three properties are proved here : generation happens, re-running it changes
nothing, and an incident that owes nothing to anyone has to say why - unless it
is a drill, where owing nothing is the expected outcome rather than a finding.
"""
import pytest
from django.db import IntegrityError, transaction

from accounts.tests.factories import UserFactory
from core.lifecycle import DomainRefusalError
from core.models import LifecycleEvent
from incidents.constants import ClockAnchor, NotificationRecipientKind, NotificationRegime
from incidents.models import IncidentNotification, PersonalDataBreach
from incidents.models.notification import NotificationDecision, ObligationSource
from incidents.tests.factories import (
    IncidentNotificationFactory,
    IncidentResponsePlanFactory,
    ReportingObligationTemplateFactory,
)
from incidents.tests.helpers import (
    COMMENT,
    INCIDENT_TRIAGED,
    NOTIFICATION_ASSESSED,
    NOTIFICATION_NOT_REQUIRED,
    declared_incident,
    triaged_incident,
    walk,
)

TWO_REGIMES = [
    NotificationRegime.GDPR_ART33_AUTHORITY,
    NotificationRegime.NIS2_EARLY_WARNING,
]


@pytest.fixture
def responder(db):
    return UserFactory()


@pytest.fixture
def plan(db):
    """A response plan declaring two regimes, which is the phase-1 shape."""
    return IncidentResponsePlanFactory(applicable_regimes=TWO_REGIMES)


def in_force(template, user):
    """Walk a catalogue row to the step ``in_force()`` actually selects.

    A template left in draft is invisible to generation, so a test that built
    one by hand and asserted nothing was generated would be proving the wrong
    thing.
    """
    return walk(template, "pending", "validated", user=user, comment=COMMENT)


# --- Triage instantiates the duties -----------------------------------------


@pytest.mark.django_db
def test_triage_instantiates_one_obligation_per_configured_regime(responder, plan):
    """Rule : the duties are put on the register by triage, not by a drafter."""
    incident = triaged_incident(responder, response_plan=plan)

    assert set(incident.notifications.values_list("regime", flat=True)) == set(
        TWO_REGIMES
    )


@pytest.mark.django_db
def test_a_generated_obligation_is_opened_through_its_lifecycle(responder, plan):
    """Rule : nothing in this module is ever *created in* a domain step.

    A row inserted straight into ``assessed`` would carry no
    ``core.LifecycleEvent``, so the register would hold an obligation nobody is
    recorded as having opened. It is saved in ``draft`` and then transitioned.
    """
    incident = triaged_incident(responder, response_plan=plan)
    obligation = incident.notifications.first()

    assert obligation.workflow_state == NOTIFICATION_ASSESSED
    assert obligation.decision == NotificationDecision.UNDECIDED
    assert obligation.source == ObligationSource.AUTO
    assert LifecycleEvent.objects.filter(
        object_id=str(obligation.pk), to_step=NOTIFICATION_ASSESSED
    ).exists()


@pytest.mark.django_db
def test_a_generated_obligation_carries_its_statutory_terms(responder, plan):
    """The shipped defaults state a delay or declare there is none, never neither."""
    incident = triaged_incident(responder, response_plan=plan)

    early_warning = incident.notifications.get(
        regime=NotificationRegime.NIS2_EARLY_WARNING
    )
    authority_filing = incident.notifications.get(
        regime=NotificationRegime.GDPR_ART33_AUTHORITY
    )

    assert early_warning.deadline_hours == 24
    assert early_warning.obligation_reference == "NIS2 Art. 23(4)(a)"
    assert authority_filing.deadline_hours == 72
    assert authority_filing.obligation_reference == "GDPR Art. 33(1)"


# --- Idempotence, and the key that makes it possible ------------------------


@pytest.mark.django_db
def test_re_running_generation_creates_nothing_and_changes_nothing(responder, plan):
    """Rule : generation is idempotent, because it is re-run at every point
    where the answer can change.

    Idempotence is the generator's own job and not the constraint's : relying on
    the unique index alone would turn a re-run into an ``IntegrityError`` in the
    middle of a severity-raise save, which is a worse failure than the duplicate
    it prevents.
    """
    incident = triaged_incident(responder, response_plan=plan)
    before = list(incident.notifications.values_list("pk", flat=True))

    created = incident.generate_notification_obligations(responder)

    assert created == []
    assert list(incident.notifications.values_list("pk", flat=True)) == before


@pytest.mark.django_db
def test_the_recipient_key_is_what_makes_a_duplicate_detectable(responder, plan):
    """Rule : the uniqueness key is derived and never null.

    Keying the constraint on the nullable recipient foreign keys would not stop
    the duplicate it is written for : both are ``NULL`` on every generated
    authority obligation, and a unique index treats ``NULL``s as distinct. The
    derived discriminator is a real, comparable value, empty string included.
    """
    incident = triaged_incident(responder, response_plan=plan)
    obligation = incident.notifications.get(
        regime=NotificationRegime.GDPR_ART33_AUTHORITY
    )

    assert obligation.recipient_key == ""

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IncidentNotificationFactory(
                incident=incident,
                regime=NotificationRegime.GDPR_ART33_AUTHORITY,
                recipient_kind=NotificationRecipientKind.SUPERVISORY_AUTHORITY,
            )


@pytest.mark.django_db
def test_re_running_generation_never_revisits_a_decision_already_taken(
    responder, plan
):
    """Rule : an obligation once answered is never reopened by a re-run.

    The register's job is to record that a judgement was made. A generator that
    walked a decided obligation back to *to decide* would erase it.
    """
    incident = triaged_incident(responder, response_plan=plan)
    obligation = incident.notifications.get(
        regime=NotificationRegime.GDPR_ART33_AUTHORITY
    )
    obligation.transition_to(
        NOTIFICATION_NOT_REQUIRED,
        responder,
        comment="No personal data was affected : Art. 33(1) does not apply.",
    )

    incident.generate_notification_obligations(responder)
    obligation.refresh_from_db()

    assert obligation.workflow_state == NOTIFICATION_NOT_REQUIRED
    assert obligation.decision == NotificationDecision.NOT_REQUIRED
    assert obligation.decision_rationale


# --- An exercise owes nothing to anyone -------------------------------------


@pytest.mark.django_db
def test_an_exercise_generates_no_obligation_at_all(responder, plan):
    """Rule : filing a real notification for a drill is an incident in its own right.

    The exercise runs the identical lifecycle through the identical gates. The
    one thing it never does is put a real regulatory duty on the register.
    """
    incident = triaged_incident(responder, response_plan=plan, is_exercise=True)

    assert incident.notifications.count() == 0


@pytest.mark.django_db
def test_an_exercise_is_not_asked_to_justify_owing_nothing(responder):
    """Rule : the coverage gate is qualified on the exercise flag.

    An unqualified gate would demand a legal justification for owing nothing on
    every single drill, which trains the wrong reflex and pollutes the exact
    field an auditor reads.
    """
    incident = declared_incident(
        responder, incident_manager=responder, is_exercise=True
    )

    incident.transition_to(INCIDENT_TRIAGED, responder)

    assert incident.workflow_state == INCIDENT_TRIAGED
    assert incident.no_obligation_justification == ""


@pytest.mark.django_db
def test_a_real_incident_owing_nothing_must_say_why(responder):
    """Rule : a missing regime configuration must never read as compliance.

    Triage producing no obligation at all is either a correct legal conclusion
    or a forgotten configuration, and a green dashboard cannot tell them apart.
    The gate makes the operator state which it is.
    """
    incident = declared_incident(responder, incident_manager=responder)

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_TRIAGED, responder)

    incident.refresh_from_db()
    incident.no_obligation_justification = (
        "Purely internal outage, no personal data, no regulated service."
    )
    incident.save()
    incident.transition_to(INCIDENT_TRIAGED, responder)

    assert incident.workflow_state == INCIDENT_TRIAGED


@pytest.mark.django_db
def test_an_incident_that_generated_an_obligation_is_not_asked_to_justify_anything(
    responder, plan
):
    """The gate is about the *absence* of duties, never about their presence."""
    incident = declared_incident(
        responder, incident_manager=responder, response_plan=plan
    )

    incident.transition_to(INCIDENT_TRIAGED, responder)

    assert incident.workflow_state == INCIDENT_TRIAGED
    assert incident.no_obligation_justification == ""
    assert incident.notifications.count() == len(TWO_REGIMES)


# --- What the flags force, whatever the plan says ---------------------------


@pytest.mark.django_db
def test_personal_data_alone_instantiates_the_article_33_duty(responder):
    """Rule : RG-INC-18. A plan that forgot the regime must not read as *nothing owed*.

    The same flag opens the GDPR qualification, so the two records that a
    supervisory authority asks for are created by the same act.
    """
    incident = triaged_incident(
        responder, personal_data_involved=True, no_obligation_justification=""
    )

    assert incident.notifications.filter(
        regime=NotificationRegime.GDPR_ART33_AUTHORITY
    ).exists()
    assert PersonalDataBreach.objects.filter(incident=incident).exists()


@pytest.mark.django_db
def test_the_qualification_is_opened_through_its_own_lifecycle(responder):
    """A qualification created in ``draft`` would be deletable and invisible."""
    incident = triaged_incident(
        responder, personal_data_involved=True, no_obligation_justification=""
    )
    breach = PersonalDataBreach.objects.get(incident=incident)

    assert breach.workflow_state == "under_qualification"
    assert LifecycleEvent.objects.filter(
        object_id=str(breach.pk), to_step="under_qualification"
    ).exists()


# --- The catalogue ----------------------------------------------------------


@pytest.mark.django_db
def test_a_matching_template_is_snapshotted_onto_the_obligation(responder):
    """Rule : the legal terms are copied, never read through the foreign key.

    A template corrected in 2027 must not retroactively change what a 2025
    filing cited. The foreign key is kept alongside because it answers a
    different question : which rule produced this row.
    """
    template = in_force(
        ReportingObligationTemplateFactory(
            regime=NotificationRegime.DORA_INITIAL,
            recipient_kind=NotificationRecipientKind.FINANCIAL_REGULATOR,
            legal_reference="DORA Art. 19(1)",
            clock_hours=4,
        ),
        responder,
    )

    incident = triaged_incident(responder)
    obligation = incident.notifications.get(regime=NotificationRegime.DORA_INITIAL)

    assert obligation.template_id == template.pk
    assert obligation.deadline_hours == 4
    assert obligation.obligation_reference == "DORA Art. 19(1)"

    template.clock_hours = 24
    template.legal_reference = "DORA Art. 19(1), as corrected"
    template.save()
    obligation.refresh_from_db()

    assert obligation.deadline_hours == 4
    assert obligation.obligation_reference == "DORA Art. 19(1)"


@pytest.mark.django_db
def test_a_template_that_does_not_match_generates_nothing(responder):
    """Rule : a condition nobody has answered yet neither fires nor suppresses.

    ``requires_significant`` is compared against ``True`` and never with a
    truthiness test : *not yet determined* is not *no*.
    """
    in_force(
        ReportingObligationTemplateFactory(
            regime=NotificationRegime.NIS2_NOTIFICATION,
            requires_significant=True,
            clock_hours=72,
        ),
        responder,
    )

    undetermined = triaged_incident(responder)

    assert undetermined.notifications.count() == 0

    significant = triaged_incident(
        responder,
        is_significant=True,
        no_obligation_justification="",
    )

    assert significant.notifications.filter(
        regime=NotificationRegime.NIS2_NOTIFICATION
    ).exists()


@pytest.mark.django_db
def test_the_catalogue_wins_over_the_plans_flat_list_for_the_same_regime(responder):
    """Rule : one duty is one row, whichever source had an opinion about it.

    Generating from both would file two obligations for one duty, with two
    recipients and two clocks, and nobody watching the second.
    """
    in_force(
        ReportingObligationTemplateFactory(
            regime=NotificationRegime.GDPR_ART33_AUTHORITY,
            legal_reference="GDPR Art. 33(1), CNIL guidance",
            clock_hours=48,
        ),
        responder,
    )
    plan = IncidentResponsePlanFactory(
        applicable_regimes=[NotificationRegime.GDPR_ART33_AUTHORITY]
    )

    incident = triaged_incident(responder, response_plan=plan)
    obligations = incident.notifications.filter(
        regime=NotificationRegime.GDPR_ART33_AUTHORITY
    )

    assert obligations.count() == 1
    assert obligations.first().deadline_hours == 48


@pytest.mark.django_db
def test_a_staged_obligation_is_wired_to_the_filing_that_starts_its_clock(responder):
    """Rule : the NIS2 final report is due one month after the *notification*.

    Anchoring it on awareness would make every NIS2 final-report deadline in the
    register wrong, always in the direction that makes the organisation look
    later than it is.
    """
    plan = IncidentResponsePlanFactory(
        applicable_regimes=[
            NotificationRegime.NIS2_NOTIFICATION,
            NotificationRegime.NIS2_FINAL,
        ]
    )

    incident = triaged_incident(responder, response_plan=plan)
    final_report = incident.notifications.get(regime=NotificationRegime.NIS2_FINAL)
    notification = incident.notifications.get(
        regime=NotificationRegime.NIS2_NOTIFICATION
    )

    assert final_report.clock_anchor == ClockAnchor.PREVIOUS_STAGE
    assert final_report.depends_on_id == notification.pk
    assert final_report.due_at is None


# --- A severity raise can create a duty that did not exist an hour earlier ---


@pytest.mark.django_db
def test_raising_the_severity_after_triage_re_runs_generation(responder):
    """Rule : a raise can cross a template's floor and start a new statutory clock.

    Waiting for the next triage would mean a 24-hour clock nobody is watching.
    """
    in_force(
        ReportingObligationTemplateFactory(
            regime=NotificationRegime.NIS2_EARLY_WARNING,
            min_severity="critical",
            clock_hours=24,
        ),
        responder,
    )
    incident = triaged_incident(responder, severity="low")

    assert incident.notifications.count() == 0

    incident.severity = "critical"
    incident.save()

    assert incident.notifications.filter(
        regime=NotificationRegime.NIS2_EARLY_WARNING
    ).exists()


@pytest.mark.django_db
def test_lowering_the_severity_never_removes_an_obligation(responder, plan):
    """Rule : an obligation once believed to exist leaves a decision, never a gap.

    It is answered through ``not_required`` with a written rationale. Deleting
    it would destroy the evidence that the organisation considered the regime.
    """
    incident = triaged_incident(responder, response_plan=plan, severity="critical")
    before = incident.notifications.count()

    incident.severity = "low"
    incident.save()

    assert incident.notifications.count() == before


@pytest.mark.django_db
def test_a_generated_obligation_is_never_deleted(responder, plan):
    """Rule : deleting it destroys the evidence that the regime was considered."""
    from core.lifecycle import LifecycleProtectedError

    incident = triaged_incident(responder, response_plan=plan)
    obligation = incident.notifications.first()

    with pytest.raises(LifecycleProtectedError):
        obligation.delete()

    assert IncidentNotification.objects.filter(pk=obligation.pk).exists()

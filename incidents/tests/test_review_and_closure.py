# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An incident closes on a learning record, or it does not close.

ISO/IEC 27001:2022 A.5.27 asks that knowledge gained from incidents be used to
strengthen controls. That sentence is trivially satisfiable on paper and almost
never satisfied in practice, because the natural end of an incident is the
moment service is restored. The answer here is structural rather than
procedural : the review is created by the lifecycle when the incident reaches
its review phase, and the closure gate refuses while it is unapproved. There is
no surface on which a closed incident can exist without one.

The second half of this file is clause 10.2 : a review that raises a
nonconformity raises the *same kind* of nonconformity an audit does, in the same
register, and the ``effectiveness_verified`` step is the record that the
corrective action actually worked rather than merely having been implemented.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.tests.factories import UserFactory
from compliance.constants import EffectivenessVerdict, FindingSource
from compliance.tests.factories import ComplianceActionPlanFactory, FindingFactory
from core.lifecycle import DomainRefusalError, LifecycleProtectedError
from incidents.models import PostIncidentReview
from incidents.tests.factories import (
    IncidentResponsePlanFactory,
    PostIncidentReviewFactory,
)
from incidents.tests.helpers import (
    COMMENT,
    INCIDENT_CLOSED,
    INCIDENT_CONTAINED,
    INCIDENT_ERADICATED,
    INCIDENT_INVESTIGATING,
    INCIDENT_RECLASSIFIED,
    INCIDENT_RECOVERED,
    INCIDENT_REVIEW,
    NOTIFICATION_NOT_REQUIRED,
    REVIEW_APPROVED,
    REVIEW_ARCHIVED,
    REVIEW_CANCELLED,
    REVIEW_DRAFT,
    REVIEW_IN_PROGRESS,
    REVIEW_SCHEDULED,
    REVIEW_SUBMITTED,
    REVIEW_VERIFIED,
    approved_review,
    assessed_obligation,
    collected_evidence,
    declared_incident,
    incident_in_review_phase,
    sealed_evidence,
    triaged_incident,
    walk,
)


@pytest.fixture
def responder(db):
    return UserFactory()


def in_force_action_plan(user):
    """An action plan walked far enough to count in reports.

    RG-FND-06 : a verdict about the effectiveness of nothing is not a record, so
    the propagation skips a finding whose action plans are all still invisible.
    """
    plan = ComplianceActionPlanFactory()
    return walk(plan, "to_define", "to_validate", user=user)


# --- The review is opened by the lifecycle, exactly once --------------------


@pytest.mark.django_db
def test_reaching_the_review_phase_opens_the_review(responder):
    """Rule : the A.5.27 record is created by the platform, not by a reminder."""
    incident = incident_in_review_phase(responder)
    review = PostIncidentReview.objects.get(incident=incident)

    assert review.workflow_state == REVIEW_SCHEDULED


@pytest.mark.django_db
def test_an_incident_never_holds_more_than_one_review(responder):
    """Rule : exactly one review per incident (RG-INC-31).

    The relation is a ``OneToOne``, so a second one is not merely discouraged :
    re-entering the review phase must return the existing record untouched.
    """
    incident = incident_in_review_phase(responder)
    first = PostIncidentReview.objects.get(incident=incident)

    again = incident.ensure_post_incident_review(responder)

    assert again.pk == first.pk
    assert PostIncidentReview.objects.filter(incident=incident).count() == 1


# --- GP-01 : a review is not a status meeting -------------------------------


@pytest.mark.django_db
def test_a_review_cannot_be_held_while_the_incident_is_still_being_contained(
    responder,
):
    """Rule : holding the review before the response ends is a status meeting."""
    incident = triaged_incident(responder)
    review = PostIncidentReviewFactory(incident=incident)
    walk(review, REVIEW_SCHEDULED, user=responder)

    with pytest.raises(DomainRefusalError):
        review.transition_to(REVIEW_IN_PROGRESS, responder)

    walk(
        incident,
        INCIDENT_INVESTIGATING,
        INCIDENT_CONTAINED,
        INCIDENT_ERADICATED,
        INCIDENT_RECOVERED,
        INCIDENT_REVIEW,
        user=responder,
    )
    review.refresh_from_db()
    review.transition_to(REVIEW_IN_PROGRESS, responder)

    assert review.workflow_state == REVIEW_IN_PROGRESS
    assert review.held_at is not None


# --- GP-02 : a review with no determined cause is a chronology --------------


@pytest.mark.django_db
def test_submitting_a_review_requires_the_determined_root_cause(responder):
    """Rule : clause 10.2 b). The register already holds the chronology."""
    incident = incident_in_review_phase(responder)
    review = incident.post_incident_review
    review.similar_incidents_checked = True
    review.save()
    walk(review, REVIEW_IN_PROGRESS, user=responder)

    with pytest.raises(DomainRefusalError):
        review.transition_to(REVIEW_SUBMITTED, responder)

    review.root_cause = "An unpatched edge appliance reachable from the internet."
    review.save()
    review.transition_to(REVIEW_SUBMITTED, responder)

    assert review.workflow_state == REVIEW_SUBMITTED


@pytest.mark.django_db
def test_submitting_a_review_requires_the_similar_incident_check(responder):
    """Rule : clause 10.2 b) 3) is confirmed as performed, not assumed."""
    incident = incident_in_review_phase(responder)
    review = incident.post_incident_review
    review.root_cause = "An unpatched edge appliance."
    review.save()
    walk(review, REVIEW_IN_PROGRESS, user=responder)

    with pytest.raises(DomainRefusalError):
        review.transition_to(REVIEW_SUBMITTED, responder)


# --- GP-03 and GP-04 : the clause 10.2 d) and f) record ---------------------


@pytest.mark.django_db
def test_approving_a_review_requires_the_effectiveness_verification_date(responder):
    """Rule : approving with no verification date scheduled is how 10.2 d) is missed.

    The gate refuses it rather than trusting a reminder to catch it later.
    """
    incident = incident_in_review_phase(responder)
    review = incident.post_incident_review
    review.root_cause = "An unpatched edge appliance."
    review.similar_incidents_checked = True
    review.save()
    walk(review, REVIEW_IN_PROGRESS, REVIEW_SUBMITTED, user=responder)

    with pytest.raises(DomainRefusalError):
        review.transition_to(REVIEW_APPROVED, responder, comment=COMMENT)

    review.effectiveness_review_date = timezone.localdate() + timedelta(days=30)
    review.save()
    review.transition_to(REVIEW_APPROVED, responder, comment=COMMENT)

    assert review.workflow_state == REVIEW_APPROVED


@pytest.mark.django_db
def test_verifying_effectiveness_requires_a_verdict_and_an_author(responder):
    """Rule : clause 10.2 f) is a documented result with an author. Neither is optional.

    An action plan reaching a done step proves the action was implemented. It
    says nothing about whether it worked, and this step is that missing record.
    """
    incident = incident_in_review_phase(responder)
    review = approved_review(incident, responder)

    with pytest.raises(DomainRefusalError):
        review.transition_to(REVIEW_VERIFIED, responder, comment=COMMENT)

    review.effectiveness_verdict = EffectivenessVerdict.EFFECTIVE
    review.save()

    with pytest.raises(DomainRefusalError):
        review.transition_to(REVIEW_VERIFIED, responder, comment=COMMENT)

    review.effectiveness_reviewed_by = responder
    review.save()
    review.transition_to(REVIEW_VERIFIED, responder, comment=COMMENT)

    assert review.workflow_state == REVIEW_VERIFIED
    assert review.effectiveness_reviewed_at is not None


@pytest.mark.django_db
def test_a_rework_loop_keeps_the_date_the_review_was_actually_held(responder):
    """Rule : the two review clocks are write-once (RG-INC-12)."""
    incident = incident_in_review_phase(responder)
    review = incident.post_incident_review
    review.root_cause = "An unpatched edge appliance."
    review.similar_incidents_checked = True
    review.effectiveness_review_date = timezone.localdate() + timedelta(days=30)
    review.save()
    walk(review, REVIEW_IN_PROGRESS, REVIEW_SUBMITTED, user=responder)
    held_at = review.held_at

    review.transition_to(REVIEW_IN_PROGRESS, responder, comment="Root cause too thin.")

    assert review.held_at == held_at


# --- GP-05 and GP-06 : the review cannot be made to disappear ---------------


@pytest.mark.django_db
def test_an_opened_review_cannot_be_restored_to_draft(responder):
    """Rule : draft and scheduled are deletable, so restore is the one dangerous edge.

    Without the gate, archiving then restoring would destroy the A.5.27 record
    an incident was closed on.
    """
    incident = incident_in_review_phase(responder)
    review = approved_review(incident, responder)
    review.transition_to(REVIEW_ARCHIVED, responder, comment=COMMENT)

    with pytest.raises(DomainRefusalError):
        review.transition_to(REVIEW_DRAFT, responder)


@pytest.mark.django_db
def test_a_never_opened_review_can_be_restored(responder):
    """The counterpart : a review row created in error is still removable."""
    incident = triaged_incident(responder)
    review = PostIncidentReviewFactory(incident=incident)
    walk(review, REVIEW_ARCHIVED, REVIEW_DRAFT, user=responder)

    assert review.workflow_state == REVIEW_DRAFT


@pytest.mark.django_db
def test_a_review_is_only_cancellable_once_its_incident_is_itself_terminal(responder):
    """Rule : a live incident must have a live review to reach closure.

    Cancelling one on an open incident would strand it : the relation is a
    ``OneToOne``, so a cancelled review can never be replaced.
    """
    incident = declared_incident(responder)
    review = PostIncidentReviewFactory(incident=incident)
    walk(review, REVIEW_SCHEDULED, user=responder)

    with pytest.raises(DomainRefusalError):
        review.transition_to(REVIEW_CANCELLED, responder, comment=COMMENT)

    incident.transition_to(INCIDENT_RECLASSIFIED, responder, comment=COMMENT)
    review.transition_to(REVIEW_CANCELLED, responder, comment=COMMENT)

    assert review.workflow_state == REVIEW_CANCELLED


@pytest.mark.django_db
def test_a_review_cannot_be_deleted_while_its_incident_is_still_open(responder):
    """Rule : deleting it would leave an incident that can never close.

    The row is the answer to a question the platform asked on the organisation's
    behalf, and deleting it destroys the evidence the question was considered.
    """
    incident = triaged_incident(responder)
    review = PostIncidentReviewFactory(incident=incident)

    assert review.is_deletable is True
    with pytest.raises(LifecycleProtectedError):
        review.delete()

    assert PostIncidentReview.objects.filter(pk=review.pk).exists()


# --- The closure gate -------------------------------------------------------


@pytest.mark.django_db
def test_an_incident_cannot_close_without_an_approved_review(responder):
    """Rule : the whole point of the entity (RG-INC-14).

    An unapproved review is not a learning record : it is a draft of one.
    """
    incident = incident_in_review_phase(responder)
    review = incident.post_incident_review

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)

    review.root_cause = "An unpatched edge appliance."
    review.similar_incidents_checked = True
    review.effectiveness_review_date = timezone.localdate() + timedelta(days=30)
    review.save()
    walk(review, REVIEW_IN_PROGRESS, REVIEW_SUBMITTED, user=responder)

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)

    review.transition_to(REVIEW_APPROVED, responder, comment=COMMENT)
    incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)

    assert incident.workflow_state == INCIDENT_CLOSED
    assert incident.closed_at is not None


@pytest.mark.django_db
def test_an_incident_cannot_close_on_an_undecided_regulatory_obligation(responder):
    """Rule : closure requires a decision on every obligation, not a filing.

    *Not required, because …* closes an obligation perfectly well. *Nobody
    looked* does not, and the two must not be able to end the same way.
    """
    incident = incident_in_review_phase(responder)
    approved_review(incident, responder)
    obligation = assessed_obligation(incident, responder)

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)

    obligation.transition_to(
        NOTIFICATION_NOT_REQUIRED,
        responder,
        comment="No personal data was affected : Art. 33(1) does not apply.",
    )
    incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)

    assert incident.workflow_state == INCIDENT_CLOSED


@pytest.mark.django_db
def test_an_incident_cannot_close_on_evidence_left_merely_collected(responder):
    """Rule : an acquired artefact is secured or otherwise disposed of before closure.

    An item still sitting in ``collected`` has been taken off a live system and
    never sealed, which is the state in which its evidential value evaporates.
    """
    incident = incident_in_review_phase(responder)
    approved_review(incident, responder)
    evidence = collected_evidence(
        incident,
        responder,
        content_hash="d" * 64,
        collection_method="dd through a write blocker.",
    )

    with pytest.raises(DomainRefusalError):
        incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)

    evidence.transition_to("secured", responder)
    incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)

    assert incident.workflow_state == INCIDENT_CLOSED


@pytest.mark.django_db
def test_sealed_evidence_is_no_obstacle_to_closure(responder):
    """The gate is about unfinished handling, never about holding evidence."""
    incident = incident_in_review_phase(responder)
    approved_review(incident, responder)
    sealed_evidence(incident, responder)

    incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)

    assert incident.workflow_state == INCIDENT_CLOSED


@pytest.mark.django_db
def test_reopening_a_closed_incident_clears_only_the_closure_stamp(responder):
    """Rule : the original closure stays in the ledger; only the stamp is cleared.

    Re-closure re-stamps it, so the register always states when the incident is
    currently held to have closed, and the history states every earlier answer.
    """
    incident = incident_in_review_phase(responder)
    approved_review(incident, responder)
    incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)
    first_closure = incident.closed_at

    incident.transition_to(
        INCIDENT_INVESTIGATING, responder, comment="New forensic finding."
    )

    assert incident.closed_at is None

    walk(
        incident,
        INCIDENT_CONTAINED,
        INCIDENT_ERADICATED,
        INCIDENT_RECOVERED,
        INCIDENT_REVIEW,
        user=responder,
    )
    incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)

    assert incident.closed_at is not None
    assert incident.closed_at >= first_closure


@pytest.mark.django_db
def test_closing_an_exercise_is_what_maintains_the_plan_testing_evidence(responder):
    """Rule : RG-INC-17. A hand-typed plan-testing date is worthless as evidence.

    The A.5.24 obligation is to have a *tested* plan, and this transition is the
    only writer of the date that proves it.
    """
    plan = IncidentResponsePlanFactory()
    incident = incident_in_review_phase(
        responder, is_exercise=True, response_plan=plan
    )
    approved_review(incident, responder)

    incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)
    plan.refresh_from_db()

    assert plan.last_exercise_date == timezone.localtime(incident.closed_at).date()


@pytest.mark.django_db
def test_closing_a_real_incident_does_not_touch_the_plan_testing_evidence(responder):
    """A real incident is not a drill, whatever it taught anybody."""
    plan = IncidentResponsePlanFactory()
    incident = incident_in_review_phase(responder, response_plan=plan)
    approved_review(incident, responder)

    incident.transition_to(INCIDENT_CLOSED, responder, comment=COMMENT)
    plan.refresh_from_db()

    assert plan.last_exercise_date is None


# --- Clause 10.2 : the nonconformities a review raises ----------------------


@pytest.mark.django_db
def test_submitting_a_review_stamps_every_nonconformity_it_raised(responder):
    """Rule : RG-INC-34. An incident-born nonconformity says so, in one register.

    ``assessment`` stays null on purpose : fabricating an audit to hang an
    incident's nonconformity off is exactly the practice the generalisation of
    ``compliance.Finding`` exists to end.
    """
    incident = incident_in_review_phase(responder)
    review = incident.post_incident_review
    facilitator = UserFactory()
    finding = FindingFactory(assessment=None, assessor=None)
    review.raised_findings.add(finding)
    review.facilitator = facilitator
    review.root_cause = "An unpatched edge appliance."
    review.similar_incidents_checked = True
    review.effectiveness_review_date = timezone.localdate() + timedelta(days=30)
    review.save()

    walk(review, REVIEW_IN_PROGRESS, REVIEW_SUBMITTED, user=responder)
    finding.refresh_from_db()

    assert finding.source == FindingSource.INCIDENT
    assert finding.incident_id == incident.pk
    assert finding.assessor_id == facilitator.pk
    assert finding.assessment_id is None


@pytest.mark.django_db
def test_the_stamping_is_idempotent_and_never_overwrites_a_named_author(responder):
    """Rule : it runs on the submit and the approve edge, so a rework loop is covered.

    An explicitly named author is left alone : the review asserts the *origin* of
    the nonconformity, never who is credited with raising it.
    """
    incident = incident_in_review_phase(responder)
    review = incident.post_incident_review
    named_author = UserFactory()
    anonymous = FindingFactory(assessment=None, assessor=None)
    attributed = FindingFactory(assessment=None, assessor=named_author)
    review.raised_findings.add(anonymous, attributed)
    review.facilitator = responder
    review.save()

    approved_review(incident, responder, facilitator=responder)
    anonymous.refresh_from_db()
    attributed.refresh_from_db()

    assert anonymous.assessor_id == responder.pk
    assert attributed.assessor_id == named_author.pk
    assert anonymous.source == FindingSource.INCIDENT
    assert attributed.source == FindingSource.INCIDENT


@pytest.mark.django_db
def test_the_effectiveness_verdict_is_copied_onto_the_nonconformities(responder):
    """Rule : a snapshot at this instant, never a live mirror.

    A nonconformity whose individual verdict differs is edited on the finding
    itself afterwards, and the finding's own history records the divergence.
    """
    incident = incident_in_review_phase(responder)
    review = incident.post_incident_review
    finding = FindingFactory(assessment=None, assessor=None)
    finding.action_plans.add(in_force_action_plan(responder))
    review.raised_findings.add(finding)
    review.save()

    approved_review(incident, responder)
    review.effectiveness_verdict = EffectivenessVerdict.EFFECTIVE
    review.effectiveness_reviewed_by = responder
    review.save()
    review.transition_to(REVIEW_VERIFIED, responder, comment=COMMENT)
    finding.refresh_from_db()

    assert finding.effectiveness_verdict == EffectivenessVerdict.EFFECTIVE
    assert finding.effectiveness_reviewed_by_id == responder.pk
    assert finding.effectiveness_reviewed_at == review.effectiveness_reviewed_at


@pytest.mark.django_db
def test_a_nonconformity_with_no_visible_action_plan_is_skipped_not_stamped(responder):
    """Rule : RG-FND-06. A verdict about the effectiveness of nothing is not a record.

    The skipped rows are returned and kept on the instance, so the calling
    surface can tell the operator which ones it could not answer for.
    """
    incident = incident_in_review_phase(responder)
    review = incident.post_incident_review
    finding = FindingFactory(assessment=None, assessor=None)
    review.raised_findings.add(finding)
    review.save()

    approved_review(incident, responder)
    review.effectiveness_verdict = EffectivenessVerdict.EFFECTIVE
    review.effectiveness_reviewed_by = responder
    review.save()
    review.transition_to(REVIEW_VERIFIED, responder, comment=COMMENT)
    finding.refresh_from_db()

    assert finding.effectiveness_verdict == ""
    assert list(review.effectiveness_propagation_skipped) == [finding]

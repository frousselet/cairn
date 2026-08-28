# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Walkers shared by the module 6 behaviour tests.

Every helper here builds its row **through** ``transition_to()``. None of them
assigns ``workflow_state``, and that is the whole point : a fixture that writes
the step directly produces a record with no ``core.LifecycleEvent``, no stamped
clock and no generated child, so a test built on it proves the gate passes on a
row the governance never touched.

The step codes are imported from ``incidents/constants.py`` rather than spelled
as literals, for the same reason the models do it (RG-INC-37) : a rename there
must break these helpers at import time instead of quietly aiming them at a
step that no longer exists.
"""

import uuid
from datetime import timedelta

from django.utils import timezone

from incidents.constants import (
    BREACH_STATES,
    EVIDENCE_STATES,
    INCIDENT_STATES,
    NOTIFICATION_STATES,
    REVIEW_STATES,
    SECURITY_EVENT_STATES,
)
from incidents.tests.factories import (
    IncidentEvidenceFactory,
    IncidentFactory,
    IncidentNotificationFactory,
    PersonalDataBreachFactory,
    SecurityEventFactory,
)

#: Every transition that declares ``requires_comment`` refuses a blank one, and
#: several fold the text into the record itself. One constant, so a test that
#: cares about the stored text says so explicitly.
COMMENT = "Recorded by the module 6 behaviour tests."


def _step(code, states, lifecycle):
    """Resolve a step code by name against the single source of truth."""
    if code not in {declared for declared, *_flags in states}:
        raise AssertionError(f"'{code}' is not a step of the {lifecycle} lifecycle.")
    return code


# --- Step codes, resolved by name --------------------------------------------

INCIDENT_DRAFT = _step("draft", INCIDENT_STATES, "incident")
INCIDENT_DETECTED = _step("detected", INCIDENT_STATES, "incident")
INCIDENT_TRIAGED = _step("triaged", INCIDENT_STATES, "incident")
INCIDENT_INVESTIGATING = _step("investigating", INCIDENT_STATES, "incident")
INCIDENT_CONTAINED = _step("contained", INCIDENT_STATES, "incident")
INCIDENT_ERADICATED = _step("eradicated", INCIDENT_STATES, "incident")
INCIDENT_RECOVERED = _step("recovered", INCIDENT_STATES, "incident")
INCIDENT_REVIEW = _step("post_incident_review", INCIDENT_STATES, "incident")
INCIDENT_CLOSED = _step("closed", INCIDENT_STATES, "incident")
INCIDENT_RECLASSIFIED = _step("reclassified", INCIDENT_STATES, "incident")
INCIDENT_ARCHIVED = _step("archived", INCIDENT_STATES, "incident")

EVENT_DRAFT = _step("draft", SECURITY_EVENT_STATES, "security_event")
EVENT_REPORTED = _step("reported", SECURITY_EVENT_STATES, "security_event")
EVENT_UNDER_ASSESSMENT = _step(
    "under_assessment", SECURITY_EVENT_STATES, "security_event"
)
EVENT_CONFIRMED_INCIDENT = _step(
    "confirmed_incident", SECURITY_EVENT_STATES, "security_event"
)
EVENT_CONFIRMED_WEAKNESS = _step(
    "confirmed_weakness", SECURITY_EVENT_STATES, "security_event"
)
EVENT_DISCARDED = _step("discarded", SECURITY_EVENT_STATES, "security_event")
EVENT_ARCHIVED = _step("archived", SECURITY_EVENT_STATES, "security_event")

EVIDENCE_DRAFT = _step("draft", EVIDENCE_STATES, "incident_evidence")
EVIDENCE_COLLECTED = _step("collected", EVIDENCE_STATES, "incident_evidence")
EVIDENCE_SECURED = _step("secured", EVIDENCE_STATES, "incident_evidence")
EVIDENCE_ANALYSED = _step("analysed", EVIDENCE_STATES, "incident_evidence")
EVIDENCE_RETAINED = _step("retained", EVIDENCE_STATES, "incident_evidence")
EVIDENCE_RELEASED = _step("released", EVIDENCE_STATES, "incident_evidence")
EVIDENCE_DESTROYED = _step("destroyed", EVIDENCE_STATES, "incident_evidence")
EVIDENCE_ARCHIVED = _step("archived", EVIDENCE_STATES, "incident_evidence")

NOTIFICATION_DRAFT = _step("draft", NOTIFICATION_STATES, "incident_notification")
NOTIFICATION_ASSESSED = _step("assessed", NOTIFICATION_STATES, "incident_notification")
NOTIFICATION_REQUIRED = _step("required", NOTIFICATION_STATES, "incident_notification")
NOTIFICATION_DRAFTED = _step("drafted", NOTIFICATION_STATES, "incident_notification")
NOTIFICATION_SENT = _step("sent", NOTIFICATION_STATES, "incident_notification")
NOTIFICATION_ACKNOWLEDGED = _step(
    "acknowledged", NOTIFICATION_STATES, "incident_notification"
)
NOTIFICATION_NOT_REQUIRED = _step(
    "not_required", NOTIFICATION_STATES, "incident_notification"
)
NOTIFICATION_ARCHIVED = _step("archived", NOTIFICATION_STATES, "incident_notification")

REVIEW_DRAFT = _step("draft", REVIEW_STATES, "post_incident_review")
REVIEW_SCHEDULED = _step("scheduled", REVIEW_STATES, "post_incident_review")
REVIEW_IN_PROGRESS = _step("in_progress", REVIEW_STATES, "post_incident_review")
REVIEW_SUBMITTED = _step("submitted", REVIEW_STATES, "post_incident_review")
REVIEW_APPROVED = _step("approved", REVIEW_STATES, "post_incident_review")
REVIEW_VERIFIED = _step(
    "effectiveness_verified", REVIEW_STATES, "post_incident_review"
)
REVIEW_CANCELLED = _step("cancelled", REVIEW_STATES, "post_incident_review")
REVIEW_ARCHIVED = _step("archived", REVIEW_STATES, "post_incident_review")

BREACH_DRAFT = _step("draft", BREACH_STATES, "personal_data_breach")
BREACH_UNDER_QUALIFICATION = _step(
    "under_qualification", BREACH_STATES, "personal_data_breach"
)
BREACH_CONFIRMED = _step("confirmed", BREACH_STATES, "personal_data_breach")
BREACH_DOCUMENTED = _step("documented", BREACH_STATES, "personal_data_breach")
BREACH_NOT_A_BREACH = _step("not_a_breach", BREACH_STATES, "personal_data_breach")
BREACH_ARCHIVED = _step("archived", BREACH_STATES, "personal_data_breach")

#: The operational spine between triage and the review phase.
INCIDENT_RESPONSE_PATH = (
    INCIDENT_INVESTIGATING,
    INCIDENT_CONTAINED,
    INCIDENT_ERADICATED,
    INCIDENT_RECOVERED,
    INCIDENT_REVIEW,
)


# --- Walkers -----------------------------------------------------------------


def walk(obj, *targets, user=None, comment=COMMENT, **kwargs):
    """Move ``obj`` through each target in turn, through the lifecycle."""
    for target in targets:
        obj.transition_to(target, user, comment=comment, **kwargs)
    return obj


def declared_incident(user, **fields):
    """An incident on the register : saved in draft, then declared."""
    incident = IncidentFactory(**fields)
    return walk(incident, INCIDENT_DETECTED, user=user)


def triaged_incident(user, **fields):
    """A declared incident whose A.5.25 triage has completed.

    The two defaults are what the triage gates ask for : a named accountable
    responder (G-02) and, for an incident that owes nothing to anyone, the
    written reason why (G-03). A caller testing either gate supplies its own.
    """
    fields.setdefault("incident_manager", user)
    fields.setdefault(
        "no_obligation_justification",
        "No regulatory regime applies to this test perimeter.",
    )
    incident = declared_incident(user, **fields)
    return walk(incident, INCIDENT_TRIAGED, user=user)


def incident_in_review_phase(user, **fields):
    """A triaged incident walked down the response spine to its review phase.

    Reaching ``post_incident_review`` is what creates the A.5.27 review, so
    this is also the only honest way to obtain one.
    """
    incident = triaged_incident(user, **fields)
    return walk(incident, *INCIDENT_RESPONSE_PATH, user=user)


def approved_review(incident, user, **fields):
    """The incident's own review, filled in and walked to ``approved``.

    Each field answers a gate : the root cause and the similar-incident check
    are GP-02, the verification date is GP-03.
    """
    review = incident.post_incident_review
    review.facilitator = fields.pop("facilitator", user)
    review.root_cause = fields.pop(
        "root_cause", "An unpatched edge appliance reachable from the internet."
    )
    review.similar_incidents_checked = fields.pop("similar_incidents_checked", True)
    review.effectiveness_review_date = fields.pop(
        "effectiveness_review_date", timezone.localdate() + timedelta(days=30)
    )
    for name, value in fields.items():
        setattr(review, name, value)
    review.save()
    return walk(review, REVIEW_IN_PROGRESS, REVIEW_SUBMITTED, REVIEW_APPROVED, user=user)


def closed_incident(user, **fields):
    """An incident closed the only way it can be : on an approved review."""
    incident = incident_in_review_phase(user, **fields)
    approved_review(incident, user)
    return walk(incident, INCIDENT_CLOSED, user=user)


def reported_event(user, **fields):
    """A security event on the A.6.8 register."""
    event = SecurityEventFactory(**fields)
    return walk(event, EVENT_REPORTED, user=user)


def assessed_event(user, **fields):
    """A reported event whose A.5.25 assessment is under way and documented."""
    fields.setdefault(
        "assessment_notes",
        "Correlated with the SIEM alert; the source address is a known scanner.",
    )
    event = reported_event(user, **fields)
    return walk(event, EVENT_UNDER_ASSESSMENT, user=user)


def collected_evidence(incident, user, **fields):
    """An evidence item whose acquisition is registered (GE-01 satisfied)."""
    fields.setdefault("collected_by", user)
    fields.setdefault("source_description", "WEB-PRD-02, production web front end")
    evidence = IncidentEvidenceFactory(incident=incident, **fields)
    return walk(evidence, EVIDENCE_COLLECTED, user=user)


def sealed_evidence(incident, user, **fields):
    """A collected evidence item sealed under GE-02 : hash and method both stated."""
    fields.setdefault("content_hash", uuid.uuid4().hex * 2)
    fields.setdefault(
        "collection_method",
        "dd 8.32 through a Tableau T35u write blocker, source powered down.",
    )
    evidence = collected_evidence(incident, user, **fields)
    return walk(evidence, EVIDENCE_SECURED, user=user)


def retained_evidence(incident, user, **fields):
    """A sealed item moved into its retention period."""
    evidence = sealed_evidence(incident, user, **fields)
    return walk(evidence, EVIDENCE_RETAINED, user=user)


def assessed_obligation(incident, user, **fields):
    """An obligation on the register, awaiting its decision."""
    obligation = IncidentNotificationFactory(incident=incident, **fields)
    return walk(obligation, NOTIFICATION_ASSESSED, user=user)


def drafted_obligation(incident, user, **fields):
    """An obligation decided to be required and drafted, ready to be filed."""
    obligation = assessed_obligation(incident, user, **fields)
    return walk(obligation, NOTIFICATION_REQUIRED, NOTIFICATION_DRAFTED, user=user)


def opened_qualification(incident, user, **fields):
    """A GDPR qualification record with its qualification open."""
    breach = PersonalDataBreachFactory(incident=incident, **fields)
    return walk(breach, BREACH_UNDER_QUALIFICATION, user=user)


def article_33_3_content():
    """The Art. 33(3)(a) to (d) minimum content, as the breach gate asks for it."""
    return {
        "nature": "Unauthorised access to a customer database export.",
        "dpo_contact": "dpo@example.org, +33 1 23 45 67 89",
        "likely_consequences": "Identity theft and targeted phishing of the data subjects.",
        "measures_taken": "Credentials rotated, export revoked, monitoring raised.",
    }

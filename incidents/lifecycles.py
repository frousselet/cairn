# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Standardised lifecycles for module 6 (incidents).

Six lifecycles, all generated from the transition constants in
``incidents/constants.py`` so those stay the single source of truth (RG-INC-37).

Every one of them declares its ``draft`` and ``archived`` steps **explicitly**.
That is not cosmetic. ``lifecycle_from_state_flags`` only auto-wires the
bookends when the corresponding step is absent, and the edges it generates
carry **no** ``permission_action`` and **no** ``requires_comment``, while
``user_can_perform`` allows any transition whose ``permission_action`` is
empty. Left generated, every lifecycle here would expose an
``archive -> restore -> delete`` path out of its deletable draft step, which on
``IncidentEvidence`` means a sealed A.5.28 artefact could be destroyed by
anyone holding ``incidents.evidence.update``. Declaring both steps forces the
hand-written, gated edges at the end of each transition list.

Imported from ``IncidentsConfig.ready()``. Omitting that import fails
**silently** : ``lifecycle_name_for`` falls back to the default 4-state
lifecycle with no error, in tests as well as in production, so
``incidents/tests/test_lifecycles.py`` asserts each model resolves the
lifecycle it declares.
"""

from core.lifecycle import lifecycle_from_state_flags, register_lifecycle
from incidents.constants import (
    BREACH_STATES,
    BREACH_TRANSITIONS,
    EVIDENCE_STATES,
    EVIDENCE_TRANSITIONS,
    INCIDENT_STATES,
    INCIDENT_TRANSITIONS,
    NOTIFICATION_STATES,
    NOTIFICATION_TRANSITIONS,
    REVIEW_STATES,
    REVIEW_TRANSITIONS,
    SECURITY_EVENT_STATES,
    SECURITY_EVENT_TRANSITIONS,
)

INCIDENT_LIFECYCLE_NAME = "incident"
SECURITY_EVENT_LIFECYCLE_NAME = "security_event"
EVIDENCE_LIFECYCLE_NAME = "incident_evidence"
NOTIFICATION_LIFECYCLE_NAME = "incident_notification"
REVIEW_LIFECYCLE_NAME = "post_incident_review"
BREACH_LIFECYCLE_NAME = "personal_data_breach"


def _register(name, states, transitions):
    return register_lifecycle(
        lifecycle_from_state_flags(name, states, transitions, layout="graph")
    )


INCIDENT_LIFECYCLE = _register(
    INCIDENT_LIFECYCLE_NAME, INCIDENT_STATES, INCIDENT_TRANSITIONS
)
SECURITY_EVENT_LIFECYCLE = _register(
    SECURITY_EVENT_LIFECYCLE_NAME, SECURITY_EVENT_STATES, SECURITY_EVENT_TRANSITIONS
)
EVIDENCE_LIFECYCLE = _register(
    EVIDENCE_LIFECYCLE_NAME, EVIDENCE_STATES, EVIDENCE_TRANSITIONS
)
NOTIFICATION_LIFECYCLE = _register(
    NOTIFICATION_LIFECYCLE_NAME, NOTIFICATION_STATES, NOTIFICATION_TRANSITIONS
)
REVIEW_LIFECYCLE = _register(
    REVIEW_LIFECYCLE_NAME, REVIEW_STATES, REVIEW_TRANSITIONS
)
BREACH_LIFECYCLE = _register(
    BREACH_LIFECYCLE_NAME, BREACH_STATES, BREACH_TRANSITIONS
)

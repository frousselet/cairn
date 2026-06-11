"""Specific lifecycle workflows for the risks module.

These statuses had no transition constants (freely editable), so the graphs
encode the natural ISO 27005 progressions; legacy free status writes (and the
automated overdue / expiry flips) keep working through the
status <-> workflow_state sync during the migration period.

Governance highlights: a freshly *identified* risk is a working entry and does
not reach the risk register yet (the spec's draft analog); a *closed* risk
stays in the register as history but cannot gain new links; a *cancelled*
treatment plan leaves reports while every acceptance state remains reportable
(a revoked acceptance is audit-relevant governance history).

Imported from ``RisksConfig.ready()`` so registration happens at startup.
"""

from core.workflow import (
    WORKFLOW_REGISTRY,
    State,
    Transition,
    Workflow,
    register_workflow,
)
from risks.constants import (
    AcceptanceStatus,
    RiskStatus,
    TreatmentPlanStatus,
    VulnerabilityStatus,
)

RISK_WORKFLOW_NAME = "risk"
TREATMENT_PLAN_WORKFLOW_NAME = "risk_treatment_plan"
ACCEPTANCE_WORKFLOW_NAME = "risk_acceptance"
VULNERABILITY_WORKFLOW_NAME = "vulnerability"

# code -> (counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
_RISK_STATE_FLAGS = {
    RiskStatus.IDENTIFIED: (False, False, True, True, False, "secondary"),
    RiskStatus.ANALYZED: (True, True, False, False, False, "info"),
    RiskStatus.EVALUATED: (True, True, False, False, False, "primary"),
    RiskStatus.TREATMENT_PLANNED: (True, True, False, False, False, "primary"),
    RiskStatus.TREATMENT_IN_PROGRESS: (True, True, False, False, False, "warning"),
    RiskStatus.TREATED: (True, True, False, False, False, "success"),
    RiskStatus.ACCEPTED: (True, True, False, False, False, "success"),
    RiskStatus.MONITORING: (True, True, False, False, False, "info"),
    RiskStatus.CLOSED: (True, False, False, False, True, "dark"),
}

_RISK_TRANSITIONS = [
    (RiskStatus.IDENTIFIED, RiskStatus.ANALYZED),
    (RiskStatus.ANALYZED, RiskStatus.EVALUATED),
    (RiskStatus.EVALUATED, RiskStatus.TREATMENT_PLANNED),
    (RiskStatus.EVALUATED, RiskStatus.ACCEPTED),
    (RiskStatus.TREATMENT_PLANNED, RiskStatus.TREATMENT_IN_PROGRESS),
    (RiskStatus.TREATMENT_IN_PROGRESS, RiskStatus.TREATED),
    (RiskStatus.TREATED, RiskStatus.ACCEPTED),
    (RiskStatus.TREATED, RiskStatus.MONITORING),
    (RiskStatus.TREATED, RiskStatus.CLOSED),
    (RiskStatus.ACCEPTED, RiskStatus.MONITORING),
    (RiskStatus.ACCEPTED, RiskStatus.CLOSED),
    # The monitoring loop can re-enter the analysis cycle (periodic review).
    (RiskStatus.MONITORING, RiskStatus.ANALYZED),
    (RiskStatus.MONITORING, RiskStatus.CLOSED),
]

_TREATMENT_PLAN_STATE_FLAGS = {
    TreatmentPlanStatus.PLANNED: (True, True, True, True, False, "info"),
    TreatmentPlanStatus.IN_PROGRESS: (True, True, False, False, False, "primary"),
    TreatmentPlanStatus.OVERDUE: (True, True, False, False, False, "danger"),
    TreatmentPlanStatus.COMPLETED: (True, False, False, False, True, "success"),
    TreatmentPlanStatus.CANCELLED: (False, False, False, False, True, "danger"),
}

_TREATMENT_PLAN_TRANSITIONS = [
    (TreatmentPlanStatus.PLANNED, TreatmentPlanStatus.IN_PROGRESS),
    (TreatmentPlanStatus.IN_PROGRESS, TreatmentPlanStatus.COMPLETED),
    # Overdue is normally flipped automatically when the target date passes,
    # but the moves stay legal as manual transitions too.
    (TreatmentPlanStatus.PLANNED, TreatmentPlanStatus.OVERDUE),
    (TreatmentPlanStatus.IN_PROGRESS, TreatmentPlanStatus.OVERDUE),
    (TreatmentPlanStatus.OVERDUE, TreatmentPlanStatus.IN_PROGRESS),
    (TreatmentPlanStatus.OVERDUE, TreatmentPlanStatus.COMPLETED),
    (TreatmentPlanStatus.PLANNED, TreatmentPlanStatus.CANCELLED),
    (TreatmentPlanStatus.IN_PROGRESS, TreatmentPlanStatus.CANCELLED),
    (TreatmentPlanStatus.OVERDUE, TreatmentPlanStatus.CANCELLED),
]

_ACCEPTANCE_STATE_FLAGS = {
    AcceptanceStatus.ACTIVE: (True, False, True, True, False, "success"),
    AcceptanceStatus.RENEWED: (True, False, False, False, False, "info"),
    AcceptanceStatus.EXPIRED: (True, False, False, False, False, "warning"),
    AcceptanceStatus.REVOKED: (True, False, False, False, True, "danger"),
}

_ACCEPTANCE_TRANSITIONS = [
    (AcceptanceStatus.ACTIVE, AcceptanceStatus.EXPIRED),
    (AcceptanceStatus.ACTIVE, AcceptanceStatus.RENEWED),
    (AcceptanceStatus.ACTIVE, AcceptanceStatus.REVOKED),
    (AcceptanceStatus.RENEWED, AcceptanceStatus.EXPIRED),
    (AcceptanceStatus.RENEWED, AcceptanceStatus.REVOKED),
    (AcceptanceStatus.EXPIRED, AcceptanceStatus.RENEWED),
    (AcceptanceStatus.EXPIRED, AcceptanceStatus.REVOKED),
]

_VULNERABILITY_STATE_FLAGS = {
    VulnerabilityStatus.IDENTIFIED: (True, True, True, True, False, "secondary"),
    VulnerabilityStatus.CONFIRMED: (True, True, False, False, False, "warning"),
    VulnerabilityStatus.MITIGATED: (True, True, False, False, False, "success"),
    VulnerabilityStatus.ACCEPTED: (True, True, False, False, False, "info"),
    VulnerabilityStatus.CLOSED: (True, False, False, False, True, "dark"),
}

_VULNERABILITY_TRANSITIONS = [
    (VulnerabilityStatus.IDENTIFIED, VulnerabilityStatus.CONFIRMED),
    # A false positive can be closed directly.
    (VulnerabilityStatus.IDENTIFIED, VulnerabilityStatus.CLOSED),
    (VulnerabilityStatus.CONFIRMED, VulnerabilityStatus.MITIGATED),
    (VulnerabilityStatus.CONFIRMED, VulnerabilityStatus.ACCEPTED),
    (VulnerabilityStatus.MITIGATED, VulnerabilityStatus.CLOSED),
    (VulnerabilityStatus.ACCEPTED, VulnerabilityStatus.CLOSED),
]


def _build(name, status_enum, flags, transition_pairs):
    states = []
    for status in status_enum:
        counts, linkable, deletable, initial, terminal, tone = flags[status]
        states.append(
            State(
                str(status.value),
                status.label,
                counts_in_reports=counts,
                linkable=linkable,
                deletable=deletable,
                is_initial=initial,
                is_terminal=terminal,
                tone=tone,
            )
        )
    transitions = [
        Transition(
            str(source.value),
            str(target.value),
            status_enum(target).label,
            action="update",
        )
        for source, target in transition_pairs
    ]
    return Workflow(name, states, transitions)


_DEFINITIONS = [
    (RISK_WORKFLOW_NAME, RiskStatus, _RISK_STATE_FLAGS, _RISK_TRANSITIONS),
    (
        TREATMENT_PLAN_WORKFLOW_NAME,
        TreatmentPlanStatus,
        _TREATMENT_PLAN_STATE_FLAGS,
        _TREATMENT_PLAN_TRANSITIONS,
    ),
    (
        ACCEPTANCE_WORKFLOW_NAME,
        AcceptanceStatus,
        _ACCEPTANCE_STATE_FLAGS,
        _ACCEPTANCE_TRANSITIONS,
    ),
    (
        VULNERABILITY_WORKFLOW_NAME,
        VulnerabilityStatus,
        _VULNERABILITY_STATE_FLAGS,
        _VULNERABILITY_TRANSITIONS,
    ),
]

for _name, _enum, _flags, _pairs in _DEFINITIONS:
    if _name not in WORKFLOW_REGISTRY:
        register_workflow(_build(_name, _enum, _flags, _pairs))

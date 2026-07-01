"""Standardised lifecycles for the risks module (rebuilt engine).

Ports every legacy risks ``core.workflow`` machine (risk, risk assessment,
treatment plan, acceptance, vulnerability and the six EBIOS RM deliverables) to
the standardised :mod:`core.lifecycle` engine. Step codes, labels and
governance flags are identical to the legacy machines, so no ``workflow_state``
data migration is needed; the EBIOS workshop rejection keeps its mandatory
comment.

The legacy per-transition Django-permission ``action`` (approve / validate) is
not carried over: the lifecycle engine gates transitions by role (and the
API / MCP layers keep their own permission checks), matching the other migrated
entities.

Imported from ``RisksConfig.ready()`` so registration happens at startup.
"""

from core.lifecycle import lifecycle_from_state_flags, register_lifecycle
from risks.constants import (
    AcceptanceStatus,
    AssessmentStatus,
    BaselineGapStatus,
    EbiosBaselineStatus,
    EbiosStudyFrameworkStatus,
    EbiosSummaryStatus,
    EbiosWorkshopStatus,
    PACSMeasureStatus,
    RiskStatus,
    TreatmentPlanStatus,
    VulnerabilityStatus,
)

# ── Risk ────────────────────────────────────────────────────
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
    (RiskStatus.MONITORING, RiskStatus.ANALYZED),
    (RiskStatus.MONITORING, RiskStatus.CLOSED),
]

# ── Risk treatment plan ─────────────────────────────────────
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
    (TreatmentPlanStatus.PLANNED, TreatmentPlanStatus.OVERDUE),
    (TreatmentPlanStatus.IN_PROGRESS, TreatmentPlanStatus.OVERDUE),
    (TreatmentPlanStatus.OVERDUE, TreatmentPlanStatus.IN_PROGRESS),
    (TreatmentPlanStatus.OVERDUE, TreatmentPlanStatus.COMPLETED),
    (TreatmentPlanStatus.PLANNED, TreatmentPlanStatus.CANCELLED),
    (TreatmentPlanStatus.IN_PROGRESS, TreatmentPlanStatus.CANCELLED),
    (TreatmentPlanStatus.OVERDUE, TreatmentPlanStatus.CANCELLED),
]

# ── Risk acceptance ─────────────────────────────────────────
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

# ── Vulnerability ───────────────────────────────────────────
_VULNERABILITY_STATE_FLAGS = {
    VulnerabilityStatus.IDENTIFIED: (True, True, True, True, False, "secondary"),
    VulnerabilityStatus.CONFIRMED: (True, True, False, False, False, "warning"),
    VulnerabilityStatus.MITIGATED: (True, True, False, False, False, "success"),
    VulnerabilityStatus.ACCEPTED: (True, True, False, False, False, "info"),
    VulnerabilityStatus.CLOSED: (True, False, False, False, True, "dark"),
}

_VULNERABILITY_TRANSITIONS = [
    (VulnerabilityStatus.IDENTIFIED, VulnerabilityStatus.CONFIRMED),
    (VulnerabilityStatus.IDENTIFIED, VulnerabilityStatus.CLOSED),
    (VulnerabilityStatus.CONFIRMED, VulnerabilityStatus.MITIGATED),
    (VulnerabilityStatus.CONFIRMED, VulnerabilityStatus.ACCEPTED),
    (VulnerabilityStatus.MITIGATED, VulnerabilityStatus.CLOSED),
    (VulnerabilityStatus.ACCEPTED, VulnerabilityStatus.CLOSED),
]

# ── Risk assessment campaign ────────────────────────────────
_RISK_ASSESSMENT_STATE_FLAGS = {
    AssessmentStatus.DRAFT: (False, False, True, True, False, "secondary"),
    AssessmentStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    AssessmentStatus.COMPLETED: (True, False, False, False, False, "info"),
    AssessmentStatus.VALIDATED: (True, False, False, False, False, "success"),
    AssessmentStatus.ARCHIVED: (False, False, False, False, True, "dark"),
}

_RISK_ASSESSMENT_TRANSITIONS = [
    (AssessmentStatus.DRAFT, AssessmentStatus.IN_PROGRESS),
    (AssessmentStatus.IN_PROGRESS, AssessmentStatus.COMPLETED),
    (AssessmentStatus.COMPLETED, AssessmentStatus.IN_PROGRESS),
    (AssessmentStatus.COMPLETED, AssessmentStatus.VALIDATED),
    (AssessmentStatus.VALIDATED, AssessmentStatus.ARCHIVED),
]

# ── EBIOS RM deliverables ───────────────────────────────────
_EBIOS_WORKSHOP_STATE_FLAGS = {
    EbiosWorkshopStatus.NOT_STARTED: (True, False, True, True, False, "secondary"),
    EbiosWorkshopStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    EbiosWorkshopStatus.UNDER_REVIEW: (True, False, False, False, False, "warning"),
    EbiosWorkshopStatus.VALIDATED: (True, False, False, False, True, "success"),
    EbiosWorkshopStatus.REJECTED: (True, False, False, False, False, "danger"),
}

_EBIOS_WORKSHOP_TRANSITIONS = [
    (EbiosWorkshopStatus.NOT_STARTED, EbiosWorkshopStatus.IN_PROGRESS),
    (EbiosWorkshopStatus.IN_PROGRESS, EbiosWorkshopStatus.UNDER_REVIEW),
    (EbiosWorkshopStatus.UNDER_REVIEW, EbiosWorkshopStatus.VALIDATED),
    (EbiosWorkshopStatus.UNDER_REVIEW, EbiosWorkshopStatus.REJECTED, {"requires_comment": True}),
    (EbiosWorkshopStatus.REJECTED, EbiosWorkshopStatus.IN_PROGRESS),
]

_EBIOS_STUDY_FRAMEWORK_STATE_FLAGS = {
    EbiosStudyFrameworkStatus.DRAFT: (True, False, True, True, False, "secondary"),
    EbiosStudyFrameworkStatus.VALIDATED: (True, False, False, False, True, "success"),
}

_EBIOS_STUDY_FRAMEWORK_TRANSITIONS = [
    (EbiosStudyFrameworkStatus.DRAFT, EbiosStudyFrameworkStatus.VALIDATED),
]

_EBIOS_SECURITY_BASELINE_STATE_FLAGS = {
    EbiosBaselineStatus.DRAFT: (True, False, True, True, False, "secondary"),
    EbiosBaselineStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    EbiosBaselineStatus.COMPLETED: (True, False, False, False, True, "success"),
}

_EBIOS_SECURITY_BASELINE_TRANSITIONS = [
    (EbiosBaselineStatus.DRAFT, EbiosBaselineStatus.IN_PROGRESS),
    (EbiosBaselineStatus.IN_PROGRESS, EbiosBaselineStatus.COMPLETED),
]

_EBIOS_SUMMARY_STATE_FLAGS = {
    EbiosSummaryStatus.DRAFT: (True, False, True, True, False, "secondary"),
    EbiosSummaryStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    EbiosSummaryStatus.UNDER_REVIEW: (True, False, False, False, False, "warning"),
    EbiosSummaryStatus.VALIDATED: (True, False, False, False, True, "success"),
}

_EBIOS_SUMMARY_TRANSITIONS = [
    (EbiosSummaryStatus.DRAFT, EbiosSummaryStatus.IN_PROGRESS),
    (EbiosSummaryStatus.IN_PROGRESS, EbiosSummaryStatus.UNDER_REVIEW),
    (EbiosSummaryStatus.UNDER_REVIEW, EbiosSummaryStatus.VALIDATED),
    (EbiosSummaryStatus.UNDER_REVIEW, EbiosSummaryStatus.IN_PROGRESS),
]

_EBIOS_BASELINE_GAP_STATE_FLAGS = {
    BaselineGapStatus.IDENTIFIED: (True, False, True, True, False, "secondary"),
    BaselineGapStatus.ACCEPTED: (True, False, False, False, False, "info"),
    BaselineGapStatus.IN_REMEDIATION: (True, False, False, False, False, "warning"),
    BaselineGapStatus.REMEDIATED: (True, False, False, False, True, "success"),
}

_EBIOS_BASELINE_GAP_TRANSITIONS = [
    (BaselineGapStatus.IDENTIFIED, BaselineGapStatus.ACCEPTED),
    (BaselineGapStatus.IDENTIFIED, BaselineGapStatus.IN_REMEDIATION),
    (BaselineGapStatus.ACCEPTED, BaselineGapStatus.IN_REMEDIATION),
    (BaselineGapStatus.IN_REMEDIATION, BaselineGapStatus.REMEDIATED),
]

_EBIOS_PACS_MEASURE_STATE_FLAGS = {
    PACSMeasureStatus.PLANNED: (True, False, True, True, False, "info"),
    PACSMeasureStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    PACSMeasureStatus.OVERDUE: (True, False, False, False, False, "danger"),
    PACSMeasureStatus.COMPLETED: (True, False, False, False, True, "success"),
    PACSMeasureStatus.CANCELLED: (False, False, False, False, True, "danger"),
}

_EBIOS_PACS_MEASURE_TRANSITIONS = [
    (PACSMeasureStatus.PLANNED, PACSMeasureStatus.IN_PROGRESS),
    (PACSMeasureStatus.IN_PROGRESS, PACSMeasureStatus.COMPLETED),
    (PACSMeasureStatus.PLANNED, PACSMeasureStatus.OVERDUE),
    (PACSMeasureStatus.IN_PROGRESS, PACSMeasureStatus.OVERDUE),
    (PACSMeasureStatus.OVERDUE, PACSMeasureStatus.IN_PROGRESS),
    (PACSMeasureStatus.OVERDUE, PACSMeasureStatus.COMPLETED),
    (PACSMeasureStatus.PLANNED, PACSMeasureStatus.CANCELLED),
    (PACSMeasureStatus.IN_PROGRESS, PACSMeasureStatus.CANCELLED),
    (PACSMeasureStatus.OVERDUE, PACSMeasureStatus.CANCELLED),
]


def _build(name, status_enum, flags, transition_pairs):
    """Build a lifecycle from per-state flags and (source, target[, options]) pairs."""
    steps = [
        (status.value, status.label, *flags[status])
        for status in status_enum
    ]
    transitions = []
    for pair in transition_pairs:
        source, target = pair[0], pair[1]
        options = pair[2] if len(pair) > 2 else {}
        transitions.append(
            (source.value, target.value, status_enum(target).label, options.get("requires_comment", False))
        )
    return lifecycle_from_state_flags(name, steps, transitions, layout="graph")


_DEFINITIONS = [
    ("risk", RiskStatus, _RISK_STATE_FLAGS, _RISK_TRANSITIONS),
    ("risk_assessment", AssessmentStatus, _RISK_ASSESSMENT_STATE_FLAGS, _RISK_ASSESSMENT_TRANSITIONS),
    ("risk_treatment_plan", TreatmentPlanStatus, _TREATMENT_PLAN_STATE_FLAGS, _TREATMENT_PLAN_TRANSITIONS),
    ("risk_acceptance", AcceptanceStatus, _ACCEPTANCE_STATE_FLAGS, _ACCEPTANCE_TRANSITIONS),
    ("vulnerability", VulnerabilityStatus, _VULNERABILITY_STATE_FLAGS, _VULNERABILITY_TRANSITIONS),
    ("ebios_workshop", EbiosWorkshopStatus, _EBIOS_WORKSHOP_STATE_FLAGS, _EBIOS_WORKSHOP_TRANSITIONS),
    ("ebios_study_framework", EbiosStudyFrameworkStatus, _EBIOS_STUDY_FRAMEWORK_STATE_FLAGS, _EBIOS_STUDY_FRAMEWORK_TRANSITIONS),
    ("ebios_security_baseline", EbiosBaselineStatus, _EBIOS_SECURITY_BASELINE_STATE_FLAGS, _EBIOS_SECURITY_BASELINE_TRANSITIONS),
    ("ebios_summary", EbiosSummaryStatus, _EBIOS_SUMMARY_STATE_FLAGS, _EBIOS_SUMMARY_TRANSITIONS),
    ("ebios_baseline_gap", BaselineGapStatus, _EBIOS_BASELINE_GAP_STATE_FLAGS, _EBIOS_BASELINE_GAP_TRANSITIONS),
    ("ebios_pacs_measure", PACSMeasureStatus, _EBIOS_PACS_MEASURE_STATE_FLAGS, _EBIOS_PACS_MEASURE_TRANSITIONS),
]

for _name, _enum, _flags, _pairs in _DEFINITIONS:
    register_lifecycle(_build(_name, _enum, _flags, _pairs))

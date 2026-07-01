"""Standardised lifecycles for the compliance module (rebuilt engine).

Ports the legacy ``action_plan`` and ``compliance_assessment`` workflows to the
standardised :mod:`core.lifecycle` engine. Step codes, labels and governance
flags are identical to the legacy machines (generated from the same transition
constants), so no ``workflow_state`` data migration is needed. The action-plan
refusal moves keep their mandatory comment.

Imported from ``ComplianceConfig.ready()`` so registration happens at startup.
"""

from compliance.constants import (
    ACTION_PLAN_CANCELLABLE_STATUSES,
    ACTION_PLAN_REFUSAL_TRANSITIONS,
    ACTION_PLAN_TRANSITIONS,
    ASSESSMENT_STATUS_TRANSITIONS,
    ActionPlanStatus,
    AssessmentStatus,
)
from core.lifecycle import lifecycle_from_state_flags, register_lifecycle

ACTION_PLAN_LIFECYCLE_NAME = "action_plan"
ASSESSMENT_LIFECYCLE_NAME = "compliance_assessment"

# code -> (counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
_ACTION_PLAN_STATE_FLAGS = {
    ActionPlanStatus.NEW: (False, False, True, True, False, "secondary"),
    ActionPlanStatus.TO_DEFINE: (False, False, True, False, False, "info"),
    ActionPlanStatus.TO_VALIDATE: (True, False, False, False, False, "warning"),
    ActionPlanStatus.TO_IMPLEMENT: (True, True, False, False, False, "primary"),
    ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE: (True, True, False, False, False, "warning"),
    ActionPlanStatus.VALIDATED: (True, True, False, False, False, "success"),
    ActionPlanStatus.CLOSED: (True, False, False, False, True, "dark"),
    ActionPlanStatus.CANCELLED: (False, False, False, False, True, "danger"),
}

_ASSESSMENT_STATE_FLAGS = {
    AssessmentStatus.DRAFT: (False, False, True, True, False, "secondary"),
    AssessmentStatus.PLANNED: (True, False, False, False, False, "info"),
    AssessmentStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    AssessmentStatus.COMPLETED: (True, False, False, False, False, "success"),
    AssessmentStatus.CLOSED: (True, False, False, False, True, "dark"),
    AssessmentStatus.CANCELLED: (False, False, False, False, True, "danger"),
}


def _action_plan_steps():
    return [
        (status.value, status.label, *_ACTION_PLAN_STATE_FLAGS[status])
        for status in ActionPlanStatus
    ]


def _action_plan_transitions():
    transitions = []
    for source, targets in ACTION_PLAN_TRANSITIONS.items():
        for target in targets:
            is_refusal = ACTION_PLAN_REFUSAL_TRANSITIONS.get(source) == target
            transitions.append((source.value, target.value, ActionPlanStatus(target).label, is_refusal))
    for source in ACTION_PLAN_CANCELLABLE_STATUSES:
        transitions.append(
            (source.value, ActionPlanStatus.CANCELLED.value, ActionPlanStatus.CANCELLED.label, False)
        )
    return transitions


def _assessment_steps():
    return [
        (status.value, status.label, *_ASSESSMENT_STATE_FLAGS[status])
        for status in AssessmentStatus
    ]


def _assessment_transitions():
    return [
        (source.value, target.value, AssessmentStatus(target).label)
        for source, targets in ASSESSMENT_STATUS_TRANSITIONS.items()
        for target in targets
    ]


ACTION_PLAN_LIFECYCLE = register_lifecycle(
    lifecycle_from_state_flags(
        ACTION_PLAN_LIFECYCLE_NAME,
        _action_plan_steps(),
        _action_plan_transitions(),
        layout="graph",
    )
)

ASSESSMENT_LIFECYCLE = register_lifecycle(
    lifecycle_from_state_flags(
        ASSESSMENT_LIFECYCLE_NAME,
        _assessment_steps(),
        _assessment_transitions(),
        layout="graph",
    )
)

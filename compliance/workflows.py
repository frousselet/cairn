"""Specific lifecycle workflows for the compliance module.

The action plan workflow is generated from the existing constants
(``ACTION_PLAN_TRANSITIONS``, refusals, cancellable statuses and per-transition
permissions) so the state machine has a single source of truth. Governance
flags per state follow the spec in issue #105: drafting states are deletable,
working states count in reports, implementation states are linkable, and the
closed / cancelled states are terminal.

Imported from ``ComplianceConfig.ready()`` so registration happens at startup.
"""

from compliance.constants import (
    ACTION_PLAN_CANCELLABLE_STATUSES,
    ACTION_PLAN_REFUSAL_TRANSITIONS,
    ACTION_PLAN_TRANSITION_PERMISSIONS,
    ACTION_PLAN_TRANSITIONS,
    ActionPlanStatus,
)
from core.workflow import (
    WORKFLOW_REGISTRY,
    State,
    Transition,
    Workflow,
    register_workflow,
)

ACTION_PLAN_WORKFLOW_NAME = "action_plan"

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


def _build_action_plan_workflow():
    states = []
    for status in ActionPlanStatus:
        counts, linkable, deletable, initial, terminal, tone = _ACTION_PLAN_STATE_FLAGS[status]
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

    transitions = []
    for source, targets in ACTION_PLAN_TRANSITIONS.items():
        for target in targets:
            codename = ACTION_PLAN_TRANSITION_PERMISSIONS.get((source, target), "")
            action = codename.rsplit(".", 1)[1] if codename else "update"
            is_refusal = ACTION_PLAN_REFUSAL_TRANSITIONS.get(source) == target
            transitions.append(
                Transition(
                    str(source.value),
                    str(target.value),
                    ActionPlanStatus(target).label,
                    action=action,
                    requires_comment=is_refusal,
                )
            )
    for source in ACTION_PLAN_CANCELLABLE_STATUSES:
        transitions.append(
            Transition(
                str(source.value),
                str(ActionPlanStatus.CANCELLED.value),
                ActionPlanStatus.CANCELLED.label,
                action="cancel",
            )
        )

    return Workflow(ACTION_PLAN_WORKFLOW_NAME, states, transitions)


if ACTION_PLAN_WORKFLOW_NAME not in WORKFLOW_REGISTRY:
    ACTION_PLAN_WORKFLOW = register_workflow(_build_action_plan_workflow())
else:
    ACTION_PLAN_WORKFLOW = WORKFLOW_REGISTRY[ACTION_PLAN_WORKFLOW_NAME]

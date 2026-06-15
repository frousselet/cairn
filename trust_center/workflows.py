"""Specific lifecycle workflows for the trust center module.

The workflows are generated from the transition constants so each state machine
keeps a single source of truth (per the governance spec in
``docs/modules/governance/workflow.md``). Imported from
``TrustCenterConfig.ready()`` so registration happens at startup.
"""

from core.workflow import (
    WORKFLOW_REGISTRY,
    State,
    Transition,
    Workflow,
    register_workflow,
)
from trust_center.constants import (
    DOCUMENT_REQUEST_STATES,
    DOCUMENT_REQUEST_TRANSITIONS,
    PUBLICATION_STATES,
    PUBLICATION_TRANSITIONS,
)

PUBLICATION_WORKFLOW_NAME = "trust_center_publication"
DOCUMENT_REQUEST_WORKFLOW_NAME = "trust_center_document_request"


def _build_publication_workflow():
    states = [
        State(
            code,
            label,
            counts_in_reports=counts,
            linkable=linkable,
            deletable=deletable,
            is_initial=initial,
            is_terminal=terminal,
            tone=tone,
            branch=branch,
        )
        for (code, label, counts, linkable, deletable, initial, terminal, tone, branch)
        in PUBLICATION_STATES
    ]
    transitions = [
        Transition(source, target, verb, action=action)
        for (source, target, verb, action) in PUBLICATION_TRANSITIONS
    ]
    return Workflow(PUBLICATION_WORKFLOW_NAME, states, transitions)


def _build_document_request_workflow():
    states = [
        State(
            code,
            label,
            counts_in_reports=counts,
            linkable=linkable,
            deletable=deletable,
            is_initial=initial,
            is_terminal=terminal,
            tone=tone,
            branch=branch,
        )
        for (code, label, counts, linkable, deletable, initial, terminal, tone, branch)
        in DOCUMENT_REQUEST_STATES
    ]
    transitions = [
        Transition(source, target, verb, action=action, requires_comment=requires_comment)
        for (source, target, verb, action, requires_comment) in DOCUMENT_REQUEST_TRANSITIONS
    ]
    return Workflow(DOCUMENT_REQUEST_WORKFLOW_NAME, states, transitions)


if PUBLICATION_WORKFLOW_NAME not in WORKFLOW_REGISTRY:
    PUBLICATION_WORKFLOW = register_workflow(_build_publication_workflow())
else:
    PUBLICATION_WORKFLOW = WORKFLOW_REGISTRY[PUBLICATION_WORKFLOW_NAME]

if DOCUMENT_REQUEST_WORKFLOW_NAME not in WORKFLOW_REGISTRY:
    DOCUMENT_REQUEST_WORKFLOW = register_workflow(_build_document_request_workflow())
else:
    DOCUMENT_REQUEST_WORKFLOW = WORKFLOW_REGISTRY[DOCUMENT_REQUEST_WORKFLOW_NAME]

"""Specific lifecycle workflows for the assets module.

Unlike the compliance / reports machines, the asset statuses had no transition
constants (the status was freely editable), so the graphs below encode the
natural ITAM progressions; the legacy free status writes keep working through
the status <-> workflow_state sync during the migration period.

Governance: every state stays reportable (decommissioned and disposed assets
belong to audit history; there is no cancelled-like state), terminal-bound
states are not linkable (consistent with RS-04: no new dependencies on
decommissioned / disposed support assets), and only each model's
creation-default states are deletable.

Imported from ``AssetsConfig.ready()`` so registration happens at startup.
"""

from assets.constants import EssentialAssetStatus, SupportAssetStatus
from core.workflow import (
    WORKFLOW_REGISTRY,
    State,
    Transition,
    Workflow,
    register_workflow,
)

ESSENTIAL_ASSET_WORKFLOW_NAME = "essential_asset"
SUPPORT_ASSET_WORKFLOW_NAME = "support_asset"

# code -> (counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
_ESSENTIAL_ASSET_STATE_FLAGS = {
    EssentialAssetStatus.IDENTIFIED: (True, True, True, True, False, "secondary"),
    EssentialAssetStatus.ACTIVE: (True, True, False, False, False, "success"),
    EssentialAssetStatus.UNDER_REVIEW: (True, True, False, False, False, "warning"),
    EssentialAssetStatus.DECOMMISSIONED: (True, False, False, False, True, "dark"),
}

_ESSENTIAL_ASSET_TRANSITIONS = [
    (EssentialAssetStatus.IDENTIFIED, EssentialAssetStatus.ACTIVE),
    (EssentialAssetStatus.IDENTIFIED, EssentialAssetStatus.DECOMMISSIONED),
    (EssentialAssetStatus.ACTIVE, EssentialAssetStatus.UNDER_REVIEW),
    (EssentialAssetStatus.UNDER_REVIEW, EssentialAssetStatus.ACTIVE),
    (EssentialAssetStatus.UNDER_REVIEW, EssentialAssetStatus.DECOMMISSIONED),
    (EssentialAssetStatus.ACTIVE, EssentialAssetStatus.DECOMMISSIONED),
]

# The support asset is created directly active (model default); in_stock
# covers hardware received but not yet deployed. Decommissioned is not
# terminal: disposal follows it.
_SUPPORT_ASSET_STATE_FLAGS = {
    SupportAssetStatus.IN_STOCK: (True, True, True, False, False, "secondary"),
    SupportAssetStatus.DEPLOYED: (True, True, False, False, False, "info"),
    SupportAssetStatus.ACTIVE: (True, True, True, True, False, "success"),
    SupportAssetStatus.UNDER_MAINTENANCE: (True, True, False, False, False, "warning"),
    SupportAssetStatus.DECOMMISSIONED: (True, False, False, False, False, "dark"),
    SupportAssetStatus.DISPOSED: (True, False, False, False, True, "dark"),
}

_SUPPORT_ASSET_TRANSITIONS = [
    (SupportAssetStatus.IN_STOCK, SupportAssetStatus.DEPLOYED),
    (SupportAssetStatus.IN_STOCK, SupportAssetStatus.ACTIVE),
    (SupportAssetStatus.IN_STOCK, SupportAssetStatus.DECOMMISSIONED),
    (SupportAssetStatus.DEPLOYED, SupportAssetStatus.ACTIVE),
    (SupportAssetStatus.DEPLOYED, SupportAssetStatus.DECOMMISSIONED),
    (SupportAssetStatus.ACTIVE, SupportAssetStatus.UNDER_MAINTENANCE),
    (SupportAssetStatus.ACTIVE, SupportAssetStatus.DECOMMISSIONED),
    (SupportAssetStatus.UNDER_MAINTENANCE, SupportAssetStatus.ACTIVE),
    (SupportAssetStatus.UNDER_MAINTENANCE, SupportAssetStatus.DECOMMISSIONED),
    (SupportAssetStatus.DECOMMISSIONED, SupportAssetStatus.DISPOSED),
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


if ESSENTIAL_ASSET_WORKFLOW_NAME not in WORKFLOW_REGISTRY:
    ESSENTIAL_ASSET_WORKFLOW = register_workflow(
        _build(
            ESSENTIAL_ASSET_WORKFLOW_NAME,
            EssentialAssetStatus,
            _ESSENTIAL_ASSET_STATE_FLAGS,
            _ESSENTIAL_ASSET_TRANSITIONS,
        )
    )
else:
    ESSENTIAL_ASSET_WORKFLOW = WORKFLOW_REGISTRY[ESSENTIAL_ASSET_WORKFLOW_NAME]

if SUPPORT_ASSET_WORKFLOW_NAME not in WORKFLOW_REGISTRY:
    SUPPORT_ASSET_WORKFLOW = register_workflow(
        _build(
            SUPPORT_ASSET_WORKFLOW_NAME,
            SupportAssetStatus,
            _SUPPORT_ASSET_STATE_FLAGS,
            _SUPPORT_ASSET_TRANSITIONS,
        )
    )
else:
    SUPPORT_ASSET_WORKFLOW = WORKFLOW_REGISTRY[SUPPORT_ASSET_WORKFLOW_NAME]

# NB: the supplier no longer runs a core.workflow workflow - it was migrated to
# the standardised core.lifecycle engine (see assets/lifecycles.py).

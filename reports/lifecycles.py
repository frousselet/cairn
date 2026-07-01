"""Standardised lifecycle for the management review (ISO 27001 clause 9.3).

Ports the legacy ``management_review`` workflow to the standardised
:mod:`core.lifecycle` engine: identical step codes, labels and governance flags
(generated from the same transition constants), so no ``workflow_state`` data
migration is needed. Cancellation keeps its mandatory comment. The legacy
``approve`` permission action on closure is enforced by the API / view layer,
not the engine.

Imported from ``ReportsConfig.ready()`` so registration happens at startup.
"""

from core.lifecycle import lifecycle_from_state_flags, register_lifecycle
from reports.constants import (
    MANAGEMENT_REVIEW_CANCELLABLE_STATUSES,
    MANAGEMENT_REVIEW_TRANSITIONS,
    ManagementReviewStatus,
)

MANAGEMENT_REVIEW_LIFECYCLE_NAME = "management_review"

# code -> (counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
_MANAGEMENT_REVIEW_STATE_FLAGS = {
    ManagementReviewStatus.PLANNED: (True, False, True, True, False, "info"),
    ManagementReviewStatus.IN_PREPARATION: (True, False, False, False, False, "primary"),
    ManagementReviewStatus.HELD: (True, False, False, False, False, "success"),
    ManagementReviewStatus.CLOSED: (True, False, False, False, True, "dark"),
    ManagementReviewStatus.CANCELLED: (False, False, False, False, True, "danger"),
}


def _steps():
    return [
        (status.value, status.label, *_MANAGEMENT_REVIEW_STATE_FLAGS[status])
        for status in ManagementReviewStatus
    ]


def _transitions():
    transitions = []
    for source, targets in MANAGEMENT_REVIEW_TRANSITIONS.items():
        for target in targets:
            transitions.append((source.value, target.value, ManagementReviewStatus(target).label, False))
    for source in MANAGEMENT_REVIEW_CANCELLABLE_STATUSES:
        # Cancellation requires a mandatory comment.
        transitions.append(
            (source.value, ManagementReviewStatus.CANCELLED.value, ManagementReviewStatus.CANCELLED.label, True)
        )
    return transitions


MANAGEMENT_REVIEW_LIFECYCLE = register_lifecycle(
    lifecycle_from_state_flags(
        MANAGEMENT_REVIEW_LIFECYCLE_NAME,
        _steps(),
        _transitions(),
        layout="graph",
    )
)

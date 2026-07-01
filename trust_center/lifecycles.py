"""Standardised lifecycles for the trust center module (rebuilt engine).

Ports the legacy ``trust_center_publication`` and
``trust_center_document_request`` workflows to the standardised
:mod:`core.lifecycle` engine. Step codes, labels and governance flags are
identical to the legacy machines (generated from the same constants), so no
``workflow_state`` data migration is needed.

Unlike the other migrated entities, the trust center is a publishing surface
that keeps a **per-transition Django permission**: publishing / unpublishing /
approving a document request requires the matching ``.approve`` permission. The
ported transitions carry that permission via ``permission_action`` so the
lifecycle engine (and every layer that goes through it) keeps enforcing it.

Imported from ``TrustCenterConfig.ready()`` so registration happens at startup.
"""

from core.lifecycle import lifecycle_from_state_flags, register_lifecycle
from trust_center.constants import (
    DOCUMENT_REQUEST_STATES,
    DOCUMENT_REQUEST_TRANSITIONS,
    PUBLICATION_STATES,
    PUBLICATION_TRANSITIONS,
)

PUBLICATION_LIFECYCLE_NAME = "trust_center_publication"
DOCUMENT_REQUEST_LIFECYCLE_NAME = "trust_center_document_request"


def _steps(rows):
    # rows: (code, label, counts, linkable, deletable, is_initial, is_terminal, tone, branch)
    return [
        (code, label, counts, linkable, deletable, is_initial, is_terminal, tone)
        for (code, label, counts, linkable, deletable, is_initial, is_terminal, tone, _branch) in rows
    ]


def _publication_transitions():
    # (source, target, verb, action) -> (source, target, label, requires_comment, permission_action)
    return [(source, target, verb, False, action) for (source, target, verb, action) in PUBLICATION_TRANSITIONS]


def _document_request_transitions():
    # (source, target, verb, action, requires_comment) -> (..., requires_comment, permission_action)
    return [
        (source, target, verb, requires_comment, action)
        for (source, target, verb, action, requires_comment) in DOCUMENT_REQUEST_TRANSITIONS
    ]


PUBLICATION_LIFECYCLE = register_lifecycle(
    lifecycle_from_state_flags(
        PUBLICATION_LIFECYCLE_NAME,
        _steps(PUBLICATION_STATES),
        _publication_transitions(),
        layout="graph",
    )
)

DOCUMENT_REQUEST_LIFECYCLE = register_lifecycle(
    lifecycle_from_state_flags(
        DOCUMENT_REQUEST_LIFECYCLE_NAME,
        _steps(DOCUMENT_REQUEST_STATES),
        _document_request_transitions(),
        layout="graph",
    )
)

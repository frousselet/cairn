"""Safe, translatable messages for workflow transition errors.

Returning ``str(exc)`` from a workflow error to an HTTP client leaks internal
exception detail (CodeQL ``py/stack-trace-exposure``). These helpers map the
known transition errors to stable, user-facing, translatable messages instead.
Shared across every app that surfaces workflow transitions (context, trust
center, ...).
"""

from django.utils.translation import gettext_lazy as _

from core.lifecycle import CommentRequiredError as LifecycleCommentRequiredError
from core.lifecycle import IllegalTransitionError as LifecycleIllegalTransitionError
from core.lifecycle import TransitionNotAllowedError, UnknownStepError
from core.workflow import (
    CommentRequiredError,
    IllegalTransitionError,
    PermissionDeniedError,
    UnknownStateError,
)

PERMISSION_DENIED_DETAIL = _("You do not have permission to perform this transition.")
GENERIC_DETAIL = _("This transition is not allowed.")

_COMMENT_REQUIRED = _("A comment is required for this transition.")
_ILLEGAL = _("This transition is not allowed from the current state.")
_UNKNOWN = _("Unknown target state.")

_BY_TYPE = {
    # Legacy core.workflow errors.
    CommentRequiredError: _COMMENT_REQUIRED,
    IllegalTransitionError: _ILLEGAL,
    UnknownStateError: _UNKNOWN,
    # Standardised core.lifecycle errors.
    LifecycleCommentRequiredError: _COMMENT_REQUIRED,
    LifecycleIllegalTransitionError: _ILLEGAL,
    UnknownStepError: _UNKNOWN,
}


def transition_error_detail(exc):
    """Return a safe message for a workflow / lifecycle transition error.

    Never returns ``str(exc)`` (CodeQL ``py/stack-trace-exposure``): the known
    transition errors of both engines map to stable, translatable messages.
    """
    if isinstance(exc, (PermissionDeniedError, TransitionNotAllowedError)):
        return PERMISSION_DENIED_DETAIL
    return _BY_TYPE.get(type(exc), GENERIC_DETAIL)

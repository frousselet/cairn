"""Safe, translatable messages for lifecycle transition errors.

Returning ``str(exc)`` from a transition error to an HTTP client leaks internal
exception detail (CodeQL ``py/stack-trace-exposure``). These helpers map the
known :mod:`core.lifecycle` transition errors to stable, user-facing,
translatable messages instead. Shared across every app that surfaces lifecycle
transitions (context, trust center, ...).
"""

from django.utils.translation import gettext_lazy as _

from core.lifecycle import (
    CommentRequiredError,
    IllegalTransitionError,
    TransitionNotAllowedError,
    UnknownStepError,
)

PERMISSION_DENIED_DETAIL = _("You do not have permission to perform this transition.")
GENERIC_DETAIL = _("This transition is not allowed.")

_BY_TYPE = {
    CommentRequiredError: _("A comment is required for this transition."),
    IllegalTransitionError: _("This transition is not allowed from the current state."),
    UnknownStepError: _("Unknown target state."),
}


def transition_error_detail(exc):
    """Return a safe message for a lifecycle transition error.

    Never returns ``str(exc)`` (CodeQL ``py/stack-trace-exposure``): the known
    transition errors map to stable, translatable messages.
    """
    if isinstance(exc, TransitionNotAllowedError):
        return PERMISSION_DENIED_DETAIL
    return _BY_TYPE.get(type(exc), GENERIC_DETAIL)

"""Safe, translatable messages for workflow transition errors.

Returning ``str(exc)`` from a workflow error to an HTTP client leaks internal
exception detail (CodeQL ``py/stack-trace-exposure``). These helpers map the
known transition errors to stable, user-facing, translatable messages instead,
shared by the management API and the curation views.
"""

from django.utils.translation import gettext_lazy as _

from core.workflow import (
    CommentRequiredError,
    IllegalTransitionError,
    PermissionDeniedError,
    UnknownStateError,
)

PERMISSION_DENIED_DETAIL = _("You do not have permission to perform this transition.")
GENERIC_DETAIL = _("This transition is not allowed.")

_BY_TYPE = {
    CommentRequiredError: _("A comment is required for this transition."),
    IllegalTransitionError: _("This transition is not allowed from the current state."),
    UnknownStateError: _("Unknown target state."),
}


def transition_error_detail(exc):
    """Return a safe message for a workflow transition error (never str(exc))."""
    if isinstance(exc, PermissionDeniedError):
        return PERMISSION_DENIED_DETAIL
    return _BY_TYPE.get(type(exc), GENERIC_DETAIL)

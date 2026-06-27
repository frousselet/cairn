"""Backward-compatible re-export.

The canonical helper now lives in :mod:`core.transition_messages` so every app
(not just the trust center) can map workflow transition errors to safe,
translatable messages. The imports below keep existing call sites working.
"""

from core.transition_messages import (  # noqa: F401
    GENERIC_DETAIL,
    PERMISSION_DENIED_DETAIL,
    transition_error_detail,
)

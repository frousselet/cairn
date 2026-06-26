"""Model-facing service for the rebuilt lifecycle engine.

:mod:`core.lifecycle` is pure schema/logic with no model imports. This thin
layer ties it to the database: it performs a transition on a model instance and
records the immutable :class:`core.models.LifecycleEvent`. Every layer (web
view, DRF, MCP) funnels through :func:`perform_transition` so validation,
permission/role checks, the per-transition form and the history log are applied
in exactly one place.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from core.lifecycle import Lifecycle, validate_transition


def _jsonify(value):
    """Coerce a form ``cleaned_data`` value to a JSON-serialisable form."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if hasattr(value, "pk"):  # a model instance
        return str(value.pk)
    if isinstance(value, (list, tuple, set)):
        return [_jsonify(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    return str(value)


def resolve_lifecycle(instance, lifecycle: Lifecycle | None) -> Lifecycle:
    """Return the lifecycle to use: explicit arg, or ``instance.get_lifecycle()``."""
    if lifecycle is not None:
        return lifecycle
    getter = getattr(instance, "get_lifecycle", None)
    if getter is None:
        raise ValueError(
            f"{type(instance).__name__} has no get_lifecycle(); pass lifecycle explicitly."
        )
    return getter()


def build_transition_form(transition, instance, data=None, files=None):
    """Instantiate the transition's form (or ``None`` if it declares no form).

    The form is constructed with ``instance=instance`` when it accepts it, so a
    transition form can read the element it acts on.
    """
    form_class = transition.get_form_class()
    if form_class is None:
        return None
    try:
        return form_class(data=data, files=files, instance=instance)
    except TypeError:
        return form_class(data=data, files=files)


def perform_transition(
    instance,
    target,
    *,
    user=None,
    comment=None,
    data=None,
    files=None,
    lifecycle: Lifecycle | None = None,
    step_field: str = "workflow_state",
    enforce_permission: bool = True,
    save: bool = True,
):
    """Validate, apply and record a lifecycle transition on ``instance``.

    Reads the current step from ``instance.<step_field>`` (falling back to the
    lifecycle's Draft step), validates the move (existence, legality, role/user
    restriction, required comment), validates the per-transition form when one is
    declared, writes the new step, persists, and appends a
    :class:`~core.models.LifecycleEvent`.

    Returns ``(event, transition)``. Raises a :class:`core.lifecycle.LifecycleError`
    subclass on an invalid or forbidden transition, or
    :class:`django.core.exceptions.ValidationError` when the form is invalid.
    """
    from django.core.exceptions import ValidationError

    from core.models import LifecycleEvent

    lc = resolve_lifecycle(instance, lifecycle)
    current = getattr(instance, step_field, None) or lc.initial_step.code

    transition = validate_transition(
        lc,
        current,
        target,
        instance=instance,
        user=user,
        comment=comment,
        enforce_permission=enforce_permission,
    )

    form_data: dict = {}
    form = build_transition_form(transition, instance, data=data, files=files)
    if form is not None:
        if not form.is_valid():
            raise ValidationError(form.errors)
        form_data = {k: _jsonify(v) for k, v in form.cleaned_data.items()}

    setattr(instance, step_field, target)
    if save:
        instance.save()

    event = LifecycleEvent.record(
        instance,
        lifecycle_name=lc.name,
        from_step=current,
        to_step=target,
        actor=user,
        comment=(comment or "").strip(),
        form_data=form_data,
    )
    return event, transition

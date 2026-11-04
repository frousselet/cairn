# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Read helpers behind the *Controls* reverse cards (README §8).

A requirement, a risk, a treatment plan, a PACS measure, a support asset, an
objective and a document each show the controls linked to them, through the
shared ``controls/includes/controls_card.html``. The card lists controls in
**any** step with their state badge (RG-CTL-04), a retired one flagged and
sorted last (RG-CTL-03), each with its effectiveness (RG-CTL-20 on the risk
and treatment pages), filtered by the reader's scopes and shown only to a
holder of ``controls.control.read``.
"""

from django.db.models import Case, IntegerField, Min, Q, Value, When
from django.utils import timezone

from controls.constants import CONTROL_RETIRED, TEST_ACTIVE, ControlEffectiveness

READ_PERMISSION = "controls.control.read"


def can_read_controls(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.has_perm(READ_PERMISSION)))


def _scoped(qs, user):
    if user.is_superuser:
        return qs
    scope_ids = user.get_allowed_scope_ids()
    if scope_ids is None:
        return qs
    from core.scoping import filter_queryset_by_scopes

    return filter_queryset_by_scopes(qs, scope_ids)


def _decorate(controls):
    """Flag a stale effectiveness (RG-CTL-15) from the annotated earliest due
    date of the active tests, without one query per row."""
    today = timezone.localdate()
    for control in controls:
        due = getattr(control, "next_active_due", None)
        control.effectiveness_stale = bool(
            not control.is_retired
            and due is not None
            and due < today
            and control.effectiveness != ControlEffectiveness.NOT_TESTED
        )
    return controls


def controls_queryset(base, user):
    """``base`` (a ``Control`` queryset) restricted to the reader's scopes,
    retired controls last, with what the card needs in a single query."""
    qs = (
        _scoped(base, user)
        .select_related("owner")
        .annotate(
            next_active_due=Min("tests__next_due_date", filter=Q(tests__workflow_state=TEST_ACTIVE)),
            retired_rank=Case(
                When(workflow_state=CONTROL_RETIRED, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .order_by("retired_rank", "reference")
    )
    return qs


def linked_controls(obj, user):
    """The controls linked to ``obj`` through its ``controls`` reverse
    accessor, or ``None`` when ``user`` may not read controls (the card is
    then not rendered at all)."""
    if not can_read_controls(user):
        return None
    return _decorate(list(controls_queryset(obj.controls.all(), user)))


def linked_controls_for_measures(measures, user):
    """The controls linked to any of ``measures`` (the PACS measures of an
    EBIOS RM study, shown together on workshop 5), each carrying in
    ``linked_via`` the references of the measures it serves."""
    if not can_read_controls(user):
        return None
    from controls.models import Control

    measures = list(measures)
    if not measures:
        return []
    by_pk = {m.pk: m for m in measures}
    controls = _decorate(list(controls_queryset(
        Control.objects.filter(pacs_measures__in=list(by_pk)).distinct(), user,
    )))
    links = Control.pacs_measures.through.objects.filter(
        control_id__in=[c.pk for c in controls], pacsmeasure_id__in=list(by_pk),
    ).values_list("control_id", "pacsmeasure_id")
    via = {}
    for control_id, measure_id in links:
        via.setdefault(control_id, []).append(by_pk[measure_id].reference)
    for control in controls:
        control.linked_via = sorted(via.get(control.pk, []))
    return controls

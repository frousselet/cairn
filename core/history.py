"""Canonical history / audit-trail computation.

Single source of truth for turning ``django-simple-history`` records into a
normalized, chronological timeline of :class:`HistoryEntry` events. Every
consumer (the lazy detail-page panel, the DRF ``/history/`` action, the MCP
``get_<entity>_history`` tools and the system-wide audit log) builds its view
from these functions, so diff logic, hidden-field rules and event
classification never diverge again.

The module is deliberately free of module-level model imports (lazy inside
functions, mirroring :mod:`core.workflow`) so it can be imported from any layer
without import cycles.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from django.utils.translation import gettext_lazy as _

# --- Field rules ------------------------------------------------------------

#: Approval bookkeeping fields, never shown as ordinary edits.
APPROVAL_FIELDS = frozenset(
    {"is_approved", "approved_by", "approved_by_id", "approved_at"}
)
#: Fields hidden from ordinary modification diffs (approval + version churn).
HIDDEN_FIELDS = APPROVAL_FIELDS | {"version"}
#: Lifecycle field whose change marks a record as a workflow transition.
WORKFLOW_FIELD = "workflow_state"
#: Fields excluded from creation / deletion snapshots.
SNAPSHOT_EXCLUDED = HIDDEN_FIELDS | {
    "id",
    "history_id",
    "history_date",
    "history_change_reason",
    "history_type",
    "history_user",
    "history_user_id",
    "created_at",
    "updated_at",
    WORKFLOW_FIELD,
}

#: Default number of timeline entries returned to a single consumer.
DEFAULT_HISTORY_LIMIT = 100
#: Hard ceiling a consumer may request.
MAX_HISTORY_LIMIT = 500


# --- Normalized event model -------------------------------------------------


class EntryKind(str, Enum):
    """The kind of a single timeline event."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVAL = "approval"
    TRANSITION = "transition"


@dataclass(frozen=True)
class FieldChange:
    """A single field delta (``new`` carries the value for snapshots)."""

    field: str  # human (verbose) name
    field_code: str  # raw attname, stable for API consumers
    old: object = None
    new: object = None


@dataclass(frozen=True)
class HistoryEntry:
    """One normalized, render-ready event in an entity timeline."""

    history_id: object
    history_date: datetime
    kind: EntryKind
    user: str | None = None
    version: int | None = None
    entity_label: str | None = None
    # UPDATE
    changes: tuple[FieldChange, ...] = ()
    # CREATE / DELETE
    snapshot: tuple[FieldChange, ...] = ()
    # APPROVAL
    approved: bool | None = None
    # TRANSITION
    from_state: str | None = None
    to_state: str | None = None
    from_label: str | None = None
    to_label: str | None = None
    comment: str | None = None
    is_refusal: bool = False

    def as_dict(self) -> dict:
        """JSON-serializable form for the API and MCP surfaces."""
        data = {
            "history_id": self.history_id,
            "history_date": (
                self.history_date.isoformat()
                if hasattr(self.history_date, "isoformat")
                else self.history_date
            ),
            "kind": self.kind.value,
            "user": self.user,
            "version": self.version,
            "entity_label": str(self.entity_label) if self.entity_label else None,
        }
        if self.kind is EntryKind.UPDATE:
            data["changes"] = [
                {
                    "field": str(c.field),
                    "field_code": c.field_code,
                    "old": _str_or_none(c.old),
                    "new": _str_or_none(c.new),
                }
                for c in self.changes
            ]
        elif self.kind in (EntryKind.CREATE, EntryKind.DELETE):
            data["snapshot"] = [
                {"field": str(c.field), "field_code": c.field_code, "value": _str_or_none(c.new)}
                for c in self.snapshot
            ]
        elif self.kind is EntryKind.APPROVAL:
            data["approved"] = self.approved
        elif self.kind is EntryKind.TRANSITION:
            data.update(
                from_state=self.from_state,
                to_state=self.to_state,
                from_label=str(self.from_label) if self.from_label else None,
                to_label=str(self.to_label) if self.to_label else None,
                comment=self.comment,
                is_refusal=self.is_refusal,
            )
        return data


def _str_or_none(value):
    return str(value) if value not in (None, "") else None


# --- Per-record helpers -----------------------------------------------------


def resolve_verbose_name(record, field_code: str) -> str:
    """Return a field's verbose name, falling back to a humanized code."""
    try:
        return str(record.instance_type._meta.get_field(field_code).verbose_name)
    except Exception:
        return field_code.replace("_", " ").capitalize()


def _safe_prev(record):
    try:
        return record.prev_record
    except Exception:
        return None


def _is_backward_transition(model, from_code: str, to_code: str) -> bool:
    """Whether ``from_code -> to_code`` moves back along the main flow.

    Recomputed from the registered workflow (the single source of truth) rather
    than persisted, mirroring :class:`accounts.mixins.WorkflowStepperMixin`'s
    refusal logic. Branch off-ramps (cancelled / archived) are not refusals.
    """
    try:
        from core.workflow import resolve_workflow

        workflow = resolve_workflow(model)
        main = [s.code for s in workflow.states if not s.branch]
        if from_code in main and to_code in main:
            return main.index(to_code) < main.index(from_code)
    except Exception:
        pass
    return False


def _state_label(model, code: str) -> str:
    try:
        from core.workflow import resolve_workflow

        return str(resolve_workflow(model).state(code).label)
    except Exception:
        return code


def snapshot(record) -> tuple[FieldChange, ...]:
    """Full field values of a creation / deletion record (as ``new``)."""
    fields = []
    for f in record._meta.get_fields():
        name = getattr(f, "attname", None) or f.name
        if name in SNAPSHOT_EXCLUDED or name.startswith("history_"):
            continue
        if not hasattr(f, "column"):  # skip reverse relations
            continue
        try:
            value = getattr(record, name)
        except Exception:
            continue
        if value in (None, ""):
            continue
        fields.append(FieldChange(resolve_verbose_name(record, f.name), f.name, new=value))
    return tuple(fields)


def classify_record(record) -> EntryKind:
    """Classify a single historical record into an :class:`EntryKind`.

    Precedence on a modification (``~``): transition (the lifecycle field
    changed) > approval-only (only approval fields changed) > update.
    """
    if record.history_type == "+":
        return EntryKind.CREATE
    if record.history_type == "-":
        return EntryKind.DELETE
    prev = _safe_prev(record)
    if prev is None:
        return EntryKind.UPDATE
    try:
        changed = {c.field for c in record.diff_against(prev).changes}
    except Exception:
        return EntryKind.UPDATE
    if WORKFLOW_FIELD in changed:
        return EntryKind.TRANSITION
    if changed and changed <= HIDDEN_FIELDS and (changed & APPROVAL_FIELDS):
        return EntryKind.APPROVAL
    return EntryKind.UPDATE


def build_entry(record) -> HistoryEntry:
    """Turn one historical record into a normalized :class:`HistoryEntry`."""
    common = {
        "history_id": record.history_id,
        "history_date": record.history_date,
        "user": str(record.history_user) if record.history_user_id else None,
        "version": getattr(record, "version", None),
        "entity_label": getattr(record, "entity_label", None),
    }
    kind = classify_record(record)

    if kind is EntryKind.CREATE:
        return HistoryEntry(kind=kind, snapshot=snapshot(record), **common)
    if kind is EntryKind.DELETE:
        return HistoryEntry(kind=kind, snapshot=snapshot(record), **common)

    delta = record.diff_against(_safe_prev(record))

    if kind is EntryKind.TRANSITION:
        ws = next(c for c in delta.changes if c.field == WORKFLOW_FIELD)
        model = record.instance_type
        return HistoryEntry(
            kind=kind,
            from_state=ws.old,
            to_state=ws.new,
            from_label=_state_label(model, ws.old),
            to_label=_state_label(model, ws.new),
            comment=getattr(record, "history_change_reason", None) or None,
            is_refusal=_is_backward_transition(model, ws.old, ws.new),
            **common,
        )

    if kind is EntryKind.APPROVAL:
        return HistoryEntry(kind=kind, approved=bool(getattr(record, "is_approved", False)), **common)

    changes = tuple(
        FieldChange(resolve_verbose_name(record, c.field), c.field, old=c.old, new=c.new)
        for c in delta.changes
        if c.field not in HIDDEN_FIELDS
    )
    return HistoryEntry(kind=EntryKind.UPDATE, changes=changes, **common)


# --- Timeline assembly ------------------------------------------------------


@dataclass(frozen=True)
class ExtraSource:
    """Entries merged into a timeline from a non-``history`` source.

    ``suppress_generic_transitions`` drops transition events derived from the
    instance's own ``workflow_state`` diffs, so an entity that carries a richer
    dedicated transition log (action plans, management reviews) shows those rows
    instead of bare state changes, with no duplication.
    """

    entries: tuple[HistoryEntry, ...] = ()
    suppress_generic_transitions: bool = False


def build_timeline(
    instance,
    *,
    limit: int = DEFAULT_HISTORY_LIMIT,
    extra: ExtraSource | None = None,
) -> list[HistoryEntry]:
    """Return the merged, reverse-chronological timeline for ``instance``."""
    records = instance.history.select_related("history_user").all()[:limit]
    entries = [build_entry(r) for r in records]
    if extra is not None:
        if extra.suppress_generic_transitions:
            entries = [e for e in entries if e.kind is not EntryKind.TRANSITION]
        entries.extend(extra.entries)
    entries.sort(key=lambda e: e.history_date, reverse=True)
    return entries[:limit]


# --- Extra-source registry (generalizes the one-off merges) -----------------

#: ``"app_label.model"`` -> callable(instance) -> :class:`ExtraSource`.
HISTORY_SOURCE_HOOKS: dict[str, Callable[[object], ExtraSource]] = {}


def register_source_hook(label: str):
    def _decorator(func):
        HISTORY_SOURCE_HOOKS[label] = func
        return func

    return _decorator


def extra_source_for(instance) -> ExtraSource | None:
    """Resolve the registered :class:`ExtraSource` for an instance, if any."""
    hook = HISTORY_SOURCE_HOOKS.get(instance._meta.label_lower)
    return hook(instance) if hook else None


def _transition_entry_from_row(model, from_code, to_code, user, when, comment, is_refusal):
    return HistoryEntry(
        history_id=f"transition-{when.isoformat()}",
        history_date=when,
        kind=EntryKind.TRANSITION,
        user=str(user) if user else None,
        from_state=from_code,
        to_state=to_code,
        from_label=_state_label(model, from_code),
        to_label=_state_label(model, to_code),
        comment=comment or None,
        is_refusal=bool(is_refusal),
    )


@register_source_hook("context.role")
def _role_extra(role) -> ExtraSource:
    """Merge each responsibility's history into the role timeline."""
    from context.models import Responsibility

    label = _("Responsibility")
    entries = []
    for rec in Responsibility.history.filter(role_id=role.pk).select_related("history_user"):
        rec.entity_label = label
        entries.append(build_entry(rec))
    return ExtraSource(entries=tuple(entries))


@register_source_hook("compliance.complianceactionplan")
def _action_plan_extra(action_plan) -> ExtraSource:
    """Use the dedicated transition log (carries comments) for action plans."""
    entries = [
        _transition_entry_from_row(
            type(action_plan), t.from_status, t.to_status, t.performed_by,
            t.created_at, t.comment, t.is_refusal,
        )
        for t in action_plan.transitions.select_related("performed_by").all()
    ]
    return ExtraSource(entries=tuple(entries), suppress_generic_transitions=True)


@register_source_hook("reports.managementreview")
def _management_review_extra(review) -> ExtraSource:
    """Use the dedicated transition log (carries comments) for reviews."""
    entries = [
        _transition_entry_from_row(
            type(review), t.from_status, t.to_status, t.performed_by,
            t.created_at, t.comment, getattr(t, "is_refusal", False),
        )
        for t in review.transitions.select_related("performed_by").all()
    ]
    return ExtraSource(entries=tuple(entries), suppress_generic_transitions=True)

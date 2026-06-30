"""Unified To do / Doing / Done Kanban board.

Aggregates governance work items from several modules into a single, read-only
three-column board (To do / Doing / Done). This first version groups four entity
types:

- Action plans (``compliance.ComplianceActionPlan``)
- Treatment actions (``risks.TreatmentAction``)
- Audits (``compliance.ComplianceAssessment``)
- Risk assessments (``risks.RiskAssessment``)

The board is intentionally read-only (no drag-and-drop) and omits the terminal
"removed from tracking" states (cancelled / archived): a card disappears from the
board once its item is cancelled or archived.

Each entity declares how its statuses map to the three columns and which
Bootstrap tone its status badge uses. This module is the single source of truth
shared by the web view, the JSON endpoint and the MCP tool.
"""

from datetime import date

from django.urls import reverse
from django.utils import timezone
from django.utils.translation import pgettext_lazy

# ── Columns ────────────────────────────────────────────────

TODO = "todo"
DOING = "doing"
DONE = "done"

COLUMN_ORDER = (TODO, DOING, DONE)

COLUMN_LABELS = {
    TODO: pgettext_lazy("kanban", "To do"),
    DOING: pgettext_lazy("kanban", "Doing"),
    DONE: pgettext_lazy("kanban", "Done"),
}

# ── Entity type metadata ───────────────────────────────────

# Read permission gating each entity type. A user only sees the types they are
# allowed to read.
ENTITY_PERMS = {
    "action_plan": "compliance.action_plan.read",
    "treatment_action": "risks.treatment.read",
    "audit": "compliance.assessment.read",
    "risk_assessment": "risks.assessment.read",
}

# Bootstrap Icons identifying each type (brand: neutral type marker, icon only,
# semantic colours are reserved for status badges).
TYPE_ICONS = {
    "action_plan": "bi-card-checklist",
    "treatment_action": "bi-bandaid",
    "audit": "bi-clipboard-check",
    "risk_assessment": "bi-shield-exclamation",
}

TYPE_LABELS = {
    "action_plan": pgettext_lazy("kanban", "Action plan"),
    "treatment_action": pgettext_lazy("kanban", "Treatment action"),
    "audit": pgettext_lazy("kanban", "Audit"),
    "risk_assessment": pgettext_lazy("kanban", "Risk assessment"),
}

# ── Status → (column, badge tone) maps ─────────────────────
# Statuses absent from a map (cancelled, archived) are excluded from the board.

_ACTION_PLAN_BUCKETS = {
    "new": (TODO, "secondary"),
    "to_define": (TODO, "info"),
    "to_validate": (TODO, "warning"),
    "to_implement": (DOING, "primary"),
    "implementation_to_validate": (DOING, "warning"),
    "validated": (DONE, "success"),
    "closed": (DONE, "dark"),
}

_TREATMENT_ACTION_BUCKETS = {
    "planned": (TODO, "secondary"),
    "in_progress": (DOING, "primary"),
    "completed": (DONE, "success"),
}

_AUDIT_BUCKETS = {
    "draft": (TODO, "secondary"),
    "planned": (TODO, "info"),
    "in_progress": (DOING, "primary"),
    "completed": (DONE, "success"),
    "closed": (DONE, "dark"),
}

_RISK_ASSESSMENT_BUCKETS = {
    "draft": (TODO, "secondary"),
    "in_progress": (DOING, "primary"),
    "completed": (DONE, "info"),
    "validated": (DONE, "success"),
}


# ── Helpers ────────────────────────────────────────────────

def _resolve_scope_ids(user):
    """Return the scope ids the user is restricted to, or ``None`` if unrestricted."""
    if user.is_superuser:
        return None
    return user.get_allowed_scope_ids()


def _scope_filter(qs, scope_ids):
    """Filter a queryset by scope, mirroring ``ScopeFilterMixin`` semantics."""
    if scope_ids is None:
        return qs
    model = qs.model
    if any(f.name == "scopes" for f in model._meta.many_to_many):
        return qs.filter(scopes__id__in=scope_ids).distinct()
    return qs


def _status_labels(model):
    """Map state value -> human label.

    From the legacy ``status`` field's choices when present, otherwise from the
    model's lifecycle steps (entities whose duplicate ``status`` column was
    removed read their labels off ``workflow_state``'s lifecycle).
    """
    try:
        return dict(model._meta.get_field("status").flatchoices)
    except Exception:
        from core.lifecycle import resolve_lifecycle

        try:
            return {s.code: str(s.label) for s in resolve_lifecycle(model).steps}
        except Exception:
            return {}


def _make_card(*, column, type_key, reference, title, url, owner, due_date,
               status_label, status_tone):
    """Build a plain-dict card. ``due_date`` is a ``date`` or ``None``."""
    is_overdue = bool(
        due_date and column != DONE and due_date < timezone.localdate()
    )
    return {
        "column": column,
        "type_key": type_key,
        "type_label": str(TYPE_LABELS[type_key]),
        "type_icon": TYPE_ICONS[type_key],
        "reference": reference or "",
        "title": (title or "").strip(),
        "url": url,
        "owner": owner,
        "due_date": due_date,
        "is_overdue": is_overdue,
        "status_label": str(status_label),
        "status_tone": status_tone,
    }


# ── Per-entity builders ────────────────────────────────────

def _build_action_plans(scope_ids):
    from compliance.models import ComplianceActionPlan

    labels = _status_labels(ComplianceActionPlan)
    qs = _scope_filter(
        ComplianceActionPlan.objects.select_related("owner"), scope_ids
    )
    cards = []
    for ap in qs:
        bucket = _ACTION_PLAN_BUCKETS.get(ap.status)
        if not bucket:
            continue
        column, tone = bucket
        cards.append(_make_card(
            column=column,
            type_key="action_plan",
            reference=ap.reference,
            title=ap.name,
            url=reverse("compliance:action-plan-detail", kwargs={"pk": ap.pk}),
            owner=ap.owner.display_name if ap.owner_id else "",
            due_date=ap.target_date,
            status_label=labels.get(ap.status, ap.status),
            status_tone=tone,
        ))
    return cards


def _build_treatment_actions(scope_ids):
    from risks.models import TreatmentAction

    labels = _status_labels(TreatmentAction)
    # Treatment actions are not scope-tenant (their plan is a plain BaseModel),
    # so no scope filter applies; they are gated by the treatment read perm.
    qs = TreatmentAction.objects.select_related("owner", "treatment_plan")
    cards = []
    for ta in qs:
        bucket = _TREATMENT_ACTION_BUCKETS.get(ta.status)
        if not bucket:
            continue
        column, tone = bucket
        cards.append(_make_card(
            column=column,
            type_key="treatment_action",
            reference=ta.treatment_plan.reference,
            title=ta.description,
            url=reverse(
                "risks:treatment-plan-detail",
                kwargs={"pk": ta.treatment_plan_id},
            ),
            owner=ta.owner.display_name if ta.owner_id else "",
            due_date=ta.target_date,
            status_label=labels.get(ta.status, ta.status),
            status_tone=tone,
        ))
    return cards


def _build_audits(scope_ids):
    from compliance.models import ComplianceAssessment

    labels = _status_labels(ComplianceAssessment)
    qs = _scope_filter(
        ComplianceAssessment.objects.select_related("assessor"), scope_ids
    )
    cards = []
    for audit in qs:
        bucket = _AUDIT_BUCKETS.get(audit.status)
        if not bucket:
            continue
        column, tone = bucket
        cards.append(_make_card(
            column=column,
            type_key="audit",
            reference=audit.reference,
            title=audit.name,
            url=reverse("compliance:assessment-detail", kwargs={"pk": audit.pk}),
            owner=audit.assessor.display_name if audit.assessor_id else "",
            due_date=audit.assessment_end_date,
            status_label=labels.get(audit.status, audit.status),
            status_tone=tone,
        ))
    return cards


def _build_risk_assessments(scope_ids):
    from risks.models import RiskAssessment

    labels = _status_labels(RiskAssessment)
    qs = _scope_filter(
        RiskAssessment.objects.select_related("assessor"), scope_ids
    )
    cards = []
    for ra in qs:
        bucket = _RISK_ASSESSMENT_BUCKETS.get(ra.status)
        if not bucket:
            continue
        column, tone = bucket
        cards.append(_make_card(
            column=column,
            type_key="risk_assessment",
            reference=ra.reference,
            title=ra.name,
            url=reverse("risks:assessment-detail", kwargs={"pk": ra.pk}),
            owner=ra.assessor.display_name if ra.assessor_id else "",
            due_date=ra.next_review_date,
            status_label=labels.get(ra.status, ra.status),
            status_tone=tone,
        ))
    return cards


_BUILDERS = {
    "action_plan": _build_action_plans,
    "treatment_action": _build_treatment_actions,
    "audit": _build_audits,
    "risk_assessment": _build_risk_assessments,
}


# ── Public API ─────────────────────────────────────────────

def build_kanban_cards(user):
    """Return the flat list of cards the user is allowed to see."""
    scope_ids = _resolve_scope_ids(user)
    cards = []
    for type_key, builder in _BUILDERS.items():
        if user.is_superuser or user.has_perm(ENTITY_PERMS[type_key]):
            cards.extend(builder(scope_ids))
    return cards


def _card_sort_key(card):
    # Overdue first, then by due date (undated last), then by reference.
    return (not card["is_overdue"], card["due_date"] or date.max, card["reference"])


def build_kanban_columns(user):
    """Return the three ordered columns with their cards and counts."""
    cards = build_kanban_cards(user)
    columns = []
    for key in COLUMN_ORDER:
        col_cards = sorted(
            (c for c in cards if c["column"] == key), key=_card_sort_key
        )
        columns.append({
            "key": key,
            "label": str(COLUMN_LABELS[key]),
            "cards": col_cards,
            "count": len(col_cards),
        })
    return columns


def serialize_card(card):
    """Return a JSON-serialisable copy of a card (date -> ISO string)."""
    data = dict(card)
    data["due_date"] = card["due_date"].isoformat() if card["due_date"] else None
    return data

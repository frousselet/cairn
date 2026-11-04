# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Unified To do / Doing / Done Kanban board.

Aggregates governance work items from several modules into a single, read-only
three-column board (To do / Doing / Done). This first version groups four entity
types:

- Action plans (``compliance.ComplianceActionPlan``)
- Treatment actions (``risks.TreatmentAction``)
- Audits (``compliance.ComplianceAssessment``)
- Risk assessments (``risks.RiskAssessment``)
- Incidents (``incidents.Incident``)
- The current user's pending acknowledgements (``documents.PolicyAcknowledgement``)
- The current user's control tests due and test runs, in progress or to
  review (``controls.ControlTest``, ``controls.ControlTestRun``)

The board is intentionally read-only (no drag-and-drop) and omits the terminal
"removed from tracking" states (cancelled / archived): a card disappears from the
board once its item is cancelled or archived.

The four legacy entities declare how their ``status`` values map to the three
columns and which Bootstrap tone their status badge uses. Incidents, which have
no ``status`` column, read the same three answers off their **lifecycle**
instead (see :func:`_build_incidents`); that is the direction the rest should
follow as their duplicate status columns go away.
This module is the single source of truth shared by the web view, the JSON
endpoint and the MCP tool.
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
# allowed to read. ``None`` means no permission is needed : the type is
# personal (the user's own acknowledgements, RG-DOC-17).
ENTITY_PERMS = {
    "action_plan": "compliance.action_plan.read",
    "treatment_action": "risks.treatment.read",
    "audit": "compliance.assessment.read",
    "risk_assessment": "risks.assessment.read",
    "incident": "incidents.incident.read",
    "acknowledgement": None,
    "control_test": "controls.test.read",
    "control_test_run": "controls.test.read",
}

# Bootstrap Icons identifying each type (brand: neutral type marker, icon only,
# semantic colours are reserved for status badges).
TYPE_ICONS = {
    "action_plan": "bi-card-checklist",
    "treatment_action": "bi-bandaid",
    "audit": "bi-clipboard-check",
    "risk_assessment": "bi-shield-exclamation",
    "incident": "bi-fire",
    "acknowledgement": "bi-pen",
    "control_test": "bi-clipboard-pulse",
    "control_test_run": "bi-clipboard-check",
}

TYPE_LABELS = {
    "action_plan": pgettext_lazy("kanban", "Action plan"),
    "treatment_action": pgettext_lazy("kanban", "Treatment action"),
    "audit": pgettext_lazy("kanban", "Audit"),
    "risk_assessment": pgettext_lazy("kanban", "Risk assessment"),
    "incident": pgettext_lazy("kanban", "Incident"),
    "acknowledgement": pgettext_lazy("kanban", "Acknowledgement"),
    "control_test": pgettext_lazy("kanban", "Control test"),
    "control_test_run": pgettext_lazy("kanban", "Test run"),
}

# Lifecycle ``Step.tone`` -> Bootstrap badge context, for the entities whose
# card colour is read off the lifecycle rather than a hand-written status map.
# Mirrors the mapping the ``workflow_badge`` tag applies, so a step's badge is
# the same colour on the board as on its detail page.
_LIFECYCLE_TONE_CLASSES = {
    "neutral": "secondary",
    "muted": "secondary",
    "secondary": "secondary",
    "info": "info",
    "primary": "primary",
    "warning": "warning",
    "success": "success",
    "danger": "danger",
    "dark": "dark",
}

# Bootstrap tone -> ``.badge-dot`` variant used by the card template. The board
# keeps the Bootstrap names in ``status_tone`` (serialised by the MCP tool), and
# the card renders the framework badge, where the theme colour is ``accent``.
_BADGE_DOT_VARIANTS = {"primary": "accent"}

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
    """Filter a queryset by scope through the single resolver.

    ``core.scoping`` is the one place that knows how a model reaches
    ``context.Scope`` : its own ``scopes`` M2M, a ``scope_parent_lookup``
    inherited from a parent row, or nothing at all. Going through it means a
    child entity (an incident's notification obligation, for instance) is
    filtered here exactly as it is in the views, the API and the MCP layer,
    instead of falling through to "no filtering" the way a local copy of the
    M2M test does.
    """
    if scope_ids is None:
        return qs
    from core.scoping import filter_queryset_by_scopes

    return filter_queryset_by_scopes(qs, scope_ids)


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
        "badge_variant": _BADGE_DOT_VARIANTS.get(status_tone, status_tone),
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


def _incident_notification_due_dates(incident_ids):
    """Earliest deadline still owed, per incident, as a local date.

    An incident carries no target date of its own : what it owes is a statutory
    filing, so the deadline a responder is actually working against is the
    nearest notification obligation still open on it. Resolved in one query for
    the whole board rather than per card.
    """
    if not incident_ids:
        return {}
    from core.views import live_notification_obligations

    earliest = {}
    rows = (
        live_notification_obligations()
        .filter(incident_id__in=incident_ids, due_at__isnull=False)
        .values_list("incident_id", "due_at")
    )
    for incident_id, due_at in rows:
        current = earliest.get(incident_id)
        if current is None or due_at < current:
            earliest[incident_id] = due_at
    return {
        incident_id: timezone.localdate(due_at)
        for incident_id, due_at in earliest.items()
    }


def _build_incidents(scope_ids):
    """Incidents still being handled.

    No ``_INCIDENT_BUCKETS`` map on purpose : the incident lifecycle already
    answers the two questions a bucket map would, so it answers them here.

    - **On the board or not** : :func:`core.views.open_incidents` decides, off
      the lifecycle's own governance : a step counts while it counts in reports
      (a draft nobody has declared yet does not) and is not an exit. That leaves
      exactly the open spine and drops the closed and the reclassified, the way
      a cancelled action plan drops off.
    - **Which column** : the step the Draft entry leads into is the one where
      the response has not started, so it sits in To do; every other open step
      is work in flight, so it sits in Doing. Nothing reaches Done, because on
      this lifecycle "done" *is* an exit.

    Adding a step to ``INCIDENT_STATES`` therefore places it on the board with
    no change here.
    """
    from core.lifecycle import resolve_lifecycle
    from core.views import open_incidents
    from incidents.models import Incident

    lifecycle = resolve_lifecycle(Incident)
    # Targets of the Draft entry, minus the exits it also leads to (the
    # "from any state" archive edge starts at Draft too): what is left is the
    # step a declared incident lands on before anyone has worked it.
    entry_codes = {
        transition.target
        for transition in lifecycle.transitions_from(lifecycle.initial_step.code)
        if not lifecycle.step(transition.target).is_archived
    }
    labels = _status_labels(Incident)
    incidents = list(_scope_filter(
        open_incidents().select_related("incident_manager"), scope_ids,
    ))
    due_dates = _incident_notification_due_dates([i.pk for i in incidents])

    cards = []
    for incident in incidents:
        step = lifecycle.step(incident.workflow_state)
        cards.append(_make_card(
            column=TODO if incident.workflow_state in entry_codes else DOING,
            type_key="incident",
            reference=incident.reference,
            title=incident.title,
            url=reverse("incidents:incident-detail", kwargs={"pk": incident.pk}),
            owner=(
                incident.incident_manager.display_name
                if incident.incident_manager_id else ""
            ),
            due_date=due_dates.get(incident.pk),
            status_label=labels.get(incident.workflow_state, step.label),
            status_tone=_LIFECYCLE_TONE_CLASSES.get(step.tone, "secondary"),
        ))
    return cards


def _build_acknowledgements(scope_ids, user=None):
    """The current user's pending acknowledgements, in To do.

    Personal by construction : only the addressee may acknowledge a row
    (RG-DOC-17), so the card is the user's own and is shown regardless of
    their scopes (RG-DOC-22), with no permission required. Only rows of a
    running campaign are actionable; a closed campaign has already expired
    its pending rows. The card opens the acknowledgement page of that row.
    """
    if user is None or not user.is_authenticated:
        return []
    from documents.constants import CAMPAIGN_RUNNING, AcknowledgementStatus
    from documents.models import PolicyAcknowledgement

    rows = (
        PolicyAcknowledgement.objects.filter(
            user=user,
            status=AcknowledgementStatus.PENDING,
            campaign__workflow_state=CAMPAIGN_RUNNING,
        )
        .select_related("campaign__policy_version__policy__owner")
    )
    labels = dict(AcknowledgementStatus.choices)
    cards = []
    for row in rows:
        version = row.campaign.policy_version
        policy = version.policy
        cards.append(_make_card(
            column=TODO,
            type_key="acknowledgement",
            reference=version.reference,
            title=f"{policy.title} v{version.version_label}",
            url=reverse("documents:acknowledge", kwargs={"pk": row.pk}),
            owner=policy.owner.display_name if policy.owner_id else "",
            due_date=row.campaign.due_date,
            status_label=labels[AcknowledgementStatus.PENDING],
            status_tone="warning",
        ))
    return cards


def _build_control_tests(scope_ids, user=None):
    """The current user's control tests due within ``TEST_DUE_REMINDER_DAYS``
    (overdue ones included), in To do.

    "Mine" is whoever the due reminder goes to (README §7) : the test's
    tester, else the control owner when the test names no tester. Only an
    active test is ever due (RG-CTL-07, read off ``reportable()``).
    """
    if user is None or not user.is_authenticated:
        return []
    from datetime import timedelta

    from django.db.models import Q

    from controls.constants import TEST_DUE_REMINDER_DAYS
    from controls.models import ControlTest
    from core.lifecycle import reportable

    horizon = timezone.localdate() + timedelta(days=TEST_DUE_REMINDER_DAYS)
    tests = _scope_filter(
        reportable(ControlTest.objects.filter(
            Q(tester=user) | Q(tester__isnull=True, control__owner=user),
            next_due_date__isnull=False, next_due_date__lte=horizon,
        )).select_related("control", "tester"),
        scope_ids,
    )
    label = pgettext_lazy("kanban", "Test due")
    return [
        _make_card(
            column=TODO,
            type_key="control_test",
            reference=test.reference,
            title=test.name,
            url=reverse("controls:controltest-detail", kwargs={"pk": test.pk}),
            owner=test.tester.display_name if test.tester_id else "",
            due_date=test.next_due_date,
            status_label=label,
            status_tone="warning",
        )
        for test in tests
    ]


def _build_control_test_runs(scope_ids, user=None):
    """Test runs waiting on the current user.

    - Their own runs still in progress (``draft``), in Doing, due when their
      test is due.
    - Runs in review they may validate, in To do : only for a holder of
      ``controls.test.approve``, and **never their own** (RG-CTL-11, which
      binds superusers too), since the model would refuse the validation.
    """
    if user is None or not user.is_authenticated:
        return []
    from controls.constants import RUN_DRAFT, RUN_IN_REVIEW
    from controls.models import ControlTestRun
    from core.lifecycle import resolve_lifecycle

    lifecycle = resolve_lifecycle(ControlTestRun)
    base = ControlTestRun.objects.select_related("test__control", "performed_by")
    rows = [(DOING, run) for run in _scope_filter(base.filter(workflow_state=RUN_DRAFT, performed_by=user), scope_ids)]
    if user.is_superuser or user.has_perm("controls.test.approve"):
        to_review = base.filter(workflow_state=RUN_IN_REVIEW).exclude(performed_by=user)
        rows += [(TODO, run) for run in _scope_filter(to_review, scope_ids)]
    cards = []
    for column, run in rows:
        step = lifecycle.step(run.workflow_state)
        cards.append(_make_card(
            column=column,
            type_key="control_test_run",
            reference=run.reference,
            title=run.test.name,
            url=reverse("controls:controltestrun-detail", kwargs={"pk": run.pk}),
            owner=run.performed_by.display_name if run.performed_by_id else "",
            due_date=run.test.next_due_date if column == DOING else None,
            status_label=step.label,
            status_tone=_LIFECYCLE_TONE_CLASSES.get(step.tone, "secondary"),
        ))
    return cards


# Builders whose cards depend on the user themselves, not only on their scopes.
_PERSONAL_BUILDERS = {"acknowledgement", "control_test", "control_test_run"}

_BUILDERS = {
    "action_plan": _build_action_plans,
    "treatment_action": _build_treatment_actions,
    "audit": _build_audits,
    "risk_assessment": _build_risk_assessments,
    "incident": _build_incidents,
    "acknowledgement": _build_acknowledgements,
    "control_test": _build_control_tests,
    "control_test_run": _build_control_test_runs,
}


# ── Public API ─────────────────────────────────────────────

def build_kanban_cards(user):
    """Return the flat list of cards the user is allowed to see."""
    scope_ids = _resolve_scope_ids(user)
    cards = []
    for type_key, builder in _BUILDERS.items():
        perm = ENTITY_PERMS[type_key]
        if perm is not None and not (user.is_superuser or user.has_perm(perm)):
            continue
        if type_key in _PERSONAL_BUILDERS:
            cards.extend(builder(scope_ids, user))
        else:
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
    data.pop("badge_variant", None)  # presentation only, not part of the API
    data["due_date"] = card["due_date"].isoformat() if card["due_date"] else None
    return data

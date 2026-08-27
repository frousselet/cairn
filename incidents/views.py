# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web views for module 6 (incidents).

Four kinds of surface live in this file, and each one follows a house pattern
rather than inventing its own:

**Register pages** (incident, security event, response plan, obligations due,
and the two catalogue lists) run the full list stack, with ``ListSummaryMixin``
strictly to the left of ``ScopeFilterMixin`` so the rail counts reflect the
whole visible list rather than the active facets. Each has a matching
``*TableBodyView`` serving the HTMX refresh of ``#item-table-body``.

**Detail pages** run ``ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin,
DetailView``. Every state change on every entity in this module goes through the
generic ``workflow:transition`` endpoint fed by the stepper : there is no
transition view in this file, and ``lifecycle_transition_url_name`` is never
set, because each model's own ``transition_to()`` already carries the gates, the
stamps and the side effects.

**Drawer CRUD** for the children of an incident uses ``HtmxFormMixin`` with a
``modal_template_name``, returning to the parent's detail page. Three of those
children are append-only ledgers (the chronology, the custody ledger and the
filing log) and therefore expose a create route and nothing else : their models
refuse ``delete()`` outright, and offering an affordance that always fails is
worse than offering none.

**Scope tenancy is resolved on the parent, always.** Every view over a
non-``ScopedModel`` child declares ``scope_parent_lookup``, and every parent
resolved from a URL keyword goes through :func:`_scoped_get`, which applies the
same lookup. Reading an evidence item, a custody row or an omission rationale
from outside the incident's scopes is the failure mode this module exists to
prevent, so the guard is applied to the parent lookup and not only to the child
queryset.
"""

import json
from datetime import timedelta
from urllib.parse import quote, urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.utils.translation import pgettext_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import HistoryUrlMixin, LifecycleStepperMixin, ScopeFilterMixin
from accounts.views import PermissionRequiredMixin
from context.constants import Criticality
from core.lifecycle import DEFAULT_LIFECYCLE, LifecycleProtectedError, StepKind, reportable_states
from core.mixins import (
    AdvancedFilterMixin,
    ColumnPreferenceMixin,
    HtmxFormMixin,
    ListSummaryMixin,
    PredefinedFilterMixin,
    SavedFilterMixin,
    SortableListMixin,
    TableBodyPaginatedMixin,
)
from core.scoping import filter_queryset_by_scopes
from risks.constants import ThreatCategory

from .constants import (
    INCIDENT_STATES,
    NOTIFICATION_STATES,
    SECURITY_EVENT_STATES,
    AuthorityType,
    ClockAnchor,
    DetectionSource,
    EventTriageDecision,
    FilingOutcome,
    NotificationChannel,
    NotificationRecipientKind,
    NotificationRegime,
    SecurityEventClass,
    TrafficLightProtocol,
)
from .forms import (
    EvidenceCustodyEventForm,
    IncidentEvidenceForm,
    IncidentForm,
    IncidentNotificationForm,
    IncidentResponseActionForm,
    IncidentResponsePlanForm,
    IncidentTimelineEntryForm,
    NotificationFilingForm,
    PersonalDataBreachForm,
    PostIncidentReviewForm,
    ReportingAuthorityForm,
    ReportingObligationTemplateForm,
    SecurityEventForm,
)
from .models import (
    EvidenceCustodyEvent,
    Incident,
    IncidentEvidence,
    IncidentNotification,
    IncidentResponseAction,
    IncidentResponsePlan,
    IncidentTimelineEntry,
    NotificationFiling,
    PersonalDataBreach,
    PostIncidentReview,
    ReportingAuthority,
    ReportingObligationTemplate,
    SecurityEvent,
)
# Read from the model modules rather than from ``incidents/constants.py``,
# deliberately in each case:
#
# - ``NotificationDecision`` exists in **both** places with the same values and
#   different labels. The model's copy is the one the column's ``choices`` point
#   at, so it is the one whose labels ``get_decision_display()`` renders on the
#   row. Importing the other would give the register facets that read
#   differently from the rows they filter.
# - The deadline buckets and the two verification outcomes are derived state,
#   not lifecycle vocabulary, and the module that computes them owns them.
# - ``STEP_REPORTED`` / ``STEP_UNDER_ASSESSMENT`` are the named step codes the
#   security-event model already resolves against the constants (RG-INC-37), so
#   the KPI tiles here carry no state literal of their own.
from .models.evidence import VERIFICATION_MATCH, VERIFICATION_MISMATCH
from .models.notification import (
    DEADLINE_BUCKET_DATED,
    DEADLINE_BUCKET_NO_DEADLINE,
    DEADLINE_BUCKET_PENDING,
    NotificationDecision,
)
from .models.response_plan import EXERCISE_STALE_AFTER_DAYS
from .models.security_event import STEP_REPORTED, STEP_UNDER_ASSESSMENT

PAGE_SIZE = 50

# Six labels this module's models already declare with the ``incident``
# context, because the bare English collides with a different sense already in
# the catalogue. Re-declared here as bare strings, each would open a *second*,
# bare entry in the ``.po``, and the facet would then read differently from the
# column it filters and from the field label on the form beside it.
_SEVERITY = pgettext_lazy("incident", "Severity")
_DETECTION_SOURCE = pgettext_lazy("incident", "Detection source")
_TRIAGE_DECISION = pgettext_lazy("incident", "Triage decision")
_DECISION = pgettext_lazy("incident", "Decision")
_INCIDENT = pgettext_lazy("incident", "Incident")

#: The four-step ``default`` lifecycle, as facet options. The response plan and
#: both catalogue entities run it, so their status facets are read off the
#: registered lifecycle object rather than restated as literals here.
DEFAULT_STATE_OPTIONS = [(step.code, step.label) for step in DEFAULT_LIFECYCLE.steps]


# ── Shared helpers ─────────────────────────────────────────


def _state_options(states):
    """``(code, label)`` pairs for a lifecycle declared in ``constants.py``.

    Read off the declaration tuples rather than off a resolved ``Lifecycle``,
    because these feed module-level facet constants : resolving a lifecycle
    reaches for the ``LifecycleDefinition`` table, and a database query at
    URLconf import time breaks a fresh install and every management command.
    """
    return [(code, label) for code, label, *_flags in states]


def _archived_state_codes(states):
    """Step codes that render as a detached exit for a declared lifecycle.

    Mirrors :func:`core.lifecycle.lifecycle_from_state_flags` exactly : the
    generic ``archived`` bookend plus every state flagged terminal. This is what
    ``is_terminal_state`` answers per row, expressed as a list a queryset can
    filter on, so no view ever hardcodes a state literal (RG-INC-37).
    """
    return [
        code
        for code, _label, _counts, _linkable, _deletable, _initial, is_terminal, _tone in states
        if code == StepKind.ARCHIVED or is_terminal
    ]


def _active_state_codes(states):
    """Step codes that are neither the archived bookend nor a terminal outcome."""
    archived = set(_archived_state_codes(states))
    return [code for code, *_rest in states if code not in archived]


INCIDENT_ACTIVE_STATES = _active_state_codes(INCIDENT_STATES)
NOTIFICATION_ACTIVE_STATES = _active_state_codes(NOTIFICATION_STATES)


def _overdue_notification_q(prefix=""):
    """Match an obligation past its deadline with no filing recorded.

    The exact three conditions of ``IncidentNotification.is_overdue``, which is
    a property and therefore unusable in a queryset. Kept as one function so the
    list facet, the incident-list flag column and the rail KPI can never drift
    into three different definitions of *late*.
    """
    field = (lambda name: f"{prefix}{name}") if prefix else (lambda name: name)
    return Q(
        **{
            f"{field('due_at')}__lt": timezone.now(),
            f"{field('sent_at')}__isnull": True,
            f"{field('workflow_state')}__in": NOTIFICATION_ACTIVE_STATES,
        }
    )


def _scoped_get(model, request, pk, *, parent_lookup=None):
    """Fetch one row by primary key, honouring the caller's scope tenancy.

    Used for every parent resolved from a URL keyword. ``get_object_or_404`` on
    the bare manager would let a user outside the incident's scopes reach its
    children's create forms, and the drawer would then write a row into a
    perimeter that user cannot see.
    """
    qs = model._default_manager.all()
    user = request.user
    if not user.is_superuser:
        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is not None:
            qs = filter_queryset_by_scopes(qs, scope_ids, explicit=parent_lookup)
    return get_object_or_404(qs, pk=pk)


def _attachment_disposition(filename):
    """Build a safe ``Content-Disposition`` value (no header injection)."""
    safe = "".join(ch for ch in (filename or "") if ch not in '"\\\r\n').strip() or "download"
    return f"attachment; filename=\"{safe}\"; filename*=UTF-8''{quote(safe)}"


class CreatedByMixin:
    """Stamp the creating user on a ``BaseModel`` row."""

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class UserFormKwargsMixin:
    """Pass the acting user to the form.

    Every form in this module accepts ``user`` : ``ScopedFormMixin`` is mixed
    into all thirteen of them and is inert where there is no scope picker, so
    the drawer layer can pass it uniformly.
    """

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ProtectedDeleteMixin:
    """Turn a lifecycle deletion refusal into a message instead of a 500.

    Several models in this module refuse ``delete()`` from the model layer : a
    generated obligation, a review whose incident is still open, and anything
    outside a deletable step. Those refusals raise
    :class:`~core.lifecycle.LifecycleProtectedError`, which is not a
    ``ValidationError`` and is caught nowhere in the generic delete flow. The
    operator is told why the row survives, and is returned to the page they came
    from.
    """

    def form_valid(self, form):
        self.object = self.get_object()
        success_url = self.get_success_url()
        try:
            self.object.delete()
        except LifecycleProtectedError as exc:
            messages.error(self.request, str(exc))
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=204, headers={"HX-Trigger": "formSaved"})
        return redirect(success_url)


class IncidentChildMixin:
    """Resolve the parent incident of a child row created from its detail page.

    The lookup is a ``cached_property`` rather than a ``dispatch()`` override so
    it runs **after** the authentication and permission checks of the mixins to
    its left : resolving it in ``dispatch()`` would answer *does this incident
    exist* to an anonymous caller through the difference between a 404 and a
    login redirect.
    """

    incident_url_kwarg = "incident_pk"

    @cached_property
    def incident(self):
        return _scoped_get(Incident, self.request, self.kwargs[self.incident_url_kwarg])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["incident"] = self.incident
        return ctx

    def get_success_url(self):
        return reverse("incidents:incident-detail", args=[self.incident.pk])


class IncidentChildEditMixin:
    """The same contract for updating or deleting an existing child row.

    The parent is read off the row rather than from the URL, so an edit route
    cannot be pointed at another incident's child. ``scope_parent_lookup`` is
    **not** declared here on purpose : ``ScopeFilterMixin`` carries its own
    ``scope_parent_lookup = None`` class attribute, which wins on the MRO of
    every view that mixes both in, and the tenancy filter would then silently do
    nothing. Each view declares it explicitly instead.
    """

    @property
    def incident(self):
        return self.object.incident

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["incident"] = self.object.incident
        return ctx

    def get_success_url(self):
        return reverse("incidents:incident-detail", args=[self.object.incident_id])


# ══ Incident : the register ════════════════════════════════

INCIDENT_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": _state_options(INCIDENT_STATES)},
    {"param": "severity", "field": "severity", "label": _SEVERITY, "options": Criticality.choices},
    {"param": "category", "field": "category", "label": _l("Category"), "options": ThreatCategory.choices},
    {"param": "detection_source", "field": "detection_source", "label": _DETECTION_SOURCE, "options": DetectionSource.choices},
    {"param": "tlp", "field": "tlp", "label": _l("TLP"), "options": TrafficLightProtocol.choices},
]
INCIDENT_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Reference")},
    {"param": "title", "field": "title", "label": _l("Title")},
]
INCIDENT_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "title", "label": _l("Title"), "always": True},
    {"key": "severity", "label": _SEVERITY},
    {"key": "category", "label": _l("Category")},
    {"key": "status", "label": _l("Status")},
    {"key": "manager", "label": _l("Incident manager")},
    {"key": "detected_at", "label": _l("Detected at")},
    {"key": "obligations", "label": _l("Overdue obligations")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
INCIDENT_SORTABLE_FIELDS = {
    "reference": "reference",
    "title": "title",
    "severity": "severity",
    "category": "category",
    "status": "workflow_state",
    "manager": "incident_manager__last_name",
    "detected_at": "detected_at",
    "awareness_at": "awareness_at",
}
INCIDENT_SEARCH_FIELDS = ["reference", "title", "summary", "description"]


def _incident_queryset(qs):
    """Shared shaping for the register : joins, and the overdue-obligation flag.

    The flag is a filtered ``Count`` rather than a per-row property read : the
    register renders fifty rows and each of them would otherwise issue its own
    query for the obligations it owes.
    """
    return (
        qs.select_related("incident_manager", "response_plan", "origin_supplier")
        .prefetch_related("scopes", "tags")
        .annotate(
            overdue_obligation_count=Count(
                "notifications",
                filter=_overdue_notification_q("notifications__"),
                distinct=True,
            )
        )
    )


def _incident_list_kpis(base):
    """Rail tiles : the open register by severity, plus what is owed late."""
    if base is None:
        return []
    # RG-INC-17 : a drill runs through the real process and is excluded from
    # every KPI, so counting it here would inflate the one number an executive
    # reads off this page.
    # `.order_by()` before every aggregation and every subquery : the base
    # queryset arrives sorted and `.distinct()`-ed from the scope filter, and
    # PostgreSQL refuses a SELECT DISTINCT whose ORDER BY names a joined column
    # that is not in the select list - which "sort by incident manager" is.
    live = base.order_by().filter(is_exercise=False)
    open_incidents = live.filter(workflow_state__in=INCIDENT_ACTIVE_STATES)
    overdue = IncidentNotification.objects.filter(
        _overdue_notification_q(), incident__in=live.values("pk")
    )
    return [
        {
            "label": _("Open incidents"),
            "value": open_incidents.count(),
            "icon": "exclamation-octagon",
            "tone": "accent",
        },
        {
            "label": _("Critical"),
            "value": open_incidents.filter(severity=Criticality.CRITICAL).count(),
            "icon": "fire",
            "tone": "danger",
        },
        {
            "label": _("High"),
            "value": open_incidents.filter(severity=Criticality.HIGH).count(),
            "icon": "exclamation-triangle",
            "tone": "warning",
        },
        {
            "label": _("Overdue obligations"),
            "value": overdue.count(),
            "icon": "hourglass-bottom",
            "tone": "danger",
            "url": f"{reverse('incidents:notification-list')}?deadline=overdue",
        },
    ]


class IncidentListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    """The A.5.26 incident register."""

    model = Incident
    permission_required = "incidents.incident.read"
    filter_groups = INCIDENT_FILTER_GROUPS
    text_filters = INCIDENT_TEXT_FILTERS
    columns = INCIDENT_COLUMNS
    template_name = "incidents/incident_list.html"
    context_object_name = "incidents"
    paginate_by = PAGE_SIZE
    sortable_fields = INCIDENT_SORTABLE_FIELDS
    default_sort = "detected_at"
    default_sort_order = "desc"
    search_fields = INCIDENT_SEARCH_FIELDS

    def get_queryset(self):
        qs = _incident_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["list_kpis"] = _incident_list_kpis(getattr(self, "_summary_base_qs", None))
        return ctx


class IncidentTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Incident
    permission_required = "incidents.incident.read"
    template_name = "incidents/incident_table_body.html"
    context_object_name = "incidents"
    paginate_by = PAGE_SIZE
    sortable_fields = INCIDENT_SORTABLE_FIELDS
    default_sort = "detected_at"
    default_sort_order = "desc"
    search_fields = INCIDENT_SEARCH_FIELDS
    filter_groups = INCIDENT_FILTER_GROUPS
    text_filters = INCIDENT_TEXT_FILTERS

    def get_queryset(self):
        qs = _incident_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class IncidentDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    """The incident file : one page, one query budget.

    Everything the 2-column template renders is assembled here, because the page
    holds seven child collections and each of them would otherwise be walked
    per row : the chronology reads its corrections to know whether a line was
    superseded, the obligations read their recipient, and the evidence reads its
    source asset.
    """

    model = Incident
    permission_required = "incidents.incident.read"
    template_name = "incidents/incident_detail.html"
    context_object_name = "incident"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "incident_manager",
                "reporter",
                "response_plan",
                "origin_supplier",
                "parent_incident",
            )
            .prefetch_related(
                "scopes",
                "tags",
                # `outage_duration` is rendered beside each asset's declared
                # objectives verbatim, so both are needed on the same page.
                "affected_essential_assets",
                "affected_support_assets",
                "affected_suppliers",
                "affected_sites",
                "affected_activities",
                "threats",
                "exploited_vulnerabilities",
                "realised_risks",
                "linked_requirements",
                "source_events",
                "child_incidents",
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        incident = self.object
        user = self.request.user

        # --- Chronology : append-only, oldest first ------------------------
        ctx["timeline_entries"] = list(
            incident.timeline_entries.select_related(
                "author", "related_action", "related_evidence", "superseded_entry"
            )
            # `is_superseded` is a query per row; prefetching the corrections
            # answers it from memory for the whole card.
            .prefetch_related("corrections")
            .order_by("occurred_at", "recorded_at")
        )

        # --- Response actions ---------------------------------------------
        ctx["response_actions"] = list(
            incident.response_actions.select_related("owner", "performed_by").order_by(
                "due_at", "reference"
            )
        )

        # --- Evidence register --------------------------------------------
        ctx["evidence_items"] = list(
            incident.evidence_items.select_related(
                "collected_by", "source_support_asset"
            )
            .prefetch_related("tags")
            .order_by("collected_at", "reference")
        )

        # --- Regulatory obligations ---------------------------------------
        # Ordered by deadline with the undated ones last, so what is owed
        # soonest reads first and an obligation whose clock has not started is
        # never mistaken for one that has no deadline at all.
        notifications = list(
            incident.notifications.select_related(
                "authority", "recipient_stakeholder", "recipient_supplier", "depends_on"
            )
            .prefetch_related("filings")
            .order_by("due_at", "regime")
        )
        ctx["notifications"] = notifications
        ctx["overdue_notifications"] = [n for n in notifications if n.is_overdue]
        ctx["undecided_notifications"] = [n for n in notifications if n.is_undecided]

        # --- The two one-per-incident records ------------------------------
        # `filter().first()` and not the reverse accessor : a `OneToOneField`
        # raises `RelatedObjectDoesNotExist` when the row has not been created
        # yet, which is the normal state of an incident before triage.
        ctx["review"] = (
            PostIncidentReview.objects.filter(incident=incident)
            .select_related("facilitator", "response_plan", "effectiveness_reviewed_by")
            .prefetch_related("participants", "raised_findings", "corrective_action_plans")
            .first()
        )
        ctx["breach"] = (
            PersonalDataBreach.objects.filter(incident=incident)
            .select_related("lead_authority", "controller_supplier", "qualified_by")
            .first()
        )

        # --- Inline add forms, so the cards never leave the page -----------
        # Built here rather than fetched over HTMX on open : the chronology and
        # the response-action forms are the two things a responder reaches for
        # mid-incident, and a round trip to render an empty form is a round trip
        # spent during the window where delay is the harm. The permission check
        # is here only because building the form is Python work; every *button*
        # on the page is gated with `{% has_perm %}` in the template, which is
        # the house pattern and the one place that check should live.
        if user.has_perm("incidents.incident.update"):
            ctx["timeline_entry_form"] = IncidentTimelineEntryForm(
                incident=incident, author=user, user=user
            )
            ctx["response_action_form"] = IncidentResponseActionForm(
                incident=incident, user=user
            )
        return ctx


class IncidentCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    """Open an incident file.

    The row is created in ``draft`` and declared through the stepper : writing
    it straight into ``detected`` would leave no ``LifecycleEvent``, and the
    declaration is exactly the act the register exists to record.
    """

    model = Incident
    permission_required = "incidents.incident.create"
    form_class = IncidentForm
    template_name = "incidents/incident_form.html"
    modal_template_name = "incidents/incident_form_modal.html"
    modal_title_create = _l("New incident")
    modal_title_update = _l("Edit incident")

    def get_success_url(self):
        return reverse("incidents:incident-detail", args=[self.object.pk])


class IncidentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = Incident
    permission_required = "incidents.incident.update"
    form_class = IncidentForm
    template_name = "incidents/incident_form.html"
    modal_template_name = "incidents/incident_form_modal.html"
    modal_title_create = _l("New incident")
    modal_title_update = _l("Edit incident")

    def get_success_url(self):
        return reverse("incidents:incident-detail", args=[self.object.pk])


class IncidentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    model = Incident
    permission_required = "incidents.incident.delete"
    template_name = "incidents/incident_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("incidents:incident-list")


# ══ SecurityEvent : the A.6.8 intake ═══════════════════════
#
# The point of this page is the events that were NOT promoted : an auditor asks
# what was reported, what was concluded about it and who concluded it. The
# triage decision is therefore a first-class column, a first-class facet and a
# rail KPI, and the *awaiting assessment* count is the A.6.8 backlog.

SECURITY_EVENT_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": _state_options(SECURITY_EVENT_STATES)},
    {"param": "decision", "field": "triage_decision", "label": _TRIAGE_DECISION, "options": EventTriageDecision.choices},
    {"param": "event_class", "field": "event_class", "label": _l("Class"), "options": SecurityEventClass.choices},
    {"param": "category", "field": "category", "label": _l("Category"), "options": ThreatCategory.choices},
    {"param": "detection_source", "field": "detection_source", "label": _DETECTION_SOURCE, "options": DetectionSource.choices},
]
SECURITY_EVENT_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Reference")},
    {"param": "title", "field": "title", "label": _l("Title")},
    {"param": "source_reference", "field": "source_reference", "label": _l("Source reference")},
]
SECURITY_EVENT_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "title", "label": _l("Title"), "always": True},
    {"key": "event_class", "label": _l("Class")},
    {"key": "decision", "label": _TRIAGE_DECISION},
    {"key": "assessed_by", "label": _l("Assessed by")},
    {"key": "outcome", "label": _l("Promoted to")},
    {"key": "status", "label": _l("Status")},
    {"key": "reported_at", "label": _l("Reported at")},
    {"key": "delay", "label": _l("Reporting delay")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
SECURITY_EVENT_SORTABLE_FIELDS = {
    "reference": "reference",
    "title": "title",
    "event_class": "event_class",
    "decision": "triage_decision",
    "assessed_by": "assessed_by__last_name",
    "status": "workflow_state",
    "reported_at": "reported_at",
    "detected_at": "detected_at",
}
SECURITY_EVENT_SEARCH_FIELDS = ["reference", "title", "description", "source_reference"]


def _security_event_queryset(qs):
    return qs.select_related(
        "assessed_by", "reporter", "reported_by_supplier", "incident", "vulnerability", "duplicate_of"
    ).prefetch_related("scopes", "tags")


#: The three verdicts that close a report without an incident. Kept apart from
#: each other in the facet (an auditor asking why an event was not escalated
#: gets a different answer from *duplicate* and from *false positive*) but
#: counted together in the tile, because the question the tile answers is how
#: much of the intake was assessed and closed.
_NOT_PROMOTED_DECISIONS = [
    EventTriageDecision.DUPLICATE,
    EventTriageDecision.FALSE_POSITIVE,
    EventTriageDecision.NO_ACTION,
]


def _security_event_list_kpis(base):
    """Rail tiles : the backlog first, then what the assessment concluded.

    *Awaiting assessment* is the A.6.8 measure - a report nobody has looked at
    yet - and it is the reason this list exists as its own page.
    """
    if base is None:
        return []
    base = base.order_by()
    return [
        {
            "label": _("Awaiting assessment"),
            "value": base.filter(workflow_state=STEP_REPORTED).count(),
            "icon": "inbox",
            "tone": "warning",
            "url": f"{reverse('incidents:event-list')}?status={STEP_REPORTED}",
        },
        {
            "label": _("Under assessment"),
            "value": base.filter(workflow_state=STEP_UNDER_ASSESSMENT).count(),
            "icon": "search",
            "tone": "accent",
        },
        {
            "label": _("Promoted to incident"),
            "value": base.filter(triage_decision=EventTriageDecision.INCIDENT).count(),
            "icon": "arrow-up-right-circle",
            "tone": "danger",
        },
        {
            # The number this page exists for : what was reported, assessed and
            # deliberately not escalated. An auditor reads it before anything
            # else, and it links straight to the rows and their deciders.
            "label": _("Not promoted"),
            "value": base.filter(triage_decision__in=_NOT_PROMOTED_DECISIONS).count(),
            "icon": "slash-circle",
            "tone": "success",
            "url": "{}?{}".format(
                reverse("incidents:event-list"),
                urlencode([("decision", value) for value in _NOT_PROMOTED_DECISIONS]),
            ),
        },
    ]


class SecurityEventListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    """The A.5.25 / A.6.8 event intake and its recorded verdicts."""

    model = SecurityEvent
    permission_required = "incidents.event.read"
    filter_groups = SECURITY_EVENT_FILTER_GROUPS
    text_filters = SECURITY_EVENT_TEXT_FILTERS
    columns = SECURITY_EVENT_COLUMNS
    template_name = "incidents/security_event_list.html"
    context_object_name = "events"
    paginate_by = PAGE_SIZE
    sortable_fields = SECURITY_EVENT_SORTABLE_FIELDS
    default_sort = "reported_at"
    default_sort_order = "desc"
    search_fields = SECURITY_EVENT_SEARCH_FIELDS

    def get_queryset(self):
        qs = _security_event_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["list_kpis"] = _security_event_list_kpis(getattr(self, "_summary_base_qs", None))
        return ctx


class SecurityEventTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = SecurityEvent
    permission_required = "incidents.event.read"
    template_name = "incidents/security_event_table_body.html"
    context_object_name = "events"
    paginate_by = PAGE_SIZE
    sortable_fields = SECURITY_EVENT_SORTABLE_FIELDS
    default_sort = "reported_at"
    default_sort_order = "desc"
    search_fields = SECURITY_EVENT_SEARCH_FIELDS
    filter_groups = SECURITY_EVENT_FILTER_GROUPS
    text_filters = SECURITY_EVENT_TEXT_FILTERS

    def get_queryset(self):
        qs = _security_event_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class SecurityEventDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = SecurityEvent
    permission_required = "incidents.event.read"
    template_name = "incidents/security_event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "assessed_by",
                "reporter",
                "reported_by_supplier",
                "incident",
                "vulnerability",
                "duplicate_of",
            )
            .prefetch_related(
                "scopes",
                "tags",
                "affected_essential_assets",
                "affected_support_assets",
                "affected_sites",
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Reports that repeat this one. Shown because a duplicate chain is part
        # of why a single event was, or was not, escalated.
        ctx["duplicate_reports"] = list(self.object.duplicates.only("id", "reference", "title"))
        return ctx


class SecurityEventCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    model = SecurityEvent
    permission_required = "incidents.event.create"
    form_class = SecurityEventForm
    template_name = "incidents/security_event_form.html"
    modal_template_name = "incidents/security_event_form_modal.html"
    modal_title_create = _l("Report a security event")
    modal_title_update = _l("Edit security event")

    def get_success_url(self):
        return reverse("incidents:event-detail", args=[self.object.pk])


class SecurityEventUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = SecurityEvent
    permission_required = "incidents.event.update"
    form_class = SecurityEventForm
    template_name = "incidents/security_event_form.html"
    modal_template_name = "incidents/security_event_form_modal.html"
    modal_title_create = _l("Report a security event")
    modal_title_update = _l("Edit security event")

    def get_success_url(self):
        return reverse("incidents:event-detail", args=[self.object.pk])


class SecurityEventDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    model = SecurityEvent
    permission_required = "incidents.event.delete"
    template_name = "incidents/security_event_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("incidents:event-list")


# ══ IncidentResponsePlan : the A.5.24 procedure ════════════

RESPONSE_PLAN_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": DEFAULT_STATE_OPTIONS},
]
RESPONSE_PLAN_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Reference")},
    {"param": "name", "field": "name", "label": _l("Name")},
]
RESPONSE_PLAN_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "owner", "label": _l("Owner")},
    {"key": "effective_from", "label": _l("Effective from")},
    {"key": "review_date", "label": _l("Review date")},
    {"key": "last_exercise_date", "label": _l("Last exercise date")},
    {"key": "incidents", "label": pgettext_lazy("incident", "Incidents")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
RESPONSE_PLAN_SORTABLE_FIELDS = {
    "reference": "reference",
    "name": "name",
    "owner": "owner__last_name",
    "effective_from": "effective_from",
    "review_date": "review_date",
    "last_exercise_date": "last_exercise_date",
    "status": "workflow_state",
}
RESPONSE_PLAN_SEARCH_FIELDS = ["reference", "name", "purpose"]


def _response_plan_queryset(qs):
    return (
        qs.select_related("owner", "approved_by")
        .prefetch_related("scopes", "tags", "responsible_roles")
        .annotate(incident_count=Count("incidents", distinct=True))
    )


class ResponsePlanListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    """The incident response procedures, and how stale each one is.

    A plan past its review date and a plan more than twelve months without an
    exercise are both A.5.24 nonconformities waiting to be written up, so both
    are computed here and flagged on the row.
    """

    model = IncidentResponsePlan
    permission_required = "incidents.response_plan.read"
    filter_groups = RESPONSE_PLAN_FILTER_GROUPS
    text_filters = RESPONSE_PLAN_TEXT_FILTERS
    columns = RESPONSE_PLAN_COLUMNS
    template_name = "incidents/response_plan_list.html"
    context_object_name = "plans"
    paginate_by = PAGE_SIZE
    sortable_fields = RESPONSE_PLAN_SORTABLE_FIELDS
    default_sort = "name"
    search_fields = RESPONSE_PLAN_SEARCH_FIELDS

    def get_queryset(self):
        qs = _response_plan_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            base = base.order_by()
            today = timezone.localdate()
            # "In force" is exactly "counts in reports" on the default
            # lifecycle, read off the step flags rather than compared against a
            # state literal (RG-INC-37). Both figures are counted in SQL : the
            # equivalent model properties would walk the whole unpaginated list.
            in_force = base.filter(
                workflow_state__in=reportable_states(IncidentResponsePlan)
            )
            untested = in_force.filter(
                Q(last_exercise_date__isnull=True)
                | Q(last_exercise_date__lt=today - timedelta(days=EXERCISE_STALE_AFTER_DAYS))
            )
            ctx["list_kpis"] = [
                {"label": _("Plans"), "value": base.count(), "icon": "journal-text", "tone": "accent"},
                {
                    "label": _("In force"),
                    "value": in_force.count(),
                    "icon": "check-circle",
                    "tone": "success",
                },
                {
                    "label": _("Review overdue"),
                    "value": base.filter(review_date__lt=today).count(),
                    "icon": "calendar-x",
                    "tone": "warning",
                },
                {
                    # A plan never exercised is the worst case, not an exempt
                    # one : A.5.24 asks for a *tested* plan.
                    "label": _("Untested"),
                    "value": untested.count(),
                    "icon": "shield-exclamation",
                    "tone": "danger",
                },
            ]
        return ctx


class ResponsePlanTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = IncidentResponsePlan
    permission_required = "incidents.response_plan.read"
    template_name = "incidents/response_plan_table_body.html"
    context_object_name = "plans"
    paginate_by = PAGE_SIZE
    sortable_fields = RESPONSE_PLAN_SORTABLE_FIELDS
    default_sort = "name"
    search_fields = RESPONSE_PLAN_SEARCH_FIELDS
    filter_groups = RESPONSE_PLAN_FILTER_GROUPS
    text_filters = RESPONSE_PLAN_TEXT_FILTERS

    def get_queryset(self):
        qs = _response_plan_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class ResponsePlanDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = IncidentResponsePlan
    permission_required = "incidents.response_plan.read"
    template_name = "incidents/response_plan_detail.html"
    context_object_name = "plan"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("owner", "approved_by")
            .prefetch_related("scopes", "tags", "responsible_roles", "linked_requirements")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        plan = self.object
        # The incidents handled under this version of the procedure. Capped in
        # the sidebar and linked through to the filtered register, since a plan
        # in force for two years can carry hundreds.
        incidents = plan.incidents.select_related("incident_manager").order_by("-detected_at")
        ctx["handled_incidents"] = list(incidents[:10])
        ctx["handled_incident_count"] = incidents.count()
        # A ready-made advanced-filter rule, so the sidebar count links to the
        # real register rather than to a second, differently-filtered listing.
        ctx["handled_incidents_url"] = "{}?{}".format(
            reverse("incidents:incident-list"),
            urlencode(
                {
                    "rule": json.dumps(
                        {"f": "response_plan", "o": "in", "v": [str(plan.pk)]}
                    )
                }
            ),
        )
        return ctx


class ResponsePlanCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    model = IncidentResponsePlan
    permission_required = "incidents.response_plan.create"
    form_class = IncidentResponsePlanForm
    template_name = "incidents/response_plan_form.html"
    modal_template_name = "incidents/response_plan_form_modal.html"
    modal_title_create = _l("New response plan")
    modal_title_update = _l("Edit response plan")

    def get_success_url(self):
        return reverse("incidents:response-plan-detail", args=[self.object.pk])


class ResponsePlanUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = IncidentResponsePlan
    permission_required = "incidents.response_plan.update"
    form_class = IncidentResponsePlanForm
    template_name = "incidents/response_plan_form.html"
    modal_template_name = "incidents/response_plan_form_modal.html"
    modal_title_create = _l("New response plan")
    modal_title_update = _l("Edit response plan")

    def get_success_url(self):
        return reverse("incidents:response-plan-detail", args=[self.object.pk])


class ResponsePlanDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    model = IncidentResponsePlan
    permission_required = "incidents.response_plan.delete"
    template_name = "incidents/response_plan_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("incidents:response-plan-list")


# ══ Obligations due : the cross-cutting register ═══════════
#
# One question, asked across every incident at once : what do we owe, to whom,
# by when, and are we late. Sorted by `due_at` ascending, and the undecided
# obligations are surfaced rather than hidden - GDPR Art. 33(1) permits omission
# only on a judgement, and a judgement nobody made is not a judgement that
# concluded nothing is owed.

NOTIFICATION_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": _state_options(NOTIFICATION_STATES)},
    {"param": "decision", "field": "decision", "label": _DECISION, "options": NotificationDecision.choices},
    {"param": "regime", "field": "regime", "label": _l("Regime"), "options": NotificationRegime.choices},
    {"param": "recipient_kind", "field": "recipient_kind", "label": _l("Recipient"), "options": NotificationRecipientKind.choices},
    {"param": "channel", "field": "channel", "label": _l("Channel"), "options": NotificationChannel.choices},
    {"param": "anchor", "field": "clock_anchor", "label": _l("Clock anchor"), "options": ClockAnchor.choices},
]
NOTIFICATION_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Reference")},
    {"param": "obligation_reference", "field": "obligation_reference", "label": _l("Legal reference")},
    {"param": "incident", "field": "incident__reference", "label": _INCIDENT},
]
NOTIFICATION_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "incident", "label": _INCIDENT, "always": True},
    {"key": "regime", "label": _l("Regime")},
    {"key": "recipient", "label": _l("Recipient")},
    {"key": "decision", "label": _DECISION},
    {"key": "due_at", "label": _l("Due at")},
    {"key": "countdown", "label": _l("Time left")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
NOTIFICATION_SORTABLE_FIELDS = {
    "reference": "reference",
    "incident": "incident__reference",
    "regime": "regime",
    "recipient": "recipient_kind",
    "decision": "decision",
    "due_at": "due_at",
    "status": "workflow_state",
}
NOTIFICATION_SEARCH_FIELDS = [
    "reference",
    "obligation_reference",
    "recipient_name",
    "incident__reference",
    "incident__title",
]

#: The deadline facets the rail offers, as ``?deadline=<key>``. They are not
#: ``filter_groups`` entries because none of them is a field value : *overdue*
#: and *due in 24 h* are windows on a computed clock, and *pending* and *no
#: deadline* are the two undated buckets the module refuses to merge.
NOTIFICATION_DEADLINE_FACETS = {
    DEADLINE_BUCKET_DATED: _l("With a deadline"),
    DEADLINE_BUCKET_NO_DEADLINE: _l("No statutory deadline"),
    DEADLINE_BUCKET_PENDING: _l("Deadline pending"),
    "overdue": _l("Overdue"),
    "due24": _l("Due within 24 hours"),
    "undecided": _l("To decide"),
}


def _notification_queryset(qs):
    return qs.select_related(
        "incident",
        "authority",
        "recipient_stakeholder",
        "recipient_supplier",
        "depends_on",
        "template",
        "decided_by",
    ).prefetch_related("tags")


def _apply_deadline_facet(qs, value):
    """Narrow the obligation register to one deadline facet.

    Whitelisted rather than interpreted : the key comes from the query string,
    and an unknown one narrows nothing instead of raising.
    """
    now = timezone.now()
    if value == "overdue":
        return qs.filter(_overdue_notification_q())
    if value == "due24":
        return qs.filter(
            due_at__gte=now,
            due_at__lte=now + timedelta(hours=24),
            sent_at__isnull=True,
            workflow_state__in=NOTIFICATION_ACTIVE_STATES,
        )
    if value == "undecided":
        return qs.filter(decision=NotificationDecision.UNDECIDED)
    if value == DEADLINE_BUCKET_DATED:
        return qs.filter(due_at__isnull=False)
    if value == DEADLINE_BUCKET_NO_DEADLINE:
        return qs.filter(no_fixed_deadline=True)
    if value == DEADLINE_BUCKET_PENDING:
        return qs.filter(due_at__isnull=True, no_fixed_deadline=False)
    return qs


class _NotificationFacetMixin:
    """Shared deadline facet handling for the list page and its table body."""

    def deadline_facet(self):
        value = self.request.GET.get("deadline", "")
        return value if value in NOTIFICATION_DEADLINE_FACETS else ""

    def apply_facets(self, qs):
        facet = self.deadline_facet()
        return _apply_deadline_facet(qs, facet) if facet else qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        current = self.deadline_facet()
        ctx["deadline_facet"] = current
        ctx["deadline_facets"] = [
            {"value": key, "label": label, "active": key == current}
            for key, label in NOTIFICATION_DEADLINE_FACETS.items()
        ]
        return ctx


class NotificationListView(_NotificationFacetMixin, LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    """What the organisation owes, to whom, by when, and whether it is late.

    Sorted by ``due_at`` ascending by default, so the soonest duty reads first.
    The rows carrying no date are **not** filtered out : an obligation whose
    clock has not started yet is not the same thing as one that has no deadline
    in law, and neither is the same as one already past. The three are told
    apart through the ``?deadline=`` facets rather than by where the database
    happens to sort a NULL, which differs by backend.
    """

    model = IncidentNotification
    permission_required = "incidents.notification.read"
    scope_parent_lookup = "incident__scopes"
    filter_groups = NOTIFICATION_FILTER_GROUPS
    text_filters = NOTIFICATION_TEXT_FILTERS
    columns = NOTIFICATION_COLUMNS
    template_name = "incidents/notification_list.html"
    context_object_name = "notifications"
    paginate_by = PAGE_SIZE
    sortable_fields = NOTIFICATION_SORTABLE_FIELDS
    default_sort = "due_at"
    search_fields = NOTIFICATION_SEARCH_FIELDS

    def get_queryset(self):
        qs = _notification_queryset(super().get_queryset())
        qs = self.apply_facets(qs)
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            # RG-INC-17 : an exercise never instantiates a regulatory
            # obligation, so nothing here needs excluding - but the filter is
            # stated rather than assumed, since a hand-added obligation on a
            # drill would otherwise be counted as a real duty.
            live = base.order_by().filter(incident__is_exercise=False)
            undecided = live.filter(decision=NotificationDecision.UNDECIDED)
            overdue = live.filter(_overdue_notification_q())
            ctx["list_kpis"] = [
                {
                    "label": _("To decide"),
                    "value": undecided.count(),
                    "icon": "question-octagon",
                    "tone": "warning",
                    "url": f"{reverse('incidents:notification-list')}?deadline=undecided",
                },
                {
                    "label": _("Overdue"),
                    "value": overdue.count(),
                    "icon": "hourglass-bottom",
                    "tone": "danger",
                    "url": f"{reverse('incidents:notification-list')}?deadline=overdue",
                },
                {
                    "label": _("Due within 24 hours"),
                    "value": _apply_deadline_facet(live, "due24").count(),
                    "icon": "alarm",
                    "tone": "warning",
                    "url": f"{reverse('incidents:notification-list')}?deadline=due24",
                },
                {
                    "label": _("Filed late"),
                    "value": live.filter(late_by__isnull=False).count(),
                    "icon": "exclamation-diamond",
                    "tone": "danger",
                },
            ]
        return ctx


class NotificationTableBodyView(_NotificationFacetMixin, LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = IncidentNotification
    permission_required = "incidents.notification.read"
    scope_parent_lookup = "incident__scopes"
    template_name = "incidents/notification_table_body.html"
    context_object_name = "notifications"
    paginate_by = PAGE_SIZE
    sortable_fields = NOTIFICATION_SORTABLE_FIELDS
    default_sort = "due_at"
    search_fields = NOTIFICATION_SEARCH_FIELDS
    filter_groups = NOTIFICATION_FILTER_GROUPS
    text_filters = NOTIFICATION_TEXT_FILTERS

    def get_queryset(self):
        qs = _notification_queryset(super().get_queryset())
        qs = self.apply_facets(qs)
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class NotificationDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    """One obligation : the duty, the decision, and the filings that discharged it."""

    model = IncidentNotification
    permission_required = "incidents.notification.read"
    scope_parent_lookup = "incident__scopes"
    template_name = "incidents/notification_detail.html"
    context_object_name = "notification"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "incident",
                "authority",
                "recipient_stakeholder",
                "recipient_supplier",
                "template",
                "depends_on",
                "decided_by",
                "sent_by",
                "proof_evidence",
            )
            .prefetch_related("tags", "dependents")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obligation = self.object
        ctx["filings"] = _notification_filings(obligation)
        # The filings partial builds the completion control from this.
        # Without it the <select> renders with zero options and, being
        # required, cannot be submitted at all on first page load.
        ctx["filing_outcomes"] = FilingOutcome.choices
        ctx["authority"] = obligation.authority
        if self.request.user.has_perm("incidents.notification.update"):
            # Pre-filled from the obligation, so recording a filing is one form
            # and not a transcription exercise.
            ctx["filing_form"] = NotificationFilingForm(
                notification=obligation,
                submitted_by=self.request.user,
                user=self.request.user,
                initial={
                    "submitted_at": timezone.now(),
                    "channel": obligation.channel or None,
                    "recipient_name": obligation.recipient_display,
                    "content": obligation.content,
                },
            )
        return ctx


class NotificationCreateView(LoginRequiredMixin, PermissionRequiredMixin, IncidentChildMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    """Add an obligation by hand to an incident.

    Only ever produces a ``manual`` row : a generated obligation is created by
    the triage transition and is answered through a decision, never typed in.
    """

    model = IncidentNotification
    permission_required = "incidents.notification.create"
    form_class = IncidentNotificationForm
    template_name = "incidents/notification_form.html"
    modal_template_name = "incidents/notification_form_modal.html"
    modal_title_create = _l("Add a notification obligation")
    modal_title_update = _l("Edit notification obligation")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["incident"] = self.incident
        return kwargs


class NotificationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, IncidentChildEditMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = IncidentNotification
    permission_required = "incidents.notification.update"
    scope_parent_lookup = "incident__scopes"
    form_class = IncidentNotificationForm
    template_name = "incidents/notification_form.html"
    modal_template_name = "incidents/notification_form_modal.html"
    modal_title_create = _l("Add a notification obligation")
    modal_title_update = _l("Edit notification obligation")

    def get_success_url(self):
        return reverse("incidents:notification-detail", args=[self.object.pk])


class NotificationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, IncidentChildEditMixin, ProtectedDeleteMixin, DeleteView):
    """Delete a hand-added obligation.

    A generated one refuses deletion from the model layer : it is answered
    through ``not_required`` with a written rationale, because deleting it
    destroys the evidence that the regime was considered at all. The refusal is
    surfaced as a message by :class:`ProtectedDeleteMixin`.
    """

    model = IncidentNotification
    permission_required = "incidents.notification.delete"
    scope_parent_lookup = "incident__scopes"
    template_name = "incidents/notification_confirm_delete_modal.html"


class NotificationProofDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Stream the obligation's proof of filing, scope- and permission-checked."""

    permission_required = "incidents.notification.read"

    def get(self, request, pk):
        obligation = _scoped_get(
            IncidentNotification, request, pk, parent_lookup="incident__scopes"
        )
        data = obligation.get_proof_bytes()
        if not data:
            raise Http404()
        response = HttpResponse(data, content_type="application/octet-stream")
        response["Content-Disposition"] = _attachment_disposition(
            obligation.proof_filename_display or f"{obligation.reference}.bin"
        )
        return response


# ══ Chronology : append-only ═══════════════════════════════
#
# Create and nothing else. `IncidentTimelineEntry.delete()` refuses outright and
# an entry is corrected by a later one that supersedes it, so an edit or a
# delete affordance here would be a button that always fails.


def _timeline_entries(incident):
    return list(
        incident.timeline_entries.select_related(
            "author", "related_action", "related_evidence", "superseded_entry"
        )
        .prefetch_related("corrections")
        .order_by("occurred_at", "recorded_at")
    )


class TimelineEntryCreateView(LoginRequiredMixin, PermissionRequiredMixin, IncidentChildMixin, HtmxFormMixin, UserFormKwargsMixin, CreateView):
    model = IncidentTimelineEntry
    permission_required = "incidents.incident.update"
    form_class = IncidentTimelineEntryForm
    template_name = "incidents/timeline_entry_form.html"
    modal_template_name = "incidents/timeline_entry_form_modal.html"
    modal_title_create = _l("Add a chronology entry")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["incident"] = self.incident
        kwargs["author"] = self.request.user
        return kwargs


class TimelineEntriesPartialView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Re-render the ``#timeline-entries`` card after an append."""

    permission_required = "incidents.incident.read"

    def get(self, request, pk):
        incident = _scoped_get(Incident, request, pk)
        html = render_to_string(
            "incidents/_timeline_entries.html",
            {
                "incident": incident,
                "timeline_entries": _timeline_entries(incident),
                "timeline_entry_form": (
                    IncidentTimelineEntryForm(
                        incident=incident, author=request.user, user=request.user
                    )
                    if request.user.has_perm("incidents.incident.update")
                    else None
                ),
            },
            request=request,
        )
        return HttpResponse(html)


# ══ Response actions ═══════════════════════════════════════


def _response_actions(incident):
    return list(
        incident.response_actions.select_related("owner", "performed_by").order_by(
            "due_at", "reference"
        )
    )


class ResponseActionCreateView(LoginRequiredMixin, PermissionRequiredMixin, IncidentChildMixin, HtmxFormMixin, UserFormKwargsMixin, CreateView):
    model = IncidentResponseAction
    permission_required = "incidents.incident.update"
    form_class = IncidentResponseActionForm
    template_name = "incidents/response_action_form.html"
    modal_template_name = "incidents/response_action_form_modal.html"
    modal_title_create = _l("Add a response action")
    modal_title_update = _l("Edit response action")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["incident"] = self.incident
        return kwargs


class ResponseActionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, IncidentChildEditMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = IncidentResponseAction
    permission_required = "incidents.incident.update"
    scope_parent_lookup = "incident__scopes"
    form_class = IncidentResponseActionForm
    template_name = "incidents/response_action_form.html"
    modal_template_name = "incidents/response_action_form_modal.html"
    modal_title_create = _l("Add a response action")
    modal_title_update = _l("Edit response action")


class ResponseActionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, IncidentChildEditMixin, ProtectedDeleteMixin, DeleteView):
    model = IncidentResponseAction
    permission_required = "incidents.incident.update"
    scope_parent_lookup = "incident__scopes"
    template_name = "incidents/response_action_confirm_delete_modal.html"


class ResponseActionsPartialView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Re-render the ``#response-actions`` card after an add or an edit."""

    permission_required = "incidents.incident.read"

    def get(self, request, pk):
        incident = _scoped_get(Incident, request, pk)
        html = render_to_string(
            "incidents/_response_actions.html",
            {
                "incident": incident,
                "response_actions": _response_actions(incident),
                "response_action_form": (
                    IncidentResponseActionForm(incident=incident, user=request.user)
                    if request.user.has_perm("incidents.incident.update")
                    else None
                ),
            },
            request=request,
        )
        return HttpResponse(html)


# ══ Evidence (A.5.28) ══════════════════════════════════════
#
# No standalone register page in this layer : evidence is reached from the
# incident it belongs to. It still needs a detail page of its own, because that
# is where its lifecycle stepper lives and a sealed artefact is released,
# destroyed or moved into retention through nothing else.


class EvidenceDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    """One artefact : how it was acquired, whether it still matches, who held it."""

    model = IncidentEvidence
    permission_required = "incidents.evidence.read"
    scope_parent_lookup = "incident__scopes"
    template_name = "incidents/evidence_detail.html"
    context_object_name = "evidence"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "incident", "collected_by", "source_support_asset", "destruction_authorised_by"
            )
            .prefetch_related("tags")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        item = self.object
        ctx["custody_events"] = _custody_events(item)
        if self.request.user.has_perm("incidents.evidence.update"):
            ctx["custody_form"] = EvidenceCustodyEventForm(
                evidence=item, actor=self.request.user, user=self.request.user
            )
        return ctx


class EvidenceCreateView(LoginRequiredMixin, PermissionRequiredMixin, IncidentChildMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    model = IncidentEvidence
    permission_required = "incidents.evidence.create"
    form_class = IncidentEvidenceForm
    template_name = "incidents/evidence_form.html"
    modal_template_name = "incidents/evidence_form_modal.html"
    modal_title_create = _l("Register an evidence item")
    modal_title_update = _l("Edit evidence item")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["incident"] = self.incident
        kwargs["collected_by"] = self.request.user
        return kwargs


class EvidenceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, IncidentChildEditMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    """Edit an evidence item.

    Once the item is sealed the form disables the six acquisition fields itself,
    so the write-once guard in ``save()`` - which raises rather than validating -
    can never be reached from this route.
    """

    model = IncidentEvidence
    permission_required = "incidents.evidence.update"
    scope_parent_lookup = "incident__scopes"
    form_class = IncidentEvidenceForm
    template_name = "incidents/evidence_form.html"
    modal_template_name = "incidents/evidence_form_modal.html"
    modal_title_create = _l("Register an evidence item")
    modal_title_update = _l("Edit evidence item")

    def get_success_url(self):
        return reverse("incidents:evidence-detail", args=[self.object.pk])


class EvidenceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, IncidentChildEditMixin, ProtectedDeleteMixin, DeleteView):
    """Remove an item registered in error, while it is still a draft.

    Destruction of a real artefact is a gated transition with a confirmation and
    an approval, never this route : the model refuses deletion from any step
    past ``draft``.
    """

    model = IncidentEvidence
    permission_required = "incidents.evidence.delete"
    scope_parent_lookup = "incident__scopes"
    template_name = "incidents/evidence_confirm_delete_modal.html"


class EvidenceFileDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Stream the stored artefact, scope- and permission-checked.

    Never a raw media URL : an evidence file carries the incident's TLP caveat,
    and a guessable path would put a TLP:RED artefact one URL away from anyone.
    """

    permission_required = "incidents.evidence.read"

    def get(self, request, pk):
        item = _scoped_get(
            IncidentEvidence, request, pk, parent_lookup="incident__scopes"
        )
        if not item.has_file:
            raise Http404()
        try:
            handle = item.file.open("rb")
        except (FileNotFoundError, OSError):
            # The register may legitimately outlive its media volume. A missing
            # artefact is a 404, never a traceback naming the storage path.
            raise Http404() from None
        with handle:
            data = handle.read()
        response = HttpResponse(data, content_type="application/octet-stream")
        response["Content-Disposition"] = _attachment_disposition(
            item.original_filename or f"{item.reference}.bin"
        )
        return response


class EvidenceVerifyIntegrityView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Re-measure the artefact and append the ledger row.

    Not a lifecycle transition : verification does not move the item, it records
    a measurement. The three-way outcome is the model's, verbatim - a match, a
    mismatch, and an artefact that could not be read at all, which is a claim
    about the infrastructure and never about the evidence.
    """

    permission_required = "incidents.evidence.update"

    def post(self, request, pk):
        item = _scoped_get(
            IncidentEvidence, request, pk, parent_lookup="incident__scopes"
        )
        outcome = item.verify_integrity(
            request.user, notes=request.POST.get("notes", "").strip()
        )
        if outcome == VERIFICATION_MATCH:
            messages.success(
                request,
                _("Integrity verified : the artefact matches its recorded digest."),
            )
        elif outcome == VERIFICATION_MISMATCH:
            messages.error(
                request,
                _(
                    "Integrity check failed : the artefact no longer matches its "
                    "recorded digest."
                ),
            )
        else:
            # Deliberately a warning and not an error : an unreadable artefact
            # is a claim about the storage, never about the evidence.
            messages.warning(
                request,
                _(
                    "Integrity could not be verified : the artefact could not be "
                    "read. Check its storage location."
                ),
            )
        return redirect("incidents:evidence-detail", pk=item.pk)


# ══ Chain of custody : append-only ═════════════════════════


def _custody_events(evidence):
    return list(
        evidence.custody_events.select_related("actor").order_by(
            "occurred_at", "recorded_at"
        )
    )


class CustodyEventCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, CreateView):
    """Record one handling act on an evidence item.

    Create only : the ledger is append-only and its model has neither an update
    nor a delete route on any surface. The form offers the four acts a human
    attests to; the rest are appended by the item's own transitions.
    """

    model = EvidenceCustodyEvent
    permission_required = "incidents.evidence.update"
    form_class = EvidenceCustodyEventForm
    template_name = "incidents/custody_event_form.html"
    modal_template_name = "incidents/custody_event_form_modal.html"
    modal_title_create = _l("Record a custody act")

    @cached_property
    def evidence(self):
        return _scoped_get(
            IncidentEvidence,
            self.request,
            self.kwargs["evidence_pk"],
            parent_lookup="incident__scopes",
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["evidence"] = self.evidence
        kwargs["actor"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["evidence"] = self.evidence
        ctx["incident"] = self.evidence.incident
        return ctx

    def get_success_url(self):
        return reverse("incidents:evidence-detail", args=[self.evidence.pk])


class CustodyEventsPartialView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Re-render the ``#custody-events`` card after an append."""

    permission_required = "incidents.evidence.read"

    def get(self, request, pk):
        item = _scoped_get(
            IncidentEvidence, request, pk, parent_lookup="incident__scopes"
        )
        html = render_to_string(
            "incidents/_custody_events.html",
            {
                "evidence": item,
                "custody_events": _custody_events(item),
                "custody_form": (
                    EvidenceCustodyEventForm(
                        evidence=item, actor=request.user, user=request.user
                    )
                    if request.user.has_perm("incidents.evidence.update")
                    else None
                ),
            },
            request=request,
        )
        return HttpResponse(html)


# ══ Notification filings : append-only ═════════════════════


def _notification_filings(notification):
    return list(
        notification.filings.select_related("submitted_by", "supersedes")
        .prefetch_related("superseded_by")
        .order_by("submitted_at")
    )


class FilingCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, CreateView):
    """Record that a notification actually left the organisation.

    Needs ``update`` and not ``approve`` (RG-INC-26) : the governed decision is
    whether the duty exists, not the clerical act of transmitting the filing.
    Create only - an amendment is a further filing, never a rewrite.
    """

    model = NotificationFiling
    permission_required = "incidents.notification.update"
    form_class = NotificationFilingForm
    template_name = "incidents/filing_form.html"
    modal_template_name = "incidents/filing_form_modal.html"
    modal_title_create = _l("Record a filing")

    @cached_property
    def notification(self):
        return _scoped_get(
            IncidentNotification,
            self.request,
            self.kwargs["notification_pk"],
            parent_lookup="incident__scopes",
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["notification"] = self.notification
        kwargs["submitted_by"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        obligation = self.notification
        initial.setdefault("submitted_at", timezone.now())
        initial.setdefault("channel", obligation.channel or None)
        initial.setdefault("recipient_name", obligation.recipient_display)
        initial.setdefault("content", obligation.content)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["notification"] = self.notification
        ctx["incident"] = self.notification.incident
        return ctx

    def get_success_url(self):
        return reverse("incidents:notification-detail", args=[self.notification.pk])


class FilingOutcomeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Record the recipient's answer on a filing, once.

    The narrow completion exception : what was transmitted never changes because
    of the answer, so this posts through ``record_outcome()`` - the model's one
    implementation of what may be written after the insert - rather than through
    a form that could reopen the content.
    """

    permission_required = "incidents.notification.update"

    def post(self, request, pk):
        filing = _scoped_get(
            NotificationFiling,
            request,
            pk,
            parent_lookup="notification__incident__scopes",
        )
        outcome = request.POST.get("outcome", "")
        if outcome not in FilingOutcome.values:
            messages.error(request, _("Unknown filing outcome."))
            return redirect("incidents:notification-detail", pk=filing.notification_id)
        reference = request.POST.get("external_reference", "").strip()
        # Only an acknowledgement carries an acknowledgement timestamp : a
        # rejection and an information request are answers too, and stamping
        # them as acknowledged would record a receipt that never happened.
        acknowledged_at = (
            timezone.now() if outcome == FilingOutcome.ACKNOWLEDGED else None
        )
        try:
            filing.record_outcome(
                outcome=outcome,
                acknowledged_at=acknowledged_at,
                external_reference=reference or None,
            )
        # LifecycleProtectedError is a bare Exception, not a ValidationError :
        # a double-click or a back-and-resubmit on an already-completed
        # filing would otherwise be a 500 with a traceback.
        except (ValidationError, ValueError, LifecycleProtectedError) as exc:
            messages.error(request, _("This outcome could not be recorded : %(error)s") % {"error": exc})
        else:
            messages.success(request, _("The filing outcome has been recorded."))
        return redirect("incidents:notification-detail", pk=filing.notification_id)


class FilingProofDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Stream a filing's proof document, scope- and permission-checked."""

    permission_required = "incidents.notification.read"

    def get(self, request, pk):
        filing = _scoped_get(
            NotificationFiling,
            request,
            pk,
            parent_lookup="notification__incident__scopes",
        )
        data = filing.get_proof_bytes()
        if not data:
            raise Http404()
        response = HttpResponse(data, content_type="application/octet-stream")
        response["Content-Disposition"] = _attachment_disposition(
            filing.proof_filename or f"{filing.reference}.bin"
        )
        return response


class FilingsPartialView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Re-render the ``#notification-filings`` table after a filing."""

    permission_required = "incidents.notification.read"

    def get(self, request, pk):
        obligation = _scoped_get(
            IncidentNotification, request, pk, parent_lookup="incident__scopes"
        )
        html = render_to_string(
            "incidents/_notification_filings.html",
            {
                "notification": obligation,
                "filings": _notification_filings(obligation),
                "filing_outcomes": FilingOutcome.choices,
            },
            request=request,
        )
        return HttpResponse(html)


# ══ Post-incident review (A.5.27) ══════════════════════════


class PostIncidentReviewDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = PostIncidentReview
    permission_required = "incidents.review.read"
    template_name = "incidents/review_detail.html"
    context_object_name = "review"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "incident", "response_plan", "facilitator", "effectiveness_reviewed_by"
            )
            .prefetch_related(
                "scopes",
                "tags",
                "participants",
                "raised_findings",
                "corrective_action_plans",
                "failed_controls",
                "controls_to_strengthen",
                "identified_risks",
                "identified_vulnerabilities",
                "isms_changes",
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        review = self.object
        ctx["incident"] = review.incident
        # Rendered side by side with the facilitator so self-verification is
        # visible rather than inferred.
        ctx["is_self_verified"] = (
            review.effectiveness_reviewed_by_id is not None
            and review.effectiveness_reviewed_by_id == review.facilitator_id
        )
        return ctx


class PostIncidentReviewCreateView(LoginRequiredMixin, PermissionRequiredMixin, IncidentChildMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    """Open the A.5.27 review by hand.

    The incident's own ``post_incident_review`` transition creates one
    automatically; this route exists for the review scheduled ahead of that
    step. Exactly one review per incident, enforced by a ``OneToOneField``.
    """

    model = PostIncidentReview
    permission_required = "incidents.review.create"
    form_class = PostIncidentReviewForm
    template_name = "incidents/review_form.html"
    modal_template_name = "incidents/review_form_modal.html"
    modal_title_create = _l("Open the post-incident review")
    modal_title_update = _l("Edit the post-incident review")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["incident"] = self.incident
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        # RG-INC-31 : the review's tenancy is the incident's, and the incident's
        # save realigns it on every write. Setting it here means the row is
        # correctly scoped from its first instant rather than from the next
        # incident edit.
        self.object.scopes.set(self.incident.scopes.all())
        return response


class PostIncidentReviewUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = PostIncidentReview
    permission_required = "incidents.review.update"
    form_class = PostIncidentReviewForm
    template_name = "incidents/review_form.html"
    modal_template_name = "incidents/review_form_modal.html"
    modal_title_create = _l("Open the post-incident review")
    modal_title_update = _l("Edit the post-incident review")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["incident"] = self.object.incident
        return ctx

    def get_success_url(self):
        return reverse("incidents:review-detail", args=[self.object.pk])


class PostIncidentReviewDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    """Remove a review opened in error, while its incident is already over.

    The model refuses to delete a review whose incident is still open : the
    incident could then never be closed and could never obtain a second review.
    """

    model = PostIncidentReview
    permission_required = "incidents.review.delete"
    template_name = "incidents/review_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("incidents:incident-detail", args=[self.object.incident_id])


# ══ Personal data breach : the GDPR qualification ══════════
#
# No top-level register : a breach is always a qualification *of* an incident,
# and a separate list would invite the two to drift. It is reached from the
# incident page and has its own detail view for the DPO's working view.


class PersonalDataBreachDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = PersonalDataBreach
    permission_required = "incidents.notification.read"
    scope_parent_lookup = "incident__scopes"
    template_name = "incidents/breach_detail.html"
    context_object_name = "breach"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "incident", "lead_authority", "controller_supplier", "qualified_by"
            )
            .prefetch_related("tags")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        breach = self.object
        ctx["incident"] = breach.incident
        # The obligations this verdict produced, so the qualification page shows
        # what it actually caused rather than asserting it in prose.
        ctx["generated_notifications"] = list(
            breach.incident.notifications.select_related(
                "authority", "recipient_supplier", "recipient_stakeholder"
            ).order_by("due_at", "regime")
        )
        return ctx


class PersonalDataBreachCreateView(LoginRequiredMixin, PermissionRequiredMixin, IncidentChildMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    """Open the GDPR qualification by hand.

    Triage opens one automatically as soon as the incident declares personal
    data. This route covers the qualification opened before triage, and the one
    an incident acquires when the flag is set later.
    """

    model = PersonalDataBreach
    permission_required = "incidents.notification.create"
    form_class = PersonalDataBreachForm
    template_name = "incidents/breach_form.html"
    modal_template_name = "incidents/breach_form_modal.html"
    modal_title_create = _l("Open the personal data qualification")
    modal_title_update = _l("Edit the personal data qualification")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["incident"] = self.incident
        return kwargs


class PersonalDataBreachUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, IncidentChildEditMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = PersonalDataBreach
    permission_required = "incidents.notification.update"
    scope_parent_lookup = "incident__scopes"
    form_class = PersonalDataBreachForm
    template_name = "incidents/breach_form.html"
    modal_template_name = "incidents/breach_form_modal.html"
    modal_title_create = _l("Open the personal data qualification")
    modal_title_update = _l("Edit the personal data qualification")

    def get_success_url(self):
        return reverse("incidents:breach-detail", args=[self.object.pk])


class PersonalDataBreachDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, IncidentChildEditMixin, ProtectedDeleteMixin, DeleteView):
    model = PersonalDataBreach
    permission_required = "incidents.notification.delete"
    scope_parent_lookup = "incident__scopes"
    template_name = "incidents/breach_confirm_delete_modal.html"


# ══ Catalogue : the regulatory configuration ═══════════════
#
# Neither entity carries `scopes` nor a `scope_parent_lookup`, and neither view
# below mixes in `ScopeFilterMixin`. That is a decision, not the oversight the
# rest of the module guards against : the CNIL is the CNIL for every scope of
# the ISMS, and a per-perimeter copy of the authority catalogue would drift.

REPORTING_AUTHORITY_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": DEFAULT_STATE_OPTIONS},
    {"param": "type", "field": "authority_type", "label": _l("Type"), "options": AuthorityType.choices},
    {"param": "regime", "field": "primary_regime", "label": _l("Primary regime"), "options": NotificationRegime.choices},
]
REPORTING_AUTHORITY_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
    {"param": "jurisdiction", "field": "jurisdiction_country", "label": _l("Jurisdiction")},
]
REPORTING_AUTHORITY_COLUMNS = [
    {"key": "short_name", "label": _l("Short name"), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "type", "label": _l("Type")},
    {"key": "regime", "label": _l("Primary regime")},
    {"key": "jurisdiction", "label": _l("Jurisdiction")},
    {"key": "templates", "label": _l("Templates")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
REPORTING_AUTHORITY_SORTABLE_FIELDS = {
    "short_name": "short_name",
    "name": "name",
    "type": "authority_type",
    "regime": "primary_regime",
    "jurisdiction": "jurisdiction_country",
    "status": "workflow_state",
}
REPORTING_AUTHORITY_SEARCH_FIELDS = ["reference", "name", "short_name", "jurisdiction_country"]


def _authority_queryset(qs):
    return qs.prefetch_related("tags").annotate(
        template_count=Count("obligation_templates", distinct=True),
        obligation_count=Count("obligations", distinct=True),
    )


class ReportingAuthorityListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = ReportingAuthority
    permission_required = "incidents.response_plan.read"
    filter_groups = REPORTING_AUTHORITY_FILTER_GROUPS
    text_filters = REPORTING_AUTHORITY_TEXT_FILTERS
    columns = REPORTING_AUTHORITY_COLUMNS
    template_name = "incidents/reporting_authority_list.html"
    context_object_name = "authorities"
    paginate_by = PAGE_SIZE
    sortable_fields = REPORTING_AUTHORITY_SORTABLE_FIELDS
    default_sort = "name"
    search_fields = REPORTING_AUTHORITY_SEARCH_FIELDS

    def get_queryset(self):
        qs = _authority_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class ReportingAuthorityTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, SortableListMixin, ListView):
    model = ReportingAuthority
    permission_required = "incidents.response_plan.read"
    template_name = "incidents/reporting_authority_table_body.html"
    context_object_name = "authorities"
    paginate_by = PAGE_SIZE
    sortable_fields = REPORTING_AUTHORITY_SORTABLE_FIELDS
    default_sort = "name"
    search_fields = REPORTING_AUTHORITY_SEARCH_FIELDS
    filter_groups = REPORTING_AUTHORITY_FILTER_GROUPS
    text_filters = REPORTING_AUTHORITY_TEXT_FILTERS

    def get_queryset(self):
        qs = _authority_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class ReportingAuthorityDetailView(LoginRequiredMixin, PermissionRequiredMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = ReportingAuthority
    permission_required = "incidents.response_plan.read"
    template_name = "incidents/reporting_authority_detail.html"
    context_object_name = "authority"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("tags")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        authority = self.object
        ctx["templates"] = list(
            authority.obligation_templates.order_by("regime", "order", "name")
        )
        ctx["obligation_count"] = authority.obligations.count()
        ctx["obligations_url"] = f"{reverse('incidents:notification-list')}?q={quote(authority.short_name or authority.name)}"
        return ctx


class ReportingAuthorityCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    model = ReportingAuthority
    permission_required = "incidents.response_plan.create"
    form_class = ReportingAuthorityForm
    template_name = "incidents/reporting_authority_form.html"
    modal_template_name = "incidents/reporting_authority_form_modal.html"
    modal_title_create = _l("New reporting authority")
    modal_title_update = _l("Edit reporting authority")

    def get_success_url(self):
        return reverse("incidents:reporting-authority-detail", args=[self.object.pk])


class ReportingAuthorityUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = ReportingAuthority
    permission_required = "incidents.response_plan.update"
    form_class = ReportingAuthorityForm
    template_name = "incidents/reporting_authority_form.html"
    modal_template_name = "incidents/reporting_authority_form_modal.html"
    modal_title_create = _l("New reporting authority")
    modal_title_update = _l("Edit reporting authority")

    def get_success_url(self):
        return reverse("incidents:reporting-authority-detail", args=[self.object.pk])


class ReportingAuthorityDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ProtectedDeleteMixin, DeleteView):
    model = ReportingAuthority
    permission_required = "incidents.response_plan.delete"
    template_name = "incidents/reporting_authority_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("incidents:reporting-authority-list")


OBLIGATION_TEMPLATE_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": DEFAULT_STATE_OPTIONS},
    {"param": "regime", "field": "regime", "label": _l("Regime"), "options": NotificationRegime.choices},
    {"param": "recipient_kind", "field": "recipient_kind", "label": _l("Recipient"), "options": NotificationRecipientKind.choices},
    {"param": "anchor", "field": "clock_anchor", "label": _l("Clock anchor"), "options": ClockAnchor.choices},
    {"param": "min_severity", "field": "min_severity", "label": pgettext_lazy("incident", "Minimum severity"), "options": Criticality.choices},
]
OBLIGATION_TEMPLATE_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
    {"param": "legal_reference", "field": "legal_reference", "label": _l("Legal reference")},
]
OBLIGATION_TEMPLATE_COLUMNS = [
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "regime", "label": _l("Regime")},
    {"key": "recipient_kind", "label": _l("Recipient")},
    {"key": "authority", "label": _l("Authority")},
    {"key": "clock", "label": _l("Clock")},
    {"key": "conditions", "label": _l("Trigger conditions")},
    {"key": "obligations", "label": _l("Generated obligations")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
OBLIGATION_TEMPLATE_SORTABLE_FIELDS = {
    "name": "name",
    "regime": "regime",
    "recipient_kind": "recipient_kind",
    "authority": "authority__short_name",
    "order": "order",
    "status": "workflow_state",
}
OBLIGATION_TEMPLATE_SEARCH_FIELDS = ["reference", "name", "legal_reference"]


def _template_queryset(qs):
    return (
        qs.select_related("authority")
        .prefetch_related("tags")
        .annotate(obligation_count=Count("obligations", distinct=True))
    )


class ObligationTemplateListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    """The legal rules obligations are generated from.

    Sorted by regime then ``order`` then name, so the 24-hour early warning is
    listed above the 72-hour notification rather than alphabetically.
    """

    model = ReportingObligationTemplate
    permission_required = "incidents.response_plan.read"
    filter_groups = OBLIGATION_TEMPLATE_FILTER_GROUPS
    text_filters = OBLIGATION_TEMPLATE_TEXT_FILTERS
    columns = OBLIGATION_TEMPLATE_COLUMNS
    template_name = "incidents/obligation_template_list.html"
    context_object_name = "templates"
    paginate_by = PAGE_SIZE
    sortable_fields = OBLIGATION_TEMPLATE_SORTABLE_FIELDS
    default_sort = "regime"
    search_fields = OBLIGATION_TEMPLATE_SEARCH_FIELDS

    def get_queryset(self):
        qs = _template_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class ObligationTemplateTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, SortableListMixin, ListView):
    model = ReportingObligationTemplate
    permission_required = "incidents.response_plan.read"
    template_name = "incidents/obligation_template_table_body.html"
    context_object_name = "templates"
    paginate_by = PAGE_SIZE
    sortable_fields = OBLIGATION_TEMPLATE_SORTABLE_FIELDS
    default_sort = "regime"
    search_fields = OBLIGATION_TEMPLATE_SEARCH_FIELDS
    filter_groups = OBLIGATION_TEMPLATE_FILTER_GROUPS
    text_filters = OBLIGATION_TEMPLATE_TEXT_FILTERS

    def get_queryset(self):
        qs = _template_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class ObligationTemplateDetailView(LoginRequiredMixin, PermissionRequiredMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = ReportingObligationTemplate
    permission_required = "incidents.response_plan.read"
    template_name = "incidents/obligation_template_detail.html"
    context_object_name = "template"

    def get_queryset(self):
        return super().get_queryset().select_related("authority").prefetch_related("tags")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obligation_template = self.object
        # The clock in one plain-language sentence, rendered above the raw
        # fields : it is what a reviewer actually checks.
        ctx["clock_summary"] = obligation_template.clock_summary
        ctx["obligation_count"] = obligation_template.obligations.count()
        ctx["recent_obligations"] = list(
            obligation_template.obligations.select_related("incident").order_by("-created_at")[:10]
        )
        return ctx


class ObligationTemplateCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    model = ReportingObligationTemplate
    permission_required = "incidents.response_plan.create"
    form_class = ReportingObligationTemplateForm
    template_name = "incidents/obligation_template_form.html"
    modal_template_name = "incidents/obligation_template_form_modal.html"
    modal_title_create = _l("New obligation template")
    modal_title_update = _l("Edit obligation template")

    def get_success_url(self):
        return reverse("incidents:obligation-template-detail", args=[self.object.pk])


class ObligationTemplateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = ReportingObligationTemplate
    permission_required = "incidents.response_plan.update"
    form_class = ReportingObligationTemplateForm
    template_name = "incidents/obligation_template_form.html"
    modal_template_name = "incidents/obligation_template_form_modal.html"
    modal_title_create = _l("New obligation template")
    modal_title_update = _l("Edit obligation template")

    def get_success_url(self):
        return reverse("incidents:obligation-template-detail", args=[self.object.pk])


class ObligationTemplateDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ProtectedDeleteMixin, DeleteView):
    model = ReportingObligationTemplate
    permission_required = "incidents.response_plan.delete"
    template_name = "incidents/obligation_template_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("incidents:obligation-template-list")

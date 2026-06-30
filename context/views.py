import json
import math

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from accounts.mixins import ApprovableUpdateMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, ScopeFilterMixin
from accounts.views import PermissionRequiredMixin
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
from core.query_params import parse_uuid
from .constants import (
    ActivityStatus,
    CollectionMethod,
    Criticality,
    ImpactLevel,
    IndicatorStatus,
    IndicatorType,
    IssueStatus,
    IssueType,
    ObjectiveCategory,
    ObjectiveStatus,
    PREDEFINED_SOURCE_FORMAT,
    RoleStatus,
    RoleType,
    StakeholderStatus,
)
from .forms import (
    ActivityCreateForm,
    ActivityUpdateForm,
    IndicatorCreateForm,
    IndicatorUpdateForm,
    IndicatorMeasurementForm,
    PredefinedIndicatorCreateForm,
    PredefinedIndicatorUpdateForm,
    IssueCreateForm,
    IssueUpdateForm,
    ObjectiveCreateForm,
    ObjectiveUpdateForm,
    ResponsibilityForm,
    RoleCreateForm,
    RoleUpdateForm,
    ScopeCreateForm,
    ScopeUpdateForm,
    StakeholderCreateForm,
    StakeholderUpdateForm,
    SwotAnalysisCreateForm,
    SwotAnalysisUpdateForm,
    SwotItemForm,
    SwotStrategyForm,
)
from .models import (
    Activity,
    Indicator,
    IndicatorMeasurement,
    Issue,
    Objective,
    Responsibility,
    Role,
    Scope,
    Site,
    Stakeholder,
    SwotAnalysis,
    SwotItem,
    SwotStrategy,
    Tag,
)


# ── Mixins ──────────────────────────────────────────────────

class CreatedByMixin:
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class ApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Generic approve view for context domain models."""

    model = None
    permission_feature = None
    permission_required = None
    success_url = None

    def dispatch(self, request, *args, **kwargs):
        if not self.permission_required:
            feature = self.permission_feature or self.model._meta.model_name
            self.permission_required = f"context.{feature}.approve"
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        from core.models import VersioningConfig
        from core.redirects import safe_redirect_target

        obj = get_object_or_404(self.model, pk=pk)
        if not VersioningConfig.is_approval_enabled(self.model):
            messages.error(request, _("Approval is disabled for this item type."))
            return redirect(safe_redirect_target(request, request.META.get("HTTP_REFERER")))
        feature = self.permission_feature or self.model._meta.model_name
        codename = f"context.{feature}.approve"
        if not request.user.is_superuser and not request.user.has_perm(codename):
            messages.error(request, _("You do not have permission to approve this item."))
            return redirect(safe_redirect_target(request, request.META.get("HTTP_REFERER")))
        obj.is_approved = True
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=["is_approved", "approved_by", "approved_at"])
        messages.success(request, _("Item approved."))
        return redirect(safe_redirect_target(request, request.META.get("HTTP_REFERER"), self.success_url or "/"))


# ── Dashboard indicator helpers ──────────────────────────────

DASHBOARD_INDICATOR_SLOTS = 10


def _format_number(value):
    """Format a numeric string with locale-aware thousand separators."""
    try:
        num = float(value)
    except (ValueError, TypeError):
        return value
    # A stored "nan" / "inf" parses as a float but int(num) below raises
    # ValueError / OverflowError, crashing every dashboard render. Display the
    # raw value instead of formatting a non-finite number.
    if not math.isfinite(num):
        return value
    # For string values with an explicit decimal point, preserve original precision
    if isinstance(value, str) and '.' in value:
        decimal_pos = len(value.strip().split('.')[-1])
        return formats.number_format(num, decimal_pos=decimal_pos, use_l10n=True)
    # Use integer display when there is no fractional part
    if num == int(num):
        return formats.number_format(int(num), use_l10n=True)
    return formats.number_format(num, decimal_pos=1, use_l10n=True)


def build_indicator_slot(ind, show_chart):
    """Build a single indicator's dashboard slot (value, trend, sparkline).

    ``ind`` is an :class:`Indicator` (ideally with ``measurements`` prefetched).
    Returns the dict the KPI-card template consumes. Shared by the legacy pinned
    KPI strip and the per-indicator dashboard widget.
    """
    # Fetch enough measurements for sparklines when the chart is enabled.
    limit = 20 if show_chart else 2
    measurements = list(ind.measurements.order_by("-recorded_at")[:limit])
    current = measurements[0] if measurements else None
    previous = measurements[1] if len(measurements) > 1 else None

    trend = None
    trend_value = None
    delta_display = ""
    if current and previous and ind.format == "number":
        try:
            cur_val = float(current.value)
            prev_val = float(previous.value)
            diff = cur_val - prev_val
            trend_value = diff
            if diff > 0:
                trend = "up"
                delta_display = "+" + _format_number(diff)
            elif diff < 0:
                trend = "down"
                delta_display = _format_number(diff)
            else:
                trend = "stable"
        except (ValueError, TypeError):
            pass
    elif current and previous and ind.format == "boolean":
        cur_bool = current.value.lower() in ("true", "1", "yes")
        prev_bool = previous.value.lower() in ("true", "1", "yes")
        trend = "changed" if cur_bool != prev_bool else "stable"

    # Formatted current value with thousand separators.
    formatted_value = None
    if ind.format == "number" and ind.current_value:
        formatted_value = _format_number(ind.current_value)

    # Build sparkline values (chronological, numeric only).
    sparkline_data = []
    if show_chart and ind.format == "number" and len(measurements) >= 2:
        for m in reversed(measurements):
            try:
                sparkline_data.append(float(m.value))
            except (ValueError, TypeError):
                continue

    return {
        "indicator": ind,
        "current_measurement": current,
        "previous_measurement": previous,
        "trend": trend,
        "trend_value": trend_value,
        "delta_display": delta_display,
        "formatted_value": formatted_value,
        "show_chart": show_chart,
        "sparkline_data": sparkline_data,
    }


def get_dashboard_indicator_slots(user):
    """Load pinned indicators with trend + sparkline data, padded to 10 slots."""
    pinned_ids = user.dashboard_indicators or []
    chart_ids = {str(i) for i in (user.dashboard_indicator_charts or [])}

    indicator_map = {}
    if pinned_ids:
        indicators = Indicator.objects.filter(
            id__in=pinned_ids,
        ).prefetch_related("measurements")
        for ind in indicators:
            indicator_map[str(ind.pk)] = build_indicator_slot(ind, str(ind.pk) in chart_ids)

    # Build ordered list, padded with None for empty slots
    slots = []
    for pid in pinned_ids:
        if pid in indicator_map:
            slots.append(indicator_map[pid])
    while len(slots) < DASHBOARD_INDICATOR_SLOTS:
        slots.append(None)
    return slots


# ── Scope ───────────────────────────────────────────────────

# Workflow-state facet options mirroring the old status chips (draft / validated
# / archived); the lifecycle's "pending" state was never offered as a chip.
WORKFLOW_STATUS_OPTIONS = [
    ("draft", _l("Draft")),
    ("validated", _l("Validated")),
    ("archived", _l("Archived")),
]

# Scopes run the standardised perimeter lifecycle (core/lifecycle.py), so their
# status facet offers the lifecycle step codes, not the default-workflow ones.
SCOPE_STATUS_OPTIONS = [
    ("draft", _l("Draft")),
    ("definition", _l("Definition")),
    ("validation", _l("Validation")),
    ("in_force", _l("In force")),
    ("archived", _l("Archived")),
]

SCOPE_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": SCOPE_STATUS_OPTIONS},
]
SCOPE_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
SCOPE_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "status", "label": _l("Status")},
    {"key": "effective_date", "label": _l("Effective date")},
    {"key": "responsible", "label": _l("Responsible")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class ScopeListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Scope
    permission_required = "context.scope.read"
    template_name = "context/scope_list.html"
    context_object_name = "scopes"
    filter_groups = SCOPE_FILTER_GROUPS
    text_filters = SCOPE_TEXT_FILTERS
    columns = SCOPE_COLUMNS
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "version": "version",
        "workflow_state": "workflow_state",
        "effective_date": "effective_date",
        "review_date": "review_date",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]
    paginate_by = None  # tree view shows all

    def get_queryset(self):
        qs = super().get_queryset().select_related("parent_scope")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["scopes"] = self._build_tree(list(ctx["scopes"]))
        return ctx

    @staticmethod
    def _build_tree(scopes):
        """Return scopes in depth-first tree order, annotated with tree_level/tree_indent.

        Sibling order is preserved from the queryset (i.e. server-side sort
        applies within each parent group, keeping the hierarchy intact).
        """
        by_parent = {}
        for s in scopes:
            by_parent.setdefault(s.parent_scope_id, []).append(s)

        result = []
        visited = set()

        def walk(parent_id, level):
            for s in by_parent.get(parent_id, []):
                s.tree_level = level
                s.tree_indent = level * 24
                result.append(s)
                visited.add(s.pk)
                walk(s.pk, level + 1)

        walk(None, 0)

        # Orphans (parent filtered out by scope access)
        for s in scopes:
            if s.pk not in visited:
                s.tree_level = 0
                s.tree_indent = 0
                result.append(s)

        return result


class ScopeDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, LifecycleStepperMixin, HistoryUrlMixin, DetailView):
    model = Scope
    permission_required = "context.scope.read"
    template_name = "context/scope_detail.html"
    context_object_name = "scope"
    approve_url_name = "context:scope-approve"

    def get_queryset(self):
        return super().get_queryset().select_related("parent_scope")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ancestors = self.object.get_ancestors()
        ctx["ancestors"] = ancestors
        # Scope ancestry for the page_header breadcrumb (Scopes > parent ref >
        # ... > current ref): references linking to each ancestor's detail page.
        ctx["scope_breadcrumb"] = [
            {"label": a.reference, "url": reverse("context:scope-detail", kwargs={"pk": a.pk})}
            for a in ancestors
        ]
        ctx["children"] = self.object.children.exclude(workflow_state="archived")
        # Strategic KPI tiles for the detail rail : the perimeter's compliance
        # posture, security objectives and the value it protects. Counts use the
        # governance-reportable set so the rail mirrors what counts in reports.
        from compliance.services import (
            active_frameworks_for_scoring,
            overall_compliance_rate,
        )
        from core.workflow import reportable

        scope = self.object
        scoped_frameworks = scope.frameworks.all()
        ctx["kpi_compliance_rate"] = (
            overall_compliance_rate(scoped_frameworks)
            if active_frameworks_for_scoring(scoped_frameworks).exists()
            else None
        )
        ctx["kpi_objectives"] = reportable(scope.objective_set.all()).count()
        ctx["kpi_essential_assets"] = reportable(scope.essentialasset_set.all()).count()
        # Hero map payload : the perimeter's own included sites PLUS the sites of
        # all its sub-scopes (descendants), deduplicated and geocoded client-side
        # from their address (like the supplier address map). A parent perimeter's
        # map therefore shows the geographic footprint of its whole subtree. The
        # "Included sites" badges above stay the scope's own direct sites.
        included = scope.included_sites.all()
        ctx["included_sites"] = included
        footprint = {}
        for source in [scope, *scope.get_descendants()]:
            for site in source.included_sites.all():
                if site.pk not in footprint and (site.address or "").strip():
                    footprint[site.pk] = site
        map_sites = [
            {"name": site.full_path, "address": (site.address or "").strip()}
            for site in footprint.values()
        ]
        ctx["scope_sites_json"] = json.dumps(map_sites)
        ctx["has_site_map"] = bool(map_sites)
        return ctx


class ScopeCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Scope
    permission_required = "context.scope.create"
    form_class = ScopeCreateForm
    template_name = "context/scope_form.html"
    modal_template_name = "context/scope_form_modal.html"
    modal_title_create = _l("New scope")
    modal_title_update = _l("Edit scope")
    success_url = reverse_lazy("context:scope-list")


class ScopeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, UpdateView):
    model = Scope
    permission_required = "context.scope.update"
    form_class = ScopeUpdateForm
    template_name = "context/scope_form.html"
    modal_template_name = "context/scope_form_modal.html"
    modal_title_create = _l("New scope")
    modal_title_update = _l("Edit scope")
    success_url = reverse_lazy("context:scope-list")


class ScopeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Scope
    permission_required = "context.scope.delete"
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:scope-list")


# ── Issue ───────────────────────────────────────────────────

ISSUE_FILTER_GROUPS = [
    {"param": "type", "field": "type", "label": _l("Type"), "options": IssueType.choices},
    {"param": "impact", "field": "impact_level", "label": _l("Impact"), "options": ImpactLevel.choices},
    {"param": "status", "field": "status", "label": _l("Status"), "options": IssueStatus.choices},
]
ISSUE_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Title")},
]
ISSUE_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Title"), "always": True},
    {"key": "scopes", "label": _l("Scopes")},
    {"key": "category", "label": _l("Category")},
    {"key": "impact", "label": _l("Impact")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class IssueListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Issue
    permission_required = "context.issue.read"
    template_name = "context/issue_list.html"
    context_object_name = "issues"
    status_field = "status"
    filter_groups = ISSUE_FILTER_GROUPS
    text_filters = ISSUE_TEXT_FILTERS
    columns = ISSUE_COLUMNS
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "category": "category",
        "impact": "impact_level",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Entity-specific KPI tiles for the rail, over the scope-filtered list
        # (the summary base captured before the facets are applied).
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            ctx["list_kpis"] = [
                {"label": _("Total issues"), "value": base.count(), "icon": "exclamation-triangle", "tone": "accent"},
                {"label": _("Critical impact"), "value": base.filter(impact_level=ImpactLevel.CRITICAL).count(), "icon": "fire", "tone": "danger"},
                {"label": _("Active"), "value": base.filter(status=IssueStatus.ACTIVE).count(), "icon": "activity", "tone": "warning"},
                {"label": _("Closed"), "value": base.filter(status=IssueStatus.CLOSED).count(), "icon": "check-circle", "tone": "success"},
            ]
        return ctx


class IssueDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Issue
    permission_required = "context.issue.read"
    template_name = "context/issue_detail.html"
    context_object_name = "issue"
    approve_url_name = "context:issue-approve"


class IssueCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Issue
    permission_required = "context.issue.create"
    form_class = IssueCreateForm
    template_name = "context/issue_form.html"
    modal_template_name = "context/issue_form_modal.html"
    modal_title_create = _l("New issue")
    modal_title_update = _l("Edit issue")
    success_url = reverse_lazy("context:issue-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class IssueUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Issue
    permission_required = "context.issue.update"
    form_class = IssueUpdateForm
    template_name = "context/issue_form.html"
    modal_template_name = "context/issue_form_modal.html"
    modal_title_create = _l("New issue")
    modal_title_update = _l("Edit issue")
    success_url = reverse_lazy("context:issue-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class IssueDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Issue
    permission_required = "context.issue.delete"
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:issue-list")


# ── Stakeholder ─────────────────────────────────────────────

STAKEHOLDER_FILTER_GROUPS = [
    {"param": "type", "field": "type", "label": _l("Type"), "options": IssueType.choices},
    {"param": "status", "field": "status", "label": _l("Status"), "options": StakeholderStatus.choices},
]
STAKEHOLDER_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
STAKEHOLDER_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "scopes", "label": _l("Scopes")},
    {"key": "category", "label": _l("Category")},
    {"key": "influence", "label": _l("Influence")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class StakeholderListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Stakeholder
    permission_required = "context.stakeholder.read"
    template_name = "context/stakeholder_list.html"
    context_object_name = "stakeholders"
    status_field = "status"
    filter_groups = STAKEHOLDER_FILTER_GROUPS
    text_filters = STAKEHOLDER_TEXT_FILTERS
    columns = STAKEHOLDER_COLUMNS
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "category": "category",
        "influence": "influence_level",
        "interest": "interest_level",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class StakeholderDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Stakeholder
    permission_required = "context.stakeholder.read"
    template_name = "context/stakeholder_detail.html"
    context_object_name = "stakeholder"
    approve_url_name = "context:stakeholder-approve"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("expectations")


class StakeholderCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Stakeholder
    permission_required = "context.stakeholder.create"
    form_class = StakeholderCreateForm
    template_name = "context/stakeholder_form.html"
    modal_template_name = "context/stakeholder_form_modal.html"
    modal_title_create = _l("New stakeholder")
    modal_title_update = _l("Edit stakeholder")
    success_url = reverse_lazy("context:stakeholder-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class StakeholderUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Stakeholder
    permission_required = "context.stakeholder.update"
    form_class = StakeholderUpdateForm
    template_name = "context/stakeholder_form.html"
    modal_template_name = "context/stakeholder_form_modal.html"
    modal_title_create = _l("New stakeholder")
    modal_title_update = _l("Edit stakeholder")
    success_url = reverse_lazy("context:stakeholder-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class StakeholderDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Stakeholder
    permission_required = "context.stakeholder.delete"
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:stakeholder-list")


# ── Objective ───────────────────────────────────────────────

OBJECTIVE_FILTER_GROUPS = [
    {"param": "status", "field": "status", "label": _l("Status"), "options": ObjectiveStatus.choices},
    {"param": "category", "field": "category", "label": _l("Category"), "options": ObjectiveCategory.choices},
]
OBJECTIVE_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Title")},
]
OBJECTIVE_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Title"), "always": True},
    {"key": "owner", "label": _l("Owner")},
    {"key": "progress", "label": _l("Progress")},
    {"key": "status", "label": _l("Status")},
    {"key": "target_date", "label": _l("Target date")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class ObjectiveListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Objective
    permission_required = "context.objective.read"
    template_name = "context/objective_list.html"
    context_object_name = "objectives"
    status_field = "status"
    filter_groups = OBJECTIVE_FILTER_GROUPS
    text_filters = OBJECTIVE_TEXT_FILTERS
    columns = OBJECTIVE_COLUMNS
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "category": "category",
        "progress": "progress_percentage",
        "workflow_state": "workflow_state",
        "target_date": "target_date",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class ObjectiveDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Objective
    permission_required = "context.objective.read"
    template_name = "context/objective_detail.html"
    context_object_name = "objective"
    approve_url_name = "context:objective-approve"


class ObjectiveCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Objective
    permission_required = "context.objective.create"
    form_class = ObjectiveCreateForm
    template_name = "context/objective_form.html"
    modal_template_name = "context/objective_form_modal.html"
    modal_title_create = _l("New objective")
    modal_title_update = _l("Edit objective")
    success_url = reverse_lazy("context:objective-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ObjectiveUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Objective
    permission_required = "context.objective.update"
    form_class = ObjectiveUpdateForm
    template_name = "context/objective_form.html"
    modal_template_name = "context/objective_form_modal.html"
    modal_title_create = _l("New objective")
    modal_title_update = _l("Edit objective")
    success_url = reverse_lazy("context:objective-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ObjectiveDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Objective
    permission_required = "context.objective.delete"
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:objective-list")


# ── SWOT ────────────────────────────────────────────────────

SWOT_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": WORKFLOW_STATUS_OPTIONS},
]
SWOT_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Title")},
]
SWOT_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Title"), "always": True},
    {"key": "items", "label": _l("Items")},
    {"key": "date", "label": _l("Analysis date")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class SwotListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = SwotAnalysis
    permission_required = "context.swot.read"
    template_name = "context/swot_list.html"
    context_object_name = "analyses"
    filter_groups = SWOT_FILTER_GROUPS
    text_filters = SWOT_TEXT_FILTERS
    columns = SWOT_COLUMNS
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "date": "analysis_date",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().annotate(
            strength_count=Count("items", filter=Q(items__quadrant="strength")),
            weakness_count=Count("items", filter=Q(items__quadrant="weakness")),
            opportunity_count=Count("items", filter=Q(items__quadrant="opportunity")),
            threat_count=Count("items", filter=Q(items__quadrant="threat")),
            strategy_count=Count("strategies"),
        )
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class SwotDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = SwotAnalysis
    permission_required = "context.swot.read"
    template_name = "context/swot_detail.html"
    context_object_name = "analysis"
    approval_feature = "swot"
    approve_url_name = "context:swot-approve"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("items", "strategies")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        items = list(self.object.items.all())
        ctx["items"] = items
        ctx["quadrants"] = [
            ("strength", _("Strengths"), "success", "bi-shield-check"),
            ("weakness", _("Weaknesses"), "danger", "bi-exclamation-triangle"),
            ("opportunity", _("Opportunities"), "primary", "bi-rocket-takeoff"),
            ("threat", _("Threats"), "warning", "bi-lightning"),
        ]
        ctx["strengths"] = [i for i in items if i.quadrant == "strength"]
        ctx["weaknesses"] = [i for i in items if i.quadrant == "weakness"]
        ctx["opportunities"] = [i for i in items if i.quadrant == "opportunity"]
        ctx["threats"] = [i for i in items if i.quadrant == "threat"]
        strategies = list(self.object.strategies.all())
        ctx["strategies_so"] = [s for s in strategies if s.quadrant == "so"]
        ctx["strategies_st"] = [s for s in strategies if s.quadrant == "st"]
        ctx["strategies_wo"] = [s for s in strategies if s.quadrant == "wo"]
        ctx["strategies_wt"] = [s for s in strategies if s.quadrant == "wt"]
        return ctx


class SwotCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = SwotAnalysis
    permission_required = "context.swot.create"
    form_class = SwotAnalysisCreateForm
    template_name = "context/swot_form.html"
    modal_template_name = "context/swot_form_modal.html"
    modal_title_create = _l("New SWOT analysis")
    modal_title_update = _l("Edit SWOT analysis")
    success_url = reverse_lazy("context:swot-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SwotUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = SwotAnalysis
    permission_required = "context.swot.update"
    form_class = SwotAnalysisUpdateForm
    template_name = "context/swot_form.html"
    modal_template_name = "context/swot_form_modal.html"
    modal_title_create = _l("New SWOT analysis")
    modal_title_update = _l("Edit SWOT analysis")
    success_url = reverse_lazy("context:swot-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SwotDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SwotAnalysis
    permission_required = "context.swot.delete"
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:swot-list")


class SwotItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SwotItem
    permission_required = "context.swot.create"
    form_class = SwotItemForm
    template_name = "context/swot_item_form_modal.html"

    def dispatch(self, request, *args, **kwargs):
        self.analysis = get_object_or_404(SwotAnalysis, pk=kwargs["analysis_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        quadrant = self.request.GET.get("quadrant")
        if quadrant:
            initial["quadrant"] = quadrant
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["analysis"] = self.analysis
        ctx["modal_title"] = _("New SWOT item")
        return ctx

    def form_valid(self, form):
        form.instance.swot_analysis = self.analysis
        form.save()
        return HttpResponse(status=204, headers={"HX-Trigger": "refreshItems"})

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class SwotItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SwotItem
    permission_required = "context.swot.update"
    form_class = SwotItemForm
    template_name = "context/swot_item_form_modal.html"

    def dispatch(self, request, *args, **kwargs):
        self.analysis = get_object_or_404(SwotAnalysis, pk=kwargs["analysis_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["analysis"] = self.analysis
        ctx["modal_title"] = _("Edit SWOT item")
        return ctx

    def form_valid(self, form):
        form.save()
        return HttpResponse(status=204, headers={"HX-Trigger": "refreshItems"})

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class SwotItemDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "context.swot.delete"

    def post(self, request, analysis_pk, pk):
        item = get_object_or_404(SwotItem, pk=pk, swot_analysis_id=analysis_pk)
        item.delete()
        return HttpResponse(status=204, headers={"HX-Trigger": "refreshItems"})


class SwotStrategyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SwotStrategy
    permission_required = "context.swot.create"
    form_class = SwotStrategyForm
    template_name = "context/swot_strategy_form_modal.html"

    def dispatch(self, request, *args, **kwargs):
        self.analysis = get_object_or_404(SwotAnalysis, pk=kwargs["analysis_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        quadrant = self.request.GET.get("quadrant")
        if quadrant:
            initial["quadrant"] = quadrant
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["analysis"] = self.analysis
        ctx["modal_title"] = _("New strategy")
        return ctx

    def form_valid(self, form):
        form.instance.swot_analysis = self.analysis
        form.save()
        return HttpResponse(status=204, headers={"HX-Trigger": "refreshItems"})

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class SwotStrategyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SwotStrategy
    permission_required = "context.swot.update"
    form_class = SwotStrategyForm
    template_name = "context/swot_strategy_form_modal.html"

    def dispatch(self, request, *args, **kwargs):
        self.analysis = get_object_or_404(SwotAnalysis, pk=kwargs["analysis_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["analysis"] = self.analysis
        ctx["modal_title"] = _("Edit strategy")
        return ctx

    def form_valid(self, form):
        form.save()
        return HttpResponse(status=204, headers={"HX-Trigger": "refreshItems"})

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class SwotStrategyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "context.swot.delete"

    def post(self, request, analysis_pk, pk):
        strategy = get_object_or_404(SwotStrategy, pk=pk, swot_analysis_id=analysis_pk)
        strategy.delete()
        return HttpResponse(status=204, headers={"HX-Trigger": "refreshItems"})


# ── Responsibility (nested under Role) ──────────────────────

class ResponsibilityCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Responsibility
    permission_required = "context.role.update"
    form_class = ResponsibilityForm
    template_name = "context/responsibility_form_modal.html"

    def dispatch(self, request, *args, **kwargs):
        self.role = get_object_or_404(Role, pk=kwargs["role_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["role"] = self.role
        ctx["modal_title"] = _("New responsibility")
        return ctx

    def form_valid(self, form):
        form.instance.role = self.role
        form.save()
        self.role.send_back_to_draft()
        return HttpResponse(status=204, headers={"HX-Trigger": "refreshItems"})

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class ResponsibilityUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Responsibility
    permission_required = "context.role.update"
    form_class = ResponsibilityForm
    template_name = "context/responsibility_form_modal.html"

    def dispatch(self, request, *args, **kwargs):
        self.role = get_object_or_404(Role, pk=kwargs["role_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Responsibility.objects.filter(role_id=self.kwargs["role_pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["role"] = self.role
        ctx["modal_title"] = _("Edit responsibility")
        return ctx

    def form_valid(self, form):
        form.save()
        self.role.send_back_to_draft()
        return HttpResponse(status=204, headers={"HX-Trigger": "refreshItems"})

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class ResponsibilityDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "context.role.update"

    def post(self, request, role_pk, pk):
        role = get_object_or_404(Role, pk=role_pk)
        responsibility = get_object_or_404(Responsibility, pk=pk, role_id=role_pk)
        responsibility.delete()
        role.send_back_to_draft()
        return HttpResponse(status=204, headers={"HX-Trigger": "refreshItems"})


# ── Role ────────────────────────────────────────────────────

ROLE_FILTER_GROUPS = [
    {"param": "type", "field": "type", "label": _l("Type"), "options": RoleType.choices},
    {"param": "status", "field": "status", "label": _l("Status"), "options": RoleStatus.choices},
]
ROLE_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Title")},
]
ROLE_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Title"), "always": True},
    {"key": "type", "label": _l("Type")},
    {"key": "users", "label": _l("Users")},
    {"key": "responsibilities", "label": _l("Responsibilities")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class RoleListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Role
    permission_required = "context.role.read"
    template_name = "context/role_list.html"
    context_object_name = "roles"
    status_field = "status"
    filter_groups = ROLE_FILTER_GROUPS
    text_filters = ROLE_TEXT_FILTERS
    columns = ROLE_COLUMNS
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().annotate(
            user_count=Count("assigned_users", distinct=True),
            responsible_count=Count("responsibilities", filter=Q(responsibilities__raci_type="responsible"), distinct=True),
            accountable_count=Count("responsibilities", filter=Q(responsibilities__raci_type="accountable"), distinct=True),
            consulted_count=Count("responsibilities", filter=Q(responsibilities__raci_type="consulted"), distinct=True),
            informed_count=Count("responsibilities", filter=Q(responsibilities__raci_type="informed"), distinct=True),
        )
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class RoleDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Role
    permission_required = "context.role.read"
    template_name = "context/role_detail.html"
    context_object_name = "role"
    approve_url_name = "context:role-approve"

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            "responsibilities", "assigned_users"
        )


class RoleCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Role
    permission_required = "context.role.create"
    form_class = RoleCreateForm
    template_name = "context/role_form.html"
    modal_template_name = "context/role_form_modal.html"
    modal_title_create = _l("New role")
    modal_title_update = _l("Edit role")
    success_url = reverse_lazy("context:role-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RoleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Role
    permission_required = "context.role.update"
    form_class = RoleUpdateForm
    template_name = "context/role_form.html"
    modal_template_name = "context/role_form_modal.html"
    modal_title_create = _l("New role")
    modal_title_update = _l("Edit role")
    success_url = reverse_lazy("context:role-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RoleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Role
    permission_required = "context.role.delete"
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:role-list")


# ── Activity ────────────────────────────────────────────────

ACTIVITY_FILTER_GROUPS = [
    {"param": "criticality", "field": "criticality", "label": _l("Criticality"), "options": Criticality.choices},
    {"param": "status", "field": "status", "label": _l("Status"), "options": ActivityStatus.choices},
]
ACTIVITY_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
ACTIVITY_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "criticality", "label": _l("Criticality")},
    {"key": "owner", "label": _l("Owner")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class ActivityListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Activity
    permission_required = "context.activity.read"
    template_name = "context/activity_list.html"
    context_object_name = "activities"
    status_field = "status"
    filter_groups = ACTIVITY_FILTER_GROUPS
    text_filters = ACTIVITY_TEXT_FILTERS
    columns = ACTIVITY_COLUMNS
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "criticality": "criticality",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner", "parent_activity")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class ActivityDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Activity
    permission_required = "context.activity.read"
    template_name = "context/activity_detail.html"
    context_object_name = "activity"
    approve_url_name = "context:activity-approve"


class ActivityCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Activity
    permission_required = "context.activity.create"
    form_class = ActivityCreateForm
    template_name = "context/activity_form.html"
    modal_template_name = "context/activity_form_modal.html"
    modal_title_create = _l("New activity")
    modal_title_update = _l("Edit activity")
    success_url = reverse_lazy("context:activity-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ActivityUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Activity
    permission_required = "context.activity.update"
    form_class = ActivityUpdateForm
    template_name = "context/activity_form.html"
    modal_template_name = "context/activity_form_modal.html"
    modal_title_create = _l("New activity")
    modal_title_update = _l("Edit activity")
    success_url = reverse_lazy("context:activity-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ActivityDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Activity
    permission_required = "context.activity.delete"
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:activity-list")


# ── Table body views (HTMX partial refresh) ───────────────

class ScopeTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Scope
    permission_required = "context.scope.read"
    template_name = "context/scope_table_body.html"
    context_object_name = "scopes"
    paginate_by = None
    sortable_fields = ScopeListView.sortable_fields
    default_sort = ScopeListView.default_sort
    search_fields = ["reference", "name"]
    filter_groups = SCOPE_FILTER_GROUPS
    text_filters = SCOPE_TEXT_FILTERS

    def get_queryset(self):
        qs = super().get_queryset().select_related("parent_scope").prefetch_related("tags")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["scopes"] = ScopeListView._build_tree(list(ctx["scopes"]))
        return ctx


class IssueTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Issue
    permission_required = "context.issue.read"
    template_name = "context/issue_table_body.html"
    context_object_name = "issues"
    paginate_by = 50
    sortable_fields = IssueListView.sortable_fields
    default_sort = IssueListView.default_sort
    search_fields = ["reference", "name"]
    filter_groups = ISSUE_FILTER_GROUPS
    text_filters = ISSUE_TEXT_FILTERS

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class StakeholderTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Stakeholder
    permission_required = "context.stakeholder.read"
    template_name = "context/stakeholder_table_body.html"
    context_object_name = "stakeholders"
    paginate_by = 50
    sortable_fields = StakeholderListView.sortable_fields
    default_sort = StakeholderListView.default_sort
    search_fields = ["reference", "name"]
    filter_groups = STAKEHOLDER_FILTER_GROUPS
    text_filters = STAKEHOLDER_TEXT_FILTERS

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class ObjectiveTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Objective
    permission_required = "context.objective.read"
    template_name = "context/objective_table_body.html"
    context_object_name = "objectives"
    paginate_by = 50
    sortable_fields = ObjectiveListView.sortable_fields
    default_sort = ObjectiveListView.default_sort
    search_fields = ["reference", "name"]
    filter_groups = OBJECTIVE_FILTER_GROUPS
    text_filters = OBJECTIVE_TEXT_FILTERS

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class SwotTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = SwotAnalysis
    permission_required = "context.swot.read"
    template_name = "context/swot_table_body.html"
    context_object_name = "analyses"
    paginate_by = 50
    sortable_fields = SwotListView.sortable_fields
    default_sort = SwotListView.default_sort
    search_fields = ["reference", "name"]
    filter_groups = SWOT_FILTER_GROUPS
    text_filters = SWOT_TEXT_FILTERS

    def get_queryset(self):
        qs = super().get_queryset().annotate(
            strength_count=Count("items", filter=Q(items__quadrant="strength")),
            weakness_count=Count("items", filter=Q(items__quadrant="weakness")),
            opportunity_count=Count("items", filter=Q(items__quadrant="opportunity")),
            threat_count=Count("items", filter=Q(items__quadrant="threat")),
            strategy_count=Count("strategies"),
        )
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class RoleTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Role
    permission_required = "context.role.read"
    template_name = "context/role_table_body.html"
    context_object_name = "roles"
    paginate_by = 50
    sortable_fields = RoleListView.sortable_fields
    default_sort = RoleListView.default_sort
    search_fields = ["reference", "name"]
    filter_groups = ROLE_FILTER_GROUPS
    text_filters = ROLE_TEXT_FILTERS

    def get_queryset(self):
        qs = super().get_queryset().annotate(
            user_count=Count("assigned_users", distinct=True),
            responsible_count=Count("responsibilities", filter=Q(responsibilities__raci_type="responsible"), distinct=True),
            accountable_count=Count("responsibilities", filter=Q(responsibilities__raci_type="accountable"), distinct=True),
            consulted_count=Count("responsibilities", filter=Q(responsibilities__raci_type="consulted"), distinct=True),
            informed_count=Count("responsibilities", filter=Q(responsibilities__raci_type="informed"), distinct=True),
        )
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class ActivityTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Activity
    permission_required = "context.activity.read"
    template_name = "context/activity_table_body.html"
    context_object_name = "activities"
    paginate_by = 50
    sortable_fields = ActivityListView.sortable_fields
    default_sort = ActivityListView.default_sort
    search_fields = ["reference", "name"]
    filter_groups = ACTIVITY_FILTER_GROUPS
    text_filters = ACTIVITY_TEXT_FILTERS

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner", "parent_activity")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


@login_required
@require_POST
def tag_create_inline(request):
    """Create (or retrieve) a tag via AJAX and return its id/name as JSON."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "Name is required"}, status=400)

    tag, _created = Tag.objects.get_or_create(
        name__iexact=name,
        defaults={"name": name},
    )
    return JsonResponse({"id": str(tag.id), "name": tag.name})


class TagListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Tag
    permission_required = "context.scope.read"
    template_name = "context/tag_list.html"
    context_object_name = "tags"
    paginate_by = 50

    def get_queryset(self):
        from django.db.models.fields.related import ManyToManyRel

        qs = Tag.objects.all()
        tags = list(qs)
        for tag in tags:
            usage = []
            for field in Tag._meta.get_fields():
                if isinstance(field, ManyToManyRel):
                    accessor = field.get_accessor_name()
                    count = getattr(tag, accessor).count()
                    if count > 0:
                        model_name = field.related_model._meta.verbose_name_plural
                        usage.append((str(model_name), count))
            tag.usage = usage
            tag.usage_total = sum(c for _, c in usage)
        return tags


class TagUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Tag
    permission_required = "context.scope.update"
    template_name = "context/tag_form.html"
    success_url = reverse_lazy("context:tag-list")

    def get_form_class(self):
        from .forms import TagForm
        return TagForm


class TagDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Tag
    permission_required = "context.scope.delete"
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:tag-list")


# ── Indicators ─────────────────────────────────────────────

MAX_DASHBOARD_INDICATORS = 10


@login_required
@require_POST
def dashboard_indicator_toggle(request):
    """Toggle an indicator on/off the dashboard (AJAX)."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # A valid-JSON non-object body (123, [1], "x") has no .get; guard before use.
    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    raw_id = data.get("indicator_id", "")
    indicator_id = parse_uuid(raw_id if isinstance(raw_id, str) else "")
    if indicator_id is None:
        return JsonResponse({"error": "indicator_id is required"}, status=400)
    indicator_id = str(indicator_id)

    # Verify the indicator exists
    if not Indicator.objects.filter(pk=indicator_id).exists():
        return JsonResponse({"error": "Indicator not found"}, status=404)

    user = request.user
    pinned = list(user.dashboard_indicators or [])

    if indicator_id in pinned:
        pinned.remove(indicator_id)
        action = "removed"
    else:
        if len(pinned) >= MAX_DASHBOARD_INDICATORS:
            return JsonResponse(
                {"error": _("Maximum %d indicators on the dashboard.") % MAX_DASHBOARD_INDICATORS},
                status=400,
            )
        pinned.append(indicator_id)
        action = "added"

    user.dashboard_indicators = pinned
    user.save(update_fields=["dashboard_indicators"])
    return JsonResponse({"action": action, "pinned": pinned})


@login_required
@require_POST
def dashboard_indicator_chart_toggle(request):
    """Toggle sparkline visibility for a single indicator (AJAX)."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # A valid-JSON non-object body (123, [1], "x") has no .get; guard before use.
    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    raw_id = data.get("indicator_id", "")
    indicator_id = raw_id.strip() if isinstance(raw_id, str) else ""
    if not indicator_id:
        return JsonResponse({"error": "indicator_id is required"}, status=400)

    user = request.user
    chart_ids = list(user.dashboard_indicator_charts or [])

    if indicator_id in chart_ids:
        chart_ids.remove(indicator_id)
        action = "hidden"
    else:
        chart_ids.append(indicator_id)
        action = "shown"

    user.dashboard_indicator_charts = chart_ids
    user.save(update_fields=["dashboard_indicator_charts"])
    return JsonResponse({"action": action, "chart_ids": chart_ids})


def _attach_indicator_sparklines(indicators, limit=20):
    """Attach ``sparkline_data`` (chronological numeric values) and ``spark_trend``
    to each number indicator, for the per-row mini chart in the list.

    Relies on the ``measurements`` relation being prefetched (newest first) so it
    does not issue a query per row.
    """
    for ind in indicators:
        data = []
        trend = None
        if ind.format == "number":
            measurements = list(ind.measurements.all())[:limit]  # cached, newest first
            for m in reversed(measurements):
                try:
                    data.append(float(m.value))
                except (ValueError, TypeError):
                    continue
            if len(measurements) >= 2:
                try:
                    diff = float(measurements[0].value) - float(measurements[1].value)
                    trend = "up" if diff > 0 else "down" if diff < 0 else "stable"
                except (ValueError, TypeError):
                    pass
        ind.sparkline_data = data
        ind.spark_trend = trend
    return indicators


INDICATOR_FILTER_GROUPS = [
    {"param": "status", "field": "status", "label": _l("Status"), "options": IndicatorStatus.choices},
]
INDICATOR_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Title")},
]
INDICATOR_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Title"), "always": True},
    {"key": "current_value", "label": _l("Current value")},
    {"key": "trend", "label": _l("Trend")},
    {"key": "collection", "label": _l("Collection")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class IndicatorListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Indicator
    permission_required = "context.indicator.read"
    template_name = "context/indicator_list.html"
    context_object_name = "indicators"
    status_field = "status"
    filter_groups = INDICATOR_FILTER_GROUPS
    text_filters = INDICATOR_TEXT_FILTERS
    columns = INDICATOR_COLUMNS
    paginate_by = 50
    indicator_type = None
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "format": "format",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related(
            "scopes",
            Prefetch("measurements", queryset=IndicatorMeasurement.objects.order_by("-recorded_at")),
        )
        if self.indicator_type:
            qs = qs.filter(indicator_type=self.indicator_type)
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["indicator_type"] = self.indicator_type
        ctx["nav_key"] = (
            "context:indicator-technical-list"
            if str(self.indicator_type) == "technical"
            else "context:indicator-organizational-list"
        )
        _attach_indicator_sparklines(ctx["indicators"])
        return ctx


class IndicatorTableBodyView(LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Indicator
    permission_required = "context.indicator.read"
    template_name = "context/indicator_table_body.html"
    context_object_name = "indicators"
    paginate_by = 50
    sortable_fields = IndicatorListView.sortable_fields
    default_sort = IndicatorListView.default_sort
    search_fields = ["reference", "name"]
    filter_groups = INDICATOR_FILTER_GROUPS
    text_filters = INDICATOR_TEXT_FILTERS

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related(
            "scopes",
            Prefetch("measurements", queryset=IndicatorMeasurement.objects.order_by("-recorded_at")),
        )
        indicator_type = self.request.GET.get("indicator_type")
        if indicator_type:
            qs = qs.filter(indicator_type=indicator_type)
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        _attach_indicator_sparklines(ctx["indicators"])
        return ctx


class IndicatorDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Indicator
    permission_required = "context.indicator.read"
    template_name = "context/indicator_detail.html"
    context_object_name = "indicator"
    approve_url_name = "context:indicator-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["measurements"] = self.object.measurements.select_related("recorded_by")[:50]
        ctx["measurement_form"] = IndicatorMeasurementForm(
            indicator_format=self.object.format,
        )
        ctx["nav_key"] = (
            "context:indicator-technical-list"
            if str(self.object.indicator_type) == "technical"
            else "context:indicator-organizational-list"
        )
        return ctx


class IndicatorCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Indicator
    permission_required = "context.indicator.create"
    form_class = IndicatorCreateForm
    template_name = "context/indicator_form.html"
    modal_template_name = "context/indicator_form_modal.html"
    modal_title_create = _l("New indicator")
    modal_title_update = _l("Edit indicator")
    indicator_type = None

    def get_success_url(self):
        return reverse_lazy("context:indicator-detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["indicator_type"] = self.indicator_type
        return ctx

    def form_valid(self, form):
        form.instance.indicator_type = self.indicator_type
        return super().form_valid(form)


class PredefinedIndicatorCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Indicator
    permission_required = "context.indicator.create"
    form_class = PredefinedIndicatorCreateForm
    template_name = "context/indicator_predefined_form.html"
    modal_template_name = "context/indicator_predefined_form_modal.html"
    modal_title_create = _l("New predefined indicator")
    modal_title_update = _l("Edit predefined indicator")

    def get_success_url(self):
        return reverse_lazy("context:indicator-detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.is_internal = True
        form.instance.indicator_type = IndicatorType.ORGANIZATIONAL
        form.instance.collection_method = CollectionMethod.INTERNAL
        # Auto-determine format and unit from source
        source = form.instance.internal_source
        fmt, unit = PREDEFINED_SOURCE_FORMAT.get(source, ("number", ""))
        form.instance.format = fmt
        form.instance.unit = unit
        response = super().form_valid(form)
        # Trigger first measurement on creation
        value = self.object.compute_internal_value()
        if value is not None:
            self.object.record_measurement(
                value=value,
                recorded_by=self.request.user,
                notes=_("Initial measurement (automatic)."),
            )
        return response


class IndicatorUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Indicator
    permission_required = "context.indicator.update"
    template_name = "context/indicator_form.html"
    modal_template_name = "context/indicator_form_modal.html"
    modal_title_create = _l("New indicator")
    modal_title_update = _l("Edit indicator")

    def get_form_class(self):
        if self.object.is_internal:
            return PredefinedIndicatorUpdateForm
        return IndicatorUpdateForm

    def get_template_names(self):
        if self._is_htmx() and self.object.is_internal:
            return ["context/indicator_predefined_form_modal.html"]
        if self._is_htmx():
            return ["context/indicator_form_modal.html"]
        if self.object.is_internal:
            return ["context/indicator_predefined_form.html"]
        return ["context/indicator_form.html"]

    def get_success_url(self):
        return reverse_lazy("context:indicator-detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["indicator_type"] = self.object.indicator_type
        return ctx


class IndicatorDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Indicator
    permission_required = "context.indicator.delete"
    template_name = "context/confirm_delete.html"

    def get_success_url(self):
        indicator = self.get_object()
        if indicator.indicator_type == IndicatorType.TECHNICAL:
            return reverse_lazy("context:indicator-technical-list")
        return reverse_lazy("context:indicator-organizational-list")


class IndicatorRecordMeasurementView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Record a measurement for an indicator (manual)."""
    permission_required = "context.indicator.update"

    def post(self, request, pk):
        indicator = get_object_or_404(Indicator, pk=pk)
        form = IndicatorMeasurementForm(request.POST, indicator_format=indicator.format)
        if form.is_valid():
            indicator.record_measurement(
                value=form.cleaned_data["value"],
                recorded_by=request.user,
                notes=form.cleaned_data.get("notes", ""),
            )
            messages.success(request, _("Measurement recorded."))
        else:
            messages.error(request, _("Invalid measurement data."))
        return redirect("context:indicator-detail", pk=pk)


class IndicatorRefreshView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Trigger a refresh of a predefined indicator's value."""
    permission_required = "context.indicator.update"

    def post(self, request, pk):
        indicator = get_object_or_404(Indicator, pk=pk)
        if not indicator.is_internal:
            messages.error(request, _("This indicator is not a predefined indicator."))
            return redirect("context:indicator-detail", pk=pk)
        value = indicator.compute_internal_value()
        if value is not None:
            indicator.record_measurement(
                value=value,
                recorded_by=request.user,
                notes=_("Manual refresh."),
            )
            messages.success(request, _("Indicator refreshed."))
        else:
            messages.warning(request, _("Could not compute the indicator value."))
        return redirect("context:indicator-detail", pk=pk)

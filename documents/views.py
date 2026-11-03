# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web views of module 7 (documents).

**Registers** (documents, campaigns) run the house list stack, with
``ListSummaryMixin`` to the left of ``ScopeFilterMixin`` so the rail counts the
whole visible list, and a ``*TableBodyView`` for the HTMX refresh.

**Detail pages** run ``ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin,
DetailView``. Every state change goes through the generic
``workflow:transition`` endpoint fed by the stepper : the gates and side
effects (supersession, approval stamps, campaign launch and closure) live in
each model's ``transition_to()``, so there is no transition view here.

**Acts that are not transitions** (reviewed with no change, new version, add
newcomers, excuse, acknowledge) each call the one model method that owns them.

**Tenancy** : every object resolved from a URL goes through a scope-filtered
queryset. A version and an acknowledgement inherit their document's scopes
(``scope_parent_lookup``), resolved by ``core.scoping``. The personal
"To acknowledge" pages need no permission and no scope : they only ever read
the current user's own rows (RG-DOC-17, RG-DOC-22), and answer 404 for anyone
else's.
"""

from collections import defaultdict
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, CharField, Count, OuterRef, ProtectedError, Q, Subquery, Value, When
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.utils.translation import ngettext
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView

from accounts.mixins import HistoryUrlMixin, LifecycleStepperMixin, ScopeFilterMixin
from accounts.views import PermissionRequiredMixin
from context.models import Scope
from core.lifecycle import DomainRefusalError, LifecycleProtectedError, reportable, reportable_states, resolve_lifecycle
from core.mixins import (
    AdvancedFilterMixin,
    ColumnPreferenceMixin,
    ConfirmDeleteShellMixin,
    HtmxFormMixin,
    ListSummaryMixin,
    PredefinedFilterMixin,
    SavedFilterMixin,
    SortableListMixin,
    TableBodyPaginatedMixin,
    is_drawer_request,
)
from core.scoping import filter_queryset_by_scopes

from .constants import (
    CAMPAIGN_RUNNING,
    CAMPAIGN_STATES,
    POLICY_ACTIVE,
    POLICY_STATES,
    VERSION_IN_FORCE,
    AcknowledgementChannel,
    AcknowledgementStatus,
    DocumentType,
)
from .forms import (
    AcknowledgementCampaignForm,
    ExcuseForm,
    NewVersionForm,
    PolicyCreateForm,
    PolicyForm,
    PolicyVersionForm,
    RecordReviewForm,
    _freeze,
)
from .models import AcknowledgementCampaign, Policy, PolicyAcknowledgement, PolicyVersion

PAGE_SIZE = 50


# ── Shared helpers ─────────────────────────────────────────


def _state_options(states):
    """``(code, label)`` pairs read off a lifecycle declaration (no DB at import)."""
    return [(code, label) for code, label, *_flags in states]


def _scoped(qs, user):
    """Restrict ``qs`` to the rows ``user`` may see (scope tenancy)."""
    if user.is_superuser:
        return qs
    scope_ids = user.get_allowed_scope_ids()
    if scope_ids is None:
        return qs
    return filter_queryset_by_scopes(qs, scope_ids)


def _scoped_get(model, request, pk, qs=None):
    """One row by primary key, honouring the caller's scopes, else 404."""
    return get_object_or_404(_scoped(qs if qs is not None else model._default_manager.all(), request.user), pk=pk)


def _attachment_disposition(filename):
    """A safe ``Content-Disposition: attachment`` value (no header injection)."""
    safe = "".join(ch for ch in (filename or "") if ch not in '"\\\r\n').strip() or "document.pdf"
    return f"attachment; filename=\"{safe}\"; filename*=UTF-8''{quote(safe)}"


def _rate(counts):
    """RG-DOC-19 : acknowledged / (all - excused), as an integer percentage."""
    total = sum(counts.values())
    denominator = total - counts.get(AcknowledgementStatus.EXCUSED, 0)
    if not total:
        return None
    return round(100 * counts.get(AcknowledgementStatus.ACKNOWLEDGED, 0) / denominator) if denominator else 0


def _campaign_counts(campaign_ids):
    """``{campaign_id: {status: n}}`` in one grouped query."""
    counts = defaultdict(lambda: defaultdict(int))
    rows = (
        PolicyAcknowledgement.objects.filter(campaign_id__in=list(campaign_ids))
        .order_by()
        .values_list("campaign_id", "status")
        .annotate(n=Count("pk"))
    )
    for campaign_id, status, n in rows:
        counts[campaign_id][status] = n
    return counts


def _latest_campaign_rates(policy_ids):
    """``{policy_id: rate}`` of each document's most recently launched campaign."""
    launched = reportable_states(AcknowledgementCampaign)
    campaigns = (
        AcknowledgementCampaign.objects.filter(
            policy_version__policy_id__in=list(policy_ids), workflow_state__in=launched,
        )
        .order_by("policy_version__policy_id", "-launched_at", "-created_at")
        .values_list("pk", "policy_version__policy_id")
    )
    latest = {}
    for campaign_id, policy_id in campaigns:
        latest.setdefault(policy_id, campaign_id)
    counts = _campaign_counts(latest.values())
    return {policy_id: _rate(counts.get(campaign_id, {})) for policy_id, campaign_id in latest.items()}


def _average(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values)) if values else None


class CreatedByMixin:
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class UserFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ProtectedDeleteMixin:
    """A lifecycle or ``PROTECT`` refusal becomes a message, not a 500."""

    def form_valid(self, form):
        self.object = self.get_object()
        success_url = self.get_success_url()
        try:
            self.object.delete()
        except LifecycleProtectedError as exc:
            messages.error(self.request, str(exc))
            success_url = self.get_refused_url()
        except ProtectedError:
            messages.error(self.request, _("This element is still referenced and cannot be deleted."))
            success_url = self.get_refused_url()
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=204, headers={"HX-Trigger": "formSaved"})
        return redirect(success_url)

    def get_refused_url(self):
        return self.get_success_url()


class PageFormNavMixin:
    """Breadcrumb, Cancel target and accent of the full-page form fallback."""

    page_form_nav = "documents:policy-list"

    def get_page_form_cancel_url(self):
        obj = getattr(self, "object", None)
        if obj is not None and obj.pk and not obj._state.adding:
            return self.get_success_url()
        parent_url = self.get_form_parent_url()
        return parent_url or reverse(self.page_form_nav)

    def get_form_parent(self):
        return None

    def get_form_parent_url(self):
        parent = self.get_form_parent()
        return _detail_url(parent) if parent is not None else None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not ctx.get("is_modal"):
            ctx["cancel_url"] = self.get_page_form_cancel_url()
            ctx["form_nav"] = self.page_form_nav
            ctx["form_accent"] = "documents"
            parent = self.get_form_parent()
            if parent is not None:
                ctx["form_parent_label"] = parent.reference
                ctx["form_parent_url"] = _detail_url(parent)
        return ctx


def _detail_url(obj):
    if isinstance(obj, Policy):
        return reverse("documents:policy-detail", args=[obj.pk])
    if isinstance(obj, PolicyVersion):
        return reverse("documents:policyversion-detail", args=[obj.pk])
    if isinstance(obj, AcknowledgementCampaign):
        return reverse("documents:acknowledgementcampaign-detail", args=[obj.pk])
    return None


# ══ Policy : the register ══════════════════════════════════

_REVIEW_OVERDUE = "overdue"
_REVIEW_ON_TIME = "on_time"

POLICY_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Reference")},
    {"param": "title", "field": "title", "label": _l("Title")},
]
POLICY_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "title", "label": _l("Title"), "always": True},
    {"key": "type", "label": _l("Type")},
    {"key": "owner", "label": _l("Owner")},
    {"key": "version", "label": _l("Version in force")},
    {"key": "next_review", "label": _l("Next review")},
    {"key": "ack_rate", "label": _l("Acknowledged")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
POLICY_SORTABLE_FIELDS = {
    "reference": "reference",
    "title": "title",
    "type": "document_type",
    "owner": "owner__last_name",
    "next_review": "next_review_date",
    "status": "workflow_state",
}
POLICY_SEARCH_FIELDS = ["reference", "title", "summary"]


def _policy_queryset(qs):
    """Joins, the version in force (one subquery per column) and the review flag.

    The review flag is the SQL twin of ``Policy.is_review_overdue`` (RG-DOC-12),
    so the facet and the red date on the row never disagree.
    """
    in_force = PolicyVersion.objects.filter(policy=OuterRef("pk"), workflow_state=VERSION_IN_FORCE)
    return (
        qs.select_related("owner", "parent")
        .prefetch_related("scopes", "tags")
        .annotate(
            in_force_pk=Subquery(in_force.values("pk")[:1]),
            in_force_label=Subquery(in_force.values("version_label")[:1]),
            in_force_effective=Subquery(in_force.values("effective_from")[:1]),
            review_flag=Case(
                When(workflow_state=POLICY_ACTIVE, next_review_date__lt=timezone.localdate(), then=Value(_REVIEW_OVERDUE)),
                default=Value(_REVIEW_ON_TIME),
                output_field=CharField(),
            ),
        )
    )


class _PolicyListMixin:
    """Facets, search and row decoration shared by the register and its table body."""

    model = Policy
    permission_required = "documents.policy.read"
    context_object_name = "policies"
    paginate_by = PAGE_SIZE
    sortable_fields = POLICY_SORTABLE_FIELDS
    default_sort = "reference"
    search_fields = POLICY_SEARCH_FIELDS
    text_filters = POLICY_TEXT_FILTERS

    @cached_property
    def filter_groups(self):
        User = get_user_model()
        owners = User.objects.filter(owned_policies__isnull=False).distinct().order_by("last_name", "first_name")
        scopes = _scoped(Scope.objects.all(), self.request.user).order_by("name")
        return [
            {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": _state_options(POLICY_STATES)},
            {"param": "type", "field": "document_type", "label": _l("Type"), "options": DocumentType.choices},
            {"param": "owner", "field": "owner", "label": _l("Owner"), "options": [(str(u.pk), u.display_name) for u in owners]},
            {"param": "scope", "field": "scopes", "label": _l("Scope"), "options": [(str(s.pk), s.name) for s in scopes]},
            {
                "param": "review", "field": "review_flag", "label": _l("Review"),
                "options": [(_REVIEW_OVERDUE, _l("Review overdue")), (_REVIEW_ON_TIME, _l("Not overdue"))],
            },
        ]

    def get_queryset(self):
        qs = _policy_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs).distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rows = list(ctx.get(self.context_object_name) or [])
        rates = _latest_campaign_rates([p.pk for p in rows])
        for policy in rows:
            policy.ack_rate = rates.get(policy.pk)
        ctx[self.context_object_name] = rows
        return ctx


class PolicyListView(_PolicyListMixin, LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    """The register of documented information (clause 7.5)."""

    columns = POLICY_COLUMNS
    template_name = "documents/policy_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            base = base.order_by()
            today = timezone.localdate()
            # "Without a version in force" counts the living documents only : a
            # retired document has none by design (RG-DOC-09).
            terminal = [step.code for step in resolve_lifecycle(Policy).archived_steps]
            without = base.exclude(workflow_state__in=terminal).exclude(
                pk__in=PolicyVersion.objects.filter(workflow_state=VERSION_IN_FORCE).values("policy_id")
            )
            average = _average(_latest_campaign_rates(base.values_list("pk", flat=True)).values())
            ctx["list_kpis"] = [
                {"label": _("Active documents"), "value": reportable(base).count(), "icon": "file-earmark-check", "tone": "success"},
                {
                    "label": _("Reviews overdue"),
                    "value": base.filter(workflow_state=POLICY_ACTIVE, next_review_date__lt=today).count(),
                    "icon": "calendar-x", "tone": "danger",
                    "url": f"{reverse('documents:policy-list')}?review={_REVIEW_OVERDUE}",
                },
                {"label": _("Without a version in force"), "value": without.count(), "icon": "file-earmark-x", "tone": "warning"},
                {
                    "label": _("Average acknowledgement rate"), "value": average,
                    "suffix": "%" if average is not None else None, "icon": "patch-check", "tone": "accent",
                },
            ]
        return ctx


class PolicyTableBodyView(_PolicyListMixin, LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    template_name = "documents/policy_table_body.html"


class PolicyDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Policy
    permission_required = "documents.policy.read"
    template_name = "documents/policy_detail.html"
    context_object_name = "policy"

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("owner", "approver", "parent", "last_reviewed_by")
            .prefetch_related("scopes", "tags", "linked_requirements", "applies_to_roles")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        policy = self.object
        user = self.request.user
        versions = list(policy.versions.select_related("approved_by", "superseded_by").order_by("-created_at"))
        in_force = next((v for v in versions if v.workflow_state == VERSION_IN_FORCE), None)
        campaigns = list(
            _scoped(AcknowledgementCampaign.objects.filter(policy_version__policy=policy), user)
            .select_related("policy_version")
            .order_by("-created_at")
        )
        counts = _campaign_counts([c.pk for c in campaigns])
        for campaign in campaigns:
            campaign.rate = _rate(counts.get(campaign.pk, {}))
        launched = reportable_states(AcknowledgementCampaign)
        latest_launched = next(
            iter(sorted(
                (c for c in campaigns if c.workflow_state in launched),
                key=lambda c: (c.launched_at or c.created_at), reverse=True,
            )),
            None,
        )
        children = list(_scoped(policy.children.all(), user).select_related("owner").order_by("reference"))
        ctx.update({
            "versions": versions,
            "version_in_force": in_force,
            "campaigns": campaigns,
            "latest_campaign": latest_launched,
            "children": children,
            "children_living": [c for c in children if not c.is_terminal_state],
            "parent_retired": bool(policy.parent and policy.parent.is_terminal_state),
            "is_active": policy.workflow_state == POLICY_ACTIVE,
            "has_draft_version": any(not v.is_frozen for v in versions),
        })
        return ctx


class PolicyCreateView(LoginRequiredMixin, PermissionRequiredMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, CreateView):
    """Create a document and its first, draft version (``documents.policy.create``)."""

    model = Policy
    permission_required = "documents.policy.create"
    form_class = PolicyCreateForm
    template_name = "documents/policy_form.html"
    modal_template_name = "documents/policy_form_modal.html"
    modal_title_create = _l("New document")
    modal_title_update = _l("Edit document")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        with transaction.atomic():
            response = super().form_valid(form)
            form.save_first_version(self.object, self.request.user)
        return response

    def get_success_url(self):
        return reverse("documents:policy-detail", args=[self.object.pk])


class PolicyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    """Edit a document's identity (RG-DOC-08). The content changes only through a new version."""

    model = Policy
    permission_required = "documents.policy.update"
    form_class = PolicyForm
    template_name = "documents/policy_form.html"
    modal_template_name = "documents/policy_form_modal.html"
    modal_title_create = _l("New document")
    modal_title_update = _l("Edit document")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.object.is_terminal_state:
            _freeze(form, _("A retired document is a closed record and can no longer be edited."))
        return form

    def form_valid(self, form):
        if getattr(form, "frozen_note", None):
            form.add_error(None, form.frozen_note)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("documents:policy-detail", args=[self.object.pk])


class PolicyDeleteView(LoginRequiredMixin, ConfirmDeleteShellMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    model = Policy
    permission_required = "documents.policy.delete"
    template_name = "documents/policy_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("documents:policy-list")

    def get_refused_url(self):
        return reverse("documents:policy-detail", args=[self.object.pk])


class _PolicyActFormView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, FormView):
    """A drawer form acting on one document : the document is resolved through its scopes."""

    page_form_nav = "documents:policy-list"

    @cached_property
    def policy(self):
        return _scoped_get(Policy, self.request, self.kwargs["pk"])

    def get_success_url(self):
        return reverse("documents:policy-detail", args=[self.policy.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["policy"] = self.policy
        if not ctx.get("is_modal"):
            ctx["cancel_url"] = self.get_success_url()
            ctx["form_nav"] = self.page_form_nav
            ctx["form_accent"] = "documents"
            ctx["form_parent_label"] = self.policy.reference
            ctx["form_parent_url"] = self.get_success_url()
        return ctx


class PolicyRecordReviewView(_PolicyActFormView):
    """RG-DOC-13 : "Reviewed, no change" closes a review cycle without a new version."""

    permission_required = "documents.policy.approve"
    form_class = RecordReviewForm
    template_name = "documents/policy_record_review_form.html"
    modal_template_name = "documents/policy_record_review_form_modal.html"
    modal_title_create = _l("Reviewed, no change")

    def form_valid(self, form):
        try:
            self.policy.record_review(self.request.user, form.cleaned_data.get("comment", ""))
        except DomainRefusalError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        next_review = self.policy.next_review_date
        messages.success(self.request, _("The review was recorded. Next review : %(date)s.") % {
            "date": date_format(next_review, "SHORT_DATE_FORMAT") if next_review else "-",
        })
        return super().form_valid(form)


class PolicyNewVersionView(_PolicyActFormView):
    """RG-DOC-05 : draft the next version from the one in force, then open it."""

    permission_required = "documents.policy.update"
    form_class = NewVersionForm
    template_name = "documents/policy_new_version_form.html"
    modal_template_name = "documents/policy_new_version_form_modal.html"
    modal_title_create = _l("New version")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["policy"] = self.policy
        return kwargs

    def form_valid(self, form):
        if self.policy.is_terminal_state:
            form.add_error(None, _("A retired document cannot receive a new version."))
            return self.form_invalid(form)
        try:
            version = self.policy.new_version(self.request.user, bump=form.cleaned_data["bump"])
        except DomainRefusalError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        url = reverse("documents:policyversion-detail", args=[version.pk])
        messages.success(self.request, _("Version %(label)s was drafted.") % {"label": version.version_label})
        if is_drawer_request(self.request):
            return HttpResponse(status=204, headers={"HX-Redirect": url})
        return redirect(url)


# ══ PolicyVersion ══════════════════════════════════════════


class PolicyVersionDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = PolicyVersion
    permission_required = "documents.policy.read"
    template_name = "documents/policyversion_detail.html"
    context_object_name = "version"

    def get_queryset(self):
        return super().get_queryset().select_related("policy", "approved_by", "superseded_by", "created_by")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        version = self.object
        campaigns = list(_scoped(version.campaigns.all(), self.request.user).order_by("-created_at"))
        counts = _campaign_counts([c.pk for c in campaigns])
        for campaign in campaigns:
            campaign.rate = _rate(counts.get(campaign.pk, {}))
        ctx.update({
            "policy": version.policy,
            "campaigns": campaigns,
            "current_in_force": version.policy.version_in_force,
            "is_in_force": version.workflow_state == VERSION_IN_FORCE,
        })
        return ctx


class PolicyVersionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    """Edit a draft version; a submitted one renders frozen (RG-DOC-02)."""

    model = PolicyVersion
    permission_required = "documents.policy.update"
    form_class = PolicyVersionForm
    template_name = "documents/policyversion_form.html"
    modal_template_name = "documents/policyversion_form_modal.html"
    modal_title_create = _l("New version")
    modal_title_update = _l("Edit version")

    def get_form_parent(self):
        return self.object.policy

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValidationError as exc:  # the model's own frozen guard, as a last resort
            form.add_error(None, exc)
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("documents:policyversion-detail", args=[self.object.pk])


class PolicyVersionDeleteView(LoginRequiredMixin, ConfirmDeleteShellMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    model = PolicyVersion
    permission_required = "documents.policy.delete"
    template_name = "documents/policyversion_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("documents:policy-detail", args=[self.object.policy_id])

    def get_refused_url(self):
        return reverse("documents:policyversion-detail", args=[self.object.pk])


class PolicyVersionPdfView(LoginRequiredMixin, View):
    """Serve a version as a PDF : the attached copy, else the rich text rendered (WeasyPrint).

    Two ways in, both checked : a reader of the register (``documents.policy.read``
    and the document's scopes), or the addressee of a campaign targeting this
    very version, who must be able to read what they are asked to acknowledge
    whatever their permissions and scopes (RG-DOC-22).
    """

    def get(self, request, pk):
        version = self._resolve(request, pk)
        try:
            data = version.render_pdf()
        except (ImportError, OSError):
            # The text of a version without an attached PDF is rendered by
            # WeasyPrint, whose native libraries may be missing on a host.
            messages.error(request, _("The PDF could not be generated on this server. The text of the version stays readable on its page."))
            if request.user.has_perm("documents.policy.read"):
                return redirect("documents:policyversion-detail", pk=version.pk)
            return redirect("documents:acknowledge-list")
        name = version.file_name if version.has_pdf else f"{version.policy.reference}-v{version.version_label}.pdf"
        response = HttpResponse(data, content_type="application/pdf")
        response["Content-Disposition"] = _attachment_disposition(name)
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def _resolve(self, request, pk):
        qs = PolicyVersion.objects.select_related("policy")
        user = request.user
        if user.has_perm("documents.policy.read"):
            found = _scoped(qs, user).filter(pk=pk).first()
            if found is not None:
                return found
        own = qs.filter(pk=pk, campaigns__acknowledgements__user=user).first()
        if own is None:
            raise Http404
        return own


# ══ AcknowledgementCampaign ════════════════════════════════

CAMPAIGN_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": _state_options(CAMPAIGN_STATES)},
]
CAMPAIGN_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Reference")},
    {"param": "name", "field": "name", "label": _l("Name")},
]
CAMPAIGN_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "document", "label": _l("Document")},
    {"key": "due_date", "label": _l("Due date")},
    {"key": "audience", "label": _l("Audience")},
    {"key": "rate", "label": _l("Completion rate")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
CAMPAIGN_SORTABLE_FIELDS = {
    "reference": "reference",
    "name": "name",
    "document": "policy_version__policy__reference",
    "due_date": "due_date",
    "status": "workflow_state",
}
CAMPAIGN_SEARCH_FIELDS = ["reference", "name", "policy_version__policy__title", "policy_version__policy__reference"]


def _campaign_queryset(qs):
    return (
        qs.select_related("policy_version", "policy_version__policy")
        .prefetch_related("scopes", "tags")
        .annotate(
            audience_count=Count("acknowledgements", distinct=True),
            acknowledged_count=Count(
                "acknowledgements", filter=Q(acknowledgements__status=AcknowledgementStatus.ACKNOWLEDGED), distinct=True,
            ),
            excused_count=Count(
                "acknowledgements", filter=Q(acknowledgements__status=AcknowledgementStatus.EXCUSED), distinct=True,
            ),
        )
    )


def _annotated_rate(campaign):
    if not campaign.audience_count:
        return None
    denominator = campaign.audience_count - campaign.excused_count
    return round(100 * campaign.acknowledged_count / denominator) if denominator else 0


class _CampaignListMixin:
    model = AcknowledgementCampaign
    permission_required = "documents.acknowledgement.read"
    context_object_name = "campaigns"
    paginate_by = PAGE_SIZE
    sortable_fields = CAMPAIGN_SORTABLE_FIELDS
    default_sort = "due_date"
    default_sort_order = "desc"
    search_fields = CAMPAIGN_SEARCH_FIELDS
    filter_groups = CAMPAIGN_FILTER_GROUPS
    text_filters = CAMPAIGN_TEXT_FILTERS

    def get_queryset(self):
        qs = _campaign_queryset(super().get_queryset())
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rows = list(ctx.get(self.context_object_name) or [])
        for campaign in rows:
            campaign.rate = _annotated_rate(campaign)
        ctx[self.context_object_name] = rows
        return ctx


class CampaignListView(_CampaignListMixin, LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    """Who was asked to acknowledge what, and how far each campaign got (A.5.1, clause 7.3)."""

    columns = CAMPAIGN_COLUMNS
    template_name = "documents/campaign_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            base = base.order_by()
            running = base.filter(workflow_state=CAMPAIGN_RUNNING)
            launched = reportable(base)
            counts = _campaign_counts(launched.values_list("pk", flat=True))
            pending = PolicyAcknowledgement.objects.filter(
                campaign__in=running, status=AcknowledgementStatus.PENDING,
            ).count()
            average = _average(_rate(c) for c in counts.values())
            ctx["list_kpis"] = [
                {
                    "label": _("Running campaigns"), "value": running.count(), "icon": "broadcast", "tone": "info",
                    "url": f"{reverse('documents:campaign-list')}?status={CAMPAIGN_RUNNING}",
                },
                {
                    "label": _("Past due date"), "value": running.filter(due_date__lt=timezone.localdate()).count(),
                    "icon": "calendar-x", "tone": "danger",
                },
                {"label": _("Pending acknowledgements"), "value": pending, "icon": "hourglass-split", "tone": "warning"},
                {
                    "label": _("Average completion rate"), "value": average,
                    "suffix": "%" if average is not None else None, "icon": "patch-check", "tone": "accent",
                },
            ]
        return ctx


class CampaignTableBodyView(_CampaignListMixin, LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin, AdvancedFilterMixin, ScopeFilterMixin, SortableListMixin, ListView):
    template_name = "documents/campaign_table_body.html"


AUDIENCE_STATUS_PARAM = "ack_status"


class CampaignDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = AcknowledgementCampaign
    permission_required = "documents.acknowledgement.read"
    template_name = "documents/campaign_detail.html"
    context_object_name = "campaign"

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("policy_version", "policy_version__policy")
            .prefetch_related("scopes", "tags", "audience_users", "audience_groups", "audience_roles")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campaign = self.object
        counts = campaign.counts
        rows = campaign.acknowledgements.select_related("user", "excused_by")
        current = self.request.GET.get(AUDIENCE_STATUS_PARAM, "")
        if current in AcknowledgementStatus.values:
            rows = rows.filter(status=current)
        else:
            current = ""
        base_url = reverse("documents:acknowledgementcampaign-detail", args=[campaign.pk])
        ctx.update({
            "counts": counts,
            "rate": _rate({k: v for k, v in counts.items() if k != "total"}),
            "audience_rows": list(rows),
            "audience_filter": current,
            "audience_filters": [
                {"value": "", "label": _("All"), "count": counts["total"], "active": not current, "url": base_url},
            ] + [
                {
                    "value": status.value, "label": status.label, "count": counts[status.value],
                    "active": current == status.value,
                    "url": f"{base_url}?{AUDIENCE_STATUS_PARAM}={status.value}",
                }
                for status in AcknowledgementStatus
            ],
            "is_running": campaign.workflow_state == CAMPAIGN_RUNNING,
            "is_draft": campaign.is_deletable,
            "statement_preview": campaign.statement_for(),
        })
        return ctx


class CampaignCreateView(LoginRequiredMixin, PermissionRequiredMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    model = AcknowledgementCampaign
    permission_required = "documents.acknowledgement.create"
    form_class = AcknowledgementCampaignForm
    template_name = "documents/campaign_form.html"
    modal_template_name = "documents/campaign_form_modal.html"
    page_form_nav = "documents:campaign-list"
    modal_title_create = _l("New acknowledgement campaign")
    modal_title_update = _l("Edit acknowledgement campaign")

    @cached_property
    def initial_version(self):
        """The version named by ``?version=``, when the user may see it."""
        pk = self.request.GET.get("version")
        if not pk:
            return None
        try:
            return _scoped(PolicyVersion.objects.select_related("policy"), self.request.user).filter(pk=pk).first()
        except (ValueError, ValidationError):
            return None

    def get_initial(self):
        initial = super().get_initial()
        version = self.initial_version
        if version is not None:
            policy = version.policy
            initial.update({
                "policy_version": version.pk,
                "name": f"{policy.title} {version.version_label}",
                "audience_roles": list(policy.applies_to_roles.values_list("pk", flat=True)),
                "scopes": list(policy.scopes.all()),
            })
        return initial

    def get_form_parent(self):
        version = self.initial_version
        return version.policy if version is not None else None

    def get_success_url(self):
        return reverse("documents:acknowledgementcampaign-detail", args=[self.object.pk])


class CampaignUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, UpdateView):
    model = AcknowledgementCampaign
    permission_required = "documents.acknowledgement.update"
    form_class = AcknowledgementCampaignForm
    template_name = "documents/campaign_form.html"
    modal_template_name = "documents/campaign_form_modal.html"
    page_form_nav = "documents:campaign-list"
    modal_title_create = _l("New acknowledgement campaign")
    modal_title_update = _l("Edit acknowledgement campaign")

    def get_success_url(self):
        return reverse("documents:acknowledgementcampaign-detail", args=[self.object.pk])


class CampaignDeleteView(LoginRequiredMixin, ConfirmDeleteShellMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    model = AcknowledgementCampaign
    permission_required = "documents.acknowledgement.delete"
    template_name = "documents/campaign_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("documents:campaign-list")

    def get_refused_url(self):
        return reverse("documents:acknowledgementcampaign-detail", args=[self.object.pk])


class CampaignAddNewcomersView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """RG-DOC-15 : re-resolve the audience of a running campaign, add the missing rows."""

    permission_required = "documents.acknowledgement.update"
    http_method_names = ["post"]

    def post(self, request, pk):
        campaign = _scoped_get(AcknowledgementCampaign, request, pk)
        try:
            rows = campaign.add_newcomers(request.user)
        except DomainRefusalError as exc:
            messages.error(request, str(exc))
        else:
            if rows:
                messages.success(request, ngettext(
                    "%(n)d newcomer added to the campaign.", "%(n)d newcomers added to the campaign.", len(rows),
                ) % {"n": len(rows)})
            else:
                messages.info(request, _("No newcomer : everyone in the audience already has a row."))
        return redirect("documents:acknowledgementcampaign-detail", pk=campaign.pk)


class AcknowledgementExcuseView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, FormView):
    """RG-DOC-19 : excuse a pending addressee, with a reason."""

    permission_required = "documents.acknowledgement.update"
    form_class = ExcuseForm
    template_name = "documents/acknowledgement_excuse_form.html"
    modal_template_name = "documents/acknowledgement_excuse_form_modal.html"
    modal_title_create = _l("Excuse from the campaign")

    @cached_property
    def acknowledgement(self):
        qs = PolicyAcknowledgement.objects.select_related("user", "campaign", "campaign__policy_version__policy")
        return _scoped_get(PolicyAcknowledgement, self.request, self.kwargs["pk"], qs=qs)

    def get_success_url(self):
        return reverse("documents:acknowledgementcampaign-detail", args=[self.acknowledgement.campaign_id])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["acknowledgement"] = self.acknowledgement
        if not ctx.get("is_modal"):
            ctx["cancel_url"] = self.get_success_url()
            ctx["form_nav"] = "documents:campaign-list"
            ctx["form_accent"] = "documents"
            ctx["form_parent_label"] = self.acknowledgement.campaign.reference
            ctx["form_parent_url"] = self.get_success_url()
        return ctx

    def form_valid(self, form):
        try:
            self.acknowledgement.excuse(self.request.user, form.cleaned_data["reason"])
        except DomainRefusalError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, _("%(name)s was excused.") % {"name": self.acknowledgement.user.display_name})
        return super().form_valid(form)


# ══ To acknowledge : the current user's own rows ═══════════


def _own_rows(user):
    """The current user's rows, and only theirs (RG-DOC-17). No scope filter (RG-DOC-22)."""
    return PolicyAcknowledgement.objects.filter(user=user).select_related(
        "campaign", "campaign__policy_version", "campaign__policy_version__policy",
    )


class AcknowledgeListView(LoginRequiredMixin, TemplateView):
    template_name = "documents/acknowledge_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rows = _own_rows(self.request.user)
        pending = list(
            rows.filter(status=AcknowledgementStatus.PENDING, campaign__workflow_state=CAMPAIGN_RUNNING)
            .order_by("campaign__due_date", "requested_at")
        )
        history = list(rows.exclude(status=AcknowledgementStatus.PENDING).order_by("-acknowledged_at", "-requested_at"))
        today = timezone.localdate()
        next_due = min((r.campaign.due_date for r in pending), default=None)
        ctx.update({
            "pending": pending,
            "history": history,
            "overdue_count": sum(1 for r in pending if r.campaign.due_date < today),
            "acknowledged_count": sum(1 for r in history if r.status == AcknowledgementStatus.ACKNOWLEDGED),
            "next_due": next_due,
            "today": today,
        })
        return ctx


class AcknowledgeView(LoginRequiredMixin, DetailView):
    """Read a version and acknowledge it : the addressee's own act (RG-DOC-16, RG-DOC-17)."""

    template_name = "documents/acknowledge.html"
    context_object_name = "acknowledgement"

    def get_queryset(self):
        return _own_rows(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        row = self.object
        campaign = row.campaign
        ctx.update({
            "campaign": campaign,
            "version": campaign.policy_version,
            "policy": campaign.policy_version.policy,
            "statement_text": row.statement or campaign.statement_for(),
            "can_acknowledge": row.is_pending and campaign.workflow_state == CAMPAIGN_RUNNING,
            "is_overdue": row.is_pending and campaign.due_date < timezone.localdate(),
        })
        return ctx

    def post(self, request, *args, **kwargs):
        row = self.get_object()
        try:
            row.acknowledge(request.user, channel=AcknowledgementChannel.WEB)
        except DomainRefusalError as exc:
            messages.error(request, str(exc))
            return redirect("documents:acknowledge", pk=row.pk)
        messages.success(request, _("Thank you : your acknowledgement of %(title)s version %(label)s is recorded.") % {
            "title": row.campaign.policy_version.policy.title,
            "label": row.campaign.policy_version.version_label,
        })
        return redirect("documents:acknowledge-list")

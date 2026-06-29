from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import ApprovableUpdateMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, ScopeFilterMixin, WorkflowStepperMixin
from accounts.views import PermissionRequiredMixin
from core.mixins import (
    AdvancedFilterMixin,
    ColumnPreferenceMixin,
    HtmxFormMixin,
    ListSummaryMixin,
    PredefinedFilterMixin,
    SavedFilterMixin,
    SortableListMixin,
)
from core.query_params import parse_int
from compliance.models import Framework
from context.constants import Criticality, SiteType
from context.models import Scope, Site
from .constants import (
    CertificateStatus,
    ContractStatus,
    DependencyType,
    EssentialAssetStatus,
    EssentialAssetType,
    SiteAssetDependencyType,
    SiteSupplierDependencyType,
    SupplierDependencyType,
    SupplierStatus,
    SupportAssetStatus,
    SupportAssetType,
)
from .forms import (
    AssetDependencyForm,
    AssetGroupCreateForm,
    AssetGroupUpdateForm,
    CertificateCreateForm,
    CertificateUpdateForm,
    ContractCreateForm,
    ContractUpdateForm,
    EssentialAssetCreateForm,
    EssentialAssetUpdateForm,
    SiteAssetDependencyForm,
    SiteCreateForm,
    SiteUpdateForm,
    SiteSupplierDependencyForm,
    SupplierDependencyForm,
    SupplierContactForm,
    SupplierCreateForm,
    SupplierUpdateForm,
    SupplierRequirementForm,
    SupplierRequirementReviewForm,
    SupplierTypeForm,
    SupplierTypeRequirementForm,
    SupplierTypeRequirementFormSet,
    SupportAssetCreateForm,
    SupportAssetUpdateForm,
)
from .models import (
    AssetDependency,
    AssetGroup,
    Certificate,
    Contract,
    EssentialAsset,
    SiteAssetDependency,
    SiteSupplierDependency,
    Supplier,
    SupplierContact,
    SupplierDependency,
    SupplierRequirement,
    SupplierRequirementReview,
    SupplierType,
    SupplierTypeRequirement,
    SupportAsset,
)


class CreatedByMixin:
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)




class ApproveView(LoginRequiredMixin, View):
    """Generic approve view for assets domain models."""

    model = None
    permission_feature = None
    success_url = None

    def post(self, request, pk):
        from core.models import VersioningConfig
        from core.redirects import safe_redirect_target

        obj = get_object_or_404(self.model, pk=pk)
        if not VersioningConfig.is_approval_enabled(self.model):
            messages.error(request, _("Approval is disabled for this item type."))
            return redirect(safe_redirect_target(request, request.META.get("HTTP_REFERER")))
        feature = self.permission_feature or self.model._meta.model_name
        codename = f"assets.{feature}.approve"
        if not request.user.is_superuser and not request.user.has_perm(codename):
            messages.error(request, _("You do not have permission to approve this item."))
            return redirect(safe_redirect_target(request, request.META.get("HTTP_REFERER")))
        obj.is_approved = True
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=["is_approved", "approved_by", "approved_at"])
        messages.success(request, _("Item approved."))
        return redirect(safe_redirect_target(request, request.META.get("HTTP_REFERER"), self.success_url or "/"))


# ── Essential Asset ─────────────────────────────────────────

ESSENTIAL_ASSET_FILTER_GROUPS = [
    {"param": "type", "field": "type", "label": _l("Type"), "options": EssentialAssetType.choices},
    {"param": "status", "field": "status", "label": _l("Status"), "options": EssentialAssetStatus.choices},
]
ESSENTIAL_ASSET_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
ESSENTIAL_ASSET_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "owner", "label": _l("Owner")},
    {"key": "cia", "label": _l("C / I / A")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class EssentialAssetListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = EssentialAsset
    template_name = "assets/essential_asset_list.html"
    context_object_name = "assets"
    status_field = "status"
    filter_groups = ESSENTIAL_ASSET_FILTER_GROUPS
    text_filters = ESSENTIAL_ASSET_TEXT_FILTERS
    columns = ESSENTIAL_ASSET_COLUMNS
    permission_required = "assets.essential_asset.read"
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "category": "category",
        "owner": "owner__last_name",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name", "owner__last_name", "owner__first_name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class EssentialAssetDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, WorkflowStepperMixin, DetailView):
    model = EssentialAsset
    template_name = "assets/essential_asset_detail.html"
    context_object_name = "asset"
    permission_required = "assets.essential_asset.read"
    approval_feature = "essential_asset"
    approve_url_name = "assets:essential-asset-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dependencies"] = self.object.dependencies_as_essential.select_related(
            "support_asset"
        )
        ctx["valuations"] = self.object.valuations.all()[:10]
        return ctx


class EssentialAssetCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = EssentialAsset
    form_class = EssentialAssetCreateForm
    template_name = "assets/essential_asset_form.html"
    permission_required = "assets.essential_asset.create"
    modal_template_name = "assets/essential_asset_form_modal.html"
    modal_title_create = _l("New essential asset")
    modal_title_update = _l("Edit essential asset")
    success_url = reverse_lazy("assets:essential-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class EssentialAssetUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = EssentialAsset
    form_class = EssentialAssetUpdateForm
    template_name = "assets/essential_asset_form.html"
    permission_required = "assets.essential_asset.update"
    modal_template_name = "assets/essential_asset_form_modal.html"
    modal_title_create = _l("New essential asset")
    modal_title_update = _l("Edit essential asset")
    success_url = reverse_lazy("assets:essential-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class EssentialAssetDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = EssentialAsset
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.essential_asset.delete"
    success_url = reverse_lazy("assets:essential-asset-list")


# ── Contract (Documents) ────────────────────────────────────

def _attachment_disposition(filename):
    """Build a safe Content-Disposition value (no header injection / breakout)."""
    safe = "".join(ch for ch in (filename or "") if ch not in '"\\\r\n').strip() or "document.pdf"
    return f"attachment; filename=\"{safe}\"; filename*=UTF-8''{quote(safe)}"


CONTRACT_FILTER_GROUPS = [
    {"param": "status", "field": "status", "label": _l("Status"), "options": ContractStatus.choices},
]
CONTRACT_TEXT_FILTERS = [
    {"param": "label", "field": "label", "label": _l("Title")},
]
CONTRACT_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "label", "label": _l("Title"), "always": True},
    {"key": "parties", "label": _l("Parties")},
    {"key": "end_date", "label": _l("End date")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class ContractListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Contract
    template_name = "assets/contract_list.html"
    context_object_name = "contracts"
    status_field = "status"
    filter_groups = CONTRACT_FILTER_GROUPS
    text_filters = CONTRACT_TEXT_FILTERS
    columns = CONTRACT_COLUMNS
    permission_required = "assets.contract.read"
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "label": "label",
        "end_date": "end_date",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "label", "notes"]
    paginate_by = None  # tree view shows the whole contract / amendment hierarchy

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("parent", "supersedes")
            .prefetch_related("scopes", "suppliers", "clients", "superseded_by")
        )
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["contracts"] = self._build_tree(list(ctx["contracts"]))
        return ctx

    @staticmethod
    def _build_tree(contracts):
        """Return contracts in depth-first order: a top-level contract followed
        by its amendments (avenants), annotated with tree_level / tree_indent.

        Sibling order is preserved from the queryset, so server-side sorting
        applies within each parent group while keeping the hierarchy intact.
        """
        by_parent = {}
        for c in contracts:
            by_parent.setdefault(c.parent_id, []).append(c)

        result = []
        visited = set()

        def walk(parent_id, level):
            for c in by_parent.get(parent_id, []):
                c.tree_level = level
                c.tree_indent = level * 24
                result.append(c)
                visited.add(c.pk)
                walk(c.pk, level + 1)

        walk(None, 0)

        # Orphans (a parent filtered out by scope access / facets).
        for c in contracts:
            if c.pk not in visited:
                c.tree_level = 0
                c.tree_indent = 0
                result.append(c)

        return result


class ContractDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Contract
    template_name = "assets/contract_detail.html"
    context_object_name = "contract"
    permission_required = "assets.contract.read"
    approval_feature = "contract"
    approve_url_name = "assets:contract-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["amendments"] = self.object.amendments.prefetch_related(
            "suppliers", "clients"
        )
        suppliers = self.object.suppliers.all()
        clients = self.object.clients.all()
        ctx["suppliers"] = suppliers
        ctx["clients"] = clients
        ctx["party_count"] = suppliers.count() + clients.count()
        ctx["superseded_by"] = self.object.superseded_by.all()
        return ctx


class ContractCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Contract
    form_class = ContractCreateForm
    template_name = "assets/contract_form.html"
    permission_required = "assets.contract.create"
    modal_template_name = "assets/contract_form_modal.html"
    modal_title_create = _l("New contract")
    modal_title_update = _l("Edit contract")
    success_url = reverse_lazy("assets:contract-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ContractUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Contract
    form_class = ContractUpdateForm
    template_name = "assets/contract_form.html"
    permission_required = "assets.contract.update"
    modal_template_name = "assets/contract_form_modal.html"
    modal_title_create = _l("New contract")
    modal_title_update = _l("Edit contract")
    success_url = reverse_lazy("assets:contract-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ContractDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Contract
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.contract.delete"
    success_url = reverse_lazy("assets:contract-list")


class ContractDocumentDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Stream a contract's attached PDF, scope-filtered and permission-gated."""

    permission_required = "assets.contract.read"

    def get(self, request, pk):
        qs = Contract.objects.all()
        if not request.user.is_superuser:
            scope_ids = request.user.get_allowed_scope_ids()
            if scope_ids is not None:
                qs = qs.filter(scopes__id__in=scope_ids).distinct()
        contract = get_object_or_404(qs, pk=pk)
        data = contract.get_file_bytes()
        if not data:
            raise Http404()
        resp = HttpResponse(
            data, content_type=contract.content_type or "application/pdf"
        )
        resp["Content-Disposition"] = _attachment_disposition(
            contract.file_name or f"{contract.reference}.pdf"
        )
        return resp


# ── Certificate (Documents) ─────────────────────────────────

CERTIFICATE_TEXT_FILTERS = [
    {"param": "label", "field": "label", "label": _l("Title")},
    {"param": "issuer", "field": "issuer", "label": _l("Certification body")},
]
CERTIFICATE_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "label", "label": _l("Title"), "always": True},
    {"key": "framework", "label": _l("Framework")},
    {"key": "issuer", "label": _l("Certification body")},
    {"key": "expiry_date", "label": _l("Expiry date")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class CertificateListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Certificate
    template_name = "assets/certificate_list.html"
    context_object_name = "certificates"
    status_field = "status"
    text_filters = CERTIFICATE_TEXT_FILTERS
    columns = CERTIFICATE_COLUMNS
    permission_required = "assets.certificate.read"
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "label": "label",
        "framework": "framework__short_name",
        "issuer": "issuer",
        "expiry_date": "expiry_date",
        "workflow_state": "workflow_state",
    }
    default_sort = "-expiry_date"
    search_fields = [
        "reference", "label", "issuer", "certificate_number", "notes",
        "framework__name", "framework__short_name",
    ]

    @property
    def filter_groups(self):
        # The framework (référentiel) facet is data-driven, so build its options
        # from the existing frameworks at request time.
        return [
            {
                "param": "framework",
                "field": "framework",
                "label": _l("Framework"),
                "options": [
                    (str(fw.pk), fw.short_name or fw.name)
                    for fw in Framework.objects.order_by("short_name", "name")
                ],
            },
            {"param": "status", "field": "status", "label": _l("Status"), "options": CertificateStatus.choices},
        ]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("framework", "supersedes")
            .prefetch_related("scopes", "sites", "tags", "superseded_by")
        )
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class CertificateDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Certificate
    template_name = "assets/certificate_detail.html"
    context_object_name = "certificate"
    permission_required = "assets.certificate.read"
    approval_feature = "certificate"
    approve_url_name = "assets:certificate-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sites"] = self.object.sites.all()
        ctx["superseded_by"] = self.object.superseded_by.all()
        return ctx


class CertificateCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Certificate
    form_class = CertificateCreateForm
    template_name = "assets/certificate_form.html"
    permission_required = "assets.certificate.create"
    modal_template_name = "assets/certificate_form_modal.html"
    modal_title_create = _l("New certificate")
    modal_title_update = _l("Edit certificate")
    success_url = reverse_lazy("assets:certificate-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class CertificateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Certificate
    form_class = CertificateUpdateForm
    template_name = "assets/certificate_form.html"
    permission_required = "assets.certificate.update"
    modal_template_name = "assets/certificate_form_modal.html"
    modal_title_create = _l("New certificate")
    modal_title_update = _l("Edit certificate")
    success_url = reverse_lazy("assets:certificate-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class CertificateDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Certificate
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.certificate.delete"
    success_url = reverse_lazy("assets:certificate-list")


class CertificateDocumentDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Stream a certificate's attached PDF, scope-filtered and permission-gated."""

    permission_required = "assets.certificate.read"

    def get(self, request, pk):
        qs = Certificate.objects.all()
        if not request.user.is_superuser:
            scope_ids = request.user.get_allowed_scope_ids()
            if scope_ids is not None:
                qs = qs.filter(scopes__id__in=scope_ids).distinct()
        certificate = get_object_or_404(qs, pk=pk)
        data = certificate.get_file_bytes()
        if not data:
            raise Http404()
        resp = HttpResponse(
            data, content_type=certificate.content_type or "application/pdf"
        )
        resp["Content-Disposition"] = _attachment_disposition(
            certificate.file_name or f"{certificate.reference}.pdf"
        )
        return resp


# ── Support Asset ───────────────────────────────────────────

SUPPORT_ASSET_FILTER_GROUPS = [
    {"param": "type", "field": "type", "label": _l("Type"), "options": SupportAssetType.choices},
    {"param": "status", "field": "status", "label": _l("Status"), "options": SupportAssetStatus.choices},
]
SUPPORT_ASSET_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
SUPPORT_ASSET_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "owner", "label": _l("Owner")},
    {"key": "cia", "label": _l("C / I / A")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class SupportAssetListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = SupportAsset
    template_name = "assets/support_asset_list.html"
    context_object_name = "assets"
    status_field = "status"
    filter_groups = SUPPORT_ASSET_FILTER_GROUPS
    text_filters = SUPPORT_ASSET_TEXT_FILTERS
    columns = SUPPORT_ASSET_COLUMNS
    permission_required = "assets.support_asset.read"
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "category": "category",
        "owner": "owner__last_name",
        "workflow_state": "workflow_state",
        "eol": "end_of_life_date",
    }
    default_sort = "reference"
    search_fields = ["reference", "name", "owner__last_name", "owner__first_name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class SupportAssetDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, WorkflowStepperMixin, DetailView):
    model = SupportAsset
    template_name = "assets/support_asset_detail.html"
    context_object_name = "asset"
    permission_required = "assets.support_asset.read"
    approval_feature = "support_asset"
    approve_url_name = "assets:support-asset-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dependencies"] = self.object.dependencies_as_support.select_related(
            "essential_asset"
        )
        ctx["children"] = self.object.children.all()
        return ctx


class SupportAssetCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = SupportAsset
    form_class = SupportAssetCreateForm
    template_name = "assets/support_asset_form.html"
    permission_required = "assets.support_asset.create"
    modal_template_name = "assets/support_asset_form_modal.html"
    modal_title_create = _l("New support asset")
    modal_title_update = _l("Edit support asset")
    success_url = reverse_lazy("assets:support-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupportAssetUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = SupportAsset
    form_class = SupportAssetUpdateForm
    template_name = "assets/support_asset_form.html"
    permission_required = "assets.support_asset.update"
    modal_template_name = "assets/support_asset_form_modal.html"
    modal_title_create = _l("New support asset")
    modal_title_update = _l("Edit support asset")
    success_url = reverse_lazy("assets:support-asset-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupportAssetDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupportAsset
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.support_asset.delete"
    success_url = reverse_lazy("assets:support-asset-list")


# ── Dependency ──────────────────────────────────────────────

DEPENDENCY_FILTER_GROUPS = [
    {"param": "type", "field": "dependency_type", "label": _l("Type"), "options": DependencyType.choices},
    {"param": "criticality", "field": "criticality", "label": _l("Criticality"), "options": Criticality.choices},
]
DEPENDENCY_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Ref.")},
]
DEPENDENCY_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "essential", "label": _l("Dependency"), "always": True},
    {"key": "type", "label": _l("Type")},
    {"key": "criticality", "label": _l("Criticality")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class DependencyListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = AssetDependency
    template_name = "assets/dependency_list.html"
    context_object_name = "dependencies"
    filter_groups = DEPENDENCY_FILTER_GROUPS
    text_filters = DEPENDENCY_TEXT_FILTERS
    columns = DEPENDENCY_COLUMNS
    permission_required = "assets.dependency.read"
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "essential": "essential_asset__name",
        "support": "support_asset__name",
        "type": "dependency_type",
        "criticality": "criticality",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "essential_asset__name", "support_asset__name"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("essential_asset", "support_asset")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class DependencyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreatedByMixin, CreateView):
    model = AssetDependency
    form_class = AssetDependencyForm
    template_name = "assets/dependency_form.html"
    permission_required = "assets.dependency.create"
    success_url = reverse_lazy("assets:dependency-list")


class DependencyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = AssetDependency
    form_class = AssetDependencyForm
    template_name = "assets/dependency_form.html"
    permission_required = "assets.dependency.update"
    success_url = reverse_lazy("assets:dependency-list")


class DependencyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = AssetDependency
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.dependency.delete"
    success_url = reverse_lazy("assets:dependency-list")


# ── Group ───────────────────────────────────────────────────

GROUP_FILTER_GROUPS = [
    {"param": "type", "field": "type", "label": _l("Type"), "options": SupportAssetType.choices},
]
GROUP_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
GROUP_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "owner", "label": _l("Owner")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class GroupListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = AssetGroup
    template_name = "assets/group_list.html"
    context_object_name = "groups"
    filter_groups = GROUP_FILTER_GROUPS
    text_filters = GROUP_TEXT_FILTERS
    columns = GROUP_COLUMNS
    permission_required = "assets.group.read"
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
        qs = super().get_queryset().select_related("owner").annotate(
            member_count=Count("members")
        )
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class GroupDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, WorkflowStepperMixin, DetailView):
    model = AssetGroup
    template_name = "assets/group_detail.html"
    context_object_name = "group"
    permission_required = "assets.group.read"
    approval_feature = "group"
    approve_url_name = "assets:group-approve"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("members")


class GroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = AssetGroup
    form_class = AssetGroupCreateForm
    template_name = "assets/group_form.html"
    permission_required = "assets.group.create"
    modal_template_name = "assets/group_form_modal.html"
    modal_title_create = _l("New asset group")
    modal_title_update = _l("Edit asset group")
    success_url = reverse_lazy("assets:group-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class GroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = AssetGroup
    form_class = AssetGroupUpdateForm
    template_name = "assets/group_form.html"
    permission_required = "assets.group.update"
    modal_template_name = "assets/group_form_modal.html"
    modal_title_create = _l("New asset group")
    modal_title_update = _l("Edit asset group")
    success_url = reverse_lazy("assets:group-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class GroupDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = AssetGroup
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.group.delete"
    success_url = reverse_lazy("assets:group-list")


# ── Supplier ──────────────────────────────────────────────

SUPPLIER_FILTER_GROUPS = [
    {"param": "status", "field": "status", "label": _l("Status"), "options": SupplierStatus.choices},
    {"param": "criticality", "field": "criticality", "label": _l("Criticality"), "options": Criticality.choices},
]
SUPPLIER_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
SUPPLIER_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "criticality", "label": _l("Criticality")},
    {"key": "owner", "label": _l("Owner")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class SupplierListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Supplier
    template_name = "assets/supplier_list.html"
    context_object_name = "suppliers"
    status_field = "status"
    filter_groups = SUPPLIER_FILTER_GROUPS
    text_filters = SUPPLIER_TEXT_FILTERS
    columns = SUPPLIER_COLUMNS
    permission_required = "assets.supplier.read"
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "criticality": "criticality",
        "contract_end": "contract_end_date",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name", "contact_name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner", "type")
        supplier_type = parse_int(self.request.GET.get("supplier_type"))
        if supplier_type is not None:
            qs = qs.filter(type_id=supplier_type)
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class SupplierDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Supplier
    template_name = "assets/supplier_detail.html"
    context_object_name = "supplier"
    permission_required = "assets.supplier.read"
    approval_feature = "supplier"
    approve_url_name = "assets:supplier-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reqs = list(
            self.object.requirements.select_related(
                "requirement", "verified_by", "source_type_requirement"
            ).prefetch_related("reviews")
        )
        ctx["requirements"] = reqs
        ctx["compliance_summary"] = self.object.requirement_compliance_summary
        type_requirements = list(self.object.type.requirements.all()) if self.object.type else []
        ctx["type_requirements"] = type_requirements

        # Unified compliance rows : every actual SupplierRequirement (labelled
        # "inherited" when it came from a type requirement, "specific" otherwise),
        # plus the type requirements not yet instantiated into a review (shown as
        # pending inherited rows). Avoids the previous two-table duplication.
        instantiated_type_ids = {
            r.source_type_requirement_id for r in reqs if r.source_type_requirement_id
        }
        rows = [
            {"kind": "requirement", "inherited": bool(r.source_type_requirement_id),
             "title": r.title or "", "req": r}
            for r in reqs
        ]
        rows += [
            {"kind": "type_template", "inherited": True, "title": tr.title or "", "type_req": tr}
            for tr in type_requirements
            if tr.pk not in instantiated_type_ids
        ]
        # Inherited rows grouped first, then specific; alphabetical within each.
        rows.sort(key=lambda r: (not r["inherited"], r["title"].lower()))
        ctx["compliance_rows"] = rows
        # Top-level contracts only (amendments are nested under their parent).
        ctx["contracts"] = (
            self.object.contracts.filter(parent__isnull=True)
            .prefetch_related("suppliers", "amendments")
        )
        return ctx


class SupplierCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Supplier
    form_class = SupplierCreateForm
    template_name = "assets/supplier_form.html"
    permission_required = "assets.supplier.create"
    modal_template_name = "assets/supplier_form_modal.html"
    modal_title_create = _l("New supplier")
    modal_title_update = _l("Edit supplier")
    success_url = reverse_lazy("assets:supplier-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupplierUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Supplier
    form_class = SupplierUpdateForm
    template_name = "assets/supplier_form.html"
    permission_required = "assets.supplier.update"
    modal_template_name = "assets/supplier_form_modal.html"
    modal_title_create = _l("New supplier")
    modal_title_update = _l("Edit supplier")
    success_url = reverse_lazy("assets:supplier-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SupplierDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Supplier
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"
    success_url = reverse_lazy("assets:supplier-list")


# ── Supplier Contacts ─────────────────────────────────────

class SupplierContactCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreateView):
    model = SupplierContact
    form_class = SupplierContactForm
    template_name = "assets/supplier_contact_form.html"
    modal_template_name = "assets/supplier_contact_form_modal.html"
    modal_title_create = _l("New contact")
    modal_title_update = _l("Edit contact")
    permission_required = "assets.supplier.update"

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, pk=kwargs["supplier_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.supplier
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.supplier.pk})


class SupplierContactUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UpdateView):
    model = SupplierContact
    form_class = SupplierContactForm
    template_name = "assets/supplier_contact_form.html"
    modal_template_name = "assets/supplier_contact_form_modal.html"
    modal_title_create = _l("New contact")
    modal_title_update = _l("Edit contact")
    permission_required = "assets.supplier.update"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.object.supplier
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.object.supplier.pk})


class SupplierContactDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierContact
    template_name = "assets/supplier_contact_confirm_delete_modal.html"
    permission_required = "assets.supplier.update"

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.object.supplier.pk})

    def form_valid(self, form):
        """Delete and, for HTMX, close the drawer + reload the detail page."""
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=204, headers={"HX-Trigger": "formSaved"})
        return redirect(success_url)


# ── Supplier Types ────────────────────────────────────────


SUPPLIER_TYPE_FILTER_GROUPS = []
SUPPLIER_TYPE_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
SUPPLIER_TYPE_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "requirements", "label": _l("Requirements")},
    {"key": "suppliers", "label": _l("Suppliers")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class SupplierTypeListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = SupplierType
    template_name = "assets/supplier_type_list.html"
    context_object_name = "supplier_types"
    filter_groups = SUPPLIER_TYPE_FILTER_GROUPS
    text_filters = SUPPLIER_TYPE_TEXT_FILTERS
    columns = SUPPLIER_TYPE_COLUMNS
    permission_required = "assets.supplier.read"
    sortable_fields = {"reference": "reference", "name": "name"}
    default_sort = "name"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .annotate(req_count=Count("requirements", distinct=True))
            .prefetch_related("suppliers")
        )
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class SupplierTypeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = SupplierType
    template_name = "assets/supplier_type_detail.html"
    context_object_name = "supplier_type"
    permission_required = "assets.supplier.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["requirements"] = self.object.requirements.all()
        ctx["suppliers"] = self.object.suppliers.prefetch_related("scopes").select_related("owner")
        return ctx


class SupplierTypeFormsetMixin:
    """Handle the requirements inline formset for SupplierType create/update."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["requirement_formset"] = SupplierTypeRequirementFormSet(
                self.request.POST, instance=self.object
            )
        else:
            ctx["requirement_formset"] = SupplierTypeRequirementFormSet(
                instance=self.object
            )
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["requirement_formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return redirect(self.get_success_url())
        return self.render_to_response(ctx)


class SupplierTypeCreateView(LoginRequiredMixin, PermissionRequiredMixin, SupplierTypeFormsetMixin, CreateView):
    model = SupplierType
    form_class = SupplierTypeForm
    template_name = "assets/supplier_type_form.html"
    permission_required = "assets.supplier.create"
    success_url = reverse_lazy("assets:supplier-type-list")


class SupplierTypeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SupplierTypeFormsetMixin, UpdateView):
    model = SupplierType
    form_class = SupplierTypeForm
    template_name = "assets/supplier_type_form.html"
    permission_required = "assets.supplier.update"
    success_url = reverse_lazy("assets:supplier-type-list")


class SupplierTypeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierType
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"
    success_url = reverse_lazy("assets:supplier-type-list")


# ── Supplier Type Requirements ───────────────────────────

class SupplierTypeRequirementCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SupplierTypeRequirement
    form_class = SupplierTypeRequirementForm
    template_name = "assets/supplier_type_requirement_form.html"
    permission_required = "assets.supplier.create"

    def dispatch(self, request, *args, **kwargs):
        self.supplier_type = get_object_or_404(SupplierType, pk=kwargs["type_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.supplier_type = self.supplier_type
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier_type"] = self.supplier_type
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-type-detail", kwargs={"pk": self.supplier_type.pk})


class SupplierTypeRequirementUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SupplierTypeRequirement
    form_class = SupplierTypeRequirementForm
    template_name = "assets/supplier_type_requirement_form.html"
    permission_required = "assets.supplier.update"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier_type"] = self.object.supplier_type
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-type-detail", kwargs={"pk": self.object.supplier_type.pk})


class SupplierTypeRequirementDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierTypeRequirement
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"

    def get_success_url(self):
        return reverse_lazy("assets:supplier-type-detail", kwargs={"pk": self.object.supplier_type.pk})


# ── Supplier Requirements ─────────────────────────────────

class SupplierRequirementCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SupplierRequirement
    form_class = SupplierRequirementForm
    template_name = "assets/supplier_requirement_form.html"
    permission_required = "assets.supplier.create"

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, pk=kwargs["supplier_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.supplier
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.supplier.pk})


class SupplierRequirementUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SupplierRequirement
    form_class = SupplierRequirementForm
    template_name = "assets/supplier_requirement_form.html"
    permission_required = "assets.supplier.update"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.object.supplier
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.object.supplier.pk})


class SupplierRequirementDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierRequirement
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.object.supplier.pk})


class SupplierRequirementDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = SupplierRequirement
    template_name = "assets/supplier_requirement_detail.html"
    context_object_name = "req"
    permission_required = "assets.supplier.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.object.supplier
        ctx["reviews"] = self.object.reviews.select_related("reviewer")
        return ctx


# ── Supplier Requirement Reviews ──────────────────────────

class _RequirementReviewModalBase(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreateView):
    """Shared base : evaluate a requirement in the HTMX drawer modal.

    Subclasses resolve the target ``SupplierRequirement`` (an existing one, or
    one instantiated on save from a type requirement). Saving records a review
    (compliance level + justification + evidence file) and rolls the result up
    onto the requirement's compliance status / verification.
    """

    model = SupplierRequirementReview
    form_class = SupplierRequirementReviewForm
    template_name = "assets/supplier_requirement_review_form.html"
    modal_template_name = "assets/supplier_requirement_review_form_modal.html"
    modal_title_create = _l("Evaluate requirement")
    modal_title_update = _l("Evaluate requirement")
    permission_required = "assets.supplier.create"

    def get_requirement(self):
        raise NotImplementedError

    def form_valid(self, form):
        req = self.get_requirement()
        form.instance.supplier_requirement = req
        form.instance.reviewer = self.request.user
        response = super().form_valid(form)
        req.compliance_status = form.instance.result
        req.verified_at = timezone.now()
        req.verified_by = self.request.user
        req.save(update_fields=["compliance_status", "verified_at", "verified_by", "updated_at"])
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["supplier"] = self.supplier
        ctx["requirement_title"] = self.requirement_title
        if ctx.get("is_modal") and self.requirement_title:
            ctx["modal_title"] = f'{_("Evaluate")} : {self.requirement_title}'
        return ctx

    def get_success_url(self):
        return reverse_lazy("assets:supplier-detail", kwargs={"pk": self.supplier.pk})


class SupplierRequirementReviewCreateView(_RequirementReviewModalBase):
    def dispatch(self, request, *args, **kwargs):
        self.supplier_requirement = get_object_or_404(
            SupplierRequirement.objects.select_related("supplier"),
            pk=kwargs["requirement_pk"],
        )
        self.supplier = self.supplier_requirement.supplier
        self.requirement_title = self.supplier_requirement.title
        return super().dispatch(request, *args, **kwargs)

    def get_requirement(self):
        return self.supplier_requirement


class SupplierRequirementReviewDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierRequirementReview
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier.delete"

    def get_success_url(self):
        return reverse_lazy(
            "assets:supplier-requirement-detail",
            kwargs={"pk": self.object.supplier_requirement.pk},
        )


class InstantiateTypeRequirementReviewView(_RequirementReviewModalBase):
    """Evaluate a type requirement from the drawer : on save, instantiate it as a
    SupplierRequirement for this supplier (idempotent), then record the review."""

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, pk=kwargs["supplier_pk"])
        self.type_req = get_object_or_404(SupplierTypeRequirement, pk=kwargs["type_req_pk"])
        self.requirement_title = self.type_req.title
        return super().dispatch(request, *args, **kwargs)

    def get_requirement(self):
        req, _created = SupplierRequirement.objects.get_or_create(
            supplier=self.supplier,
            source_type_requirement=self.type_req,
            defaults={"title": self.type_req.title, "description": self.type_req.description},
        )
        return req


class SupplierRequirementReviewHistoryView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Read-only evaluation history (reviews) for a requirement, shown in the drawer."""

    model = SupplierRequirement
    template_name = "assets/supplier_requirement_history_modal.html"
    context_object_name = "req"
    permission_required = "assets.supplier.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["reviews"] = self.object.reviews.select_related("reviewer")
        return ctx


# ── Supplier Dependencies ─────────────────────────────────

SUPPLIER_DEPENDENCY_FILTER_GROUPS = [
    {"param": "type", "field": "dependency_type", "label": _l("Type"), "options": SupplierDependencyType.choices},
    {"param": "criticality", "field": "criticality", "label": _l("Criticality"), "options": Criticality.choices},
]
SUPPLIER_DEPENDENCY_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Ref.")},
]
SUPPLIER_DEPENDENCY_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "support", "label": _l("Dependency"), "always": True},
    {"key": "type", "label": _l("Type")},
    {"key": "criticality", "label": _l("Criticality")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class SupplierDependencyListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = SupplierDependency
    template_name = "assets/supplier_dependency_list.html"
    context_object_name = "dependencies"
    filter_groups = SUPPLIER_DEPENDENCY_FILTER_GROUPS
    text_filters = SUPPLIER_DEPENDENCY_TEXT_FILTERS
    columns = SUPPLIER_DEPENDENCY_COLUMNS
    permission_required = "assets.supplier_dependency.read"
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "support": "support_asset__name",
        "supplier": "supplier__name",
        "type": "dependency_type",
        "criticality": "criticality",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "support_asset__name", "supplier__name"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("support_asset", "supplier")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class SupplierDependencyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreatedByMixin, CreateView):
    model = SupplierDependency
    form_class = SupplierDependencyForm
    template_name = "assets/supplier_dependency_form.html"
    permission_required = "assets.supplier_dependency.create"
    success_url = reverse_lazy("assets:supplier-dependency-list")


class SupplierDependencyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = SupplierDependency
    form_class = SupplierDependencyForm
    template_name = "assets/supplier_dependency_form.html"
    permission_required = "assets.supplier_dependency.update"
    success_url = reverse_lazy("assets:supplier-dependency-list")


class SupplierDependencyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SupplierDependency
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier_dependency.delete"
    success_url = reverse_lazy("assets:supplier-dependency-list")


# ── Sites ─────────────────────────────────────────────────

SITE_FILTER_GROUPS = [
    {"param": "type", "field": "type", "label": _l("Type"), "options": SiteType.choices},
]
SITE_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
SITE_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "type", "label": _l("Type")},
    {"key": "status", "label": _l("Status")},
    {"key": "tags", "label": _l("Tags")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class SiteListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ListView):
    model = Site
    template_name = "assets/site_list.html"
    context_object_name = "sites"
    filter_groups = SITE_FILTER_GROUPS
    text_filters = SITE_TEXT_FILTERS
    columns = SITE_COLUMNS
    permission_required = "context.site.read"

    def get_queryset(self):
        qs = super().get_queryset().select_related("parent_site")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sites"] = self._build_tree(list(ctx["sites"]))
        return ctx

    @staticmethod
    def _build_tree(sites):
        by_parent = {}
        for s in sites:
            by_parent.setdefault(s.parent_site_id, []).append(s)
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
        for s in sites:
            if s.pk not in visited:
                s.tree_level = 0
                s.tree_indent = 0
                result.append(s)
        return result


class SiteDetailView(LoginRequiredMixin, PermissionRequiredMixin, ApprovalContextMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Site
    template_name = "assets/site_detail.html"
    context_object_name = "site"
    permission_required = "context.site.read"
    approve_url_name = "assets:site-approve"

    def get_queryset(self):
        return super().get_queryset().select_related("parent_site").prefetch_related(
            "children",
            "asset_dependencies__support_asset",
            "supplier_dependencies__supplier",
        )

    def get_context_data(self, **kwargs):
        from django.urls import reverse

        ctx = super().get_context_data(**kwargs)
        site = self.object
        ancestors = site.get_ancestors()
        ctx["ancestors"] = ancestors
        # Site ancestry for the page_header breadcrumb (Sites > parent > ... >
        # current): each ancestor links to its detail page.
        ctx["site_breadcrumb"] = [
            {"label": a.name, "url": reverse("assets:site-detail", kwargs={"pk": a.pk})}
            for a in ancestors
        ]
        ctx["children"] = site.children.exclude(workflow_state="archived")
        # Related dependencies surfaced on the detail page and counted in the rail.
        ctx["asset_dependencies"] = site.asset_dependencies.all()
        ctx["supplier_dependencies"] = site.supplier_dependencies.all()
        return ctx


class SiteCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Site
    form_class = SiteCreateForm
    template_name = "assets/site_form.html"
    permission_required = "context.site.create"
    modal_template_name = "assets/site_form_modal.html"
    modal_title_create = _l("New site")
    modal_title_update = _l("Edit site")
    success_url = reverse_lazy("assets:site-list")


class SiteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, UpdateView):
    model = Site
    form_class = SiteUpdateForm
    template_name = "assets/site_form.html"
    permission_required = "context.site.update"
    modal_template_name = "assets/site_form_modal.html"
    modal_title_create = _l("New site")
    modal_title_update = _l("Edit site")
    success_url = reverse_lazy("assets:site-list")


class SiteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Site
    template_name = "assets/confirm_delete.html"
    permission_required = "context.site.delete"
    success_url = reverse_lazy("assets:site-list")


# ── Site–Asset Dependencies ──────────────────────────────

SITE_ASSET_DEPENDENCY_FILTER_GROUPS = [
    {"param": "type", "field": "dependency_type", "label": _l("Type"), "options": SiteAssetDependencyType.choices},
    {"param": "criticality", "field": "criticality", "label": _l("Criticality"), "options": Criticality.choices},
]
SITE_ASSET_DEPENDENCY_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Ref.")},
]
SITE_ASSET_DEPENDENCY_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "support", "label": _l("Dependency"), "always": True},
    {"key": "type", "label": _l("Type")},
    {"key": "criticality", "label": _l("Criticality")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class SiteAssetDependencyListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = SiteAssetDependency
    template_name = "assets/site_asset_dependency_list.html"
    context_object_name = "dependencies"
    filter_groups = SITE_ASSET_DEPENDENCY_FILTER_GROUPS
    text_filters = SITE_ASSET_DEPENDENCY_TEXT_FILTERS
    columns = SITE_ASSET_DEPENDENCY_COLUMNS
    permission_required = "assets.dependency.read"
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "support": "support_asset__name",
        "site": "site__name",
        "type": "dependency_type",
        "criticality": "criticality",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "support_asset__name", "site__name"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("support_asset", "site")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class SiteAssetDependencyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreatedByMixin, CreateView):
    model = SiteAssetDependency
    form_class = SiteAssetDependencyForm
    template_name = "assets/site_asset_dependency_form.html"
    permission_required = "assets.dependency.create"
    success_url = reverse_lazy("assets:site-asset-dependency-list")


class SiteAssetDependencyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = SiteAssetDependency
    form_class = SiteAssetDependencyForm
    permission_required = "assets.dependency.update"
    template_name = "assets/site_asset_dependency_form.html"
    success_url = reverse_lazy("assets:site-asset-dependency-list")


class SiteAssetDependencyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SiteAssetDependency
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.dependency.delete"
    success_url = reverse_lazy("assets:site-asset-dependency-list")


# ── Site–Supplier Dependencies ───────────────────────────

SITE_SUPPLIER_DEPENDENCY_FILTER_GROUPS = [
    {"param": "type", "field": "dependency_type", "label": _l("Type"), "options": SiteSupplierDependencyType.choices},
    {"param": "criticality", "field": "criticality", "label": _l("Criticality"), "options": Criticality.choices},
]
SITE_SUPPLIER_DEPENDENCY_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Ref.")},
]
SITE_SUPPLIER_DEPENDENCY_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "site", "label": _l("Dependency"), "always": True},
    {"key": "type", "label": _l("Type")},
    {"key": "criticality", "label": _l("Criticality")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]


class SiteSupplierDependencyListView(LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView):
    model = SiteSupplierDependency
    template_name = "assets/site_supplier_dependency_list.html"
    context_object_name = "dependencies"
    filter_groups = SITE_SUPPLIER_DEPENDENCY_FILTER_GROUPS
    text_filters = SITE_SUPPLIER_DEPENDENCY_TEXT_FILTERS
    columns = SITE_SUPPLIER_DEPENDENCY_COLUMNS
    permission_required = "assets.supplier_dependency.read"
    paginate_by = 50
    sortable_fields = {
        "reference": "reference",
        "site": "site__name",
        "supplier": "supplier__name",
        "type": "dependency_type",
        "criticality": "criticality",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "site__name", "supplier__name"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("site", "supplier")
        qs = self.filter_queryset_predefined(qs)
        return self.filter_queryset_advanced(qs)


class SiteSupplierDependencyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreatedByMixin, CreateView):
    model = SiteSupplierDependency
    form_class = SiteSupplierDependencyForm
    template_name = "assets/site_supplier_dependency_form.html"
    permission_required = "assets.supplier_dependency.create"
    success_url = reverse_lazy("assets:site-supplier-dependency-list")


class SiteSupplierDependencyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = SiteSupplierDependency
    form_class = SiteSupplierDependencyForm
    template_name = "assets/site_supplier_dependency_form.html"
    permission_required = "assets.supplier_dependency.update"
    success_url = reverse_lazy("assets:site-supplier-dependency-list")


class SiteSupplierDependencyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SiteSupplierDependency
    template_name = "assets/confirm_delete.html"
    permission_required = "assets.supplier_dependency.delete"
    success_url = reverse_lazy("assets:site-supplier-dependency-list")


# ── Dependency Graph ──────────────────────────────────────

class DependencyGraphView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "assets/dependency_graph.html"
    permission_required = "assets.dependency.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Asset dependencies (essential → support)
        asset_deps = AssetDependency.objects.select_related(
            "essential_asset", "support_asset"
        ).all()
        # Supplier dependencies (support → supplier)
        supplier_deps = SupplierDependency.objects.select_related(
            "support_asset", "supplier"
        ).all()
        # Site–asset dependencies (support → site)
        site_asset_deps = SiteAssetDependency.objects.select_related(
            "support_asset", "site"
        ).all()
        # Site–supplier dependencies (site → supplier)
        site_supplier_deps = SiteSupplierDependency.objects.select_related(
            "site", "supplier"
        ).all()

        nodes = {}
        edges = []

        for dep in asset_deps:
            ea = dep.essential_asset
            sa = dep.support_asset
            ea_id = str(ea.id)
            sa_id = str(sa.id)
            if ea_id not in nodes:
                nodes[ea_id] = {
                    "id": ea_id,
                    "label": f"{ea.reference} - {ea.name}",
                    "type": "essential",
                }
            if sa_id not in nodes:
                nodes[sa_id] = {
                    "id": sa_id,
                    "label": f"{sa.reference} - {sa.name}",
                    "type": "support",
                }
            edges.append({
                "source": ea_id,
                "target": sa_id,
                "label": dep.get_dependency_type_display(),
                "criticality": dep.criticality,
                "is_spof": dep.is_single_point_of_failure,
                "kind": "asset",
            })

        for dep in supplier_deps:
            sa = dep.support_asset
            sup = dep.supplier
            sa_id = str(sa.id)
            sup_id = str(sup.id)
            if sa_id not in nodes:
                nodes[sa_id] = {
                    "id": sa_id,
                    "label": f"{sa.reference} - {sa.name}",
                    "type": "support",
                }
            if sup_id not in nodes:
                nodes[sup_id] = {
                    "id": sup_id,
                    "label": f"{sup.reference} - {sup.name}",
                    "type": "supplier",
                    "logo": sup.logo_64 or sup.logo or "",
                }
            edges.append({
                "source": sa_id,
                "target": sup_id,
                "label": dep.get_dependency_type_display(),
                "criticality": dep.criticality,
                "is_spof": dep.is_single_point_of_failure,
                "kind": "supplier",
            })

        for dep in site_asset_deps:
            sa = dep.support_asset
            site = dep.site
            sa_id = str(sa.id)
            site_id = str(site.id)
            if sa_id not in nodes:
                nodes[sa_id] = {
                    "id": sa_id,
                    "label": f"{sa.reference} - {sa.name}",
                    "type": "support",
                }
            if site_id not in nodes:
                nodes[site_id] = {
                    "id": site_id,
                    "label": f"{site.reference} - {site.name}",
                    "type": "site",
                }
            edges.append({
                "source": sa_id,
                "target": site_id,
                "label": dep.get_dependency_type_display(),
                "criticality": dep.criticality,
                "is_spof": dep.is_single_point_of_failure,
                "kind": "site",
            })

        for dep in site_supplier_deps:
            site = dep.site
            sup = dep.supplier
            site_id = str(site.id)
            sup_id = str(sup.id)
            if site_id not in nodes:
                nodes[site_id] = {
                    "id": site_id,
                    "label": f"{site.reference} - {site.name}",
                    "type": "site",
                }
            if sup_id not in nodes:
                nodes[sup_id] = {
                    "id": sup_id,
                    "label": f"{sup.reference} - {sup.name}",
                    "type": "supplier",
                    "logo": sup.logo_64 or sup.logo or "",
                }
            edges.append({
                "source": site_id,
                "target": sup_id,
                "label": dep.get_dependency_type_display(),
                "criticality": dep.criticality,
                "is_spof": dep.is_single_point_of_failure,
                "kind": "site_supplier",
            })

        import json
        ctx["graph_nodes"] = json.dumps(list(nodes.values()))
        ctx["graph_edges"] = json.dumps(edges)
        ctx["asset_dep_count"] = asset_deps.count()
        ctx["supplier_dep_count"] = supplier_deps.count()
        ctx["site_asset_dep_count"] = site_asset_deps.count()
        ctx["site_supplier_dep_count"] = site_supplier_deps.count()
        return ctx

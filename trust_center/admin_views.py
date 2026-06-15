"""Internal curation UI for the Trust Center.

Lives under ``/trust-center/manage/`` (deliberately NOT under ``/trust/`` so the
host-isolation middleware can block it on a public domain). All views require
authentication + the relevant ``trust_center.*`` permission. Lifecycle
transitions (publish / unpublish) use the shared workflow stepper, which posts
to the generic ``workflow:transition`` endpoint.
"""

from django.conf import settings as dj_settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import WorkflowStepperMixin
from accounts.views import PermissionRequiredMixin
from core.workflow import WorkflowError
from trust_center.constants import DocumentRequestState
from trust_center.forms import (
    CertificationForm,
    DocumentForm,
    MeasureForm,
    SubprocessorForm,
    TrustCenterSettingsForm,
)
from trust_center.models import (
    DocumentRequest,
    TrustCenterCertification,
    TrustCenterDocument,
    TrustCenterMeasure,
    TrustCenterSettings,
    TrustCenterSubprocessor,
)
from trust_center.notifications import send_gated_link_email
from trust_center.transition_messages import transition_error_detail

ENTITY_CONFIG = {
    "certification": {
        "model": TrustCenterCertification,
        "form": CertificationForm,
        "perm": "certification",
        "label": _("Certification"),
        "label_plural": _("Certifications"),
        "icon": "bi-patch-check",
        "select_related": ["framework"],
        "detail_fields": lambda o: [
            (_("Framework"), str(o.framework)),
            (_("Public label"), o.public_label),
            (_("Public description"), o.public_description),
            (_("Show percentage"), o.show_percentage),
            (_("Display order"), o.display_order),
        ],
    },
    "subprocessor": {
        "model": TrustCenterSubprocessor,
        "form": SubprocessorForm,
        "perm": "subprocessor",
        "label": _("Subprocessor"),
        "label_plural": _("Subprocessors"),
        "icon": "bi-diagram-3",
        "select_related": ["supplier"],
        "detail_fields": lambda o: [
            (_("Supplier"), str(o.supplier)),
            (_("Public name"), o.public_name),
            (_("Purpose"), o.purpose),
            (_("Country"), o.public_country),
            (_("Website"), o.public_website),
            (_("Display order"), o.display_order),
        ],
    },
    "measure": {
        "model": TrustCenterMeasure,
        "form": MeasureForm,
        "perm": "measure",
        "label": _("Measure"),
        "label_plural": _("Measures"),
        "icon": "bi-shield-check",
        "select_related": [],
        "detail_fields": lambda o: [
            (_("Title"), o.title),
            (_("Description"), o.description),
            (_("Icon"), o.icon),
            (_("Category"), o.get_category_display()),
            (_("Display order"), o.display_order),
        ],
    },
    "document": {
        "model": TrustCenterDocument,
        "form": DocumentForm,
        "perm": "document",
        "label": _("Document"),
        "label_plural": _("Documents"),
        "icon": "bi-file-earmark-text",
        "select_related": ["report"],
        "detail_fields": lambda o: [
            (_("Title"), o.title),
            (_("Description"), o.description),
            (_("Access"), o.get_access_display()),
            (_("Requires NDA"), o.requires_nda),
            (
                _("Source"),
                str(o.report) if o.report_id else (o.file_name or "-"),
            ),
            (_("Display order"), o.display_order),
        ],
    },
}

ENTITY_ORDER = ["certification", "subprocessor", "measure", "document"]


class ManageHubView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "trust_center/manage/hub.html"
    permission_required = "trust_center.settings.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["settings_obj"] = TrustCenterSettings.get()
        sections = []
        for key in ENTITY_ORDER:
            cfg = ENTITY_CONFIG[key]
            qs = cfg["model"].objects.all()
            if cfg["select_related"]:
                qs = qs.select_related(*cfg["select_related"])
            sections.append({"entity": key, "cfg": cfg, "objects": qs})
        ctx["sections"] = sections
        ctx["pending_requests"] = DocumentRequest.objects.filter(
            workflow_state=DocumentRequestState.PENDING
        ).count()
        return ctx


class SettingsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "trust_center.settings.read"

    def get(self, request):
        form = TrustCenterSettingsForm(instance=TrustCenterSettings.get())
        return render(request, "trust_center/manage/settings_form.html", {"form": form})

    def post(self, request):
        if not (
            request.user.is_superuser
            or request.user.has_perm("trust_center.settings.update")
        ):
            messages.error(
                request, _("You do not have permission to update these settings.")
            )
            return redirect("trust_center_manage:settings")
        form = TrustCenterSettingsForm(
            request.POST, request.FILES, instance=TrustCenterSettings.get()
        )
        if form.is_valid():
            form.save()
            messages.success(request, _("Trust Center settings updated."))
            return redirect("trust_center_manage:hub")
        return render(request, "trust_center/manage/settings_form.html", {"form": form})


class _EntityBase(PermissionRequiredMixin):
    action = "read"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.entity = kwargs.get("entity")
        self.cfg = ENTITY_CONFIG.get(self.entity)
        if self.cfg:
            self.model = self.cfg["model"]
            self.permission_required = f"trust_center.{self.cfg['perm']}.{self.action}"

    def dispatch(self, request, *args, **kwargs):
        if not self.cfg:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return self.cfg["form"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["entity"] = self.entity
        ctx["cfg"] = self.cfg
        return ctx


class EntityCreateView(LoginRequiredMixin, _EntityBase, CreateView):
    action = "create"
    template_name = "trust_center/manage/entity_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Created."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("trust_center_manage:detail", args=[self.entity, self.object.pk])


class EntityUpdateView(LoginRequiredMixin, _EntityBase, UpdateView):
    action = "update"
    template_name = "trust_center/manage/entity_form.html"

    def form_valid(self, form):
        messages.success(self.request, _("Updated."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("trust_center_manage:detail", args=[self.entity, self.object.pk])


class EntityDetailView(LoginRequiredMixin, _EntityBase, WorkflowStepperMixin, DetailView):
    action = "read"
    template_name = "trust_center/manage/entity_detail.html"
    context_object_name = "obj"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["detail_rows"] = self.cfg["detail_fields"](self.object)
        return ctx


class EntityDeleteView(LoginRequiredMixin, _EntityBase, DeleteView):
    action = "delete"
    template_name = "trust_center/manage/entity_confirm_delete.html"
    context_object_name = "obj"

    def get_success_url(self):
        return reverse("trust_center_manage:hub")

    def form_valid(self, form):
        self.object = self.get_object()
        if not self.object.is_deletable:
            messages.error(
                self.request,
                _("This item cannot be deleted in its current state. Unpublish it first."),
            )
            return redirect("trust_center_manage:detail", entity=self.entity, pk=self.object.pk)
        messages.success(self.request, _("Deleted."))
        return super().form_valid(form)


# --- Document requests inbox ------------------------------------------------


class DocumentRequestListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = DocumentRequest
    template_name = "trust_center/manage/request_list.html"
    permission_required = "trust_center.document_request.read"
    context_object_name = "requests"
    paginate_by = 50

    def get_queryset(self):
        return DocumentRequest.objects.select_related("document").all()


class DocumentRequestDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, WorkflowStepperMixin, DetailView
):
    model = DocumentRequest
    template_name = "trust_center/manage/request_detail.html"
    permission_required = "trust_center.document_request.read"
    context_object_name = "obj"
    # Approve carries side effects (issue token + email), so transitions go to a
    # bespoke endpoint instead of the generic workflow:transition.
    workflow_transition_url_name = "trust_center_manage:request-transition"


class DocumentRequestTransitionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    # The view is reachable by any reader; the approve permission is enforced by
    # transition_to(enforce_permission=True) per the transition's action.
    permission_required = "trust_center.document_request.read"

    def post(self, request, pk):
        obj = get_object_or_404(DocumentRequest, pk=pk)
        target = request.POST.get("target_status")
        comment = request.POST.get("comment", "")
        try:
            obj.transition_to(
                target, request.user, comment=comment, enforce_permission=True
            )
        except WorkflowError as exc:
            messages.error(request, transition_error_detail(exc))
            return redirect("trust_center_manage:request-detail", pk=pk)

        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        if comment:
            obj.decision_note = comment
        obj.save(update_fields=["reviewed_by", "reviewed_at", "decision_note", "updated_at"])

        if target == DocumentRequestState.APPROVED:
            token = obj.issue_download_link(dj_settings.TRUST_CENTER_DOWNLOAD_TTL)
            url = reverse("trust_center:gated-download", kwargs={"token": token})
            if send_gated_link_email(obj, url):
                messages.success(request, _("Request approved and a download link was emailed."))
            else:
                messages.warning(
                    request,
                    _("Request approved, but the download link email could not be sent."),
                )
        else:
            messages.success(request, _("Request updated."))
        return redirect("trust_center_manage:request-detail", pk=pk)

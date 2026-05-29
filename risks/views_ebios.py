"""Web views for the EBIOS RM module (workshops W0..W5).

Mounted under `/risks/assessments/<assessment_pk>/ebios/...`. The views are
class-based, scope-filtered, permission-gated and HTMX-friendly: any view
that handles a form save returns a partial when the request carries the
`HX-Request` header.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DeleteView, DetailView, UpdateView

from accounts.mixins import ScopeFilterMixin
from accounts.views import PermissionRequiredMixin
from core.mixins import HtmxFormMixin
from risks.constants import (
    EBIOS_WORKSHOP_COUNT,
    EbiosWorkshopNumber,
    EbiosWorkshopStatus,
)
from risks.forms_ebios import (
    BaselineGapForm,
    FearedEventForm,
    SecurityBaselineForm,
    StudyFrameworkForm,
    WorkshopRejectForm,
)
from risks.models import (
    BaselineGap,
    EbiosWorkshopProgress,
    FearedEvent,
    RiskAssessment,
    SecurityBaseline,
    StudyFramework,
)


# ── Workshop transitions ──────────────────────────────────────


class _WorkshopTransitionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Base class for workshop status transitions.

    Subclasses set `target_status` and override `_check_preconditions(workshop)`
    to enforce the porte de validation.
    """

    permission_required = "risks.ebios_assessment.update"
    target_status: str = ""

    def _check_preconditions(self, workshop):
        """Return a list of error strings; empty list when the transition is OK."""
        return []

    def post(self, request, assessment_pk, workshop_pk):
        workshop = get_object_or_404(
            EbiosWorkshopProgress.objects.select_related("assessment"),
            pk=workshop_pk,
            assessment_id=assessment_pk,
        )
        errors = self._check_preconditions(workshop)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect(
                "risks:ebios-workshop-detail",
                assessment_pk=assessment_pk, workshop_pk=workshop_pk,
            )
        workshop.status = self.target_status
        if self.target_status == EbiosWorkshopStatus.IN_PROGRESS and not workshop.started_at:
            workshop.started_at = timezone.now()
        if self.target_status == EbiosWorkshopStatus.VALIDATED:
            workshop.validated_by = request.user
            workshop.validated_at = timezone.now()
        workshop.save()
        messages.success(request, _("Workshop status updated."))
        return redirect(
            "risks:ebios-workshop-detail",
            assessment_pk=assessment_pk, workshop_pk=workshop_pk,
        )


class WorkshopStartView(_WorkshopTransitionView):
    target_status = EbiosWorkshopStatus.IN_PROGRESS

    def _check_preconditions(self, workshop):
        if workshop.status not in (
            EbiosWorkshopStatus.NOT_STARTED,
            EbiosWorkshopStatus.REJECTED,
        ):
            return [_("Workshop is already in progress or beyond.")]
        # Workshops other than W0 require the previous workshop to be validated.
        if workshop.workshop_number > 0:
            prev = workshop.assessment.ebios_workshops.filter(
                workshop_number=workshop.workshop_number - 1,
                iteration_type=workshop.iteration_type,
                iteration_number=workshop.iteration_number,
            ).first()
            if prev and prev.status != EbiosWorkshopStatus.VALIDATED:
                return [
                    _("Workshop %(num)d must be validated before workshop %(next)d can start.")
                    % {"num": prev.workshop_number, "next": workshop.workshop_number}
                ]
        return []


class WorkshopSubmitView(_WorkshopTransitionView):
    """Move a workshop from in_progress to under_review."""

    target_status = EbiosWorkshopStatus.UNDER_REVIEW

    def _check_preconditions(self, workshop):
        if workshop.status != EbiosWorkshopStatus.IN_PROGRESS:
            return [_("Only in-progress workshops can be submitted for review.")]
        return []


class WorkshopValidateView(_WorkshopTransitionView):
    permission_required = "risks.ebios_assessment.validate"
    target_status = EbiosWorkshopStatus.VALIDATED

    def _check_preconditions(self, workshop):
        if workshop.status not in (
            EbiosWorkshopStatus.IN_PROGRESS,
            EbiosWorkshopStatus.UNDER_REVIEW,
        ):
            return [_("Only in-progress or under-review workshops can be validated.")]
        return []


class WorkshopRejectView(_WorkshopTransitionView):
    permission_required = "risks.ebios_assessment.validate"
    target_status = EbiosWorkshopStatus.REJECTED

    def _check_preconditions(self, workshop):
        if workshop.status not in (
            EbiosWorkshopStatus.IN_PROGRESS,
            EbiosWorkshopStatus.UNDER_REVIEW,
        ):
            return [_("Only in-progress or under-review workshops can be rejected.")]
        return []

    def post(self, request, assessment_pk, workshop_pk):
        workshop = get_object_or_404(
            EbiosWorkshopProgress.objects.select_related("assessment"),
            pk=workshop_pk,
            assessment_id=assessment_pk,
        )
        errors = self._check_preconditions(workshop)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect(
                "risks:ebios-workshop-detail",
                assessment_pk=assessment_pk, workshop_pk=workshop_pk,
            )
        form = WorkshopRejectForm(request.POST)
        if not form.is_valid():
            messages.error(request, _("A rejection reason is required."))
            return redirect(
                "risks:ebios-workshop-detail",
                assessment_pk=assessment_pk, workshop_pk=workshop_pk,
            )
        workshop.status = EbiosWorkshopStatus.REJECTED
        workshop.rejection_reason = form.cleaned_data["rejection_reason"]
        workshop.save()
        messages.success(request, _("Workshop rejected."))
        return redirect(
            "risks:ebios-workshop-detail",
            assessment_pk=assessment_pk, workshop_pk=workshop_pk,
        )


# ── Workshop detail (dispatcher) ──────────────────────────────


WORKSHOP_TEMPLATES = {
    EbiosWorkshopNumber.W0: "risks/ebios/workshop_w0.html",
    EbiosWorkshopNumber.W1: "risks/ebios/workshop_w1.html",
    EbiosWorkshopNumber.W2: "risks/ebios/workshop_w2.html",
    EbiosWorkshopNumber.W3: "risks/ebios/workshop_w3.html",
    EbiosWorkshopNumber.W4: "risks/ebios/workshop_w4.html",
    EbiosWorkshopNumber.W5: "risks/ebios/workshop_w5.html",
}


class WorkshopDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Dispatcher view picking the template per workshop_number.

    The detail page hosts the entity tables, forms and the workshop sidebar
    with status + CTA buttons (Start / Submit / Validate / Reject).
    """

    permission_required = "risks.ebios_assessment.read"
    model = EbiosWorkshopProgress
    context_object_name = "workshop"
    pk_url_kwarg = "workshop_pk"

    def get_queryset(self):
        return EbiosWorkshopProgress.objects.select_related(
            "assessment", "validated_by",
        ).filter(assessment_id=self.kwargs["assessment_pk"])

    def get_template_names(self):
        workshop = self.get_object()
        return [WORKSHOP_TEMPLATES.get(workshop.workshop_number, "risks/ebios/workshop_generic.html")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        workshop = ctx["workshop"]
        assessment = workshop.assessment
        ctx["assessment"] = assessment
        ctx["reject_form"] = WorkshopRejectForm()
        ctx["ebios_workshops"] = list(
            assessment.ebios_workshops.filter(
                iteration_type=workshop.iteration_type,
                iteration_number=workshop.iteration_number,
            ).order_by("workshop_number")
        )

        # Action eligibility flags consumed by the sidebar template
        ctx["can_start"] = workshop.status in (
            EbiosWorkshopStatus.NOT_STARTED, EbiosWorkshopStatus.REJECTED,
        )
        ctx["can_submit"] = workshop.status == EbiosWorkshopStatus.IN_PROGRESS
        ctx["can_validate"] = workshop.status in (
            EbiosWorkshopStatus.IN_PROGRESS, EbiosWorkshopStatus.UNDER_REVIEW,
        )
        ctx["can_reject"] = workshop.status in (
            EbiosWorkshopStatus.IN_PROGRESS, EbiosWorkshopStatus.UNDER_REVIEW,
        )

        # Per-workshop entity context
        if workshop.workshop_number == EbiosWorkshopNumber.W0:
            ctx["study_framework"] = assessment.ebios_study_framework
        elif workshop.workshop_number == EbiosWorkshopNumber.W1:
            baseline = assessment.ebios_security_baseline
            ctx["baseline"] = baseline
            ctx["feared_events"] = baseline.feared_events.select_related("essential_asset").all()
            ctx["baseline_gaps"] = baseline.gaps.select_related("linked_requirement").all()
        return ctx


# ── Study framework (W0) edit ────────────────────────────────


class StudyFrameworkUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_assessment.update"
    model = StudyFramework
    form_class = StudyFrameworkForm
    template_name = "risks/ebios/study_framework_form.html"

    def get_success_url(self):
        workshop = self.object.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W0,
        ).first()
        if workshop:
            return reverse(
                "risks:ebios-workshop-detail",
                kwargs={"assessment_pk": self.object.assessment_id, "workshop_pk": workshop.pk},
            )
        return reverse("risks:assessment-detail", kwargs={"pk": self.object.assessment_id})


# ── Security baseline (W1) edit + inline feared events / gaps ─


class SecurityBaselineUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_baseline.update"
    model = SecurityBaseline
    form_class = SecurityBaselineForm
    template_name = "risks/ebios/security_baseline_form.html"

    def get_success_url(self):
        workshop = self.object.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        if workshop:
            return reverse(
                "risks:ebios-workshop-detail",
                kwargs={"assessment_pk": self.object.assessment_id, "workshop_pk": workshop.pk},
            )
        return reverse("risks:assessment-detail", kwargs={"pk": self.object.assessment_id})


class FearedEventCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Inline create of a FearedEvent under a given SecurityBaseline."""

    permission_required = "risks.ebios_baseline.create"

    def get(self, request, baseline_pk):
        from django.shortcuts import render
        baseline = get_object_or_404(SecurityBaseline, pk=baseline_pk)
        form = FearedEventForm()
        return render(
            request,
            "risks/ebios/feared_event_form.html",
            {"form": form, "baseline": baseline, "feared_event": None},
        )

    def post(self, request, baseline_pk):
        baseline = get_object_or_404(SecurityBaseline, pk=baseline_pk)
        form = FearedEventForm(request.POST)
        if not form.is_valid():
            from django.shortcuts import render
            return render(
                request,
                "risks/ebios/feared_event_form.html",
                {"form": form, "baseline": baseline, "feared_event": None},
                status=400,
            )
        feared = form.save(commit=False)
        feared.baseline = baseline
        feared.created_by = request.user
        feared.save()
        workshop = baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return HttpResponseRedirect(
            reverse(
                "risks:ebios-workshop-detail",
                kwargs={"assessment_pk": baseline.assessment_id, "workshop_pk": workshop.pk},
            )
        )


class FearedEventUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_baseline.update"
    model = FearedEvent
    form_class = FearedEventForm
    template_name = "risks/ebios/feared_event_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["baseline"] = self.object.baseline
        ctx["feared_event"] = self.object
        return ctx

    def get_success_url(self):
        workshop = self.object.baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return reverse(
            "risks:ebios-workshop-detail",
            kwargs={
                "assessment_pk": self.object.baseline.assessment_id,
                "workshop_pk": workshop.pk,
            },
        )


class FearedEventDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_baseline.delete"
    model = FearedEvent
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        workshop = self.object.baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return reverse(
            "risks:ebios-workshop-detail",
            kwargs={
                "assessment_pk": self.object.baseline.assessment_id,
                "workshop_pk": workshop.pk,
            },
        )


class BaselineGapCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_baseline.create"

    def get(self, request, baseline_pk):
        from django.shortcuts import render
        baseline = get_object_or_404(SecurityBaseline, pk=baseline_pk)
        form = BaselineGapForm()
        return render(
            request,
            "risks/ebios/baseline_gap_form.html",
            {"form": form, "baseline": baseline, "gap": None},
        )

    def post(self, request, baseline_pk):
        baseline = get_object_or_404(SecurityBaseline, pk=baseline_pk)
        form = BaselineGapForm(request.POST)
        if not form.is_valid():
            from django.shortcuts import render
            return render(
                request,
                "risks/ebios/baseline_gap_form.html",
                {"form": form, "baseline": baseline, "gap": None},
                status=400,
            )
        gap = form.save(commit=False)
        gap.baseline = baseline
        gap.created_by = request.user
        gap.save()
        workshop = baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return HttpResponseRedirect(
            reverse(
                "risks:ebios-workshop-detail",
                kwargs={"assessment_pk": baseline.assessment_id, "workshop_pk": workshop.pk},
            )
        )


class BaselineGapUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_baseline.update"
    model = BaselineGap
    form_class = BaselineGapForm
    template_name = "risks/ebios/baseline_gap_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["baseline"] = self.object.baseline
        ctx["gap"] = self.object
        return ctx

    def get_success_url(self):
        workshop = self.object.baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return reverse(
            "risks:ebios-workshop-detail",
            kwargs={
                "assessment_pk": self.object.baseline.assessment_id,
                "workshop_pk": workshop.pk,
            },
        )


class BaselineGapDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_baseline.delete"
    model = BaselineGap
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        workshop = self.object.baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return reverse(
            "risks:ebios-workshop-detail",
            kwargs={
                "assessment_pk": self.object.baseline.assessment_id,
                "workshop_pk": workshop.pk,
            },
        )

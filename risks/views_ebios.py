# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web views for the EBIOS RM module (workshops W0..W5).

Mounted under `/risks/assessments/<assessment_pk>/ebios/...`. The views are
class-based, scope-filtered, permission-gated and HTMX-friendly: any view
that handles a form save returns a partial when the request carries the
`HX-Request` header.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from accounts.views import PermissionRequiredMixin
from controls.integrations import linked_controls_for_measures
from core.completeness import completeness_of, refuse_if_incomplete
from core.lifecycle import DomainRefusalError, LifecycleProtectedError
from core.mixins import ConfirmDeleteShellMixin, HtmxFormMixin
from core.query_params import parse_uuid
from core.transition_messages import transition_error_detail
from risks.constants import (
    EbiosIterationType,
    EbiosWorkshopNumber,
    EbiosWorkshopStatus,
    Methodology,
)


# ── Stepper context builder ──────────────────────────────────


_WORKSHOP_SHORT_LABELS = {
    0: _("Framework"),
    1: _("Baseline"),
    2: _("Sources"),
    3: _("Strategic"),
    4: _("Operational"),
    5: _("Treatment"),
}


def build_ebios_stepper_context(assessment, current_workshop=None):
    """Return the dict consumed by `risks/ebios/_workshop_stepper.html`.

    Mirrors the structure of `compliance.AssessmentDetailView`:
    - `ebios_workshops` (list of dicts with state in done/current/next/future)
    - `rejected_workshops` (list of dicts for the bottom branch)
    - `ebios_next_workshop` (the workshop ready to be started, or None)
    - `branch_line_color`, `branch_line_opacity` (SVG branch styling hints)
    """
    qs = assessment.ebios_workshops.filter(
        iteration_type=EbiosIterationType.STRATEGIC,
    ).order_by("iteration_number", "workshop_number")
    workshops = list(qs)

    # Identify the "current" workshop = the lowest-numbered non-validated.
    current_idx = None
    for i, w in enumerate(workshops):
        if w.status != EbiosWorkshopStatus.VALIDATED:
            current_idx = i
            break

    next_action = None
    steps = []
    rejected = []
    for i, w in enumerate(workshops):
        short_label = _WORKSHOP_SHORT_LABELS.get(w.workshop_number, "")
        if w.status == EbiosWorkshopStatus.REJECTED:
            # Rejected workshops live on the bottom branch, mirroring the
            # compliance "cancelled" pill. They keep their workshop_number
            # as the label so the user can navigate back to them.
            rejected.append({
                "pk": str(w.pk),
                "workshop_number": w.workshop_number,
                "label": w.get_workshop_number_display(),
                "short_label": short_label,
                "status": w.status,
                "state": "rejected",
                "is_current": current_workshop is not None and current_workshop.pk == w.pk,
            })
            continue

        if w.status == EbiosWorkshopStatus.VALIDATED:
            state = "done"
        elif w.status == EbiosWorkshopStatus.IN_PROGRESS:
            state = "current"
        elif w.status == EbiosWorkshopStatus.UNDER_REVIEW:
            state = "review"
        elif current_idx is not None and i == current_idx:
            # not_started AND it's the first non-validated workshop -> next CTA
            state = "next"
            next_action = w
        else:
            state = "future"

        steps.append({
            "pk": str(w.pk),
            "workshop_number": w.workshop_number,
            "label": w.get_workshop_number_display(),
            "short_label": short_label,
            "status": w.status,
            "state": state,
            "is_current": current_workshop is not None and current_workshop.pk == w.pk,
        })

    return {
        "ebios_workshops": workshops,  # backwards-compat for templates expecting the queryset
        "ebios_stepper_steps": steps,
        "ebios_rejected_steps": rejected,
        "ebios_next_action": next_action,
        "ebios_branch_line_color": "var(--danger)" if rejected else "var(--border-light)",
        "ebios_branch_line_opacity": "1" if rejected else "0.3",
    }
from risks.forms_ebios import (
    AttackPathStepCreateForm,
    AttackPathStepForm,
    AttackTechniqueCreateForm,
    AttackTechniqueForm,
    BaselineGapCreateForm,
    BaselineGapForm,
    EbiosSummaryForm,
    EcosystemStakeholderCreateForm,
    EcosystemStakeholderForm,
    FearedEventCreateForm,
    FearedEventForm,
    OperationalScenarioCreateForm,
    OperationalScenarioForm,
    PACSMeasureCreateForm,
    PACSMeasureForm,
    RiskSourceCreateForm,
    RiskSourceForm,
    RiskSourceObjectivePairCreateForm,
    RiskSourceObjectivePairForm,
    SecurityBaselineForm,
    StrategicScenarioCreateForm,
    StrategicScenarioForm,
    StudyFrameworkForm,
    TargetedObjectiveCreateForm,
    TargetedObjectiveForm,
    WorkshopRejectForm,
)
from risks.models import (
    AttackPathStep,
    AttackTechnique,
    BaselineGap,
    EbiosSummary,
    EbiosWorkshopProgress,
    EcosystemStakeholder,
    FearedEvent,
    OperationalScenario,
    PACSMeasure,
    Risk,
    RiskAssessment,
    RiskSource,
    RiskSourceObjectivePair,
    SecurityBaseline,
    StrategicScenario,
    StudyFramework,
    TargetedObjective,
)
from core.scoping import get_scoped_object_or_404, scoped_queryset


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
        workshop = get_scoped_object_or_404(request.user, 
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
        # A workshop is validated on its deliverables : what its page lists
        # under "To complete" (``EbiosWorkshopProgress.COMPLETENESS``). The
        # lifecycle service asks the same of the other surfaces.
        try:
            refuse_if_incomplete(workshop, EbiosWorkshopStatus.VALIDATED)
        except DomainRefusalError as refusal:
            return [transition_error_detail(refusal)]
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
        workshop = get_scoped_object_or_404(request.user, 
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
        # Each of the six workshops has its page : a number that is none of
        # them is no workshop.
        template = WORKSHOP_TEMPLATES.get(self.object.workshop_number)
        if template is None:
            raise Http404
        return [template]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        workshop = ctx["workshop"]
        assessment = workshop.assessment
        # Defensive: assessments created before the bootstrap signal was
        # extended (e.g. EbiosSummary added in the W5 lot) might be missing
        # some of the singleton artifacts. Ensure them on every detail view
        # access so the page never 500s on a missing related object.
        from risks.signals import ensure_ebios_artifacts
        ensure_ebios_artifacts(assessment)
        ctx["assessment"] = assessment
        ctx["completeness"] = completeness_of(workshop)
        ctx["reject_form"] = WorkshopRejectForm()
        ctx.update(build_ebios_stepper_context(assessment, current_workshop=workshop))

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
            ctx.update(self._study_framework_context(assessment))
        elif workshop.workshop_number == EbiosWorkshopNumber.W1:
            ctx.update(self._security_baseline_context(assessment))
        elif workshop.workshop_number == EbiosWorkshopNumber.W2:
            ctx.update(self._risk_sources_context(assessment))
        elif workshop.workshop_number == EbiosWorkshopNumber.W3:
            ctx.update(self._ecosystem_context(assessment))
        elif workshop.workshop_number == EbiosWorkshopNumber.W4:
            ctx.update(self._operational_scenarios_context(assessment))
        elif workshop.workshop_number == EbiosWorkshopNumber.W5:
            ctx.update(self._summary_context(assessment))
        return ctx


    def _study_framework_context(self, assessment):
        """What the page of workshop 0 shows : the study framework, card by card."""
        user = self.request.user
        framework = assessment.ebios_study_framework
        return {
            "study_framework": framework,
            "study_framework_edit_url": (
                reverse("risks:ebios-study-framework-update", kwargs={"pk": framework.pk})
                if user.has_perm("risks.ebios_assessment.update") else ""
            ),
            "participants": list(framework.participants.order_by("first_name", "last_name", "email")),
            "external_participants": framework.external_participant_list,
            "applicable_frameworks": list(scoped_queryset(user, framework.applicable_frameworks.all())),
        }

    def _security_baseline_context(self, assessment):
        """What the page of workshop 1 shows : the baseline, its events and its gaps.

        A record the baseline links to is named when the reader may reach it :
        an activity, an asset or a framework filed under another scope is left
        out, and a feared event about such an asset shows a dash in its place.
        """
        user = self.request.user
        baseline = assessment.ebios_security_baseline
        may = user.has_perm
        essential_assets = list(scoped_queryset(user, baseline.essential_assets.all()))
        gravity_names = _level_names(getattr(assessment, "risk_criteria", None), "impact")
        feared_events = list(baseline.feared_events.all())
        covered = {event.essential_asset_id for event in feared_events}
        asset_model = FearedEvent._meta.get_field("essential_asset").related_model
        within_reach = {asset.pk: asset for asset in scoped_queryset(user, asset_model.objects.filter(pk__in=covered))}
        for event in feared_events:
            # The asset is named through what the reader may reach, the level by its name.
            event.asset_within_reach = within_reach.get(event.essential_asset_id)
            event.gravity_name = gravity_names.get(event.gravity_level, "")
        return {
            "baseline": baseline,
            "baseline_edit_url": (
                reverse("risks:ebios-baseline-update", kwargs={"pk": baseline.pk})
                if may("risks.ebios_baseline.update") else ""
            ),
            "can_add_row": may("risks.ebios_baseline.create"),
            "can_edit_row": may("risks.ebios_baseline.update"),
            "can_delete_row": may("risks.ebios_baseline.delete"),
            "business_values": list(scoped_queryset(user, baseline.business_values.all())),
            "essential_assets": essential_assets,
            "support_assets": list(scoped_queryset(user, baseline.support_assets.all())),
            "baseline_references": list(scoped_queryset(user, baseline.baseline_references.all())),
            "feared_events": feared_events,
            "assets_without_event": [asset for asset in essential_assets if asset.pk not in covered],
            "baseline_gaps": list(baseline.gaps.select_related("linked_requirement")),
        }


    def _risk_sources_context(self, assessment):
        """What the page of workshop 2 shows : the risk sources, their objectives and the pairs.

        Each objective is listed under its risk source with the pair that
        judges it, so that an objective nobody has judged yet is seen where it
        stands.
        """
        may = self.request.user.has_perm
        pairs = list(assessment.ebios_sr_ov_pairs.select_related("risk_source", "targeted_objective"))
        pair_of = {pair.targeted_objective_id: pair for pair in pairs}
        risk_sources = list(
            assessment.ebios_risk_sources.prefetch_related("targeted_objectives").order_by("created_at", "reference")
        )
        unpaired = 0
        for source in risk_sources:
            source.objectives = list(source.targeted_objectives.all())
            for objective in source.objectives:
                objective.pair = pair_of.get(objective.pk)
                unpaired += objective.pair is None
        return {
            "risk_sources": risk_sources,
            "sr_ov_pairs": pairs,
            "objectives_without_pair": unpaired,
            "has_objectives": any(source.objectives for source in risk_sources),
            "can_add_row": may("risks.ebios_risk_source.create"),
            "can_edit_row": may("risks.ebios_risk_source.update"),
            "can_delete_row": may("risks.ebios_risk_source.delete"),
        }


    def _ecosystem_context(self, assessment):
        """What the page of workshop 3 shows : the ecosystem, the strategic scenarios and their steps.

        A level reads by its name on the scales of the criteria of the study,
        and a scenario carries the steps of its attack path.
        """
        may = self.request.user.has_perm
        criteria = getattr(assessment, "risk_criteria", None)
        gravity_names = _level_names(criteria, "impact")
        likelihood_names = _level_names(criteria, "likelihood")
        risk_names = dict(criteria.risk_levels.values_list("level", "name")) if criteria is not None else {}
        scenarios = list(
            assessment.ebios_strategic_scenarios.select_related(
                "sr_ov_pair__risk_source", "sr_ov_pair__targeted_objective",
            ).prefetch_related("attack_path_steps__stakeholder").order_by("created_at", "reference")
        )
        for scenario in scenarios:
            scenario.steps = list(scenario.attack_path_steps.all())
            scenario.gravity_name = gravity_names.get(scenario.gravity_level, "")
            scenario.likelihood_name = likelihood_names.get(scenario.likelihood_level, "")
            scenario.risk_level_name = risk_names.get(scenario.risk_level, "")
        return {
            "ecosystem_stakeholders": list(assessment.ebios_ecosystem_stakeholders.all()),
            "strategic_scenarios": scenarios,
            "has_retained_pair": assessment.ebios_sr_ov_pairs.filter(is_retained=True).exists(),
            "can_add_stakeholder": may("risks.ebios_ecosystem.create"),
            "can_edit_stakeholder": may("risks.ebios_ecosystem.update"),
            "can_delete_stakeholder": may("risks.ebios_ecosystem.delete"),
            "can_add_row": may("risks.ebios_strategic.create"),
            "can_edit_row": may("risks.ebios_strategic.update"),
            "can_delete_row": may("risks.ebios_strategic.delete"),
        }


    def _operational_scenarios_context(self, assessment):
        """What the page of workshop 4 shows : the operational scenarios and their techniques."""
        may = self.request.user.has_perm
        criteria = getattr(assessment, "risk_criteria", None)
        gravity_names = _level_names(criteria, "impact")
        risk_names = dict(criteria.risk_levels.values_list("level", "name")) if criteria is not None else {}
        scenarios = list(
            assessment.ebios_operational_scenarios.select_related("strategic_scenario", "consolidated_risk")
            .prefetch_related("attack_techniques__mitre_technique", "attack_techniques__targeted_support_asset")
            .order_by("created_at", "reference")
        )
        for scenario in scenarios:
            scenario.techniques = list(scenario.attack_techniques.all())
            scenario.gravity_name = gravity_names.get(scenario.gravity_level, "")
            scenario.risk_level_name = risk_names.get(scenario.risk_level, "")
        return {
            "operational_scenarios": scenarios,
            "has_retained_scenario": assessment.ebios_strategic_scenarios.filter(is_retained=True).exists(),
            "can_add_row": may("risks.ebios_operational.create"),
            "can_edit_row": may("risks.ebios_operational.update"),
            "can_delete_row": may("risks.ebios_operational.delete"),
            "can_consolidate": may("risks.risk.create"),
        }


    def _summary_context(self, assessment):
        """What the page of workshop 5 shows : the summary, its snapshots and the measures of the plan."""
        user = self.request.user
        may = user.has_perm
        summary = assessment.ebios_summary
        criteria = getattr(assessment, "risk_criteria", None)
        risk_names = dict(criteria.risk_levels.values_list("level", "name")) if criteria is not None else {}

        def by_level(snapshot, key):
            """The counts of a snapshot, each level with its name, the lowest first."""
            counts = (snapshot or {}).get(key) or {}
            rows = []
            for level, count in sorted(counts.items(), key=lambda pair: str(pair[0])):
                try:
                    name = risk_names.get(int(level), "")
                except (TypeError, ValueError):
                    name = ""
                rows.append({"level": level, "name": name, "count": count})
            return rows

        measures = list(summary.pacs_measures.select_related("owner"))
        return {
            "summary": summary,
            "summary_edit_url": (
                reverse("risks:ebios-summary-update", kwargs={"pk": summary.pk})
                if may("risks.ebios_summary.update") else ""
            ),
            "before_by_level": by_level(summary.risk_mapping_before, "by_current_risk_level"),
            "after_by_level": by_level(summary.risk_mapping_after, "by_residual_risk_level"),
            "pacs_measures": measures,
            "linked_controls": linked_controls_for_measures(measures, user),
            "can_add_row": may("risks.ebios_summary.create"),
            "can_edit_row": may("risks.ebios_summary.update"),
            "can_delete_row": may("risks.ebios_summary.delete"),
        }


# ── The rows of a workshop page ──────────────────────────────


def _workshop_url(assessment, workshop_number):
    """The page of a workshop of ``assessment`` : the current strategic iteration.

    Falls back on the page of the assessment when the workshop does not exist
    (a study whose progress rows were removed).
    """
    workshop = assessment.ebios_workshops.filter(
        workshop_number=workshop_number,
        iteration_type=EbiosIterationType.STRATEGIC,
    ).order_by("-iteration_number").first()
    if workshop is None:
        return reverse("risks:assessment-detail", kwargs={"pk": assessment.pk})
    return reverse(
        "risks:ebios-workshop-detail",
        kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
    )


def _redirect_to_workshop(assessment, workshop_number):
    """Return a HttpResponseRedirect to the assessment's workshop detail page."""
    return HttpResponseRedirect(_workshop_url(assessment, workshop_number))


def _level_names(criteria, scale_type):
    """``level -> name`` on a scale of the criteria of a study (empty when it has none)."""
    if criteria is None:
        return {}
    return dict(criteria.scale_levels.filter(scale_type=scale_type).values_list("level", "name"))


class WorkshopRowFormMixin:
    """The form of a row of a workshop page : it comes from that page and goes back to it.

    For a ``CreateView`` or an ``UpdateView`` with ``HtmxFormMixin`` : the form
    opens in the side panel of the workshop page, or on a page of its own on a
    direct visit, whose Cancel leads back to the workshop and whose breadcrumb
    names the study. The form is given the person filling it, so that it
    offers what they may select.

    Class attributes:
        workshop_number: the workshop whose page lists the row.
    """

    workshop_number = None
    template_name = "risks/ebios/row_form.html"
    modal_template_name = "risks/ebios/row_form_modal.html"

    def get_assessment(self):
        """The study the row belongs to."""
        raise NotImplementedError

    def get_workshop_url(self):
        return _workshop_url(self.get_assessment(), self.workshop_number)

    def get_success_url(self):
        return self.get_workshop_url()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not ctx.get("is_modal"):
            assessment = self.get_assessment()
            ctx["cancel_url"] = self.get_workshop_url()
            ctx["form_nav"] = "risks:assessment-list"
            ctx["form_parent_label"] = assessment.name
            ctx["form_parent_url"] = reverse("risks:assessment-detail", kwargs={"pk": assessment.pk})
            ctx["form_accent"] = "risks"
        return ctx


class WorkshopRowDeleteMixin(ConfirmDeleteShellMixin):
    """Remove a row of a workshop page, from the side panel, and go back to that page.

    A refusal (a step of its lifecycle that protects the row, a record that
    still refers to it) is a message on the page, not a server error.
    """

    workshop_number = None
    template_name = "risks/ebios/confirm_delete.html"

    def get_assessment(self):
        raise NotImplementedError

    def get_success_url(self):
        return _workshop_url(self.get_assessment(), self.workshop_number)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.get_success_url()
        return ctx

    def form_valid(self, form):
        self.object = self.get_object()
        url = self.get_success_url()
        try:
            self.object.delete()
        except LifecycleProtectedError:
            messages.error(
                self.request,
                _("%(reference)s cannot be deleted at the step it has reached : %(step)s.")
                % {"reference": self.object.reference, "step": self.object.lifecycle_label},
            )
        except ProtectedError:
            messages.error(self.request, _("This element is still referenced and cannot be deleted."))
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=204, headers={"HX-Redirect": url})
        return redirect(url)


# ── Workshop 0 : the study framework ──


class StudyFrameworkUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, WorkshopRowFormMixin, HtmxFormMixin, UpdateView,
):
    """The study framework of a study, edited card by card from the page of workshop 0."""

    permission_required = "risks.ebios_assessment.update"
    workshop_number = EbiosWorkshopNumber.W0
    model = StudyFramework
    form_class = StudyFrameworkForm
    modal_title_update = _l("Edit study framework")

    def get_assessment(self):
        return self.object.assessment


# ── Workshop 1 : the security baseline, its feared events and its gaps ──


class SecurityBaselineUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, WorkshopRowFormMixin, HtmxFormMixin, UpdateView,
):
    """The security baseline of a study, edited card by card from the page of workshop 1."""

    permission_required = "risks.ebios_baseline.update"
    workshop_number = EbiosWorkshopNumber.W1
    model = SecurityBaseline
    form_class = SecurityBaselineForm
    modal_title_update = _l("Edit security baseline")

    def get_assessment(self):
        return self.object.assessment


class _RowOfTheBaseline(WorkshopRowFormMixin):
    """A feared event or a gap : a row of the security baseline, on the page of workshop 1."""

    workshop_number = EbiosWorkshopNumber.W1

    def get_baseline(self):
        return self.object.baseline

    def get_assessment(self):
        return self.get_baseline().assessment

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["baseline"] = self.get_baseline()
        return kwargs


class _NewRowOfTheBaseline(_RowOfTheBaseline):
    """The baseline a row is added to comes from the address, among those the user may reach."""

    @cached_property
    def baseline(self):
        return get_scoped_object_or_404(
            self.request.user, SecurityBaseline.objects.select_related("assessment"), pk=self.kwargs["baseline_pk"],
        )

    def get_baseline(self):
        return self.baseline

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class FearedEventCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _NewRowOfTheBaseline, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_baseline.create"
    model = FearedEvent
    form_class = FearedEventCreateForm
    modal_title_create = _l("New feared event")


class FearedEventUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _RowOfTheBaseline, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_baseline.update"
    model = FearedEvent
    form_class = FearedEventForm
    modal_title_update = _l("Edit feared event")


class FearedEventDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_baseline.delete"
    workshop_number = EbiosWorkshopNumber.W1
    model = FearedEvent

    def get_assessment(self):
        return self.object.baseline.assessment


class BaselineGapCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _NewRowOfTheBaseline, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_baseline.create"
    model = BaselineGap
    form_class = BaselineGapCreateForm
    modal_title_create = _l("New baseline gap")


class BaselineGapUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _RowOfTheBaseline, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_baseline.update"
    model = BaselineGap
    form_class = BaselineGapForm
    modal_title_update = _l("Edit baseline gap")


class BaselineGapDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_baseline.delete"
    workshop_number = EbiosWorkshopNumber.W1
    model = BaselineGap

    def get_assessment(self):
        return self.object.baseline.assessment


# ── Rows that hang under the study itself ────────────────────


class _RowOfTheStudy(WorkshopRowFormMixin):
    """A row filed under the study : a risk source, a pair. Its form is told which study."""

    def get_assessment(self):
        return self.object.assessment

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["assessment"] = self.get_assessment()
        return kwargs


class _NewRowOfTheStudy(_RowOfTheStudy):
    """The study a row is added to comes from the address : an EBIOS RM one, that the user may reach."""

    @cached_property
    def assessment(self):
        return get_scoped_object_or_404(
            self.request.user, RiskAssessment, pk=self.kwargs["assessment_pk"], methodology=Methodology.EBIOS_RM,
        )

    def get_assessment(self):
        return self.assessment

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


# ── Workshop 2 : risk sources, targeted objectives and their pairs ──


class RiskSourceCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _NewRowOfTheStudy, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_risk_source.create"
    workshop_number = EbiosWorkshopNumber.W2
    model = RiskSource
    form_class = RiskSourceCreateForm
    modal_title_create = _l("New risk source")


class RiskSourceUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _RowOfTheStudy, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_risk_source.update"
    workshop_number = EbiosWorkshopNumber.W2
    model = RiskSource
    form_class = RiskSourceForm
    modal_title_update = _l("Edit risk source")


class RiskSourceDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_risk_source.delete"
    workshop_number = EbiosWorkshopNumber.W2
    model = RiskSource

    def get_assessment(self):
        return self.object.assessment


class _ObjectiveOfASource(WorkshopRowFormMixin):
    """A targeted objective : a row of its risk source, on the page of workshop 2."""

    workshop_number = EbiosWorkshopNumber.W2

    def get_risk_source(self):
        return self.object.risk_source

    def get_assessment(self):
        return self.get_risk_source().assessment

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["risk_source"] = self.get_risk_source()
        return kwargs


class TargetedObjectiveCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _ObjectiveOfASource, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_risk_source.create"
    model = TargetedObjective
    form_class = TargetedObjectiveCreateForm
    modal_title_create = _l("New targeted objective")

    @cached_property
    def risk_source(self):
        return get_scoped_object_or_404(
            self.request.user, RiskSource.objects.select_related("assessment"), pk=self.kwargs["risk_source_pk"],
        )

    def get_risk_source(self):
        return self.risk_source

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class TargetedObjectiveUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _ObjectiveOfASource, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_risk_source.update"
    model = TargetedObjective
    form_class = TargetedObjectiveForm
    modal_title_update = _l("Edit targeted objective")


class TargetedObjectiveDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_risk_source.delete"
    workshop_number = EbiosWorkshopNumber.W2
    model = TargetedObjective

    def get_assessment(self):
        return self.object.risk_source.assessment


class SrOvPairCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _NewRowOfTheStudy, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_risk_source.create"
    workshop_number = EbiosWorkshopNumber.W2
    model = RiskSourceObjectivePair
    form_class = RiskSourceObjectivePairCreateForm
    modal_title_create = _l("New pair (SR/OV)")

    def get_initial(self):
        """Opened from the line of an objective, the form opens on it (``?objective=<id>``)."""
        initial = super().get_initial()
        objective_id = parse_uuid(self.request.GET.get("objective"))
        if objective_id and TargetedObjective.objects.filter(
            pk=objective_id, risk_source__assessment=self.assessment,
        ).exists():
            initial["targeted_objective"] = objective_id
        return initial


class SrOvPairUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _RowOfTheStudy, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_risk_source.update"
    workshop_number = EbiosWorkshopNumber.W2
    model = RiskSourceObjectivePair
    form_class = RiskSourceObjectivePairForm
    modal_title_update = _l("Edit pair (SR/OV)")


class SrOvPairDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_risk_source.delete"
    workshop_number = EbiosWorkshopNumber.W2
    model = RiskSourceObjectivePair

    def get_assessment(self):
        return self.object.assessment


# ── Workshop 3 : the ecosystem, the strategic scenarios and their attack paths ──


class EcosystemStakeholderCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _NewRowOfTheStudy, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_ecosystem.create"
    workshop_number = EbiosWorkshopNumber.W3
    model = EcosystemStakeholder
    form_class = EcosystemStakeholderCreateForm
    modal_title_create = _l("New ecosystem stakeholder")


class EcosystemStakeholderUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _RowOfTheStudy, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_ecosystem.update"
    workshop_number = EbiosWorkshopNumber.W3
    model = EcosystemStakeholder
    form_class = EcosystemStakeholderForm
    modal_title_update = _l("Edit ecosystem stakeholder")


class EcosystemStakeholderDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_ecosystem.delete"
    workshop_number = EbiosWorkshopNumber.W3
    model = EcosystemStakeholder

    def get_assessment(self):
        return self.object.assessment


class StrategicScenarioCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _NewRowOfTheStudy, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_strategic.create"
    workshop_number = EbiosWorkshopNumber.W3
    model = StrategicScenario
    form_class = StrategicScenarioCreateForm
    modal_title_create = _l("New strategic scenario")


class StrategicScenarioUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _RowOfTheStudy, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_strategic.update"
    workshop_number = EbiosWorkshopNumber.W3
    model = StrategicScenario
    form_class = StrategicScenarioForm
    modal_title_update = _l("Edit strategic scenario")


class StrategicScenarioDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_strategic.delete"
    workshop_number = EbiosWorkshopNumber.W3
    model = StrategicScenario

    def get_assessment(self):
        return self.object.assessment


class _StepOfAScenario(WorkshopRowFormMixin):
    """A step of an attack path : a row of its strategic scenario, on the page of workshop 3."""

    workshop_number = EbiosWorkshopNumber.W3

    def get_scenario(self):
        return self.object.scenario

    def get_assessment(self):
        return self.get_scenario().assessment

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["scenario"] = self.get_scenario()
        return kwargs


class AttackPathStepCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _StepOfAScenario, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_strategic.create"
    model = AttackPathStep
    form_class = AttackPathStepCreateForm
    modal_title_create = _l("New attack path step")

    @cached_property
    def scenario(self):
        return get_scoped_object_or_404(
            self.request.user, StrategicScenario.objects.select_related("assessment"), pk=self.kwargs["scenario_pk"],
        )

    def get_scenario(self):
        return self.scenario

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class AttackPathStepUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _StepOfAScenario, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_strategic.update"
    model = AttackPathStep
    form_class = AttackPathStepForm
    modal_title_update = _l("Edit attack path step")


class AttackPathStepDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_strategic.delete"
    workshop_number = EbiosWorkshopNumber.W3
    model = AttackPathStep

    def get_assessment(self):
        return self.object.scenario.assessment


# ── Workshop 4 : operational scenarios and their attack techniques ──


class OperationalScenarioCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _NewRowOfTheStudy, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_operational.create"
    workshop_number = EbiosWorkshopNumber.W4
    model = OperationalScenario
    form_class = OperationalScenarioCreateForm
    modal_title_create = _l("New operational scenario")


class OperationalScenarioUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _RowOfTheStudy, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_operational.update"
    workshop_number = EbiosWorkshopNumber.W4
    model = OperationalScenario
    form_class = OperationalScenarioForm
    modal_title_update = _l("Edit operational scenario")


class OperationalScenarioDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_operational.delete"
    workshop_number = EbiosWorkshopNumber.W4
    model = OperationalScenario

    def get_assessment(self):
        return self.object.assessment


class OperationalScenarioConsolidateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Materialise an OperationalScenario into a Risk in the unified register."""

    permission_required = "risks.risk.create"

    def post(self, request, pk):
        scenario = get_scoped_object_or_404(request.user, OperationalScenario, pk=pk)
        if scenario.consolidated_risk_id:
            messages.info(
                request,
                _("This operational scenario is already consolidated as %(ref)s.")
                % {"ref": scenario.consolidated_risk.reference},
            )
            return _redirect_to_workshop(scenario.assessment, EbiosWorkshopNumber.W4)
        from risks.constants import RiskSourceType
        risk = Risk.objects.create(
            assessment=scenario.assessment,
            name=scenario.name,
            description=scenario.description,
            risk_source=RiskSourceType.EBIOS_OPERATIONAL,
            source_entity_id=scenario.pk,
            source_entity_type="risks.OperationalScenario",
            initial_likelihood=scenario.likelihood_v,
            initial_impact=scenario.gravity_level,
            current_likelihood=scenario.likelihood_v,
            current_impact=scenario.gravity_level,
            criteria_snapshot=scenario.criteria_snapshot,
            created_by=request.user,
        )
        risk.affected_support_assets.set(scenario.targeted_support_assets.all())
        scenario.consolidated_risk = risk
        scenario.save(update_fields=["consolidated_risk"])
        messages.success(
            request,
            _("Operational scenario consolidated as risk %(ref)s.") % {"ref": risk.reference},
        )
        return _redirect_to_workshop(scenario.assessment, EbiosWorkshopNumber.W4)


class _TechniqueOfAScenario(WorkshopRowFormMixin):
    """An attack technique : a row of its operational scenario, on the page of workshop 4."""

    workshop_number = EbiosWorkshopNumber.W4

    def get_scenario(self):
        return self.object.scenario

    def get_assessment(self):
        return self.get_scenario().assessment

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["scenario"] = self.get_scenario()
        return kwargs


class AttackTechniqueCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _TechniqueOfAScenario, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_operational.create"
    model = AttackTechnique
    form_class = AttackTechniqueCreateForm
    modal_title_create = _l("New attack technique")

    @cached_property
    def scenario(self):
        return get_scoped_object_or_404(
            self.request.user, OperationalScenario.objects.select_related("assessment"), pk=self.kwargs["scenario_pk"],
        )

    def get_scenario(self):
        return self.scenario

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class AttackTechniqueUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _TechniqueOfAScenario, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_operational.update"
    model = AttackTechnique
    form_class = AttackTechniqueForm
    modal_title_update = _l("Edit attack technique")


class AttackTechniqueDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_operational.delete"
    workshop_number = EbiosWorkshopNumber.W4
    model = AttackTechnique

    def get_assessment(self):
        return self.object.scenario.assessment


# ── Workshop 5 : the summary of the study and its security improvement plan ──


class EbiosSummaryUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, WorkshopRowFormMixin, HtmxFormMixin, UpdateView,
):
    """The summary of a study, edited card by card from the page of workshop 5."""

    permission_required = "risks.ebios_summary.update"
    workshop_number = EbiosWorkshopNumber.W5
    model = EbiosSummary
    form_class = EbiosSummaryForm
    modal_title_update = _l("Edit summary")

    def get_assessment(self):
        return self.object.assessment


class EbiosSummaryCaptureMappingsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Capture the before/after risk mapping snapshots from the W5 page.

    POST body fields: `slot` ∈ {"before", "after", "both"}.
    """

    permission_required = "risks.ebios_summary.update"

    def post(self, request, pk):
        summary = get_scoped_object_or_404(request.user, EbiosSummary, pk=pk)
        slot = request.POST.get("slot", "both")
        capture_before = slot in ("before", "both")
        capture_after = slot in ("after", "both")
        summary.capture_risk_mappings(
            capture_before=capture_before, capture_after=capture_after,
        )
        messages.success(request, _("Risk mapping snapshot captured."))
        return _redirect_to_workshop(summary.assessment, EbiosWorkshopNumber.W5)


class _MeasureOfThePlan(WorkshopRowFormMixin):
    """A measure of the security improvement plan : a row of the summary, on the page of workshop 5."""

    workshop_number = EbiosWorkshopNumber.W5

    def get_summary(self):
        return self.object.summary

    def get_assessment(self):
        return self.get_summary().assessment

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["summary"] = self.get_summary()
        return kwargs


class PACSMeasureCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, _MeasureOfThePlan, HtmxFormMixin, CreateView,
):
    permission_required = "risks.ebios_summary.create"
    model = PACSMeasure
    form_class = PACSMeasureCreateForm
    modal_title_create = _l("New PACS measure")

    @cached_property
    def summary(self):
        return get_scoped_object_or_404(
            self.request.user, EbiosSummary.objects.select_related("assessment"), pk=self.kwargs["summary_pk"],
        )

    def get_summary(self):
        return self.summary

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class PACSMeasureUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, _MeasureOfThePlan, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_summary.update"
    model = PACSMeasure
    form_class = PACSMeasureForm
    modal_title_update = _l("Edit PACS measure")


class PACSMeasureDeleteView(LoginRequiredMixin, WorkshopRowDeleteMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_summary.delete"
    workshop_number = EbiosWorkshopNumber.W5
    model = PACSMeasure

    def get_assessment(self):
        return self.object.summary.assessment

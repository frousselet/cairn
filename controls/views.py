# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web views of module 8 (controls).

**Registers** (controls, tests) run the house list stack, with
``ListSummaryMixin`` to the left of ``ScopeFilterMixin`` so the rail counts the
whole visible list. The URL contract has no table-body route : the list view
itself answers the HTMX refresh of ``#item-table-body`` (filters, search,
pagination) with the rows partial and an out-of-band pager.

**Detail pages** run ``ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin,
DetailView``. Every state change goes through the generic
``workflow:transition`` endpoint fed by the stepper : the gates and side
effects (implementation stamp, test activation, segregation of duties, the
effectiveness and due-date recomputation) live in each model's
``transition_to()``, so there is no transition view here.

**Acts that are not transitions** (create controls from requirements, raise a
finding, add or remove evidence) each call the one service or model method
that owns them.

**Tenancy** : every object resolved from a URL goes through a scope-filtered
queryset. A test, a run and an evidence file inherit their control's scopes
(``scope_parent_lookup``), resolved by ``core.scoping``; the evidence file is
only ever served by the permission-checked download view (RG-CTL-13).
"""

from datetime import timedelta
from itertools import groupby
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import (
    Case,
    CharField,
    Count,
    Exists,
    IntegerField,
    OuterRef,
    ProtectedError,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.utils.translation import ngettext, pgettext_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from accounts.mixins import HistoryUrlMixin, LifecycleStepperMixin, ScopeFilterMixin
from accounts.views import PermissionRequiredMixin
from context.models import Scope
from core.lifecycle import DomainRefusalError, LifecycleProtectedError, reportable
from core.mixins import (
    AdvancedFilterMixin,
    ColumnPreferenceMixin,
    ConfirmDeleteShellMixin,
    HtmxFormMixin,
    ListSummaryMixin,
    PredefinedFilterMixin,
    SavedFilterMixin,
    SortableListMixin,
    is_drawer_request,
)

from .constants import (
    CONTROL_IMPLEMENTED,
    CONTROL_STATES,
    RUN_DRAFT,
    RUN_VALIDATED,
    TEST_ACTIVE,
    TEST_DUE_REMINDER_DAYS,
    TEST_STATES,
    ControlEffectiveness,
    ControlNature,
    ControlTheme,
    RunResult,
)
from .forms import (
    ControlForm,
    ControlTestForm,
    ControlTestRunForm,
    EvidenceForm,
    FromRequirementsForm,
    RaiseFindingForm,
    scoped,
)
from .models import Control, ControlTest, ControlTestEvidence, ControlTestRun
from .services import create_controls_from_requirements

PAGE_SIZE = 50
RECENT_RUNS = 10


# ── Shared helpers ─────────────────────────────────────────


def _state_options(states):
    """``(code, label)`` pairs read off a lifecycle declaration (no DB at import)."""
    return [(code, label) for code, label, *_flags in states]


def _scoped_get(model, request, pk, qs=None):
    """One row by primary key, honouring the caller's scopes, else 404."""
    return get_object_or_404(scoped(qs if qs is not None else model._default_manager.all(), request.user), pk=pk)


def _attachment_disposition(filename):
    """A safe ``Content-Disposition: attachment`` value (no header injection)."""
    safe = "".join(ch for ch in (filename or "") if ch not in '"\\\r\n').strip() or "evidence"
    return f"attachment; filename=\"{safe}\"; filename*=UTF-8''{quote(safe)}"


def _detail_url(obj):
    if isinstance(obj, Control):
        return reverse("controls:control-detail", args=[obj.pk])
    if isinstance(obj, ControlTest):
        return reverse("controls:controltest-detail", args=[obj.pk])
    if isinstance(obj, ControlTestRun):
        return reverse("controls:controltestrun-detail", args=[obj.pk])
    return None


def _done(request, url):
    """After an act : a drawer gets a 204 + HX-Redirect, a page a redirect."""
    if is_drawer_request(request):
        return HttpResponse(status=204, headers={"HX-Redirect": url})
    return redirect(url)


def _users_with(related_name):
    User = get_user_model()
    return User.objects.filter(**{f"{related_name}__isnull": False}).distinct().order_by("last_name", "first_name")


class UserFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class CreatedByMixin:
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class FrozenFormGuardMixin:
    """A frozen form re-renders with its note; the model's own guard is the last resort."""

    def form_valid(self, form):
        if getattr(form, "frozen_note", None):
            form.add_error(None, form.frozen_note)
            return self.form_invalid(form)
        try:
            return super().form_valid(form)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)


class ProtectedDeleteMixin:
    """A lifecycle, ``PROTECT`` or write-once refusal becomes a message, not a 500."""

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
        except ValidationError as exc:
            messages.error(self.request, " ".join(exc.messages))
            success_url = self.get_refused_url()
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=204, headers={"HX-Redirect": success_url})
        return redirect(success_url)

    def get_refused_url(self):
        return self.get_success_url()


class PageFormNavMixin:
    """Breadcrumb, Cancel target and accent of the full-page form fallback."""

    page_form_nav = "controls:control-list"

    def get_form_parent(self):
        return None

    def get_page_form_cancel_url(self):
        obj = getattr(self, "object", None)
        if obj is not None and obj.pk and not obj._state.adding:
            return _detail_url(obj) or reverse(self.page_form_nav)
        parent = self.get_form_parent()
        return (_detail_url(parent) if parent is not None else None) or reverse(self.page_form_nav)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not ctx.get("is_modal"):
            ctx["cancel_url"] = self.get_page_form_cancel_url()
            ctx["form_nav"] = self.page_form_nav
            ctx["form_accent"] = "controls"
            parent = self.get_form_parent()
            if parent is not None:
                ctx["form_parent_label"] = parent.reference
                ctx["form_parent_url"] = _detail_url(parent)
        return ctx


class TableBodyRefreshMixin:
    """Answer the HTMX refresh of ``#item-table-body`` from the list view itself.

    The rows partial plus an out-of-band pager, as ``TableBodyPaginatedMixin``
    does for the modules that have a separate table-body route.
    """

    table_body_template_name = None

    def _is_table_refresh(self):
        headers = self.request.headers
        return (
            headers.get("HX-Request") == "true"
            and headers.get("HX-Boosted") != "true"
            and headers.get("HX-Target") == "item-table-body"
        )

    def render_to_response(self, context, **response_kwargs):
        if self._is_table_refresh():
            rows = render_to_string(self.table_body_template_name, context, request=self.request)
            pager = render_to_string("includes/pagination.html", {**context, "oob": True}, request=self.request)
            return HttpResponse(rows + pager)
        return super().render_to_response(context, **response_kwargs)


# ══ Control : the register ═════════════════════════════════

_OVERDUE = "overdue"
_ON_TIME = "on_time"

CONTROL_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Reference")},
    {"param": "name", "field": "name", "label": _l("Name")},
]
CONTROL_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "owner", "label": _l("Owner")},
    {"key": "status", "label": _l("Status")},
    {"key": "effectiveness", "label": _l("Effectiveness")},
    {"key": "next_due", "label": _l("Next test due")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
CONTROL_SORTABLE_FIELDS = {
    "reference": "reference",
    "name": "name",
    "owner": "owner__last_name",
    "status": "workflow_state",
    "effectiveness": "effectiveness",
    "next_due": "next_due",
}
CONTROL_SEARCH_FIELDS = ["reference", "name", "description"]


def _annotate_controls(qs):
    """Next test due, overdue flag and requirement count, one subquery each.

    The overdue flag is the SQL twin of ``Control.is_test_overdue``
    (RG-CTL-15), so the facet and the red date on the row never disagree.
    """
    today = timezone.localdate()
    active = ControlTest.objects.filter(control=OuterRef("pk"), workflow_state=TEST_ACTIVE).exclude(next_due_date=None)
    requirement_links = (
        Control.requirements.through.objects.filter(control_id=OuterRef("pk"))
        .order_by().values("control_id").annotate(n=Count("pk")).values("n")
    )
    return qs.annotate(
        next_due=Subquery(active.order_by("next_due_date").values("next_due_date")[:1]),
        requirement_count=Coalesce(Subquery(requirement_links, output_field=IntegerField()), Value(0)),
        overdue_flag=Case(
            When(Exists(active.filter(next_due_date__lt=today)), then=Value(_OVERDUE)),
            default=Value(_ON_TIME),
            output_field=CharField(),
        ),
    )


class _ControlAnnotationMixin:
    """Sits right of ``SortableListMixin`` so the annotations can be sorted on."""

    def get_queryset(self):
        return _annotate_controls(super().get_queryset()).select_related("owner").prefetch_related("scopes", "tags")


class _ControlListMixin:
    model = Control
    permission_required = "controls.control.read"
    context_object_name = "controls"
    paginate_by = PAGE_SIZE
    sortable_fields = CONTROL_SORTABLE_FIELDS
    default_sort = "reference"
    search_fields = CONTROL_SEARCH_FIELDS
    text_filters = CONTROL_TEXT_FILTERS
    columns = CONTROL_COLUMNS
    template_name = "controls/control_list.html"
    table_body_template_name = "controls/control_table_body.html"

    @cached_property
    def filter_groups(self):
        owners = _users_with("owned_controls")
        scopes = scoped(Scope.objects.all(), self.request.user).order_by("name")
        return [
            {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": _state_options(CONTROL_STATES)},
            {"param": "theme", "field": "theme", "label": _l("Theme"), "options": ControlTheme.choices},
            {"param": "nature", "field": "nature", "label": _l("Nature"), "options": ControlNature.choices},
            {"param": "effectiveness", "field": "effectiveness", "label": _l("Effectiveness"), "options": ControlEffectiveness.choices},
            {"param": "owner", "field": "owner", "label": _l("Owner"), "options": [(str(u.pk), u.display_name) for u in owners]},
            {"param": "scope", "field": "scopes", "label": _l("Scope"), "options": [(str(s.pk), s.name) for s in scopes]},
            {
                "param": "tests", "field": "overdue_flag", "label": _l("Tests"),
                "options": [(_OVERDUE, _l("Test overdue")), (_ON_TIME, _l("No test overdue"))],
            },
        ]

    def get_queryset(self):
        qs = self.filter_queryset_predefined(super().get_queryset())
        return self.filter_queryset_advanced(qs).distinct()


class ControlListView(_ControlListMixin, LoginRequiredMixin, PermissionRequiredMixin, TableBodyRefreshMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, _ControlAnnotationMixin, ListView):
    """The register of security controls (ISO/IEC 27001:2022 6.1.3, 8.1)."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            base = base.order_by()
            living = reportable(base)
            tested = living.exclude(effectiveness=ControlEffectiveness.NOT_TESTED)
            tested_count = tested.count()
            effective = tested.filter(effectiveness=ControlEffectiveness.EFFECTIVE).count()
            rate = round(100 * effective / tested_count) if tested_count else None
            overdue_tests = ControlTest.objects.filter(
                control__in=base.values("pk"), workflow_state=TEST_ACTIVE,
                next_due_date__lt=timezone.localdate(),
            ).count()
            validated = ControlTestRun.objects.filter(test__control=OuterRef("pk"), workflow_state=RUN_VALIDATED)
            never_tested = living.exclude(Exists(validated)).count()
            list_url = reverse("controls:control-list")
            ctx["list_kpis"] = [
                {
                    "label": _("Implemented controls"), "value": base.filter(workflow_state=CONTROL_IMPLEMENTED).count(),
                    "icon": "shield-check", "tone": "success",
                    "url": f"{list_url}?status={CONTROL_IMPLEMENTED}",
                },
                {
                    "label": _("Effective rate"), "value": rate, "suffix": "%" if rate is not None else None,
                    "icon": "patch-check", "tone": "accent",
                },
                {
                    "label": _("Overdue tests"), "value": overdue_tests, "icon": "calendar-x", "tone": "danger",
                    "url": f"{reverse('controls:controltest-list')}?due={_DUE_OVERDUE}",
                },
                {"label": _("Never tested"), "value": never_tested, "icon": "dash-circle", "tone": "warning"},
            ]
        ctx["today"] = timezone.localdate()
        return ctx


# ══ Control : one record ═══════════════════════════════════


class ControlDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = Control
    permission_required = "controls.control.read"
    template_name = "controls/control_detail.html"
    context_object_name = "control"

    def get_queryset(self):
        return super().get_queryset().select_related("owner").prefetch_related("scopes", "tags")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        control = self.object
        user = self.request.user
        validated = ControlTestRun.objects.filter(test=OuterRef("pk"), workflow_state=RUN_VALIDATED).order_by(
            "-performed_on", "-reviewed_at", "-created_at",
        )
        tests = list(
            control.tests.select_related("tester")
            .annotate(latest_result_value=Subquery(validated.values("result")[:1]))
            .order_by("name")
        )
        runs = list(
            ControlTestRun.objects.filter(test__control=control)
            .select_related("test", "performed_by", "reviewed_by")
            .order_by("-performed_on", "-created_at")[:RECENT_RUNS]
        )
        requirements = list(
            scoped(control.requirements.all(), user).select_related("framework")
            .order_by("framework__name", "requirement_number", "name")
        )
        requirement_groups = [
            {"framework": framework, "requirements": list(items)}
            for framework, items in groupby(requirements, key=lambda r: r.framework)
        ]
        ctx.update({
            "tests": tests,
            "recent_runs": runs,
            "run_count": ControlTestRun.objects.filter(test__control=control).count(),
            "requirement_groups": requirement_groups,
            "requirement_count": len(requirements),
            "risks": list(scoped(control.risks.all(), user).order_by("reference")),
            "treatment_plans": list(scoped(control.treatment_plans.all(), user).order_by("reference")),
            "pacs_measures": list(scoped(control.pacs_measures.all(), user).order_by("reference")),
            "support_assets": list(scoped(control.support_assets.all(), user).order_by("reference")),
            "objectives": list(scoped(control.objectives.all(), user).order_by("reference")),
            "policies": list(scoped(control.policies.all(), user).order_by("reference")),
            "next_test_due": control.next_test_due,
            "is_test_overdue": control.is_test_overdue,
            "is_stale": control.is_effectiveness_stale,
            "today": timezone.localdate(),
        })
        return ctx


class ControlCreateView(LoginRequiredMixin, PermissionRequiredMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    model = Control
    permission_required = "controls.control.create"
    form_class = ControlForm
    template_name = "controls/control_form.html"
    modal_template_name = "controls/control_form_modal.html"
    modal_title_create = _l("New control")
    modal_title_update = _l("Edit control")

    def get_success_url(self):
        return reverse("controls:control-detail", args=[self.object.pk])


class ControlUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, FrozenFormGuardMixin, UpdateView):
    """Edit a control's identity and links. A retired control renders frozen (RG-CTL-03)."""

    model = Control
    permission_required = "controls.control.update"
    form_class = ControlForm
    template_name = "controls/control_form.html"
    modal_template_name = "controls/control_form_modal.html"
    modal_title_create = _l("New control")
    modal_title_update = _l("Edit control")

    def get_success_url(self):
        return reverse("controls:control-detail", args=[self.object.pk])


class ControlDeleteView(LoginRequiredMixin, ConfirmDeleteShellMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    """Only a proposed control without tests is deletable; otherwise it is retired."""

    model = Control
    permission_required = "controls.control.delete"
    template_name = "controls/control_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("controls:control-list")

    def get_refused_url(self):
        return reverse("controls:control-detail", args=[self.object.pk])


class ControlFromRequirementsView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, FormView):
    """RG-CTL-05 : one proposed control per ticked, uncovered requirement of a framework.

    Choosing a framework in the drawer reloads the form (HTMX GET with
    ``?framework=``) with its checklist; on the page fallback, saving with a
    framework and no requirement re-renders the form with the checklist.
    """

    permission_required = "controls.control.create"
    form_class = FromRequirementsForm
    template_name = "controls/control_from_requirements_form.html"
    modal_template_name = "controls/control_from_requirements_form_modal.html"
    modal_title_create = _l("Create controls from requirements")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        if is_drawer_request(self.request):
            kwargs["reload_url"] = self.request.path
        if self.request.method == "GET":
            kwargs["framework"] = self._requested_framework()
        return kwargs

    def _requested_framework(self):
        from compliance.models import Framework

        raw = self.request.GET.get("framework")
        if not raw:
            return None
        try:
            return scoped(reportable(Framework.objects.all()), self.request.user).filter(pk=raw).first()
        except (ValueError, ValidationError):
            return None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not ctx.get("is_modal"):
            ctx["cancel_url"] = reverse("controls:control-list")
            ctx["form_nav"] = "controls:control-list"
            ctx["form_accent"] = "controls"
        return ctx

    def form_valid(self, form):
        framework = form.cleaned_data["framework"]
        requirement_ids = [r.pk for r in form.cleaned_data["requirements"]]
        created, skipped = create_controls_from_requirements(framework, self.request.user, requirement_ids=requirement_ids)
        if created:
            messages.success(self.request, ngettext(
                "%(n)d proposed control was created from %(framework)s.",
                "%(n)d proposed controls were created from %(framework)s.",
                len(created),
            ) % {"n": len(created), "framework": framework.short_name or framework.name})
        if skipped:
            messages.info(self.request, ngettext(
                "%(n)d requirement was skipped : it already has a control or is not applicable.",
                "%(n)d requirements were skipped : they already have a control or are not applicable.",
                len(skipped),
            ) % {"n": len(skipped)})
        if not created and not skipped:
            messages.info(self.request, _("No control was created."))
        return _done(self.request, reverse("controls:control-list"))


# ══ ControlTest : the register ═════════════════════════════

_DUE_OVERDUE = "overdue"
_DUE_SOON = "soon"
_DUE_LATER = "later"
_DUE_NONE = "none"

TEST_TEXT_FILTERS = [
    {"param": "reference", "field": "reference", "label": _l("Reference")},
    {"param": "name", "field": "name", "label": _l("Name")},
]
TEST_COLUMNS = [
    {"key": "reference", "label": _l("Ref."), "always": True},
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "control", "label": pgettext_lazy("control", "Control")},
    {"key": "tester", "label": _l("Tester")},
    {"key": "latest_result", "label": _l("Latest result")},
    {"key": "next_due", "label": _l("Next due")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
TEST_SORTABLE_FIELDS = {
    "reference": "reference",
    "name": "name",
    "control": "control__reference",
    "tester": "tester__last_name",
    "latest_result": "latest_result_value",
    "next_due": "next_due_date",
    "status": "workflow_state",
}
TEST_SEARCH_FIELDS = ["reference", "name", "control__reference", "control__name"]


def _annotate_tests(qs):
    """The latest validated result and the due window, the SQL twins of
    ``ControlTest.latest_result`` and ``ControlTest.is_overdue`` (RG-CTL-07)."""
    today = timezone.localdate()
    soon = today + timedelta(days=TEST_DUE_REMINDER_DAYS)
    validated = ControlTestRun.objects.filter(test=OuterRef("pk"), workflow_state=RUN_VALIDATED).order_by(
        "-performed_on", "-reviewed_at", "-created_at",
    )
    return qs.annotate(
        latest_result_value=Subquery(validated.values("result")[:1]),
        due_flag=Case(
            When(workflow_state=TEST_ACTIVE, next_due_date__lt=today, then=Value(_DUE_OVERDUE)),
            When(workflow_state=TEST_ACTIVE, next_due_date__lte=soon, then=Value(_DUE_SOON)),
            When(workflow_state=TEST_ACTIVE, next_due_date__isnull=False, then=Value(_DUE_LATER)),
            default=Value(_DUE_NONE),
            output_field=CharField(),
        ),
    )


class _TestAnnotationMixin:
    def get_queryset(self):
        return _annotate_tests(super().get_queryset()).select_related("control", "tester").prefetch_related("tags")


class _TestListMixin:
    model = ControlTest
    permission_required = "controls.test.read"
    context_object_name = "tests"
    paginate_by = PAGE_SIZE
    sortable_fields = TEST_SORTABLE_FIELDS
    default_sort = "next_due"
    search_fields = TEST_SEARCH_FIELDS
    text_filters = TEST_TEXT_FILTERS
    columns = TEST_COLUMNS
    template_name = "controls/controltest_list.html"
    table_body_template_name = "controls/controltest_table_body.html"

    @cached_property
    def filter_groups(self):
        testers = _users_with("control_tests")
        scopes = scoped(Scope.objects.all(), self.request.user).order_by("name")
        return [
            {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": _state_options(TEST_STATES)},
            {
                "param": "due", "field": "due_flag", "label": _l("Due"),
                "options": [
                    (_DUE_OVERDUE, _l("Overdue")),
                    (_DUE_SOON, _l("Due within 14 days")),
                    (_DUE_LATER, _l("Due later")),
                    (_DUE_NONE, _l("Not scheduled")),
                ],
            },
            {"param": "tester", "field": "tester", "label": _l("Tester"), "options": [(str(u.pk), u.display_name) for u in testers]},
            {"param": "result", "field": "latest_result_value", "label": _l("Latest result"), "options": RunResult.choices},
            {"param": "scope", "field": "control__scopes", "label": _l("Scope"), "options": [(str(s.pk), s.name) for s in scopes]},
        ]

    def get_queryset(self):
        qs = self.filter_queryset_predefined(super().get_queryset())
        return self.filter_queryset_advanced(qs).distinct()


class ControlTestListView(_TestListMixin, LoginRequiredMixin, PermissionRequiredMixin, TableBodyRefreshMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin, SavedFilterMixin, ColumnPreferenceMixin, ScopeFilterMixin, SortableListMixin, _TestAnnotationMixin, ListView):
    """Every test, its tester, its frequency, its latest result and when it is next due."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = getattr(self, "_summary_base_qs", None)
        if base is not None:
            base = base.order_by()
            list_url = reverse("controls:controltest-list")
            active = base.filter(workflow_state=TEST_ACTIVE)
            failing = active.filter(latest_result_value__in=[RunResult.PARTIAL, RunResult.FAIL]).count()
            ctx["list_kpis"] = [
                {
                    "label": _("Active tests"), "value": active.count(), "icon": "clipboard-check", "tone": "success",
                    "url": f"{list_url}?status={TEST_ACTIVE}",
                },
                {
                    "label": _("Overdue tests"), "value": active.filter(due_flag=_DUE_OVERDUE).count(),
                    "icon": "calendar-x", "tone": "danger", "url": f"{list_url}?due={_DUE_OVERDUE}",
                },
                {
                    "label": _("Due within 14 days"), "value": active.filter(due_flag=_DUE_SOON).count(),
                    "icon": "calendar-event", "tone": "warning", "url": f"{list_url}?due={_DUE_SOON}",
                },
                {"label": _("Latest result not a pass"), "value": failing, "icon": "x-circle", "tone": "danger"},
            ]
        return ctx


# ══ ControlTest : one record ═══════════════════════════════


class ControlTestDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = ControlTest
    permission_required = "controls.test.read"
    template_name = "controls/controltest_detail.html"
    context_object_name = "test"

    def get_queryset(self):
        return super().get_queryset().select_related("control", "tester").prefetch_related("tags")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        test = self.object
        ctx.update({
            "control": test.control,
            "runs": list(test.runs.select_related("performed_by", "reviewed_by").order_by("-performed_on", "-created_at")),
            "latest_run": test.latest_validated_run,
            "is_active": test.is_active,
            "is_overdue": test.is_overdue,
        })
        return ctx


class ControlTestCreateView(LoginRequiredMixin, PermissionRequiredMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, CreateView):
    """A new test of a control (``controls.test.create``). A retired control takes no new test."""

    model = ControlTest
    permission_required = "controls.test.create"
    form_class = ControlTestForm
    template_name = "controls/controltest_form.html"
    modal_template_name = "controls/controltest_form_modal.html"
    modal_title_create = _l("New test")
    modal_title_update = _l("Edit test")

    @cached_property
    def control(self):
        return _scoped_get(Control, self.request, self.kwargs["control_pk"])

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.has_perm(self.permission_required):
            if self.control.is_terminal_state:
                messages.error(request, _("A retired control takes no new test."))
                return _done(request, _detail_url(self.control))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["tester"] = self.control.owner_id
        return initial

    def get_form_parent(self):
        return self.control

    def form_valid(self, form):
        form.instance.control = self.control
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("controls:controltest-detail", args=[self.object.pk])


class ControlTestUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, FrozenFormGuardMixin, UpdateView):
    """Edit a test while it lives; the next due date follows (RG-CTL-07). Retired : frozen."""

    model = ControlTest
    permission_required = "controls.test.update"
    form_class = ControlTestForm
    template_name = "controls/controltest_form.html"
    modal_template_name = "controls/controltest_form_modal.html"
    page_form_nav = "controls:controltest-list"
    modal_title_create = _l("New test")
    modal_title_update = _l("Edit test")

    def get_form_parent(self):
        return self.object.control

    def get_success_url(self):
        return reverse("controls:controltest-detail", args=[self.object.pk])


class ControlTestDeleteView(LoginRequiredMixin, ConfirmDeleteShellMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    """Only a draft test without runs is deletable; otherwise it is retired (RG-CTL-08)."""

    model = ControlTest
    permission_required = "controls.test.delete"
    template_name = "controls/controltest_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("controls:control-detail", args=[self.object.control_id])

    def get_refused_url(self):
        return reverse("controls:controltest-detail", args=[self.object.pk])


# ══ ControlTestRun ═════════════════════════════════════════


class ControlTestRunDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryUrlMixin, LifecycleStepperMixin, DetailView):
    model = ControlTestRun
    permission_required = "controls.test.read"
    template_name = "controls/controltestrun_detail.html"
    context_object_name = "run"

    def get_queryset(self):
        return super().get_queryset().select_related("test", "test__control", "performed_by", "reviewed_by")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        run = self.object
        ctx.update({
            "test": run.test,
            "control": run.test.control,
            "evidence": list(run.evidence.select_related("uploaded_by").order_by("uploaded_at")),
            "findings": list(scoped(run.findings.all(), self.request.user).order_by("created_at")),
            "is_draft": run.workflow_state == RUN_DRAFT,
            "needs_finding": run.needs_finding,
        })
        return ctx


class _RunDraftOnlyMixin:
    """RG-CTL-09 : a run's content is editable only in ``draft``."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.has_perm(self.permission_required):
            run = _scoped_get(ControlTestRun, request, kwargs["pk"])
            if run.workflow_state != RUN_DRAFT:
                messages.error(request, _("A submitted test run is frozen : its content can no longer be changed."))
                return _done(request, _detail_url(run))
        return super().dispatch(request, *args, **kwargs)


class ControlTestRunCreateView(LoginRequiredMixin, PermissionRequiredMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, CreatedByMixin, FrozenFormGuardMixin, CreateView):
    """Record a run against an active test (RG-CTL-09), prefilled with the tester and today."""

    model = ControlTestRun
    permission_required = "controls.test.create"
    form_class = ControlTestRunForm
    template_name = "controls/controltestrun_form.html"
    modal_template_name = "controls/controltestrun_form_modal.html"
    page_form_nav = "controls:controltest-list"
    modal_title_create = _l("Record a run")
    modal_title_update = _l("Edit run")

    @cached_property
    def test(self):
        return _scoped_get(ControlTest, self.request, self.kwargs["test_pk"], qs=ControlTest.objects.select_related("control"))

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.has_perm(self.permission_required):
            if self.test.workflow_state != TEST_ACTIVE:
                messages.error(request, _("Runs can only be recorded against an active test."))
                return _done(request, _detail_url(self.test))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["test"] = self.test
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["performed_by"] = self.test.tester_id or self.request.user.pk
        initial["performed_on"] = timezone.localdate()
        return initial

    def get_form_parent(self):
        return self.test

    def get_success_url(self):
        return reverse("controls:controltestrun-detail", args=[self.object.pk])


class ControlTestRunUpdateView(_RunDraftOnlyMixin, LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, PageFormNavMixin, HtmxFormMixin, UserFormKwargsMixin, FrozenFormGuardMixin, UpdateView):
    model = ControlTestRun
    permission_required = "controls.test.update"
    form_class = ControlTestRunForm
    template_name = "controls/controltestrun_form.html"
    modal_template_name = "controls/controltestrun_form_modal.html"
    page_form_nav = "controls:controltest-list"
    modal_title_create = _l("Record a run")
    modal_title_update = _l("Edit run")

    def get_form_parent(self):
        return self.object.test

    def get_success_url(self):
        return reverse("controls:controltestrun-detail", args=[self.object.pk])


class ControlTestRunDeleteView(LoginRequiredMixin, ConfirmDeleteShellMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    """Only a draft run is deletable, with its evidence; afterwards it is withdrawn."""

    model = ControlTestRun
    permission_required = "controls.test.delete"
    template_name = "controls/controltestrun_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("controls:controltest-detail", args=[self.object.test_id])

    def get_refused_url(self):
        return reverse("controls:controltestrun-detail", args=[self.object.pk])


class RaiseFindingView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, FormView):
    """RG-CTL-16 : raise a finding from a validated partial or failed run, once."""

    permission_required = "controls.test.approve"
    form_class = RaiseFindingForm
    template_name = "controls/raise_finding_form.html"
    modal_template_name = "controls/raise_finding_form_modal.html"
    modal_title_create = _l("Raise a finding")

    @cached_property
    def run(self):
        qs = ControlTestRun.objects.select_related("test", "test__control")
        return _scoped_get(ControlTestRun, self.request, self.kwargs["pk"], qs=qs)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.has_perm(self.permission_required):
            if not self.run.needs_finding:
                messages.error(request, _("A finding can only be raised once, from a validated partial or failed run."))
                return _done(request, _detail_url(self.run))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["run"] = self.run
        if not ctx.get("is_modal"):
            ctx["cancel_url"] = _detail_url(self.run)
            ctx["form_nav"] = "controls:controltest-list"
            ctx["form_accent"] = "controls"
            ctx["form_parent_label"] = self.run.reference
            ctx["form_parent_url"] = _detail_url(self.run)
        return ctx

    def form_valid(self, form):
        try:
            finding = self.run.raise_finding(
                self.request.user, form.cleaned_data["finding_type"], form.cleaned_data.get("recommendation", ""),
            )
        except (DomainRefusalError, ValidationError) as exc:
            form.add_error(None, exc.messages if isinstance(exc, ValidationError) else str(exc))
            return self.form_invalid(form)
        messages.success(self.request, _("Finding %(ref)s was raised from run %(run)s.") % {
            "ref": finding.reference, "run": self.run.reference,
        })
        return _done(self.request, reverse("compliance:finding-detail", args=[finding.pk]))


# ══ Evidence (RG-CTL-13) ═══════════════════════════════════


class EvidenceUploadView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UserFormKwargsMixin, CreateView):
    """Attach a file to a run while it is in progress. Size and SHA-256 are stamped by the model."""

    model = ControlTestEvidence
    permission_required = "controls.test.update"
    form_class = EvidenceForm
    template_name = "controls/evidence_form.html"
    modal_template_name = "controls/evidence_form_modal.html"
    modal_title_create = _l("Add evidence")

    @cached_property
    def run(self):
        return _scoped_get(ControlTestRun, self.request, self.kwargs["pk"], qs=ControlTestRun.objects.select_related("test"))

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.has_perm(self.permission_required):
            if self.run.workflow_state != RUN_DRAFT:
                messages.error(request, _("Evidence can only be added or removed while the test run is in progress."))
                return _done(request, _detail_url(self.run))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["run"] = self.run
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["run"] = self.run
        if not ctx.get("is_modal"):
            ctx["cancel_url"] = _detail_url(self.run)
            ctx["form_nav"] = "controls:controltest-list"
            ctx["form_accent"] = "controls"
            ctx["form_parent_label"] = self.run.reference
            ctx["form_parent_url"] = _detail_url(self.run)
        return ctx

    def form_valid(self, form):
        try:
            self.object = form.save()
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, _("The evidence %(name)s was added.") % {"name": self.object.original_filename})
        if is_drawer_request(self.request):
            return HttpResponse(status=204, headers={"HX-Trigger": "formSaved"})
        return redirect(self.get_success_url())

    def get_success_url(self):
        return _detail_url(self.run)


class EvidenceDeleteView(LoginRequiredMixin, ConfirmDeleteShellMixin, PermissionRequiredMixin, ScopeFilterMixin, ProtectedDeleteMixin, DeleteView):
    """Remove an evidence file while its run is in progress (RG-CTL-13)."""

    model = ControlTestEvidence
    permission_required = "controls.test.update"
    template_name = "controls/evidence_confirm_delete_modal.html"

    def get_queryset(self):
        return super().get_queryset().select_related("run")

    def get_success_url(self):
        return reverse("controls:controltestrun-detail", args=[self.object.run_id])


class EvidenceDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Stream an evidence file, permission- and scope-checked (RG-CTL-13).

    Never a media URL : the path is guessable from the run and row ids, and a
    test's evidence may hold personal data or security configuration.
    """

    permission_required = "controls.test.read"

    def get(self, request, pk):
        item = _scoped_get(ControlTestEvidence, request, pk)
        if not item.file:
            raise Http404()
        try:
            handle = item.file.open("rb")
        except (FileNotFoundError, OSError):
            # A missing file is a 404, never a traceback naming the storage path.
            raise Http404() from None
        with handle:
            data = handle.read()
        response = HttpResponse(data, content_type="application/octet-stream")
        response["Content-Disposition"] = _attachment_disposition(item.original_filename or f"{item.pk}.bin")
        response["X-Content-Type-Options"] = "nosniff"
        return response

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The register of the agent skills (``/mcp/skills/``).

An agent skill is instance-wide : a procedure of the organization belongs to
no scope, so no view below mixes in ``ScopeFilterMixin``. What a skill says is
served to the agents connected to the MCP server once it is validated
(``mcp/skills.py``).
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _l
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import HistoryUrlMixin, LifecycleStepperMixin
from accounts.views import PermissionRequiredMixin
from core.lifecycle import DEFAULT_LIFECYCLE, LifecycleProtectedError
from core.mixins import (
    AdvancedFilterMixin,
    ColumnPreferenceMixin,
    CompleteOnRecordMixin,
    ConfirmDeleteShellMixin,
    HtmxFormMixin,
    ListSummaryMixin,
    PredefinedFilterMixin,
    SavedFilterMixin,
    SortableListMixin,
    TableBodyPaginatedMixin,
)
from mcp import skills
from mcp.forms import McpSkillCreateForm, McpSkillForm
from mcp.models import McpSkill

PAGE_SIZE = 50
STATE_OPTIONS = [(step.code, step.label) for step in DEFAULT_LIFECYCLE.steps]

SKILL_FILTER_GROUPS = [
    {"param": "status", "field": "workflow_state", "label": _l("Status"), "options": STATE_OPTIONS},
]
SKILL_TEXT_FILTERS = [
    {"param": "name", "field": "name", "label": _l("Name")},
]
SKILL_COLUMNS = [
    {"key": "name", "label": _l("Name"), "always": True},
    {"key": "description", "label": _l("Description")},
    {"key": "status", "label": _l("Status")},
    {"key": "actions", "label": _l("Actions"), "always": True},
]
SKILL_SORTABLE_FIELDS = {"name": "name", "status": "workflow_state"}
SKILL_SEARCH_FIELDS = ["reference", "name", "description"]


class _SkillFormMixin:
    """What the create and the edit form share : the acting user, the
    Cancel target and the breadcrumb of the full-page fallback."""

    model = McpSkill
    template_name = "mcp/skill_form.html"
    modal_template_name = "mcp/skill_form_modal.html"
    land_on_record = True
    modal_title_create = _l("New agent skill")
    modal_title_update = _l("Edit agent skill")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("mcp_skills:skill-detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not ctx.get("is_modal"):
            obj = getattr(self, "object", None)
            ctx["cancel_url"] = self.get_success_url() if obj is not None and obj.pk else reverse(
                "mcp_skills:skill-list"
            )
            ctx["form_nav"] = "mcp_skills:skill-list"
        return ctx


class McpSkillListView(
    LoginRequiredMixin, PermissionRequiredMixin, ListSummaryMixin, PredefinedFilterMixin, AdvancedFilterMixin,
    SavedFilterMixin, ColumnPreferenceMixin, SortableListMixin, ListView,
):
    model = McpSkill
    permission_required = "system.mcp_skill.read"
    filter_groups = SKILL_FILTER_GROUPS
    text_filters = SKILL_TEXT_FILTERS
    columns = SKILL_COLUMNS
    template_name = "mcp/skill_list.html"
    context_object_name = "skills"
    paginate_by = PAGE_SIZE
    sortable_fields = SKILL_SORTABLE_FIELDS
    default_sort = "name"
    search_fields = SKILL_SEARCH_FIELDS

    def get_queryset(self):
        qs = self.filter_queryset_predefined(super().get_queryset())
        return self.filter_queryset_advanced(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # What Cairn ships, and which of it a validated skill of the
        # organization replaces : the register says what the agents read.
        served = skills.catalogue()
        ctx["shipped_skills"] = [
            {"skill": skill, "replaced": served[name].origin == "organization"}
            for name, skill in skills.shipped().items()
        ]
        return ctx


class McpSkillTableBodyView(
    LoginRequiredMixin, PermissionRequiredMixin, TableBodyPaginatedMixin, PredefinedFilterMixin,
    AdvancedFilterMixin, SortableListMixin, ListView,
):
    model = McpSkill
    permission_required = "system.mcp_skill.read"
    template_name = "mcp/skill_table_body.html"
    context_object_name = "skills"
    paginate_by = PAGE_SIZE
    sortable_fields = SKILL_SORTABLE_FIELDS
    default_sort = "name"
    search_fields = SKILL_SEARCH_FIELDS
    filter_groups = SKILL_FILTER_GROUPS
    text_filters = SKILL_TEXT_FILTERS

    def get_queryset(self):
        qs = self.filter_queryset_predefined(super().get_queryset())
        return self.filter_queryset_advanced(qs)


class McpSkillDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, HistoryUrlMixin, LifecycleStepperMixin, CompleteOnRecordMixin,
    DetailView,
):
    model = McpSkill
    permission_required = "system.mcp_skill.read"
    template_name = "mcp/skill_detail.html"
    context_object_name = "skill"
    edit_url_name = "mcp_skills:skill-update"
    edit_permission = "system.mcp_skill.update"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        skill = self.object
        ctx["skill_md"] = skill.skill_md()
        ctx["is_served"] = skill.counts_in_reports
        if skill.is_terminal_state:
            # An archived skill is history : nothing is left to complete.
            ctx["completeness"] = None
        return ctx


class McpSkillCreateView(LoginRequiredMixin, PermissionRequiredMixin, _SkillFormMixin, HtmxFormMixin, CreateView):
    permission_required = "system.mcp_skill.create"
    form_class = McpSkillCreateForm

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class McpSkillUpdateView(LoginRequiredMixin, PermissionRequiredMixin, _SkillFormMixin, HtmxFormMixin, UpdateView):
    permission_required = "system.mcp_skill.update"
    form_class = McpSkillForm


class McpSkillDeleteView(LoginRequiredMixin, ConfirmDeleteShellMixin, PermissionRequiredMixin, DeleteView):
    model = McpSkill
    permission_required = "system.mcp_skill.delete"
    template_name = "mcp/skill_confirm_delete_modal.html"

    def get_success_url(self):
        return reverse("mcp_skills:skill-list")

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

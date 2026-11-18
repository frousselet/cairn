# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import (
    ACTION_PLAN_CANCELLABLE_STATUSES,
    ACTION_PLAN_REFUSAL_TRANSITIONS,
    ACTION_PLAN_TRANSITIONS,
    ActionPlanStatus,
    Priority,
)
from context.models.base import LegacyStatusMixin, ScopedModel
from core.completeness import Completeness, Requirement


class ComplianceActionPlan(LegacyStatusMixin, ScopedModel):
    REFERENCE_PREFIX = "CAPL"
    LIFECYCLE_NAME = "action_plan"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    risks = models.ManyToManyField(
        "risks.Risk",
        blank=True,
        related_name="action_plans",
        verbose_name=_("Linked risks"),
    )
    findings = models.ManyToManyField(
        "compliance.Finding",
        blank=True,
        related_name="action_plans",
        verbose_name=_("Linked findings"),
    )
    requirements = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="action_plans",
        verbose_name=_("Linked requirements"),
    )
    # Written on the plan page, not at creation : the lifecycle waits for
    # both before the plan is submitted for validation (``COMPLETENESS``).
    gap_description = models.TextField(_("Gap description"), blank=True, default="")
    remediation_plan = models.TextField(_("Remediation plan"), blank=True, default="")
    priority = models.CharField(
        _("Priority"), max_length=20, choices=Priority.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_action_plans",
        verbose_name=_("Supervisor"),
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_action_plans",
        verbose_name=_("Assignees"),
    )
    start_date = models.DateField(_("Start date"), null=True, blank=True)
    target_date = models.DateField(_("Target date"))
    completion_date = models.DateField(_("Completion date"), null=True, blank=True)
    progress_percentage = models.PositiveIntegerField(
        _("Progress (%)"), default=0
    )
    cost_estimate = models.DecimalField(
        _("Cost estimate"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    originating_review = models.ForeignKey(
        "reports.ManagementReview",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originated_action_plans",
        verbose_name=_("Originating management review"),
    )

    history = HistoricalRecords()

    # What a plan needs before somebody is asked to validate it : the gap it
    # closes, and how. Every later step waits for them as well, since a plan
    # may be imported straight into one of them.
    COMPLETENESS = Completeness(
        Requirement(
            "gap", _("describe the gap to close"),
            fields=["gap_description"], section="remediation",
        ),
        Requirement(
            "remediation", _("write what will be done to close it"),
            fields=["remediation_plan"], section="remediation",
        ),
        Requirement(
            "assignees", _("name who does the work"),
            fields=["assignees"], section="planning", blocking=False,
        ),
        Requirement(
            "linkages", _("link what it answers : a risk, a finding or a requirement"),
            any_of=["risks", "findings", "requirements"], section="linkages", blocking=False,
        ),
        before=(
            ActionPlanStatus.TO_VALIDATE.value,
            ActionPlanStatus.TO_IMPLEMENT.value,
            ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE.value,
            ActionPlanStatus.VALIDATED.value,
            ActionPlanStatus.CLOSED.value,
        ),
    )

    class Meta(ScopedModel.Meta):
        verbose_name = _("Compliance action plan")
        verbose_name_plural = _("Compliance action plans")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def get_absolute_url(self):
        return reverse("compliance:action-plan-detail", args=[self.pk])

    @property
    def workflow_perm_namespace(self):
        return "compliance.action_plan"

    @property
    def is_overdue(self):
        """Return True if target_date is past and the plan is still open."""
        if not self.target_date:
            return False
        if self.status in (ActionPlanStatus.CLOSED, ActionPlanStatus.CANCELLED):
            return False
        return self.target_date < timezone.localdate()

    def get_allowed_transitions(self):
        """Return the list of statuses this action plan can transition to."""
        allowed = list(ACTION_PLAN_TRANSITIONS.get(self.status, []))
        if self.status in ACTION_PLAN_CANCELLABLE_STATUSES:
            allowed.append(ActionPlanStatus.CANCELLED)
        return allowed


    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        """Perform a lifecycle transition with validation and audit trail.

        Routed through the workflow framework (the ``action_plan`` workflow is
        generated from the same constants as before), keeping the legacy
        contract: raises ``ValueError`` if the transition is not allowed or a
        refusal comment is missing, auto-fills the completion fields when
        closing, and records an :class:`ActionPlanTransition` row.
        """
        from compliance.models.action_plan_transition import ActionPlanTransition

        previous = self.workflow_state or self.status
        if target == ActionPlanStatus.CLOSED:
            self.completion_date = timezone.localdate()
            self.progress_percentage = 100

        transition = super().transition_to(
            target, user, comment=comment,
            enforce_permission=enforce_permission, save=save,
        )

        if save and user is not None:
            ActionPlanTransition.objects.create(
                action_plan=self,
                from_status=previous,
                to_status=target,
                performed_by=user,
                comment=comment or "",
                is_refusal=ACTION_PLAN_REFUSAL_TRANSITIONS.get(previous) == target,
            )
        return transition

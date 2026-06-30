from django.conf import settings
from django.db import models
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
from context.models.base import ScopedModel


class ComplianceActionPlan(ScopedModel):
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
    gap_description = models.TextField(_("Gap description"))
    remediation_plan = models.TextField(_("Remediation plan"))
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
    status = models.CharField(
        _("Status"),
        max_length=30,
        choices=ActionPlanStatus.choices,
        default=ActionPlanStatus.NEW,
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

    class Meta(ScopedModel.Meta):
        verbose_name = _("Compliance action plan")
        verbose_name_plural = _("Compliance action plans")

    def __str__(self):
        return f"{self.reference} : {self.name}"

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
        return self.target_date < timezone.now().date()

    def get_allowed_transitions(self):
        """Return the list of statuses this action plan can transition to."""
        allowed = list(ACTION_PLAN_TRANSITIONS.get(self.status, []))
        if self.status in ACTION_PLAN_CANCELLABLE_STATUSES:
            allowed.append(ActionPlanStatus.CANCELLED)
        return allowed

    def save(self, *args, **kwargs):
        from core.workflow import sync_legacy_status

        sync_legacy_status(self, kwargs, ActionPlanStatus.NEW)
        super().save(*args, **kwargs)

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
            self.completion_date = timezone.now().date()
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

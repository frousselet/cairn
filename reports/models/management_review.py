import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import LegacyStatusMixin, ScopedModel
from reports.constants import (
    MANAGEMENT_REVIEW_CANCELLABLE_STATUSES,
    MANAGEMENT_REVIEW_TRANSITIONS,
    DecisionCategory,
    DecisionInputClause,
    DecisionPriority,
    DecisionStatus,
    IsmsChangeStatus,
    IsmsChangeType,
    ManagementReviewFrequency,
    ManagementReviewStatus,
    ParticipantRole,
)


class ManagementReview(LegacyStatusMixin, ScopedModel):
    """Persistent management review record (ISO 27001:2022 clause 9.3).

    Captures the full life cycle of a management review: planning, preparation,
    conduct, and closure. When closed, the aggregated inputs and outputs are
    frozen into `snapshot_data` so that exports remain immutable for audit
    purposes.
    """

    REFERENCE_PREFIX = "MRVW"
    LIFECYCLE_NAME = "management_review"

    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    frequency = models.CharField(
        _("Frequency"),
        max_length=20,
        choices=ManagementReviewFrequency.choices,
    )
    period_start = models.DateField(_("Review period start"))
    period_end = models.DateField(_("Review period end"))
    planned_date = models.DateField(_("Planned date"))
    held_date = models.DateField(_("Held date"), null=True, blank=True)
    location = models.CharField(_("Location"), max_length=255, blank=True, default="")
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="facilitated_management_reviews",
        verbose_name=_("Facilitator"),
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_management_reviews",
        verbose_name=_("Approver"),
    )
    next_review_date = models.DateField(_("Next review date"), null=True, blank=True)
    summary = models.TextField(_("Executive summary"), blank=True, default="")
    agenda = models.TextField(_("Agenda"), blank=True, default="")
    minutes = models.TextField(_("Minutes"), blank=True, default="")
    snapshot_data = models.JSONField(
        _("Frozen snapshot data"), blank=True, null=True, default=None,
    )
    snapshot_taken_at = models.DateTimeField(
        _("Snapshot taken at"), null=True, blank=True,
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Management review")
        verbose_name_plural = _("Management reviews")

    def __str__(self):
        return f"{self.reference} : {self.title}"

    @property
    def has_snapshot(self):
        return bool(self.snapshot_data)

    def get_allowed_transitions(self):
        """Return the list of statuses this review can transition to."""
        allowed = list(MANAGEMENT_REVIEW_TRANSITIONS.get(self.status, []))
        if self.status in MANAGEMENT_REVIEW_CANCELLABLE_STATUSES:
            allowed.append(ManagementReviewStatus.CANCELLED)
        return allowed

    def can_close(self):
        """Check whether closure prerequisites are met.

        Returns (bool ok, list[str] blocking_reasons).
        """
        reasons = []
        if self.status != ManagementReviewStatus.HELD:
            reasons.append(
                _("The review must be in 'held' status before closure.")
            )
        incomplete = self.decisions.filter(
            models.Q(owner__isnull=True) | models.Q(due_date__isnull=True)
        )
        if incomplete.exists():
            reasons.append(
                _("All decisions must have an owner and a due date.")
            )
        return (not reasons, reasons)

    @property
    def workflow_perm_namespace(self):
        return "reports.management_review"


    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        """Perform a status transition with audit trail.

        Routed through the standardised lifecycle engine (the
        ``management_review`` lifecycle is generated from the same constants as
        before), keeping the legacy contract. Raises ValueError when:
          - the transition is not allowed,
          - the transition is a cancellation without a comment,
          - closure preconditions are not met.
        """
        from core.lifecycle import validate_transition
        from reports.models.management_review_transition import (
            ManagementReviewTransition,
        )

        lifecycle = self.get_lifecycle()
        previous = self.workflow_state or self.status or lifecycle.initial_step.code
        # Legality and mandatory-comment checks first (legacy precedence),
        # then the closure preconditions.
        validate_transition(lifecycle, previous, target, comment=comment, enforce_permission=False)
        if target == ManagementReviewStatus.CLOSED:
            ok, reasons = self.can_close()
            if not ok:
                raise ValueError("; ".join(str(r) for r in reasons))

        if target == ManagementReviewStatus.HELD and not self.held_date:
            # Use the local date, not the UTC date: timezone.now().date() can be
            # a day behind localdate() near midnight in a non-UTC timezone.
            self.held_date = timezone.localdate()

        transition = super().transition_to(
            target, user, comment=comment,
            enforce_permission=enforce_permission, save=save,
        )

        if save and user is not None:
            ManagementReviewTransition.objects.create(
                review=self,
                from_status=previous,
                to_status=target,
                performed_by=user,
                comment=comment or "",
            )
        return transition

    def take_snapshot(self, data):
        """Store a frozen snapshot of the aggregated data."""
        self.snapshot_data = data
        self.snapshot_taken_at = timezone.now()
        self.save(update_fields=[
            "snapshot_data", "snapshot_taken_at", "updated_at",
        ])


class ManagementReviewParticipant(models.Model):
    """Participant (internal user or external person) of a management review."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    review = models.ForeignKey(
        ManagementReview,
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name=_("Review"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="management_review_participations",
        verbose_name=_("User"),
    )
    external_name = models.CharField(
        _("External name"), max_length=255, blank=True, default="",
    )
    external_role = models.CharField(
        _("External role"), max_length=255, blank=True, default="",
    )
    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=ParticipantRole.choices,
        default=ParticipantRole.CONTRIBUTOR,
    )
    attended = models.BooleanField(_("Attended"), default=False)
    signature_data = models.TextField(
        _("Signature data"), blank=True, default="",
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["role", "external_name"]
        verbose_name = _("Management review participant")
        verbose_name_plural = _("Management review participants")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(user__isnull=False)
                    | ~models.Q(external_name="")
                ),
                name="participant_user_or_external",
            ),
        ]

    def __str__(self):
        if self.user_id:
            return f"{self.user} ({self.get_role_display()})"
        return f"{self.external_name} ({self.get_role_display()})"

    @property
    def display_name(self):
        if self.user_id:
            return str(self.user)
        return self.external_name

    @property
    def display_role(self):
        if self.user_id:
            return self.get_role_display()
        return self.external_role or self.get_role_display()


class ManagementReviewDecision(models.Model):
    """Structured decision recorded during a management review (clause 9.3.3)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    reference = models.CharField(
        _("Reference"), max_length=50, unique=True, blank=True,
    )
    review = models.ForeignKey(
        ManagementReview,
        on_delete=models.CASCADE,
        related_name="decisions",
        verbose_name=_("Review"),
    )
    category = models.CharField(
        _("Category"), max_length=30, choices=DecisionCategory.choices,
    )
    input_clause = models.CharField(
        _("Related input clause"),
        max_length=5,
        choices=DecisionInputClause.choices,
        blank=True,
        default="",
    )
    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"))
    rationale = models.TextField(_("Rationale"), blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_management_review_decisions",
        verbose_name=_("Owner"),
    )
    due_date = models.DateField(_("Due date"), null=True, blank=True)
    priority = models.CharField(
        _("Priority"),
        max_length=20,
        choices=DecisionPriority.choices,
        default=DecisionPriority.MEDIUM,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=DecisionStatus.choices,
        default=DecisionStatus.PENDING,
    )
    implemented_at = models.DateField(
        _("Implemented at"), null=True, blank=True,
    )
    implementation_evidence = models.TextField(
        _("Implementation evidence"), blank=True, default="",
    )
    linked_action_plan = models.ForeignKey(
        "compliance.ComplianceActionPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originating_decisions",
        verbose_name=_("Linked action plan"),
    )
    linked_treatment_plan = models.ForeignKey(
        "risks.RiskTreatmentPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originating_decisions",
        verbose_name=_("Linked treatment plan"),
    )
    linked_objective = models.ForeignKey(
        "context.Objective",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originating_decisions",
        verbose_name=_("Linked objective"),
    )
    linked_isms_change = models.ForeignKey(
        "reports.IsmsChange",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originating_decisions",
        verbose_name=_("Linked ISMS change"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["review", "-priority", "due_date"]
        verbose_name = _("Management review decision")
        verbose_name_plural = _("Management review decisions")

    def __str__(self):
        return f"{self.reference} : {self.title}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_next_reference()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_next_reference(cls):
        prefix = "DECS-"
        existing = cls.objects.filter(
            reference__startswith=prefix,
        ).values_list("reference", flat=True)
        max_num = 0
        for ref in existing:
            try:
                num = int(ref[len(prefix):])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        return f"DECS-{max_num + 1}"


class IsmsChange(models.Model):
    """ISMS change recorded as an output of a management review (clause 9.3.3)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    reference = models.CharField(
        _("Reference"), max_length=50, unique=True, blank=True,
    )
    review = models.ForeignKey(
        ManagementReview,
        on_delete=models.CASCADE,
        related_name="isms_changes",
        verbose_name=_("Review"),
    )
    change_type = models.CharField(
        _("Change type"),
        max_length=20,
        choices=IsmsChangeType.choices,
    )
    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"))
    impact_analysis = models.TextField(
        _("Impact analysis"), blank=True, default="",
    )
    affected_scopes = models.ManyToManyField(
        "context.Scope",
        blank=True,
        related_name="affected_by_isms_changes",
        verbose_name=_("Affected scopes"),
    )
    affected_frameworks = models.ManyToManyField(
        "compliance.Framework",
        blank=True,
        related_name="affected_by_isms_changes",
        verbose_name=_("Affected frameworks"),
    )
    affected_policies = models.TextField(
        _("Affected policies"), blank=True, default="",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_isms_changes",
        verbose_name=_("Owner"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=IsmsChangeStatus.choices,
        default=IsmsChangeStatus.PROPOSED,
    )
    target_date = models.DateField(_("Target date"), null=True, blank=True)
    implemented_at = models.DateField(
        _("Implemented at"), null=True, blank=True,
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["review", "target_date"]
        verbose_name = _("ISMS change")
        verbose_name_plural = _("ISMS changes")

    def __str__(self):
        return f"{self.reference} : {self.title}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_next_reference()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_next_reference(cls):
        prefix = "ICHG-"
        existing = cls.objects.filter(
            reference__startswith=prefix,
        ).values_list("reference", flat=True)
        max_num = 0
        for ref in existing:
            try:
                num = int(ref[len(prefix):])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        return f"ICHG-{max_num + 1}"


class ManagementReviewComment(models.Model):
    """Comment thread attached to a management review."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    review = models.ForeignKey(
        ManagementReview,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Review"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="management_review_comments",
        verbose_name=_("Author"),
    )
    content = models.TextField(_("Content"))
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Management review comment")
        verbose_name_plural = _("Management review comments")

    def __str__(self):
        return f"{self.author} @ {self.review.reference}"

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import (
    DEFAULT_IMPACT_SCALES,
    DEFAULT_LIKELIHOOD_SCALES,
    RiskPriority,
    RiskSourceType,
    RiskStatus,
    TreatmentDecision,
)


class Risk(BaseModel):
    REFERENCE_PREFIX = "RISK"
    LIFECYCLE_NAME = "risk"

    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="risks",
        verbose_name=_("Assessment"),
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    risk_source = models.CharField(
        _("Risk source"),
        max_length=30,
        choices=RiskSourceType.choices,
        default=RiskSourceType.MANUAL,
    )
    source_entity_id = models.UUIDField(
        _("Source entity ID"), null=True, blank=True
    )
    source_entity_type = models.CharField(
        _("Source entity type"), max_length=100, blank=True
    )
    affected_essential_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="risks",
        verbose_name=_("Affected essential assets"),
    )
    affected_support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="risks",
        verbose_name=_("Affected support assets"),
    )
    impact_confidentiality = models.BooleanField(
        _("Confidentiality impact"), default=False
    )
    impact_integrity = models.BooleanField(_("Integrity impact"), default=False)
    impact_availability = models.BooleanField(
        _("Availability impact"), default=False
    )
    # Initial risk levels
    initial_likelihood = models.PositiveIntegerField(
        _("Initial likelihood"), null=True, blank=True
    )
    initial_impact = models.PositiveIntegerField(
        _("Initial impact"), null=True, blank=True
    )
    initial_risk_level = models.PositiveIntegerField(
        _("Initial risk level"), null=True, blank=True
    )
    # Current risk levels
    current_likelihood = models.PositiveIntegerField(
        _("Current likelihood"), null=True, blank=True
    )
    current_impact = models.PositiveIntegerField(
        _("Current impact"), null=True, blank=True
    )
    current_risk_level = models.PositiveIntegerField(
        _("Current risk level"), null=True, blank=True
    )
    # Residual risk levels
    residual_likelihood = models.PositiveIntegerField(
        _("Residual likelihood"), null=True, blank=True
    )
    residual_impact = models.PositiveIntegerField(
        _("Residual impact"), null=True, blank=True
    )
    residual_risk_level = models.PositiveIntegerField(
        _("Residual risk level"), null=True, blank=True
    )
    treatment_decision = models.CharField(
        _("Treatment decision"),
        max_length=20,
        choices=TreatmentDecision.choices,
        default=TreatmentDecision.NOT_DECIDED,
    )
    treatment_justification = models.TextField(
        _("Treatment justification"), blank=True
    )
    risk_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_risks",
        verbose_name=_("Risk owner"),
    )
    priority = models.CharField(
        _("Priority"),
        max_length=20,
        choices=RiskPriority.choices,
        default=RiskPriority.LOW,
    )
    status = models.CharField(
        _("Status"),
        max_length=30,
        choices=RiskStatus.choices,
        default=RiskStatus.IDENTIFIED,
    )
    review_date = models.DateField(_("Review date"), null=True, blank=True)
    linked_requirements = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="linked_risks",
        verbose_name=_("Linked requirements"),
    )
    criteria_snapshot = models.JSONField(
        _("Criteria snapshot"),
        null=True,
        blank=True,
        help_text=_(
            "Frozen copy of the risk matrix and criteria metadata at the time "
            "of first evaluation. Used to keep historical scores immutable even "
            "if the underlying criteria are edited later."
        ),
    )
    # FK to unimplemented modules
    # linked_measures = ...
    # linked_incidents = ...
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Risk")
        verbose_name_plural = _("Risks")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def _get_valid_levels(self):
        """Return (likelihood_levels, impact_levels) sets from criteria or defaults."""
        from risks.models.risk_criteria import RiskCriteria

        criteria = None
        if self.assessment_id:
            criteria = getattr(self.assessment, "risk_criteria", None)
        if not criteria:
            criteria = (
                RiskCriteria.objects.filter(is_default=True).first()
                or RiskCriteria.objects.filter(workflow_state="validated").first()
            )
        if criteria:
            l_levels = set(
                criteria.scale_levels.filter(scale_type="likelihood")
                .values_list("level", flat=True)
            )
            i_levels = set(
                criteria.scale_levels.filter(scale_type="impact")
                .values_list("level", flat=True)
            )
            if l_levels and i_levels:
                return l_levels, i_levels
        return (
            {level for level, _ in DEFAULT_LIKELIHOOD_SCALES},
            {level for level, _ in DEFAULT_IMPACT_SCALES},
        )

    def clean(self):
        super().clean()
        l_levels, i_levels = self._get_valid_levels()
        errors = {}
        for fname in ("initial_likelihood", "current_likelihood", "residual_likelihood"):
            val = getattr(self, fname)
            if val is not None and val not in l_levels:
                errors[fname] = (
                    _("Value must be one of %(levels)s.") % {"levels": sorted(l_levels)}
                )
        for fname in ("initial_impact", "current_impact", "residual_impact"):
            val = getattr(self, fname)
            if val is not None and val not in i_levels:
                errors[fname] = (
                    _("Value must be one of %(levels)s.") % {"levels": sorted(i_levels)}
                )
        if errors:
            raise ValidationError(errors)

    def _resolve_scoring_matrix(self):
        """Return the matrix used for scoring: snapshot first, live criteria as fallback."""
        if self.criteria_snapshot and self.criteria_snapshot.get("matrix"):
            return self.criteria_snapshot["matrix"]
        criteria = getattr(self.assessment, "risk_criteria", None) if self.assessment_id else None
        if criteria and criteria.risk_matrix:
            return criteria.risk_matrix
        return None

    def calculate_risk_level(self, likelihood, impact):
        """Calculate risk level using the snapshot (if present) or the live criteria."""
        if likelihood is None or impact is None:
            return None
        matrix = self._resolve_scoring_matrix()
        if matrix:
            level = matrix.get(f"{likelihood},{impact}")
            if level is not None:
                return int(level)
        return None

    def _capture_criteria_snapshot(self):
        """Freeze the assessment's criteria into criteria_snapshot. No-op if already set."""
        if self.criteria_snapshot:
            return
        if not self.assessment_id:
            return
        criteria = getattr(self.assessment, "risk_criteria", None)
        if not criteria or not criteria.risk_matrix:
            return
        self.criteria_snapshot = {
            "criteria_id": str(criteria.pk),
            "criteria_reference": criteria.reference,
            "criteria_name": criteria.name,
            "criteria_version": criteria.version,
            "matrix": dict(criteria.risk_matrix),
            "captured_at": timezone.now().isoformat(),
        }

    def save(self, *args, **kwargs):
        has_evaluation = (
            (self.initial_likelihood is not None and self.initial_impact is not None)
            or (self.current_likelihood is not None and self.current_impact is not None)
            or (self.residual_likelihood is not None and self.residual_impact is not None)
        )
        if has_evaluation and not self.criteria_snapshot:
            self._capture_criteria_snapshot()
        if self.initial_likelihood is not None and self.initial_impact is not None:
            calculated = self.calculate_risk_level(
                self.initial_likelihood, self.initial_impact
            )
            if calculated is not None:
                self.initial_risk_level = calculated
        if self.current_likelihood is not None and self.current_impact is not None:
            calculated = self.calculate_risk_level(
                self.current_likelihood, self.current_impact
            )
            if calculated is not None:
                self.current_risk_level = calculated
        if self.residual_likelihood is not None and self.residual_impact is not None:
            calculated = self.calculate_risk_level(
                self.residual_likelihood, self.residual_impact
            )
            if calculated is not None:
                self.residual_risk_level = calculated
        from core.workflow import sync_legacy_status

        sync_legacy_status(self, kwargs, RiskStatus.IDENTIFIED)
        super().save(*args, **kwargs)

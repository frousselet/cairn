from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel


class StrategicScenario(BaseModel):
    """EBIOS RM Workshop 3 - Strategic scenario.

    High-level attack path linking an SR/OV pair to targeted feared events
    through the ecosystem. Only scenarios with `is_retained = True` can be
    declined into operational scenarios (workshop 4).

    `risk_level` is auto-computed at save() via the assessment's risk matrix
    (likelihood x gravity). The matrix is snapshot in `criteria_snapshot` at
    first scoring so historical scores stay immutable.
    """

    REFERENCE_PREFIX = "ESTS"

    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_strategic_scenarios",
        verbose_name=_("Assessment"),
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    sr_ov_pair = models.ForeignKey(
        "risks.RiskSourceObjectivePair",
        on_delete=models.PROTECT,
        related_name="strategic_scenarios",
        verbose_name=_("SR/OV pair"),
    )
    targeted_feared_events = models.ManyToManyField(
        "risks.FearedEvent",
        blank=True,
        related_name="strategic_scenarios",
        verbose_name=_("Targeted feared events"),
    )
    gravity_level = models.PositiveSmallIntegerField(
        _("Gravity level"), null=True, blank=True,
        help_text=_("Gravity on the assessment impact scale."),
    )
    gravity_justification = models.TextField(_("Gravity justification"), blank=True)
    likelihood_level = models.PositiveSmallIntegerField(
        _("Strategic likelihood"), null=True, blank=True,
        help_text=_("Likelihood on the assessment likelihood scale."),
    )
    likelihood_justification = models.TextField(_("Likelihood justification"), blank=True)
    risk_level = models.PositiveSmallIntegerField(
        _("Risk level"), null=True, blank=True,
        help_text=_("Computed via the assessment risk matrix."),
    )
    existing_security_measures = models.TextField(_("Existing security measures"), blank=True)
    is_retained = models.BooleanField(_("Retained for workshop 4"), default=True)
    retention_justification = models.TextField(_("Retention justification"), blank=True)
    consolidated_risk = models.ForeignKey(
        "risks.Risk",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_strategic_scenarios",
        verbose_name=_("Consolidated risk"),
    )
    criteria_snapshot = models.JSONField(
        _("Criteria snapshot"),
        null=True,
        blank=True,
        help_text=_(
            "Frozen copy of the risk matrix used at first scoring. Keeps "
            "risk_level immutable when the criteria are later edited."
        ),
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-risk_level", "-created_at"]
        verbose_name = _("EBIOS RM strategic scenario")
        verbose_name_plural = _("EBIOS RM strategic scenarios")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def _resolve_scoring_matrix(self):
        if self.criteria_snapshot and self.criteria_snapshot.get("matrix"):
            return self.criteria_snapshot["matrix"]
        if not self.assessment_id:
            return None
        criteria = getattr(self.assessment, "risk_criteria", None)
        if criteria and criteria.risk_matrix:
            return criteria.risk_matrix
        return None

    def _capture_criteria_snapshot(self):
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
        if self.likelihood_level is not None and self.gravity_level is not None:
            if not self.criteria_snapshot:
                self._capture_criteria_snapshot()
            matrix = self._resolve_scoring_matrix()
            if matrix:
                level = matrix.get(f"{self.likelihood_level},{self.gravity_level}")
                if level is not None:
                    self.risk_level = int(level)
        super().save(*args, **kwargs)

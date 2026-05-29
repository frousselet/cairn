from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import Relevance


# Static mapping of Relevance to a 1..4 numeric weight used by the priority
# score formula. Kept module-level so it is testable and overridable.
RELEVANCE_WEIGHT = {
    Relevance.LOW: 1,
    Relevance.MEDIUM: 2,
    Relevance.HIGH: 3,
    Relevance.CRITICAL: 4,
}


class RiskSourceObjectivePair(BaseModel):
    """EBIOS RM Workshop 2 - SR/OV pair.

    Formal evaluation of a (risk source, targeted objective) combination.
    Only retained pairs (`is_retained = True`) can be referenced by the
    strategic scenarios of workshop 3.
    """

    REFERENCE_PREFIX = "ESOV"

    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_sr_ov_pairs",
        verbose_name=_("Assessment"),
    )
    risk_source = models.ForeignKey(
        "risks.RiskSource",
        on_delete=models.CASCADE,
        related_name="sr_ov_pairs",
        verbose_name=_("Risk source"),
    )
    targeted_objective = models.ForeignKey(
        "risks.TargetedObjective",
        on_delete=models.CASCADE,
        related_name="sr_ov_pairs",
        verbose_name=_("Targeted objective"),
    )
    relevance = models.CharField(
        _("Relevance"),
        max_length=16,
        choices=Relevance.choices,
        default=Relevance.MEDIUM,
    )
    relevance_justification = models.TextField(_("Relevance justification"), blank=True)
    priority_score = models.PositiveSmallIntegerField(
        _("Priority score"),
        null=True,
        blank=True,
        help_text=_(
            "Aggregated score (1..4) derived from the risk source threat level "
            "and the SR/OV relevance. Recomputed on save."
        ),
    )
    is_retained = models.BooleanField(_("Retained for workshop 3"), default=True)
    retention_justification = models.TextField(_("Retention justification"), blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-priority_score", "-created_at"]
        verbose_name = _("EBIOS RM SR/OV pair")
        verbose_name_plural = _("EBIOS RM SR/OV pairs")
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "risk_source", "targeted_objective"],
                name="unique_sr_ov_pair_per_assessment",
            ),
        ]

    def __str__(self):
        return f"{self.reference} : {self.risk_source} / {self.targeted_objective}"

    def _compute_priority_score(self):
        """Aggregate priority = max(risk_source.threat_level, relevance_weight)."""
        weight = RELEVANCE_WEIGHT.get(self.relevance)
        threat = None
        if self.risk_source_id:
            threat = getattr(self.risk_source, "threat_level", None)
        candidates = [v for v in (weight, threat) if v is not None]
        return max(candidates) if candidates else None

    def save(self, *args, **kwargs):
        self.priority_score = self._compute_priority_score()
        super().save(*args, **kwargs)

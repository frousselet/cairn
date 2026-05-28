from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel


class ISO27005Risk(BaseModel):
    REFERENCE_PREFIX = "I27R"

    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="iso27005_risks",
        verbose_name=_("Assessment"),
    )
    threat = models.ForeignKey(
        "risks.Threat",
        on_delete=models.CASCADE,
        related_name="iso27005_risks",
        verbose_name=_("Threat"),
    )
    vulnerability = models.ForeignKey(
        "risks.Vulnerability",
        on_delete=models.CASCADE,
        related_name="iso27005_risks",
        verbose_name=_("Vulnerability"),
    )
    affected_essential_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="iso27005_risks",
        verbose_name=_("Affected essential assets"),
    )
    affected_support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="iso27005_risks",
        verbose_name=_("Affected support assets"),
    )
    threat_likelihood = models.PositiveIntegerField(
        _("Threat likelihood"), null=True, blank=True
    )
    vulnerability_exposure = models.PositiveIntegerField(
        _("Vulnerability exposure"), null=True, blank=True
    )
    combined_likelihood = models.PositiveIntegerField(
        _("Combined likelihood"), null=True, blank=True
    )
    impact_confidentiality = models.PositiveIntegerField(
        _("Confidentiality impact"), null=True, blank=True
    )
    impact_integrity = models.PositiveIntegerField(
        _("Integrity impact"), null=True, blank=True
    )
    impact_availability = models.PositiveIntegerField(
        _("Availability impact"), null=True, blank=True
    )
    max_impact = models.PositiveIntegerField(
        _("Maximum impact"), null=True, blank=True
    )
    risk_level = models.PositiveIntegerField(
        _("Risk level"), null=True, blank=True
    )
    existing_controls = models.TextField(
        _("Existing controls"), blank=True
    )
    risk = models.ForeignKey(
        "risks.Risk",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="iso27005_sources",
        verbose_name=_("Consolidated risk"),
    )
    description = models.TextField(_("Description"), blank=True)
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
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("ISO 27005 analysis")
        verbose_name_plural = _("ISO 27005 analyses")

    def __str__(self):
        return f"{self.reference} : {self.threat} × {self.vulnerability}"

    def _resolve_scoring_matrix(self):
        """Return the matrix used for scoring: snapshot first, live criteria as fallback."""
        if self.criteria_snapshot and self.criteria_snapshot.get("matrix"):
            return self.criteria_snapshot["matrix"]
        if not self.assessment_id:
            return None
        criteria = getattr(self.assessment, "risk_criteria", None)
        if criteria and criteria.risk_matrix:
            return criteria.risk_matrix
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
        # Calculate combined_likelihood = max(threat_likelihood, vulnerability_exposure)
        values = [
            v for v in [self.threat_likelihood, self.vulnerability_exposure]
            if v is not None
        ]
        self.combined_likelihood = max(values) if values else None

        # Calculate max_impact = max of non-null impact values
        impacts = [
            v for v in [
                self.impact_confidentiality,
                self.impact_integrity,
                self.impact_availability,
            ]
            if v is not None
        ]
        self.max_impact = max(impacts) if impacts else None

        # Freeze the criteria the first time we have enough to score, so later
        # criteria edits don't rewrite historical scores.
        if (
            self.combined_likelihood is not None
            and self.max_impact is not None
            and not self.criteria_snapshot
        ):
            self._capture_criteria_snapshot()

        if self.combined_likelihood is not None and self.max_impact is not None:
            matrix = self._resolve_scoring_matrix()
            if matrix:
                level = matrix.get(f"{self.combined_likelihood},{self.max_impact}")
                if level is not None:
                    self.risk_level = int(level)

        super().save(*args, **kwargs)

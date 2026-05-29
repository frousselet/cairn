from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import ThreatLevelV


class OperationalScenario(BaseModel):
    """EBIOS RM Workshop 4 - Operational scenario.

    Technical decline of a strategic scenario (workshop 3): targets concrete
    support assets and chains MITRE ATT&CK techniques. ANSSI operational
    likelihood follows the V1..V4 scale documented in M4bis spec Annex B
    (Minimal, Significant, Strong, Maximal); the V values are stored as
    integers 1..4 so they feed the assessment risk matrix directly.

    The gravity_level is inherited from the parent strategic scenario by
    default. Any override sets `gravity_inherited = False` and must carry a
    justification (enforced at the form / serializer level).
    """

    REFERENCE_PREFIX = "EOPS"

    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_operational_scenarios",
        verbose_name=_("Assessment"),
    )
    strategic_scenario = models.ForeignKey(
        "risks.StrategicScenario",
        on_delete=models.CASCADE,
        related_name="operational_scenarios",
        verbose_name=_("Parent strategic scenario"),
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    targeted_support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="ebios_operational_scenarios",
        verbose_name=_("Targeted support assets"),
    )
    gravity_level = models.PositiveSmallIntegerField(
        _("Gravity level"),
        null=True,
        blank=True,
        help_text=_("Inherits from the parent strategic scenario by default."),
    )
    gravity_inherited = models.BooleanField(
        _("Gravity inherited from parent"),
        default=True,
        help_text=_("False when the scenario carries its own gravity that overrides the parent."),
    )
    gravity_override_justification = models.TextField(
        _("Gravity override justification"),
        blank=True,
    )
    likelihood_v = models.PositiveSmallIntegerField(
        _("Operational likelihood (V)"),
        choices=ThreatLevelV.choices,
        null=True,
        blank=True,
        help_text=_("ANSSI V1..V4 operational likelihood scale (M4bis Annex B)."),
    )
    likelihood_justification = models.TextField(_("Likelihood justification"), blank=True)
    risk_level = models.PositiveSmallIntegerField(
        _("Risk level"),
        null=True,
        blank=True,
        help_text=_("Computed via the assessment risk matrix from likelihood_v x gravity_level."),
    )
    existing_controls = models.TextField(_("Existing controls"), blank=True)
    existing_measures = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="ebios_operational_scenarios",
        verbose_name=_("Existing compliance measures"),
    )
    consolidated_risk = models.ForeignKey(
        "risks.Risk",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_operational_scenarios",
        verbose_name=_("Consolidated risk"),
    )
    mitre_version = models.CharField(
        _("MITRE version"),
        max_length=16,
        blank=True,
        help_text=_("Version of the MITRE ATT&CK catalogue referenced by attached techniques."),
    )
    criteria_snapshot = models.JSONField(
        _("Criteria snapshot"),
        null=True,
        blank=True,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-risk_level", "-created_at"]
        verbose_name = _("EBIOS RM operational scenario")
        verbose_name_plural = _("EBIOS RM operational scenarios")

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
        # Inherit gravity from the parent strategic scenario when explicitly flagged.
        if self.gravity_inherited and self.strategic_scenario_id:
            parent_gravity = getattr(self.strategic_scenario, "gravity_level", None)
            if parent_gravity is not None:
                self.gravity_level = parent_gravity

        if self.likelihood_v is not None and self.gravity_level is not None:
            if not self.criteria_snapshot:
                self._capture_criteria_snapshot()
            matrix = self._resolve_scoring_matrix()
            if matrix:
                level = matrix.get(f"{self.likelihood_v},{self.gravity_level}")
                if level is not None:
                    self.risk_level = int(level)
        super().save(*args, **kwargs)

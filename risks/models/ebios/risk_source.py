from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import (
    ANSSI_THREAT_LEVEL_GRID,
    RiskSourceCategory,
    ThreatLevelV,
    compute_anssi_threat_level,
)


class RiskSource(BaseModel):
    """EBIOS RM Workshop 2 - Risk source (SR).

    A person, group, organization, state or phenomenon at the origin of risk
    scenarios. The ANSSI v1.5 threat level (V1..V4) is auto-computed at
    save() from (motivation, resources, activity) via the Grid A formula
    documented in M4bis spec §2.8 (Annex A).
    """

    REFERENCE_PREFIX = "ERSC"

    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_risk_sources",
        verbose_name=_("Assessment"),
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    category = models.CharField(
        _("Category"),
        max_length=32,
        choices=RiskSourceCategory.choices,
        default=RiskSourceCategory.OTHER,
    )
    motivation_level = models.PositiveSmallIntegerField(
        _("Motivation level"),
        choices=[(i, str(i)) for i in range(1, 5)],
        null=True,
        blank=True,
        help_text=_("1 (low) .. 4 (very strong). Drives the ANSSI threat level."),
    )
    motivation_description = models.TextField(_("Motivation description"), blank=True)
    resources_level = models.PositiveSmallIntegerField(
        _("Resources level"),
        choices=[(i, str(i)) for i in range(1, 5)],
        null=True,
        blank=True,
        help_text=_("1 (limited) .. 4 (unlimited). Drives the ANSSI threat level."),
    )
    activity_level = models.PositiveSmallIntegerField(
        _("Activity level"),
        choices=[(i, str(i)) for i in range(1, 5)],
        null=True,
        blank=True,
        help_text=_("Observed activity 1..4. Activity >= 3 majorates the threat level by one."),
    )
    threat_level = models.PositiveSmallIntegerField(
        _("Threat level"),
        choices=ThreatLevelV.choices,
        null=True,
        blank=True,
        help_text=_("ANSSI threat level V1..V4 computed from motivation, resources and activity."),
    )
    is_retained = models.BooleanField(_("Retained for analysis"), default=True)
    retention_justification = models.TextField(_("Retention justification"), blank=True)
    is_from_catalog = models.BooleanField(_("From catalog"), default=False)
    criteria_snapshot = models.JSONField(
        _("Criteria snapshot"),
        null=True,
        blank=True,
        help_text=_(
            "Frozen copy of the ANSSI threat level grid used at the time of first "
            "scoring. Keeps the threat_level immutable when the grid is edited."
        ),
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("EBIOS RM risk source")
        verbose_name_plural = _("EBIOS RM risk sources")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def _resolve_threat_grid(self):
        """Return the grid used for scoring: snapshot first, criteria override, ANSSI default."""
        if self.criteria_snapshot and self.criteria_snapshot.get("grid"):
            # Snapshot stores stringified keys ("1,2") for JSON portability.
            return {
                tuple(int(k) for k in key.split(",")): value
                for key, value in self.criteria_snapshot["grid"].items()
            }
        if self.assessment_id:
            criteria = getattr(self.assessment, "risk_criteria", None)
            if criteria and getattr(criteria, "risk_matrix", None):
                custom = criteria.risk_matrix.get("ebios_threat_grid")
                if isinstance(custom, dict):
                    parsed = {}
                    for key, value in custom.items():
                        try:
                            m, r = (int(part) for part in str(key).split(","))
                            parsed[(m, r)] = int(value)
                        except (TypeError, ValueError):
                            continue
                    if parsed:
                        return parsed
        return ANSSI_THREAT_LEVEL_GRID

    def _capture_threat_snapshot(self, grid):
        if self.criteria_snapshot:
            return
        criteria_id = None
        criteria_ref = None
        if self.assessment_id:
            criteria = getattr(self.assessment, "risk_criteria", None)
            if criteria:
                criteria_id = str(criteria.pk)
                criteria_ref = criteria.reference
        self.criteria_snapshot = {
            "criteria_id": criteria_id,
            "criteria_reference": criteria_ref,
            "grid": {f"{m},{r}": v for (m, r), v in grid.items()},
            "captured_at": timezone.now().isoformat(),
        }

    def save(self, *args, **kwargs):
        if self.motivation_level is not None and self.resources_level is not None:
            grid = self._resolve_threat_grid()
            self.threat_level = compute_anssi_threat_level(
                self.motivation_level,
                self.resources_level,
                self.activity_level,
                grid=grid,
            )
            if not self.criteria_snapshot:
                self._capture_threat_snapshot(grid)
        else:
            # Clear an inconsistent threat_level if the user removed a required input
            self.threat_level = None
        super().save(*args, **kwargs)

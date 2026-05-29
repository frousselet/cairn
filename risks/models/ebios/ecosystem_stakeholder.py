from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import (
    DEFAULT_ECOSYSTEM_THRESHOLDS,
    EcosystemStakeholderCategory,
    ThreatZone,
    compute_ecosystem_threat_level,
    compute_ecosystem_threat_zone,
)


# Stored decimal precision for threat_level (formula result is in ]0.0625, 16.0]).
_THREAT_LEVEL_QUANT = Decimal("0.01")


class EcosystemStakeholder(BaseModel):
    """EBIOS RM Workshop 3 - Ecosystem stakeholder.

    Cartographie de la menace numérique. The ANSSI v1.5 raw threat level is
    auto-computed at save() as (dependency * penetration) / (maturity * trust),
    then mapped to a control / monitoring / danger zone according to
    DEFAULT_ECOSYSTEM_THRESHOLDS (overridable per assessment through
    RiskCriteria.risk_matrix["ebios_ecosystem_thresholds"]).

    The model is independent from context.Stakeholder (the ISO 9001/27001
    interested party), with an optional FK for convenience. The ANSSI
    dimensions (dependency, penetration, maturity, trust) do not match the
    ISO ones (influence, interest).
    """

    REFERENCE_PREFIX = "EECS"

    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_ecosystem_stakeholders",
        verbose_name=_("Assessment"),
    )
    stakeholder = models.ForeignKey(
        "context.Stakeholder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_ecosystem_stakeholders",
        verbose_name=_("Linked stakeholder"),
        help_text=_("Optional link to a Module 1 interested party already on file."),
    )
    supplier = models.ForeignKey(
        "assets.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_ecosystem_stakeholders",
        verbose_name=_("Linked supplier"),
        help_text=_("Optional link to a Module 2 supplier already on file."),
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    category = models.CharField(
        _("Category"),
        max_length=32,
        choices=EcosystemStakeholderCategory.choices,
        default=EcosystemStakeholderCategory.OTHER,
    )
    dependency = models.PositiveSmallIntegerField(
        _("Dependency"),
        choices=[(i, str(i)) for i in range(1, 5)],
        null=True,
        blank=True,
        help_text=_("Organisation dependency on the stakeholder (1..4)."),
    )
    penetration = models.PositiveSmallIntegerField(
        _("Penetration"),
        choices=[(i, str(i)) for i in range(1, 5)],
        null=True,
        blank=True,
        help_text=_("Stakeholder penetration into the ecosystem (1..4)."),
    )
    maturity = models.PositiveSmallIntegerField(
        _("Cyber maturity"),
        choices=[(i, str(i)) for i in range(1, 5)],
        null=True,
        blank=True,
        help_text=_("Stakeholder cyber maturity (1..4)."),
    )
    trust = models.PositiveSmallIntegerField(
        _("Trust"),
        choices=[(i, str(i)) for i in range(1, 5)],
        null=True,
        blank=True,
        help_text=_("Trust placed in the stakeholder (1..4)."),
    )
    threat_level = models.DecimalField(
        _("Threat level"),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("(dependency * penetration) / (maturity * trust), computed at save."),
    )
    threat_zone = models.CharField(
        _("Threat zone"),
        max_length=16,
        choices=ThreatZone.choices,
        null=True,
        blank=True,
        help_text=_("ANSSI zone derived from threat_level: control, monitoring or danger."),
    )
    accessible_support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="ebios_ecosystem_stakeholders",
        verbose_name=_("Accessible support assets"),
    )
    is_attack_vector = models.BooleanField(_("Identified as attack vector"), default=False)
    attack_vector_justification = models.TextField(_("Attack vector justification"), blank=True)
    criteria_snapshot = models.JSONField(
        _("Criteria snapshot"),
        null=True,
        blank=True,
        help_text=_(
            "Frozen copy of the ecosystem thresholds used at first scoring so "
            "later edits to the criteria do not silently move stakeholders "
            "between zones."
        ),
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-threat_level", "-created_at"]
        verbose_name = _("EBIOS RM ecosystem stakeholder")
        verbose_name_plural = _("EBIOS RM ecosystem stakeholders")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def _resolve_thresholds(self):
        if self.criteria_snapshot and "thresholds" in self.criteria_snapshot:
            return self.criteria_snapshot["thresholds"]
        if self.assessment_id:
            criteria = getattr(self.assessment, "risk_criteria", None)
            if criteria and getattr(criteria, "risk_matrix", None):
                custom = criteria.risk_matrix.get("ebios_ecosystem_thresholds")
                if (
                    isinstance(custom, dict)
                    and "control" in custom
                    and "monitoring" in custom
                ):
                    try:
                        return {
                            "control": float(custom["control"]),
                            "monitoring": float(custom["monitoring"]),
                        }
                    except (TypeError, ValueError):
                        pass
        return dict(DEFAULT_ECOSYSTEM_THRESHOLDS)

    def _capture_threshold_snapshot(self, thresholds):
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
            "thresholds": dict(thresholds),
            "captured_at": timezone.now().isoformat(),
        }

    def save(self, *args, **kwargs):
        if None not in (self.dependency, self.penetration, self.maturity, self.trust):
            thresholds = self._resolve_thresholds()
            raw = compute_ecosystem_threat_level(
                self.dependency, self.penetration, self.maturity, self.trust,
            )
            if raw is None:
                self.threat_level = None
                self.threat_zone = None
            else:
                self.threat_level = Decimal(str(raw)).quantize(_THREAT_LEVEL_QUANT)
                self.threat_zone = compute_ecosystem_threat_zone(raw, thresholds)
                if not self.criteria_snapshot:
                    self._capture_threshold_snapshot(thresholds)
        else:
            self.threat_level = None
            self.threat_zone = None
        super().save(*args, **kwargs)

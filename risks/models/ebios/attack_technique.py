from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import AttackDifficulty


class AttackTechnique(BaseModel):
    """EBIOS RM Workshop 4 - Attack technique used in an operational scenario.

    Each technique either references the shared MITRE ATT&CK catalogue
    (recommended) or carries a free-form `custom_name`. At least one of the
    two must be provided; the constraint is enforced by `full_clean()`.
    """

    REFERENCE_PREFIX = "EATT"

    scenario = models.ForeignKey(
        "risks.OperationalScenario",
        on_delete=models.CASCADE,
        related_name="attack_techniques",
        verbose_name=_("Operational scenario"),
    )
    order = models.PositiveIntegerField(_("Order"), default=0)
    mitre_technique = models.ForeignKey(
        "risks.MitreAttackTechnique",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usages",
        verbose_name=_("MITRE technique"),
    )
    custom_name = models.CharField(
        _("Custom name"),
        max_length=255,
        blank=True,
        help_text=_("Free-form technique name when no MITRE mapping is available."),
    )
    description = models.TextField(_("Description"))
    targeted_support_asset = models.ForeignKey(
        "assets.SupportAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_attack_techniques",
        verbose_name=_("Targeted support asset"),
    )
    difficulty = models.CharField(
        _("Difficulty"),
        max_length=16,
        choices=AttackDifficulty.choices,
        null=True,
        blank=True,
    )
    detection_difficulty = models.CharField(
        _("Detection difficulty"),
        max_length=16,
        choices=AttackDifficulty.choices,
        null=True,
        blank=True,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["scenario", "order", "-created_at"]
        verbose_name = _("EBIOS RM attack technique")
        verbose_name_plural = _("EBIOS RM attack techniques")
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "order"],
                name="unique_attack_technique_order",
            ),
        ]

    def __str__(self):
        return f"{self.reference} : {self.display_name}"

    @property
    def display_name(self):
        if self.mitre_technique_id:
            return str(self.mitre_technique)
        return self.custom_name or _("Custom technique")

    def clean(self):
        super().clean()
        if not self.mitre_technique_id and not self.custom_name:
            raise ValidationError(
                _("An attack technique must reference either a MITRE technique or a custom name.")
            )

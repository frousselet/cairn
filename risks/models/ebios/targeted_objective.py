from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import TargetedObjectiveCategory


class TargetedObjective(BaseModel):
    """EBIOS RM Workshop 2 - Targeted objective (OV).

    Finality pursued by a risk source (espionage, sabotage, enrichment, ...).
    A risk source may carry several targeted objectives. Each objective may
    target one or more essential assets and feared events.
    """

    REFERENCE_PREFIX = "ETOV"

    risk_source = models.ForeignKey(
        "risks.RiskSource",
        on_delete=models.CASCADE,
        related_name="targeted_objectives",
        verbose_name=_("Risk source"),
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    category = models.CharField(
        _("Category"),
        max_length=32,
        choices=TargetedObjectiveCategory.choices,
        default=TargetedObjectiveCategory.OTHER,
    )
    targeted_essential_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="ebios_targeted_objectives",
        verbose_name=_("Targeted essential assets"),
    )
    targeted_feared_events = models.ManyToManyField(
        "risks.FearedEvent",
        blank=True,
        related_name="ebios_targeted_objectives",
        verbose_name=_("Targeted feared events"),
    )
    is_retained = models.BooleanField(_("Retained for analysis"), default=True)
    order = models.PositiveIntegerField(_("Order"), default=0)
    history = HistoricalRecords()

    class Meta:
        ordering = ["risk_source", "order", "-created_at"]
        verbose_name = _("EBIOS RM targeted objective")
        verbose_name_plural = _("EBIOS RM targeted objectives")

    def __str__(self):
        return f"{self.reference} : {self.name}"

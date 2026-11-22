# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import TargetedObjectiveCategory


class TargetedObjective(BaseModel):
    """EBIOS RM Workshop 2 - Targeted objective (OV).

    Finality pursued by a risk source (espionage, sabotage, enrichment, ...).
    A risk source may carry several targeted objectives. Each objective may
    target one or more essential assets and feared events.
    """

    # Filed under the scopes of its parent : every surface resolves it
    # through core.scoping (lists, records, transitions, history, API, MCP).
    scope_parent_lookup = "risk_source__assessment__scopes"

    REFERENCE_PREFIX = "ETOV"

    risk_source = models.ForeignKey(
        "risks.RiskSource",
        on_delete=models.CASCADE,
        related_name="targeted_objectives",
        # "Source de risque", the attacker of the method : not the "source du
        # risque" of the register, which says where a risk comes from.
        verbose_name=pgettext_lazy("EBIOS RM", "Risk source"),
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

    @property
    def workflow_perm_namespace(self):
        # The permission feature of its rows (workshop 2, risk sources and objectives), as its views ask :
        # the one derived from the model name does not exist, which left the
        # moves of its lifecycle and its history to superusers alone.
        return "risks.ebios_risk_source"

    def __str__(self):
        return f"{self.reference} : {self.name}"

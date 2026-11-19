# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import AttackDifficulty, AttackPathActionType


class AttackPathStep(BaseModel):
    """EBIOS RM Workshop 3 - Attack path step.

    Ordered step inside a strategic scenario. Each step typically involves a
    single ecosystem stakeholder and one action type from a normalized
    vocabulary (initial access, lateral movement, exfiltration, ...).
    """

    # Filed under the scopes of its parent : every surface resolves it
    # through core.scoping (lists, records, transitions, history, API, MCP).
    scope_parent_lookup = "scenario__assessment__scopes"

    REFERENCE_PREFIX = "EAPS"

    scenario = models.ForeignKey(
        "risks.StrategicScenario",
        on_delete=models.CASCADE,
        related_name="attack_path_steps",
        verbose_name=_("Strategic scenario"),
    )
    order = models.PositiveIntegerField(_("Order"), default=0)
    stakeholder = models.ForeignKey(
        "risks.EcosystemStakeholder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attack_path_steps",
        verbose_name=_("Involved stakeholder"),
    )
    description = models.TextField(_("Description"))
    action_type = models.CharField(
        _("Action type"),
        max_length=32,
        choices=AttackPathActionType.choices,
        default=AttackPathActionType.OTHER,
    )
    difficulty = models.CharField(
        _("Difficulty"),
        max_length=16,
        choices=AttackDifficulty.choices,
        null=True,
        blank=True,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["scenario", "order", "-created_at"]
        verbose_name = _("EBIOS RM attack path step")
        verbose_name_plural = _("EBIOS RM attack path steps")
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "order"],
                name="unique_attack_path_step_order",
            ),
        ]

    def __str__(self):
        return f"{self.reference} : step {self.order} of {self.scenario_id}"

    def come_last_when_unranked(self):
        """Give a new step with no rank the one after the last step of its scenario.

        Two steps of one rank in a scenario are refused by the database : a
        surface that lets the rank be left out (the web form, the MCP tools)
        calls this before saving.
        """
        if not self._state.adding or self.order or not self.scenario_id:
            return
        last = type(self).objects.filter(scenario_id=self.scenario_id).aggregate(last=models.Max("order"))["last"]
        self.order = (last or 0) + 1

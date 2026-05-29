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

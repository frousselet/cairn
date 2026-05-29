from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import DICCriterion


class FearedEvent(BaseModel):
    """EBIOS RM Workshop 1 - Feared event.

    Characterizes a DIC impairment on an essential asset with a gravity
    level. At most three feared events per (baseline, essential_asset),
    one per DIC criterion.
    """

    REFERENCE_PREFIX = "EFER"

    baseline = models.ForeignKey(
        "risks.SecurityBaseline",
        on_delete=models.CASCADE,
        related_name="feared_events",
        verbose_name=_("Security baseline"),
    )
    essential_asset = models.ForeignKey(
        "assets.EssentialAsset",
        on_delete=models.PROTECT,
        related_name="feared_events",
        verbose_name=_("Essential asset"),
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    dic_criterion = models.CharField(
        _("DIC criterion"),
        max_length=20,
        choices=DICCriterion.choices,
    )
    gravity_level = models.PositiveIntegerField(_("Gravity level"), null=True, blank=True)
    gravity_justification = models.TextField(_("Gravity justification"), blank=True)
    business_impacts = models.JSONField(
        _("Business impacts"),
        default=dict,
        blank=True,
        help_text=_("Optional dict with keys: financial, legal, reputation, operational, human, environmental."),
    )
    criteria_snapshot = models.JSONField(
        _("Criteria snapshot"),
        null=True,
        blank=True,
        help_text=_("Frozen copy of the impact scale at the time of gravity capture."),
    )
    order = models.PositiveIntegerField(_("Order"), default=0)
    history = HistoricalRecords()

    class Meta:
        ordering = ["baseline", "order", "essential_asset", "dic_criterion"]
        verbose_name = _("EBIOS RM feared event")
        verbose_name_plural = _("EBIOS RM feared events")
        constraints = [
            models.UniqueConstraint(
                fields=["baseline", "essential_asset", "dic_criterion"],
                name="unique_feared_event_per_dic",
            ),
        ]

    def __str__(self):
        return f"{self.reference} : {self.essential_asset} ({self.get_dic_criterion_display()})"

    def _capture_criteria_snapshot(self):
        if self.criteria_snapshot:
            return
        if not self.baseline_id:
            return
        criteria = getattr(self.baseline.assessment, "risk_criteria", None)
        if not criteria:
            return
        self.criteria_snapshot = {
            "criteria_id": str(criteria.pk),
            "criteria_reference": criteria.reference,
            "criteria_name": criteria.name,
            "criteria_version": criteria.version,
            "captured_at": timezone.now().isoformat(),
        }

    def save(self, *args, **kwargs):
        if self.gravity_level is not None and not self.criteria_snapshot:
            self._capture_criteria_snapshot()
        super().save(*args, **kwargs)

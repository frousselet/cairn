from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel, LegacyStatusMixin
from risks.constants import Severity


class BaselineGap(LegacyStatusMixin, BaseModel):
    """EBIOS RM Workshop 1 - Baseline gap.

    Gap observed between the current security state and the applicable
    baseline (ISO 27002, ANSSI guidelines, other frameworks). May reference
    a compliance Requirement for traceability.
    """

    LIFECYCLE_NAME = "ebios_baseline_gap"

    REFERENCE_PREFIX = "EBGP"

    baseline = models.ForeignKey(
        "risks.SecurityBaseline",
        on_delete=models.CASCADE,
        related_name="gaps",
        verbose_name=_("Security baseline"),
    )
    reference_source = models.CharField(_("Reference source"), max_length=255)
    linked_requirement = models.ForeignKey(
        "compliance.Requirement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_baseline_gaps",
        verbose_name=_("Linked requirement"),
    )
    description = models.TextField(_("Description"))
    affected_support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="ebios_baseline_gaps",
        verbose_name=_("Affected support assets"),
    )
    severity = models.CharField(
        _("Severity"),
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    recommended_remediation = models.TextField(_("Recommended remediation"), blank=True)
    order = models.PositiveIntegerField(_("Order"), default=0)
    history = HistoricalRecords()

    class Meta:
        ordering = ["baseline", "order", "-created_at"]
        verbose_name = _("EBIOS RM baseline gap")
        verbose_name_plural = _("EBIOS RM baseline gaps")

    @property
    def workflow_perm_namespace(self):
        return "risks.ebios_baseline"


    def __str__(self):
        return f"{self.reference} : {self.reference_source}"

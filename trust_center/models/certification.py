from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from trust_center.managers import CertificationQuerySet
from trust_center.workflows import PUBLICATION_WORKFLOW_NAME


class TrustCenterCertification(BaseModel):
    """A framework published on the public Trust Center as a certification badge.

    The entry references an internal :class:`compliance.Framework` but carries
    its own public-only label and description, so internal framework fields never
    reach the public surface.
    """

    REFERENCE_PREFIX = "TCCE"
    WORKFLOW_NAME = PUBLICATION_WORKFLOW_NAME

    framework = models.ForeignKey(
        "compliance.Framework",
        on_delete=models.PROTECT,
        related_name="trust_center_entries",
        verbose_name=_("Framework"),
    )
    public_label = models.CharField(_("Public label"), max_length=255)
    public_description = models.TextField(
        _("Public description"), blank=True, default=""
    )
    show_percentage = models.BooleanField(
        _("Show compliance percentage"), default=True
    )
    display_order = models.PositiveIntegerField(_("Display order"), default=0)

    history = HistoricalRecords()

    objects = CertificationQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        verbose_name = _("Trust Center certification")
        verbose_name_plural = _("Trust Center certifications")
        ordering = ["display_order", "public_label"]

    def __str__(self):
        return self.public_label

    @property
    def workflow_perm_namespace(self):
        return "trust_center.certification"

    @property
    def public_compliance_level(self):
        """Rounded integer compliance %, or ``None`` when percentages are hidden.

        Hidden when this entry opts out (``show_percentage``) or the global
        :class:`TrustCenterSettings` toggle is off.
        """
        from trust_center.models.settings import TrustCenterSettings

        if not self.show_percentage:
            return None
        if not TrustCenterSettings.get().show_compliance_percentages:
            return None
        try:
            return round(float(self.framework.compliance_level))
        except (TypeError, ValueError):
            return None

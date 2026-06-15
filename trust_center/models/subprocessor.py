from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from trust_center.managers import SubprocessorQuerySet
from trust_center.workflows import PUBLICATION_WORKFLOW_NAME


class TrustCenterSubprocessor(BaseModel):
    """A supplier published on the public Trust Center as a subprocessor.

    References an internal :class:`assets.Supplier` but exposes only curator
    chosen public fields; internal supplier data (contacts, contracts, notes,
    criticality) never reaches the public surface.
    """

    REFERENCE_PREFIX = "TCSP"
    WORKFLOW_NAME = PUBLICATION_WORKFLOW_NAME

    supplier = models.ForeignKey(
        "assets.Supplier",
        on_delete=models.PROTECT,
        related_name="trust_center_entries",
        verbose_name=_("Supplier"),
    )
    public_name = models.CharField(_("Public name"), max_length=255)
    purpose = models.CharField(_("Purpose"), max_length=255, blank=True, default="")
    public_country = models.CharField(
        _("Country"), max_length=100, blank=True, default=""
    )
    public_website = models.URLField(_("Website"), blank=True, default="")
    display_order = models.PositiveIntegerField(_("Display order"), default=0)

    history = HistoricalRecords()

    objects = SubprocessorQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        verbose_name = _("Trust Center subprocessor")
        verbose_name_plural = _("Trust Center subprocessors")
        ordering = ["display_order", "public_name"]

    def __str__(self):
        return self.public_name

    @property
    def workflow_perm_namespace(self):
        return "trust_center.subprocessor"

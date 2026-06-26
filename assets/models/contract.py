import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import ContractStatus


class Contract(models.Model):
    """A contract, as an autonomous, potentially multi-party entity.

    A contract is not necessarily between only two parties : it links one or
    more parties. This v1 models the supplier parties (``suppliers`` M2M); the
    organisation and other stakeholders as parties, plus the documentary
    "contrathèque", come with the dedicated contract module. ``parent`` lets a
    contract carry amendments (avenants) as child contracts.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(_("Title"), max_length=255, blank=True, default="")
    reference = models.CharField(_("Reference"), max_length=255, blank=True, default="")
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ContractStatus.choices,
        default=ContractStatus.ACTIVE,
    )
    start_date = models.DateField(_("Start date"), null=True, blank=True)
    end_date = models.DateField(_("End date"), null=True, blank=True)
    amount = models.DecimalField(
        _("Amount"), max_digits=14, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(_("Currency"), max_length=3, blank=True, default="")
    notes = models.TextField(_("Notes"), blank=True, default="")

    # Amendments (avenants) attach to their parent contract.
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="amendments",
        verbose_name=_("Amends contract"),
    )

    # Parties (v1 : suppliers ; organisation + stakeholders added with the
    # dedicated contract module).
    suppliers = models.ManyToManyField(
        "assets.Supplier",
        blank=True,
        related_name="contracts",
        verbose_name=_("Suppliers"),
    )

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords(m2m_fields=[suppliers])

    class Meta:
        ordering = ["-start_date", "-created_at"]
        verbose_name = _("Contract")
        verbose_name_plural = _("Contracts")

    def __str__(self):
        return self.label or self.reference or str(self.id)

    @property
    def is_amendment(self):
        return self.parent_id is not None

    @property
    def is_expired(self):
        from django.utils import timezone

        if self.end_date and self.status == ContractStatus.ACTIVE:
            return self.end_date <= timezone.now().date()
        return False

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import ContractStatus
from context.models.base import ScopedModel


class Contract(ScopedModel):
    """A contract: an autonomous, potentially multi-party document.

    A contract is not necessarily between only two parties : it links one or
    more parties. Parties are modelled as the union of supplier parties
    (``suppliers`` M2M) and client parties (``clients`` M2M to customer
    stakeholders). ``parent`` lets a contract carry amendments (avenants) as
    child contracts. A single PDF document is stored inline (``file_content``);
    automatic content extraction via Ask Cairn will build on it later.
    """

    REFERENCE_PREFIX = "CTRT"
    WORKFLOW_NAME = "contract"

    label = models.CharField(_("Title"), max_length=255, blank=True, default="")
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ContractStatus.choices,
        default=ContractStatus.DRAFT,
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

    # "Cancels and replaces" : this contract (or amendment) supersedes a
    # previous one. The superseded contract stays for traceability.
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by",
        verbose_name=_("Cancels and replaces"),
    )

    # Parties : supplier parties and client (customer stakeholder) parties.
    suppliers = models.ManyToManyField(
        "assets.Supplier",
        blank=True,
        related_name="contracts",
        verbose_name=_("Suppliers"),
    )
    clients = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="contracts",
        verbose_name=_("Clients"),
    )

    # Attached document (PDF only, stored inline like trust-center documents).
    file_content = models.BinaryField(
        _("File content"), null=True, blank=True, editable=False
    )
    file_name = models.CharField(_("File name"), max_length=255, blank=True, default="")
    content_type = models.CharField(
        _("Content type"), max_length=100, blank=True, default=""
    )

    history = HistoricalRecords(
        m2m_fields=[suppliers, clients], excluded_fields=["file_content"]
    )

    class Meta(ScopedModel.Meta):
        ordering = ["-start_date", "-created_at"]
        verbose_name = _("Contract")
        verbose_name_plural = _("Contracts")

    def __str__(self):
        return self.label or self.reference or str(self.id)

    @property
    def workflow_perm_namespace(self):
        return "assets.contract"

    def save(self, *args, **kwargs):
        from core.workflow import sync_legacy_status

        sync_legacy_status(self, kwargs, ContractStatus.DRAFT)
        super().save(*args, **kwargs)

    @property
    def is_amendment(self):
        return self.parent_id is not None

    @property
    def is_superseded(self):
        """Whether this contract has been cancelled and replaced by another."""
        return self.superseded_by.exists()

    @property
    def is_expired(self):
        from django.utils import timezone

        if self.end_date and self.status == ContractStatus.ACTIVE:
            return self.end_date <= timezone.now().date()
        return False

    @property
    def has_document(self):
        return bool(self.file_content)

    def get_file_bytes(self):
        """Return the attached PDF bytes, or ``None`` when no document is stored."""
        return bytes(self.file_content) if self.file_content else None

    @property
    def supplier_names(self):
        """Display names of supplier parties (read-only API / assistant output)."""
        return [s.name for s in self.suppliers.all()]

    @property
    def client_names(self):
        """Display names of client parties (read-only API / assistant output)."""
        return [c.name for c in self.clients.all()]

    def extract_document_text(self):
        """Placeholder for automatic PDF content extraction via Ask Cairn.

        Intentionally not implemented yet : the dedicated extraction pipeline
        (text + structured terms) will populate future fields from
        ``get_file_bytes()``. Left as a clean seam so callers can be wired later.
        """
        raise NotImplementedError(
            "Automatic contract content extraction is not implemented yet."
        )

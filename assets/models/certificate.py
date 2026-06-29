from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import CertificateStatus
from context.models.base import ScopedModel


class Certificate(ScopedModel):
    """A company certificate stored and historised against a framework.

    A certificate attests that the company (or a defined perimeter of it) is
    certified against a compliance framework (référentiel), e.g. ISO/IEC 27001,
    HDS or SOC 2. The ``framework`` foreign key points to that référentiel,
    which carries the standard name, version and issuing body. The attested
    perimeter is described in ``scope_statement`` and may be linked to the
    covered ``sites``. A single PDF document is stored inline
    (``file_content``). Renewals are tracked with ``supersedes``: a new
    certificate "cancels and replaces" the previous one, which stays for
    traceability, so the full certification history is kept over time.
    Field-level changes are tracked through ``django-simple-history``.
    """

    REFERENCE_PREFIX = "CERT"
    LIFECYCLE_NAME = "certificate"

    label = models.CharField(_("Title"), max_length=255, blank=True, default="")
    # The framework (référentiel) this certificate attests compliance to. PROTECT
    # keeps a référentiel that still has certificates from being deleted; the form
    # / API / MCP layers enforce that a certificate always names one.
    framework = models.ForeignKey(
        "compliance.Framework",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="certificates",
        verbose_name=_("Framework"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=CertificateStatus.choices,
        default=CertificateStatus.DRAFT,
    )
    certificate_number = models.CharField(
        _("Certificate number"), max_length=120, blank=True, default=""
    )
    issuer = models.CharField(
        _("Certification body"), max_length=255, blank=True, default=""
    )
    issue_date = models.DateField(_("Issue date"), null=True, blank=True)
    expiry_date = models.DateField(_("Expiry date"), null=True, blank=True)
    scope_statement = models.TextField(
        _("Certified scope"), blank=True, default=""
    )
    notes = models.TextField(_("Notes"), blank=True, default="")

    # Renewal chain: this certificate "cancels and replaces" a previous one.
    # The superseded certificate stays for traceability.
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by",
        verbose_name=_("Renews / replaces"),
    )

    # Sites covered by the certified perimeter.
    sites = models.ManyToManyField(
        "context.Site",
        blank=True,
        related_name="certificates",
        verbose_name=_("Covered sites"),
    )

    # Attached document (PDF only, stored inline like contract documents).
    file_content = models.BinaryField(
        _("File content"), null=True, blank=True, editable=False
    )
    file_name = models.CharField(_("File name"), max_length=255, blank=True, default="")
    content_type = models.CharField(
        _("Content type"), max_length=100, blank=True, default=""
    )

    history = HistoricalRecords(m2m_fields=[sites], excluded_fields=["file_content"])

    class Meta(ScopedModel.Meta):
        ordering = ["-issue_date", "-created_at"]
        verbose_name = _("Certificate")
        verbose_name_plural = _("Certificates")

    def __str__(self):
        return self.label or self.reference or str(self.id)

    def save(self, *args, **kwargs):
        from core.workflow import sync_legacy_status

        # The lifecycle step codes are the CertificateStatus values, so keep the
        # legacy ``status`` field coherent with ``workflow_state``.
        sync_legacy_status(self, kwargs, CertificateStatus.DRAFT)
        super().save(*args, **kwargs)

    @property
    def framework_label(self):
        """Compact label of the certified framework (référentiel)."""
        if not self.framework_id:
            return ""
        return self.framework.short_name or self.framework.name

    @property
    def is_superseded(self):
        """Whether this certificate has been renewed / replaced by another."""
        return self.superseded_by.exists()

    @property
    def is_expired(self):
        from django.utils import timezone

        if self.expiry_date and self.status in (
            CertificateStatus.VALID,
            CertificateStatus.UNDER_RENEWAL,
        ):
            return self.expiry_date <= timezone.now().date()
        return False

    @property
    def has_document(self):
        return bool(self.file_content)

    def get_file_bytes(self):
        """Return the attached PDF bytes, or ``None`` when no document is stored."""
        return bytes(self.file_content) if self.file_content else None

    @property
    def site_names(self):
        """Display names of covered sites (read-only API / assistant output)."""
        return [s.name for s in self.sites.all()]

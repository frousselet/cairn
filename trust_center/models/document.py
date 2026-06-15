from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from trust_center.constants import DEFAULT_FILE_ICON, FILE_TYPE_ICONS, DocumentAccess
from trust_center.managers import DocumentQuerySet
from trust_center.workflows import PUBLICATION_WORKFLOW_NAME


class TrustCenterDocument(BaseModel):
    """A document published on the public Trust Center.

    The source is exactly one of a generated :class:`reports.Report` or an
    inline uploaded file (stored as bytes, mirroring the Report storage so the
    same streaming download view serves both). ``access`` decides whether the
    document downloads directly (PUBLIC) or behind a request + approval (GATED).
    """

    REFERENCE_PREFIX = "TCDO"
    WORKFLOW_NAME = PUBLICATION_WORKFLOW_NAME

    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    access = models.CharField(
        _("Access"),
        max_length=10,
        choices=DocumentAccess.choices,
        default=DocumentAccess.PUBLIC,
    )
    requires_nda = models.BooleanField(
        _("Requires NDA"),
        default=True,
        help_text=_("Only applies to gated documents."),
    )
    # Source: exactly one of a linked report or inline content (enforced in clean()).
    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.PROTECT,
        related_name="trust_center_documents",
        null=True,
        blank=True,
        verbose_name=_("Source report"),
    )
    file_content = models.BinaryField(
        _("File content"), null=True, blank=True, editable=False
    )
    file_name = models.CharField(
        _("File name"), max_length=255, blank=True, default=""
    )
    content_type = models.CharField(
        _("Content type"), max_length=100, blank=True, default=""
    )
    display_order = models.PositiveIntegerField(_("Display order"), default=0)

    history = HistoricalRecords(excluded_fields=["file_content"])

    objects = DocumentQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        verbose_name = _("Trust Center document")
        verbose_name_plural = _("Trust Center documents")
        ordering = ["display_order", "title"]

    def __str__(self):
        return self.title

    @property
    def workflow_perm_namespace(self):
        return "trust_center.document"

    def clean(self):
        super().clean()
        has_report = self.report_id is not None
        has_inline = bool(self.file_content)
        if has_report and has_inline:
            raise ValidationError(
                _("Provide either a source report or an uploaded file, not both.")
            )
        if not has_report and not has_inline:
            raise ValidationError(_("Provide a source report or upload a file."))

    @property
    def is_gated(self):
        return self.access == DocumentAccess.GATED

    @property
    def effective_file_name(self):
        if self.report_id:
            return self.report.file_name
        return self.file_name

    @property
    def file_extension(self):
        name = self.effective_file_name or ""
        return name.rsplit(".", 1)[-1].lower() if "." in name else ""

    @property
    def file_icon(self):
        """Bootstrap Icons name reflecting the document's file type."""
        return FILE_TYPE_ICONS.get(self.file_extension, DEFAULT_FILE_ICON)

    def get_file_bytes(self):
        """Return the document bytes from the linked report or inline content."""
        if self.report_id and self.report.file_content:
            return bytes(self.report.file_content)
        if self.file_content:
            return bytes(self.file_content)
        return None

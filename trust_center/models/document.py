# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from trust_center.constants import DEFAULT_FILE_ICON, FILE_TYPE_ICONS, DocumentAccess
from trust_center.managers import DocumentQuerySet
from trust_center.lifecycles import PUBLICATION_LIFECYCLE_NAME as PUBLICATION_WORKFLOW_NAME


class TrustCenterDocument(BaseModel):
    """A document published on the public Trust Center.

    The source is exactly one of a generated :class:`reports.Report`, an
    inline uploaded file (stored as bytes, mirroring the Report storage so the
    same streaming download view serves both) or a governed
    :class:`documents.Policy`, which always serves its version in force
    (RG-DOC-21). ``access`` decides whether the document downloads directly
    (PUBLIC) or behind a request + approval (GATED).
    """

    REFERENCE_PREFIX = "TCDO"
    LIFECYCLE_NAME = PUBLICATION_WORKFLOW_NAME

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
    # Source: exactly one of a linked report, inline content or a governed
    # document (enforced in clean(), RG-TC-18).
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
    policy = models.ForeignKey(
        "documents.Policy",
        on_delete=models.PROTECT,
        related_name="trust_center_documents",
        null=True,
        blank=True,
        verbose_name=_("Source document"),
        help_text=_("A public document of the register : its version in force is served."),
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
        sources = [
            self.report_id is not None,
            bool(self.file_content),
            self.policy_id is not None,
        ]
        if sum(sources) > 1:
            raise ValidationError(
                _("Choose a single source : a report, an uploaded file or a document.")
            )
        if not any(sources):
            raise ValidationError(
                _("Provide a source : a report, an uploaded file or a document.")
            )
        if self.policy_id is not None:
            self._clean_policy_source()

    def _clean_policy_source(self):
        """RG-DOC-20 / RG-DOC-21 : only a public document, and a new link only
        to a linkable one (an existing link survives the document leaving it)."""
        from assets.constants import DataClassification
        from core.lifecycle import linkable_states

        policy = self.policy
        if policy.classification != DataClassification.PUBLIC:
            raise ValidationError(
                {"policy": _("Only a document classified as public can be published on the Trust Center.")}
            )
        stored = None
        if self.pk:
            stored = type(self).objects.filter(pk=self.pk).values_list("policy_id", flat=True).first()
        if stored != policy.pk and policy.workflow_state not in linkable_states(type(policy)):
            raise ValidationError(
                {"policy": _("This document cannot be linked in its current lifecycle step.")}
            )

    @property
    def is_gated(self):
        return self.access == DocumentAccess.GATED

    @property
    def policy_version(self):
        """The version in force of the source document, or ``None``."""
        if not self.policy_id:
            return None
        return self.policy.version_in_force

    @property
    def effective_file_name(self):
        if self.report_id:
            return self.report.file_name
        if self.policy_id:
            version = self.policy_version
            if version is None:
                return ""
            if version.file_name:
                return version.file_name
            return f"{self.policy.reference}-v{version.version_label}.pdf"
        return self.file_name

    @property
    def effective_content_type(self):
        """The download ``Content-Type`` : a policy always serves a PDF."""
        if self.policy_id:
            return "application/pdf"
        return self.content_type or "application/octet-stream"

    @property
    def file_extension(self):
        name = self.effective_file_name or ""
        return name.rsplit(".", 1)[-1].lower() if "." in name else ""

    @property
    def file_icon(self):
        """Bootstrap Icons name reflecting the document's file type."""
        return FILE_TYPE_ICONS.get(self.file_extension, DEFAULT_FILE_ICON)

    def get_file_bytes(self):
        """Return the document bytes from the linked report, the source
        document's version in force (RG-DOC-21) or the inline content."""
        if self.report_id and self.report.file_content:
            return bytes(self.report.file_content)
        if self.policy_id:
            version = self.policy_version
            return version.render_pdf() if version is not None else None
        if self.file_content:
            return bytes(self.file_content)
        return None

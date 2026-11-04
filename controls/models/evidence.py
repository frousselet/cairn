# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A file attached to a test run as evidence : a write-once record once the
run has left ``draft`` (RG-CTL-13). Not a governed domain element : no
lifecycle, no reference. See docs/specs/m8-controls/control-test-evidence.md.
"""

import hashlib
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from controls.constants import ALLOWED_EVIDENCE_EXTENSIONS, EVIDENCE_MAX_BYTES, RUN_DRAFT


def validate_evidence_size(value):
    if value and value.size and value.size > EVIDENCE_MAX_BYTES:
        raise ValidationError(_("An evidence file must not exceed 25 MB."))


def _evidence_upload_path(instance, filename):
    """``control_evidence/<run id>/<row id>/<filename>`` : never collides, never
    exposes another run's identifiers."""
    return f"control_evidence/{instance.run_id}/{instance.pk}/{filename}"


class ControlTestEvidence(models.Model):
    scope_parent_lookup = "run__test__control__scopes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        "controls.ControlTestRun", on_delete=models.PROTECT, related_name="evidence", verbose_name=_("Test run"),
    )
    file = models.FileField(
        _("File"), upload_to=_evidence_upload_path, max_length=400,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_EVIDENCE_EXTENSIONS), validate_evidence_size],
    )
    original_filename = models.CharField(_("File name"), max_length=255, blank=True, default="")
    size = models.PositiveBigIntegerField(_("Size (bytes)"), default=0, editable=False)
    sha256 = models.CharField(_("SHA-256"), max_length=64, blank=True, default="", editable=False)
    description = models.CharField(_("Description"), max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="uploaded_control_evidence", verbose_name=_("Uploaded by"),
    )
    uploaded_at = models.DateTimeField(_("Uploaded at"), auto_now_add=True)
    history = HistoricalRecords(excluded_fields=["file"])

    class Meta:
        ordering = ["run", "uploaded_at"]
        verbose_name = _("Test evidence")
        verbose_name_plural = _("Test evidence")

    def __str__(self):
        return self.original_filename or str(self.pk)

    def _check_run_open(self):
        from controls.models.control_test_run import ControlTestRun

        state = ControlTestRun.objects.filter(pk=self.run_id).values_list("workflow_state", flat=True).first()
        if state != RUN_DRAFT:
            raise ValidationError(_("Evidence can only be added or removed while the test run is in progress."))

    def save(self, *args, **kwargs):
        # RG-CTL-13 : write-once after submission; the file never changes.
        if not self._state.adding:
            raise ValidationError(_("An evidence file cannot be changed : remove it and upload a new one."))
        self._check_run_open()
        if self.file:
            digest = hashlib.sha256()
            for chunk in self.file.chunks():
                digest.update(chunk)
            self.sha256 = digest.hexdigest()
            self.size = self.file.size or 0
            if not self.original_filename:
                self.original_filename = self.file.name.rsplit("/", 1)[-1][:255]
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._check_run_open()
        storage, name = self.file.storage, self.file.name
        result = super().delete(*args, **kwargs)
        if name:
            storage.delete(name)
        return result

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""One version of a governing document (ISO/IEC 27001:2022 clause 7.5.2 / 7.5.3).

Frozen once submitted (RG-DOC-02); at most one version of a document is in
force (RG-DOC-01), enforced by a partial unique constraint and by the
transition, which supersedes the previous version in the same transaction.
See docs/specs/m7-documents/policy-version.md.
"""

import hashlib
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from documents.constants import (
    CAMPAIGN_CLOSED,
    CAMPAIGN_RUNNING,
    PDF_MAX_BYTES,
    POLICY_ACTIVE,
    POLICY_DRAFT,
    REFERENCE_PREFIXES,
    VERSION_DRAFT,
    VERSION_IN_FORCE,
    VERSION_IN_REVIEW,
    VERSION_SUPERSEDED,
)

FROZEN_FIELDS = ("content", "file_content", "file_name", "file_sha256", "version_label", "change_summary")

_LABEL = re.compile(r"^(\d+)(?:\.(\d+))?")


def next_version_label(current, bump="minor"):
    """RG-DOC-05 : ``1.2`` -> ``1.3`` (minor) or ``2.0`` (major); no current -> ``1.0``."""
    if not current:
        return "1.0"
    match = _LABEL.match(current)
    if not match:
        return "1.0"
    major, minor = int(match.group(1)), int(match.group(2) or 0)
    return f"{major + 1}.0" if bump == "major" else f"{major}.{minor + 1}"


def validate_pdf(data, name):
    """RG-DOC-04 (= RG-CTR-02) : extension, magic bytes, size."""
    if not (name or "").lower().endswith(".pdf"):
        raise ValidationError(_("The document must be a PDF file."))
    if not data.startswith(b"%PDF-"):
        raise ValidationError(_("The file is not a valid PDF."))
    if len(data) > PDF_MAX_BYTES:
        raise ValidationError(_("The PDF must not exceed 25 MB."))


class PolicyVersion(BaseModel):
    """A version of a :class:`~documents.models.policy.Policy`."""

    REFERENCE_PREFIX = REFERENCE_PREFIXES["PolicyVersion"]
    LIFECYCLE_NAME = "policy_version"
    scope_parent_lookup = "policy__scopes"

    policy = models.ForeignKey(
        "documents.Policy", on_delete=models.CASCADE, related_name="versions", verbose_name=_("Document"),
    )
    version_label = models.CharField(_("Version label"), max_length=20)
    content = models.TextField(_("Content"), blank=True, default="")
    file_content = models.BinaryField(_("PDF"), null=True, blank=True, editable=False)
    file_name = models.CharField(_("File name"), max_length=255, blank=True, default="")
    file_sha256 = models.CharField(_("SHA-256"), max_length=64, blank=True, default="", editable=False)
    change_summary = models.TextField(_("Change summary"), blank=True, default="")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_policy_versions", verbose_name=_("Approved by"), editable=False,
    )
    approved_at = models.DateTimeField(_("Approved at"), null=True, blank=True, editable=False)
    effective_from = models.DateField(_("Effective from"), null=True, blank=True)
    superseded_at = models.DateTimeField(_("Superseded at"), null=True, blank=True, editable=False)
    superseded_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="supersedes", verbose_name=_("Superseded by"), editable=False,
    )
    history = HistoricalRecords(excluded_fields=["file_content"])

    class Meta(BaseModel.Meta):
        ordering = ["policy", "-created_at"]
        verbose_name = _("Document version")
        verbose_name_plural = _("Document versions")
        constraints = [
            models.UniqueConstraint(fields=["policy", "version_label"], name="unique_policy_version_label"),
            # RG-DOC-01 at the database level.
            models.UniqueConstraint(
                fields=["policy"], condition=Q(workflow_state=VERSION_IN_FORCE),
                name="one_version_in_force_per_policy",
            ),
        ]

    def __str__(self):
        return f"{self.policy.reference} v{self.version_label}"

    @property
    def workflow_perm_namespace(self):
        return "documents.policy"

    # --- Content ----------------------------------------------------------

    @property
    def has_pdf(self):
        return bool(self.file_content)

    def get_file_bytes(self):
        return bytes(self.file_content) if self.file_content else None

    def set_pdf(self, data, name):
        validate_pdf(data, name)
        self.file_content = data
        self.file_name = name
        self.file_sha256 = hashlib.sha256(data).hexdigest()

    def clear_pdf(self):
        self.file_content = None
        self.file_name = ""
        self.file_sha256 = ""

    @property
    def is_frozen(self):
        return self.workflow_state != VERSION_DRAFT

    @property
    def is_first_version(self):
        others = type(self).objects.filter(policy_id=self.policy_id).exclude(pk=self.pk)
        return not others.exclude(workflow_state=VERSION_DRAFT).exists()

    def render_pdf(self):
        """The attached PDF, else the rich text rendered to PDF (WeasyPrint)."""
        if self.file_content:
            return bytes(self.file_content)
        from documents.rendering import render_version_pdf

        return render_version_pdf(self)

    # --- Integrity (RG-DOC-02, RG-DOC-07) ---------------------------------

    def clean(self):
        super().clean()
        if self.effective_from and self.effective_from > timezone.localdate():
            raise ValidationError({"effective_from": _("The effective date cannot be in the future.")})
        if self.pk and self.policy_id:
            clash = type(self).objects.filter(policy_id=self.policy_id, version_label=self.version_label).exclude(pk=self.pk)
            if clash.exists():
                raise ValidationError({"version_label": _("This document already has a version with this label.")})

    def save(self, *args, **kwargs):
        from trust_center.sanitizers import clean_html

        if self.pk and not self._state.adding:
            stored = type(self).objects.filter(pk=self.pk).values("workflow_state", *FROZEN_FIELDS).first()
            if stored and stored["workflow_state"] != VERSION_DRAFT:
                changed = [
                    f for f in FROZEN_FIELDS
                    if (bytes(stored[f]) if f == "file_content" and stored[f] is not None else stored[f])
                    != (bytes(getattr(self, f)) if f == "file_content" and getattr(self, f) is not None else getattr(self, f))
                ]
                if changed:
                    raise ValidationError(_("A submitted version is frozen : its content can no longer be changed."))
            if stored and stored["workflow_state"] in (VERSION_IN_FORCE, VERSION_SUPERSEDED):
                effective = type(self).objects.filter(pk=self.pk).values_list("effective_from", flat=True).first()
                if effective != self.effective_from:
                    raise ValidationError(_("The effective date of an approved version cannot be changed."))
        if self.workflow_state in (VERSION_DRAFT, "", None):
            self.content = clean_html(self.content or "")
        super().save(*args, **kwargs)

    # --- Lifecycle side effects (RG-DOC-01, -03, -06, -07, -18) -----------

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True, superseded_by=None):
        from core.lifecycle import DomainRefusalError, validate_transition
        from documents.models.policy import Policy

        lifecycle = self.get_lifecycle()
        current = self.workflow_state or lifecycle.initial_step.code
        validate_transition(lifecycle, current, target, instance=self, user=user, comment=comment, enforce_permission=False)
        with transaction.atomic():
            policy = Policy.objects.select_for_update().get(pk=self.policy_id)
            if target == VERSION_IN_REVIEW:
                if not (self.content or "").strip() and not self.file_content:
                    raise DomainRefusalError(_("A version needs a content : write the text or attach a PDF."))
                if not self.is_first_version and not (self.change_summary or "").strip():
                    raise DomainRefusalError(_("Describe what changed since the previous version before submitting."))

            if target == VERSION_IN_FORCE:
                if policy.workflow_state not in (POLICY_DRAFT, POLICY_ACTIVE):
                    raise DomainRefusalError(_("A retired document cannot have a version put in force."))
                if self.effective_from and self.effective_from > timezone.localdate():
                    raise DomainRefusalError(_("The effective date cannot be in the future."))
                previous = policy.versions.filter(workflow_state=VERSION_IN_FORCE).exclude(pk=self.pk).first()
                if previous is not None:
                    # RG-DOC-01 : the previous version leaves `in_force` first, through
                    # its own recorded transition, so the partial unique constraint
                    # holds at every statement of the transaction.
                    previous.transition_to(
                        VERSION_SUPERSEDED, user,
                        comment=str(_("Superseded by %(ref)s")) % {"ref": self.reference},
                        enforce_permission=False, superseded_by=self,
                    )
                self.approved_by = user
                self.approved_at = timezone.now()
                if self.effective_from is None:
                    self.effective_from = timezone.localdate()

            result = super().transition_to(target, user, comment=comment, enforce_permission=enforce_permission, save=save)

            if target == VERSION_IN_REVIEW and user is not None:
                from accounts.notifications import notify_lifecycle_submitted

                notify_lifecycle_submitted(policy, actor=user)
            if target == VERSION_IN_FORCE:
                from documents.notifications import notify_version_in_force

                notify_version_in_force(self, actor=user)
                type(self).objects.filter(pk=self.pk).update(
                    approved_by=self.approved_by, approved_at=self.approved_at, effective_from=self.effective_from,
                )
                if policy.workflow_state == POLICY_DRAFT:
                    policy.transition_to(POLICY_ACTIVE, user, enforce_permission=False)
                policy.last_reviewed_at = self.approved_at
                policy.last_reviewed_by = user
                policy.save()
            elif target == VERSION_SUPERSEDED:
                self.superseded_at = timezone.now()
                self.superseded_by = superseded_by
                type(self).objects.filter(pk=self.pk).update(
                    superseded_at=self.superseded_at, superseded_by=superseded_by,
                )
                self.close_campaigns(user)
                policy.refresh_review_date()
        return result

    def close_campaigns(self, user):
        """RG-DOC-18 : a superseded version's running campaigns close."""
        for campaign in self.campaigns.filter(workflow_state=CAMPAIGN_RUNNING):
            campaign.transition_to(
                CAMPAIGN_CLOSED, user,
                comment=str(_("Version %(ref)s superseded")) % {"ref": self.reference},
                enforce_permission=False,
            )

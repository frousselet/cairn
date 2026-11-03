# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A governing document of the ISMS (ISO/IEC 27001:2022 clause 5.2, 7.5, A.5.1).

The row is the document's identity; its content lives in its versions, of
which at most one is in force (RG-DOC-01). See docs/specs/m7-documents/policy.md.
"""

import calendar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import DataClassification
from context.models.base import ScopedModel
from documents.constants import (
    CAMPAIGN_RUNNING,
    DEFAULT_REVIEW_FREQUENCY_MONTHS,
    POLICY_ACTIVE,
    POLICY_DRAFT,
    POLICY_RETIRED,
    REFERENCE_PREFIXES,
    VERSION_IN_FORCE,
    VERSION_SUPERSEDED,
    DocumentType,
)


def add_months(day, months):
    """``day`` plus ``months`` calendar months, clamped to the month's last day."""
    total = day.month - 1 + months
    year, month = day.year + total // 12, total % 12 + 1
    return day.replace(year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1]))


class Policy(ScopedModel):
    """A policy, procedure, standard, guideline, charter or plan of record."""

    REFERENCE_PREFIX = REFERENCE_PREFIXES["Policy"]
    LIFECYCLE_NAME = "policy"

    title = models.CharField(_("Title"), max_length=255)
    document_type = models.CharField(
        _("Document type"), max_length=20, choices=DocumentType.choices, default=DocumentType.POLICY,
    )
    summary = models.TextField(_("Summary"), blank=True, default="")
    classification = models.CharField(
        _("Classification"), max_length=20, choices=DataClassification.choices,
        default=DataClassification.INTERNAL,
    )
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="children", verbose_name=_("Parent document"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="owned_policies", verbose_name=_("Owner"),
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approver_of_policies", verbose_name=_("Approver"),
    )
    review_frequency_months = models.PositiveSmallIntegerField(
        _("Review frequency (months)"), default=DEFAULT_REVIEW_FREQUENCY_MONTHS,
        validators=[MinValueValidator(1), MaxValueValidator(60)],
    )
    next_review_override = models.DateField(_("Next review (explicit date)"), null=True, blank=True)
    # Derived (RG-DOC-11), stored for the calendar, the dashboard and filters.
    next_review_date = models.DateField(_("Next review"), null=True, blank=True, db_index=True, editable=False)
    last_reviewed_at = models.DateTimeField(_("Last reviewed at"), null=True, blank=True, editable=False)
    last_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_policies", verbose_name=_("Last reviewed by"), editable=False,
    )
    linked_requirements = models.ManyToManyField(
        "compliance.Requirement", blank=True, related_name="linked_policies",
        verbose_name=_("Linked requirements"),
    )
    applies_to_roles = models.ManyToManyField(
        "context.Role", blank=True, related_name="applicable_policies",
        verbose_name=_("Addressed to roles"),
    )
    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        ordering = ["reference"]
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")

    def __str__(self):
        return f"{self.reference} : {self.title}"

    @property
    def workflow_perm_namespace(self):
        return "documents.policy"

    # --- Versions ---------------------------------------------------------

    @property
    def version_in_force(self):
        return self.versions.filter(workflow_state=VERSION_IN_FORCE).first()

    @property
    def latest_version(self):
        return self.versions.order_by("-created_at").first()

    # --- Review cycle (RG-DOC-11 to RG-DOC-13) ----------------------------

    def compute_next_review_date(self):
        """The explicit date if set, else the version in force's effective date
        (or the last review, whichever is later) plus the review frequency."""
        if self.next_review_override:
            return self.next_review_override
        if not self.pk:
            return None
        current = self.version_in_force
        if current is None or current.effective_from is None:
            return None
        start = current.effective_from
        if self.last_reviewed_at and self.last_reviewed_at.date() > start:
            start = self.last_reviewed_at.date()
        return add_months(start, self.review_frequency_months)

    @property
    def is_review_overdue(self):
        return (
            self.workflow_state == POLICY_ACTIVE
            and self.next_review_date is not None
            and self.next_review_date < timezone.localdate()
        )

    def refresh_review_date(self, save=True):
        self.next_review_date = self.compute_next_review_date()
        if save:
            type(self).objects.filter(pk=self.pk).update(next_review_date=self.next_review_date)

    def record_review(self, user, comment=""):
        """RG-DOC-13 : reviewed, no change. Closes a review cycle without a new version."""
        if self.workflow_state != POLICY_ACTIVE:
            from core.lifecycle import DomainRefusalError

            raise DomainRefusalError(_("Only an active document can be recorded as reviewed."))
        self.last_reviewed_at = timezone.now()
        self.last_reviewed_by = user
        self._change_reason = comment or str(_("Reviewed, no change"))
        self.save()

    def new_version(self, user, bump="minor"):
        """RG-DOC-05 : draft the next version from the one in force."""
        from documents.models.policy_version import PolicyVersion, next_version_label

        source = self.version_in_force or self.latest_version
        label = next_version_label(source.version_label if source else None, bump)
        while self.versions.filter(version_label=label).exists():
            label = next_version_label(label, "minor")
        version = PolicyVersion(
            policy=self,
            version_label=label,
            content=source.content if source else "",
            created_by=user,
        )
        if source is not None and source.file_content:
            version.file_content = bytes(source.file_content)
            version.file_name = source.file_name
            version.file_sha256 = source.file_sha256
        version.save()
        return version

    # --- Structure (RG-DOC-10) --------------------------------------------

    def ancestors(self):
        chain, node, seen = [], self.parent, set()
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            chain.append(node)
            node = node.parent
        return chain

    def clean(self):
        super().clean()
        if self.parent_id and self.pk:
            if self.parent_id == self.pk or any(a.pk == self.pk for a in self.parent.ancestors()):
                raise ValidationError({"parent": _("A document cannot be placed under itself or one of its own children.")})

    def save(self, *args, **kwargs):
        self.next_review_date = self.compute_next_review_date()
        super().save(*args, **kwargs)

    # --- Lifecycle side effects (RG-DOC-09) -------------------------------

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        from core.lifecycle import DomainRefusalError, validate_transition

        lifecycle = self.get_lifecycle()
        current = self.workflow_state or lifecycle.initial_step.code
        validate_transition(lifecycle, current, target, instance=self, user=user, comment=comment, enforce_permission=False)
        with transaction.atomic():
            if current == POLICY_DRAFT and target == POLICY_ACTIVE and self.version_in_force is None:
                raise DomainRefusalError(_("A document is activated by putting its first version in force."))
            if target == POLICY_RETIRED:
                version = self.version_in_force
                if version is not None:
                    version.transition_to(
                        VERSION_SUPERSEDED, user,
                        comment=str(_("Document %(ref)s retired")) % {"ref": self.reference},
                        enforce_permission=False,
                    )
            result = super().transition_to(target, user, comment=comment, enforce_permission=enforce_permission, save=save)
            if target == POLICY_RETIRED:
                self.refresh_review_date()
        return result

    def open_campaigns(self):
        from documents.models.campaign import AcknowledgementCampaign

        return AcknowledgementCampaign.objects.filter(
            policy_version__policy=self, workflow_state__in=[CAMPAIGN_RUNNING],
        )


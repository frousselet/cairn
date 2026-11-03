# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""One addressee of an acknowledgement campaign : a write-once evidence row.

Only the addressee acknowledges (RG-DOC-17); a row that has left ``pending``
can never change again (RG-DOC-16). Not a governed domain element : no
lifecycle, no reference. See docs/specs/m7-documents/policy-acknowledgement.md.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from documents.constants import CAMPAIGN_RUNNING, AcknowledgementChannel, AcknowledgementStatus


class PolicyAcknowledgement(models.Model):
    scope_parent_lookup = "campaign__policy_version__policy__scopes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "documents.AcknowledgementCampaign", on_delete=models.PROTECT, related_name="acknowledgements",
        verbose_name=_("Campaign"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="policy_acknowledgements",
        verbose_name=_("User"),
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=AcknowledgementStatus.choices,
        default=AcknowledgementStatus.PENDING, db_index=True,
    )
    requested_at = models.DateTimeField(_("Requested at"), auto_now_add=True)
    acknowledged_at = models.DateTimeField(_("Acknowledged at"), null=True, blank=True, editable=False)
    statement = models.CharField(_("Statement"), max_length=500, blank=True, default="", editable=False)
    channel = models.CharField(
        _("Channel"), max_length=10, choices=AcknowledgementChannel.choices, blank=True, default="", editable=False,
    )
    excused_at = models.DateTimeField(_("Excused at"), null=True, blank=True, editable=False)
    excused_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="excused_policy_acknowledgements", verbose_name=_("Excused by"), editable=False,
    )
    excuse_reason = models.TextField(_("Excuse reason"), blank=True, default="")
    last_reminded_at = models.DateTimeField(_("Last reminded at"), null=True, blank=True, editable=False)
    history = HistoricalRecords()

    class Meta:
        ordering = ["campaign", "user__last_name", "user__first_name"]
        verbose_name = _("Acknowledgement")
        verbose_name_plural = _("Acknowledgements")
        constraints = [
            models.UniqueConstraint(fields=["campaign", "user"], name="one_acknowledgement_per_user_and_campaign"),
        ]

    def __str__(self):
        return f"{self.campaign.reference} : {self.user}"

    @property
    def is_pending(self):
        return self.status == AcknowledgementStatus.PENDING

    def save(self, *args, **kwargs):
        # RG-DOC-16 : once a row has left `pending`, nothing about it changes.
        # `last_reminded_at` is the only field the system may still touch, and
        # only while pending.
        if not self._state.adding:
            stored = type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
            if stored is not None and stored != AcknowledgementStatus.PENDING:
                raise ValidationError(_("An acknowledgement that has been given, excused or expired cannot change."))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_("Acknowledgements are kept as evidence and cannot be deleted."))

    # --- The three one-way paths ------------------------------------------

    def acknowledge(self, user, channel=AcknowledgementChannel.WEB):
        """RG-DOC-17 : the addressee, and only them, acknowledges a pending row."""
        from core.lifecycle import DomainRefusalError

        if user is None or user.pk != self.user_id:
            raise DomainRefusalError(_("Only the addressee can acknowledge this document."))
        if not self.is_pending:
            raise DomainRefusalError(_("This acknowledgement is no longer pending."))
        if self.campaign.workflow_state != CAMPAIGN_RUNNING:
            raise DomainRefusalError(_("This campaign is closed."))
        self.status = AcknowledgementStatus.ACKNOWLEDGED
        self.acknowledged_at = timezone.now()
        self.statement = self.campaign.statement_for()
        self.channel = channel
        self.save()

    def excuse(self, user, reason):
        """RG-DOC-19 : excuse a pending row (leaver, long absence) with a reason."""
        from core.lifecycle import DomainRefusalError

        if not self.is_pending:
            raise DomainRefusalError(_("This acknowledgement is no longer pending."))
        if not (reason or "").strip():
            raise DomainRefusalError(_("Give the reason for excusing this person."))
        self.status = AcknowledgementStatus.EXCUSED
        self.excused_at = timezone.now()
        self.excused_by = user
        self.excuse_reason = reason.strip()
        self.save()

    def expire(self):
        """The campaign closed (RG-DOC-18) : a pending row becomes expired."""
        if self.is_pending:
            self.status = AcknowledgementStatus.EXPIRED
            self.save()

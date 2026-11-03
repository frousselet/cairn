# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A request, addressed to an audience, to acknowledge one version of a document.

The A.5.1 / clause 7.3 evidence of communication and awareness. The audience is
resolved once, at launch, into write-once acknowledgement rows (RG-DOC-15).
See docs/specs/m7-documents/acknowledgement-campaign.md.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import ScopedModel
from documents.constants import (
    CAMPAIGN_CLOSED,
    CAMPAIGN_DRAFT,
    CAMPAIGN_RUNNING,
    REFERENCE_PREFIXES,
    VERSION_IN_FORCE,
    AcknowledgementStatus,
)


def default_statement():
    return gettext("I have read and understood {title} version {label}, and I will comply with it.")


class AcknowledgementCampaign(ScopedModel):
    REFERENCE_PREFIX = REFERENCE_PREFIXES["AcknowledgementCampaign"]
    LIFECYCLE_NAME = "acknowledgement_campaign"

    name = models.CharField(_("Name"), max_length=255)
    policy_version = models.ForeignKey(
        "documents.PolicyVersion", on_delete=models.PROTECT, related_name="campaigns",
        verbose_name=_("Version to acknowledge"),
    )
    message = models.TextField(_("Message"), blank=True, default="")
    statement = models.CharField(_("Statement"), max_length=500, default=default_statement)
    due_date = models.DateField(_("Due date"))
    launched_at = models.DateTimeField(_("Launched at"), null=True, blank=True, editable=False)
    closed_at = models.DateTimeField(_("Closed at"), null=True, blank=True, editable=False)
    audience_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="acknowledgement_campaigns",
        verbose_name=_("Users"),
    )
    audience_groups = models.ManyToManyField(
        "accounts.Group", blank=True, related_name="acknowledgement_campaigns", verbose_name=_("Groups"),
    )
    audience_roles = models.ManyToManyField(
        "context.Role", blank=True, related_name="acknowledgement_campaigns", verbose_name=_("Roles"),
    )
    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        ordering = ["-created_at"]
        verbose_name = _("Acknowledgement campaign")
        verbose_name_plural = _("Acknowledgement campaigns")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    @property
    def workflow_perm_namespace(self):
        return "documents.acknowledgement"

    # --- Audience (RG-DOC-15) ---------------------------------------------

    def resolve_audience(self):
        """Active users named, members of the groups, assignees of the roles."""
        User = get_user_model()
        ids = set(self.audience_users.values_list("pk", flat=True))
        for group in self.audience_groups.all():
            ids |= set(group.users.values_list("pk", flat=True))
        for role in self.audience_roles.all():
            ids |= set(role.assigned_users.values_list("pk", flat=True))
        return User.objects.filter(pk__in=ids, is_active=True)

    def _create_rows(self, users):
        from documents.models.acknowledgement import PolicyAcknowledgement

        existing = set(self.acknowledgements.values_list("user_id", flat=True))
        rows = [PolicyAcknowledgement(campaign=self, user=u) for u in users if u.pk not in existing]
        # With history, so each row's creation is in its own audit trail.
        from simple_history.utils import bulk_create_with_history

        bulk_create_with_history(rows, PolicyAcknowledgement)
        return rows

    def add_newcomers(self, user):
        """Re-resolve the audience of a running campaign and add the missing rows."""
        from core.lifecycle import DomainRefusalError

        if self.workflow_state != CAMPAIGN_RUNNING:
            raise DomainRefusalError(_("Newcomers can only be added to a running campaign."))
        rows = self._create_rows(self.resolve_audience())
        if rows:
            self._change_reason = gettext("%(n)d newcomers added") % {"n": len(rows)}
            self.save()
            from documents.notifications import notify_acknowledgement_requested

            notify_acknowledgement_requested(self, [r.user for r in rows])
        return rows

    # --- Progress (RG-DOC-19) ---------------------------------------------

    @property
    def counts(self):
        data = {s.value: 0 for s in AcknowledgementStatus}
        for row in self.acknowledgements.values("status").annotate(n=models.Count("pk")):
            data[row["status"]] = row["n"]
        data["total"] = sum(data.values())
        return data

    @property
    def completion_rate(self):
        c = self.counts
        denominator = c["total"] - c[AcknowledgementStatus.EXCUSED]
        return round(100 * c[AcknowledgementStatus.ACKNOWLEDGED] / denominator) if denominator else 0

    @property
    def is_overdue(self):
        return self.workflow_state == CAMPAIGN_RUNNING and self.due_date < timezone.localdate()

    def statement_for(self):
        version = self.policy_version
        return (
            (self.statement or default_statement())
            .replace("{title}", version.policy.title)
            .replace("{label}", version.version_label)
        )

    # --- Lifecycle side effects (RG-DOC-14, -15, -18) ---------------------

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        from core.lifecycle import DomainRefusalError, validate_transition

        lifecycle = self.get_lifecycle()
        current = self.workflow_state or lifecycle.initial_step.code
        validate_transition(lifecycle, current, target, instance=self, user=user, comment=comment, enforce_permission=False)
        with transaction.atomic():
            audience = None
            if current == CAMPAIGN_DRAFT and target == CAMPAIGN_RUNNING:
                if self.policy_version.workflow_state != VERSION_IN_FORCE:
                    raise DomainRefusalError(_("Only a version in force can be submitted for acknowledgement."))
                audience = list(self.resolve_audience())
                if not audience:
                    raise DomainRefusalError(_("The audience is empty : add users, groups or roles."))
                if self.due_date < timezone.localdate():
                    raise DomainRefusalError(_("The due date is already past."))
                self.launched_at = timezone.now()
            if target == CAMPAIGN_CLOSED:
                self.closed_at = timezone.now()
            result = super().transition_to(target, user, comment=comment, enforce_permission=enforce_permission, save=save)
            if audience is not None:
                rows = self._create_rows(audience)
                from documents.notifications import notify_acknowledgement_requested

                notify_acknowledgement_requested(self, [r.user for r in rows])
            if target == CAMPAIGN_CLOSED:
                # One save per row (not a bulk update) so each expiry is in the
                # row's history.
                for row in self.acknowledgements.filter(status=AcknowledgementStatus.PENDING):
                    row.expire()
        return result

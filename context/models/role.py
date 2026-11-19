# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from core.completeness import Completeness, Requirement
from context.constants import RaciType, RoleStatus, RoleType
from .base import ScopedModel


class Role(ScopedModel):
    REFERENCE_PREFIX = "ROLE"

    name = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(_("Type"), max_length=20, choices=RoleType.choices)
    assigned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="context_roles",
        verbose_name=_("Assigned users"),
    )
    is_mandatory = models.BooleanField(_("Mandatory role"), default=False)
    source_standard = models.CharField(
        _("Source standard"), max_length=255, blank=True, default=""
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=RoleStatus.choices, default=RoleStatus.ACTIVE
    )

    history = HistoricalRecords()

    # What makes the record useful : advice, nothing holds its lifecycle back
    # (a mandatory role nobody holds is flagged on its page, rule RS-06).
    COMPLETENESS = Completeness(
        Requirement(
            "holder", _("assign a user"),
            fields=["assigned_users"], section="assignment", blocking=False,
        ),
        Requirement(
            "responsibilities", _("add a responsibility"),
            check=lambda role: role.responsibilities.exists(),
            # Its responsibilities are rows of its page : the line leads to their card.
            href=lambda role: reverse("context:role-detail", args=[role.pk]) + "#responsibilities-section",
            blocking=False,
        ),
    )

    class Meta(ScopedModel.Meta):
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def get_absolute_url(self):
        return reverse("context:role-detail", args=[self.pk])

    @property
    def compliance_alert(self):
        """RS-06: mandatory role without assigned user."""
        if self.is_mandatory and not self.assigned_users.exists():
            return _("Mandatory role without assigned user")
        return ""

    def send_back_to_draft(self):
        """Demote the role to its initial (draft) state after a change.

        Changing a role's responsibilities invalidates any prior review, so the
        role must be re-validated. Terminal states (archived / cancelled) are
        left untouched. The ``save()`` records the demotion in the role's
        django-simple-history trail, so the change is visible in its history.
        Single source of truth shared by the web views and the REST API.
        """
        try:
            if self.is_terminal_state:
                return
        except Exception:
            pass
        draft_code = self.get_lifecycle().initial_step.code
        if self.workflow_state == draft_code:
            return  # already a plain draft, nothing to record
        self.workflow_state = draft_code
        self.version = (self.version or 0) + 1
        self.save()


class Responsibility(models.Model):
    # Filed under the scopes of its parent : every surface resolves it
    # through core.scoping (lists, records, transitions, history, API, MCP).
    scope_parent_lookup = "role__scopes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="responsibilities",
        verbose_name=_("Role"),
    )
    description = models.TextField(_("Description"))
    raci_type = models.CharField(_("Involvement (RACI)"), max_length=20, choices=RaciType.choices)
    related_activity = models.ForeignKey(
        "context.Activity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsibilities",
        verbose_name=_("Related activity"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Responsibility")
        verbose_name_plural = _("Responsibilities")
        ordering = ["role", "raci_type"]

    def __str__(self):
        return f"{self.role.name} - {self.get_raci_type_display()}"

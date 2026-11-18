# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from core.completeness import Completeness, Requirement
from context.constants import ActivityStatus, ActivityType, Criticality
from .base import ScopedModel


class Activity(ScopedModel):
    REFERENCE_PREFIX = "ACTV"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(_("Type"), max_length=20, choices=ActivityType.choices)
    criticality = models.CharField(
        _("Criticality"), max_length=20, choices=Criticality.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_activities",
        verbose_name=_("Owner"),
    )
    parent_activity = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent activity"),
    )
    related_stakeholders = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="related_activities",
        verbose_name=_("Stakeholders"),
    )
    related_objectives = models.ManyToManyField(
        "context.Objective",
        blank=True,
        related_name="related_activities",
        verbose_name=_("Contributing objectives"),
    )
    # Linked essential assets are exposed via the reverse manager
    # `essential_assets` set up by EssentialAsset.related_activities.
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ActivityStatus.choices,
        default=ActivityStatus.ACTIVE,
    )

    history = HistoricalRecords()

    # What makes the record useful : advice, nothing holds its lifecycle back.
    COMPLETENESS = Completeness(
        Requirement(
            "description", _("say what it covers"),
            fields=["description"], section="identity", blocking=False,
        ),
        Requirement(
            "objectives", _("link the objectives it helps to reach"),
            fields=["related_objectives"], section="relations", blocking=False,
        ),
    )

    class Meta(ScopedModel.Meta):
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def get_absolute_url(self):
        return reverse("context:activity-detail", args=[self.pk])

    @property
    def owner_name(self):
        """Display name of the responsible owner (for read-only API / assistant output)."""
        return self.owner.display_name if self.owner_id else ""

    def clean(self):
        super().clean()
        # RS-04: parent and child must share at least one scope
        if self.parent_activity_id and self.pk:
            parent_scopes = set(self.parent_activity.scopes.values_list("pk", flat=True))
            child_scopes = set(self.scopes.values_list("pk", flat=True))
            if parent_scopes and child_scopes and not (parent_scopes & child_scopes):
                raise ValidationError(
                    {
                        "parent_activity": _(
                            "The child activity must share at least one scope with its parent."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

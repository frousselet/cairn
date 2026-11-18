# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from core.completeness import Completeness, Requirement
from context.constants import (
    EXTERNAL_CATEGORIES,
    INTERNAL_CATEGORIES,
    ImpactLevel,
    IssueCategory,
    IssueStatus,
    IssueType,
    Trend,
)
from .base import ScopedModel


class Issue(ScopedModel):
    REFERENCE_PREFIX = "ISSU"

    name = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(_("Type"), max_length=20, choices=IssueType.choices)
    category = models.CharField(
        _("Category"), max_length=30, choices=IssueCategory.choices
    )
    impact_level = models.CharField(
        _("Impact level"), max_length=20, choices=ImpactLevel.choices
    )
    trend = models.CharField(
        _("Trend"), max_length=20, choices=Trend.choices, blank=True, default=""
    )
    source = models.CharField(_("Source"), max_length=255, blank=True, default="")
    related_stakeholders = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="related_issues",
        verbose_name=_("Related stakeholders"),
    )
    review_date = models.DateField(_("Next review date"), null=True, blank=True)
    status = models.CharField(
        _("Status"), max_length=20, choices=IssueStatus.choices, default=IssueStatus.IDENTIFIED
    )

    history = HistoricalRecords()

    # What makes the record useful : advice, nothing holds its lifecycle back.
    COMPLETENESS = Completeness(
        Requirement(
            "description", _("say why it matters for security"),
            fields=["description"], section="identity", blocking=False,
        ),
        Requirement(
            "review_date", _("plan its next review"),
            fields=["review_date"], section="assessment", blocking=False,
        ),
    )

    class Meta(ScopedModel.Meta):
        verbose_name = _("Issue")
        verbose_name_plural = _("Issues")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def get_absolute_url(self):
        return reverse("context:issue-detail", args=[self.pk])

    def clean(self):
        super().clean()
        # RS-01: type / category consistency
        if self.type == IssueType.INTERNAL and self.category not in INTERNAL_CATEGORIES:
            raise ValidationError(
                {
                    "category": _("An internal issue can only have an internal category.")
                }
            )
        if self.type == IssueType.EXTERNAL and self.category not in EXTERNAL_CATEGORIES:
            raise ValidationError(
                {
                    "category": _("An external issue can only have an external category.")
                }
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

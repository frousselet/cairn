# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords

from context.models.base import LegacyStatusMixin, ScopedModel
from core.completeness import Completeness, Requirement
from risks.constants import Methodology


class RiskAssessment(LegacyStatusMixin, ScopedModel):
    REFERENCE_PREFIX = "RASS"
    LIFECYCLE_NAME = "risk_assessment"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    methodology = models.CharField(
        _("Methodology"),
        max_length=20,
        choices=Methodology.choices,
        default=Methodology.ISO27005,
    )
    assessment_date = models.DateField(pgettext_lazy("risk", "Assessment date"), null=True, blank=True)
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_assessments_assessed",
        verbose_name=_("Assessor"),
    )
    risk_criteria = models.ForeignKey(
        "risks.RiskCriteria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments",
        verbose_name=_("Risk criteria"),
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_assessments_validated",
        verbose_name=_("Validated by"),
    )
    validated_at = models.DateTimeField(_("Validation date"), null=True, blank=True)
    next_review_date = models.DateField(_("Next review"), null=True, blank=True)
    summary = models.TextField(_("Summary"), blank=True)
    history = HistoricalRecords()

    # What makes the record useful : advice, nothing holds its lifecycle back.
    COMPLETENESS = Completeness(
        Requirement(
            "criteria", _("choose the risk criteria"),
            fields=["risk_criteria"], section="identity", blocking=False,
        ),
        Requirement(
            "assessor", _("assign an assessor"),
            fields=["assessor"], section="identity", blocking=False,
        ),
        Requirement(
            "review", _("set the next review date"),
            fields=["next_review_date"], section="planning", blocking=False,
        ),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Risk assessment")
        verbose_name_plural = _("Risk assessments")

    @property
    def workflow_perm_namespace(self):
        return "risks.assessment"


    def __str__(self):
        return f"{self.reference} : {self.name}"

    def get_absolute_url(self):
        return reverse("risks:assessment-detail", args=[self.pk])

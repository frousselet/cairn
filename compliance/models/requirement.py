# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import (
    ComplianceStatus,
    Priority,
    RequirementCategory,
    RequirementStatus,
    RequirementType,
)
from context.models.base import BaseModel
from core.completeness import Completeness, is_filled
from core.completeness import Requirement as Needs


class Requirement(BaseModel):

    # Scope is inherited from the parent : this model carries no `scopes` M2M.
    # Declared on the model, not only on the views, so the generic workflow,
    # history and MCP surfaces enforce it too (see core.scoping).
    scope_parent_lookup = "framework__scopes"
    REFERENCE_PREFIX = "REQT"

    framework = models.ForeignKey(
        "compliance.Framework",
        on_delete=models.CASCADE,
        related_name="requirements",
        verbose_name=_("Framework"),
    )
    section = models.ForeignKey(
        "compliance.Section",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requirements",
        verbose_name=_("Section"),
    )
    requirement_number = models.CharField(
        _("Requirement number"), max_length=100, blank=True, default=""
    )
    name = models.CharField(_("Title"), max_length=500)
    description = models.TextField(_("Description"))
    guidance = models.TextField(
        _("Implementation recommendations"), blank=True, default=""
    )
    type = models.CharField(
        _("Type"), max_length=20, choices=RequirementType.choices
    )
    category = models.CharField(
        _("Category"),
        max_length=20,
        choices=RequirementCategory.choices,
        blank=True,
        default="",
    )
    is_applicable = models.BooleanField(_("Applicable"), default=True)
    applicability_justification = models.TextField(
        _("Applicability justification"), blank=True, default=""
    )
    compliance_status = models.CharField(
        _("Compliance status"),
        max_length=30,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.NOT_ASSESSED,
    )
    compliance_level = models.PositiveIntegerField(
        _("Compliance level (%)"), default=0
    )
    compliance_evidence = models.TextField(_("Compliance evidence"), blank=True, default="")
    compliance_finding = models.TextField(_("Finding"), blank=True, default="")
    last_assessment_date = models.DateField(
        _("Last assessment"), null=True, blank=True
    )
    last_assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessed_requirements",
        verbose_name=_("Last assessor"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_requirements",
        verbose_name=_("Owner"),
    )
    priority = models.CharField(
        _("Priority"),
        max_length=20,
        choices=Priority.choices,
        blank=True,
        default="",
    )
    target_date = models.DateField(_("Target date"), null=True, blank=True)
    # Controls : reverse accessor `controls` from controls.Control.requirements.
    linked_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="linked_requirements",
        verbose_name=_("Linked essential assets"),
    )
    # linked_risks: reverse M2M from risks.Risk.linked_requirements
    linked_stakeholder_expectations = models.ManyToManyField(
        "context.StakeholderExpectation",
        blank=True,
        related_name="linked_requirements",
        verbose_name=_("Linked stakeholder expectations"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=RequirementStatus.choices,
        default=RequirementStatus.ACTIVE,
    )

    history = HistoricalRecords()

    # What makes the record useful : advice, nothing holds its lifecycle back.
    COMPLETENESS = Completeness(
        Needs(
            "owner", _("assign an owner"),
            fields=["owner"], section="follow_up", blocking=False,
        ),
        Needs(
            "exclusion", _("justify the exclusion"),
            check=lambda requirement: requirement.is_applicable or is_filled(requirement, "applicability_justification"),
            section="applicability", blocking=False,
        ),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Requirement")
        verbose_name_plural = _("Requirements")
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "requirement_number"],
                name="unique_requirement_number_per_framework",
                condition=~models.Q(requirement_number=""),
            )
        ]

    def __str__(self):
        if self.requirement_number:
            return f"{self.requirement_number} : {self.name}"
        return f"{self.reference} : {self.name}"

    def get_absolute_url(self):
        return reverse("compliance:requirement-detail", args=[self.pk])

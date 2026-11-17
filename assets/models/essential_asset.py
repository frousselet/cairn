# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import (
    INFORMATION_CATEGORIES,
    PROCESS_CATEGORIES,
    DICLevel,
    DataClassification,
    EssentialAssetCategory,
    EssentialAssetStatus,
    EssentialAssetType,
)
from context.models.base import LegacyStatusMixin, ScopedModel
from core.completeness import Completeness, Requirement


class EssentialAsset(LegacyStatusMixin, ScopedModel):
    REFERENCE_PREFIX = "EAST"
    LIFECYCLE_NAME = "essential_asset"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(
        _("Type"), max_length=20, choices=EssentialAssetType.choices
    )
    category = models.CharField(
        _("Category"), max_length=30, choices=EssentialAssetCategory.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_essential_assets",
        verbose_name=_("Owner"),
    )
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custodian_essential_assets",
        verbose_name=_("Custodian"),
    )
    # The security needs. Empty means "not assessed yet" : a level is a
    # decision somebody took, never a default the record was born with
    # (RV-07). An asset is created without them and cannot become active
    # until the three are set (COMPLETENESS below).
    confidentiality_level = models.IntegerField(
        _("Confidentiality"), choices=DICLevel.choices, null=True, blank=True
    )
    integrity_level = models.IntegerField(
        _("Integrity"), choices=DICLevel.choices, null=True, blank=True
    )
    availability_level = models.IntegerField(
        _("Availability"), choices=DICLevel.choices, null=True, blank=True
    )
    confidentiality_justification = models.TextField(
        _("Confidentiality justification"), blank=True, default=""
    )
    integrity_justification = models.TextField(
        _("Integrity justification"), blank=True, default=""
    )
    availability_justification = models.TextField(
        _("Availability justification"), blank=True, default=""
    )
    # The label spells the notion out, its acronym follows : the reader who
    # has never met "RTO" still knows what is asked.
    max_tolerable_downtime = models.CharField(
        _("Maximum tolerable downtime (MTD)"), max_length=100, blank=True, default=""
    )
    recovery_time_objective = models.CharField(
        _("Recovery time objective (RTO)"), max_length=100, blank=True, default=""
    )
    recovery_point_objective = models.CharField(
        _("Recovery point objective (RPO)"), max_length=100, blank=True, default=""
    )
    data_classification = models.CharField(
        _("Classification"),
        max_length=20,
        choices=DataClassification.choices,
        blank=True,
        default="",
    )
    personal_data = models.BooleanField(
        _("Personal data"), default=False
    )
    personal_data_categories = models.JSONField(
        _("GDPR categories"), null=True, blank=True
    )
    regulatory_constraints = models.TextField(
        _("Regulatory constraints"), blank=True, default=""
    )
    related_activities = models.ManyToManyField(
        "context.Activity",
        blank=True,
        related_name="essential_assets",
        verbose_name=_("Business activities"),
    )
    review_date = models.DateField(_("Next review date"), null=True, blank=True)

    history = HistoricalRecords()

    # An essential asset is created with what it is and who answers for it,
    # then completed on its page. It cannot become active until its security
    # needs are assessed (RS-10 in docs/specs/m2-assets/README.md).
    COMPLETENESS = Completeness(
        Requirement(
            "security_needs", _("assess its security needs"),
            fields=["confidentiality_level", "integrity_level", "availability_level"],
            section="security",
        ),
        Requirement(
            "description", _("say what it is used for"),
            fields=["description"], section="identity", blocking=False,
        ),
        Requirement(
            "support_assets", _("attach the support assets it relies on"),
            fields=["dependencies_as_essential"], blocking=False,
            href=lambda asset: reverse("assets:dependency-list"),
        ),
        Requirement(
            "continuity", _("say how long the business can do without it"),
            any_of=["max_tolerable_downtime", "recovery_time_objective", "recovery_point_objective"],
            section="continuity", blocking=False,
        ),
        before=(EssentialAssetStatus.ACTIVE.value,),
    )

    class Meta(ScopedModel.Meta):
        verbose_name = _("Essential asset")
        verbose_name_plural = _("Essential assets")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def get_absolute_url(self):
        return reverse("assets:essential-asset-detail", kwargs={"pk": self.pk})

    @property
    def owner_name(self):
        """Display name of the responsible owner (for read-only API / assistant output)."""
        return self.owner.display_name if self.owner_id else ""

    def clean(self):
        super().clean()
        # RS-01: type/category coherence
        if self.type == EssentialAssetType.BUSINESS_PROCESS and self.category not in PROCESS_CATEGORIES:
            raise ValidationError(
                {"category": _("A business process can only have a process category.")}
            )
        if self.type == EssentialAssetType.INFORMATION and self.category not in INFORMATION_CATEGORIES:
            raise ValidationError(
                {"category": _("An information asset can only have an information category.")}
            )

    @property
    def workflow_perm_namespace(self):
        return "assets.essential_asset"

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        # RV-04: recalculate inherited DIC on all linked support assets
        self._recalculate_support_assets_dic()

    def _recalculate_support_assets_dic(self):
        for dep in self.dependencies_as_essential.select_related("support_asset"):
            dep.support_asset.recalculate_inherited_dic()

    @property
    def security_needs_assessed(self):
        """Whether the three security needs have been set."""
        return None not in (self.confidentiality_level, self.integrity_level, self.availability_level)

    @property
    def max_dic_level(self):
        """The highest of the levels set, or ``None`` when none is."""
        levels = [
            level
            for level in (self.confidentiality_level, self.integrity_level, self.availability_level)
            if level is not None
        ]
        return max(levels) if levels else None

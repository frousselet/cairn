# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel, LegacyStatusMixin
from core.completeness import Completeness, Requirement
from risks.constants import (
    EbiosIterationType,
    EbiosWorkshopNumber,
)

# ── What a workshop needs before it is validated ─────────────────────────────
#
# A workshop is validated on its deliverables (rule RE-04 of the EBIOS RM
# specification) : its page lists what is missing, each line leading to the
# card where it is done, and its lifecycle refuses "validated" while a
# blocking line remains. Each requirement concerns one workshop (``when``).


def _of_workshop(number):
    """The requirements of workshop ``number`` concern its progress rows only."""
    return lambda workshop: workshop.workshop_number == number


def _at(anchor):
    """The card of the workshop page where a requirement is met."""
    return lambda workshop: f"{workshop.get_absolute_url()}#{anchor}"


def _security_baseline(workshop):
    return getattr(workshop.assessment, "ebios_security_baseline", None)


def _the_baseline_names(relation):
    """The security baseline of the study holds at least one record of ``relation``."""

    def check(workshop):
        baseline = _security_baseline(workshop)
        return baseline is not None and getattr(baseline, relation).exists()

    return check


def _each_essential_asset_has_a_feared_event(workshop):
    baseline = _security_baseline(workshop)
    if baseline is None:
        return False
    studied = set(baseline.essential_assets.values_list("pk", flat=True))
    feared = set(baseline.feared_events.values_list("essential_asset_id", flat=True))
    # No asset chosen yet : that is the line above, not this one.
    return studied <= feared


def _each_feared_event_has_a_gravity(workshop):
    baseline = _security_baseline(workshop)
    return baseline is None or not baseline.feared_events.filter(gravity_level__isnull=True).exists()


def _the_study_has(related_name, **filters):
    """The study holds at least one row of ``related_name`` matching ``filters``."""

    def check(workshop):
        return getattr(workshop.assessment, related_name).filter(**filters).exists()

    return check


def _each_retained_risk_source_is_rated(workshop):
    # The threat level follows from the motivation and the resources : a
    # retained source without one has not been rated.
    return not workshop.assessment.ebios_risk_sources.filter(is_retained=True, threat_level__isnull=True).exists()


_W1 = _of_workshop(EbiosWorkshopNumber.W1)
_W2 = _of_workshop(EbiosWorkshopNumber.W2)


class EbiosWorkshopProgress(LegacyStatusMixin, BaseModel):
    """Tracks the progression of an EBIOS RM workshop for an assessment.

    Six instances are created automatically when an assessment with
    methodology=ebios_rm is created (W0..W5, iteration_type=strategic,
    iteration_number=1). New iterations are created via the `iterate` action.
    """

    # Filed under the scopes of its parent : every surface resolves it
    # through core.scoping (lists, records, transitions, history, API, MCP).
    scope_parent_lookup = "assessment__scopes"

    LIFECYCLE_NAME = "ebios_workshop"

    REFERENCE_PREFIX = "EWSP"

    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_workshops",
        verbose_name=_("Risk assessment"),
    )
    workshop_number = models.IntegerField(
        _("Workshop number"),
        choices=EbiosWorkshopNumber.choices,
    )
    iteration_type = models.CharField(
        _("Iteration type"),
        max_length=20,
        choices=EbiosIterationType.choices,
        default=EbiosIterationType.STRATEGIC,
    )
    iteration_number = models.PositiveIntegerField(
        _("Iteration number"),
        default=1,
    )
    started_at = models.DateTimeField(_("Started at"), null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_workshops_validated",
        verbose_name=_("Validated by"),
    )
    validated_at = models.DateTimeField(_("Validated at"), null=True, blank=True)
    rejection_reason = models.TextField(_("Rejection reason"), blank=True)
    deliverables_summary = models.TextField(_("Deliverables summary"), blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["assessment", "iteration_number", "workshop_number"]
        verbose_name = _("EBIOS RM workshop progress")
        verbose_name_plural = _("EBIOS RM workshop progress")
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "workshop_number", "iteration_type", "iteration_number"],
                name="unique_ebios_workshop_iteration",
            ),
        ]

    COMPLETENESS = Completeness(
        # ── Workshop 1 : the security baseline ──
        Requirement(
            "w1_essential_assets", _("choose the essential assets"),
            check=_the_baseline_names("essential_assets"), when=_W1, href=_at("business-values-and-assets"),
        ),
        Requirement(
            "w1_support_assets", _("choose the support assets"),
            check=_the_baseline_names("support_assets"), when=_W1, href=_at("business-values-and-assets"),
        ),
        Requirement(
            "w1_feared_events", _("add a feared event for each essential asset"),
            check=_each_essential_asset_has_a_feared_event, when=_W1, href=_at("feared-events"),
        ),
        Requirement(
            "w1_gravity", _("assess the gravity of each feared event"),
            check=_each_feared_event_has_a_gravity, when=_W1, href=_at("feared-events"), blocking=False,
        ),
        Requirement(
            "w1_business_values", _("choose the business values (activities)"),
            check=_the_baseline_names("business_values"), when=_W1, href=_at("business-values-and-assets"),
            blocking=False,
        ),
        Requirement(
            "w1_baseline_references", _("choose the baseline references"),
            check=_the_baseline_names("baseline_references"), when=_W1, href=_at("baseline-references"),
            blocking=False,
        ),
        # ── Workshop 2 : risk sources and targeted objectives ──
        Requirement(
            "w2_risk_sources", _("add a risk source"),
            check=_the_study_has("ebios_risk_sources"), when=_W2, href=_at("risk-sources"),
        ),
        Requirement(
            "w2_targeted_objectives", _("add a targeted objective"),
            check=_the_study_has("ebios_risk_sources", targeted_objectives__isnull=False),
            when=_W2, href=_at("risk-sources"),
        ),
        Requirement(
            "w2_retained_pair", _("retain a pair of risk source and targeted objective"),
            check=_the_study_has("ebios_sr_ov_pairs", is_retained=True), when=_W2, href=_at("pairs"),
        ),
        Requirement(
            "w2_threat_levels", _("rate the motivation and the resources of each retained risk source"),
            check=_each_retained_risk_source_is_rated, when=_W2, href=_at("risk-sources"), blocking=False,
        ),
        before=("validated",),
    )

    @property
    def workflow_perm_namespace(self):
        return "risks.ebios_assessment"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse(
            "risks:ebios-workshop-detail",
            kwargs={"assessment_pk": self.assessment_id, "workshop_pk": self.pk},
        )


    def __str__(self):
        return f"{self.reference} : W{self.workshop_number} ({self.get_status_display()})"

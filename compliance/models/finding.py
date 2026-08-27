# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import (
    EffectivenessVerdict,
    FindingSource,
    FindingType,
    FINDING_REFERENCE_PREFIXES,
)
from context.models.base import BaseModel


class Finding(BaseModel):
    """The organisation's nonconformity register entry (ISO 27001 clause 10.1).

    Originally an *audit finding* : it required an assessment and existed only
    inside one. It now records one departure from a requirement, a control or
    the organisation's own procedure, whatever surfaced it, so clause 10.2 is
    answered from a single register rather than from several to reconcile.

    Reference is auto-generated from the finding type:
    NCMAJ-1, NCMIN-1, OBS-1, OA-1, STR-1, etc.
    """

    # Scope is inherited from the parent : this model carries no `scopes` M2M.
    # Declared on the model, not only on the views, so the generic workflow,
    # history and MCP surfaces enforce it too (see core.scoping).
    scope_parent_lookup = "assessment__scopes"
    # A nonconformity raised outside an audit has no parent to inherit from.
    # Without this it would be dropped by the INNER JOIN and invisible to
    # every non-superuser, which for a register is data loss in practice.
    scope_parent_optional = True

    assessment = models.ForeignKey(
        "compliance.ComplianceAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="findings",
        verbose_name=_("Assessment"),
        help_text=_("The audit that raised this nonconformity, when one did."),
    )
    source = models.CharField(
        _("Source"),
        max_length=32,
        choices=FindingSource.choices,
        default=FindingSource.AUDIT,
        db_index=True,
        help_text=_("What surfaced this nonconformity."),
    )
    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="findings",
        verbose_name=_("Incident"),
        help_text=_("The security incident that raised this nonconformity."),
    )
    finding_type = models.CharField(
        _("Finding type"),
        max_length=20,
        choices=FindingType.choices,
    )
    description = models.TextField(_("Finding"))
    recommendation = models.TextField(
        _("Recommendation"), blank=True, default=""
    )
    evidence = models.TextField(
        _("Evidence presented"), blank=True, default=""
    )
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="findings",
        # The column is unchanged; only the label moves, because the field
        # names whoever raised the nonconformity and that is no longer
        # always an auditor.
        verbose_name=_("Raised by"),
    )
    requirements = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="findings",
        verbose_name=_("Related requirements"),
    )
    effectiveness_reviewed_at = models.DateTimeField(
        _("Effectiveness reviewed at"),
        null=True,
        blank=True,
        help_text=_("When the corrective action's effectiveness was reviewed."),
    )
    effectiveness_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_findings",
        verbose_name=_("Effectiveness reviewed by"),
    )
    effectiveness_verdict = models.CharField(
        _("Effectiveness verdict"),
        max_length=32,
        choices=EffectivenessVerdict.choices,
        blank=True,
        default="",
        help_text=_(
            "Whether the corrective action worked. An action plan reaching a "
            "done step proves it was implemented, never that it was effective."
        ),
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Finding")
        verbose_name_plural = _("Findings")
        ordering = ["reference"]

    def __str__(self):
        return f"{self.reference} - {self.get_finding_type_display()}"

    @property
    def assessment_name(self):
        """Audit that raised it, if any (for read-only API / assistant output)."""
        return self.assessment.name if self.assessment_id else ""

    @property
    def incident_reference(self):
        """Incident that raised it, if any (for read-only API / assistant output)."""
        return self.incident.reference if self.incident_id else ""

    @property
    def assessor_name(self):
        """Who raised it (for read-only API / assistant output)."""
        return self.assessor.display_name if self.assessor_id else ""

    @property
    def effectiveness_reviewed_by_name(self):
        """Who reviewed effectiveness (for read-only API / assistant output)."""
        return (
            self.effectiveness_reviewed_by.display_name
            if self.effectiveness_reviewed_by_id
            else ""
        )

    def clean(self):
        """An audit finding still needs its audit and its auditor.

        The two fields became optional so a nonconformity raised by an
        incident, a management review, monitoring or a complaint does not
        need a fabricated audit. They stay mandatory for `source = audit`,
        which is where they mean something.
        """
        super().clean()
        errors = {}
        if self.source == FindingSource.AUDIT:
            if self.assessment_id is None:
                errors["assessment"] = _(
                    "An audit finding must be linked to an assessment."
                )
            if self.assessor_id is None:
                errors["assessor"] = _("An audit finding must name who raised it.")
        if self.effectiveness_verdict and self.effectiveness_reviewed_at is None:
            errors["effectiveness_reviewed_at"] = _(
                "Recording an effectiveness verdict requires the date it was reviewed."
            )
        if errors:
            raise ValidationError(errors)

    @classmethod
    def _generate_reference_for_type(cls, finding_type):
        """Generate the next unique reference for the given finding type."""
        prefix = FINDING_REFERENCE_PREFIXES.get(finding_type, "FIND")
        prefix_with_dash = f"{prefix}-"
        existing_refs = cls.objects.filter(
            reference__startswith=prefix_with_dash
        ).values_list("reference", flat=True)
        max_num = 0
        prefix_len = len(prefix_with_dash)
        for ref in existing_refs:
            try:
                num = int(ref[prefix_len:])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        return f"{prefix}-{max_num + 1}"

    def save(self, *args, **kwargs):
        if not self.reference and self.finding_type:
            self.reference = self._generate_reference_for_type(self.finding_type)
        # Skip ReferenceGeneratorMixin.save() which requires 4-char REFERENCE_PREFIX
        models.Model.save(self, *args, **kwargs)

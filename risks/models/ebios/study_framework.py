# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel, LegacyStatusMixin

# What an external participant is made of : the keys of an entry of
# ``StudyFramework.participants_external``, each a short text on one line.
EXTERNAL_PARTICIPANT_KEYS = ("name", "role", "organization")
EXTERNAL_PARTICIPANT_TEXT_MAX = 150
EXTERNAL_PARTICIPANTS_MAX = 50


def validate_external_participants(value):
    """Refuse external participants that are not a list of ``{name, role, organization}`` texts.

    The field is JSON and stored what it was given, whereas the page of
    workshop 0 reads a name out of each entry. Declared on the field, the rule
    holds for the REST API and the MCP tool; the form of the workshop builds
    its entries from text and goes through here too.
    """
    shape = _("The external participants must be a list of {name, role, organization} entries, each a text.")
    if not isinstance(value, list):
        raise ValidationError(shape)
    if len(value) > EXTERNAL_PARTICIPANTS_MAX:
        raise ValidationError(
            _("A study framework is limited to %(max)d external participants.")
            % {"max": EXTERNAL_PARTICIPANTS_MAX}
        )
    for entry in value:
        if not isinstance(entry, dict) or set(entry) - set(EXTERNAL_PARTICIPANT_KEYS):
            raise ValidationError(shape)
        texts = [entry.get(key) for key in EXTERNAL_PARTICIPANT_KEYS]
        if any(text is not None and not isinstance(text, str) for text in texts):
            raise ValidationError(shape)
        if any(len(text or "") > EXTERNAL_PARTICIPANT_TEXT_MAX for text in texts):
            raise ValidationError(
                _("The name, the role and the organisation of an external participant are limited to "
                  "%(max)d characters.") % {"max": EXTERNAL_PARTICIPANT_TEXT_MAX}
            )
        if not (entry.get("name") or "").strip():
            raise ValidationError(_("An external participant needs a name."))


class StudyFramework(LegacyStatusMixin, BaseModel):
    """EBIOS RM Workshop 0 - Study framework.

    Captures the pre-requisites required by ANSSI before workshop 1:
    perimeters, participants, applicable frameworks, assumptions, constraints.
    Exactly one instance per ebios_rm RiskAssessment.
    """

    # Filed under the scopes of its parent : every surface resolves it
    # through core.scoping (lists, records, transitions, history, API, MCP).
    scope_parent_lookup = "assessment__scopes"

    LIFECYCLE_NAME = "ebios_study_framework"

    REFERENCE_PREFIX = "EFRA"

    assessment = models.OneToOneField(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_study_framework",
        verbose_name=_("Risk assessment"),
    )
    mission_statement = models.TextField(_("Mission statement"), blank=True)
    business_perimeter = models.TextField(_("Business perimeter"), blank=True)
    technical_perimeter = models.TextField(_("Technical perimeter"), blank=True)
    temporal_perimeter = models.TextField(_("Temporal perimeter"), blank=True)
    financial_envelope = models.DecimalField(
        _("Financial envelope"),
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="ebios_study_frameworks",
        verbose_name=_("Internal participants"),
    )
    participants_external = models.JSONField(
        _("External participants"),
        default=list,
        blank=True,
        validators=[validate_external_participants],
        help_text=_("List of external participants as {name, role, organization} entries."),
    )
    applicable_frameworks = models.ManyToManyField(
        "compliance.Framework",
        blank=True,
        related_name="ebios_study_frameworks",
        verbose_name=_("Applicable frameworks"),
    )
    assumptions = models.TextField(_("Assumptions"), blank=True)
    constraints = models.TextField(_("Constraints"), blank=True)
    expected_deliverables = models.TextField(_("Expected deliverables"), blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("EBIOS RM study framework")
        verbose_name_plural = _("EBIOS RM study frameworks")

    @property
    def workflow_perm_namespace(self):
        return "risks.ebios_assessment"

    @property
    def external_participant_list(self):
        """The external participants that can be shown : ``{name, role, organization}`` of one-line texts.

        Lenient where :func:`validate_external_participants` is strict : a row
        written before the shape was held is read for what it has, and an
        entry without a name is left out.
        """
        value = self.participants_external
        people = []
        for entry in value if isinstance(value, list) else []:
            if not isinstance(entry, dict):
                continue
            person = {
                key: " ".join(str(entry.get(key) or "").split())[:EXTERNAL_PARTICIPANT_TEXT_MAX]
                for key in EXTERNAL_PARTICIPANT_KEYS
            }
            if person["name"]:
                people.append(person)
        return people


    def __str__(self):
        return f"{self.reference} : {self.assessment.name}"

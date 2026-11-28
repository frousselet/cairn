# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An agent skill written by the organization, served over MCP once validated."""

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from core.completeness import Completeness, Requirement


def validate_skill_name(value):
    from mcp.skills import name_problem

    if name_problem(value):
        raise ValidationError(
            _("Use 1 to 64 lowercase letters, digits and hyphens, without a hyphen first, last or twice in a row."),
            code="invalid_skill_name",
        )


class McpSkill(BaseModel):
    """A procedure of the organization, written for the agents that use Cairn.

    Served by the MCP server as ``skill://cairn/<name>/SKILL.md`` (see
    :mod:`mcp.skills`) once it reaches a reportable step of its lifecycle
    (*Validated*) : what it says becomes instructions in the model's context,
    so it is validated by someone holding ``system.mcp_skill.approve`` before
    any agent reads it. A skill named like one Cairn ships replaces it for the
    whole instance while it is validated.

    What was validated is what is served : changing the name, the description
    or the instructions of a served skill sends it back to the first step of
    its lifecycle (:meth:`save`), whatever the surface, so the new text is
    read by no agent until it is validated again.
    """

    #: The fields the served ``SKILL.md`` is made of.
    SERVED_FIELDS = ("name", "description", "body")

    REFERENCE_PREFIX = "SKIL"

    name = models.CharField(
        _("Name"),
        max_length=64,
        unique=True,
        validators=[validate_skill_name],
        help_text=_(
            "Lowercase letters, digits and hyphens, for example supplier-onboarding. "
            "The name of a skill Cairn ships replaces it."
        ),
    )
    description = models.TextField(
        _("Description"),
        max_length=1024,
        validators=[MaxLengthValidator(1024)],
        help_text=_(
            "What the skill does and when an agent should use it, for example: "
            "Onboard a new supplier, when the user asks to add or assess a supplier."
        ),
    )
    body = models.TextField(
        _("Instructions"),
        blank=True,
        default="",
        help_text=_("The steps the agent follows, in Markdown. Name the tools it calls."),
    )

    history = HistoricalRecords()

    COMPLETENESS = Completeness(
        Requirement("body", _("write the instructions"), fields=["body"], section="instructions"),
        before=("pending", "validated"),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Agent skill")
        verbose_name_plural = _("Agent skills")
        ordering = ["name"]

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def save(self, *args, **kwargs):
        if not self._state.adding and self.counts_in_reports:
            stored = type(self)._base_manager.filter(pk=self.pk).values("workflow_state", *self.SERVED_FIELDS).first()
            lifecycle = self.get_lifecycle()
            if (
                stored is not None
                and stored["workflow_state"] in lifecycle.reportable_step_codes
                and any(stored[name] != getattr(self, name) for name in self.SERVED_FIELDS)
            ):
                # Served text changed : it waits for a new validation.
                self.workflow_state = lifecycle.initial_step.code
                fields = kwargs.get("update_fields")
                if fields is not None and "workflow_state" not in fields:
                    kwargs["update_fields"] = [*fields, "workflow_state"]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("mcp_skills:skill-detail", args=[self.pk])

    @property
    def workflow_perm_namespace(self):
        return "system.mcp_skill"

    @property
    def replaces_shipped_skill(self):
        """Whether Cairn ships a skill of this name, which this one replaces once validated."""
        from mcp.skills import shipped_names

        return self.name in shipped_names()

    @property
    def uri(self):
        from mcp.skills import URI_PREFIX

        return f"{URI_PREFIX}{self.name}/SKILL.md"

    def skill_md(self):
        """The ``SKILL.md`` this skill is served as."""
        from mcp.skills import render_skill_md

        return render_skill_md(self.name, self.description, self.body)

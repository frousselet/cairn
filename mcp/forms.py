# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Forms of the agent skills (``mcp.McpSkill``)."""

from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.modal_forms import CreationFormMixin, ScopedFormMixin, Step, SteppedFormMixin
from mcp.models import McpSkill

FORM_WIDGET_ATTRS = {"class": "form-control"}


class McpSkillForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """An agent skill : its name and when to use it, then its instructions.

    The instructions are Markdown, as the Agent Skills format reads them : a
    plain text area, never the rich-text editor (``no-richtext``), whose HTML
    an agent would receive as it is.
    """

    steps = [
        Step(_("Identity"), "card-text", ["name", "description"], key="identity",
             intro=_("The name and the description are all an agent reads before it chooses the skill.")),
        Step(_("Instructions"), "list-ol", ["body"], key="instructions",
             intro=_("The steps the agent follows once it chose the skill, in Markdown.")),
    ]

    class Meta:
        model = McpSkill
        fields = ["name", "description", "body"]
        widgets = {
            "name": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "autocomplete": "off", "spellcheck": "false"}),
            "description": forms.Textarea(attrs={"class": "form-control no-richtext", "rows": 3}),
            "body": forms.Textarea(attrs={"class": "form-control no-richtext font-monospace", "rows": 18}),
        }

    def clean_name(self):
        """Lowercase and hyphenate what was typed : *Supplier onboarding* is ``supplier-onboarding``."""
        name = self.cleaned_data.get("name") or ""
        return slugify(name).replace("_", "-").strip("-")[:64]


class McpSkillCreateForm(CreationFormMixin, McpSkillForm):
    """A skill is created by its name and its description, on one screen; its
    instructions are written on its page, which lists them."""

    owner_field = None

    steps = [
        Step(_("Identity"), "card-text", ["name", "description"]),
    ]

    class Meta(McpSkillForm.Meta):
        fields = ["name", "description"]

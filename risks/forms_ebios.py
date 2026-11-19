# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The forms of the EBIOS RM workshops.

The records of a workshop are rows of its page : they are added and edited
in the side panel, from that page, and go back to it. A row is created with
the few fields that make it exist (``docs/sdk/usability-standard.md``, rule
F1), the rest is filled in when it is edited. The record a row hangs under
(the security baseline, the study) is known from the address : it is never
asked (rule F2).

The forms of workshop 1 follow the standard; those of the other workshops are
brought to it one workshop at a time.
"""

from django import forms
from django.db.models import Max, Q
from django.utils.translation import gettext_lazy as _

from core.lifecycle import linkable_or_linked
from core.modal_forms import CreationFormMixin, Step, SteppedFormMixin
from core.scoping import restrict_form_relations
from risks.forms import FORM_WIDGET_ATTRS, SELECT_ATTRS, get_scale_choices
from risks.models import (
    AttackPathStep,
    AttackTechnique,
    BaselineGap,
    EbiosSummary,
    EcosystemStakeholder,
    FearedEvent,
    OperationalScenario,
    PACSMeasure,
    RiskSource,
    RiskSourceObjectivePair,
    SecurityBaseline,
    StrategicScenario,
    StudyFramework,
    TargetedObjective,
)


class StudyFrameworkForm(forms.ModelForm):
    """Workshop 0 main form. Lives on the assessment detail / workshop page."""

    class Meta:
        model = StudyFramework
        fields = [
            "mission_statement",
            "business_perimeter",
            "technical_perimeter",
            "temporal_perimeter",
            "financial_envelope",
            "applicable_frameworks",
            "participants",
            "assumptions",
            "constraints",
            "expected_deliverables",
        ]
        widgets = {
            "mission_statement": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "business_perimeter": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "technical_perimeter": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "temporal_perimeter": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "financial_envelope": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "applicable_frameworks": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "participants": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "assumptions": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "constraints": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "expected_deliverables": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


def next_rank(siblings):
    """The rank of a row added at the end of ``siblings`` (a queryset of the rows it joins).

    A row is not asked where it stands : it comes last, and keeps the order
    the rows were added in.
    """
    return (siblings.aggregate(last=Max("order"))["last"] or 0) + 1


def named_level_field(field, choices, current):
    """The select of a level picked by its name on a scale, in place of ``field``.

    ``choices`` are the levels of the scale. No level is an answer too : it
    reads *Not assessed*, never a default (rule F8). A level rated on a scale
    that has since changed is kept as it is.
    """
    levels = [(value, label) for value, label in choices if value not in ("", None)]
    if current is not None and current not in [value for value, _label in levels]:
        levels.append((current, str(current)))
    offered = [("", _("Not assessed")), *levels]
    return forms.TypedChoiceField(
        choices=offered, coerce=int, required=False, empty_value=None,
        label=field.label, help_text=field.help_text,
        widget=forms.Select(attrs=SELECT_ATTRS),
    )


class SecurityBaselineForm(SteppedFormMixin, forms.ModelForm):
    """The security baseline of a study : one section per card of the page of workshop 1."""

    steps = [
        Step(_("Business values and assets"), "diagram-3",
             ["business_values", "essential_assets", "support_assets"],
             key="studied",
             intro=_("A study protects business values : the activities of the organisation and its "
                     "essential assets, with the support assets they rely on.")),
        Step(_("Security needs summary"), "shield-lock", ["dic_summary"], key="needs"),
        Step(_("Baseline references"), "journal-check", ["baseline_references"], key="references",
             intro=_("The security baseline is what the organisation already applies : the frameworks "
                     "it follows. A baseline gap is one of their rules that is not met.")),
    ]

    class Meta:
        model = SecurityBaseline
        fields = [
            "business_values",
            "essential_assets",
            "support_assets",
            "dic_summary",
            "baseline_references",
        ]
        widgets = {
            "business_values": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "essential_assets": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "support_assets": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "dic_summary": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "baseline_references": forms.SelectMultiple(attrs=SELECT_ATTRS),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "business_values": _('The activities the study protects, for example "Electricity generation".'),
            "essential_assets": _("The information and the processes the study protects. Each one gets a feared event."),
            "support_assets": _("The systems, the premises and the teams these essential assets rely on."),
            "dic_summary": _("In a few lines, how far the studied assets must stay available, exact and secret."),
            "baseline_references": _("For example ISO 27002 or the ANSSI hygiene guide."),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # A new link targets a record that can be linked; what the baseline
        # already holds stays, whatever became of it since.
        for name in ("business_values", "essential_assets", "support_assets", "baseline_references"):
            field = self.fields.get(name)
            if field is None:
                continue
            held = getattr(self.instance, name).all() if self.instance.pk else None
            field.queryset = linkable_or_linked(field.queryset, held)
        if user is not None:
            restrict_form_relations(self, user)


class FearedEventForm(SteppedFormMixin, forms.ModelForm):
    """A feared event of the security baseline : a row of workshop 1, on one screen."""

    steps = [
        Step(_("Feared event"), "exclamation-triangle",
             [["essential_asset", "dic_criterion"], "name", "description",
              "gravity_level", "gravity_justification"],
             key="event"),
    ]

    class Meta:
        model = FearedEvent
        fields = [
            "essential_asset",
            "dic_criterion",
            "name",
            "description",
            "gravity_level",
            "gravity_justification",
        ]
        widgets = {
            "essential_asset": forms.Select(attrs=SELECT_ATTRS),
            "dic_criterion": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "gravity_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
        help_texts = {
            "essential_asset": _("The essential asset the event would harm, among those of the security baseline."),
            "dic_criterion": _("Confidentiality when the asset leaks, integrity when it is altered, "
                               "availability when it stops. One feared event per asset and criterion."),
            "name": _('For example "The customer file is disclosed" or "Production supervision stops".'),
            "description": _("The event as the business would live it, and the consequences that follow."),
            "gravity_level": _("The seriousness of the consequences, on the impact scale of the risk criteria. "
                               "Leave it empty until it is assessed."),
            "gravity_justification": _("The financial, legal, operational or human consequences that explain the level."),
        }

    def __init__(self, *args, baseline=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # The baseline the event belongs to is known from the address : it is
        # not asked, and the event is checked against it before it is saved.
        if baseline is not None and not self.instance.baseline_id:
            self.instance.baseline = baseline
        self.baseline = self.instance.baseline if self.instance.baseline_id else baseline
        if self.baseline is not None:
            # A feared event is about one of the essential assets of the study;
            # the one an event already names stays, whatever the study holds.
            studied = Q(pk__in=self.baseline.essential_assets.values("pk"))
            if self.instance.essential_asset_id:
                studied |= Q(pk=self.instance.essential_asset_id)
            asset = self.fields["essential_asset"]
            asset.queryset = asset.queryset.filter(studied)
        # The gravity is picked on the impact scale of the criteria of the
        # assessment, each level by its name, where a bare number was typed.
        if "gravity_level" in self.fields:
            criteria = getattr(self.baseline.assessment, "risk_criteria", None) if self.baseline is not None else None
            self.fields["gravity_level"] = named_level_field(
                self.fields["gravity_level"], get_scale_choices("impact", criteria), self.instance.gravity_level,
            )
        if user is not None:
            restrict_form_relations(self, user)

    def clean(self):
        cleaned = super().clean()
        asset, criterion = cleaned.get("essential_asset"), cleaned.get("dic_criterion")
        if self.baseline is not None and asset and criterion:
            # The baseline is not a field of the form, so the form does not
            # check the constraint that names it : the database refused the
            # row, and the page answered with a server error.
            twin = FearedEvent.objects.filter(
                baseline=self.baseline, essential_asset=asset, dic_criterion=criterion,
            ).exclude(pk=self.instance.pk).first()
            if twin is not None:
                self.add_error(
                    "dic_criterion",
                    _("%(reference)s is already the feared event of this essential asset for this criterion : edit it.")
                    % {"reference": twin.reference},
                )
        return cleaned

    def save(self, commit=True):
        if self.instance._state.adding and self.baseline is not None and not self.instance.order:
            self.instance.order = next_rank(self.baseline.feared_events.all())
        return super().save(commit=commit)


class FearedEventCreateForm(CreationFormMixin, FearedEventForm):
    """A new feared event : the asset it harms, the criterion, its name and its gravity.

    Its description and the justification of its gravity are written when it
    is edited.
    """

    owner_field = None
    steps = [
        Step(_("Feared event"), "exclamation-triangle",
             [["essential_asset", "dic_criterion"], "name", "gravity_level"]),
    ]

    class Meta(FearedEventForm.Meta):
        fields = ["essential_asset", "dic_criterion", "name", "gravity_level"]


class BaselineGapForm(SteppedFormMixin, forms.ModelForm):
    """A gap against the security baseline : a row of workshop 1, on one screen."""

    steps = [
        Step(_("Baseline gap"), "bug",
             [["reference_source", "severity"], "description", "linked_requirement",
              "affected_support_assets", "recommended_remediation"],
             key="gap"),
    ]

    class Meta:
        model = BaselineGap
        fields = [
            "reference_source",
            "severity",
            "description",
            "linked_requirement",
            "affected_support_assets",
            "recommended_remediation",
        ]
        widgets = {
            "reference_source": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "severity": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "linked_requirement": forms.Select(attrs=SELECT_ATTRS),
            "affected_support_assets": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "recommended_remediation": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
        help_texts = {
            "reference_source": _('The rule of the security baseline that is not met, for example '
                                  '"ISO 27002, control 8.22" or "ANSSI hygiene guide, rule 12".'),
            "severity": _("How much the gap exposes the organisation."),
            "description": _('The gap as it stands today, for example "The office network and the '
                             'industrial network are not separated".'),
            "linked_requirement": _("The requirement that is not met, picked in the baseline references."),
            "affected_support_assets": _("Among the support assets of the security baseline."),
            "recommended_remediation": _("The work that would close the gap."),
        }

    def __init__(self, *args, baseline=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if baseline is not None and not self.instance.baseline_id:
            self.instance.baseline = baseline
        self.baseline = self.instance.baseline if self.instance.baseline_id else baseline
        if self.baseline is not None:
            # A requirement is picked in the frameworks of the baseline, an
            # asset among its support assets : the lists stay short and say
            # what the gap is measured against. What the gap holds stays.
            requirement = self.fields.get("linked_requirement")
            if requirement is not None:
                offered = Q(framework__in=self.baseline.baseline_references.values("pk"))
                if self.instance.linked_requirement_id:
                    offered |= Q(pk=self.instance.linked_requirement_id)
                requirement.queryset = requirement.queryset.filter(offered).select_related("framework")
            assets = self.fields.get("affected_support_assets")
            if assets is not None:
                offered = Q(pk__in=self.baseline.support_assets.values("pk"))
                if self.instance.pk:
                    offered |= Q(pk__in=self.instance.affected_support_assets.values("pk"))
                assets.queryset = assets.queryset.filter(offered)
        if user is not None:
            restrict_form_relations(self, user)

    def save(self, commit=True):
        if self.instance._state.adding and self.baseline is not None and not self.instance.order:
            self.instance.order = next_rank(self.baseline.gaps.all())
        return super().save(commit=commit)


class BaselineGapCreateForm(CreationFormMixin, BaselineGapForm):
    """A new baseline gap : the rule that is not met, what the gap is and how severe.

    The requirement, the support assets and the remediation are filled in
    when it is edited.
    """

    owner_field = None
    # The severity is judged : the default of the model is not saved for the reader.
    decisions = ("severity",)
    steps = [
        Step(_("Baseline gap"), "bug", [["reference_source", "severity"], "description"]),
    ]

    class Meta(BaselineGapForm.Meta):
        fields = ["reference_source", "severity", "description"]


class WorkshopRejectForm(forms.Form):
    """Form for rejecting a workshop with a mandatory reason."""

    rejection_reason = forms.CharField(
        label=_("Rejection reason"),
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control", "required": "required"}),
        required=True,
    )


# ── Workshop W2 forms ────────────────────────────────────────


class RiskSourceForm(forms.ModelForm):
    class Meta:
        model = RiskSource
        fields = [
            "name", "description", "category",
            "motivation_level", "motivation_description",
            "resources_level", "activity_level",
            "is_retained", "retention_justification",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "motivation_level": forms.Select(attrs={"class": "form-select"}),
            "motivation_description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "resources_level": forms.Select(attrs={"class": "form-select"}),
            "activity_level": forms.Select(attrs={"class": "form-select"}),
            "is_retained": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "retention_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class TargetedObjectiveForm(forms.ModelForm):
    class Meta:
        model = TargetedObjective
        fields = [
            "name", "description", "category",
            "targeted_essential_assets", "targeted_feared_events",
            "is_retained", "order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "targeted_essential_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "targeted_feared_events": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "is_retained": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class RiskSourceObjectivePairForm(forms.ModelForm):
    class Meta:
        model = RiskSourceObjectivePair
        fields = [
            "risk_source", "targeted_objective",
            "relevance", "relevance_justification",
            "is_retained", "retention_justification",
        ]
        widgets = {
            "risk_source": forms.Select(attrs={"class": "form-select"}),
            "targeted_objective": forms.Select(attrs={"class": "form-select"}),
            "relevance": forms.Select(attrs={"class": "form-select"}),
            "relevance_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "is_retained": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "retention_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


# ── Workshop W3 forms ────────────────────────────────────────


class EcosystemStakeholderForm(forms.ModelForm):
    class Meta:
        model = EcosystemStakeholder
        fields = [
            "name", "description", "category",
            "stakeholder", "supplier",
            "dependency", "penetration", "maturity", "trust",
            "accessible_support_assets",
            "is_attack_vector", "attack_vector_justification",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "stakeholder": forms.Select(attrs={"class": "form-select"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "dependency": forms.Select(attrs={"class": "form-select"}),
            "penetration": forms.Select(attrs={"class": "form-select"}),
            "maturity": forms.Select(attrs={"class": "form-select"}),
            "trust": forms.Select(attrs={"class": "form-select"}),
            "accessible_support_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "is_attack_vector": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "attack_vector_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class StrategicScenarioForm(forms.ModelForm):
    class Meta:
        model = StrategicScenario
        fields = [
            "name", "description", "sr_ov_pair",
            "targeted_feared_events",
            "gravity_level", "gravity_justification",
            "likelihood_level", "likelihood_justification",
            "existing_security_measures",
            "is_retained", "retention_justification",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "sr_ov_pair": forms.Select(attrs={"class": "form-select"}),
            "targeted_feared_events": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "gravity_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "gravity_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "likelihood_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "likelihood_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "existing_security_measures": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "is_retained": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "retention_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class AttackPathStepForm(forms.ModelForm):
    class Meta:
        model = AttackPathStep
        fields = ["order", "stakeholder", "description", "action_type", "difficulty"]
        widgets = {
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "stakeholder": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "action_type": forms.Select(attrs={"class": "form-select"}),
            "difficulty": forms.Select(attrs={"class": "form-select"}),
        }


# ── Workshop W4 forms ────────────────────────────────────────


class OperationalScenarioForm(forms.ModelForm):
    class Meta:
        model = OperationalScenario
        fields = [
            "strategic_scenario", "name", "description",
            "targeted_support_assets",
            "gravity_level", "gravity_inherited", "gravity_override_justification",
            "likelihood_v", "likelihood_justification",
            "existing_controls", "mitre_version",
        ]
        widgets = {
            "strategic_scenario": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "targeted_support_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "gravity_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "gravity_inherited": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "gravity_override_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "likelihood_v": forms.Select(attrs={"class": "form-select"}),
            "likelihood_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "existing_controls": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "mitre_version": forms.TextInput(attrs={"class": "form-control"}),
        }


class AttackTechniqueForm(forms.ModelForm):
    class Meta:
        model = AttackTechnique
        fields = [
            "order", "mitre_technique", "custom_name", "description",
            "targeted_support_asset", "difficulty", "detection_difficulty",
        ]
        widgets = {
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "mitre_technique": forms.Select(attrs={"class": "form-select"}),
            "custom_name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "targeted_support_asset": forms.Select(attrs={"class": "form-select"}),
            "difficulty": forms.Select(attrs={"class": "form-select"}),
            "detection_difficulty": forms.Select(attrs={"class": "form-select"}),
        }


# ── Workshop W5 forms ────────────────────────────────────────


class EbiosSummaryForm(forms.ModelForm):
    class Meta:
        model = EbiosSummary
        fields = [
            "residual_risk_strategy", "monitoring_plan", "pacs_summary",
            "next_strategic_cycle_date", "next_operational_cycle_date",
        ]
        widgets = {
            "residual_risk_strategy": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "monitoring_plan": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "pacs_summary": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "next_strategic_cycle_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "next_operational_cycle_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class PACSMeasureForm(forms.ModelForm):
    class Meta:
        model = PACSMeasure
        fields = [
            "name", "description", "measure_type",
            "linked_treatment_plans", "linked_baseline_gaps", "linked_requirements",
            "owner", "start_date", "target_date", "completion_date",
            "cost_estimate", "expected_gain",
            "priority", "progress_percentage", "order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "measure_type": forms.Select(attrs={"class": "form-select"}),
            "linked_treatment_plans": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "linked_baseline_gaps": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "linked_requirements": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "owner": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "target_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "completion_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "cost_estimate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "expected_gain": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "progress_percentage": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The forms of the EBIOS RM workshops.

The records of a workshop are rows of its page : they are added and edited
in the side panel, from that page, and go back to it. A row is created with
the few fields that make it exist (``docs/sdk/usability-standard.md``, rule
F1), the rest is filled in when it is edited. The record a row hangs under
(the security baseline, the study) is known from the address : it is never
asked (rule F2).

The forms of workshops 1 to 5 follow the standard; the study framework of
workshop 0 is the last to be brought to it.
"""

from html import unescape

from django import forms
from django.db.models import Max, Q
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from core.lifecycle import linkable_or_linked
from core.modal_forms import CreationFormMixin, Step, SteppedFormMixin, pick_among_active_people
from core.scoping import restrict_form_relations
from risks.forms import CHECKBOX_ATTRS, FORM_WIDGET_ATTRS, SELECT_ATTRS, get_scale_choices
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


def is_filled_text(value):
    """Whether a text typed in the editor says something (an emptied editor leaves markup behind)."""
    return bool(unescape(strip_tags(value or "")).replace("\xa0", " ").strip())


def read_unrated_as_not_assessed(form, names):
    """The empty choice of a level reads *Not assessed* (rule F8), on each field of ``names``."""
    for name in names:
        field = form.fields.get(name)
        if field is None:
            continue
        choices = list(field.choices)
        if choices and choices[0][0] in ("", None):
            field.choices = [(choices[0][0], _("Not assessed")), *choices[1:]]


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
            held = None if self.instance._state.adding else getattr(self.instance, name).all()
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
                if not self.instance._state.adding:
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


class RiskSourceForm(SteppedFormMixin, forms.ModelForm):
    """A risk source of a study : a row of workshop 2, on one screen."""

    RATINGS = ("motivation_level", "resources_level", "activity_level")

    steps = [
        Step(pgettext_lazy("EBIOS RM", "Risk source"), "people",
             [["name", "category"], "description",
              ["motivation_level", "resources_level", "activity_level"], "motivation_description",
              "is_retained", "retention_justification"],
             key="source"),
    ]

    class Meta:
        model = RiskSource
        fields = [
            "name", "category", "description",
            "motivation_level", "resources_level", "activity_level", "motivation_description",
            "is_retained", "retention_justification",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "motivation_level": forms.Select(attrs=SELECT_ATTRS),
            "resources_level": forms.Select(attrs=SELECT_ATTRS),
            "activity_level": forms.Select(attrs=SELECT_ATTRS),
            "motivation_description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "is_retained": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "retention_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. The three ratings take theirs from the model.
        help_texts = {
            "name": _('For example "A ransomware group" or "A dismissed employee".'),
            "description": _("The source in a few words, and what is known of it."),
            "motivation_description": _('What the source has to gain, for example "A ransom paid quickly".'),
            "is_retained": _("Untick to set the source aside : the study goes on without it."),
            "retention_justification": _("The reason the source is retained, or set aside."),
        }

    def __init__(self, *args, assessment=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # The study the source belongs to is known from the address.
        if assessment is not None and not self.instance.assessment_id:
            self.instance.assessment = assessment
        read_unrated_as_not_assessed(self, self.RATINGS)
        if user is not None:
            restrict_form_relations(self, user)


class RiskSourceCreateForm(CreationFormMixin, RiskSourceForm):
    """A new risk source : its name, its category and its three ratings.

    A rating may wait : it reads *Not assessed* until it is given.
    """

    owner_field = None
    # The category says what kind of attacker it is : "Other" is not chosen for the reader.
    decisions = ("category",)
    steps = [
        Step(pgettext_lazy("EBIOS RM", "Risk source"), "people",
             [["name", "category"], ["motivation_level", "resources_level", "activity_level"]]),
    ]

    class Meta(RiskSourceForm.Meta):
        fields = ["name", "category", "motivation_level", "resources_level", "activity_level"]


class TargetedObjectiveForm(SteppedFormMixin, forms.ModelForm):
    """A targeted objective of a risk source : a row of workshop 2, on one screen."""

    steps = [
        Step(_("Targeted objective"), "bullseye",
             [["name", "category"], "description", "targeted_feared_events", "targeted_essential_assets",
              "is_retained"],
             key="objective"),
    ]

    class Meta:
        model = TargetedObjective
        fields = [
            "name", "category", "description",
            "targeted_feared_events", "targeted_essential_assets",
            "is_retained",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "targeted_feared_events": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "targeted_essential_assets": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "is_retained": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
        }
        help_texts = {
            "name": _('The goal the source pursues, for example "Extort money by stopping production".'),
            "category": _("Lucrative for money, strategic for an advantage or espionage, ideological for a cause, "
                          "ludic for the challenge."),
            "targeted_feared_events": _("The feared events of workshop 1 the objective would cause."),
            "targeted_essential_assets": _("Among the essential assets of the security baseline."),
            "is_retained": _("Untick to set the objective aside : the study goes on without it."),
        }

    def __init__(self, *args, risk_source=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # The risk source the objective belongs to is known from the address.
        if risk_source is not None and not self.instance.risk_source_id:
            self.instance.risk_source = risk_source
        self.risk_source = self.instance.risk_source if self.instance.risk_source_id else risk_source
        baseline = None
        if self.risk_source is not None:
            baseline = getattr(self.risk_source.assessment, "ebios_security_baseline", None)
        if baseline is not None:
            # An objective targets what the study holds : its feared events and
            # its essential assets, not those of every study. What the
            # objective already targets stays.
            events = self.fields.get("targeted_feared_events")
            if events is not None:
                offered = Q(baseline=baseline)
                if not self.instance._state.adding:
                    offered |= Q(pk__in=self.instance.targeted_feared_events.values("pk"))
                events.queryset = events.queryset.filter(offered)
            assets = self.fields.get("targeted_essential_assets")
            if assets is not None:
                offered = Q(pk__in=baseline.essential_assets.values("pk"))
                if not self.instance._state.adding:
                    offered |= Q(pk__in=self.instance.targeted_essential_assets.values("pk"))
                assets.queryset = assets.queryset.filter(offered)
        if user is not None:
            restrict_form_relations(self, user)

    def save(self, commit=True):
        if self.instance._state.adding and self.risk_source is not None and not self.instance.order:
            self.instance.order = next_rank(self.risk_source.targeted_objectives.all())
        return super().save(commit=commit)


class TargetedObjectiveCreateForm(CreationFormMixin, TargetedObjectiveForm):
    """A new targeted objective : its name, its category and the feared events it would cause."""

    owner_field = None
    decisions = ("category",)
    steps = [
        Step(_("Targeted objective"), "bullseye", [["name", "category"], "targeted_feared_events"]),
    ]

    class Meta(TargetedObjectiveForm.Meta):
        fields = ["name", "category", "targeted_feared_events"]


class RiskSourceObjectivePairForm(SteppedFormMixin, forms.ModelForm):
    """A risk source and one of its targeted objectives, judged together : a row of workshop 2.

    The risk source is not asked : a targeted objective belongs to one, so
    choosing the objective names the pair.
    """

    steps = [
        Step(_("Pair"), "diagram-2",
             ["targeted_objective", "relevance", "relevance_justification",
              "is_retained", "retention_justification"],
             key="pair"),
    ]

    class Meta:
        model = RiskSourceObjectivePair
        fields = [
            "targeted_objective",
            "relevance", "relevance_justification",
            "is_retained", "retention_justification",
        ]
        widgets = {
            "targeted_objective": forms.Select(attrs=SELECT_ATTRS),
            "relevance": forms.Select(attrs=SELECT_ATTRS),
            "relevance_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "is_retained": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "retention_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
        help_texts = {
            "targeted_objective": _("Each objective is listed under its risk source : the pair is that source "
                                    "and that objective."),
            "relevance": _("How credible it is that this source pursues this objective against the organisation."),
            "relevance_justification": _("The facts that make the pair credible, or not."),
            "is_retained": _("A retained pair is studied in the strategic scenarios of workshop 3."),
            "retention_justification": _("The reason the pair is retained, or set aside."),
        }

    def __init__(self, *args, assessment=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assessment is not None and not self.instance.assessment_id:
            self.instance.assessment = assessment
        self.assessment = self.instance.assessment if self.instance.assessment_id else assessment
        objective = self.fields.get("targeted_objective")
        # A new row already has its identifier : what tells a creation from an
        # edition is whether it was ever saved.
        creating = self.instance._state.adding
        if objective is not None:
            if not creating:
                # The pair is its objective : an existing one keeps it.
                objective.queryset = objective.queryset.filter(pk=self.instance.targeted_objective_id)
                objective.disabled = True
                objective.help_text = ""
            elif self.assessment is not None:
                # The objectives of the study that are not paired yet, each
                # under its risk source.
                paired = RiskSourceObjectivePair.objects.filter(assessment=self.assessment)
                objective.queryset = (
                    objective.queryset.filter(risk_source__assessment=self.assessment)
                    .exclude(pk__in=paired.values("targeted_objective"))
                    .select_related("risk_source")
                    .order_by("risk_source__reference", "order", "reference")
                )
        if user is not None:
            restrict_form_relations(self, user)
        if objective is not None and creating:
            objective.choices = self._objectives_by_source(objective)

    @staticmethod
    def _objectives_by_source(field):
        """The choices of ``field`` : the objectives it offers, grouped under their risk source."""
        groups = {}
        for objective in field.queryset:
            groups.setdefault(str(objective.risk_source), []).append((objective.pk, str(objective)))
        blank = [("", pgettext_lazy("empty select option", "Choose…"))]
        return blank + [(source, objectives) for source, objectives in groups.items()]

    def clean(self):
        cleaned = super().clean()
        # The objective names its risk source and its study : the pair follows it.
        if cleaned.get("targeted_objective") is not None:
            self.instance.targeted_objective = cleaned["targeted_objective"]
            self.instance.risk_source = cleaned["targeted_objective"].risk_source
            if not self.instance.assessment_id:
                self.instance.assessment_id = self.instance.risk_source.assessment_id
        return cleaned


class RiskSourceObjectivePairCreateForm(CreationFormMixin, RiskSourceObjectivePairForm):
    """A new pair : the targeted objective (its risk source follows) and how relevant the pair is."""

    owner_field = None
    # The relevance is the judgment the pair exists for : "Medium" is not chosen for the reader.
    decisions = ("relevance",)
    steps = [
        Step(_("Pair"), "diagram-2", ["targeted_objective", "relevance"]),
    ]

    class Meta(RiskSourceObjectivePairForm.Meta):
        fields = ["targeted_objective", "relevance"]


# ── Workshop W3 forms ────────────────────────────────────────


class EcosystemStakeholderForm(SteppedFormMixin, forms.ModelForm):
    """A stakeholder of the ecosystem of a study : a row of workshop 3."""

    RATINGS = ("dependency", "penetration", "maturity", "trust")

    # Two sections : the four ratings are a judgment of their own, and a
    # dozen fields on one screen would bury them.
    steps = [
        Step(_("Ecosystem stakeholder"), "diagram-3",
             [["name", "category"], "description", ["stakeholder", "supplier"], "accessible_support_assets"],
             key="stakeholder"),
        Step(_("Threat level"), "speedometer2",
             ["dependency", "penetration", "maturity", "trust", "is_attack_vector", "attack_vector_justification"],
             key="threat",
             intro=_("Dependency and penetration say how exposed you are to this stakeholder, cyber maturity "
                     "and trust how reliable it is. Their ratio is its threat level, which places it in a zone.")),
    ]

    class Meta:
        model = EcosystemStakeholder
        fields = [
            "name", "category", "description",
            "stakeholder", "supplier", "accessible_support_assets",
            "dependency", "penetration", "maturity", "trust",
            "is_attack_vector", "attack_vector_justification",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "stakeholder": forms.Select(attrs=SELECT_ATTRS),
            "supplier": forms.Select(attrs=SELECT_ATTRS),
            "accessible_support_assets": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "dependency": forms.Select(attrs=SELECT_ATTRS),
            "penetration": forms.Select(attrs=SELECT_ATTRS),
            "maturity": forms.Select(attrs=SELECT_ATTRS),
            "trust": forms.Select(attrs=SELECT_ATTRS),
            "is_attack_vector": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "attack_vector_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
        # The four ratings and the two links take their helper from the model.
        help_texts = {
            "name": _('For example "Our hosting provider" or "The maintenance subcontractor".'),
            "description": _("The stakeholder in a few words, and the service it gives or receives."),
            "accessible_support_assets": _("Among the support assets of the security baseline."),
            "is_attack_vector": _("Tick when an attacker could pass through this stakeholder to reach you."),
            "attack_vector_justification": _("The access or the weakness an attacker would use."),
        }

    def __init__(self, *args, assessment=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assessment is not None and not self.instance.assessment_id:
            self.instance.assessment = assessment
        self.assessment = self.instance.assessment if self.instance.assessment_id else assessment
        creating = self.instance._state.adding
        # A new link targets a record that can be linked; a link already
        # there stays, whatever became of the record since.
        for name in ("stakeholder", "supplier"):
            field = self.fields.get(name)
            if field is None:
                continue
            held_id = getattr(self.instance, f"{name}_id", None)
            held = None if creating or not held_id else field.queryset.model.objects.filter(pk=held_id)
            field.queryset = linkable_or_linked(field.queryset, held)
        assets = self.fields.get("accessible_support_assets")
        baseline = getattr(self.assessment, "ebios_security_baseline", None) if self.assessment is not None else None
        if assets is not None and baseline is not None:
            offered = Q(pk__in=baseline.support_assets.values("pk"))
            if not creating:
                offered |= Q(pk__in=self.instance.accessible_support_assets.values("pk"))
            assets.queryset = assets.queryset.filter(offered)
        read_unrated_as_not_assessed(self, self.RATINGS)
        if user is not None:
            restrict_form_relations(self, user)


class EcosystemStakeholderCreateForm(CreationFormMixin, EcosystemStakeholderForm):
    """A new ecosystem stakeholder : its name, its category and its four ratings.

    A rating may wait : it reads *Not assessed* until it is given.
    """

    owner_field = None
    decisions = ("category",)
    steps = [
        Step(_("Ecosystem stakeholder"), "diagram-3",
             [["name", "category"], "dependency", "penetration", "maturity", "trust"]),
    ]

    class Meta(EcosystemStakeholderForm.Meta):
        fields = ["name", "category", "dependency", "penetration", "maturity", "trust"]


class StrategicScenarioForm(SteppedFormMixin, forms.ModelForm):
    """A strategic scenario of a study : a row of workshop 3."""

    steps = [
        Step(_("Strategic scenario"), "signpost-2",
             ["name", "sr_ov_pair", "targeted_feared_events", "description", "existing_security_measures"],
             key="scenario"),
        Step(_("Gravity and likelihood"), "speedometer2",
             [["gravity_level", "likelihood_level"], "gravity_justification", "likelihood_justification",
              "is_retained", "retention_justification"],
             key="rating",
             intro=_("Gravity and likelihood give the risk level of the scenario, on the matrix of the risk criteria.")),
    ]

    class Meta:
        model = StrategicScenario
        fields = [
            "name", "sr_ov_pair", "targeted_feared_events", "description", "existing_security_measures",
            "gravity_level", "likelihood_level", "gravity_justification", "likelihood_justification",
            "is_retained", "retention_justification",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "sr_ov_pair": forms.Select(attrs=SELECT_ATTRS),
            "targeted_feared_events": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "existing_security_measures": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "gravity_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "likelihood_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "is_retained": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "retention_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
        help_texts = {
            "name": _('For example "A criminal group stops production through the maintenance provider".'),
            "sr_ov_pair": _("Among the pairs retained in workshop 2 : the attacker and the goal of the scenario."),
            "targeted_feared_events": _("The feared events of workshop 1 the scenario leads to."),
            "description": _("The path of the attack in a few sentences, from the risk source to the feared event."),
            "existing_security_measures": _("The measures already in place that stand in the way of the scenario."),
            "gravity_level": _("Usually the gravity of the most serious feared event the scenario leads to."),
            "likelihood_level": _("The chances that the scenario succeeds, on the likelihood scale of the risk criteria."),
            "gravity_justification": "",
            "likelihood_justification": "",
            "is_retained": _("A retained scenario is detailed in the operational scenarios of workshop 4."),
            "retention_justification": _("The reason the scenario is retained, or set aside."),
        }

    def __init__(self, *args, assessment=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assessment is not None and not self.instance.assessment_id:
            self.instance.assessment = assessment
        self.assessment = self.instance.assessment if self.instance.assessment_id else assessment
        creating = self.instance._state.adding
        if self.assessment is not None:
            # A scenario is built on a pair retained in workshop 2 and leads to
            # feared events of workshop 1, of its own study. The pair and the
            # events it already names stay.
            pair = self.fields.get("sr_ov_pair")
            if pair is not None:
                offered = Q(assessment=self.assessment, is_retained=True)
                if not creating and self.instance.sr_ov_pair_id:
                    offered |= Q(pk=self.instance.sr_ov_pair_id)
                pair.queryset = pair.queryset.filter(offered).select_related("risk_source", "targeted_objective")
            events = self.fields.get("targeted_feared_events")
            if events is not None:
                offered = Q(baseline__assessment=self.assessment)
                if not creating:
                    offered |= Q(pk__in=self.instance.targeted_feared_events.values("pk"))
                events.queryset = events.queryset.filter(offered)
        # Each level is picked by its name on the scale of the criteria of
        # the assessment, where a bare number was typed.
        criteria = getattr(self.assessment, "risk_criteria", None) if self.assessment is not None else None
        for name, scale in (("gravity_level", "impact"), ("likelihood_level", "likelihood")):
            if name in self.fields:
                self.fields[name] = named_level_field(
                    self.fields[name], get_scale_choices(scale, criteria), getattr(self.instance, name),
                )
        if user is not None:
            restrict_form_relations(self, user)


class StrategicScenarioCreateForm(CreationFormMixin, StrategicScenarioForm):
    """A new strategic scenario : its name, its pair, the feared events it leads to and its two levels."""

    owner_field = None
    steps = [
        Step(_("Strategic scenario"), "signpost-2",
             ["name", "sr_ov_pair", "targeted_feared_events", ["gravity_level", "likelihood_level"]]),
    ]

    class Meta(StrategicScenarioForm.Meta):
        fields = ["name", "sr_ov_pair", "targeted_feared_events", "gravity_level", "likelihood_level"]


class AttackPathStepForm(SteppedFormMixin, forms.ModelForm):
    """A step of the attack path of a strategic scenario : a row of workshop 3, on one screen."""

    steps = [
        Step(_("Attack path step"), "arrow-right-circle",
             [["action_type", "difficulty"], "stakeholder", "description", "order"],
             key="step"),
    ]

    class Meta:
        model = AttackPathStep
        fields = ["action_type", "difficulty", "stakeholder", "description", "order"]
        widgets = {
            "action_type": forms.Select(attrs=SELECT_ATTRS),
            "difficulty": forms.Select(attrs=SELECT_ATTRS),
            "stakeholder": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "order": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 1}),
        }
        help_texts = {
            "action_type": "",
            "difficulty": _("The effort this step asks of the attacker."),
            "stakeholder": _("The ecosystem stakeholder the attacker passes through at this step, when there is one."),
            "description": _('The move of the attacker, for example "Steals the credentials of a maintenance technician".'),
            "order": _("The place of the step in the attack path : the lowest number comes first."),
        }

    def __init__(self, *args, scenario=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if scenario is not None and not self.instance.scenario_id:
            self.instance.scenario = scenario
        self.scenario = self.instance.scenario if self.instance.scenario_id else scenario
        stakeholder = self.fields.get("stakeholder")
        if stakeholder is not None and self.scenario is not None:
            # A step passes through a stakeholder of the ecosystem of its own study.
            offered = Q(assessment=self.scenario.assessment_id)
            if not self.instance._state.adding and self.instance.stakeholder_id:
                offered |= Q(pk=self.instance.stakeholder_id)
            stakeholder.queryset = stakeholder.queryset.filter(offered)
        if user is not None:
            restrict_form_relations(self, user)

    def clean_order(self):
        order = self.cleaned_data.get("order")
        if order is None or self.scenario is None:
            return order
        # The scenario is not a field of the form, so the form does not check
        # the constraint that names it : two steps of one rank were a server error.
        twin = AttackPathStep.objects.filter(scenario=self.scenario, order=order).exclude(pk=self.instance.pk).first()
        if twin is not None:
            raise forms.ValidationError(
                _("Step %(order)s of this attack path already exists : choose another number.") % {"order": order},
            )
        return order

    def save(self, commit=True):
        self.instance.come_last_when_unranked()
        return super().save(commit=commit)


class AttackPathStepCreateForm(CreationFormMixin, AttackPathStepForm):
    """A new step : what the attacker does, how hard it is and through whom. It comes last."""

    owner_field = None
    decisions = ("action_type",)
    steps = [
        Step(_("Attack path step"), "arrow-right-circle", [["action_type", "difficulty"], "stakeholder", "description"]),
    ]

    class Meta(AttackPathStepForm.Meta):
        fields = ["action_type", "difficulty", "stakeholder", "description"]


# ── Workshop W4 forms ────────────────────────────────────────


class OperationalScenarioForm(SteppedFormMixin, forms.ModelForm):
    """An operational scenario of a study : a row of workshop 4."""

    steps = [
        Step(_("Operational scenario"), "bullseye",
             ["strategic_scenario", "name", "targeted_support_assets", "description", "existing_controls"],
             key="scenario"),
        Step(_("Likelihood and gravity"), "speedometer2",
             ["likelihood_v", "likelihood_justification",
              "gravity_inherited", "gravity_level", "gravity_override_justification"],
             key="rating",
             intro=_("The likelihood is judged on the techniques of the scenario. The gravity is the one of "
                     "its strategic scenario, unless you give it its own.")),
    ]

    class Meta:
        model = OperationalScenario
        fields = [
            "strategic_scenario", "name", "targeted_support_assets", "description", "existing_controls",
            "likelihood_v", "likelihood_justification",
            "gravity_inherited", "gravity_level", "gravity_override_justification",
        ]
        widgets = {
            "strategic_scenario": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "targeted_support_assets": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "existing_controls": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "likelihood_v": forms.Select(attrs=SELECT_ATTRS),
            "likelihood_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "gravity_inherited": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "gravity_override_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
        # The likelihood and the two gravity fields take their helper from the model.
        help_texts = {
            "strategic_scenario": _("Among the strategic scenarios retained in workshop 3 : the one this scenario details."),
            "name": _('For example "Ransomware deployed through the maintenance access".'),
            "targeted_support_assets": _("Among the support assets of the security baseline."),
            "description": _("The attack in a few sentences, as it would unfold on your systems."),
            "existing_controls": _("The measures already in place that stand in the way of the attack."),
            "likelihood_justification": "",
            "gravity_override_justification": _("Required when the scenario has a gravity of its own."),
        }

    def __init__(self, *args, assessment=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assessment is not None and not self.instance.assessment_id:
            self.instance.assessment = assessment
        self.assessment = self.instance.assessment if self.instance.assessment_id else assessment
        creating = self.instance._state.adding
        if self.assessment is not None:
            # A scenario details a strategic scenario retained in workshop 3
            # (rule RE-09) and aims at support assets of the study. What it
            # already names stays.
            parent = self.fields.get("strategic_scenario")
            if parent is not None:
                offered = Q(assessment=self.assessment, is_retained=True)
                if not creating and self.instance.strategic_scenario_id:
                    offered |= Q(pk=self.instance.strategic_scenario_id)
                parent.queryset = parent.queryset.filter(offered)
            assets = self.fields.get("targeted_support_assets")
            baseline = getattr(self.assessment, "ebios_security_baseline", None)
            if assets is not None and baseline is not None:
                offered = Q(pk__in=baseline.support_assets.values("pk"))
                if not creating:
                    offered |= Q(pk__in=self.instance.targeted_support_assets.values("pk"))
                assets.queryset = assets.queryset.filter(offered)
        read_unrated_as_not_assessed(self, ("likelihood_v",))
        if "gravity_level" in self.fields:
            criteria = getattr(self.assessment, "risk_criteria", None) if self.assessment is not None else None
            self.fields["gravity_level"] = named_level_field(
                self.fields["gravity_level"], get_scale_choices("impact", criteria), self.instance.gravity_level,
            )
        if user is not None:
            restrict_form_relations(self, user)

    def clean(self):
        cleaned = super().clean()
        # A gravity of its own is a decision, and says why (rule RE-10).
        if "gravity_inherited" in cleaned and not cleaned.get("gravity_inherited"):
            if "gravity_level" in self.fields and cleaned.get("gravity_level") is None:
                self.add_error("gravity_level", _("Choose the gravity of the scenario, or tick the box to keep the one of its strategic scenario."))
            justification = cleaned.get("gravity_override_justification") or ""
            if "gravity_override_justification" in self.fields and not is_filled_text(justification):
                self.add_error("gravity_override_justification", _("Say why the scenario has a gravity of its own."))
        return cleaned


class OperationalScenarioCreateForm(CreationFormMixin, OperationalScenarioForm):
    """A new operational scenario : the strategic scenario it details, its name, its targets and its likelihood.

    Its gravity is the one of its strategic scenario : it is not asked.
    """

    owner_field = None
    steps = [
        Step(_("Operational scenario"), "bullseye",
             ["strategic_scenario", "name", "targeted_support_assets", "likelihood_v"]),
    ]

    class Meta(OperationalScenarioForm.Meta):
        fields = ["strategic_scenario", "name", "targeted_support_assets", "likelihood_v"]


class AttackTechniqueForm(SteppedFormMixin, forms.ModelForm):
    """A technique of an operational scenario : a row of workshop 4, on one screen."""

    steps = [
        Step(_("Attack technique"), "tools",
             ["mitre_technique", "custom_name", "description", "targeted_support_asset",
              ["difficulty", "detection_difficulty"], "order"],
             key="technique"),
    ]

    class Meta:
        model = AttackTechnique
        fields = [
            "mitre_technique", "custom_name", "description", "targeted_support_asset",
            "difficulty", "detection_difficulty", "order",
        ]
        widgets = {
            "mitre_technique": forms.Select(attrs=SELECT_ATTRS),
            "custom_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "targeted_support_asset": forms.Select(attrs=SELECT_ATTRS),
            "difficulty": forms.Select(attrs=SELECT_ATTRS),
            "detection_difficulty": forms.Select(attrs=SELECT_ATTRS),
            "order": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 1}),
        }
        # The custom name takes its helper from the model.
        help_texts = {
            "mitre_technique": _("The techniques of the MITRE ATT&CK catalogue, listed under their tactic. "
                                 "Leave empty and fill in a custom name when none fits."),
            "description": _('The move as it would happen here, for example "A booby-trapped invoice is sent to the accountants".'),
            "targeted_support_asset": _("Among the support assets the operational scenario aims at."),
            "difficulty": _("The effort the technique asks of the attacker."),
            "detection_difficulty": _("The effort it would take you to notice the technique at work."),
            "order": _("The place of the technique in the scenario : the lowest number comes first."),
        }

    def __init__(self, *args, scenario=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if scenario is not None and not self.instance.scenario_id:
            self.instance.scenario = scenario
        self.scenario = self.instance.scenario if self.instance.scenario_id else scenario
        creating = self.instance._state.adding
        technique = self.fields.get("mitre_technique")
        if technique is not None:
            # The active techniques of the catalogue, and the one already chosen.
            offered = Q(is_active=True)
            if not creating and self.instance.mitre_technique_id:
                offered |= Q(pk=self.instance.mitre_technique_id)
            technique.queryset = technique.queryset.filter(offered).order_by("tactic", "mitre_id")
            technique.choices = self._techniques_by_tactic(technique)
        asset = self.fields.get("targeted_support_asset")
        if asset is not None and self.scenario is not None:
            # The support assets the scenario aims at, or those of the study
            # while it names none.
            targeted = self.scenario.targeted_support_assets.values("pk")
            baseline = getattr(self.scenario.assessment, "ebios_security_baseline", None)
            offered = Q(pk__in=targeted)
            if not self.scenario.targeted_support_assets.exists() and baseline is not None:
                offered = Q(pk__in=baseline.support_assets.values("pk"))
            if not creating and self.instance.targeted_support_asset_id:
                offered |= Q(pk=self.instance.targeted_support_asset_id)
            asset.queryset = asset.queryset.filter(offered)
        if user is not None:
            restrict_form_relations(self, user)

    @staticmethod
    def _techniques_by_tactic(field):
        """The choices of ``field`` : the techniques it offers, grouped under their tactic."""
        groups = {}
        for technique in field.queryset:
            groups.setdefault(str(technique.get_tactic_display()), []).append((technique.pk, str(technique)))
        blank = [("", pgettext_lazy("empty select option", "None"))]
        return blank + list(groups.items())

    def clean_order(self):
        order = self.cleaned_data.get("order")
        if order is None or self.scenario is None:
            return order
        twin = AttackTechnique.objects.filter(scenario=self.scenario, order=order).exclude(pk=self.instance.pk).first()
        if twin is not None:
            raise forms.ValidationError(
                _("Technique %(order)s of this scenario already exists : choose another number.") % {"order": order},
            )
        return order

    def save(self, commit=True):
        self.instance.come_last_when_unranked()
        return super().save(commit=commit)


class AttackTechniqueCreateForm(CreationFormMixin, AttackTechniqueForm):
    """A new technique : the MITRE technique or its own name, what happens, on what, and how hard it is. It comes last."""

    owner_field = None
    steps = [
        Step(_("Attack technique"), "tools",
             ["mitre_technique", "custom_name", "description", "targeted_support_asset", "difficulty"]),
    ]

    class Meta(AttackTechniqueForm.Meta):
        fields = ["mitre_technique", "custom_name", "description", "targeted_support_asset", "difficulty"]


# ── Workshop W5 forms ────────────────────────────────────────


class EbiosSummaryForm(SteppedFormMixin, forms.ModelForm):
    """The summary of a study : one section per card of the page of workshop 5."""

    steps = [
        Step(_("Residual risk strategy"), "flag", ["residual_risk_strategy"], key="strategy",
             intro=_("The risks that remain once the measures are applied, and what the organisation "
                     "decides about them : accept them, watch them, treat them later.")),
        Step(_("Monitoring plan"), "binoculars",
             ["monitoring_plan", ["next_strategic_cycle_date", "next_operational_cycle_date"]],
             key="monitoring"),
        Step(_("Summary of the security improvement plan (PACS)"), "card-text", ["pacs_summary"], key="plan"),
    ]

    class Meta:
        model = EbiosSummary
        fields = [
            "residual_risk_strategy",
            "monitoring_plan", "next_strategic_cycle_date", "next_operational_cycle_date",
            "pacs_summary",
        ]
        widgets = {
            "residual_risk_strategy": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 5}),
            "monitoring_plan": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 5}),
            "pacs_summary": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 5}),
            "next_strategic_cycle_date": forms.DateInput(
                attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "next_operational_cycle_date": forms.DateInput(
                attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }
        help_texts = {
            "residual_risk_strategy": "",
            "monitoring_plan": _("The indicators followed, and the events that would reopen the study."),
            "next_strategic_cycle_date": _("The day workshops 1 to 3 are gone through again, usually within a year."),
            "next_operational_cycle_date": _("The day workshops 4 and 5 are gone through again, usually within six months."),
            "pacs_summary": _("The plan in a few lines : its priorities, its cost and the risks it brings down."),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            restrict_form_relations(self, user)


class PACSMeasureForm(SteppedFormMixin, forms.ModelForm):
    """A measure of the security improvement plan of a study : a row of workshop 5."""

    steps = [
        Step(_("PACS measure"), "list-check",
             ["name", ["measure_type", "priority"], "description", "expected_gain", "cost_estimate"],
             key="measure"),
        Step(_("Owner and dates"), "calendar-check",
             ["owner", ["start_date", "target_date"], ["completion_date", "progress_percentage"], "order"],
             key="planning"),
        Step(_("Relations"), "diagram-3",
             ["linked_treatment_plans", "linked_baseline_gaps", "linked_requirements"],
             key="relations",
             intro=_("The treatment plans the measure carries out, the baseline gaps it closes "
                     "and the requirements it meets.")),
    ]

    class Meta:
        model = PACSMeasure
        fields = [
            "name", "measure_type", "priority", "description", "expected_gain", "cost_estimate",
            "owner", "start_date", "target_date", "completion_date", "progress_percentage", "order",
            "linked_treatment_plans", "linked_baseline_gaps", "linked_requirements",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "measure_type": forms.Select(attrs=SELECT_ATTRS),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "expected_gain": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "cost_estimate": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "0.01", "min": 0}),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "start_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "completion_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "progress_percentage": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 0, "max": 100}),
            "order": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 1}),
            "linked_treatment_plans": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "linked_baseline_gaps": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "linked_requirements": forms.SelectMultiple(attrs=SELECT_ATTRS),
        }
        help_texts = {
            "name": _('For example "Separate the office network from the industrial network".'),
            "measure_type": _("Governance for rules and roles, protection to prevent, defense to detect and respond, "
                              "resilience to recover, awareness for people."),
            "priority": "",
            "description": _('The work to do, for example "Install a firewall at each plant and move the '
                             'supervision servers behind it".'),
            "expected_gain": _("The scenarios the measure makes harder, or the damage it limits."),
            "cost_estimate": _("In the currency of your budget, without a symbol."),
            "owner": _("The person who carries the measure out and reports on it."),
            "start_date": "",
            "target_date": _("A measure past this date reads as overdue."),
            "completion_date": _("The day the measure was finished."),
            "progress_percentage": "",
            "order": _("The place of the measure in the plan : the lowest number comes first."),
            "linked_treatment_plans": "",
            "linked_baseline_gaps": _("The gaps found in workshop 1 that the measure closes."),
            "linked_requirements": _("Among the requirements of the frameworks of the study."),
        }

    def __init__(self, *args, summary=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if summary is not None and not self.instance.summary_id:
            self.instance.summary = summary
        self.summary = self.instance.summary if self.instance.summary_id else summary
        creating = self.instance._state.adding
        pick_among_active_people(self, ("owner",))
        assessment = self.summary.assessment if self.summary is not None else None
        plans = self.fields.get("linked_treatment_plans")
        if plans is not None:
            # A new link targets a plan that can be linked; a link already there stays.
            held = None if creating else self.instance.linked_treatment_plans.all()
            plans.queryset = linkable_or_linked(plans.queryset, held)
        if assessment is not None:
            gaps = self.fields.get("linked_baseline_gaps")
            baseline = getattr(assessment, "ebios_security_baseline", None)
            if gaps is not None and baseline is not None:
                offered = Q(baseline=baseline)
                if not creating:
                    offered |= Q(pk__in=self.instance.linked_baseline_gaps.values("pk"))
                gaps.queryset = gaps.queryset.filter(offered)
            requirements = self.fields.get("linked_requirements")
            if requirements is not None:
                # The requirements of the frameworks the study names : those it
                # applies (workshop 0) and those of its baseline (workshop 1).
                # A study that names none is offered every requirement.
                frameworks = set()
                framework_of = getattr(assessment, "ebios_study_framework", None)
                if framework_of is not None:
                    frameworks |= set(framework_of.applicable_frameworks.values_list("pk", flat=True))
                if baseline is not None:
                    frameworks |= set(baseline.baseline_references.values_list("pk", flat=True))
                if frameworks:
                    offered = Q(framework__in=frameworks)
                    if not creating:
                        offered |= Q(pk__in=self.instance.linked_requirements.values("pk"))
                    requirements.queryset = requirements.queryset.filter(offered)
                requirements.queryset = requirements.queryset.select_related("framework")
        if user is not None:
            restrict_form_relations(self, user)

    def save(self, commit=True):
        if self.instance._state.adding and self.summary is not None and not self.instance.order:
            self.instance.order = next_rank(self.summary.pacs_measures.all())
        return super().save(commit=commit)


class PACSMeasureCreateForm(CreationFormMixin, PACSMeasureForm):
    """A new measure : its name, its type, its priority, its owner and its target date.

    The owner is whoever adds it, unless they say otherwise.
    """

    # The type and the priority are judged : "Protection" and "Medium" are not chosen for the reader.
    decisions = ("measure_type", "priority")
    steps = [
        Step(_("PACS measure"), "list-check", ["name", ["measure_type", "priority"], ["owner", "target_date"]]),
    ]

    class Meta(PACSMeasureForm.Meta):
        fields = ["name", "measure_type", "priority", "owner", "target_date"]

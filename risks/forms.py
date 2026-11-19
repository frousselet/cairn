# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django import forms
from django.utils.translation import gettext_lazy as _

from context.models import Scope
from context.widgets import ScopeTreeWidget
from core.modal_forms import CreationFormMixin, LabelledRowsFormSet, pick_among_active_people, ScopedFormMixin, Step, SteppedFormMixin
from core.query_params import parse_uuid
from core.scoping import restrict_form_relations
from .constants import DEFAULT_IMPACT_SCALES, DEFAULT_LIKELIHOOD_SCALES
from .models import (
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskLevel,
    RiskTreatmentPlan,
    ScaleLevel,
    Threat,
    TreatmentAction,
    Vulnerability,
)

# ── Criteria resolution for scale choices ────────────────────

def _resolve_criteria_from_assessment_id(assessment_id):
    """Look up the RiskCriteria linked to an assessment, or None."""
    # What comes from an address or a posted form may be anything : a value
    # that is not an identifier names no assessment.
    assessment_id = parse_uuid(getattr(assessment_id, "pk", assessment_id))
    if not assessment_id:
        return None
    assessment = RiskAssessment.objects.select_related("risk_criteria").filter(pk=assessment_id).first()
    return assessment.risk_criteria if assessment else None

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}


def get_scale_choices(scale_type, criteria=None):
    """Return (value, label) choices for likelihood or impact Select fields.

    Tries the given criteria first, then the default criteria, then any active
    criteria.  Falls back to hardcoded constants only when no criteria with
    ScaleLevels exists in the database at all.
    """
    # Build ordered list of criteria to try
    candidates = []
    if criteria is not None:
        candidates.append(criteria)
    default_c = RiskCriteria.objects.filter(is_default=True).first()
    if default_c and default_c not in candidates:
        candidates.append(default_c)
    from core.lifecycle import reportable

    active_c = reportable(RiskCriteria.objects.all()).first()
    if active_c and active_c not in candidates:
        candidates.append(active_c)

    for c in candidates:
        levels = list(
            c.scale_levels.filter(scale_type=scale_type)
            .order_by("level")
            .values_list("level", "name")
        )
        if levels:
            return [("", "---------")] + [
                (lvl, f"{lvl} - {name}") for lvl, name in levels
            ]

    # Ultimate fallback to hardcoded defaults
    defaults = (
        DEFAULT_LIKELIHOOD_SCALES if scale_type == "likelihood"
        else DEFAULT_IMPACT_SCALES
    )
    return [("", "---------")] + [
        (lvl, f"{lvl} - {name}") for lvl, name in defaults
    ]




class RiskCriteriaForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = RiskCriteria
        fields = [
            "scopes", "name", "description", "acceptance_threshold",
            "is_default", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "acceptance_threshold": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "is_default": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }


class RiskAssessmentBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the assessment page : a step opens on its own from
    # its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "clipboard-data",
             ["name", ["methodology", "assessor"], "risk_criteria", "description", "scopes", "tags"],
             key="identity"),
        Step(_("Dates and summary"), "calendar-check",
             [["assessment_date", "next_review_date"], "summary"],
             key="planning"),
    ]

    class Meta:
        model = RiskAssessment
        fields = [
            "scopes", "name", "description", "methodology",
            "assessment_date", "assessor", "risk_criteria",
            "next_review_date", "summary", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "methodology": forms.Select(attrs=SELECT_ATTRS),
            "assessment_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "assessor": forms.Select(attrs=SELECT_ATTRS),
            "risk_criteria": forms.Select(attrs=SELECT_ATTRS),
            "next_review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "summary": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('For example "Risk assessment of the customer portal 2026".'),
            "methodology": _("ISO 27005 rates what could happen to each asset. EBIOS RM, the method of the French cybersecurity agency (ANSSI), runs five workshops, from what you protect to the measures you decide. The method decides the screens this assessment uses."),
            "assessor": _("The person who conducts the risk assessment and keeps it up to date."),
            "description": _("What it covers and why it is held, in a sentence or two."),
            "risk_criteria": _("The scales its risks are rated on, and the level above which a risk is not acceptable."),
            "assessment_date": "",
            "next_review_date": _("When to look at it again. Once a year is usual, sooner after a major change."),
            "summary": _("What it concludes, for somebody who will not read the register : the main risks and what is decided."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pick_among_active_people(self, ("assessor",))


class RiskAssessmentCreateForm(CreationFormMixin, RiskAssessmentBaseForm):
    """Risk assessment creation : what it is called, how it is conducted, by whom and on which scales.

    Its dates and its summary are written on its page, when they are known.
    """

    #: Whoever conducts the assessment : its creator unless they say otherwise.
    owner_field = "assessor"
    #: The method decides the screens the assessment uses : the reader chooses.
    decisions = ("methodology",)

    steps = [
        Step(_("Identity"), "clipboard-data",
             ["name", ["methodology", "assessor"], "risk_criteria", "scopes", "description"]),
    ]

    class Meta(RiskAssessmentBaseForm.Meta):
        fields = ["scopes", "name", "description", "methodology", "assessor", "risk_criteria"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The criteria the organisation marked as its default are the answer
        # unless the reader picks others : that default is a decision somebody
        # took, not a value of the model.
        criteria = self.fields.get("risk_criteria")
        if criteria is not None and not self.is_bound:
            default = criteria.queryset.filter(is_default=True).first()
            if default is not None:
                criteria.initial = default.pk


class RiskAssessmentUpdateForm(RiskAssessmentBaseForm):
    """Risk assessment edition modal form."""


class RiskBaseForm(SteppedFormMixin, forms.ModelForm):
    # One step per card of the risk page : a step opens on its own from its
    # card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "exclamation-triangle",
             ["name", ["assessment", "risk_source"], "risk_owner", "description",
              ["impact_confidentiality", "impact_integrity", "impact_availability"], "tags"],
             key="identity"),
        Step(_("Evaluation"), "speedometer2",
             [["initial_likelihood", "initial_impact"],
              ["current_likelihood", "current_impact"]],
             key="evaluation",
             intro=_("Rate it twice : as if no control were in place, then with the controls in place today. The gap is what your controls are worth.")),
        Step(_("Treatment"), "shield-check",
             [["treatment_decision", "priority"], "treatment_justification", "review_date"],
             key="treatment"),
        Step(_("Relations"), "diagram-3",
             ["affected_essential_assets", "affected_support_assets", "linked_requirements"],
             key="relations",
             intro=_("What it would harm, what it would go through, and the requirements whose respect reduces it.")),
    ]

    class Meta:
        model = Risk
        fields = [
            "assessment", "name", "description", "risk_source",
            "affected_essential_assets", "affected_support_assets",
            "linked_requirements",
            "impact_confidentiality", "impact_integrity", "impact_availability",
            "initial_likelihood", "initial_impact",
            "current_likelihood", "current_impact",
            "treatment_decision", "treatment_justification",
            "risk_owner", "priority", "review_date", "tags",
        ]
        widgets = {
            "assessment": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "risk_source": forms.Select(attrs=SELECT_ATTRS),
            "affected_essential_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "affected_support_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "linked_requirements": forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-requirements": "true"}),
            "impact_confidentiality": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "impact_integrity": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "impact_availability": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "initial_likelihood": forms.Select(attrs=SELECT_ATTRS),
            "initial_impact": forms.Select(attrs=SELECT_ATTRS),
            "current_likelihood": forms.Select(attrs=SELECT_ATTRS),
            "current_impact": forms.Select(attrs=SELECT_ATTRS),
            "treatment_decision": forms.Select(attrs=SELECT_ATTRS),
            "treatment_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "risk_owner": forms.Select(attrs=SELECT_ATTRS),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('What could go wrong, for example "Customer data leaked after a phishing attack".'),
            "assessment": _("Its criteria give the scales this risk is rated on. Set when the risk is created."),
            "risk_source": _("Where it was noticed : an analysis, an incident, an audit, or noted by hand. Set when the risk is created."),
            "risk_owner": _("The person entitled to decide what is done about it, and to accept what remains."),
            "description": _("How it would happen and what it would cost you, in a sentence or two."),
            "impact_confidentiality": _("Tick when it would disclose information."),
            "impact_integrity": _("Tick when it would alter or destroy information."),
            "impact_availability": _("Tick when it would make something unavailable."),
            "initial_likelihood": _("How likely, as if no control were in place."),
            "initial_impact": _("How severe, as if no control were in place."),
            "current_likelihood": _("How likely, with the controls in place today."),
            "current_impact": _("How severe, with the controls in place today."),
            "treatment_decision": _("Mitigate it with controls, transfer it to an insurer or a supplier, avoid it by stopping the activity, or accept it as it is."),
            "priority": _("How soon it must be dealt with, compared with the other risks."),
            "treatment_justification": _("Why this decision : what an auditor asks about every accepted risk."),
            "affected_essential_assets": _("The information and the processes it would harm."),
            "affected_support_assets": _("The systems, the sites and the people it would go through."),
            "linked_requirements": "",
            "review_date": _("When to look at it again : a risk changes as its context does."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, user=None, **kwargs):
        #: Who fills the form : what it offers stays within their scopes.
        self.user = user
        super().__init__(*args, **kwargs)
        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        criteria = self._resolve_criteria()
        l_choices = get_scale_choices("likelihood", criteria)
        i_choices = get_scale_choices("impact", criteria)
        for names, choices, scale in (
            (("initial_likelihood", "current_likelihood"), l_choices, "likelihood"),
            (("initial_impact", "current_impact"), i_choices, "impact"),
        ):
            for fname in names:
                if fname not in self.fields:
                    continue
                self.fields[fname] = forms.TypedChoiceField(
                    choices=choices, coerce=int, required=False,
                    empty_value=None, label=self.fields[fname].label,
                    help_text=self.fields[fname].help_text,
                    widget=forms.Select(attrs=SELECT_ATTRS),
                )
                # Picking another assessment reloads the four scales from its
                # criteria (base.html wires data-scale-source / data-scale-target,
                # in the modal and on the page alike).
                self.fields[fname].widget.attrs["data-scale-target"] = scale
        if "assessment" in self.fields:
            from django.urls import reverse

            self.fields["assessment"].widget.attrs["data-scale-source"] = reverse("risks:api-scale-choices")
        pick_among_active_people(self, ("risk_owner",))
        # Link pickers only offer linkable elements (existing links are kept)
        from core.lifecycle import linkable_or_linked

        editing = bool(self.instance and self.instance.pk)
        for fname in (
            "linked_requirements",
            "affected_essential_assets",
            "affected_support_assets",
        ):
            field = self.fields.get(fname)
            if field is not None:
                field.queryset = linkable_or_linked(
                    field.queryset,
                    getattr(self.instance, fname).all() if editing else None,
                )
        # When editing an existing risk, lock the assessment and source fields
        if editing:
            for fname in ("assessment", "risk_source"):
                if fname in self.fields:
                    self.fields[fname].disabled = True
        # A risk hangs under its assessment : the assessments, the assets and
        # the requirements offered are those the user may reach.
        if user is not None:
            restrict_form_relations(self, user)

    def _resolve_criteria(self):
        """Find the best RiskCriteria for populating scale choices."""
        # 1. Existing risk → assessment's criteria
        if self.instance and self.instance.pk and self.instance.assessment_id:
            criteria = getattr(self.instance.assessment, "risk_criteria", None)
            if criteria:
                return criteria
        # 2. From POST data or initial data (selected assessment)
        assessment_id = self.data.get("assessment") or self.initial.get("assessment")
        return _resolve_criteria_from_assessment_id(assessment_id)


class RiskCreateForm(CreationFormMixin, RiskBaseForm):
    """Risk creation, inside an assessment : what could go wrong, who owns it and what it would harm.

    A risk is opened from its assessment, which is therefore not asked. Its
    rating, its treatment and its other relations are worked on its page.
    """

    #: Who owns a risk decides what is done about it : it is asked, never
    #: assumed to be whoever noted the risk.
    owner_field = None

    steps = [
        Step(_("Identity"), "exclamation-triangle",
             ["assessment", "name", ["risk_source", "risk_owner"], "affected_essential_assets", "description"]),
    ]

    class Meta(RiskBaseForm.Meta):
        fields = ["assessment", "name", "description", "risk_source", "risk_owner", "affected_essential_assets"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The assessment the risk is opened from is the answer : the question
        # is not asked (rule F2), the value travels with the form.
        if self.initial.get("assessment") or self.data.get("assessment"):
            self.fields["assessment"].widget = forms.HiddenInput()


class RiskUpdateForm(RiskBaseForm):
    """Risk edition modal form."""


def _criteria_of_the_risk(risk_id):
    """The criteria of the assessment a risk belongs to, or ``None``.

    What comes from an address or a posted form may be anything : a value
    that is not an identifier names no risk.
    """
    risk_id = parse_uuid(getattr(risk_id, "pk", risk_id))
    if not risk_id:
        return None
    risk = Risk.objects.select_related("assessment__risk_criteria").filter(pk=risk_id).first()
    return getattr(risk.assessment, "risk_criteria", None) if risk else None


class RiskTreatmentPlanBaseForm(SteppedFormMixin, forms.ModelForm):
    # One step per card of the plan page : a step opens on its own from its
    # card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "shield-check",
             ["name", ["risk", "treatment_type"], "owner", "description", "tags"],
             key="identity"),
        Step(_("Target and planning"), "speedometer2",
             [["expected_residual_likelihood", "expected_residual_impact"],
              "cost_estimate", ["start_date", "target_date"]],
             key="planning",
             intro=_("Where the plan aims to bring the risk, what it costs and when it is due.")),
        Step(_("Related action plans"), "clipboard-plus",
             ["related_action_plans"],
             key="relations"),
    ]

    class Meta:
        model = RiskTreatmentPlan
        fields = [
            "risk", "name", "description", "treatment_type",
            "expected_residual_likelihood", "expected_residual_impact",
            "cost_estimate", "owner", "start_date", "target_date", "tags",
            "related_action_plans",
        ]
        widgets = {
            "risk": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "treatment_type": forms.Select(attrs=SELECT_ATTRS),
            "expected_residual_likelihood": forms.Select(attrs=SELECT_ATTRS),
            "expected_residual_impact": forms.Select(attrs=SELECT_ATTRS),
            "cost_estimate": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "start_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "related_action_plans": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 6}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('What will be done, for example "Segment the industrial network".'),
            "risk": _("The risk this plan reduces. Its assessment gives the scales its target is rated on."),
            "treatment_type": _("Mitigate it with controls, transfer it to an insurer or a supplier, or avoid it by stopping the activity."),
            "owner": _("The person who carries the plan and reports on it."),
            "description": _("What the plan consists of, in a sentence or two."),
            "expected_residual_likelihood": _("How likely the risk should be once the plan is done."),
            "expected_residual_impact": _("How severe it should be once the plan is done."),
            "cost_estimate": _("An order of magnitude is enough, in your usual currency."),
            "start_date": "",
            "target_date": "",
            "related_action_plans": _("The compliance action plans that carry part of this work."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, user=None, **kwargs):
        #: Who fills the form : what it offers stays within their scopes.
        self.user = user
        super().__init__(*args, **kwargs)
        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        criteria = None
        # 1. Existing plan → risk → assessment → criteria
        if self.instance and self.instance.pk and self.instance.risk_id:
            assessment = getattr(self.instance.risk, "assessment", None)
            if assessment:
                criteria = getattr(assessment, "risk_criteria", None)
        # 2. From POST/initial data: get risk → assessment → criteria
        if not criteria:
            criteria = _criteria_of_the_risk(self.data.get("risk") or self.initial.get("risk"))
        for fname, scale in (
            ("expected_residual_likelihood", "likelihood"),
            ("expected_residual_impact", "impact"),
        ):
            if fname in self.fields:
                self.fields[fname] = forms.TypedChoiceField(
                    choices=get_scale_choices(scale, criteria),
                    coerce=int, required=False, empty_value=None,
                    label=self.fields[fname].label,
                    help_text=self.fields[fname].help_text,
                    widget=forms.Select(attrs=SELECT_ATTRS),
                )
        pick_among_active_people(self, ("owner",))
        # Link picker only offers linkable action plans (existing links are kept)
        from core.lifecycle import linkable_or_linked

        field = self.fields.get("related_action_plans")
        if field is not None:
            field.queryset = linkable_or_linked(
                field.queryset,
                self.instance.related_action_plans.all()
                if self.instance and self.instance.pk
                else None,
            )
        if user is not None:
            restrict_form_relations(self, user)


class RiskTreatmentPlanCreateForm(CreationFormMixin, RiskTreatmentPlanBaseForm):
    """Treatment plan creation : what will be done about which risk, how, by whom and for when.

    Its target, its cost and its actions are worked on its page.
    """

    steps = [
        Step(_("Identity"), "shield-check",
             ["risk", "name", ["treatment_type", "owner"], "target_date", "description"]),
    ]

    class Meta(RiskTreatmentPlanBaseForm.Meta):
        fields = ["risk", "name", "description", "treatment_type", "owner", "target_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The risk the plan is opened from is the answer : the question is
        # not asked (rule F2), the value travels with the form.
        if self.initial.get("risk"):
            self.fields["risk"].widget = forms.HiddenInput()


class RiskTreatmentPlanUpdateForm(RiskTreatmentPlanBaseForm):
    """Treatment plan edition modal form."""


class RiskAcceptanceBaseForm(SteppedFormMixin, forms.ModelForm):
    # One step per card of the acceptance page : a step opens on its own from
    # its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Acceptance"), "check2-circle",
             ["risk", "justification", "conditions", "tags"],
             key="acceptance"),
        Step(_("Validity"), "calendar-check",
             [["valid_until", "review_date"]],
             key="validity",
             intro=_("An acceptance is not for ever : say until when it holds, and when its conditions are checked.")),
    ]

    class Meta:
        model = RiskAcceptance
        fields = [
            "risk", "justification", "conditions", "valid_until", "review_date", "tags",
        ]
        widgets = {
            "risk": forms.Select(attrs=SELECT_ATTRS),
            "justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "conditions": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "valid_until": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "risk": _("The risk somebody accepts to live with. Its level on that day is kept with the acceptance."),
            "justification": _('Why living with it is reasonable, for example "The fix costs more than the loss it prevents".'),
            "conditions": _('What must stay true for it to hold, for example "As long as the service has fewer than 100 users".'),
            "valid_until": _("After this date the risk must be decided again."),
            "review_date": _("When to check that its conditions still hold."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, user=None, **kwargs):
        #: Who fills the form : what it offers stays within their scopes.
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None:
            restrict_form_relations(self, user)


class RiskAcceptanceCreateForm(CreationFormMixin, RiskAcceptanceBaseForm):
    """Risk acceptance creation : which risk, why, on what conditions and until when."""

    #: Whoever accepts a risk is recorded when the acceptance becomes active :
    #: nobody answers for it by filing it.
    owner_field = None

    steps = [
        Step(_("Acceptance"), "check2-circle",
             ["risk", "justification", "conditions", ["valid_until", "review_date"]]),
    ]

    class Meta(RiskAcceptanceBaseForm.Meta):
        fields = ["risk", "justification", "conditions", "valid_until", "review_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The risk the acceptance is opened from is the answer (rule F2).
        if self.initial.get("risk"):
            self.fields["risk"].widget = forms.HiddenInput()


class RiskAcceptanceUpdateForm(RiskAcceptanceBaseForm):
    """Risk acceptance edition modal form."""


class ThreatBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the threat page : a step opens on its own from its
    # card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "lightning",
             ["name", ["type", "origin"], "category", "description", "scopes", "tags"],
             key="identity"),
        Step(_("Likelihood and status"), "speedometer2",
             ["typical_likelihood", "is_from_catalog", "status"],
             key="use"),
    ]

    class Meta:
        model = Threat
        fields = [
            "scopes", "name", "description", "type", "origin",
            "category", "typical_likelihood", "is_from_catalog", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "origin": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "typical_likelihood": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "is_from_catalog": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('What could happen, for example "Phishing of an employee" or "Flood of the server room".'),
            "type": _("Deliberate when somebody wants it, accidental when nobody does, environmental when nature does it."),
            "origin": _('An employee is "human internal", an attacker "human external", a storm "natural", a breakdown "technical".'),
            "category": "",
            "typical_likelihood": _("How often you expect it, on the likelihood scale of your risk criteria (1 to 5 by default). Leave it empty when you cannot say."),
            "description": _("How it would unfold, in a sentence or two."),
            "is_from_catalog": _("Tick when it comes from a reference catalogue rather than from your own analysis."),
            "status": _("Whether it still concerns you. It only filters this register : the lifecycle says whether this record is validated."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }


class ThreatCreateForm(CreationFormMixin, ThreatBaseForm):
    """Threat creation : what could happen, what kind of event it is and where it comes from."""

    #: A threat is an entry of a shared catalogue : nobody answers for it.
    owner_field = None

    steps = [
        Step(_("Identity"), "lightning", ["name", ["type", "origin"], "category", "scopes", "description"]),
    ]

    class Meta(ThreatBaseForm.Meta):
        fields = ["scopes", "name", "description", "type", "origin", "category"]


class ThreatUpdateForm(ThreatBaseForm):
    """Threat edition modal form."""


class VulnerabilityBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the vulnerability page : a step opens on its own
    # from its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "bug",
             ["name", ["category", "severity"], "description", "scopes", "tags"],
             key="identity"),
        Step(_("Exposure and remediation"), "tools",
             ["affected_assets", "remediation_guidance", "is_from_catalog"],
             key="exposure",
             intro=_("Where the weakness is, and what would close it.")),
    ]

    class Meta:
        model = Vulnerability
        fields = [
            "scopes", "name", "description", "category",
            "severity", "affected_assets", "remediation_guidance",
            "is_from_catalog", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "severity": forms.Select(attrs=SELECT_ATTRS),
            "affected_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "remediation_guidance": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "is_from_catalog": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('The weakness, for example "Laptops without disk encryption".'),
            "category": "",
            "severity": _("How bad it would be if a threat took advantage of it."),
            "description": _("What is weak, and why it matters."),
            "remediation_guidance": _("What would close it : a patch, a setting, a procedure."),
            "affected_assets": _("The support assets that have this weakness."),
            "is_from_catalog": _("Tick when it comes from a reference catalogue rather than from your own analysis."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }


class VulnerabilityCreateForm(CreationFormMixin, VulnerabilityBaseForm):
    """Vulnerability creation : what the weakness is and how bad it would be."""

    #: A vulnerability is an entry of a shared catalogue : nobody answers for it.
    owner_field = None
    #: Its severity has no default answer : the reader decides.
    decisions = ("severity",)

    steps = [
        Step(_("Identity"), "bug", ["name", ["category", "severity"], "scopes", "description"]),
    ]

    class Meta(VulnerabilityBaseForm.Meta):
        fields = ["scopes", "name", "description", "category", "severity"]


class VulnerabilityUpdateForm(VulnerabilityBaseForm):
    """Vulnerability edition modal form."""


# ── Matrix configuration formsets ────────────────────────────

class ScaleLevelForm(forms.ModelForm):
    class Meta:
        model = ScaleLevel
        fields = ["level", "name", "description"]
        widgets = {
            "level": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "style": "width:80px"}),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
        }


class RiskLevelForm(forms.ModelForm):
    class Meta:
        model = RiskLevel
        fields = ["level", "name", "color", "requires_treatment"]
        widgets = {
            "level": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "style": "width:80px"}),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "color": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "type": "color", "style": "width:60px; padding:2px"}),
            "requires_treatment": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
        }


LikelihoodFormSet = forms.inlineformset_factory(
    RiskCriteria, ScaleLevel,
    form=ScaleLevelForm,
    extra=0,
    can_delete=True,
    formset=LabelledRowsFormSet,
)

ImpactFormSet = forms.inlineformset_factory(
    RiskCriteria, ScaleLevel,
    form=ScaleLevelForm,
    extra=0,
    can_delete=True,
    formset=LabelledRowsFormSet,
)

RiskLevelFormSet = forms.inlineformset_factory(
    RiskCriteria, RiskLevel,
    form=RiskLevelForm,
    extra=0,
    can_delete=True,
    formset=LabelledRowsFormSet,
)


class ISO27005RiskBaseForm(SteppedFormMixin, forms.ModelForm):
    # One step per card of the analysis page : a step opens on its own from
    # its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Scenario"), "exclamation-triangle",
             ["assessment", ["threat", "vulnerability"], "description", "tags"],
             key="scenario"),
        Step(_("Evaluation"), "speedometer2",
             [["threat_likelihood", "vulnerability_exposure"],
              ["impact_confidentiality", "impact_integrity", "impact_availability"],
              "existing_controls"],
             key="evaluation",
             intro=_("Rate the scenario on the scales of the assessment's criteria. The higher likelihood and the highest impact give its risk level.")),
        Step(_("Affected assets"), "hdd-stack",
             ["affected_essential_assets", "affected_support_assets"],
             key="assets"),
    ]

    #: The ratings of an analysis, and the scale each is read on.
    RATINGS = (
        ("threat_likelihood", "likelihood"),
        ("vulnerability_exposure", "likelihood"),
        ("impact_confidentiality", "impact"),
        ("impact_integrity", "impact"),
        ("impact_availability", "impact"),
    )

    class Meta:
        model = ISO27005Risk
        fields = [
            "assessment", "threat", "vulnerability",
            "affected_essential_assets", "affected_support_assets",
            "threat_likelihood", "vulnerability_exposure",
            "impact_confidentiality", "impact_integrity", "impact_availability",
            "existing_controls", "description", "tags",
        ]
        widgets = {
            "assessment": forms.Select(attrs=SELECT_ATTRS),
            "threat": forms.Select(attrs=SELECT_ATTRS),
            "vulnerability": forms.Select(attrs=SELECT_ATTRS),
            "affected_essential_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "affected_support_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "threat_likelihood": forms.Select(attrs=SELECT_ATTRS),
            "vulnerability_exposure": forms.Select(attrs=SELECT_ATTRS),
            "impact_confidentiality": forms.Select(attrs=SELECT_ATTRS),
            "impact_integrity": forms.Select(attrs=SELECT_ATTRS),
            "impact_availability": forms.Select(attrs=SELECT_ATTRS),
            "existing_controls": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "assessment": _("Its criteria give the scales this scenario is rated on."),
            "threat": _("What could happen, from the catalogue of threats."),
            "vulnerability": _("The weakness it would take advantage of."),
            "description": _("How this threat would use this weakness here, in a sentence or two."),
            "threat_likelihood": _("How often it is attempted, whatever your defences."),
            "vulnerability_exposure": _("How easy the weakness makes it. The higher of the two is kept."),
            "impact_confidentiality": _("How severe if information is disclosed."),
            "impact_integrity": _("How severe if information is altered or destroyed."),
            "impact_availability": _("How severe if something becomes unavailable. The highest of the three is kept."),
            "existing_controls": _('What already limits it today, for example "Multi-factor authentication on the VPN".'),
            "affected_essential_assets": _("The information and the processes it would harm."),
            "affected_support_assets": _("The systems, the sites and the people it would go through."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, user=None, **kwargs):
        #: Who fills the form : what it offers stays within their scopes.
        self.user = user
        super().__init__(*args, **kwargs)
        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        if "assessment" in self.fields:
            # Only show ISO 27005 assessments
            self.fields["assessment"].queryset = RiskAssessment.objects.filter(
                methodology="iso27005"
            )
            from django.urls import reverse

            # Picking another assessment reloads the scales from its criteria
            # (base.html wires data-scale-source / data-scale-target).
            self.fields["assessment"].widget.attrs["data-scale-source"] = reverse("risks:api-scale-choices")
        # A rating is picked on the scale of the assessment's criteria, each
        # level by its name, where a bare number was typed.
        criteria = self._resolve_criteria()
        choices = {scale: get_scale_choices(scale, criteria) for scale in ("likelihood", "impact")}
        for fname, scale in self.RATINGS:
            if fname not in self.fields:
                continue
            offered = list(choices[scale])
            current = getattr(self.instance, fname, None)
            if current is not None and current not in [value for value, _label in offered]:
                # A level rated on scales that have since changed is kept as it is.
                offered.append((current, str(current)))
            self.fields[fname] = forms.TypedChoiceField(
                choices=offered, coerce=int, required=False,
                empty_value=None, label=self.fields[fname].label,
                help_text=self.fields[fname].help_text,
                widget=forms.Select(attrs={**SELECT_ATTRS, "data-scale-target": scale}),
            )
        if user is not None:
            restrict_form_relations(self, user)

    def _resolve_criteria(self):
        """The criteria whose scales the ratings are read on."""
        if self.instance and self.instance.pk and self.instance.assessment_id:
            criteria = getattr(self.instance.assessment, "risk_criteria", None)
            if criteria:
                return criteria
        assessment_id = self.data.get("assessment") or self.initial.get("assessment")
        return _resolve_criteria_from_assessment_id(assessment_id)


class ISO27005RiskCreateForm(CreationFormMixin, ISO27005RiskBaseForm):
    """A scenario to analyse : a threat, the weakness it would use, and what it would harm.

    It is rated on its page, where the scales of its assessment are at hand.
    """

    #: Nobody owns a scenario : the risk it is consolidated into has an owner.
    owner_field = None

    steps = [
        Step(_("Scenario"), "exclamation-triangle",
             ["assessment", ["threat", "vulnerability"], "affected_essential_assets", "description"]),
    ]

    class Meta(ISO27005RiskBaseForm.Meta):
        fields = ["assessment", "threat", "vulnerability", "affected_essential_assets", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The assessment the analysis is opened from is the answer : the
        # question is not asked (rule F2), the value travels with the form.
        if self.initial.get("assessment"):
            self.fields["assessment"].widget = forms.HiddenInput()


class ISO27005RiskUpdateForm(ISO27005RiskBaseForm):
    """ISO 27005 risk edition modal form."""


class TreatmentActionBaseForm(SteppedFormMixin, forms.ModelForm):
    # A row of a treatment plan, added and edited from its page : one screen.
    steps = [
        Step(_("Action"), "list-task",
             ["treatment_plan", "description", ["owner", "target_date"],
              ["status", "order"]]),
    ]

    class Meta:
        model = TreatmentAction
        fields = [
            "treatment_plan", "description", "owner", "target_date", "status", "order",
        ]
        widgets = {
            "treatment_plan": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "treatment_plan": "",
            "description": _('One step of the plan, for example "Order the firewalls".'),
            "owner": "",
            "target_date": "",
            "status": "",
            "order": _("Its place in the list of the plan : the lowest number comes first."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pick_among_active_people(self, ("owner",))
        # The plan the action is added to is the answer : the question is not
        # asked (rule F2), the value travels with the form.
        if self.initial.get("treatment_plan") or (self.instance and self.instance.pk):
            self.fields["treatment_plan"].widget = forms.HiddenInput()


class TreatmentActionCreateForm(TreatmentActionBaseForm):
    """A new action of a plan : what is to be done, by whom and for when.

    It starts as planned and at the end of the list; both are changed from
    the row once it exists.
    """

    steps = [
        Step(_("Action"), "list-task", ["treatment_plan", "description", ["owner", "target_date"]]),
    ]

    class Meta(TreatmentActionBaseForm.Meta):
        fields = ["treatment_plan", "description", "owner", "target_date"]


class TreatmentActionUpdateForm(TreatmentActionBaseForm):
    """Treatment action edition modal form."""

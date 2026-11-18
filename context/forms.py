# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import math

from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .constants import EXTERNAL_CATEGORIES, INTERNAL_CATEGORIES, IssueCategory, IssueType
from .models import (
    Activity,
    Indicator,
    IndicatorMeasurement,
    Issue,
    Objective,
    Role,
    Scope,
    Site,
    Stakeholder,
    StakeholderExpectation,
    StakeholderFeedback,
    SwotAnalysis,
    SwotItem,
    SwotStrategy,
    Responsibility,
    Tag,
)
from .widgets import IconPickerWidget, ScopeTreeRadioWidget, ScopeTreeWidget
from core.modal_forms import CreationFormMixin, pick_among_active_people, ScopedFormMixin, Step, SteppedFormMixin

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}
TAGS_WIDGET = forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4})


def _scope_tree_choices(queryset):
    """Build tree-ordered (pk, label) choices with full path labels (A / B / C)."""
    scopes = list(queryset.select_related("parent_scope"))
    by_parent = {}
    for s in scopes:
        by_parent.setdefault(s.parent_scope_id, []).append(s)

    choices = []
    visited = set()

    def walk(parent_id, path):
        for s in sorted(by_parent.get(parent_id, []), key=lambda x: x.name):
            full_path = path + [s.name]
            choices.append((s.pk, " / ".join(full_path)))
            visited.add(s.pk)
            walk(s.pk, full_path)

    walk(None, [])

    for s in scopes:
        if s.pk not in visited:
            choices.append((s.pk, s.name))

    return choices




def _offer_what_can_be_linked(form, names):
    """A relation offers what may be linked, plus what the record already holds.

    Whether a record may be the target of a new link is said by its lifecycle
    (``linkable``) : a draft is not offered, and a link made earlier survives
    its target leaving that step. A form opened on one section carries a part
    of its fields only : each is prepared when it is there.
    """
    from core.lifecycle import linkable_or_linked

    editing = bool(form.instance and form.instance.pk)
    for name in names:
        field = form.fields.get(name)
        if field is None:
            continue
        held = None
        if editing:
            value = getattr(form.instance, name)
            # A many-to-many holds a set, a foreign key one record or none.
            held = value.all() if hasattr(value, "all") else field.queryset.model._default_manager.filter(
                pk=getattr(value, "pk", None),
            )
        field.queryset = linkable_or_linked(field.queryset, held)


class ScopeBaseForm(SteppedFormMixin, forms.ModelForm):
    # One step per card of the scope page : a step opens on its own from its
    # card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "diagram-3",
             [[("icon", "auto"), "name"], "parent_scope", "description", "tags"],
             key="identity"),
        Step(_("Coverage"), "bullseye",
             ["geographic_scope", "organizational_scope", "technical_scope"],
             key="coverage",
             intro=_("What the scope takes in. Fill in what applies, in your own words.")),
        Step(_("Boundaries and exclusions"), "bounding-box",
             ["boundaries", "justification_exclusions"],
             key="boundaries",
             intro=_("Where the scope stops : what is left out, and why. It is the first thing an auditor reads.")),
        Step(_("Sites"), "geo-alt",
             ["included_sites", "excluded_sites"],
             key="sites"),
        Step(_("Managers"), "people",
             ["managers"],
             key="managers"),
        Step(_("Dates"), "calendar-event",
             [["effective_date", "review_date"]],
             key="planning"),
    ]

    class Meta:
        model = Scope
        fields = [
            "name", "description", "parent_scope", "icon",
            "boundaries", "justification_exclusions",
            "geographic_scope", "organizational_scope", "technical_scope",
            "included_sites", "excluded_sites",
            "managers",
            "effective_date", "review_date", "tags",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "parent_scope": ScopeTreeRadioWidget(),
            "icon": IconPickerWidget(),
            "boundaries": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "justification_exclusions": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "geographic_scope": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "organizational_scope": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "technical_scope": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "included_sites": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 6}),
            "excluded_sites": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 6}),
            "managers": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "effective_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('For example "Head office", "Customer service" or "The whole company".'),
            "parent_scope": _("Leave empty unless this scope is a part of another one."),
            "icon": "",  # self-evident adornment: no helper (overrides model help_text)
            "description": _("In a sentence or two : what this scope covers, and what it is for."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
            "geographic_scope": _("Countries, cities or buildings concerned."),
            "organizational_scope": _("Entities, departments or teams concerned."),
            "technical_scope": _("Information systems, applications and networks concerned."),
            "boundaries": _('What is left out of the scope. Write "no exclusion" when it covers everything.'),
            "justification_exclusions": _("Why each exclusion is acceptable : an auditor will ask."),
            "included_sites": _("Pick them among the sites already registered (Sites menu)."),
            "excluded_sites": _("Only the sites you want on record as left out."),
            "managers": _("They answer for this scope, and get access to everything in it."),
            "effective_date": _("Filled in for you the day the scope comes into force. Set it only to plan a later date."),
            "review_date": _("When to check that the scope is still right. Once a year is usual."),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        if "parent_scope" in self.fields:
            qs = Scope.objects.exclude(workflow_state="archived")
            # A user restricted to some scopes picks a parent among theirs.
            # The parent already set stays offered, or saving the form would
            # silently detach the scope from it.
            if user is not None and not user.is_superuser:
                allowed = user.get_allowed_scope_ids()
                if allowed is not None:
                    qs = qs.filter(Q(id__in=allowed) | Q(pk=self.instance.parent_scope_id))
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            field = self.fields["parent_scope"]
            field.queryset = qs
            # Build tree data for the radio widget
            selected_id = self.instance.parent_scope_id if not self.instance._state.adding else None
            if self.data and self.add_prefix("parent_scope") in self.data:
                selected_id = self.data.get(self.add_prefix("parent_scope"))
            elif selected_id is None:
                selected_id = self.initial.get("parent_scope")
            field.widget.build_tree_data(qs, selected_id)
        # Site tree choices for included/excluded
        if "included_sites" in self.fields or "excluded_sites" in self.fields:
            site_qs = Site.objects.exclude(workflow_state="archived")
            site_choices = _site_tree_choices(site_qs)
            for fname in ("included_sites", "excluded_sites"):
                if fname in self.fields:
                    self.fields[fname].queryset = site_qs
                    self.fields[fname].choices = site_choices
        # Managers: only active users
        if "managers" in self.fields:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.fields["managers"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name", "email")


class ScopeCreateForm(ScopeBaseForm):
    """Scope creation : what makes the scope exist, on one screen.

    The rest (coverage, boundaries, sites, managers, dates) is filled in on
    the scope page, which lists what is missing.
    """

    steps = [
        Step(_("Identity"), "diagram-3",
             [[("icon", "auto"), "name"], "parent_scope", "description"]),
    ]

    class Meta(ScopeBaseForm.Meta):
        fields = ["name", "description", "parent_scope", "icon"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The first scope has no possible parent : the question is not asked.
        if not self.fields["parent_scope"].queryset.exists():
            del self.fields["parent_scope"]


class ScopeUpdateForm(ScopeBaseForm):
    """Scope edition : the whole form, or one of its sections."""


class IssueBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the issue page : a step opens on its own from its
    # card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "flag",
             ["name", "category", "source", "description", "scopes", "tags"],
             key="identity"),
        Step(_("Impact and follow-up"), "graph-up",
             [["impact_level", "trend"], ["review_date", "status"]],
             key="assessment"),
        Step(_("Relations"), "diagram-3", ["related_stakeholders"], key="relations"),
    ]

    class Meta:
        model = Issue
        # No ``type`` : a category is internal or external, never both (rule
        # RS-01), so the type is read from the category the reader picks.
        fields = [
            "scopes", "name", "description", "category",
            "impact_level", "trend", "source", "review_date", "status", "tags",
            "related_stakeholders",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "impact_level": forms.Select(attrs=SELECT_ATTRS),
            "trend": forms.Select(attrs=SELECT_ATTRS),
            "source": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "related_stakeholders": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "related_stakeholders": _("Whoever this issue concerns, or who raised it. Only validated stakeholders can be linked."),
            "name": _('A fact that weighs on your security, for example "Two thirds of the staff work remotely".'),
            "category": _("Internal when it comes from your organisation, external when it comes from its environment."),
            "source": _('Where it was noticed, for example "Strategy committee of March".'),
            "description": _("What it is, and why it matters for security."),
            "impact_level": _("How much it weighs on what you want to achieve."),
            "trend": _("Improving when it weighs less than before, degrading when it weighs more."),
            "review_date": _("When to look at it again : the context of an organisation moves."),
            "status": _("Where you stand with it. It only filters this register : the lifecycle says whether this record is validated."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        category = self.fields.get("category")
        if category is not None:
            # The select shows which categories are internal and which are
            # external : picking one answers both questions, and the pair the
            # model refuses (RS-01) cannot be composed.
            labels = dict(IssueCategory.choices)
            category.choices = [
                ("", "---------"),
                (IssueType.INTERNAL.label, [(code, labels[code]) for code in INTERNAL_CATEGORIES]),
                (IssueType.EXTERNAL.label, [(code, labels[code]) for code in EXTERNAL_CATEGORIES]),
            ]
        _offer_what_can_be_linked(self, ("related_stakeholders",))

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        if category:
            # Set before the model is validated : its own rule then holds.
            self.instance.type = IssueType.INTERNAL if category in INTERNAL_CATEGORIES else IssueType.EXTERNAL
        return cleaned


class IssueCreateForm(CreationFormMixin, IssueBaseForm):
    """Issue creation : what the fact is, where it comes from and how much it weighs."""

    #: An issue is a fact of the context : nobody answers for it.
    owner_field = None
    #: How much it weighs has no default answer : the reader decides.
    decisions = ("impact_level",)

    steps = [
        Step(_("Identity"), "flag", ["name", "category", "impact_level", "scopes", "description"]),
    ]

    class Meta(IssueBaseForm.Meta):
        fields = ["scopes", "name", "description", "category", "impact_level"]


class IssueUpdateForm(IssueBaseForm):
    """Issue edition modal form."""


class StakeholderBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the stakeholder page : a step opens on its own
    # from its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "person-badge",
             ["name", ["type", "category"], "description", "scopes", "tags"],
             key="identity"),
        Step(_("Contact"), "envelope",
             ["contact_name", ["contact_email", "contact_phone"]],
             key="contact"),
        Step(_("Weight and follow-up"), "graph-up",
             [["influence_level", "interest_level"], ["review_date", "status"]],
             key="assessment",
             intro=_("How much this stakeholder can weigh on your security, and how closely it watches it. The two together say how much attention it deserves.")),
    ]

    class Meta:
        model = Stakeholder
        fields = [
            "scopes", "name", "type", "category", "description",
            "contact_name", "contact_email", "contact_phone",
            "influence_level", "interest_level", "status", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "contact_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "contact_email": forms.EmailInput(attrs=FORM_WIDGET_ATTRS),
            "contact_phone": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "influence_level": forms.Select(attrs=SELECT_ATTRS),
            "interest_level": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('A person, a group or an organisation, for example "Our clients" or "The data protection authority".'),
            "type": _("Internal when it is part of your organisation, external otherwise."),
            "category": "",
            "description": _("Who it is, and what links it to you."),
            "contact_name": _("Whoever you would write to."),
            "contact_email": "",
            "contact_phone": "",
            "influence_level": _("How much it can force your hand : a regulator is high, a prospect is low."),
            "interest_level": _("How closely it watches what you do about security."),
            "review_date": _("When to check that what it expects has not changed."),
            "status": _("Whether it still concerns you. It only filters this register : the lifecycle says whether this record is validated."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }


class StakeholderCreateForm(CreationFormMixin, StakeholderBaseForm):
    """Stakeholder creation : who it is and how much it weighs."""

    #: A stakeholder is a fact of the context : nobody answers for it.
    owner_field = None
    #: Its weight has no default answer : the reader decides.
    decisions = ("influence_level", "interest_level")

    steps = [
        Step(_("Identity"), "person-badge",
             ["name", ["type", "category"], ["influence_level", "interest_level"], "scopes"]),
    ]

    class Meta(StakeholderBaseForm.Meta):
        fields = ["scopes", "name", "type", "category", "influence_level", "interest_level"]


class StakeholderUpdateForm(StakeholderBaseForm):
    """Stakeholder edition modal form."""


class StakeholderExpectationForm(SteppedFormMixin, forms.ModelForm):
    """What a stakeholder expects : a row of its page, added and edited on one screen."""

    steps = [
        Step(_("Expectation"), "list-check", ["description", ["type", "priority"], "is_applicable"]),
    ]

    class Meta:
        model = StakeholderExpectation
        fields = ["description", "type", "priority", "is_applicable"]
        widgets = {
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "is_applicable": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "description": _('What the stakeholder expects of you, for example "To be told of a data breach within 72 hours".'),
            "type": _("A requirement binds you (a law, a contract), an expectation is what the stakeholder counts on, a need is what it depends on."),
            "priority": _("How much the stakeholder cares that you meet it."),
            "is_applicable": _("Untick when you decide not to take it into account."),
        }


class ObjectiveBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the objective page : a step opens on its own from
    # its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "bullseye",
             ["name", ["category", "type"], "owner", "description", "scopes", "tags"],
             key="identity"),
        Step(_("Measurement"), "rulers",
             [["target_value", "unit"], "measurement_method", "measurement_frequency"],
             key="measurement",
             intro=_("An objective is reached or it is not : say which figure tells, and how it is read.")),
        Step(_("Progress and dates"), "graph-up",
             [["current_value", "progress_percentage"], ["target_date", "review_date"], "status"],
             key="progress"),
        Step(_("Relations"), "diagram-3",
             ["related_issues", "related_stakeholders", "parent_objective"],
             key="relations"),
    ]

    class Meta:
        model = Objective
        fields = [
            "scopes", "name", "description",
            "category", "type", "target_value", "current_value", "unit",
            "measurement_method", "measurement_frequency", "target_date",
            "owner", "status", "progress_percentage",
            "related_issues", "related_stakeholders", "parent_objective",
            "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "target_value": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "current_value": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "unit": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "measurement_method": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "measurement_frequency": forms.Select(attrs=SELECT_ATTRS),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "progress_percentage": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 0, "max": 100}),
            "related_issues": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "related_stakeholders": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "parent_objective": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('What you want to reach, for example "Every newcomer is trained within a month".'),
            "category": _("What it serves first : restoring a server in four hours is about availability."),
            "type": _("Where it comes from : your security work, a rule to comply with, or the business."),
            "owner": _("Whoever answers for reaching it."),
            "description": _("Why it matters, and what reaching it changes."),
            "target_value": _('The figure that says it is reached, for example "95".'),
            "unit": _('What the figure counts, for example "%" or "hours".'),
            "measurement_method": _('Where the figure comes from, for example "Trained newcomers over arrivals, from the HR system".'),
            "measurement_frequency": "",
            "current_value": _("What you read last."),
            "progress_percentage": _("An objective marked as achieved must be at 100."),
            "target_date": _("The day you will say whether it is reached."),
            "review_date": _("When to check that it still makes sense."),
            "status": _("Where it stands. Marking it achieved asks for a progress of 100 %."),
            "related_issues": _("The issues this objective answers. Only validated issues can be linked."),
            "related_stakeholders": _("Whoever expects it of you. Only validated stakeholders can be linked."),
            "parent_objective": _("The wider objective this one contributes to. It must share a scope with it."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pick_among_active_people(self, ("owner",))
        parent = self.fields.get("parent_objective")
        if parent is not None and self.instance.pk:
            # An objective is not its own parent.
            parent.queryset = parent.queryset.exclude(pk=self.instance.pk)
        _offer_what_can_be_linked(self, ("related_issues", "related_stakeholders", "parent_objective"))


class ObjectiveCreateForm(CreationFormMixin, ObjectiveBaseForm):
    """Objective creation : what is aimed at, what it serves, who answers for it and for when.

    Opened from an issue (``?issue=``), the objective answers that issue : the
    link is carried by the form, never asked.
    """

    steps = [
        Step(_("Identity"), "bullseye",
             ["name", ["category", "type"], ["owner", "target_date"], "scopes", "related_issues"]),
    ]

    class Meta(ObjectiveBaseForm.Meta):
        fields = ["scopes", "name", "category", "type", "owner", "target_date", "related_issues"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        answered = self.fields.get("related_issues")
        if answered is not None:
            if self.initial.get("related_issues") or (self.is_bound and self.data.get("related_issues")):
                answered.widget = forms.MultipleHiddenInput()
            else:
                # The sixth question of the screen is not this one : the
                # issues it answers are picked on its page.
                del self.fields["related_issues"]


class ObjectiveUpdateForm(ObjectiveBaseForm):
    """Objective edition modal form."""


class SwotAnalysisBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step, the card of the analysis page that opens it (``?section=identity``) :
    # the four boxes and the strategies are worked on the page itself.
    steps = [
        Step(_("Identity"), "grid-3x3",
             ["name", ["analysis_date", "review_date"], "description", "scopes", "tags"],
             key="identity"),
    ]

    class Meta:
        model = SwotAnalysis
        fields = [
            "scopes", "name", "description", "analysis_date",
            "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4, "class": "form-control no-richtext"}),
            "analysis_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('What it looks at, for example "Security of the customer portal, 2027".'),
            "analysis_date": _("The day the four boxes were filled, with your team if you can."),
            "review_date": _("When to fill them again : once a year is common."),
            "description": _("Why it was done, and who took part."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }


class SwotAnalysisCreateForm(CreationFormMixin, SwotAnalysisBaseForm):
    """SWOT analysis creation : what it looks at and when. Its boxes are filled on its page."""

    #: An analysis is the work of a team : nobody answers for it by creating it.
    owner_field = None

    steps = [
        Step(_("Identity"), "grid-3x3", ["name", "analysis_date", "scopes", "description"]),
    ]

    class Meta(SwotAnalysisBaseForm.Meta):
        fields = ["scopes", "name", "description", "analysis_date"]


class SwotAnalysisUpdateForm(SwotAnalysisBaseForm):
    """SWOT analysis edition modal form."""


class SwotItemForm(forms.ModelForm):
    class Meta:
        model = SwotItem
        fields = ["quadrant", "description", "impact_level", "order"]
        widgets = {
            "quadrant": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3, "class": "form-control no-richtext"}),
            "impact_level": forms.Select(attrs=SELECT_ATTRS),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }


class SwotStrategyForm(forms.ModelForm):
    class Meta:
        model = SwotStrategy
        fields = ["quadrant", "description", "order"]
        widgets = {
            "quadrant": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3, "class": "form-control no-richtext"}),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }


class ResponsibilityForm(forms.ModelForm):
    """Responsibility create / edit modal, nested under a Role."""

    class Meta:
        model = Responsibility
        fields = ["description", "raci_type", "related_activity"]
        widgets = {
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3, "class": "form-control no-richtext"}),
            "raci_type": forms.Select(attrs=SELECT_ATTRS),
            "related_activity": forms.Select(attrs=SELECT_ATTRS),
        }
        help_texts = {
            "description": _("What this role is responsible for."),
            "raci_type": _("Responsible does the work, Accountable answers for the result, Consulted is asked before, Informed is told after."),
            "related_activity": _("Activity this responsibility relates to, if any."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["related_activity"].queryset = Activity.objects.order_by("name")
        self.fields["related_activity"].required = False


class RoleBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the role page : a step opens on its own from its
    # card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "shield-check",
             ["name", ["type", "source_standard"], "description", "is_mandatory", "scopes", "tags", "status"],
             key="identity"),
        Step(_("Who holds it"), "people", ["assigned_users"], key="assignment"),
    ]

    class Meta:
        model = Role
        fields = [
            "scopes", "name", "description", "type", "assigned_users",
            "is_mandatory", "source_standard", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "assigned_users": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "is_mandatory": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "source_standard": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('What the role is called in your organisation, for example "Information security officer".'),
            "type": _('Governance decides, operational carries out, support helps, and "Control" checks what the others do.'),
            "source_standard": _('The text that asks for this role, for example "ISO 27001, clause 5.3".'),
            "description": _("What whoever holds it answers for, in a sentence or two."),
            "assigned_users": _("One or several people. A mandatory role nobody holds is flagged on its page."),
            "is_mandatory": _("Tick when a standard or a law asks for it : the role is then flagged while nobody holds it."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "status": _("Whether the role is still in use. It only filters this register : the lifecycle says whether this record is validated."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        holders = self.fields.get("assigned_users")
        if holders is not None:
            from django.contrib.auth import get_user_model
            from django.db.models import Q

            # Active accounts, plus whoever already holds the role : saving it
            # again neither refuses nor drops a person who left since.
            people = get_user_model().objects
            held = self.instance.assigned_users.values_list("pk", flat=True) if self.instance.pk else []
            holders.queryset = people.filter(Q(is_active=True) | Q(pk__in=list(held))).order_by(
                "first_name", "last_name", "email",
            )


class RoleCreateForm(CreationFormMixin, RoleBaseForm):
    """Role creation : what it is called, what kind it is, and who holds it."""

    #: A role is held, not owned : whoever creates it is not put on it.
    owner_field = None

    steps = [
        Step(_("Identity"), "shield-check", ["name", "type", "assigned_users", "scopes", "description"]),
    ]

    class Meta(RoleBaseForm.Meta):
        fields = ["scopes", "name", "description", "type", "assigned_users"]


class RoleUpdateForm(RoleBaseForm):
    """Role edition modal form."""


class ActivityBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the activity page : a step opens on its own from
    # its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "activity",
             ["name", ["type", "criticality"], "owner", "description", "scopes", "tags", "status"],
             key="identity"),
        Step(_("Relations"), "diagram-3",
             ["parent_activity", "related_objectives", "related_stakeholders"],
             key="relations"),
    ]

    class Meta:
        model = Activity
        fields = [
            "scopes", "name", "description",
            "type", "criticality", "owner", "parent_activity",
            "related_objectives", "related_stakeholders", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "parent_activity": forms.Select(attrs=SELECT_ATTRS),
            "related_objectives": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "related_stakeholders": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('What your organisation does, for example "Billing customers" or "Running the plants".'),
            "type": _("Core business earns the revenue, support makes it possible, management steers."),
            "criticality": _("How much the organisation suffers when it stops."),
            "owner": _("Whoever answers for it running."),
            "description": _("What it covers, from where it starts to what it delivers."),
            "parent_activity": _("The wider activity this one is a part of. Only a validated activity can be chosen."),
            "related_objectives": _("The objectives it helps to reach. Only validated objectives can be linked."),
            "related_stakeholders": _("Whoever it serves or depends on. Only validated stakeholders can be linked."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "status": _("Whether it is carried out today. It only filters this register : the lifecycle says whether this record is validated."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pick_among_active_people(self, ("owner",))
        parent = self.fields.get("parent_activity")
        if parent is not None and self.instance.pk:
            # An activity is not a part of itself.
            parent.queryset = parent.queryset.exclude(pk=self.instance.pk)
        _offer_what_can_be_linked(self, ("parent_activity", "related_objectives", "related_stakeholders"))


class ActivityCreateForm(CreationFormMixin, ActivityBaseForm):
    """Activity creation : what is done, how much it matters and who answers for it."""

    steps = [
        Step(_("Identity"), "activity", ["name", ["type", "criticality"], "owner", "scopes", "description"]),
    ]

    class Meta(ActivityBaseForm.Meta):
        fields = ["scopes", "name", "description", "type", "criticality", "owner"]


class ActivityUpdateForm(ActivityBaseForm):
    """Activity edition modal form."""


def _site_tree_choices(queryset):
    """Build tree-ordered (pk, label) choices with full path labels (A / B / C)."""
    sites = list(queryset.select_related("parent_site"))
    by_parent = {}
    for s in sites:
        by_parent.setdefault(s.parent_site_id, []).append(s)

    choices = []
    visited = set()

    def walk(parent_id, path):
        for s in sorted(by_parent.get(parent_id, []), key=lambda x: x.name):
            full_path = path + [s.name]
            choices.append((s.pk, " / ".join(full_path)))
            visited.add(s.pk)
            walk(s.pk, full_path)

    walk(None, [])

    for s in sites:
        if s.pk not in visited:
            choices.append((s.pk, s.name))

    return choices


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = [
            "name", "type", "address", "description", "parent_site", "tags",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "address": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "parent_site": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Site.objects.exclude(workflow_state="archived")
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        field = self.fields["parent_site"]
        field.queryset = qs
        field.choices = [("", field.empty_label or "---------")] + _site_tree_choices(qs)


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "color": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "type": "color", "style": "width:80px;height:38px;padding:4px"}),
        }


class IndicatorBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "bar-chart-line",
             ["name", ["collection_method", "format"], "description"]),
        Step(_("Format & thresholds"), "sliders",
             [["unit", "expected_level"],
              ["critical_threshold_operator", "critical_threshold_value"],
              ["critical_threshold_min", "critical_threshold_max"]]),
        Step(_("Review & status"), "calendar-event",
             [["review_frequency", "first_review_date"], "status", "scopes", "tags"]),
    ]

    class Meta:
        model = Indicator
        fields = [
            "scopes", "name", "description",
            "collection_method", "format", "unit",
            "expected_level", "critical_threshold_operator",
            "critical_threshold_value",
            "critical_threshold_min", "critical_threshold_max",
            "review_frequency",
            "first_review_date", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "collection_method": forms.Select(attrs=SELECT_ATTRS),
            "format": forms.Select(attrs={**SELECT_ATTRS, "id": "id_format"}),
            "unit": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "expected_level": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "critical_threshold_operator": forms.Select(attrs=SELECT_ATTRS),
            "critical_threshold_value": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "critical_threshold_min": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "any"}),
            "critical_threshold_max": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "any"}),
            "review_frequency": forms.Select(attrs=SELECT_ATTRS),
            "first_review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the indicator."),
            "collection_method": _("How the indicator is collected."),
            "format": _("Data format of the indicator."),
            "description": _("What the indicator measures."),
            "unit": _("Unit of measure."),
            "expected_level": _("Target level to reach."),
            "critical_threshold_operator": _("Comparison used to flag a critical value."),
            "critical_threshold_value": _("Value beyond which the indicator is critical."),
            "critical_threshold_min": _("Lower bound of the acceptable range."),
            "critical_threshold_max": _("Upper bound of the acceptable range."),
            "review_frequency": _("How often the indicator is reviewed."),
            "first_review_date": _("Date of the first review."),
            "status": _("Lifecycle state of the indicator."),
            "scopes": _("Organizational scopes this indicator applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class IndicatorCreateForm(IndicatorBaseForm):
    """Indicator creation modal form."""


class IndicatorUpdateForm(IndicatorBaseForm):
    """Indicator edition modal form."""


class PredefinedIndicatorBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Form for creating predefined Cairn indicators."""

    steps = [
        Step(_("Identity"), "bar-chart-line",
             ["name", ["internal_source", "internal_source_parameter"], "description"]),
        Step(_("Format & thresholds"), "sliders",
             ["expected_level",
              ["critical_threshold_operator", "critical_threshold_value"],
              ["critical_threshold_min", "critical_threshold_max"]]),
        Step(_("Review & status"), "calendar-event",
             [["review_frequency", "first_review_date"], "status", "scopes", "tags"]),
    ]

    class Meta:
        model = Indicator
        fields = [
            "scopes", "name", "description",
            "internal_source", "internal_source_parameter",
            "expected_level", "critical_threshold_operator",
            "critical_threshold_value",
            "critical_threshold_min", "critical_threshold_max",
            "review_frequency",
            "first_review_date", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "internal_source": forms.Select(attrs=SELECT_ATTRS),
            "internal_source_parameter": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "expected_level": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "critical_threshold_operator": forms.Select(attrs=SELECT_ATTRS),
            "critical_threshold_value": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "critical_threshold_min": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "any"}),
            "critical_threshold_max": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "any"}),
            "review_frequency": forms.Select(attrs=SELECT_ATTRS),
            "first_review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the indicator."),
            "internal_source": _("Cairn data source feeding this indicator."),
            "internal_source_parameter": _("Parameter passed to the data source."),
            "description": _("What the indicator measures."),
            "expected_level": _("Target level to reach."),
            "critical_threshold_operator": _("Comparison used to flag a critical value."),
            "critical_threshold_value": _("Value beyond which the indicator is critical."),
            "critical_threshold_min": _("Lower bound of the acceptable range."),
            "critical_threshold_max": _("Upper bound of the acceptable range."),
            "review_frequency": _("How often the indicator is reviewed."),
            "first_review_date": _("Date of the first review."),
            "status": _("Lifecycle state of the indicator."),
            "scopes": _("Organizational scopes this indicator applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class PredefinedIndicatorCreateForm(PredefinedIndicatorBaseForm):
    """Predefined indicator creation modal form."""


class PredefinedIndicatorUpdateForm(PredefinedIndicatorBaseForm):
    """Predefined indicator edition modal form."""


class IndicatorMeasurementForm(forms.ModelForm):
    class Meta:
        model = IndicatorMeasurement
        fields = ["value", "notes"]
        widgets = {
            "value": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "placeholder": _("Value")}),
            "notes": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "placeholder": _("Notes (optional)")}),
        }

    def __init__(self, *args, indicator_format=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.indicator_format = indicator_format
        if indicator_format == "boolean":
            self.fields["value"] = forms.ChoiceField(
                choices=[("true", _("True")), ("false", _("False"))],
                widget=forms.Select(attrs=SELECT_ATTRS),
                label=self.fields["value"].label,
            )
        elif indicator_format == "number":
            self.fields["value"].widget = forms.TextInput(
                attrs={**FORM_WIDGET_ATTRS, "inputmode": "decimal", "placeholder": _("Value")},
            )

    def clean_value(self):
        value = self.cleaned_data.get("value", "")
        if self.indicator_format == "number":
            # Normalize locale-specific separators: strip thousand separators
            # (space, non-breaking space) and convert decimal comma to dot.
            normalized = value.replace("\u00a0", "").replace("\u202f", "").replace(" ", "").replace(",", ".")
            try:
                number = float(normalized)
            except (ValueError, TypeError):
                raise forms.ValidationError(_("Please enter a valid number."))
            # Reject "nan" / "inf": they parse as floats but later crash the
            # dashboard's number formatting (int(nan) -> ValueError).
            if not math.isfinite(number):
                raise forms.ValidationError(_("Please enter a valid number."))
            return normalized
        return value


class StakeholderFeedbackForm(forms.ModelForm):
    class Meta:
        model = StakeholderFeedback
        fields = [
            "stakeholder", "channel", "received_date", "subject", "content",
            "sentiment", "severity", "status", "response",
            "linked_issues", "linked_expectations",
            "scopes", "tags",
        ]
        widgets = {
            "stakeholder": forms.Select(attrs=SELECT_ATTRS),
            "channel": forms.Select(attrs=SELECT_ATTRS),
            "received_date": forms.DateInput(
                attrs={**FORM_WIDGET_ATTRS, "type": "date"},
            ),
            "subject": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "content": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "sentiment": forms.Select(attrs=SELECT_ATTRS),
            "severity": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "response": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "linked_issues": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "linked_expectations": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "scopes": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "tags": TAGS_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stakeholder"].queryset = Stakeholder.objects.order_by("name")
        self.fields["scopes"].queryset = Scope.objects.exclude(
            workflow_state="archived",
        ).order_by("name")
        self.fields["linked_issues"].queryset = Issue.objects.order_by("-updated_at")
        self.fields["linked_expectations"].queryset = (
            StakeholderExpectation.objects.select_related("stakeholder")
            .order_by("stakeholder__name")
        )

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Web forms of module 8 (controls).

Four rules hold for every form here:

**No form writes a derived or stamped field** : ``Control.effectiveness``,
``ControlTest.next_due_date`` / ``activated_on``, ``ControlTestRun.reviewed_*``
and the evidence size and SHA-256 are written by the models
(RG-CTL-07, RG-CTL-11, RG-CTL-13, RG-CTL-14). The state only changes through
the lifecycle stepper.

**Pickers offer ``linkable_or_linked()`` targets the user may see**
(RG-CTL-04). A link the user cannot see (outside their scopes) is not offered,
and it is kept on save rather than silently dropped.

**A frozen record renders frozen** : a retired control or test, and a run past
``draft`` (RG-CTL-09), open with every field disabled and refuse to validate.

**Plain text stays plain** : the procedure, acceptance criteria, sample and
observations are checked for emptiness by the lifecycle gates, so they are
plain text areas (``no-richtext``) rather than rich-text editors.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from compliance.constants import FindingType
from compliance.models import Framework, Requirement
from context.models import Scope
from context.widgets import ScopeTreeWidget
from core.lifecycle import linkable, linkable_or_linked, reportable, resolve_lifecycle
from core.modal_forms import CreationFormMixin, Step, SteppedFormMixin
from core.scoping import filter_queryset_by_scopes

from .constants import ALLOWED_EVIDENCE_EXTENSIONS, RUN_DRAFT
from .models import Control, ControlTest, ControlTestEvidence, ControlTestRun

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
MULTISELECT_ATTRS = {**SELECT_ATTRS, "size": 5}
RICH_TEXT_ATTRS = {**FORM_WIDGET_ATTRS, "rows": 6, "class": "form-control rich-text"}

# The finding types that fit a failed or partial test (RG-CTL-16) : a
# strength or an improvement opportunity is not what a failure raises.
RAISABLE_FINDING_TYPES = (
    FindingType.MAJOR_NON_CONFORMITY,
    FindingType.MINOR_NON_CONFORMITY,
    FindingType.OBSERVATION,
)


def _date_widget():
    return forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d")


def _textarea(rows=3):
    """A plain-text area : the shell turns every other ``textarea.form-control``
    into a rich-text editor, which would store HTML in a plain field."""
    return forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": rows, "class": "form-control no-richtext"})


def _is_new(instance):
    """UUID primary keys are set before the first save : ``pk`` is not the test."""
    return instance._state.adding


def _user_scope_ids(user):
    if user is None or user.is_superuser:
        return None
    return user.get_allowed_scope_ids()


def scoped(qs, user):
    """Restrict ``qs`` to what ``user`` may see (scope tenancy)."""
    scope_ids = _user_scope_ids(user)
    if scope_ids is None:
        return qs
    return filter_queryset_by_scopes(qs, scope_ids)


def _active_users(current_ids=()):
    User = get_user_model()
    return User.objects.filter(Q(is_active=True) | Q(pk__in=[i for i in current_ids if i])).order_by(
        "last_name", "first_name", "email",
    )


def _freeze(form, note):
    """Disable every field of a frozen record and say why : once at the top of
    the drawer (``_frozen_note.html``), and on the first field for the page form."""
    for field in form.fields.values():
        field.disabled = True
    first = next(iter(form.fields.values()), None)
    if first is not None:
        first.help_text = note
    form.frozen_note = note


class FrozenFormMixin:
    """A frozen form never validates : the refusal is a message on the form."""

    frozen_note = None

    def clean(self):
        cleaned = super().clean()
        if self.frozen_note:
            raise ValidationError(self.frozen_note)
        return cleaned


class ScopedRelationsMixin:
    """Scope-aware relation pickers that keep the links the user cannot see.

    ``relation_fields`` names the many-to-many fields whose picker offers the
    linkable targets in the user's scopes plus the targets already linked
    (RG-CTL-04). A target already linked but outside the user's scopes is not
    offered, and :meth:`_save_m2m` adds it back, so editing a control never
    drops a link its editor could not see.
    """

    relation_fields = ()

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self._hidden_links = {}
        instance = self.instance
        for name in self.relation_fields:
            if name not in self.fields:
                continue
            field = self.fields[name]
            linked = None if _is_new(instance) else getattr(instance, name).all()
            field.queryset = linkable_or_linked(scoped(field.queryset.model._default_manager.all(), user), linked)
            if linked is not None:
                visible = set(field.queryset.values_list("pk", flat=True))
                hidden = set(linked.values_list("pk", flat=True)) - visible
                if hidden:
                    self._hidden_links[name] = hidden
        if "scopes" in self.fields:
            self._init_scopes(user)

    def _init_scopes(self, user):
        archived = [step.code for step in resolve_lifecycle(Scope).archived_steps]
        qs = Scope.objects.exclude(workflow_state__in=archived)
        scope_ids = _user_scope_ids(user)
        if scope_ids is not None:
            qs = qs.filter(id__in=scope_ids)
        field = self.fields["scopes"]
        field.queryset = qs
        instance = self.instance
        selected_ids = []
        if not _is_new(instance):
            current = set(instance.scopes.values_list("pk", flat=True))
            selected_ids = list(current)
            hidden = current - set(qs.values_list("pk", flat=True))
            if hidden:
                self._hidden_links["scopes"] = hidden
        if hasattr(self.data, "getlist") and self.is_bound:
            selected_ids = self.data.getlist(self.add_prefix("scopes"))
        elif self.initial.get("scopes"):
            selected_ids = [getattr(s, "pk", s) for s in self.initial["scopes"]]
        field.widget.build_tree_data(qs, selected_ids)

    def _save_m2m(self):
        super()._save_m2m()
        for name, pks in self._hidden_links.items():
            getattr(self.instance, name).add(*pks)


# --- Control ------------------------------------------------------------------


class ControlForm(FrozenFormMixin, SteppedFormMixin, ScopedRelationsMixin, forms.ModelForm):
    """A control's identity and links (RG-CTL-01, RG-CTL-04). Retired : frozen.

    Each step is a section, and a card of the page of the control : the Edit
    button of a card opens its section alone.
    """

    relation_fields = (
        "requirements", "risks", "treatment_plans", "pacs_measures",
        "support_assets", "objectives", "policies",
    )

    steps = [
        Step(_("Identity"), "shield-check", [
            "name",
            ["theme", "nature", "automation"],
            ["owner", "implemented_on"],
            "scopes",
            "tags",
        ], key="identity"),
        Step(_("Description"), "text-left", ["description"], key="description"),
        Step(_("Requirements"), "list-check", ["requirements"], key="requirements"),
        Step(_("Risks and treatment"), "shield-exclamation", [
            "risks",
            "treatment_plans",
            "pacs_measures",
        ], key="risks"),
        Step(_("Support assets, objectives and documents"), "diagram-3", [
            "support_assets",
            "objectives",
            "policies",
        ], key="coverage"),
    ]

    class Meta:
        model = Control
        fields = [
            "name", "description", "theme", "nature", "automation", "owner", "implemented_on",
            "requirements", "risks", "treatment_plans", "pacs_measures",
            "support_assets", "objectives", "policies", "scopes", "tags",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs=RICH_TEXT_ATTRS),
            "theme": forms.Select(attrs=SELECT_ATTRS),
            "nature": forms.Select(attrs=SELECT_ATTRS),
            "automation": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "implemented_on": _date_widget(),
            "requirements": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "risks": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "treatment_plans": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "pacs_measures": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "support_assets": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "objectives": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "policies": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "scopes": ScopeTreeWidget(),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('What the organisation does, for example "Multi-factor authentication on remote access".'),
            "description": _("How the control operates day to day : who does what, with which tool, how often."),
            "theme": _("Organizational for rules and roles, people for staff, physical for premises, "
                       "technological for systems."),
            "nature": _("Whether the control prevents, detects or corrects an event."),
            "automation": _("How much of the control runs without a person."),
            "owner": _("The person accountable for the control operating. They receive the reminders of a "
                       "test that has no tester."),
            "implemented_on": _("Set when the control is declared implemented. It can be earlier, never in the future."),
            "requirements": _("The requirements this control satisfies, from any framework."),
            "risks": _("The risks the control treats. Each one shows it on its page, beside its residual level."),
            "treatment_plans": _("The treatment plans whose actions put this control in place or strengthen it."),
            "pacs_measures": _("The EBIOS RM security measures that create or reinforce it."),
            "support_assets": _('The systems, the premises or the teams the control applies to, for example '
                                '"Remote access gateway".'),
            "objectives": _("The objectives of the organisation this control helps to reach."),
            "policies": _("The documents that describe it : procedure, standard, policy."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        if "owner" in self.fields:
            self.fields["owner"].queryset = _active_users([instance.owner_id])
        if "requirements" in self.fields:
            requirements = self.fields["requirements"]
            requirements.queryset = requirements.queryset.select_related("framework").order_by(
                "framework__name", "requirement_number", "name",
            )
            requirements.label_from_instance = _requirement_label
        # A classification nobody chose reads as such, never as a default
        # (rule F8). One the form asks for (``decisions``) reads *Choose…*.
        for name in ("theme", "nature", "automation"):
            field = self.fields.get(name)
            if field is not None and name not in getattr(self, "decisions", ()):
                field.choices = [("", _("Not set")), *[c for c in field.choices if c[0] not in ("", None)]]
        if not _is_new(instance) and instance.is_terminal_state:
            _freeze(self, _("A retired control is a closed record and can no longer be edited."))


class ControlCreateForm(CreationFormMixin, ControlForm):
    """Control creation : what it is and who answers for it, on one screen.

    How it operates day to day may wait : it is asked before the control is
    planned. What it answers and where it applies are filled in on its page,
    which lists what the control still needs.
    """

    # "Technological" was saved for whoever did not choose.
    decisions = ("theme",)

    steps = [
        Step(_("Identity"), "shield-check", ["name", ["theme", "owner"], "scopes", "description"]),
    ]

    class Meta(ControlForm.Meta):
        fields = ["scopes", "name", "description", "theme", "owner"]


def _requirement_label(requirement):
    framework = requirement.framework
    prefix = framework.short_name or framework.name
    number = f"{requirement.requirement_number} " if requirement.requirement_number else ""
    return f"{prefix} : {number}{requirement.name}"


def _checklist_label(requirement):
    if requirement.requirement_number:
        return f"{requirement.requirement_number} {requirement.name}"
    return requirement.name


class RequirementChecklistWidget(forms.CheckboxSelectMultiple):
    """The requirements of a framework as a bounded checklist."""

    template_name = "controls/widgets/requirement_checklist.html"
    option_template_name = "controls/widgets/requirement_checklist_option.html"


class FromRequirementsForm(SteppedFormMixin, forms.Form):
    """RG-CTL-05 : pick a framework, then the uncovered requirements to bootstrap.

    The checklist lists the framework's linkable, applicable requirements that
    no control covers yet; all are ticked by default. The service re-checks
    each one, so a requirement covered in the meantime is skipped, not doubled.
    """

    steps = [Step(_("Requirements"), "list-check", ["framework", "requirements"])]

    framework = forms.ModelChoiceField(
        label=_("Framework"), queryset=Framework.objects.none(),
        widget=forms.Select(attrs=SELECT_ATTRS),
        help_text=_("The framework whose requirements the new controls answer. They take its scopes."),
    )
    requirements = forms.ModelMultipleChoiceField(
        label=_("Requirements without a control"), queryset=Requirement.objects.none(), required=False,
        widget=RequirementChecklistWidget(),
        help_text=_("One proposed control is created for each ticked requirement, named after it."),
    )

    def __init__(self, *args, user=None, framework=None, reload_url=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        frameworks = scoped(reportable(Framework.objects.all()), user).order_by("name")
        field = self.fields["framework"]
        field.queryset = frameworks
        if reload_url:
            # In the drawer, choosing a framework reloads the form with its checklist.
            field.widget.attrs.update({
                "hx-get": reload_url, "hx-target": "#drawer-form-content",
                "hx-swap": "innerHTML", "hx-trigger": "change", "hx-disabled-elt": "this",
            })
        if framework is None and self.is_bound:
            framework = self._bound_framework(frameworks)
        self.framework = framework
        requirements = self.fields["requirements"]
        if framework is not None:
            # Any requirement of the framework validates (one covered in the
            # meantime is then reported as skipped by the service); only the
            # uncovered ones are listed.
            uncovered = list(self.uncovered_requirements(framework))
            requirements.queryset = framework.requirements.all()
            requirements.widget.choices = [(r.pk, _checklist_label(r)) for r in uncovered]
            self.has_uncovered = bool(uncovered)
            if not self.is_bound:
                self.initial["framework"] = framework.pk
                self.initial["requirements"] = [r.pk for r in uncovered]
        else:
            requirements.help_text = _("Choose a framework first : its requirements without a control are listed here.")

    def _bound_framework(self, frameworks):
        raw = self.data.get(self.add_prefix("framework"))
        if not raw:
            return None
        try:
            return frameworks.filter(pk=raw).first()
        except (ValueError, ValidationError):
            return None

    @staticmethod
    def uncovered_requirements(framework):
        return (
            linkable(framework.requirements.filter(is_applicable=True))
            .filter(controls__isnull=True)
            .order_by("requirement_number", "created_at")
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("framework") is not None and not cleaned.get("requirements"):
            if getattr(self, "has_uncovered", False):
                self.add_error("requirements", _("Tick at least one requirement."))
            else:
                self.add_error("requirements", _("Every applicable requirement of this framework already has a control."))
        return cleaned


# --- ControlTest --------------------------------------------------------------


class ControlTestForm(FrozenFormMixin, SteppedFormMixin, forms.ModelForm):
    """How a control is tested (RG-CTL-06). The next due date is derived (RG-CTL-07).

    Retired : frozen. Each step is a section, and a card of the page of the
    test : the Edit button of a card opens its section alone.
    """

    steps = [
        Step(_("Identity"), "clipboard-check", ["name", "method", "objective"], key="identity"),
        Step(
            _("Procedure"), "list-ol", ["procedure", "acceptance_criteria"], key="procedure",
            intro=_("Both are asked before the test is activated : a test with no pass criterion proves nothing."),
        ),
        Step(_("Planning"), "calendar-event", [
            ["frequency_months", "tester"],
            "first_due_date",
            "tags",
        ], key="planning"),
    ]

    class Meta:
        model = ControlTest
        fields = [
            "name", "method", "frequency_months", "objective", "procedure", "acceptance_criteria",
            "tester", "first_due_date", "tags",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "method": forms.Select(attrs=SELECT_ATTRS),
            "frequency_months": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 1, "max": 36}),
            "objective": _textarea(2),
            "procedure": _textarea(6),
            "acceptance_criteria": _textarea(3),
            "tester": forms.Select(attrs=SELECT_ATTRS),
            "first_due_date": _date_widget(),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer.
        help_texts = {
            "name": _('What is checked, for example "Quarterly sample of remote logins".'),
            "method": _("How the evidence is obtained : inquiry, observation, inspection, reperformance or an automated check."),
            "frequency_months": _("Months between two runs, from 1 to 36. The next run falls due this long after the last validated one."),
            "objective": _("What the test establishes : the design of the control, or that it operates effectively."),
            "procedure": _("The steps the tester follows, in order, with the tools and the data they use."),
            "acceptance_criteria": _('What a pass looks like, for example "Every login of the sample used a second factor".'),
            "tester": _("The person who performs the runs by default. They receive the reminders when a run falls due."),
            "first_due_date": _("When the first run is due. Leave empty to make it due on activation."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        # A form opened on one section, or the creation form, carries a part
        # of these fields only.
        if "tester" in self.fields:
            self.fields["tester"].queryset = _active_users([self.instance.tester_id])
        if not _is_new(self.instance) and self.instance.is_terminal_state:
            _freeze(self, _("A retired test is a closed record and can no longer be edited."))


class ControlTestCreateForm(CreationFormMixin, ControlTestForm):
    """Test creation : what is checked, how, how often and by whom, on one screen.

    The procedure and the acceptance criteria are written on the page of the
    test, which asks for them before it is activated.
    """

    # The tester is the control's owner (set by the view), else whoever
    # creates the test.
    owner_field = "tester"
    # "Inspection" was saved for whoever did not choose.
    decisions = ("method",)

    steps = [
        Step(_("Identity"), "clipboard-check", ["name", ["method", "frequency_months"], "tester"]),
    ]

    class Meta(ControlTestForm.Meta):
        fields = ["name", "method", "frequency_months", "tester"]


# --- ControlTestRun -----------------------------------------------------------


class ControlTestRunForm(FrozenFormMixin, SteppedFormMixin, forms.ModelForm):
    """A run, editable in ``draft`` only (RG-CTL-09); RG-CTL-10 is checked at submission.

    Each step is a section, and a card of the page of the run.
    """

    steps = [
        Step(_("Execution"), "person-check", [
            ["performed_by", "performed_on"],
            ["period_start", "period_end"],
            "sample_description",
        ], key="execution"),
        Step(
            _("Result"), "clipboard-data", ["result", "observations"], key="result",
            intro=_("The result is asked before the run is submitted for review, and so are the observations when "
                    "it is partial or failed."),
        ),
    ]

    class Meta:
        model = ControlTestRun
        fields = [
            "performed_by", "performed_on", "period_start", "period_end",
            "sample_description", "result", "observations",
        ]
        widgets = {
            "performed_by": forms.Select(attrs=SELECT_ATTRS),
            "performed_on": _date_widget(),
            "period_start": _date_widget(),
            "period_end": _date_widget(),
            "sample_description": _textarea(3),
            "result": forms.Select(attrs=SELECT_ATTRS),
            "observations": _textarea(5),
        }
        help_texts = {
            "performed_by": _("The person who performed the test. They cannot validate their own run."),
            "performed_on": _("The date of the test. It cannot be in the future."),
            "period_start": _("For example the first day of the quarter whose logins are sampled. Leave it empty "
                              "when the test looks at one moment only."),
            "period_end": _("The end of the period the test covers. It cannot be after the test date."),
            "sample_description": _("The population and the sample tested, e.g. 25 of the 1,240 remote logins of the quarter."),
            "result": _("Judged against the acceptance criteria of the test. Leave it empty while the test is under way."),
            "observations": _('What was found, for example "3 of the 25 logins had no second factor". It becomes the '
                              "description of a finding raised from the run."),
        }

    def __init__(self, *args, user=None, test=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if test is not None and _is_new(self.instance):
            self.instance.test = test
        if "performed_by" in self.fields:
            self.fields["performed_by"].queryset = _active_users([self.instance.performed_by_id])
        if "result" in self.fields:
            self.fields["result"].choices = [("", _("Not recorded yet"))] + list(self.fields["result"].choices)[1:]
        if not _is_new(self.instance) and self.instance.workflow_state != RUN_DRAFT:
            _freeze(self, _("A submitted test run is frozen : its content can no longer be changed."))


class ControlTestRunCreateForm(ControlTestRunForm):
    """Run creation : who tested, when and, once it is known, with what result, on one screen.

    The period, the sample and the evidence are added on the page of the run,
    which asks for what remains before it is submitted for review.
    """

    steps = [
        Step(_("Execution"), "person-check", [["performed_by", "performed_on"], "result", "observations"]),
    ]

    class Meta(ControlTestRunForm.Meta):
        fields = ["performed_by", "performed_on", "result", "observations"]


# --- Evidence -----------------------------------------------------------------


class EvidenceForm(SteppedFormMixin, forms.ModelForm):
    """One evidence file (RG-CTL-13). Size and SHA-256 are stamped by the model."""

    steps = [Step(_("Evidence"), "paperclip", ["file", "description"])]

    class Meta:
        model = ControlTestEvidence
        fields = ["file", "description"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={
                **FORM_WIDGET_ATTRS, "accept": ",".join(f".{ext}" for ext in ALLOWED_EVIDENCE_EXTENSIONS),
            }),
            "description": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
        }
        help_texts = {
            "file": _("An export, a screenshot, a signed review sheet (25 MB max). Its SHA-256 is recorded."),
            "description": _("What the file shows, e.g. Login export for the third quarter."),
        }

    def __init__(self, *args, user=None, run=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if run is not None:
            self.instance.run = run
        self.instance.uploaded_by = user
        self.fields["file"].required = True

    def save(self, commit=True):
        upload = self.cleaned_data.get("file")
        if upload is not None and not self.instance.original_filename:
            self.instance.original_filename = (getattr(upload, "name", "") or "")[:255]
        return super().save(commit=commit)


# --- Finding (RG-CTL-16) ------------------------------------------------------


class RaiseFindingForm(SteppedFormMixin, forms.Form):
    steps = [Step(_("Finding"), "exclamation-diamond", ["finding_type", "recommendation"])]

    finding_type = forms.ChoiceField(
        label=_("Finding type"), widget=forms.Select(attrs=SELECT_ATTRS),
        help_text=_("A judgement on the gap : a major or minor nonconformity, or an observation."),
    )
    recommendation = forms.CharField(
        label=_("Recommendation"), required=False, widget=_textarea(4),
        help_text=_("Optional : what should be done to close the gap. The run's observations become the finding's description."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["finding_type"].choices = [(value.value, value.label) for value in RAISABLE_FINDING_TYPES]
        self.fields["finding_type"].initial = FindingType.MINOR_NON_CONFORMITY


# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Model forms for module 6 (incidents).

Three rules govern every form in this file, and each one is load-bearing:

**No form ever exposes a field the lifecycle writes** (RG-INC-12). The phase
stamps, ``initial_severity``, the triage verdict, the qualification stamps, the
sealing stamp, the frozen clock and ``workflow_state`` itself are written by the
``transition_to()`` overrides and by nothing else. A form that offered them
would let an operator type a date the register is supposed to *prove*.

**Context the view holds is stamped on the instance before validation, never
after.** The parent incident, the parent evidence item and the acting user are
read by the models' own ``clean()``, which runs inside
``ModelForm._post_clean()`` : stamping them in the view's ``form_valid()`` is
too late, and the error surfaces as a puzzling validation failure or an
``IntegrityError``. Where the field is *exposed* on the form, the acting user is
offered as an ``initial`` instead, so the operator can name somebody else.

**Every field a model's ``clean()`` can key an error on is present on the form
that edits that model.** ``ModelForm.add_error()`` raises ``ValueError`` when a
model-level error names a field the form does not declare, so an omission there
is a 500, not a validation message.
"""

from datetime import timedelta

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from context.models import Scope
from context.widgets import ScopeTreeWidget
from core.lifecycle import linkable_or_linked, resolve_lifecycle
from core.modal_forms import Step, SteppedFormMixin
from risks.constants import ThreatCategory

from .constants import (
    ClockAnchor,
    ControllerRole,
    CustodyAction,
    NotificationRegime,
    TimelineEntrySource,
)
from .models import (
    EvidenceCustodyEvent,
    Incident,
    IncidentEvidence,
    IncidentNotification,
    IncidentResponseAction,
    IncidentResponsePlan,
    IncidentTimelineEntry,
    NotificationFiling,
    PersonalDataBreach,
    PostIncidentReview,
    ReportingAuthority,
    ReportingObligationTemplate,
    SecurityEvent,
)
from .models.evidence import EVIDENCE_ACQUISITION_FIELDS
from .models.notification import (
    NotificationDecision,
    ObligationSource,
    notification_max_proof_bytes,
)

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}

#: Multi-selects are the widgets that hurt most on a phone, so every one of them
#: is a plain sized select the mobile keyboard can scroll rather than a control
#: that opens its own overlay.
MULTISELECT_ATTRS = {**SELECT_ATTRS, "size": 5}


def _date_widget():
    """A native date picker, in the format the browser posts back."""
    return forms.DateInput(
        attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"
    )


def _datetime_widget():
    """A native date-and-time picker : the module runs on minutes, not days."""
    return forms.DateTimeInput(
        attrs={**FORM_WIDGET_ATTRS, "type": "datetime-local"},
        format="%Y-%m-%dT%H:%M",
    )


def _textarea(rows=3):
    return forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": rows})


def _tristate_widget():
    """The three-state verdict widget.

    ``None`` is a real answer everywhere in this module : *not yet determined*
    is not *no*, and a checkbox cannot say so.
    """
    return forms.NullBooleanSelect(attrs=SELECT_ATTRS)


# --- Picker helpers ---------------------------------------------------------
#
# Link pickers go through `linkable_or_linked()` so a new link can only target a
# linkable element, while an element that was linked before it left its linkable
# state stays selected instead of silently disappearing from the form.


def _is_new(instance):
    """Whether the instance has never been saved.

    ``instance.pk`` is **not** the test : every model in this module carries a
    UUID primary key with a ``default``, so an unsaved instance already has one
    and every ``if self.instance.pk`` reads as an edit.
    """
    return instance._state.adding


def _restrict_m2m(form, *names):
    """Restrict each many-to-many picker, keeping what is already linked."""
    for name in names:
        field = form.fields[name]
        linked = (
            None if _is_new(form.instance) else getattr(form.instance, name).all()
        )
        field.queryset = linkable_or_linked(field.queryset, linked)


def _restrict_fk(form, *names):
    """Restrict each foreign-key picker, keeping the value already chosen."""
    for name in names:
        field = form.fields[name]
        current_id = getattr(form.instance, f"{name}_id", None)
        linked = (
            field.queryset.model.objects.filter(pk=current_id)
            if current_id
            else None
        )
        field.queryset = linkable_or_linked(field.queryset, linked)


def _freeze(form, names, note):
    """Disable a set of fields and say why, in one place.

    A disabled field is ignored on submit and keeps its stored value, which is
    exactly what the models' write-once guards require : they raise a
    ``ValidationError`` from ``save()``, far too late for a form to render it
    against the field the operator touched.
    """
    for name in names:
        if name not in form.fields:
            continue
        form.fields[name].disabled = True
        form.fields[name].help_text = note


class ScopedFormMixin:
    """Populate the scopes tree widget with the user's accessible scopes.

    Mixed into **every** form in this module, including the ones editing a
    record that inherits its tenancy from its parent incident and has no scope
    picker of its own : the mixin is inert when there is no ``scopes`` field, so
    a view can pass ``user`` uniformly without the drawer breaking on half the
    module's forms.
    """

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if "scopes" not in self.fields:
            return
        archived = [step.code for step in resolve_lifecycle(Scope).archived_steps]
        qs = Scope.objects.exclude(workflow_state__in=archived)
        if user and not user.is_superuser:
            scope_ids = user.get_allowed_scope_ids()
            if scope_ids is not None:
                qs = qs.filter(id__in=scope_ids)
        field = self.fields["scopes"]
        field.queryset = qs
        selected_ids = []
        if self.instance and not _is_new(self.instance):
            selected_ids = list(self.instance.scopes.values_list("pk", flat=True))
        elif hasattr(self.data, "getlist"):
            # A bound create form re-renders with what was posted. Guarded
            # because a test may bind a plain dict, which has no `getlist`.
            selected_ids = self.data.getlist(self.add_prefix("scopes"))
        field.widget.build_tree_data(qs, selected_ids)


class LabelListField(forms.Field):
    """A free list of labels stored in a ``JSONField``, edited one per line.

    ``data_categories`` and ``data_subject_categories`` carry the same free
    value shape as an essential asset's GDPR categories, so the two registers
    stay comparable and there is no enum to offer as a picker. The field parses
    lines (or commas) into the list the model validates, and renders the stored
    list back one per line.
    """

    widget = forms.Textarea

    def prepare_value(self, value):
        if isinstance(value, (list, tuple)):
            return "\n".join(str(item) for item in value)
        return value

    def to_python(self, value):
        if value in self.empty_values:
            return []
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        lines = str(value).replace(",", "\n").splitlines()
        return [line.strip() for line in lines if line.strip()]


# --- Incident ---------------------------------------------------------------


class IncidentForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Declare or edit an incident file (A.5.26).

    Everything the lifecycle owns is absent by construction : ``workflow_state``,
    the six phase stamps (``declared_at``, ``triaged_at``, ``contained_at``,
    ``eradicated_at``, ``recovered_at``, ``closed_at``) and ``initial_severity``,
    which is copied once at triage precisely so later severity drift is a
    difference between two columns rather than a history diff to read.

    ``awareness_at`` **is** editable, and deliberately so : it is the legal
    clock anchor every statutory deadline in the module derives from, facts
    about when the organisation became aware do change, and the model refuses a
    gap with the technical detection that carries no written justification.
    """

    steps = [
        Step(_("Identity"), "exclamation-octagon", [
            "title",
            ["category", "severity"],
            ["detection_source", "tlp"],
            "is_exercise",
            "summary",
            "description",
        ]),
        Step(_("Clocks"), "clock-history", [
            ["occurred_at", "detected_at"],
            "awareness_at",
            "awareness_justification",
        ]),
        Step(_("Impact"), "bullseye", [
            ["confidentiality_impact", "integrity_impact", "availability_impact"],
            "personal_data_involved",
            ["outage_duration", "estimated_cost"],
            "no_obligation_justification",
        ]),
        Step(_("Significance"), "flag", [
            ["is_significant", "significance_determined_at"],
            "significance_justification",
            "cross_border_impact",
            "cross_border_justification",
            "suspected_malicious",
            "suspected_malicious_justification",
        ]),
        Step(_("Handling"), "people", [
            ["response_plan", "incident_manager"],
            ["reporter", "origin_supplier"],
            "parent_incident",
            "scopes",
            "tags",
        ]),
        Step(_("Blast radius"), "diagram-3", [
            "affected_essential_assets",
            "affected_support_assets",
            "affected_sites",
            "affected_activities",
            "affected_suppliers",
        ]),
        Step(_("Registers"), "link-45deg", [
            "threats",
            "exploited_vulnerabilities",
            "realised_risks",
            "linked_requirements",
        ]),
    ]

    class Meta:
        model = Incident
        fields = [
            "scopes", "title", "summary", "description",
            "category", "severity", "detection_source", "is_exercise", "tlp",
            "confidentiality_impact", "integrity_impact", "availability_impact",
            "personal_data_involved",
            "occurred_at", "detected_at", "awareness_at", "awareness_justification",
            "outage_duration", "estimated_cost", "no_obligation_justification",
            "is_significant", "significance_determined_at",
            "significance_justification",
            "cross_border_impact", "cross_border_justification",
            "suspected_malicious", "suspected_malicious_justification",
            "response_plan", "reporter", "incident_manager",
            "parent_incident", "origin_supplier",
            "affected_suppliers", "affected_essential_assets",
            "affected_support_assets", "affected_sites", "affected_activities",
            "threats", "exploited_vulnerabilities", "realised_risks",
            "linked_requirements",
            "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "title": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "summary": _textarea(3),
            "description": _textarea(5),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "severity": forms.Select(attrs=SELECT_ATTRS),
            "detection_source": forms.Select(attrs=SELECT_ATTRS),
            "is_exercise": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "tlp": forms.Select(attrs=SELECT_ATTRS),
            "confidentiality_impact": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "integrity_impact": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "availability_impact": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "personal_data_involved": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "occurred_at": _datetime_widget(),
            "detected_at": _datetime_widget(),
            "awareness_at": _datetime_widget(),
            "awareness_justification": _textarea(3),
            "outage_duration": forms.TextInput(attrs={
                **FORM_WIDGET_ATTRS,
                "placeholder": "HH:MM:SS",
            }),
            "estimated_cost": forms.NumberInput(attrs={
                **FORM_WIDGET_ATTRS, "step": "0.01", "min": "0",
            }),
            "no_obligation_justification": _textarea(3),
            "is_significant": _tristate_widget(),
            "significance_determined_at": _datetime_widget(),
            "significance_justification": _textarea(3),
            "cross_border_impact": _tristate_widget(),
            "cross_border_justification": _textarea(2),
            "suspected_malicious": _tristate_widget(),
            "suspected_malicious_justification": _textarea(2),
            "response_plan": forms.Select(attrs=SELECT_ATTRS),
            "reporter": forms.Select(attrs=SELECT_ATTRS),
            "incident_manager": forms.Select(attrs=SELECT_ATTRS),
            "parent_incident": forms.Select(attrs=SELECT_ATTRS),
            "origin_supplier": forms.Select(attrs=SELECT_ATTRS),
            "affected_suppliers": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "affected_essential_assets": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "affected_support_assets": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "affected_sites": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "affected_activities": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "threats": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "exploited_vulnerabilities": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "realised_risks": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "linked_requirements": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "title": _("What an executive reading one line has to understand."),
            "summary": _(
                "The paragraph the management review and any external statement "
                "are drafted from."
            ),
            "description": _("The technical account, for the responders."),
            "category": _(
                "The threat that materialised, in the taxonomy the risk register "
                "already uses."
            ),
            "severity": _(
                "Read through the response plan's classification scale : it is "
                "what gives this value its meaning."
            ),
            "detection_source": _("What or who brought this to light."),
            "is_exercise": _(
                "A drill run through the real process : same gates, excluded "
                "from every KPI, and never filing a regulatory notification."
            ),
            "tlp": _("How far this file may be shared, and with whom."),
            "confidentiality_impact": _("Data was, or may have been, disclosed."),
            "integrity_impact": _("Data or systems were altered."),
            "availability_impact": _("A service was degraded or interrupted."),
            "personal_data_involved": _(
                "Opens the GDPR qualification and forces the Art. 33(1) "
                "obligation at triage, whatever the response plan configures."
            ),
            "occurred_at": _("Best estimate of when it began, not when it was seen."),
            "detected_at": _(
                "When a control, a tool or a person saw it. The base of "
                "mean-time-to-detect, and never the legal clock."
            ),
            "awareness_at": _(
                "The legal clock : every statutory deadline is counted from here. "
                "Left empty, it is taken to be the detection timestamp."
            ),
            "awareness_justification": _(
                "Required as soon as awareness postdates detection : an alert "
                "unread over a weekend, a supplier notification arriving late."
            ),
            "outage_duration": _(
                "Measured interruption, as HH:MM:SS or D HH:MM:SS. Reported "
                "beside each affected asset's declared objectives, verbatim."
            ),
            "estimated_cost": _("Best current estimate, revised as it firms up."),
            "no_obligation_justification": _(
                "Why nothing is owed to anyone. Triage is refused without it "
                "when it produced no notification obligation at all."
            ),
            "is_significant": _(
                "The NIS2 Art. 23(3) verdict, which is a different judgement "
                "from severity."
            ),
            "significance_determined_at": _(
                "Usable as a statutory clock anchor in its own right."
            ),
            "significance_justification": _("What the verdict rests on."),
            "cross_border_impact": _(
                "Entities or users in more than one Member State are affected. "
                "Not the GDPR notion of cross-border processing."
            ),
            "cross_border_justification": _(
                "Required as soon as the verdict is answered either way."
            ),
            "suspected_malicious": _(
                "The NIS2 early warning cannot be filed while this is unknown."
            ),
            "suspected_malicious_justification": _(
                "Required as soon as the verdict is answered either way."
            ),
            "response_plan": _("The procedure version this incident is handled under."),
            "reporter": _("Who raised it."),
            "incident_manager": _(
                "The single accountable responder. Triage cannot complete "
                "without one."
            ),
            "parent_incident": _(
                "The major incident this one is part of, or the incident it was "
                "merged into."
            ),
            "origin_supplier": _("The third party whose breach or outage caused this."),
            "affected_suppliers": _(
                "Suppliers hit or notified downstream, kept apart from the "
                "origin because the reporting duties differ."
            ),
            "affected_essential_assets": _("The business assets actually affected."),
            "affected_support_assets": _("The machines, services and devices affected."),
            "affected_sites": _("Where the impact was felt."),
            "affected_activities": _("For a halted activity with no named asset."),
            "threats": _("The registered threat that materialised."),
            "exploited_vulnerabilities": _("What the attacker or the failure used."),
            "realised_risks": _("Which registered risks actually came true."),
            "linked_requirements": _("The controls in play, held or failed."),
            "scopes": _("Who sees this incident, and every child row it carries."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _restrict_fk(self, "response_plan", "origin_supplier", "parent_incident")
        _restrict_m2m(
            self,
            "affected_suppliers", "affected_essential_assets",
            "affected_support_assets", "affected_sites", "affected_activities",
            "threats", "exploited_vulnerabilities", "realised_risks",
            "linked_requirements",
        )
        # An incident is never its own parent, and never its own merge target.
        if not _is_new(self.instance):
            self.fields["parent_incident"].queryset = self.fields[
                "parent_incident"
            ].queryset.exclude(pk=self.instance.pk)


# --- Security event ---------------------------------------------------------


class SecurityEventForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Report or edit an A.6.8 security event or weakness.

    ``triage_decision``, ``incident`` and ``vulnerability`` are absent : the
    verdict is written by the A.5.25 assessment transition and the two promotion
    targets are created by the promotion actions, which is what keeps a
    "promoted" event from ever pointing at nothing. ``assessed_at`` is a
    transition stamp (RG-INC-12).
    """

    steps = [
        # `pgettext_lazy` : the bare "Report" already resolves to *Rapport* in
        # the catalogue, which is the document, not the act of reporting one.
        Step(pgettext_lazy("incident", "Report"), "megaphone", [
            "title",
            ["event_class", "category"],
            ["detection_source", "source_reference"],
            "description",
        ]),
        Step(_("Clocks"), "clock-history", [
            ["occurred_at", "detected_at"],
            "reported_at",
        ]),
        Step(_("Reporter"), "person", [
            "is_anonymous",
            ["reporter", "reporter_label"],
            "reported_by_supplier",
            "duplicate_of",
        ]),
        Step(_("Blast radius"), "diagram-3", [
            "affected_essential_assets",
            "affected_support_assets",
            "affected_sites",
        ]),
        Step(_("Assessment"), "clipboard-check", [
            "assessed_by",
            "assessment_notes",
            "scopes",
            "tags",
        ]),
    ]

    class Meta:
        model = SecurityEvent
        fields = [
            "scopes", "title", "description",
            "event_class", "category", "detection_source", "source_reference",
            "occurred_at", "detected_at", "reported_at",
            "is_anonymous", "reporter", "reporter_label",
            "reported_by_supplier", "duplicate_of",
            "affected_essential_assets", "affected_support_assets",
            "affected_sites",
            "assessed_by", "assessment_notes",
            "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "title": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": _textarea(5),
            "event_class": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "detection_source": forms.Select(attrs=SELECT_ATTRS),
            "source_reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "occurred_at": _datetime_widget(),
            "detected_at": _datetime_widget(),
            "reported_at": _datetime_widget(),
            "is_anonymous": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "reporter": forms.Select(attrs=SELECT_ATTRS),
            "reporter_label": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "reported_by_supplier": forms.Select(attrs=SELECT_ATTRS),
            "duplicate_of": forms.Select(attrs=SELECT_ATTRS),
            "affected_essential_assets": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "affected_support_assets": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "affected_sites": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "assessed_by": forms.Select(attrs=SELECT_ATTRS),
            "assessment_notes": _textarea(4),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "title": _("What was observed, in one line."),
            "description": _(
                "The reporter's own words. Never rewritten on promotion : the "
                "original report is part of the record."
            ),
            "event_class": _(
                "A weakness is a flaw nobody has exploited yet, and it governs "
                "which promotions are legal."
            ),
            "category": _("Provisional, and refined on promotion."),
            "detection_source": _("What or who brought this to light."),
            "source_reference": _("SIEM alert id, ticket number, CERT bulletin."),
            "occurred_at": _("Best estimate of when the occurrence started."),
            "detected_at": _("When it was seen, wherever it was seen."),
            "reported_at": _(
                "When it reached the incident response function. The gap with "
                "detection is the reporting delay A.6.8 is measured on."
            ),
            "is_anonymous": _(
                "The channel A.6.8 requires. Leaves no reporter identity at all, "
                "by constraint and not by convention."
            ),
            "reporter": _("The account that reported it, when there is one."),
            "reporter_label": _(
                "An external or non-user reporter : a customer, a researcher, an "
                "authority."
            ),
            "reported_by_supplier": _(
                "Third-party notification (NIS2 supply chain, GDPR Art. 33(2))."
            ),
            "duplicate_of": _(
                "The earlier report this one repeats, or the weakness this "
                "exploitation was first reported as."
            ),
            "affected_essential_assets": _("The business assets in play."),
            "affected_support_assets": _("The machines, services and devices in play."),
            "affected_sites": _("Where it was observed."),
            "assessed_by": _("Who performs the A.5.25 assessment."),
            "assessment_notes": _(
                "The reasoning behind the verdict. Leaving the assessment is "
                "refused while this is empty : an undocumented assessment is "
                "not an assessment."
            ),
            "scopes": _("Who sees this report."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _restrict_fk(self, "reported_by_supplier", "duplicate_of")
        _restrict_m2m(
            self,
            "affected_essential_assets", "affected_support_assets",
            "affected_sites",
        )
        # An event never duplicates itself.
        if not _is_new(self.instance):
            self.fields["duplicate_of"].queryset = self.fields[
                "duplicate_of"
            ].queryset.exclude(pk=self.instance.pk)


# --- Response plan ----------------------------------------------------------


class IncidentResponsePlanForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """The A.5.24 incident management procedure of record.

    ``last_exercise_date`` is deliberately absent from every surface : it is
    maintained only by the closure of an exercise incident, and a hand-typed
    plan-testing date is worthless as evidence.
    """

    applicable_regimes = forms.MultipleChoiceField(
        label=_("Applicable regimes"),
        choices=NotificationRegime.choices,
        required=False,
        widget=forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 8}),
        help_text=_(
            "Triage instantiates one notification obligation per regime listed "
            "here, so a regime left off this list reads as nothing being owed."
        ),
    )

    steps = [
        Step(_("Identity"), "journal-text", [
            "name",
            ["owner", "approved_by"],
            ["approved_at", "effective_from"],
            "review_date",
            "purpose",
        ]),
        Step(_("Procedure"), "list-check", [
            "procedure",
            "classification_scale",
            "escalation_matrix",
        ]),
        Step(_("Channels and evidence"), "shield-check", [
            "reporting_channels",
            "evidence_procedure",
            "lessons_learned_procedure",
        ]),
        Step(_("Regimes and scope"), "diagram-3", [
            "applicable_regimes",
            "responsible_roles",
            "linked_requirements",
            "scopes",
            "tags",
        ]),
    ]

    class Meta:
        model = IncidentResponsePlan
        fields = [
            "scopes", "name", "purpose", "procedure",
            "classification_scale", "escalation_matrix", "reporting_channels",
            "evidence_procedure", "lessons_learned_procedure",
            "applicable_regimes",
            "owner", "approved_by", "approved_at", "effective_from",
            "review_date", "responsible_roles", "linked_requirements",
            "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "purpose": _textarea(3),
            "procedure": forms.Textarea(attrs={
                **FORM_WIDGET_ATTRS, "rows": 8, "class": "form-control rich-text",
            }),
            "classification_scale": forms.Textarea(attrs={
                **FORM_WIDGET_ATTRS, "rows": 5, "class": "form-control rich-text",
            }),
            "escalation_matrix": forms.Textarea(attrs={
                **FORM_WIDGET_ATTRS, "rows": 5, "class": "form-control rich-text",
            }),
            "reporting_channels": forms.Textarea(attrs={
                **FORM_WIDGET_ATTRS, "rows": 5, "class": "form-control rich-text",
            }),
            "evidence_procedure": forms.Textarea(attrs={
                **FORM_WIDGET_ATTRS, "rows": 5, "class": "form-control rich-text",
            }),
            "lessons_learned_procedure": forms.Textarea(attrs={
                **FORM_WIDGET_ATTRS, "rows": 5, "class": "form-control rich-text",
            }),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "approved_by": forms.Select(attrs=SELECT_ATTRS),
            "approved_at": _date_widget(),
            "effective_from": _date_widget(),
            "review_date": _date_widget(),
            "responsible_roles": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "linked_requirements": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Version this plan by its name : a material change is a new plan."),
            "purpose": _("What the procedure is for, and who it binds."),
            "procedure": _("The steps responders actually follow."),
            "classification_scale": _(
                "What low, medium, high and critical mean here. Without it, "
                "incident severity means nothing."
            ),
            "escalation_matrix": _(
                "Who is escalated to, at which severity, within which delay."
            ),
            "reporting_channels": _(
                "How events are reported, the anonymous channel included."
            ),
            "evidence_procedure": _(
                "Identification, collection, acquisition and preservation "
                "(A.5.28)."
            ),
            "lessons_learned_procedure": _(
                "How what an incident taught is turned into a stronger control "
                "(A.5.27)."
            ),
            "owner": _("Who maintains the procedure."),
            "approved_by": _("Who approved it on the organisation's behalf."),
            "approved_at": _("Date of that approval."),
            "effective_from": _("The day this version became the one in force."),
            "review_date": _("When the procedure is next due for review."),
            "responsible_roles": _("The roles the procedure assigns duties to."),
            "linked_requirements": _("The controls this plan is the evidence for."),
            "scopes": _("Which parts of the organisation run this procedure."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _restrict_m2m(self, "responsible_roles", "linked_requirements")


# --- Chronology -------------------------------------------------------------


class IncidentTimelineEntryForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Append one line to an incident's chronology.

    **Append-only : there is no edit form and there never will be.** The model
    refuses any write against an existing row, and a factual error is corrected
    by appending a further entry that supersedes the first with a stated reason.
    The superseded entry is never modified and never hidden.

    The incident and the author are stamped on the instance in ``__init__``
    rather than in the view's ``form_valid()`` : the author is a required,
    ``PROTECT``-ed attribution and the model's ``clean()`` runs while the form
    validates.
    """

    steps = [
        Step(_("Entry"), "journal-text", [
            ["occurred_at", "entry_type"],
            "summary",
            "detail",
            "is_evidence",
        ]),
        Step(_("Links and correction"), "link-45deg", [
            ["related_action", "related_evidence"],
            "superseded_entry",
            "correction_reason",
        ]),
    ]

    class Meta:
        model = IncidentTimelineEntry
        fields = [
            "occurred_at", "entry_type", "summary", "detail", "is_evidence",
            "related_action", "related_evidence",
            "superseded_entry", "correction_reason",
        ]
        widgets = {
            "occurred_at": _datetime_widget(),
            "entry_type": forms.Select(attrs=SELECT_ATTRS),
            "summary": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "detail": _textarea(4),
            "is_evidence": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "related_action": forms.Select(attrs=SELECT_ATTRS),
            "related_evidence": forms.Select(attrs=SELECT_ATTRS),
            "superseded_entry": forms.Select(attrs=SELECT_ATTRS),
            "correction_reason": _textarea(2),
        }
        help_texts = {
            "occurred_at": _(
                "The real-world time of the act, which may be earlier than now : "
                "the chronology reads in the order things happened."
            ),
            "entry_type": _("What kind of act this line records."),
            "summary": _("One line, exported verbatim into filings and reports."),
            "detail": _("Commands run, output observed, people spoken to."),
            "is_evidence": _(
                "Quote this line verbatim in generated filings and in the "
                "register export."
            ),
            "related_action": _("The response step this line narrates."),
            "related_evidence": _("The evidence item this line narrates."),
            "superseded_entry": _(
                "The earlier entry this one corrects. The earlier entry stays "
                "in the chronology, visible."
            ),
            "correction_reason": _(
                "Required with a correction : a correction with no stated "
                "reason is a rewrite."
            ),
        }

    def __init__(self, *args, incident=None, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.incident = incident or getattr(self.instance, "incident", None)
        # Stamped before validation : `clean()` and the append-only guard both
        # read them, and the author can never be filled in afterwards.
        if incident is not None:
            self.instance.incident = incident
        if author is not None and self.instance.author_id is None:
            self.instance.author = author
        self.instance.source = TimelineEntrySource.MANUAL

        for name in ("related_action", "related_evidence", "superseded_entry"):
            field = self.fields[name]
            field.queryset = (
                field.queryset.filter(incident=self.incident)
                if self.incident is not None
                else field.queryset.none()
            )
        if not _is_new(self.instance):
            self.fields["superseded_entry"].queryset = self.fields[
                "superseded_entry"
            ].queryset.exclude(pk=self.instance.pk)


# --- Response action --------------------------------------------------------


class IncidentResponseActionForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """One operational step taken during an incident (A.5.26).

    A plain ``status`` column and no lifecycle, argued in the model : a
    containment step lives for twenty minutes and a permission check, a ledger
    row and a comment modal on each of four ticks manufacture delay in the exact
    window where delay is the harm.
    """

    steps = [
        Step(_("Action"), "lightning", [
            ["action_type", "status"],
            "title",
            "description",
        ]),
        Step(_("Ownership"), "person-check", [
            ["owner", "performed_by"],
            ["due_at", "started_at"],
        ]),
        Step(_("Outcome"), "check2-square", [
            "completed_at",
            "outcome",
            "effectiveness",
        ]),
    ]

    class Meta:
        model = IncidentResponseAction
        fields = [
            "action_type", "title", "description", "status",
            "owner", "performed_by",
            "due_at", "started_at", "completed_at",
            "outcome", "effectiveness",
        ]
        widgets = {
            "action_type": forms.Select(attrs=SELECT_ATTRS),
            "title": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": _textarea(3),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "performed_by": forms.Select(attrs=SELECT_ATTRS),
            "due_at": _datetime_widget(),
            "started_at": _datetime_widget(),
            "completed_at": _datetime_widget(),
            "outcome": _textarea(3),
            "effectiveness": forms.Select(attrs=SELECT_ATTRS),
        }
        help_texts = {
            "action_type": _("Which ISO 27035 response step this belongs to."),
            "title": _("What is being done, in the imperative."),
            "description": _("The command to run, the runbook section, who to call."),
            "status": _("Operational progress, not a governance state."),
            "owner": _("Who is accountable for it being done."),
            "performed_by": _("Who actually executed it, when that is someone else."),
            "due_at": _("Drives the daily escalation sweep and the overdue styling."),
            "started_at": _("When execution began."),
            "completed_at": _("Required to mark the step done."),
            "outcome": _(
                "What it achieved. A containment step marked done with no "
                "stated outcome is not evidence of containment."
            ),
            "effectiveness": _(
                "Whether it worked, assessed during the post-incident review. "
                "Left blank until then."
            ),
        }

    def __init__(self, *args, incident=None, **kwargs):
        super().__init__(*args, **kwargs)
        # The parent is stamped before validation : `clean()` runs while the
        # form validates, and a parentless row cannot be saved at all.
        if incident is not None:
            self.instance.incident = incident


# --- Evidence ---------------------------------------------------------------


class IncidentEvidenceForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Register or edit an A.5.28 evidence item.

    ``sealed_at``, ``destruction_authorised_by``, ``last_integrity_check_at``
    and ``last_integrity_check_ok`` are written by the transitions and by the
    integrity verification, never here (RG-INC-12).

    Once the item is **sealed**, the six acquisition fields are frozen : the
    model refuses to change them from ``save()``, which is far too late for a
    form to render an error against the field the operator touched, so they are
    disabled here instead and keep their stored values.
    """

    steps = [
        Step(_("Item"), "box-seam", [
            "title",
            ["evidence_type", "tlp"],
            "description",
        ]),
        Step(_("Acquisition"), "clipboard-check", [
            ["collected_at", "collected_by"],
            "collection_method",
            "source_support_asset",
            "source_description",
        ]),
        Step(_("Integrity"), "fingerprint", [
            ["content_hash", "hash_algorithm"],
            "file",
            ["original_filename", "file_size"],
            "storage_location",
        ]),
        Step(_("Retention"), "shield-lock", [
            ["legal_hold", "retention_until"],
            "admissibility_notes",
            "tags",
        ]),
    ]

    class Meta:
        model = IncidentEvidence
        fields = [
            "title", "description", "evidence_type", "tlp",
            "collected_at", "collected_by", "collection_method",
            "source_support_asset", "source_description",
            "content_hash", "hash_algorithm",
            "file", "original_filename", "file_size", "storage_location",
            "legal_hold", "retention_until", "admissibility_notes",
            "tags",
        ]
        widgets = {
            "title": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": _textarea(3),
            "evidence_type": forms.Select(attrs=SELECT_ATTRS),
            "tlp": forms.Select(attrs=SELECT_ATTRS),
            "collected_at": _datetime_widget(),
            "collected_by": forms.Select(attrs=SELECT_ATTRS),
            "collection_method": _textarea(4),
            "source_support_asset": forms.Select(attrs=SELECT_ATTRS),
            "source_description": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "content_hash": forms.TextInput(attrs={
                **FORM_WIDGET_ATTRS, "autocomplete": "off", "spellcheck": "false",
            }),
            "hash_algorithm": forms.Select(attrs=SELECT_ATTRS),
            "file": forms.ClearableFileInput(attrs=FORM_WIDGET_ATTRS),
            "original_filename": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "file_size": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": "0"}),
            "storage_location": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "legal_hold": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "retention_until": _date_widget(),
            "admissibility_notes": _textarea(3),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "title": _("How the item is cited, e.g. 'Memory image - WEB-PRD-02'."),
            "description": _("What it is, and why it matters to this incident."),
            "evidence_type": _("Drives which acquisition method is acceptable."),
            "tlp": _(
                "Defaults stricter than the incident's : an artefact usually "
                "holds more than the summary does."
            ),
            "collected_at": _("The moment the artefact left the live system."),
            "collected_by": _(
                "The named acquirer, who is not necessarily whoever is filling "
                "in this form."
            ),
            "collection_method": _(
                "Tooling and version, write-blocker, exact command line, witness "
                "present, live or powered-down source. This is what makes the "
                "item admissible."
            ),
            "source_support_asset": _("The registered machine the artefact came off."),
            "source_description": _(
                "Where it came from when that is not a registered asset : a "
                "personal device, a third-party service, a physical location."
            ),
            "content_hash": _(
                "The digest measured at acquisition. Sealing is refused without "
                "it."
            ),
            "hash_algorithm": _(
                "Recorded because a 2019 MD5 digest must stay verifiable in 2026."
            ),
            "file": _(
                "An inline copy of a small artefact only. A malware sample or a "
                "seized device is registered by reference instead."
            ),
            "original_filename": _(
                "The name as acquired, which is often itself evidence. Kept "
                "after destruction."
            ),
            "file_size": _(
                "In bytes, recorded even for an item held elsewhere, so the "
                "register states the scale of what it covers."
            ),
            "storage_location": _(
                "Safe number, evidence-bag identifier, vault, bucket and object "
                "key, provider case number. This is how bulk artefacts are "
                "registered by reference."
            ),
            "legal_hold": _("Blocks destruction outright, whatever the retention date."),
            "retention_until": _(
                "A permission to destroy after that date, never an instruction : "
                "nothing here destroys anything on its own."
            ),
            "admissibility_notes": _(
                "Which court the item may be produced to, which chain-of-custody "
                "form was countersigned, which counsel was consulted."
            ),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, incident=None, collected_by=None, **kwargs):
        super().__init__(*args, **kwargs)
        # The parent is stamped before validation : the uniqueness of a digest
        # is per incident, and the row inherits the incident's tenancy.
        if incident is not None:
            self.instance.incident = incident
        # The acquirer is a field of its own, so the acting user is *offered*
        # rather than stamped : the person registering the row is frequently not
        # the person who acquired the artefact.
        if collected_by is not None and self.instance.collected_by_id is None:
            self.fields["collected_by"].initial = collected_by

        _restrict_fk(self, "source_support_asset")

        if not _is_new(self.instance) and self.instance.is_sealed:
            _freeze(
                self,
                EVIDENCE_ACQUISITION_FIELDS,
                _(
                    "Frozen : this evidence item is sealed. Destruction is a "
                    "transition, never an edit."
                ),
            )

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get("file")
        if isinstance(upload, UploadedFile):
            # Recorded from the upload rather than retyped, and only when the
            # operator left them blank : the name as acquired is part of the
            # record.
            if not cleaned.get("original_filename"):
                cleaned["original_filename"] = (upload.name or "")[:255]
            if not cleaned.get("file_size"):
                cleaned["file_size"] = upload.size

        content_hash = (cleaned.get("content_hash") or "").strip()
        incident_id = self.instance.incident_id
        if content_hash and incident_id:
            # Mirrors the unique constraint, which Django skips because
            # `incident` is not a field of this form : the same artefact is
            # never registered twice against the same incident.
            duplicates = IncidentEvidence.objects.filter(
                incident_id=incident_id, content_hash=content_hash
            )
            if not _is_new(self.instance):
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error(
                    "content_hash",
                    _("This artefact is already registered against this incident."),
                )
        return cleaned


class EvidenceCustodyEventForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Record by hand one handling act on an evidence item.

    **Only the acts Cairn cannot observe.** Collection, sealing, analysis,
    release and destruction are appended by the parent's own transitions, one
    row each, inside the transition's transaction : offering them here would
    double every one of them. Integrity verification is not offered either, and
    for a stronger reason : it is produced by ``verify_integrity()``, which
    *measures* the digest and records a three-way outcome, and a form that let
    somebody assert a verdict without a measurement would be the one row in the
    ledger that proves nothing.

    The ledger is append-only, so this form creates and never edits.
    """

    steps = [
        Step(_("Custody act"), "box-seam", [
            ["action", "occurred_at"],
            ["counterparty", "counterparty_organisation"],
            "location",
            "hash_at_event",
            "notes",
        ]),
    ]

    #: The four acts a human records. `collected`, `sealed`, `analysed`,
    #: `released` and `destroyed` belong to the parent's transitions, and
    #: `integrity_verified` belongs to the measurement.
    MANUAL_ACTIONS = (
        CustodyAction.TRANSFERRED,
        CustodyAction.RETURNED,
        CustodyAction.ACCESSED,
        CustodyAction.COPIED,
    )

    class Meta:
        model = EvidenceCustodyEvent
        fields = [
            "action", "occurred_at",
            "counterparty", "counterparty_organisation",
            "location", "hash_at_event", "notes",
        ]
        widgets = {
            "action": forms.Select(attrs=SELECT_ATTRS),
            "occurred_at": _datetime_widget(),
            "counterparty": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "counterparty_organisation": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "location": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "hash_at_event": forms.TextInput(attrs={
                **FORM_WIDGET_ATTRS, "autocomplete": "off", "spellcheck": "false",
            }),
            "notes": _textarea(3),
        }
        help_texts = {
            "action": _(
                "The handling acts Cairn cannot observe. The others are appended "
                "by the item's own transitions."
            ),
            "occurred_at": _(
                "When the act happened, which may be days before it is being "
                "typed. The gap is itself evidence of how the ledger is kept."
            ),
            "counterparty": _(
                "Required for a transfer or a return : a handover to an "
                "organisation with no named individual is not a handover."
            ),
            "counterparty_organisation": _(
                "Free text on purpose : a police force or a data subject's "
                "counsel is not a supplier."
            ),
            "location": _(
                "Where the act took place, or where the item went : safe number, "
                "evidence-bag identifier, address, bucket and object key."
            ),
            "hash_at_event": _(
                "The digest measured at this act, when one was taken. For a "
                "copy, this is the copy's own digest."
            ),
            "notes": _(
                "Seal number, transport conditions, packaging, witnesses, or "
                "what an earlier row got wrong."
            ),
        }

    def __init__(self, *args, evidence=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Both are stamped before validation : `clean()` reads the parent to
        # refuse a ledger that jumps backwards in time, and the actor is a
        # required, `PROTECT`-ed attribution with no form field of its own.
        if evidence is not None:
            self.instance.evidence = evidence
        if actor is not None and self.instance.actor_id is None:
            self.instance.actor = actor
        # An act recorded through this form is a human act, always.
        self.instance.source = TimelineEntrySource.MANUAL

        choices = dict(CustodyAction.choices)
        self.fields["action"].choices = [
            (value, choices[value]) for value in self.MANUAL_ACTIONS
        ]


# --- Post-incident review ---------------------------------------------------


class PostIncidentReviewForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """The A.5.27 learning record, and the gate an incident closes through.

    ``scopes`` is absent by design : the review inherits the incident's tenancy
    and is realigned on every incident save (RG-INC-31), so a scope picker here
    would offer a choice the next save silently overrides. ``held_at`` and
    ``effectiveness_reviewed_at`` are transition stamps (RG-INC-12).
    """

    steps = [
        Step(_("Planning"), "calendar-check", [
            ["scheduled_date", "facilitator"],
            "participants",
            "response_plan",
        ]),
        Step(_("Root cause"), "search", [
            ["root_cause_method", "recurrence_likelihood"],
            "root_cause",
            "contributing_factors",
            "detection_gap",
        ]),
        Step(_("Assessment"), "clipboard-check", [
            "containment_assessment",
            "what_went_well",
            "what_failed",
            "similar_incidents_checked",
        ]),
        Step(_("Consequences"), "arrow-repeat", [
            [
                "risk_reassessment_required",
                "response_plan_update_required",
                "training_required",
            ],
            "failed_controls",
            "controls_to_strengthen",
        ]),
        Step(_("Outputs"), "diagram-3", [
            "raised_findings",
            "corrective_action_plans",
            "identified_risks",
            "identified_vulnerabilities",
            "isms_changes",
            "tags",
        ]),
        Step(_("Effectiveness"), "check2-circle", [
            ["effectiveness_review_date", "effectiveness_verdict"],
            "effectiveness_reviewed_by",
            "effectiveness_notes",
        ]),
    ]

    class Meta:
        model = PostIncidentReview
        fields = [
            "response_plan", "scheduled_date", "facilitator", "participants",
            "root_cause_method", "root_cause", "contributing_factors",
            "detection_gap", "containment_assessment",
            "what_went_well", "what_failed",
            "recurrence_likelihood", "similar_incidents_checked",
            "risk_reassessment_required", "response_plan_update_required",
            "training_required",
            "effectiveness_review_date", "effectiveness_verdict",
            "effectiveness_reviewed_by", "effectiveness_notes",
            "raised_findings", "corrective_action_plans",
            "failed_controls", "controls_to_strengthen",
            "identified_risks", "identified_vulnerabilities", "isms_changes",
            "tags",
        ]
        widgets = {
            "response_plan": forms.Select(attrs=SELECT_ATTRS),
            "scheduled_date": _date_widget(),
            "facilitator": forms.Select(attrs=SELECT_ATTRS),
            "participants": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "root_cause_method": forms.Select(attrs=SELECT_ATTRS),
            "root_cause": _textarea(4),
            "contributing_factors": _textarea(3),
            "detection_gap": _textarea(3),
            "containment_assessment": _textarea(3),
            "what_went_well": _textarea(3),
            "what_failed": _textarea(3),
            "recurrence_likelihood": forms.Select(attrs=SELECT_ATTRS),
            "similar_incidents_checked": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "risk_reassessment_required": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "response_plan_update_required": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "training_required": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "effectiveness_review_date": _date_widget(),
            "effectiveness_verdict": forms.Select(attrs=SELECT_ATTRS),
            "effectiveness_reviewed_by": forms.Select(attrs=SELECT_ATTRS),
            "effectiveness_notes": _textarea(3),
            "raised_findings": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "corrective_action_plans": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "failed_controls": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "controls_to_strengthen": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "identified_risks": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "identified_vulnerabilities": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "isms_changes": forms.SelectMultiple(attrs=MULTISELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "response_plan": _(
                "The procedure this review concludes must change. Copied from "
                "the incident, and editable : a different plan may be at fault."
            ),
            "scheduled_date": _("When the review is planned to be held."),
            "facilitator": _(
                "Who runs it, and who is recorded as having raised the "
                "nonconformities it produces."
            ),
            "participants": _("Who took part, which is part of the record."),
            "root_cause_method": _(
                "Naming the technique is what separates a determined cause from "
                "a plausible guess."
            ),
            "root_cause": _(
                "The cause, not the symptom and not the remediation. The review "
                "cannot be submitted without it."
            ),
            "contributing_factors": _("What made it possible, or made it worse."),
            "detection_gap": _(
                "Why it was not seen earlier. This is what makes the "
                "mean-time-to-detect figure actionable."
            ),
            "containment_assessment": _(
                "Whether the response itself was adequate and timely, which is a "
                "different verdict from the one on the controls."
            ),
            "what_went_well": _("Worth keeping, and worth saying out loud."),
            "what_failed": _("Stated plainly : this is what the corrective actions answer."),
            "recurrence_likelihood": _("Whether similar nonconformities could occur."),
            "similar_incidents_checked": _(
                "Confirms the search for similar incidents actually happened. "
                "The review cannot be submitted without it."
            ),
            "risk_reassessment_required": _(
                "The incident invalidates a registered risk evaluation."
            ),
            "response_plan_update_required": _("The procedure itself has to change."),
            "training_required": _("An awareness or training action is needed."),
            "effectiveness_review_date": _(
                "When the corrective actions will be checked for having worked. "
                "The review cannot be approved without it."
            ),
            "effectiveness_verdict": _(
                "Whether the corrective action worked. Required to verify "
                "effectiveness, and copied onto every nonconformity this review "
                "raised at that moment."
            ),
            "effectiveness_reviewed_by": _(
                "Who reached that verdict. Self-verification is permitted, and "
                "is rendered as exactly that."
            ),
            "effectiveness_notes": _("What was measured, tested or observed, and when."),
            "raised_findings": _(
                "The nonconformities this review raised, in the one register an "
                "audit uses too."
            ),
            "corrective_action_plans": _(
                "The corrective actions, on the existing action-plan lifecycle."
            ),
            "failed_controls": _("The controls that were in place and did not hold."),
            "controls_to_strengthen": _(
                "What is being done about it, kept apart from what broke : an "
                "auditor reads the two side by side."
            ),
            "identified_risks": _("Risks the incident revealed or invalidated."),
            "identified_vulnerabilities": _(
                "Weaknesses to register, in the existing vulnerability register."
            ),
            "isms_changes": _(
                "Tabled at a management review and linked back here : this "
                "review links one, it never creates one."
            ),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, incident=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Stamped before validation : the review is one per incident, and its
        # own `clean()` and its gates read the parent.
        if incident is not None:
            self.instance.incident = incident
        _restrict_fk(self, "response_plan")
        _restrict_m2m(
            self,
            "raised_findings", "corrective_action_plans",
            "failed_controls", "controls_to_strengthen",
            "identified_risks", "identified_vulnerabilities", "isms_changes",
        )


# --- Notification obligation and filing --------------------------------------


class IncidentNotificationForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Add or edit one regulatory or contractual notification obligation.

    Everything the decision and the filing own is absent : ``decision``,
    ``decided_by``, ``decided_at``, ``sent_at``, ``sent_by``,
    ``first_submitted_at``, ``late_by``, ``anchor_at``, ``due_at`` and the
    derived ``recipient_key`` (RG-INC-12). The clock is *shown* through the
    anchor and the delay, which are the two facts an operator actually chooses.

    Once a filing exists, ``content`` and ``channel`` are frozen : an amendment
    is a further filing, never a rewrite of what left the organisation.
    """

    steps = [
        Step(_("Obligation"), "file-earmark-text", [
            ["regime", "recipient_kind"],
            "obligation_reference",
            "content_requirements",
        ]),
        Step(_("Recipient"), "send", [
            "authority",
            ["recipient_stakeholder", "recipient_supplier"],
            "recipient_name",
        ]),
        Step(_("Clock"), "clock-history", [
            ["clock_anchor", "deadline_hours"],
            "no_fixed_deadline",
            "depends_on",
        ]),
        Step(_("Notification"), "card-checklist", [
            "channel",
            "content",
        ]),
        Step(_("Decision and receipt"), "journal-bookmark", [
            "decision_rationale",
            ["acknowledgement_reference", "acknowledged_at"],
            "proof_evidence",
            "tags",
        ]),
    ]

    class Meta:
        model = IncidentNotification
        fields = [
            "regime", "recipient_kind",
            "authority", "recipient_stakeholder", "recipient_supplier",
            "recipient_name",
            "obligation_reference", "content_requirements",
            "clock_anchor", "deadline_hours", "no_fixed_deadline", "depends_on",
            "channel", "content",
            "decision_rationale",
            "acknowledgement_reference", "acknowledged_at",
            "proof_evidence",
            "tags",
        ]
        widgets = {
            "regime": forms.Select(attrs=SELECT_ATTRS),
            "recipient_kind": forms.Select(attrs=SELECT_ATTRS),
            "authority": forms.Select(attrs=SELECT_ATTRS),
            "recipient_stakeholder": forms.Select(attrs=SELECT_ATTRS),
            "recipient_supplier": forms.Select(attrs=SELECT_ATTRS),
            "recipient_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "obligation_reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "content_requirements": _textarea(4),
            "clock_anchor": forms.Select(attrs=SELECT_ATTRS),
            "deadline_hours": forms.NumberInput(attrs={
                **FORM_WIDGET_ATTRS, "min": "0",
            }),
            "no_fixed_deadline": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "depends_on": forms.Select(attrs=SELECT_ATTRS),
            "channel": forms.Select(attrs=SELECT_ATTRS),
            "content": _textarea(8),
            "decision_rationale": _textarea(3),
            "acknowledgement_reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "acknowledged_at": _datetime_widget(),
            "proof_evidence": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "regime": _("The legal or contractual basis the duty arises from."),
            "recipient_kind": _("Who receives the filing."),
            "authority": _(
                "The body it goes to, with its portal, its mailbox and its "
                "procedure. Only a validated authority may be cited."
            ),
            "recipient_stakeholder": _(
                "A registered stakeholder, rather than a retyped contact."
            ),
            "recipient_supplier": _(
                "A supplier recipient, including the controller to notify when "
                "the organisation acted as a processor."
            ),
            "recipient_name": _(
                "Free text when the recipient is none of the three above."
            ),
            "obligation_reference": _(
                "The cited article, e.g. 'GDPR Art. 33(1)' : the string an "
                "auditor greps the register for."
            ),
            "content_requirements": _(
                "The legal checklist, rendered beside the drafting field so "
                "nobody leaves the page to find out what the article asks for."
            ),
            "clock_anchor": _(
                "Legal awareness is the correct anchor for a statutory clock. "
                "Technical detection never is."
            ),
            "deadline_hours": _(
                "Wall-clock hours from the anchor : 24, 72, 720. The 72 hours "
                "of Art. 33(1) run through nights and weekends."
            ),
            "no_fixed_deadline": _(
                "A 'without undue delay' duty with no numeric limit. Never "
                "fabricate hours for an obligation that legally has none."
            ),
            "depends_on": _(
                "The sibling filing that starts this clock : a NIS2 final report "
                "is due one month after the notification, not after awareness."
            ),
            "channel": _("How the notification was, or will be, transmitted."),
            "content": _(
                "The exact text transmitted. Frozen once a filing exists : an "
                "amendment is a further filing."
            ),
            "decision_rationale": _(
                "The written justification for not notifying. The single most "
                "audited sentence in a breach file."
            ),
            "acknowledgement_reference": _(
                "The recipient's case, ticket or receipt number. Recording the "
                "acknowledgement is refused without it."
            ),
            "acknowledged_at": _("When the recipient acknowledged receipt."),
            "proof_evidence": _(
                "When the receipt is itself registered as an evidence item."
            ),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, incident=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Stamped before validation : the deadline coherence check, the clock
        # resolution and the per-incident uniqueness all read the parent.
        if incident is not None:
            self.instance.incident = incident
        self.incident = (
            self.instance.incident if self.instance.incident_id else None
        )
        if _is_new(self.instance):
            # An obligation typed in by hand is answerable by deletion; a
            # generated one is answered through a decision. The form only ever
            # produces the first kind.
            self.instance.source = ObligationSource.MANUAL

        _restrict_fk(self, "authority", "recipient_stakeholder", "recipient_supplier")

        for name in ("depends_on", "proof_evidence"):
            field = self.fields[name]
            field.queryset = (
                field.queryset.filter(incident=self.incident)
                if self.incident is not None
                else field.queryset.none()
            )
        if not _is_new(self.instance):
            self.fields["depends_on"].queryset = self.fields[
                "depends_on"
            ].queryset.exclude(pk=self.instance.pk)

        if self.instance.sent_at is not None:
            _freeze(
                self,
                ("content", "channel"),
                _(
                    "Frozen : this notification has been filed. An amendment is "
                    "a further filing, never a rewrite."
                ),
            )

    def clean(self):
        cleaned = super().clean()
        self._resolve_clock(cleaned)

        # Mirrors the database constraint on the field that carries it : the
        # constraint alone would surface as a non-field error naming nothing an
        # operator can act on.
        if (
            self.instance.decision == NotificationDecision.NOT_REQUIRED
            and not (cleaned.get("decision_rationale") or "").strip()
        ):
            self.add_error(
                "decision_rationale",
                _(
                    "This obligation was ruled out : its written rationale "
                    "cannot be removed."
                ),
            )
        return cleaned

    def _resolve_clock(self, cleaned):
        """Resolve the anchor and the due date the way ``save()`` will.

        The model recomputes both in ``save()`` and its ``clean()`` refuses an
        obligation that carries a deadline with no recorded anchor. Without this,
        a brand-new obligation would be rejected for a due date that only its own
        save would have produced. A filed obligation is left strictly alone : its
        clock is frozen, and writing to it is refused (RG-INC-28).
        """
        if self.instance.first_submitted_at is not None:
            return
        anchor_choice = cleaned.get("clock_anchor") or ClockAnchor.AWARENESS_AT
        depends_on = cleaned.get("depends_on")
        if cleaned.get("no_fixed_deadline"):
            anchor = None
        elif anchor_choice == ClockAnchor.PREVIOUS_STAGE:
            anchor = depends_on.first_submitted_at if depends_on else None
        elif self.incident is not None:
            anchor = getattr(self.incident, anchor_choice, None)
        else:
            anchor = None
        hours = cleaned.get("deadline_hours")
        self.instance.anchor_at = anchor
        self.instance.due_at = (
            anchor + timedelta(hours=hours) if anchor is not None and hours else None
        )


class NotificationFilingForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Record one transmission against an obligation.

    **Create only.** The filing log is append-only : what was said is frozen and
    only the recipient's answer completes it, once, through the model's own
    ``record_outcome()``. A correction to what the organisation told a regulator
    is a new filing that supersedes the old one, never an edit of it.

    ``was_late`` is absent : it is frozen at the insert from the obligation's
    stored deadline, and a lateness verdict somebody can type is not a verdict.
    """

    proof_file = forms.FileField(
        label=_("Proof document"),
        required=False,
        widget=forms.ClearableFileInput(attrs=FORM_WIDGET_ATTRS),
        help_text=_(
            "The portal receipt or the delivery proof. A large document is "
            "registered as evidence and linked from the obligation instead."
        ),
    )

    steps = [
        Step(_("Transmission"), "send", [
            ["submitted_at", "channel"],
            "recipient_name",
            "subject",
            "content",
        ]),
        Step(_("Receipt"), "paperclip", [
            ["is_correction", "supersedes"],
            "external_reference",
            "proof_file",
        ]),
    ]

    class Meta:
        model = NotificationFiling
        fields = [
            "submitted_at", "channel", "recipient_name",
            "subject", "content", "external_reference",
            "is_correction", "supersedes",
        ]
        widgets = {
            "submitted_at": _datetime_widget(),
            "channel": forms.Select(attrs=SELECT_ATTRS),
            "recipient_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "subject": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "content": _textarea(8),
            "external_reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "is_correction": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "supersedes": forms.Select(attrs=SELECT_ATTRS),
        }
        help_texts = {
            "submitted_at": _(
                "When it actually left the organisation, not when this row is "
                "being typed."
            ),
            "channel": _("How it was transmitted."),
            "recipient_name": _(
                "The desk, mailbox or person who received it, when that is "
                "finer-grained than the obligation's recipient."
            ),
            "subject": _("The subject line or the portal form title."),
            "content": _(
                "Verbatim, and never edited afterwards. This is the field an "
                "inspector reads."
            ),
            "external_reference": _(
                "The case, ticket or receipt number. A portal returns one at "
                "once; an email filing does not, so it may be completed later."
            ),
            "is_correction": _(
                "A corrective or supplementary filing. The first filing on an "
                "obligation is never one."
            ),
            "supersedes": _(
                "The earlier filing this one replaces. Leave empty when it adds "
                "information without retracting anything."
            ),
        }

    def __init__(self, *args, notification=None, submitted_by=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Stamped before validation : `clean()` reads the obligation to refuse a
        # first filing marked as a correction and a supersession that crosses
        # obligations, and the lateness verdict is frozen against its deadline.
        if notification is not None:
            self.instance.notification = notification
        self.notification = (
            self.instance.notification if self.instance.notification_id else None
        )
        if submitted_by is not None and self.instance.submitted_by_id is None:
            self.instance.submitted_by = submitted_by

        field = self.fields["supersedes"]
        field.queryset = (
            field.queryset.filter(notification=self.notification)
            if self.notification is not None
            else field.queryset.none()
        )
        if not _is_new(self.instance):
            field.queryset = field.queryset.exclude(pk=self.instance.pk)

    def clean_proof_file(self):
        upload = self.cleaned_data.get("proof_file")
        limit = notification_max_proof_bytes()
        if upload and upload.size and upload.size > limit:
            raise forms.ValidationError(
                _(
                    "This proof document exceeds the %(limit)d byte limit. "
                    "Register the document as evidence and link it instead."
                )
                % {"limit": limit}
            )
        return upload

    def save(self, commit=True):
        filing = super().save(commit=False)
        upload = self.cleaned_data.get("proof_file")
        if upload:
            filing.proof_file_content = upload.read()
            filing.proof_filename = (upload.name or "")[:255]
        if commit:
            filing.save()
            self.save_m2m()
        return filing


# --- Personal data breach ----------------------------------------------------


class PersonalDataBreachForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """The GDPR qualification of an incident, and its Art. 33(5) register entry.

    ``qualified_by`` and ``qualified_at`` are stamped by the verdict transition
    and are written once (RG-INC-12) : they record when the qualification was
    first pronounced and by whom, and a later reversal is recorded by the
    immutable ledger rather than by overwriting them.

    The Art. 33(3) fields are laid out in article order, because that is the
    order the filing form asks for them in.
    """

    data_categories = LabelListField(
        label=_("Data categories"),
        required=False,
        widget=forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        help_text=_(
            "One per line. Same value shape as an essential asset's GDPR "
            "categories, so the two registers stay comparable."
        ),
    )
    data_subject_categories = LabelListField(
        label=_("Data subject categories"),
        required=False,
        widget=forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        help_text=_("One per line : employees, customers, minors, patients."),
    )

    steps = [
        Step(_("Capacity"), "person-badge", [
            ["controller_role", "cross_border_eu"],
            "controller_supplier",
            "lead_authority",
        ]),
        Step(_("Nature and volumes"), "database", [
            "nature",
            "data_categories",
            "data_subject_categories",
            ["approximate_data_subjects", "approximate_records"],
            ["special_categories", "volume_is_estimate"],
        ]),
        Step(_("Consequences and measures"), "file-earmark-text", [
            "dpo_contact",
            "likely_consequences",
            "measures_taken",
        ]),
        Step(_("Article 34"), "shield-exclamation", [
            "high_risk_to_rights",
            "high_risk_justification",
            "article_34_exemption",
            "article_34_exemption_justification",
        ]),
        Step(_("Register entry"), "journal-bookmark", [
            "register_entry_reference",
            "tags",
        ]),
    ]

    class Meta:
        model = PersonalDataBreach
        fields = [
            "controller_role", "controller_supplier", "lead_authority",
            "cross_border_eu",
            "nature", "data_categories", "data_subject_categories",
            "approximate_data_subjects", "approximate_records",
            "special_categories", "volume_is_estimate",
            "dpo_contact", "likely_consequences", "measures_taken",
            "high_risk_to_rights", "high_risk_justification",
            "article_34_exemption", "article_34_exemption_justification",
            "register_entry_reference",
            "tags",
        ]
        widgets = {
            "controller_role": forms.Select(attrs=SELECT_ATTRS),
            "controller_supplier": forms.Select(attrs=SELECT_ATTRS),
            "lead_authority": forms.Select(attrs=SELECT_ATTRS),
            "cross_border_eu": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "nature": _textarea(4),
            "approximate_data_subjects": forms.NumberInput(attrs={
                **FORM_WIDGET_ATTRS, "min": "0",
            }),
            "approximate_records": forms.NumberInput(attrs={
                **FORM_WIDGET_ATTRS, "min": "0",
            }),
            "special_categories": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "volume_is_estimate": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "dpo_contact": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "likely_consequences": _textarea(4),
            "measures_taken": _textarea(4),
            "high_risk_to_rights": _tristate_widget(),
            "high_risk_justification": _textarea(3),
            "article_34_exemption": forms.Select(attrs=SELECT_ATTRS),
            "article_34_exemption_justification": _textarea(3),
            "register_entry_reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "controller_role": _(
                "This alone decides which duties exist : a controller owes "
                "Art. 33(1) to the authority, a processor owes Art. 33(2) to "
                "its controller and nothing else."
            ),
            "controller_supplier": _(
                "The controller to notify when the organisation acted as a "
                "processor, taken from the supplier register."
            ),
            "lead_authority": _("The lead authority under the one-stop-shop."),
            "cross_border_eu": _(
                "Cross-border processing within the meaning of Art. 4(23), "
                "which is not the incident's operational cross-border impact."
            ),
            "nature": _("What happened to the data, Art. 33(3)(a)."),
            "approximate_data_subjects": _("How many people are concerned."),
            "approximate_records": _("How many records are concerned."),
            "special_categories": _(
                "Art. 9 data is involved. A strong pointer towards high risk, "
                "and never a substitute for the judgement."
            ),
            "volume_is_estimate": _(
                "The honest default : a 72-hour filing normally carries an "
                "estimate, and the law allows the detail to follow in phases."
            ),
            "dpo_contact": _("The DPO or other contact point, Art. 33(3)(b)."),
            "likely_consequences": _(
                "Art. 33(3)(c). A confirmed breach with this empty is a filing "
                "nobody can draft."
            ),
            "measures_taken": _(
                "Measures taken or proposed, including those mitigating the "
                "adverse effects, Art. 33(3)(d)."
            ),
            "high_risk_to_rights": _(
                "The Art. 34(1) determination. Left unanswered, the breach "
                "cannot be confirmed : unanswered is not a no."
            ),
            "high_risk_justification": _(
                "Expected in both directions : a recorded no-high-risk with no "
                "reasoning is the weakest sentence in a breach file."
            ),
            "article_34_exemption": _(
                "The Art. 34(3) ground relied on, recorded rather than assumed. "
                "The duty is discharged through the obligation's own decision."
            ),
            "article_34_exemption_justification": _(
                "Mandatory as soon as a ground is claimed."
            ),
            "register_entry_reference": _(
                "The pointer to an Art. 33(5) register kept outside Cairn, so "
                "the two stay reconcilable."
            ),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, incident=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Stamped before validation : the record is one per incident and
        # inherits its tenancy, and the confirm transition regenerates the
        # incident's obligations from it.
        if incident is not None:
            self.instance.incident = incident
        _restrict_fk(self, "controller_supplier", "lead_authority")


# --- Regulatory catalogue ----------------------------------------------------


class ReportingAuthorityForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """One body the organisation may owe a filing to.

    Configuration rather than an operational record : only a **validated** row
    may be cited by obligation generation, which is why the entity runs a
    lifecycle at all. A portal URL nobody has checked is worse than no catalogue,
    because the dashboard then reads green.
    """

    additional_regimes = forms.MultipleChoiceField(
        label=_("Additional regimes"),
        choices=NotificationRegime.choices,
        required=False,
        widget=forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 8}),
        help_text=_(
            "One body frequently wears two hats : the catalogue records that "
            "here rather than as a second row."
        ),
    )

    steps = [
        Step(_("Identity"), "bank", [
            ["name", "short_name"],
            ["authority_type", "primary_regime"],
            "additional_regimes",
            "jurisdiction_country",
        ]),
        Step(_("Filing channel"), "send", [
            "portal_url",
            ["contact_email", "contact_phone"],
            "notification_language",
        ]),
        Step(_("Procedure"), "list-check", [
            "procedure",
            "tags",
        ]),
    ]

    class Meta:
        model = ReportingAuthority
        fields = [
            "name", "short_name", "authority_type",
            "primary_regime", "additional_regimes", "jurisdiction_country",
            "portal_url", "contact_email", "contact_phone",
            "notification_language", "procedure",
            "tags",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "short_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "authority_type": forms.Select(attrs=SELECT_ATTRS),
            "primary_regime": forms.Select(attrs=SELECT_ATTRS),
            "jurisdiction_country": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "portal_url": forms.URLInput(attrs=FORM_WIDGET_ATTRS),
            "contact_email": forms.EmailInput(attrs=FORM_WIDGET_ATTRS),
            "contact_phone": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "notification_language": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "procedure": _textarea(6),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("The full legal name, as the body signs its decisions."),
            "short_name": _("The acronym every list and badge actually shows."),
            "authority_type": _("The principal capacity this body acts in."),
            "primary_regime": _(
                "A filtering aid : obligation matching keys off the template's "
                "regime, never off this."
            ),
            "jurisdiction_country": _(
                "Country name, ISO code, or the literal EU. Blank means the body "
                "is not jurisdiction-specific."
            ),
            "portal_url": _(
                "Rendered as the primary action on the obligation page : one "
                "click from the duty to the form that discharges it."
            ),
            "contact_email": _("The notification mailbox, for regimes filed by email."),
            "contact_phone": _(
                "Several CSIRTs expect a call before the written filing, and "
                "that belongs here rather than in someone's memory."
            ),
            "notification_language": _(
                "A filing rejected for language is a filing not made, and the "
                "clock does not stop."
            ),
            "procedure": _(
                "Which form, which attachments, who signs, what the "
                "acknowledgement looks like, and what to do when the portal is "
                "down."
            ),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class ReportingObligationTemplateForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """The rule that turns incident facts into an owed deliverable.

    A flat conjunction of conditions, deliberately : *significant or affecting
    more than N users* is written as two templates and the generator
    de-duplicates them, rather than the module growing a rule expression
    language nobody can explain to an operator at 02:00.

    The legal terms are snapshotted onto every obligation a match produces, so
    editing a template changes what future incidents generate and changes
    nothing about a filing already made.
    """

    controller_roles = forms.MultipleChoiceField(
        label=_("Controller roles"),
        choices=ControllerRole.choices,
        required=False,
        widget=forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 3}),
        help_text=_(
            "Empty means any. This is what separates a controller's Art. 33(1) "
            "duty from a processor's Art. 33(2) duty."
        ),
    )
    applicable_categories = forms.MultipleChoiceField(
        label=_("Applicable categories"),
        choices=ThreatCategory.choices,
        required=False,
        widget=forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 6}),
        help_text=_("Empty means every category."),
    )

    steps = [
        Step(_("Rule"), "file-earmark-ruled", [
            "name",
            ["regime", "recipient_kind"],
            "authority",
            "legal_reference",
        ]),
        Step(_("Clock"), "clock-history", [
            ["clock_anchor", "clock_hours"],
            "no_fixed_deadline",
            "depends_on_regime",
        ]),
        Step(_("Trigger conditions"), "funnel", [
            ["jurisdiction_country", "min_severity"],
            ["requires_significant", "requires_personal_data"],
            ["requires_high_risk", "requires_cross_border"],
            "controller_roles",
            "applicable_categories",
        ]),
        Step(_("Content"), "card-checklist", [
            "content_requirements",
            "order",
            "tags",
        ]),
    ]

    class Meta:
        model = ReportingObligationTemplate
        fields = [
            "name", "authority", "regime", "recipient_kind", "legal_reference",
            "content_requirements",
            "clock_anchor", "clock_hours", "no_fixed_deadline",
            "depends_on_regime",
            "jurisdiction_country", "min_severity",
            "requires_significant", "requires_personal_data",
            "requires_high_risk", "requires_cross_border",
            "controller_roles", "applicable_categories",
            "order",
            "tags",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "authority": forms.Select(attrs=SELECT_ATTRS),
            "regime": forms.Select(attrs=SELECT_ATTRS),
            "recipient_kind": forms.Select(attrs=SELECT_ATTRS),
            "legal_reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "content_requirements": _textarea(5),
            "clock_anchor": forms.Select(attrs=SELECT_ATTRS),
            "clock_hours": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": "0"}),
            "no_fixed_deadline": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "depends_on_regime": forms.Select(attrs=SELECT_ATTRS),
            "jurisdiction_country": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "min_severity": forms.Select(attrs=SELECT_ATTRS),
            "requires_significant": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "requires_personal_data": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "requires_high_risk": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "requires_cross_border": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _(
                "Say which variant this row is : the catalogue holds "
                "near-duplicates on purpose, e.g. 'NIS2 early warning (24h) - "
                "ANSSI'."
            ),
            "authority": _(
                "Leave empty for a recipient that is not an authority : data "
                "subjects, customers, the public."
            ),
            "regime": _("The legal basis the generated obligation arises from."),
            "recipient_kind": _("Who a generated filing goes to."),
            "legal_reference": _(
                "The article citation copied onto every obligation this rule "
                "produces."
            ),
            "content_requirements": _(
                "The legal checklist, copied onto the obligation and rendered "
                "beside its drafting field."
            ),
            "clock_anchor": _(
                "Legal awareness is the correct anchor for a statutory clock. "
                "Technical detection exists here only for the rare contractual "
                "clause genuinely written against it."
            ),
            "clock_hours": _(
                "The statutory delay in hours : 24, 72, 720 for a month."
            ),
            "no_fixed_deadline": _(
                "A without-undue-delay duty. Generated obligations then carry no "
                "due date and are never counted late."
            ),
            "depends_on_regime": _(
                "The sibling regime whose first filing anchors this one, for a "
                "staged report."
            ),
            "jurisdiction_country": _("Blank means the rule is not restricted by country."),
            "min_severity": _("Blank means the rule fires at any severity."),
            "requires_significant": _(
                "An undetermined significance is not a match, and never silently "
                "suppresses the duty either."
            ),
            "requires_personal_data": _(
                "Fires only on an incident that declares personal data."
            ),
            "requires_high_risk": _(
                "Evaluated against the breach qualification's Art. 34 verdict."
            ),
            "requires_cross_border": _(
                "The incident's operational cross-border impact, not the GDPR "
                "notion of cross-border processing."
            ),
            "order": _(
                "So the 24h early warning is listed above the 72h notification "
                "rather than alphabetically."
            ),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _restrict_fk(self, "authority")

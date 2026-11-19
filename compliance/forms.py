# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import base64

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from context.models import Scope
from context.widgets import ImageUploadWidget, ScopeTreeWidget
from compliance.constants import (
    ASSESSMENT_LOCKED_STATUSES,
    ComplianceStatus,
    FindingSource,
)
from helpers.image_utils import generate_image_variants
from .models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    AssessmentResult,
    Finding,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)
from .models.assessment import ALLOWED_ATTACHMENT_EXTENSIONS
from core.query_params import parse_uuid
from core.scoping import restrict_form_relations
from core.modal_forms import CreationFormMixin, pick_among_active_people, ScopedFormMixin, Step, SteppedFormMixin

User = get_user_model()

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}


def _file_to_data_uri(uploaded_file):
    """Convert an uploaded file to a base64 data URI string."""
    data = base64.b64encode(uploaded_file.read()).decode()
    return f"data:{uploaded_file.content_type};base64,{data}"


def _set_logo_with_variants(instance, data_uri):
    """Set the logo field and generate 16/32/64 variants."""
    instance.logo = data_uri
    variants = generate_image_variants(data_uri)
    instance.logo_16 = variants[16]
    instance.logo_32 = variants[32]
    instance.logo_64 = variants[64]




class FrameworkBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    logo = forms.CharField(label=_("Logo"), required=False, widget=ImageUploadWidget())

    # One step per card of the framework page : a step opens on its own from
    # its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "journal-check",
             [[("logo", "auto"), "name"], ["short_name", "framework_version"],
              ["type", "category"], "description", "scopes", "tags"],
             key="identity"),
        Step(_("Publication"), "calendar-event",
             ["issuing_body", "jurisdiction", "url",
              ["publication_date", "effective_date"], "expiry_date"],
             key="publication"),
        Step(_("Applicability"), "check2-square",
             [["is_mandatory", "is_applicable"], "applicability_managed_by_risks",
              "applicability_justification"],
             key="applicability",
             intro=_("Whether this framework binds you, and whether it applies to what you do. An auditor reads both.")),
        Step(_("Follow-up"), "person-check",
             [["owner", "review_date"], "status"],
             key="follow_up"),
    ]

    class Meta:
        model = Framework
        fields = [
            "scopes", "name", "short_name", "description",
            "type", "category", "framework_version",
            "publication_date", "effective_date", "expiry_date",
            "issuing_body", "jurisdiction", "url",
            "is_mandatory", "is_applicable", "applicability_managed_by_risks",
            "applicability_justification",
            "owner", "status", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "short_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "framework_version": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "publication_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "effective_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "expiry_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "issuing_body": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "jurisdiction": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "url": forms.URLInput(attrs=FORM_WIDGET_ATTRS),
            "is_mandatory": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "is_applicable": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "applicability_managed_by_risks": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "applicability_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "logo": "",
            "name": _('Its full title, for example "ISO/IEC 27001:2022" or "Security clauses of the Acme contract".'),
            "short_name": _('What people call it, for example "ISO 27001". Shown where space is short.'),
            "framework_version": _('The edition you follow, for example "2022".'),
            "type": _("A standard you choose to follow, a law or a regulation you must, a contract you signed."),
            "category": "",
            "description": _("What it asks of you, in a sentence or two."),
            "issuing_body": _('Who wrote it, for example "ISO" or "European Union".'),
            "jurisdiction": _('Where it applies, for example "European Union" or "France".'),
            "url": "",
            "publication_date": "",
            "effective_date": _("The day it starts to apply."),
            "expiry_date": _("The day it stops applying, when it is replaced or repealed."),
            "is_mandatory": _("Tick when you have no choice : a law, a regulation, a contract you signed."),
            "is_applicable": _("Untick when it does not concern what you do, and say why below."),
            "applicability_managed_by_risks": _(
                "Tick to let each requirement apply as soon as an active risk is linked to it, instead of deciding one by one."
            ),
            "applicability_justification": _("The reason it applies or not : what an auditor asks first."),
            "owner": _("The person who answers for your compliance with it."),
            "review_date": _("When to check it is still the edition in force. Once a year is usual."),
            "status": _("Whether you follow it today. It is kept beside its lifecycle, which says whether this record is validated."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        if "logo" in self.fields and self.instance.pk and getattr(self.instance, "logo", ""):
            self.fields["logo"].initial = self.instance.logo
        pick_among_active_people(self, ("owner",))

    def save(self, commit=True):
        framework = super().save(commit=False)
        # The logo is touched only by a form that asks for it : another section
        # (or the creation form) must not clear the one on file.
        if "logo" in self.fields:
            data_uri = self.cleaned_data.get("logo")
            if data_uri:
                _set_logo_with_variants(framework, data_uri)
            elif self.instance.pk:
                framework.logo = ""
                framework.logo_16 = ""
                framework.logo_32 = ""
                framework.logo_64 = ""
        if commit:
            framework.save()
            self.save_m2m()
        return framework


class FrameworkCreateForm(CreationFormMixin, FrameworkBaseForm):
    """Framework creation : what it is called, what kind of text it is and who answers for it.

    Its requirements are what makes it useful : the page of the new framework
    asks for them first.
    """

    #: Not asked at creation.
    logo = None

    steps = [
        Step(_("Identity"), "journal-check",
             ["name", "short_name", ["type", "category"], "owner", "scopes"]),
    ]

    class Meta(FrameworkBaseForm.Meta):
        fields = ["scopes", "name", "short_name", "type", "category", "owner"]


class FrameworkUpdateForm(FrameworkBaseForm):
    """Framework edition modal form."""


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = [
            "framework", "parent_section", "name",
            "description", "order",
        ]
        widgets = {
            "framework": forms.Select(attrs=SELECT_ATTRS),
            "parent_section": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }


class RequirementBaseForm(SteppedFormMixin, forms.ModelForm):
    linked_risks = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        label=_("Linked risks"),
        widget=forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-risks": "true"}),
    )

    # One step per card of the requirement page : a step opens on its own from
    # its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "card-text",
             ["framework", "section", ["requirement_number", "type"], "name", "category", "tags"],
             key="identity"),
        Step(_("Content"), "text-paragraph",
             ["description", "guidance"],
             key="content"),
        Step(_("Applicability"), "check2-circle",
             ["is_applicable", "applicability_justification"],
             key="applicability",
             intro=_("Whether this requirement concerns you, and why : an auditor asks for the reason of every exclusion.")),
        Step(_("Follow-up"), "person-check",
             [["owner", "priority"], ["target_date", "status"]],
             key="follow_up"),
        Step(_("Relationships"), "diagram-3",
             ["linked_risks", "linked_assets", "linked_stakeholder_expectations"],
             key="relationships",
             intro=_("The risks this requirement reduces, what it protects, and who expects it of you.")),
    ]

    class Meta:
        model = Requirement
        fields = [
            "framework", "section", "requirement_number", "name",
            "description", "guidance", "type", "category",
            "is_applicable", "applicability_justification",
            "linked_risks",
            "linked_assets", "linked_stakeholder_expectations",
            "owner", "priority", "target_date",
            "status", "tags",
        ]
        widgets = {
            "framework": forms.Select(attrs=SELECT_ATTRS),
            "section": forms.Select(attrs=SELECT_ATTRS),
            "requirement_number": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 6, "class": "form-control rich-text"}),
            "guidance": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 5, "class": "form-control rich-text"}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "is_applicable": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "applicability_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3, "class": "form-control rich-text"}),
            "linked_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-assets": "true"}),
            "linked_stakeholder_expectations": forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-expectations": "true"}),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "framework": "",
            "section": _('The part of the framework it sits in, for example "A.5 Organizational controls".'),
            "requirement_number": _('As the framework numbers it, for example "A.5.1" or "Article 32".'),
            "name": _('As the framework words it, for example "Policies for information security".'),
            "type": _("Whether the framework demands it or only recommends it."),
            "category": "",
            "description": _("What the framework asks, in its own words or summed up."),
            "guidance": _("How to meet it in practice, and what an auditor expects to see."),
            "is_applicable": _("Untick when it does not concern what you do, and say why below."),
            "applicability_justification": _("The reason it applies or not : what an auditor asks first."),
            "linked_assets": "",
            "linked_stakeholder_expectations": "",
            "owner": _("The person who answers for meeting it."),
            "priority": _("How soon it must be met, compared with the other requirements."),
            "target_date": _("The day you aim to meet it by."),
            "status": _("Whether the framework still asks it. It is kept beside its lifecycle, which says whether this record is validated."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, user=None, **kwargs):
        #: Who fills the form : what it offers stays within their scopes.
        self.user = user
        super().__init__(*args, **kwargs)
        from core.lifecycle import linkable_or_linked
        from risks.models import Risk

        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        editing = bool(self.instance and self.instance.pk)
        if "linked_risks" in self.fields:
            self.fields["linked_risks"].help_text = _("The risks this requirement helps to reduce.")
            self.fields["linked_risks"].queryset = linkable_or_linked(
                Risk.objects.all(),
                self.instance.linked_risks.all() if editing else None,
            )
            if editing:
                self.fields["linked_risks"].initial = self.instance.linked_risks.all()
        for fname in ("linked_assets", "linked_stakeholder_expectations"):
            field = self.fields.get(fname)
            if field is not None:
                field.queryset = linkable_or_linked(
                    field.queryset,
                    getattr(self.instance, fname).all() if editing else None,
                )
        pick_among_active_people(self, ("owner",))
        self._offer_the_sections_of_the_framework()

        # When the framework derives applicability from risks, the applicability
        # fields are system-controlled: disable them so they cannot be edited
        # (a disabled field is ignored on submit, and recompute is authoritative).
        framework = self.instance.framework if self.instance.framework_id else None
        self.applicability_is_managed = bool(
            framework and framework.applicability_managed_by_risks
        )
        if self.applicability_is_managed:
            note = _("Managed automatically from linked risks for this framework.")
            for fname in ("is_applicable", "applicability_justification"):
                if fname in self.fields:
                    self.fields[fname].disabled = True
                    self.fields[fname].help_text = note
        # A requirement hangs under its framework : the frameworks, the risks
        # and the assets offered are those the user may reach.
        if user is not None:
            restrict_form_relations(self, user)

    def _offer_the_sections_of_the_framework(self):
        """A section is picked within the framework of the requirement.

        Shown on a known framework (the record's, or the one the form was
        opened on) : its sections alone. Otherwise every section says which
        framework it belongs to. :meth:`clean` refuses a mismatch in words,
        whatever was posted.
        """
        section = self.fields.get("section")
        if section is None:
            return
        chosen = None if self.is_bound else (self.instance.framework_id or self.initial.get("framework"))
        framework_id = parse_uuid(getattr(chosen, "pk", chosen))
        if framework_id:
            section.queryset = section.queryset.filter(framework_id=framework_id)
        else:
            section.queryset = section.queryset.select_related("framework")
            section.label_from_instance = lambda s: f"{s.framework.short_name or s.framework.name} : {s.name}"

    def clean(self):
        cleaned = super().clean()
        section, framework = cleaned.get("section"), cleaned.get("framework")
        if section and framework and section.framework_id != framework.pk:
            self.add_error("section", _("This section belongs to another framework."))
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=commit)
        # The risks are touched only by a form that asks for them : another
        # section (or the creation form) must not unlink the ones on file.
        if "linked_risks" not in self.fields:
            return instance
        if commit:
            instance.linked_risks.set(self.cleaned_data["linked_risks"])
        else:
            old_save_m2m = self.save_m2m

            def save_m2m():
                old_save_m2m()
                instance.linked_risks.set(self.cleaned_data["linked_risks"])

            self.save_m2m = save_m2m
        return instance


class RequirementCreateForm(CreationFormMixin, RequirementBaseForm):
    """Requirement creation : where it comes from, how it is numbered and what it asks.

    Whether it applies, who answers for it and what it is linked to are
    decided on its page.
    """

    #: Not asked at creation.
    linked_risks = None
    #: Who answers for meeting a requirement is decided on its page : filing
    #: the text of a framework does not make its author answerable for it.
    owner_field = None

    steps = [
        Step(_("Identity"), "card-text",
             ["framework", "section", ["requirement_number", "type"], "name", "description"]),
    ]

    class Meta(RequirementBaseForm.Meta):
        fields = ["framework", "section", "requirement_number", "name", "type", "description"]


class RequirementUpdateForm(RequirementBaseForm):
    """Requirement edition modal form."""


class ComplianceAssessmentBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the assessment page : a step opens on its own from
    # its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "clipboard-check",
             ["name", "frameworks", "assessor", "scopes", "tags"],
             key="identity"),
        Step(_("Dates and objectives"), "calendar-check",
             [["assessment_start_date", "assessment_end_date"], "description", "limitations"],
             key="planning",
             intro=_("When it takes place, what it is for and what it leaves out. An assessment is planned once its dates are set.")),
    ]

    class Meta:
        model = ComplianceAssessment
        fields = [
            "scopes", "frameworks", "name", "description", "limitations",
            "assessment_start_date", "assessment_end_date",
            "assessor",
            "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "frameworks": forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-frameworks": "true"}),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "limitations": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "assessment_start_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "assessment_end_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "assessor": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('For example "ISO 27001 internal audit 2026".'),
            "frameworks": _("What you are measured against. Each of their requirements gets a line to assess."),
            "assessor": _("The person who conducts the assessment : an internal auditor, or the account given to an external one."),
            "description": _('Why it is held and what it must conclude, for example "Readiness check before the certification audit".'),
            "limitations": _('What it does not cover, for example "The Madrid site was not visited".'),
            "assessment_start_date": "",
            "assessment_end_date": "",
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pick_among_active_people(self, ("assessor",))
        # The lifecycle step is driven by the stepper, not this form: once the
        # assessment is locked (in progress onward), its metadata is read-only.
        if self.instance and self.instance.pk and self.instance.status in ASSESSMENT_LOCKED_STATUSES:
            for field in self.fields.values():
                field.disabled = True

    def clean(self):
        cleaned = super().clean()
        # What a step waits for is the model's ``COMPLETENESS``, held by the
        # lifecycle on every surface; the form only enforces a coherent range.
        start = cleaned.get("assessment_start_date")
        end = cleaned.get("assessment_end_date")
        if start and end and end < start:
            self.add_error(
                "assessment_end_date",
                _("End date must be after start date."),
            )
        return cleaned


class ComplianceAssessmentCreateForm(CreationFormMixin, ComplianceAssessmentBaseForm):
    """Assessment creation : what it is called, what it measures against, who leads it and when.

    Its context, its objectives and its limitations are written on its page.
    """

    #: Who leads an assessment is asked : an auditor is seldom whoever files it,
    #: and the creator must not become the lead assessor by default.
    owner_field = None

    steps = [
        Step(_("Identity"), "clipboard-check",
             ["name", "frameworks", "assessor", ["assessment_start_date", "assessment_end_date"], "scopes"]),
    ]

    class Meta(ComplianceAssessmentBaseForm.Meta):
        fields = ["scopes", "frameworks", "name", "assessment_start_date", "assessment_end_date", "assessor"]


class ComplianceAssessmentUpdateForm(ComplianceAssessmentBaseForm):
    """Compliance assessment edition modal form."""


class AssessmentResultForm(forms.ModelForm):
    class Meta:
        model = AssessmentResult
        fields = [
            "requirement", "compliance_status", "compliance_level",
            "finding", "auditor_recommendations", "evidence",
        ]
        widgets = {
            "requirement": forms.Select(attrs=SELECT_ATTRS),
            "compliance_status": forms.Select(attrs={
                **SELECT_ATTRS,
                "data-compliance-level-defaults": (
                    '{"not_assessed":0,"evaluated":50,'
                    '"major_non_conformity":0,'
                    '"minor_non_conformity":30,"observation":50,'
                    '"improvement_opportunity":70,"compliant":100,'
                    '"strength":100,"not_applicable":100}'
                ),
            }),
            "compliance_level": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 0, "max": 100}),
            "finding": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "auditor_recommendations": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "evidence": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }

    def __init__(self, *args, assessment=None, requirement_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assessment:
            self.fields["requirement"].queryset = assessment.get_all_requirements().order_by("requirement_number")
        if requirement_instance:
            self.fields["requirement"].initial = requirement_instance.pk
            self.fields["requirement"].queryset = Requirement.objects.filter(pk=requirement_instance.pk)
            self.fields["requirement"].widget.attrs["disabled"] = True
            # Lock status fields for non-applicable requirements
            if not requirement_instance.is_applicable:
                self._is_non_applicable = True
                self.fields["compliance_status"].initial = ComplianceStatus.NOT_APPLICABLE
                self.fields["compliance_status"].widget.attrs["disabled"] = True
                self.fields["compliance_level"].initial = 100
                self.fields["compliance_level"].widget.attrs["disabled"] = True

    def clean(self):
        cleaned = super().clean()
        if getattr(self, "_is_non_applicable", False):
            cleaned["compliance_status"] = ComplianceStatus.NOT_APPLICABLE
            cleaned["compliance_level"] = 100
        return cleaned


class FindingBaseForm(SteppedFormMixin, forms.ModelForm):
    # The dialog of an audit : one screen, filled in while the fact is fresh.
    steps = [
        Step(_("Finding"), "exclamation-diamond",
             ["finding_type", "requirements", "description", "recommendation", "evidence"]),
    ]

    class Meta:
        model = Finding
        fields = [
            "finding_type", "requirements",
            "description", "recommendation", "evidence",
        ]
        widgets = {
            "finding_type": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "recommendation": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "evidence": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "requirements": forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-requirements": "true"}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "finding_type": _("A nonconformity is to be corrected, an observation or an opportunity is a remark, a strength is what works well."),
            "requirements": _("What it was noticed against : the result of these requirements in this assessment follows from it."),
            "description": _('What was noticed, as a fact, for example "Three of ten leavers still had an active account".'),
            "recommendation": _("What the assessor suggests. Deciding what is done belongs to whoever answers for the requirement."),
            "evidence": _('What was seen or shown, for example "Account export of 12 March, interview with the service desk".'),
        }

    def __init__(self, *args, assessment=None, raised_by=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assessment:
            self.fields["requirements"].queryset = assessment.get_all_requirements().order_by("requirement_number")
            # Stamped before validation, not after it : `Finding.clean()`
            # requires both for `source = audit`, and it runs while the form
            # validates. Setting them in `form_valid()` would be too late.
            self.instance.assessment = assessment
        else:
            self.fields["requirements"].queryset = Requirement.objects.none()
        if raised_by and self.instance.assessor_id is None:
            self.instance.assessor = raised_by


class FindingCreateForm(FindingBaseForm):
    """Finding creation modal form."""


class FindingUpdateForm(FindingBaseForm):
    """Finding edition modal form."""


class FindingRegisterForm(SteppedFormMixin, forms.ModelForm):
    """Raise or edit a nonconformity from the register, outside any audit.

    Distinct from `FindingBaseForm`, which is the in-audit modal : here the
    source is chosen rather than implied, the audit link is optional, and the
    clause 10.2 d) effectiveness review is exposed. Requirements are picked
    from the whole catalogue, since there is no assessment to narrow them to.
    """

    # One step per card of the nonconformity page : a step opens on its own
    # from its card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Nonconformity"), "exclamation-diamond",
             [["source", "finding_type"], "description", "requirements"],
             key="nonconformity"),
        Step(_("Treatment"), "lightbulb",
             ["recommendation", "evidence"],
             key="treatment"),
        Step(_("Effectiveness"), "check2-circle",
             [["effectiveness_verdict", "effectiveness_reviewed_at"],
              "effectiveness_reviewed_by"],
             key="effectiveness",
             intro=_("Once the corrective action is done : did it work? A closed action plan proves the action was carried out, not that it worked.")),
    ]

    class Meta:
        model = Finding
        fields = [
            "source", "finding_type", "description", "requirements",
            "recommendation", "evidence",
            "effectiveness_verdict", "effectiveness_reviewed_at",
            "effectiveness_reviewed_by",
        ]
        widgets = {
            "source": forms.Select(attrs=SELECT_ATTRS),
            "finding_type": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "recommendation": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "evidence": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "requirements": forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-requirements": "true"}),
            "effectiveness_verdict": forms.Select(attrs=SELECT_ATTRS),
            "effectiveness_reviewed_at": forms.DateTimeInput(
                attrs={**FORM_WIDGET_ATTRS, "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "effectiveness_reviewed_by": forms.Select(attrs=SELECT_ATTRS),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "source": _("How it came to light : an incident, a management review, what monitoring showed, a complaint."),
            "finding_type": _("A nonconformity is to be corrected, an observation or an opportunity is a remark, a strength is what works well."),
            "description": _('What was noticed, as a fact, for example "Three of ten leavers still had an active account".'),
            "requirements": _("Leave it empty when one of your own rules is broken rather than a requirement of a framework."),
            "recommendation": _("What is suggested to correct it. The work itself is followed in an action plan."),
            "evidence": _('What was seen or shown, for example "Account export of 12 March, interview with the service desk".'),
            "effectiveness_verdict": "",
            "effectiveness_reviewed_at": "",
            "effectiveness_reviewed_by": _("Someone other than whoever carried out the action, where you can."),
        }

    def __init__(self, *args, user=None, raised_by=None, **kwargs):
        #: Who fills the form : what it offers stays within their scopes.
        self.user = user
        raised_by = raised_by or user
        super().__init__(*args, **kwargs)
        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        if "requirements" in self.fields:
            self.fields["requirements"].queryset = Requirement.objects.select_related(
                "framework"
            ).order_by("framework__name", "requirement_number")
        pick_among_active_people(self, ("effectiveness_reviewed_by",))
        if raised_by and self.instance.assessor_id is None:
            self.instance.assessor = raised_by
        source = self.fields.get("source")
        if source is not None:
            # RG-CTL-16 : a "control test" finding is raised from its run, never
            # declared by hand, and keeps that source once raised.
            if self.instance.control_test_run_id or self.instance.source == FindingSource.CONTROL_TEST:
                source.choices = [c for c in source.choices if c[0] == FindingSource.CONTROL_TEST]
            else:
                source.choices = [c for c in source.choices if c[0] != FindingSource.CONTROL_TEST]
            # RG-FND-01 : an audit finding needs its audit, and this form carries no
            # audit field : such a finding is raised from inside its assessment. The
            # "Audit" source is therefore only kept for a finding that already has
            # one (edited from the register). Offering it here let the model rule
            # fail on a field the form does not have, which crashed the page.
            if self.instance.assessment_id is None:
                source.choices = [c for c in source.choices if c[0] != FindingSource.AUDIT]
                if self.instance.pk is None and self.instance.source == FindingSource.AUDIT:
                    # The model default is "audit" : start on the first source this
                    # form can actually record.
                    source.initial = source.choices[0][0] if source.choices else None
        if user is not None:
            restrict_form_relations(self, user)


class FindingRegisterCreateForm(CreationFormMixin, FindingRegisterForm):
    """Raising a nonconformity : how it came to light, what it is and what it was noticed against.

    What is recommended and whether the correction worked are written on its
    page, when they are known.
    """

    #: Nobody answers for a nonconformity by filing it : who raised it is
    #: recorded, and its correction is followed in an action plan.
    owner_field = None
    #: How it came to light and what kind of finding it is are decided by the
    #: reader : the model default ("audit") cannot even be recorded here.
    decisions = ("source", "finding_type")

    steps = [
        Step(_("Nonconformity"), "exclamation-diamond",
             [["source", "finding_type"], "description", "requirements"]),
    ]

    class Meta(FindingRegisterForm.Meta):
        fields = ["source", "finding_type", "description", "requirements"]


class FindingRegisterUpdateForm(FindingRegisterForm):
    """Nonconformity edition modal form."""


class RequirementMappingBaseForm(SteppedFormMixin, forms.ModelForm):
    """Shared base for the inter-framework mapping create / edit modals.

    A single-step form: the modal shows a required-fields completion meter
    instead of a stepper.
    """

    steps = [
        Step(
            _("Requirements"),
            "arrow-left-right",
            [
                ["source_requirement", "target_requirement"],
                ["mapping_type", "coverage_level"],
                "description", "justification",
            ],
        ),
    ]

    class Meta:
        model = RequirementMapping
        fields = [
            "source_requirement", "target_requirement",
            "mapping_type", "coverage_level",
            "description", "justification",
        ]
        widgets = {
            "source_requirement": forms.Select(attrs=SELECT_ATTRS),
            "target_requirement": forms.Select(attrs=SELECT_ATTRS),
            "mapping_type": forms.Select(attrs=SELECT_ATTRS),
            "coverage_level": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
        help_texts = {
            "source_requirement": _("The requirement being mapped from."),
            "target_requirement": _("The requirement it maps to."),
            "mapping_type": _(
                "Nature of the relationship between the two requirements."
            ),
            "coverage_level": _(
                "How fully the source requirement is covered by the target."
            ),
            "description": _("Optional summary of the mapping."),
            "justification": _("Why this mapping holds."),
        }


class RequirementMappingCreateForm(RequirementMappingBaseForm):
    """Mapping creation modal form."""


class RequirementMappingUpdateForm(RequirementMappingBaseForm):
    """Mapping edition modal form."""


MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class FrameworkImportForm(forms.Form):
    file = forms.FileField(
        label=_("File"),
        help_text=_("JSON or Excel (.xlsx) format"),
        widget=forms.ClearableFileInput(attrs=FORM_WIDGET_ATTRS),
    )
    existing_framework = forms.ModelChoiceField(
        queryset=Framework.objects.all(),
        required=False,
        label=_("Existing framework"),
        help_text=_("Leave blank to create a new framework."),
        widget=forms.Select(attrs={**SELECT_ATTRS, "class": "form-select"}),
        empty_label=_("- New framework -"),
    )
    owner = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        label=_("Framework owner"),
        help_text=_("Required only for a new framework."),
        widget=forms.Select(attrs=SELECT_ATTRS),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        if ext not in ("json", "xlsx"):
            raise forms.ValidationError(
                _("Unsupported format. Please provide a .json or .xlsx file.")
            )
        if f.size > MAX_IMPORT_FILE_SIZE:
            raise forms.ValidationError(
                _("The file exceeds the maximum allowed size (10 MB).")
            )
        return f

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("existing_framework") and not cleaned.get("owner"):
            self.add_error(
                "owner",
                _("The owner is required to create a new framework."),
            )
        return cleaned


class ComplianceActionPlanBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the plan page : a step opens on its own from its
    # card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "list-check",
             ["name", "description", "scopes", "tags"],
             key="identity"),
        Step(_("Gap & remediation"), "clipboard-data",
             ["gap_description", "remediation_plan"],
             key="remediation",
             intro=_("What is wrong today, and what will be done about it. A plan is submitted for validation once both are written.")),
        Step(_("People and planning"), "calendar-range",
             [["owner", "priority"], "assignees",
              ["start_date", "target_date"],
              ["completion_date", "progress_percentage"], "cost_estimate"],
             key="planning"),
        Step(_("Linkages"), "link-45deg",
             ["risks", "findings", "requirements"],
             key="linkages",
             intro=_("What this plan answers : the risks it reduces, the findings it corrects, the requirements it helps to meet.")),
    ]

    class Meta:
        model = ComplianceActionPlan
        fields = [
            "scopes", "name", "description",
            "risks", "findings", "requirements",
            "gap_description", "remediation_plan",
            "priority", "owner", "assignees",
            "start_date", "target_date", "completion_date",
            "progress_percentage", "cost_estimate", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "risks": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "findings": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "requirements": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "gap_description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "remediation_plan": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "assignees": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "start_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "completion_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "progress_percentage": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 0, "max": 100}),
            "cost_estimate": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "0.01"}),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('What is to be done, for example "Encrypt the laptops of the sales team".'),
            "priority": _("How soon it must be done, compared with the other plans."),
            "owner": _("The person who follows the plan and answers for its result."),
            "assignees": _("Those who do the work."),
            "description": _("The context, in a sentence or two : what led to this plan."),
            "gap_description": _('What is wrong today, for example "Half of the laptops are not encrypted".'),
            "remediation_plan": _("What will be done, step by step, to close that gap."),
            "risks": "",
            "findings": "",
            "requirements": "",
            "start_date": "",
            "target_date": _("The day it must be done by. A plan past this date reads as overdue."),
            "completion_date": _("Closing the plan sets it to the day it is closed."),
            "progress_percentage": _("Your own estimate. Closing the plan sets it to 100."),
            "cost_estimate": _("An order of magnitude is enough, in your usual currency."),
            "scopes": _("Users limited to certain scopes see only what is filed under theirs."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pick_among_active_people(self, ("owner",))


class ComplianceActionPlanCreateForm(CreationFormMixin, ComplianceActionPlanBaseForm):
    """Action plan creation : what is to be done, by whom, how soon and for when.

    The gap and its remediation are written on the plan page : they are what
    the "to define" step of its lifecycle is for, and what it waits for
    before the plan is submitted for validation.
    """

    #: A priority has no default answer : the reader decides.
    decisions = ("priority",)

    steps = [
        Step(_("Identity"), "list-check", ["name", ["owner", "priority"], "target_date", "scopes", "description"]),
    ]

    class Meta(ComplianceActionPlanBaseForm.Meta):
        fields = ["scopes", "name", "description", "priority", "owner", "target_date"]


class ComplianceActionPlanUpdateForm(ComplianceActionPlanBaseForm):
    """Action plan edition modal form."""


class ActionPlanTransitionForm(forms.Form):
    target_status = forms.CharField(widget=forms.HiddenInput())
    comment = forms.CharField(
        widget=forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        required=False,
        label=_("Comment"),
    )


class _MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class AssessmentResultAttachmentForm(forms.Form):
    files = forms.FileField(
        label=_("Analyzed documents"),
        widget=_MultiFileInput(attrs={
            "class": "form-control form-control-sm",
            "accept": ", ".join(f".{ext}" for ext in ALLOWED_ATTACHMENT_EXTENSIONS),
        }),
        required=False,
    )

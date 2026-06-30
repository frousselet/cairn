import base64

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from context.models import Scope
from context.widgets import ImageUploadWidget, ScopeTreeWidget
from compliance.constants import (
    ASSESSMENT_LOCKED_STATUSES,
    ComplianceStatus,
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
from core.modal_forms import Step, SteppedFormMixin

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


class ScopedFormMixin:
    """Populate the scopes tree widget with the user's accessible scopes."""

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if "scopes" in self.fields:
            qs = Scope.objects.exclude(workflow_state="archived")
            if user and not user.is_superuser:
                scope_ids = user.get_allowed_scope_ids()
                if scope_ids is not None:
                    qs = qs.filter(id__in=scope_ids)
            field = self.fields["scopes"]
            field.queryset = qs
            selected_ids = []
            if self.instance and self.instance.pk:
                selected_ids = list(self.instance.scopes.values_list("pk", flat=True))
            elif self.data:
                selected_ids = self.data.getlist(self.add_prefix("scopes"))
            field.widget.build_tree_data(qs, selected_ids)


class FrameworkBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    logo = forms.CharField(label=_("Logo"), required=False, widget=ImageUploadWidget())

    steps = [
        Step(_("Identity"), "journal-check",
             [[("logo", "auto"), "name"], ["short_name", "framework_version"],
              ["type", "category"], "description"]),
        Step(_("Publication"), "calendar-event",
             ["issuing_body", "jurisdiction", "url",
              ["publication_date", "effective_date"], "expiry_date"]),
        Step(_("Applicability"), "check2-square",
             [["is_mandatory", "is_applicable"], "applicability_managed_by_risks",
              "applicability_justification", ["owner", "review_date"]]),
        Step(_("Scope & status"), "diagram-3", ["scopes", "status", "tags"]),
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
        help_texts = {
            "logo": "",
            "name": _("Name of the framework."),
            "short_name": _("Short name or acronym."),
            "framework_version": _("Version of the framework."),
            "type": _("Kind of framework."),
            "category": _("Category of the framework."),
            "description": _("What the framework covers."),
            "issuing_body": _("Organization that issues the framework."),
            "jurisdiction": _("Jurisdiction where it applies."),
            "url": _("Link to the official framework."),
            "publication_date": _("Date the framework was published."),
            "effective_date": _("Date it takes effect."),
            "expiry_date": _("Date it expires, if any."),
            "is_mandatory": _("Tick if compliance is mandatory."),
            "is_applicable": _("Tick if the framework applies to the organization."),
            "applicability_managed_by_risks": _(
                "Derive each requirement's applicability automatically from its "
                "linked risks (applicable when at least one active risk is linked)."
            ),
            "applicability_justification": _("Why the framework is or is not applicable."),
            "owner": _("Person accountable for the framework."),
            "review_date": _("Next date this framework should be reviewed."),
            "status": _("Lifecycle state of the framework."),
            "scopes": _("Organizational scopes this framework applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and getattr(self.instance, "logo", ""):
            self.fields["logo"].initial = self.instance.logo

    def save(self, commit=True):
        framework = super().save(commit=False)
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


class FrameworkCreateForm(FrameworkBaseForm):
    """Framework creation modal form."""


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


class RequirementForm(forms.ModelForm):
    linked_risks = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        label=_("Linked risks"),
        widget=forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-risks": "true"}),
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.workflow import linkable_or_linked
        from risks.models import Risk

        editing = bool(self.instance and self.instance.pk)
        self.fields["linked_risks"].queryset = linkable_or_linked(
            Risk.objects.all(),
            self.instance.linked_risks.all() if editing else None,
        )
        for fname in ("linked_assets", "linked_stakeholder_expectations"):
            field = self.fields[fname]
            field.queryset = linkable_or_linked(
                field.queryset,
                getattr(self.instance, fname).all() if editing else None,
            )
        if editing:
            self.fields["linked_risks"].initial = self.instance.linked_risks.all()

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
                self.fields[fname].disabled = True
                self.fields[fname].help_text = note

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            instance.linked_risks.set(self.cleaned_data["linked_risks"])
        else:
            old_save_m2m = self.save_m2m
            def save_m2m():
                old_save_m2m()
                instance.linked_risks.set(self.cleaned_data["linked_risks"])
            self.save_m2m = save_m2m
        return instance


class ComplianceAssessmentBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "clipboard-check",
             ["name", "frameworks", "assessor", "description"]),
        Step(_("Planning & status"), "calendar-check",
             [["assessment_start_date", "assessment_end_date"], "limitations",
              "scopes", "tags"]),
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
        help_texts = {
            "name": _("Name of the assessment."),
            "frameworks": _("Frameworks covered by this assessment."),
            "assessor": _("Person leading the assessment."),
            "description": _("Scope and purpose of the assessment."),
            "limitations": _("Known limitations or exclusions."),
            "assessment_start_date": _("Assessment start date."),
            "assessment_end_date": _("Assessment end date."),
            "scopes": _("Organizational scopes this assessment applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The lifecycle step is driven by the stepper, not this form: once the
        # assessment is locked (in progress onward), its metadata is read-only.
        if self.instance and self.instance.pk and self.instance.status in ASSESSMENT_LOCKED_STATUSES:
            for field in self.fields.values():
                field.disabled = True

    def clean(self):
        cleaned = super().clean()
        # Required-field gating per target step lives in the transition view; the
        # form only enforces a coherent date range.
        start = cleaned.get("assessment_start_date")
        end = cleaned.get("assessment_end_date")
        if start and end and end < start:
            self.add_error(
                "assessment_end_date",
                _("End date must be after start date."),
            )
        return cleaned


class ComplianceAssessmentCreateForm(ComplianceAssessmentBaseForm):
    """Compliance assessment creation modal form."""


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
    steps = [
        Step(_("Finding"), "exclamation-diamond",
             ["finding_type", "requirements", "description"]),
        Step(_("Recommendation"), "lightbulb", ["recommendation", "evidence"]),
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
        help_texts = {
            "finding_type": _("Nature of the finding."),
            "requirements": _("Requirements this finding relates to."),
            "description": _("What was observed."),
            "recommendation": _("Suggested corrective action."),
            "evidence": _("Evidence supporting the finding."),
        }

    def __init__(self, *args, assessment=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assessment:
            self.fields["requirements"].queryset = assessment.get_all_requirements().order_by("requirement_number")
        else:
            self.fields["requirements"].queryset = Requirement.objects.none()


class FindingCreateForm(FindingBaseForm):
    """Finding creation modal form."""


class FindingUpdateForm(FindingBaseForm):
    """Finding edition modal form."""


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
    steps = [
        Step(_("Identity"), "list-check",
             ["name", ["priority", "owner"], "assignees", "description"]),
        Step(_("Gap & remediation"), "clipboard-data",
             ["gap_description", "remediation_plan"]),
        Step(_("Planning"), "calendar-range",
             [["start_date", "target_date"],
              ["completion_date", "progress_percentage"], "cost_estimate"]),
        Step(_("Relations & scope"), "diagram-3",
             ["risks", "findings", "requirements", "scopes", "tags"]),
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
        help_texts = {
            "name": _("Name of the action plan."),
            "priority": _("Priority of the plan."),
            "owner": _("Person accountable for the plan."),
            "assignees": _("People working on the plan."),
            "description": _("What the plan covers."),
            "gap_description": _("The gap to close."),
            "remediation_plan": _("How the gap will be remediated."),
            "risks": _("Risks addressed by this plan."),
            "findings": _("Findings addressed by this plan."),
            "requirements": _("Requirements addressed by this plan."),
            "start_date": _("Planned start date."),
            "target_date": _("Planned completion date."),
            "completion_date": _("Actual completion date."),
            "progress_percentage": _("Completion from 0 to 100."),
            "cost_estimate": _("Estimated cost."),
            "scopes": _("Organizational scopes this plan applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class ComplianceActionPlanCreateForm(ComplianceActionPlanBaseForm):
    """Action plan creation modal form."""


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

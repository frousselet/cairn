from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from compliance.constants import AssessmentStatus
from compliance.models import ComplianceAssessment, Framework
from context.models import Scope
from core.lifecycle import reportable
from reports.constants import (
    DecisionPriority,
)
from reports.models import (
    IsmsChange,
    ManagementReview,
    ManagementReviewComment,
    ManagementReviewDecision,
    ManagementReviewParticipant,
)

User = get_user_model()

_FORM_CONTROL = {"class": "form-control"}
_FORM_SELECT = {"class": "form-select"}
_FORM_CHECK = {"class": "form-check-input"}
_FORM_DATE = {"class": "form-control", "type": "date"}


class SoaReportForm(forms.Form):
    frameworks = forms.ModelMultipleChoiceField(
        queryset=Framework.objects.all(),
        label=_("Frameworks"),
        help_text=_("Select one or more frameworks to include in the Statement of Applicability."),
        widget=forms.SelectMultiple(attrs={
            "class": "form-select",
            "size": 8,
        }),
    )


class AuditReportForm(forms.Form):
    assessment = forms.ModelChoiceField(
        queryset=ComplianceAssessment.objects.filter(
            workflow_state__in=[AssessmentStatus.COMPLETED, AssessmentStatus.CLOSED],
        ).order_by("-assessment_end_date", "-created_at"),
        label=_("Assessment"),
        help_text=_("Select a completed or closed audit to generate the report."),
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )


class ManagementReviewForm(forms.Form):
    FORMAT_CHOICES = [
        ("pptx", _("Presentation (PowerPoint)")),
        ("docx", _("Meeting minutes (Word)")),
    ]

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        label=_("Format"),
        initial="pptx",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    period_start = forms.DateField(
        label=_("Period start"),
        required=False,
        help_text=_("Start of the review period. Leave empty to include all past data."),
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
    )
    period_end = forms.DateField(
        label=_("Period end"),
        required=False,
        help_text=_("End of the review period. Defaults to today."),
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
    )

    scopes = forms.ModelMultipleChoiceField(
        # In-force scopes only : read the governance code set off the scope
        # lifecycle rather than hardcoding the step.
        queryset=reportable(Scope.objects.all()).order_by("name"),
        label=_("Scopes"),
        required=False,
        help_text=_("Optionally filter data by scope. Leave empty to include all data."),
        widget=forms.SelectMultiple(attrs={
            "class": "form-select",
            "size": 6,
        }),
    )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and start > end:
            raise forms.ValidationError(
                _("The period start date must be before the end date.")
            )
        return cleaned


# ═════════════════════════════════════════════════════════════════════
# Persistent management review forms (ISO 27001:2022 clause 9.3)
# ═════════════════════════════════════════════════════════════════════


class ManagementReviewModelForm(forms.ModelForm):
    class Meta:
        model = ManagementReview
        fields = [
            "title", "description", "frequency",
            "period_start", "period_end", "planned_date", "location",
            "facilitator", "approver", "next_review_date",
            "agenda", "summary",
            "scopes", "tags",
        ]
        widgets = {
            "title": forms.TextInput(attrs=_FORM_CONTROL),
            "description": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
            "frequency": forms.Select(attrs=_FORM_SELECT),
            "period_start": forms.DateInput(attrs=_FORM_DATE),
            "period_end": forms.DateInput(attrs=_FORM_DATE),
            "planned_date": forms.DateInput(attrs=_FORM_DATE),
            "location": forms.TextInput(attrs=_FORM_CONTROL),
            "facilitator": forms.Select(attrs=_FORM_SELECT),
            "approver": forms.Select(attrs=_FORM_SELECT),
            "next_review_date": forms.DateInput(attrs=_FORM_DATE),
            "agenda": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 4}),
            "summary": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 4}),
            "scopes": forms.SelectMultiple(attrs={**_FORM_SELECT, "size": 6}),
            "tags": forms.SelectMultiple(attrs={**_FORM_SELECT, "size": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        active_users = User.objects.filter(is_active=True).order_by(
            "last_name", "first_name", "email",
        )
        self.fields["facilitator"].queryset = active_users
        self.fields["approver"].queryset = active_users
        self.fields["scopes"].queryset = Scope.objects.exclude(
            status="archived",
        ).order_by("name")

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and start > end:
            raise forms.ValidationError(
                _("The period start date must be before the end date.")
            )
        return cleaned


class ManagementReviewParticipantForm(forms.ModelForm):
    class Meta:
        model = ManagementReviewParticipant
        fields = ["user", "external_name", "external_role", "role", "attended"]
        widgets = {
            "user": forms.Select(attrs=_FORM_SELECT),
            "external_name": forms.TextInput(attrs=_FORM_CONTROL),
            "external_role": forms.TextInput(attrs=_FORM_CONTROL),
            "role": forms.Select(attrs=_FORM_SELECT),
            "attended": forms.CheckboxInput(attrs=_FORM_CHECK),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].required = False
        self.fields["user"].queryset = User.objects.filter(
            is_active=True,
        ).order_by("last_name", "first_name", "email")

    def clean(self):
        cleaned = super().clean()
        user = cleaned.get("user")
        external_name = (cleaned.get("external_name") or "").strip()
        if not user and not external_name:
            raise forms.ValidationError(
                _("Provide either an internal user or an external participant name."),
            )
        return cleaned


ParticipantFormSet = forms.inlineformset_factory(
    ManagementReview,
    ManagementReviewParticipant,
    form=ManagementReviewParticipantForm,
    extra=1,
    can_delete=True,
)


class ManagementReviewTransitionForm(forms.Form):
    target_status = forms.CharField(widget=forms.HiddenInput())
    comment = forms.CharField(
        label=_("Comment"),
        required=False,
        widget=forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
    )


class ManagementReviewDecisionForm(forms.ModelForm):
    class Meta:
        model = ManagementReviewDecision
        fields = [
            "category", "input_clause", "title", "description", "rationale",
            "owner", "due_date", "priority", "status",
            "implemented_at", "implementation_evidence",
        ]
        widgets = {
            "category": forms.Select(attrs=_FORM_SELECT),
            "input_clause": forms.Select(attrs=_FORM_SELECT),
            "title": forms.TextInput(attrs=_FORM_CONTROL),
            "description": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
            "rationale": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 2}),
            "owner": forms.Select(attrs=_FORM_SELECT),
            "due_date": forms.DateInput(attrs=_FORM_DATE),
            "priority": forms.Select(attrs=_FORM_SELECT),
            "status": forms.Select(attrs=_FORM_SELECT),
            "implemented_at": forms.DateInput(attrs=_FORM_DATE),
            "implementation_evidence": forms.Textarea(
                attrs={**_FORM_CONTROL, "rows": 2},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = User.objects.filter(
            is_active=True,
        ).order_by("last_name", "first_name", "email")


class IsmsChangeForm(forms.ModelForm):
    class Meta:
        model = IsmsChange
        fields = [
            "change_type", "title", "description", "impact_analysis",
            "affected_scopes", "affected_frameworks", "affected_policies",
            "owner", "status", "target_date", "implemented_at",
        ]
        widgets = {
            "change_type": forms.Select(attrs=_FORM_SELECT),
            "title": forms.TextInput(attrs=_FORM_CONTROL),
            "description": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
            "impact_analysis": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
            "affected_scopes": forms.SelectMultiple(attrs={**_FORM_SELECT, "size": 4}),
            "affected_frameworks": forms.SelectMultiple(attrs={**_FORM_SELECT, "size": 4}),
            "affected_policies": forms.Textarea(attrs={**_FORM_CONTROL, "rows": 2}),
            "owner": forms.Select(attrs=_FORM_SELECT),
            "status": forms.Select(attrs=_FORM_SELECT),
            "target_date": forms.DateInput(attrs=_FORM_DATE),
            "implemented_at": forms.DateInput(attrs=_FORM_DATE),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = User.objects.filter(
            is_active=True,
        ).order_by("last_name", "first_name", "email")
        self.fields["affected_scopes"].queryset = Scope.objects.exclude(
            status="archived",
        ).order_by("name")
        self.fields["affected_frameworks"].queryset = Framework.objects.order_by(
            "short_name", "name",
        )


class ManagementReviewCommentForm(forms.ModelForm):
    class Meta:
        model = ManagementReviewComment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                **_FORM_CONTROL, "rows": 2,
                "placeholder": _("Write a comment"),
            }),
        }


class ParticipantSignatureForm(forms.Form):
    """Upload a PNG signature image for a participant.

    The image is stored as a base64 data URI in the participant's
    `signature_data` field and embedded in the DOCX export. This is a
    graphical (non-qualified) signature, not an eIDAS qualified one.
    """

    signature_image = forms.ImageField(
        label=_("Signature image"),
        help_text=_("Upload a PNG or JPEG image of your signature (max 500 KB)."),
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": "image/png,image/jpeg",
        }),
    )

    def clean_signature_image(self):
        image = self.cleaned_data["signature_image"]
        max_size = 500 * 1024
        if image.size > max_size:
            raise forms.ValidationError(
                _("Signature image must be smaller than 500 KB."),
            )
        return image


class DecisionPromoteForm(forms.Form):
    """Promote a decision into a ComplianceActionPlan."""

    name = forms.CharField(
        label=_("Action plan name"),
        max_length=255,
        widget=forms.TextInput(attrs=_FORM_CONTROL),
    )
    priority = forms.ChoiceField(
        label=_("Priority"),
        choices=DecisionPriority.choices,
        widget=forms.Select(attrs=_FORM_SELECT),
    )
    target_date = forms.DateField(
        label=_("Target date"),
        widget=forms.DateInput(attrs=_FORM_DATE),
    )
    gap_description = forms.CharField(
        label=_("Gap description"),
        widget=forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
    )
    remediation_plan = forms.CharField(
        label=_("Remediation plan"),
        widget=forms.Textarea(attrs={**_FORM_CONTROL, "rows": 3}),
    )
    owner = forms.ModelChoiceField(
        label=_("Supervisor"),
        queryset=User.objects.filter(is_active=True).order_by(
            "last_name", "first_name", "email",
        ),
        widget=forms.Select(attrs=_FORM_SELECT),
    )

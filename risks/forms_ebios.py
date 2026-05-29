from django import forms
from django.utils.translation import gettext_lazy as _

from risks.constants import EbiosWorkshopStatus
from risks.models import (
    BaselineGap,
    EbiosWorkshopProgress,
    FearedEvent,
    SecurityBaseline,
    StudyFramework,
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


class SecurityBaselineForm(forms.ModelForm):
    """Workshop 1 root form. Edits the M2M selections and the DIC summary."""

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
            "business_values": forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
            "essential_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
            "support_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
            "dic_summary": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "baseline_references": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
        }


class FearedEventForm(forms.ModelForm):
    """Inline form for adding / editing a feared event under the W1 baseline."""

    class Meta:
        model = FearedEvent
        fields = [
            "essential_asset",
            "name",
            "description",
            "dic_criterion",
            "gravity_level",
            "gravity_justification",
        ]
        widgets = {
            "essential_asset": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "dic_criterion": forms.Select(attrs={"class": "form-select"}),
            "gravity_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "gravity_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class BaselineGapForm(forms.ModelForm):
    """Inline form for adding / editing a baseline gap under the W1 baseline."""

    class Meta:
        model = BaselineGap
        fields = [
            "reference_source",
            "linked_requirement",
            "description",
            "severity",
            "recommended_remediation",
            "status",
        ]
        widgets = {
            "reference_source": forms.TextInput(attrs={"class": "form-control"}),
            "linked_requirement": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "severity": forms.Select(attrs={"class": "form-select"}),
            "recommended_remediation": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class WorkshopRejectForm(forms.Form):
    """Form for rejecting a workshop with a mandatory reason."""

    rejection_reason = forms.CharField(
        label=_("Rejection reason"),
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control", "required": "required"}),
        required=True,
    )

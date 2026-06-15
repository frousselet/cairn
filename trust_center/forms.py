from django import forms
from django.utils.translation import gettext_lazy as _

from trust_center.models import (
    TrustCenterCertification,
    TrustCenterDocument,
    TrustCenterMeasure,
    TrustCenterSettings,
    TrustCenterSubprocessor,
)


class PublicDocumentRequestForm(forms.Form):
    """Public form a visitor fills to request access to a gated document."""

    requester_name = forms.CharField(label=_("Your name"), max_length=255)
    email = forms.EmailField(label=_("Email"))
    company = forms.CharField(label=_("Company"), max_length=255, required=False)
    reason = forms.CharField(
        label=_("Reason for access"),
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
    )
    nda_accepted = forms.BooleanField(
        label=_("I accept the non-disclosure agreement"), required=False
    )
    # Honeypot: bots fill hidden fields; humans never see it.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, document=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.document = document
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.HiddenInput):
                continue
            else:
                widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError(_("Your request could not be processed."))
        if self.document and self.document.requires_nda and not cleaned.get("nda_accepted"):
            self.add_error(
                "nda_accepted",
                _("You must accept the non-disclosure agreement to request this document."),
            )
        return cleaned


class _BootstrapModelForm(forms.ModelForm):
    """Apply Bootstrap classes to every widget without per-field boilerplate."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class TrustCenterSettingsForm(_BootstrapModelForm):
    css_file = forms.FileField(
        required=False,
        label=_("Upload a CSS file"),
        help_text=_("Optional. Replaces the custom CSS below with the uploaded file."),
    )

    class Meta:
        model = TrustCenterSettings
        fields = [
            "is_published",
            "headline",
            "intro",
            "contact_email",
            "show_compliance_percentages",
            "theme_accent",
            "custom_domain",
            "custom_css",
        ]
        widgets = {
            # intro keeps the default Jodit rich-text editor (no "no-jodit").
            "intro": forms.Textarea(attrs={"rows": 3}),
            "theme_accent": forms.TextInput(attrs={"type": "color"}),
            # custom_css must stay a raw textarea, not a rich-text editor.
            "custom_css": forms.Textarea(
                attrs={
                    "rows": 8,
                    "class": "form-control no-jodit",
                    "style": "font-family: var(--bs-font-monospace, monospace);",
                    "spellcheck": "false",
                }
            ),
        }

    def _post_clean(self):
        super()._post_clean()
        css_file = self.cleaned_data.get("css_file")
        if css_file:
            try:
                self.instance.custom_css = css_file.read().decode("utf-8", errors="ignore")
            except Exception:
                self.add_error("css_file", _("Could not read the uploaded file."))


class CertificationForm(_BootstrapModelForm):
    class Meta:
        model = TrustCenterCertification
        fields = [
            "framework",
            "public_label",
            "public_description",
            "show_percentage",
            "display_order",
        ]
        widgets = {"public_description": forms.Textarea(attrs={"rows": 3})}


class SubprocessorForm(_BootstrapModelForm):
    class Meta:
        model = TrustCenterSubprocessor
        fields = [
            "supplier",
            "public_name",
            "purpose",
            "public_country",
            "public_website",
            "display_order",
        ]


class MeasureForm(_BootstrapModelForm):
    class Meta:
        model = TrustCenterMeasure
        fields = ["title", "description", "icon", "category", "display_order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class DocumentForm(_BootstrapModelForm):
    upload = forms.FileField(
        required=False,
        label=_("Upload a file"),
        help_text=_("Provide either a source report or an uploaded file (not both)."),
    )

    class Meta:
        model = TrustCenterDocument
        fields = [
            "title",
            "description",
            "access",
            "requires_nda",
            "report",
            "display_order",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("report") and cleaned.get("upload"):
            raise forms.ValidationError(
                _("Provide either a source report or an uploaded file, not both.")
            )
        return cleaned

    def _post_clean(self):
        # Apply the upload to the instance before model validation so the
        # model's clean() sees the inline source it requires.
        upload = self.cleaned_data.get("upload") if hasattr(self, "cleaned_data") else None
        if upload:
            self.instance.file_content = upload.read()
            self.instance.file_name = upload.name
            self.instance.content_type = (
                getattr(upload, "content_type", "") or "application/octet-stream"
            )
            self.instance.report = None
        super()._post_clean()

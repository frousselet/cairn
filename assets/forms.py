import base64

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from context.constants import StakeholderCategory
from context.models import Scope, Site, Stakeholder
from context.widgets import ImageUploadWidget, ScopeTreeWidget
from core.modal_forms import Step, SteppedFormMixin
from helpers.image_utils import generate_image_variants

from .constants import CONTRACT_MAX_PDF_BYTES, CONTRACT_PDF_MAGIC
from .models import (
    AssetDependency,
    AssetGroup,
    AssetValuation,
    Contract,
    EssentialAsset,
    SiteAssetDependency,
    SiteSupplierDependency,
    Supplier,
    SupplierContact,
    SupplierDependency,
    SupplierRequirement,
    SupplierRequirementReview,
    SupplierType,
    SupplierTypeRequirement,
    SupportAsset,
)


def _file_to_data_uri(uploaded_file):
    """Convert an uploaded file to a base64 data URI string."""
    data = base64.b64encode(uploaded_file.read()).decode()
    return f"data:{uploaded_file.content_type};base64,{data}"


def _set_logo_with_variants(supplier, data_uri):
    """Set the logo field and generate 16/32/64 variants."""
    supplier.logo = data_uri
    variants = generate_image_variants(data_uri)
    supplier.logo_16 = variants[16]
    supplier.logo_32 = variants[32]
    supplier.logo_64 = variants[64]


FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}


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


class EssentialAssetBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "gem",
             ["name", ["type", "category"], ["owner", "custodian"], "description"]),
        Step(_("Security needs"), "shield-lock",
             [["confidentiality_level", "integrity_level", "availability_level"],
              "confidentiality_justification", "integrity_justification",
              "availability_justification"]),
        Step(_("Continuity & data"), "arrow-repeat",
             [["max_tolerable_downtime", "recovery_time_objective", "recovery_point_objective"],
              ["data_classification", "personal_data"], "regulatory_constraints"]),
        Step(_("Relations & status"), "diagram-3",
             ["related_activities", ["status", "review_date"], "scopes", "tags"]),
    ]

    class Meta:
        model = EssentialAsset
        fields = [
            "scopes", "name", "description",
            "type", "category", "owner", "custodian",
            "confidentiality_level", "integrity_level", "availability_level",
            "confidentiality_justification", "integrity_justification",
            "availability_justification",
            "max_tolerable_downtime", "recovery_time_objective",
            "recovery_point_objective",
            "data_classification", "personal_data",
            "regulatory_constraints",
            "related_activities", "status", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "custodian": forms.Select(attrs=SELECT_ATTRS),
            "confidentiality_level": forms.Select(attrs=SELECT_ATTRS),
            "integrity_level": forms.Select(attrs=SELECT_ATTRS),
            "availability_level": forms.Select(attrs=SELECT_ATTRS),
            "confidentiality_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2}),
            "integrity_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2}),
            "availability_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2}),
            "max_tolerable_downtime": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "recovery_time_objective": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "recovery_point_objective": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "data_classification": forms.Select(attrs=SELECT_ATTRS),
            "personal_data": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "regulatory_constraints": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "related_activities": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the essential asset."),
            "type": _("Kind of essential asset."),
            "category": _("Category of the asset."),
            "owner": _("Person accountable for the asset."),
            "custodian": _("Person operating the asset day to day."),
            "description": _("What the asset is and why it matters."),
            "confidentiality_level": _("Required confidentiality level."),
            "integrity_level": _("Required integrity level."),
            "availability_level": _("Required availability level."),
            "confidentiality_justification": _("Why this confidentiality level."),
            "integrity_justification": _("Why this integrity level."),
            "availability_justification": _("Why this availability level."),
            "max_tolerable_downtime": _("Maximum time the asset can stay unavailable (MTD)."),
            "recovery_time_objective": _("Target time to restore the asset (RTO)."),
            "recovery_point_objective": _("Maximum tolerable data loss (RPO)."),
            "data_classification": _("Sensitivity classification of the data."),
            "personal_data": _("Tick if the asset handles personal data."),
            "regulatory_constraints": _("Laws or regulations applying to the asset."),
            "related_activities": _("Business activities relying on this asset."),
            "status": _("Lifecycle state of the asset."),
            "review_date": _("Next date this asset should be reviewed."),
            "scopes": _("Organizational scopes this asset applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class EssentialAssetCreateForm(EssentialAssetBaseForm):
    """Essential asset creation modal form."""


class EssentialAssetUpdateForm(EssentialAssetBaseForm):
    """Essential asset edition modal form."""


class SupportAssetBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "hdd-stack",
             ["name", ["type", "category"], ["owner", "custodian"], "description"]),
        Step(_("Hardware & network"), "hdd-network",
             [["manufacturer", "model_name"], ["serial_number", "software_version"],
              ["ip_address", "hostname"], ["operating_system", "location"]]),
        Step(_("Lifecycle"), "calendar-event",
             [["acquisition_date", "end_of_life_date"],
              ["warranty_expiry_date", "contract_reference"],
              ["exposure_level", "environment"]]),
        Step(_("Relations & status"), "diagram-3",
             ["parent_asset", ["status", "review_date"], "scopes", "tags"]),
    ]

    class Meta:
        model = SupportAsset
        fields = [
            "scopes", "name", "description",
            "type", "category", "owner", "custodian",
            "location", "manufacturer", "model_name", "serial_number",
            "software_version", "ip_address", "hostname", "operating_system",
            "acquisition_date", "end_of_life_date", "warranty_expiry_date",
            "contract_reference",
            "exposure_level", "environment",
            "parent_asset", "status", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "custodian": forms.Select(attrs=SELECT_ATTRS),
            "location": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "manufacturer": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "model_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "serial_number": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "software_version": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "ip_address": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "hostname": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "operating_system": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "acquisition_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "end_of_life_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "warranty_expiry_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "contract_reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "exposure_level": forms.Select(attrs=SELECT_ATTRS),
            "environment": forms.Select(attrs=SELECT_ATTRS),
            "parent_asset": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the support asset."),
            "type": _("Kind of support asset."),
            "category": _("Category of the asset."),
            "owner": _("Person accountable for the asset."),
            "custodian": _("Person operating the asset day to day."),
            "description": _("What the asset is and why it matters."),
            "location": _("Physical location of the asset."),
            "manufacturer": _("Manufacturer or vendor."),
            "model_name": _("Model name or number."),
            "serial_number": _("Serial number."),
            "software_version": _("Software or firmware version."),
            "ip_address": _("IP address, if applicable."),
            "hostname": _("Network hostname."),
            "operating_system": _("Operating system."),
            "acquisition_date": _("Date the asset was acquired."),
            "end_of_life_date": _("Planned end-of-life date."),
            "warranty_expiry_date": _("Warranty expiry date."),
            "contract_reference": _("Related contract reference."),
            "exposure_level": _("How exposed the asset is to threats."),
            "environment": _("Environment (production, test, etc.)."),
            "parent_asset": _("Parent asset, if this is a component."),
            "status": _("Lifecycle state of the asset."),
            "review_date": _("Next date this asset should be reviewed."),
            "scopes": _("Organizational scopes this asset applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class SupportAssetCreateForm(SupportAssetBaseForm):
    """Support asset creation modal form."""


class SupportAssetUpdateForm(SupportAssetBaseForm):
    """Support asset edition modal form."""


class AssetDependencyForm(forms.ModelForm):
    class Meta:
        model = AssetDependency
        fields = [
            "essential_asset", "support_asset",
            "dependency_type", "criticality", "description",
            "redundancy_level",
        ]
        widgets = {
            "essential_asset": forms.Select(attrs=SELECT_ATTRS),
            "support_asset": forms.Select(attrs=SELECT_ATTRS),
            "dependency_type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "redundancy_level": forms.Select(attrs=SELECT_ATTRS),
        }


class AssetGroupBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "collection",
             ["name", ["type", "owner"], "description"]),
        Step(_("Scope & status"), "diagram-3", ["scopes", "status", "tags"]),
    ]

    class Meta:
        model = AssetGroup
        fields = [
            "scopes", "name", "description", "type", "owner", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the asset group."),
            "type": _("Kind of asset group."),
            "owner": _("Person accountable for the group."),
            "description": _("What the group covers."),
            "scopes": _("Organizational scopes this group applies to."),
            "status": _("Lifecycle state of the group."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class AssetGroupCreateForm(AssetGroupBaseForm):
    """Asset group creation modal form."""


class AssetGroupUpdateForm(AssetGroupBaseForm):
    """Asset group edition modal form."""


class SupplierBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    logo = forms.CharField(label=_("Logo"), required=False, widget=ImageUploadWidget())

    steps = [
        Step(_("Identity"), "truck",
             [[("logo", "auto"), "name"], ["type", "criticality"], "owner", "description"]),
        Step(_("Coordinates"), "geo-alt",
             ["website", "country", "address"]),
        Step(_("Scope & status"), "diagram-3", ["scopes", "status", "tags", "notes"]),
    ]

    class Meta:
        model = Supplier
        fields = [
            "scopes", "name", "description",
            "type", "criticality", "owner",
            "website", "address", "country", "latitude", "longitude",
            "status", "notes", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "website": forms.URLInput(attrs=FORM_WIDGET_ATTRS),
            "address": forms.TextInput(attrs={
                **FORM_WIDGET_ATTRS,
                "data-address-autocomplete": "photon",
                "autocomplete": "off",
                "placeholder": _("Start typing an address..."),
            }),
            "country": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "notes": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "logo": "",
            "name": _("Name of the supplier."),
            "type": _("Kind of supplier."),
            "criticality": _("How critical this supplier is."),
            "owner": _("Person accountable for the relationship."),
            "description": _("What the supplier provides."),
            "website": _("Supplier website."),
            "country": _("Country where the supplier operates."),
            "address": _("Postal address of the supplier."),
            "notes": _("Free-form notes about the supplier."),
            "status": _("Lifecycle state of the supplier."),
            "scopes": _("Organizational scopes this supplier applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and getattr(self.instance, "logo", ""):
            self.fields["logo"].initial = self.instance.logo

    def save(self, commit=True):
        supplier = super().save(commit=False)
        data_uri = self.cleaned_data.get("logo")
        if data_uri:
            _set_logo_with_variants(supplier, data_uri)
        elif self.instance.pk:
            supplier.logo = ""
            supplier.logo_16 = ""
            supplier.logo_32 = ""
            supplier.logo_64 = ""
        if commit:
            supplier.save()
            self.save_m2m()
        return supplier


class SupplierCreateForm(SupplierBaseForm):
    """Supplier creation modal form."""


class SupplierUpdateForm(SupplierBaseForm):
    """Supplier edition modal form."""


class SupplierContactForm(SteppedFormMixin, forms.ModelForm):
    """Create / edit a contact person attached to a supplier."""

    steps = [
        Step(_("Identity"), "person-badge",
             ["name", ["profession", "service"], "role"]),
        Step(_("Contact details"), "envelope-at",
             [["email", "phone"]]),
    ]

    class Meta:
        model = SupplierContact
        fields = ["name", "profession", "service", "email", "phone", "role"]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "profession": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "service": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "email": forms.EmailInput(attrs=FORM_WIDGET_ATTRS),
            "phone": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "role": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
        }
        help_texts = {
            "name": _("Full name of the contact."),
            "profession": _("Job title or profession."),
            "service": _("Department or service the contact belongs to."),
            "email": _("Contact email address."),
            "phone": _("Contact phone number."),
            "role": _("Role in this relationship (e.g. Primary, Billing, Technical)."),
        }


class SupplierTypeForm(forms.ModelForm):
    class Meta:
        model = SupplierType
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }


class SupplierTypeRequirementForm(forms.ModelForm):
    class Meta:
        model = SupplierTypeRequirement
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2}),
        }


SupplierTypeRequirementFormSet = inlineformset_factory(
    SupplierType,
    SupplierTypeRequirement,
    form=SupplierTypeRequirementForm,
    extra=1,
    can_delete=True,
)


class SupplierRequirementForm(forms.ModelForm):
    class Meta:
        model = SupplierRequirement
        fields = [
            "requirement", "title", "description",
            "compliance_status", "evidence", "due_date",
        ]
        widgets = {
            "requirement": forms.Select(attrs=SELECT_ATTRS),
            "title": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "compliance_status": forms.Select(attrs=SELECT_ATTRS),
            "evidence": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "due_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }


class SupplierRequirementReviewForm(SteppedFormMixin, forms.ModelForm):
    evidence_file = forms.FileField(
        label=_("Supporting evidence (file)"),
        required=False,
        widget=forms.ClearableFileInput(attrs=FORM_WIDGET_ATTRS),
        help_text=_("Upload a supporting document (certificate, report, etc.)."),
    )

    steps = [
        Step(_("Assessment"), "clipboard-check", [["review_date", "result"]]),
        Step(_("Evidence"), "paperclip", ["comment", "evidence_file"]),
    ]

    class Meta:
        model = SupplierRequirementReview
        fields = ["review_date", "result", "comment"]
        widgets = {
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "result": forms.Select(attrs=SELECT_ATTRS),
            "comment": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
        }
        help_texts = {
            "comment": _("Written justification for the compliance assessment (rich text)."),
        }

    def save(self, commit=True):
        review = super().save(commit=False)
        if self.files.get("evidence_file"):
            f = self.files["evidence_file"]
            review.evidence_file = _file_to_data_uri(f)
            review.evidence_filename = f.name
        if commit:
            review.save()
        return review


class SupplierDependencyForm(forms.ModelForm):
    class Meta:
        model = SupplierDependency
        fields = [
            "support_asset", "supplier",
            "dependency_type", "criticality", "description",
            "redundancy_level",
        ]
        widgets = {
            "support_asset": forms.Select(attrs=SELECT_ATTRS),
            "supplier": forms.Select(attrs=SELECT_ATTRS),
            "dependency_type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "redundancy_level": forms.Select(attrs=SELECT_ATTRS),
        }


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


class SiteBaseForm(SteppedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "geo-alt",
             ["name", "type", "parent_site", "description"]),
        Step(_("Location & tags"), "pin-map", ["address", "tags"]),
    ]

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
        help_texts = {
            "name": _("Name of the site."),
            "type": _("Kind of site."),
            "parent_site": _("Parent site, if this is a sub-site."),
            "description": _("What this site is."),
            "address": _("Postal address of the site."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Site.objects.exclude(workflow_state="archived")
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        field = self.fields["parent_site"]
        field.queryset = qs
        field.choices = [("", field.empty_label or "---------")] + _site_tree_choices(qs)


class SiteCreateForm(SiteBaseForm):
    """Site creation modal form."""


class SiteUpdateForm(SiteBaseForm):
    """Site edition modal form."""


class SiteAssetDependencyForm(forms.ModelForm):
    class Meta:
        model = SiteAssetDependency
        fields = [
            "support_asset", "site",
            "dependency_type", "criticality", "description",
            "redundancy_level",
        ]
        widgets = {
            "support_asset": forms.Select(attrs=SELECT_ATTRS),
            "site": forms.Select(attrs=SELECT_ATTRS),
            "dependency_type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "redundancy_level": forms.Select(attrs=SELECT_ATTRS),
        }


class SiteSupplierDependencyForm(forms.ModelForm):
    class Meta:
        model = SiteSupplierDependency
        fields = [
            "site", "supplier",
            "dependency_type", "criticality", "description",
            "redundancy_level",
        ]
        widgets = {
            "site": forms.Select(attrs=SELECT_ATTRS),
            "supplier": forms.Select(attrs=SELECT_ATTRS),
            "dependency_type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "redundancy_level": forms.Select(attrs=SELECT_ATTRS),
        }


class AssetValuationForm(forms.ModelForm):
    class Meta:
        model = AssetValuation
        fields = [
            "evaluation_date",
            "confidentiality_level", "integrity_level", "availability_level",
            "justification", "context",
        ]
        widgets = {
            "evaluation_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "confidentiality_level": forms.Select(attrs=SELECT_ATTRS),
            "integrity_level": forms.Select(attrs=SELECT_ATTRS),
            "availability_level": forms.Select(attrs=SELECT_ATTRS),
            "justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "context": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }


class ContractBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    upload = forms.FileField(
        label=_("PDF document"),
        required=False,
        widget=forms.ClearableFileInput(
            attrs={**FORM_WIDGET_ATTRS, "accept": "application/pdf,.pdf"}
        ),
        help_text=_("Attach the contract as a PDF file (25 MB max)."),
    )

    steps = [
        Step(_("Identity"), "file-earmark-text",
             ["label", ["status", "parent"]]),
        Step(_("Parties"), "people",
             ["suppliers", "clients"]),
        Step(_("Terms"), "cash-coin",
             [["start_date", "end_date"], ["amount", "currency"]]),
        Step(_("Document"), "file-earmark-pdf",
             ["upload"]),
        Step(_("Scope & filing"), "diagram-3",
             ["scopes", "notes", "tags"]),
    ]

    class Meta:
        model = Contract
        fields = [
            "scopes", "label", "status", "parent",
            "suppliers", "clients",
            "start_date", "end_date", "amount", "currency",
            "notes", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "label": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "parent": forms.Select(attrs=SELECT_ATTRS),
            "suppliers": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "clients": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "start_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "amount": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "currency": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "maxlength": 3}),
            "notes": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "label": _("Short title of the contract."),
            "status": _("Lifecycle state of the contract."),
            "parent": _("If this contract is an amendment, the contract it amends."),
            "suppliers": _("Supplier parties to the contract."),
            "clients": _("Client (customer) parties to the contract."),
            "start_date": _("Date the contract takes effect."),
            "end_date": _("Date the contract ends."),
            "amount": _("Contract value."),
            "currency": _("ISO 4217 currency code (e.g. EUR)."),
            "notes": _("Free-form notes about the contract."),
            "scopes": _("Organizational scopes this contract applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Clients are customer stakeholders.
        self.fields["clients"].queryset = Stakeholder.objects.filter(
            category=StakeholderCategory.CUSTOMERS
        )
        # A contract can only amend a top-level contract, never itself.
        parent_qs = Contract.objects.filter(parent__isnull=True)
        if self.instance and self.instance.pk:
            parent_qs = parent_qs.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parent_qs

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("scopes"):
            self.add_error(
                "scopes", _("A contract must be attached to at least one scope.")
            )
        upload = cleaned.get("upload")
        if upload:
            name = (upload.name or "").lower()
            if not name.endswith(".pdf"):
                self.add_error("upload", _("Only PDF files are accepted."))
            elif upload.size and upload.size > CONTRACT_MAX_PDF_BYTES:
                self.add_error(
                    "upload",
                    _("The PDF exceeds the maximum allowed size of 25 MB."),
                )
            else:
                header = upload.read(len(CONTRACT_PDF_MAGIC))
                upload.seek(0)
                if header != CONTRACT_PDF_MAGIC:
                    self.add_error(
                        "upload", _("The uploaded file is not a valid PDF.")
                    )
        return cleaned

    def _post_clean(self):
        # Store the uploaded PDF inline on the instance before model validation.
        upload = self.cleaned_data.get("upload") if hasattr(self, "cleaned_data") else None
        if upload and "upload" not in self.errors:
            self.instance.file_content = upload.read()
            self.instance.file_name = upload.name
            self.instance.content_type = (
                getattr(upload, "content_type", "") or "application/pdf"
            )
        super()._post_clean()


class ContractCreateForm(ContractBaseForm):
    """Contract creation modal form."""


class ContractUpdateForm(ContractBaseForm):
    """Contract edition modal form."""

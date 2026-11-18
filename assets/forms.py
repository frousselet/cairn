# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import base64

from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from compliance.models import Framework
from context.constants import StakeholderCategory
from context.models import Scope, Site, Stakeholder
from context.widgets import ImageUploadWidget, ScopeTreeWidget
from core.modal_forms import CreationFormMixin, LabelledRowsFormSet, ScopedFormMixin, Step, SteppedFormMixin
from helpers.image_utils import generate_image_variants

from .constants import (
    CERTIFICATE_MAX_PDF_BYTES,
    CERTIFICATE_PDF_MAGIC,
    CONTRACT_MAX_PDF_BYTES,
    CONTRACT_PDF_MAGIC,
    DICLevel,
    SupplierStatus,
    essential_asset_category_choices,
    essential_asset_type_for,
    support_asset_category_choices,
    support_asset_type_for,
)
from .models import (
    AssetDependency,
    AssetGroup,
    AssetValuation,
    Certificate,
    Contract,
    EssentialAsset,
    SiteAssetDependency,
    SiteSupplierDependency,
    Supplier,
    SupplierContact,
    SupplierDependency,
    SupplierRequirement,
    SupplierRequirementReview,
    SupplierSubprocessor,
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




# A plain two-line box : a justification is a sentence, not a formatted text.
_JUSTIFICATION = forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2, "class": "form-control no-richtext"})
_LEVEL_FIELDS = ("confidentiality_level", "integrity_level", "availability_level")


def _pick_among_active_people(form, names):
    """People are picked among the active accounts; whoever is already set stays."""
    from django.contrib.auth import get_user_model

    users = get_user_model().objects
    for name in names:
        if name not in form.fields:
            continue
        current = getattr(form.instance, f"{name}_id", None)
        form.fields[name].queryset = (
            users.filter(Q(is_active=True) | Q(pk=current)) if current else users.filter(is_active=True)
        ).order_by("first_name", "last_name", "email")


class EssentialAssetBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the asset page : a step opens on its own from its
    # card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "gem",
             ["name", "category", "description", "scopes", "tags"],
             key="identity"),
        Step(_("People"), "people",
             [["owner", "custodian"]],
             key="people"),
        Step(_("Security needs"), "shield-lock",
             [[("confidentiality_level", 4), "confidentiality_justification"],
              [("integrity_level", 4), "integrity_justification"],
              [("availability_level", 4), "availability_justification"]],
             key="security",
             intro=_("For each of the three questions, pick how much harm it would do, from negligible to critical. A few words of justification make the choice defensible later.")),
        Step(_("Business continuity"), "clock-history",
             ["max_tolerable_downtime", "recovery_time_objective", "recovery_point_objective"],
             key="continuity",
             intro=_('How long the business can do without this asset. A duration in plain words is enough : "4 hours", "2 days".')),
        Step(_("Data and regulation"), "lock",
             [["data_classification", "personal_data"], "regulatory_constraints"],
             key="data"),
        Step(_("Activities and review"), "diagram-3",
             ["related_activities", "review_date"],
             key="relations"),
    ]

    class Meta:
        model = EssentialAsset
        # ``type`` is not asked : the category names it (see ``clean``).
        fields = [
            "scopes", "name", "description",
            "category", "owner", "custodian",
            "confidentiality_level", "integrity_level", "availability_level",
            "confidentiality_justification", "integrity_justification",
            "availability_justification",
            "max_tolerable_downtime", "recovery_time_objective",
            "recovery_point_objective",
            "data_classification", "personal_data",
            "regulatory_constraints",
            "related_activities", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "custodian": forms.Select(attrs=SELECT_ATTRS),
            "confidentiality_level": forms.Select(attrs=SELECT_ATTRS),
            "integrity_level": forms.Select(attrs=SELECT_ATTRS),
            "availability_level": forms.Select(attrs=SELECT_ATTRS),
            "confidentiality_justification": _JUSTIFICATION,
            "integrity_justification": _JUSTIFICATION,
            "availability_justification": _JUSTIFICATION,
            "max_tolerable_downtime": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "recovery_time_objective": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "recovery_point_objective": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "data_classification": forms.Select(attrs=SELECT_ATTRS),
            "personal_data": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "regulatory_constraints": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "related_activities": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('For example "Customer file", "Payroll" or "Online ordering".'),
            "category": _("An activity the business runs on, or an information it holds."),
            "owner": _("The person who answers for this asset and decides what it needs."),
            "custodian": _("The person or team running it day to day, when it is not the owner."),
            "description": _("What it is used for, and what would be lost without it."),
            "scopes": _("Without a scope, every user sees this asset."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
            "confidentiality_level": _("What if it were disclosed to people who should not see it ?"),
            "integrity_level": _("What if it were wrong, or altered without anyone noticing ?"),
            "availability_level": _("What if it were out of reach when it is needed ?"),
            "max_tolerable_downtime": _("Beyond this, the business is in danger. Always longer than the recovery time objective."),
            "recovery_time_objective": _('How fast you aim to have it back, for example "4 hours".'),
            "recovery_point_objective": _('How much recent data you can afford to lose, for example "1 hour of entries".'),
            "data_classification": _("How widely it may circulate, from public to secret."),
            "personal_data": _("Tick when it holds data about identifiable people (customers, employees) : the GDPR then applies."),
            "regulatory_constraints": _("Laws, regulations or contracts that apply to it, for example the GDPR or a client's security clause."),
            "related_activities": _("The business activities that cannot run without it."),
            "review_date": _("When to check this record is still right. Once a year is usual."),
        }

    def __init__(self, *args, user=None, **kwargs):
        self._user = user
        super().__init__(*args, user=user, **kwargs)
        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        if "category" in self.fields:
            self.fields["category"].choices = [
                ("", pgettext_lazy("empty select option", "Choose…")),
                *essential_asset_category_choices(),
            ]
        # An empty level reads "Not assessed" : it is a state of the record,
        # not a missing choice.
        for name in _LEVEL_FIELDS:
            if name in self.fields:
                self.fields[name].choices = [("", _("Not assessed")), *DICLevel.choices]
        _pick_among_active_people(self, ("owner", "custodian"))
        self._levels_before = tuple(getattr(self.instance, name) for name in _LEVEL_FIELDS)

    def clean(self):
        cleaned = super().clean()
        # RS-01 : the category names its type, so the two cannot disagree.
        category = cleaned.get("category")
        if category:
            self.instance.type = essential_asset_type_for(category)
        return cleaned

    def save(self, commit=True):
        asset = super().save(commit=commit)
        if commit:
            self._record_valuation(asset)
        return asset

    def _record_valuation(self, asset):
        """RV-06 : setting or changing the security needs is an assessment.

        It is recorded with its author and its date, so the history of the
        valuations shows who decided what. Nothing is recorded while a level
        is still missing, or when the three are unchanged.
        """
        levels = tuple(getattr(asset, name) for name in _LEVEL_FIELDS)
        if None in levels or levels == self._levels_before or self._user is None:
            return
        reasons = [
            f"{self._meta.model._meta.get_field(name).verbose_name} : {text}"
            for name, text in (
                ("confidentiality_level", asset.confidentiality_justification),
                ("integrity_level", asset.integrity_justification),
                ("availability_level", asset.availability_justification),
            )
            if text.strip()
        ]
        AssetValuation.objects.create(
            essential_asset=asset,
            evaluation_date=timezone.localdate(),
            confidentiality_level=levels[0],
            integrity_level=levels[1],
            availability_level=levels[2],
            evaluated_by=self._user,
            justification="\n".join(reasons),
        )
        self._levels_before = levels


class EssentialAssetCreateForm(CreationFormMixin, EssentialAssetBaseForm):
    """Essential asset creation : what it is and who answers for it, on one screen.

    The security needs, the continuity figures and the rest are filled in on
    the asset page, which lists what is missing. With one scope only the
    question is not asked, and whoever registers the asset answers for it
    unless they say otherwise (``CreationFormMixin``).
    """

    steps = [
        Step(_("Identity"), "gem", ["name", ["category", "owner"], "scopes", "description"]),
    ]

    class Meta(EssentialAssetBaseForm.Meta):
        fields = ["scopes", "name", "description", "category", "owner"]


class EssentialAssetUpdateForm(EssentialAssetBaseForm):
    """Essential asset edition : the whole form, or one of its sections."""


class SupportAssetBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    # One step per card of the asset page : a step opens on its own from its
    # card (``?section=<key>``), the whole form from the page header.
    steps = [
        Step(_("Identity"), "hdd-stack",
             ["name", "category", "description", "scopes", "tags"],
             key="identity"),
        Step(_("People"), "people",
             [["owner", "custodian"]],
             key="people"),
        Step(_("Technical specifications"), "cpu",
             [["manufacturer", "model_name"], ["serial_number", "software_version"],
              ["ip_address", "hostname"], ["operating_system", "location"]],
             key="technical",
             intro=_("Fill in what applies : a server has a serial number, an online service has none.")),
        Step(_("Environment and exposure"), "hdd-network",
             [["environment", "exposure_level"]],
             key="exposure",
             intro=_("Two facts that weigh on its risks : where it runs, and who can reach it.")),
        Step(_("Dates and contract"), "calendar-event",
             [["acquisition_date", "end_of_life_date"],
              ["warranty_expiry_date", "contract_reference"], "review_date"],
             key="dates"),
        Step(_("Relations"), "diagram-3",
             ["parent_asset"],
             key="relations"),
    ]

    class Meta:
        model = SupportAsset
        # ``type`` is not asked : the category names it (see ``clean``).
        fields = [
            "scopes", "name", "description",
            "category", "owner", "custodian",
            "location", "manufacturer", "model_name", "serial_number",
            "software_version", "ip_address", "hostname", "operating_system",
            "acquisition_date", "end_of_life_date", "warranty_expiry_date",
            "contract_reference",
            "exposure_level", "environment",
            "parent_asset", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
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
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        # A helper says what the label does not : an example, a consequence,
        # how to answer. A field whose label says it all carries none.
        help_texts = {
            "name": _('For example "Payroll server", "Customer relationship software" or "Head office network".'),
            "category": _("The kind of thing it is. Its type (hardware, software, service...) follows from it."),
            "owner": _("The person who answers for this asset and decides what it needs."),
            "custodian": _("The person or team running it day to day, when it is not the owner."),
            "description": _('What it is used for and by whom, for example "Runs the payroll of the 120 employees".'),
            "scopes": _("Without a scope, every user sees this asset."),
            "tags": _('Free words to find and group records, for example "ISO 27001".'),
            "location": _('Where to find it, for example "Rack B2, Lyon computer room".'),
            "environment": _("Production is what the business runs on; the others serve to build and to test."),
            "exposure_level": _("Who can reach it : people inside only, partners, or anyone on the internet."),
            "end_of_life_date": _("After this date its maker no longer repairs it : the asset is then flagged."),
            "contract_reference": _("The contract that covers it : maintenance, licence or hosting."),
            "parent_asset": _("The asset this one is a part of : the server a database runs on, for example."),
            "review_date": _("When to check this record is still right. Once a year is usual."),
        }

    def __init__(self, *args, user=None, **kwargs):
        self._user = user
        super().__init__(*args, user=user, **kwargs)
        # A form opened on one section, or the creation form, carries a part
        # of these fields only : each is prepared when it is there.
        if "category" in self.fields:
            self.fields["category"].choices = [
                ("", pgettext_lazy("empty select option", "Choose…")),
                *support_asset_category_choices(),
            ]
        _pick_among_active_people(self, ("owner", "custodian"))

    def clean(self):
        cleaned = super().clean()
        # RS-02 : the category names its type, so the two cannot disagree.
        category = cleaned.get("category")
        if category:
            self.instance.type = support_asset_type_for(category)
        return cleaned


class SupportAssetCreateForm(CreationFormMixin, SupportAssetBaseForm):
    """Support asset creation : what it is and who answers for it, on one screen.

    Its specifications, its dates and what it is exposed to are filled in on
    the asset page, which lists what would make the record useful.
    """

    steps = [
        Step(_("Identity"), "hdd-stack", ["name", ["category", "owner"], "scopes", "description"]),
    ]

    class Meta(SupportAssetBaseForm.Meta):
        fields = ["scopes", "name", "description", "category", "owner"]


class SupportAssetUpdateForm(SupportAssetBaseForm):
    """Support asset edition : the whole form, or one of its sections."""


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
             [[("logo", "auto"), "name"], ["type", "criticality"], ["owner", "parent_company"], "description"]),
        Step(_("Coordinates"), "geo-alt",
             ["website", "country", "address"]),
        Step(_("Scope & status"), "diagram-3", ["scopes", "status", "tags", "notes"]),
    ]

    class Meta:
        model = Supplier
        fields = [
            "scopes", "name", "description",
            "type", "criticality", "owner", "parent_company",
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
            "parent_company": forms.Select(attrs=SELECT_ATTRS),
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
            "parent_company": _("Parent company this supplier is a subsidiary of."),
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
        # A supplier cannot be its own parent company.
        parent_qs = Supplier.objects.all()
        if self.instance.pk:
            parent_qs = parent_qs.exclude(pk=self.instance.pk)
        self.fields["parent_company"].queryset = parent_qs

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


class SupplierSubprocessorForm(SteppedFormMixin, forms.ModelForm):
    """Create / edit a sub-processor (sous-délégataire) engaged by a supplier."""

    steps = [
        Step(_("Sub-processor"), "diagram-3",
             ["subprocessor", "purpose"]),
        Step(_("Engagement"), "shield-check",
             [["criticality", "status"], ["start_date", "end_date"], "description"]),
    ]

    class Meta:
        model = SupplierSubprocessor
        fields = [
            "subprocessor", "purpose", "criticality", "status",
            "start_date", "end_date", "description",
        ]
        widgets = {
            "subprocessor": forms.Select(attrs=SELECT_ATTRS),
            "purpose": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "start_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
        help_texts = {
            "subprocessor": _("Supplier engaged as a sub-processor."),
            "purpose": _("Nature of the service delegated to the sub-processor."),
            "criticality": _("How critical this sub-processing engagement is."),
            "status": _("State of the sub-processing engagement."),
            "start_date": _("Date the engagement started."),
            "end_date": _("Date the engagement ends."),
            "description": _("Additional context about the sub-processing."),
        }

    def __init__(self, *args, supplier=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.supplier = supplier or getattr(self.instance, "supplier", None)
        # A supplier cannot be listed as its own sub-processor.
        qs = Supplier.objects.exclude(status=SupplierStatus.ARCHIVED)
        if self.supplier is not None:
            qs = qs.exclude(pk=self.supplier.pk)
        self.fields["subprocessor"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        subprocessor = cleaned.get("subprocessor")
        supplier = self.supplier or getattr(self.instance, "supplier", None)
        if subprocessor and supplier and subprocessor.pk == supplier.pk:
            self.add_error(
                "subprocessor",
                _("A supplier cannot be its own sub-processor."),
            )
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date",
                _("The end date cannot be earlier than the start date."),
            )
        return cleaned


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
    formset=LabelledRowsFormSet,
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
             ["label", "parent", "supersedes"]),
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
            "scopes", "label", "parent", "supersedes",
            "suppliers", "clients",
            "start_date", "end_date", "amount", "currency",
            "notes", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "label": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "parent": forms.Select(attrs=SELECT_ATTRS),
            "supersedes": forms.Select(attrs=SELECT_ATTRS),
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
            "parent": _("If this contract is an amendment, the contract it amends."),
            "supersedes": _("The contract or amendment this one cancels and replaces."),
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
        # "Cancels and replaces" can target any other contract or amendment.
        supersedes_qs = Contract.objects.all()
        if self.instance and self.instance.pk:
            supersedes_qs = supersedes_qs.exclude(pk=self.instance.pk)
        self.fields["supersedes"].queryset = supersedes_qs

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


class CertificateBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    upload = forms.FileField(
        label=_("PDF document"),
        required=False,
        widget=forms.ClearableFileInput(
            attrs={**FORM_WIDGET_ATTRS, "accept": "application/pdf,.pdf"}
        ),
        help_text=_("Attach the certificate as a PDF file (25 MB max)."),
    )

    steps = [
        Step(_("Identity"), "patch-check",
             ["label", "framework", "supersedes"]),
        Step(_("Issuance"), "award",
             ["issuer", "certificate_number", ["issue_date", "expiry_date"]]),
        Step(_("Certified scope"), "diagram-3",
             ["scope_statement", "sites"]),
        Step(_("Document"), "file-earmark-pdf",
             ["upload"]),
        Step(_("Scope & filing"), "folder",
             ["scopes", "notes", "tags"]),
    ]

    class Meta:
        model = Certificate
        fields = [
            "scopes", "label", "framework", "supersedes",
            "issuer", "certificate_number", "issue_date", "expiry_date",
            "scope_statement", "sites",
            "notes", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "label": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "framework": forms.Select(attrs=SELECT_ATTRS),
            "supersedes": forms.Select(attrs=SELECT_ATTRS),
            "issuer": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "certificate_number": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "issue_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "expiry_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "scope_statement": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "sites": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "notes": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "label": _("Short title of the certificate."),
            "framework": _("The framework (référentiel) this certificate attests compliance to."),
            "supersedes": _("The previous certificate this one renews and replaces."),
            "issuer": _("Certification body that issued the certificate (e.g. AFNOR, BSI)."),
            "certificate_number": _("Official certificate number from the certification body."),
            "issue_date": _("Date the certificate was issued."),
            "expiry_date": _("Date the certificate expires."),
            "scope_statement": _("Perimeter covered by the certificate (free text)."),
            "sites": _("Sites covered by the certified perimeter."),
            "notes": _("Free-form notes about the certificate."),
            "scopes": _("Organizational scopes this certificate applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A certificate always attests compliance to a framework (référentiel).
        self.fields["framework"].required = True
        self.fields["framework"].queryset = Framework.objects.order_by(
            "short_name", "name"
        )
        # A certificate can only renew another certificate, never itself.
        supersedes_qs = Certificate.objects.all()
        if self.instance and self.instance.pk:
            supersedes_qs = supersedes_qs.exclude(pk=self.instance.pk)
        self.fields["supersedes"].queryset = supersedes_qs

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("scopes"):
            self.add_error(
                "scopes", _("A certificate must be attached to at least one scope.")
            )
        issue_date = cleaned.get("issue_date")
        expiry_date = cleaned.get("expiry_date")
        if issue_date and expiry_date and expiry_date < issue_date:
            self.add_error(
                "expiry_date",
                _("The expiry date cannot be earlier than the issue date."),
            )
        upload = cleaned.get("upload")
        if upload:
            name = (upload.name or "").lower()
            if not name.endswith(".pdf"):
                self.add_error("upload", _("Only PDF files are accepted."))
            elif upload.size and upload.size > CERTIFICATE_MAX_PDF_BYTES:
                self.add_error(
                    "upload",
                    _("The PDF exceeds the maximum allowed size of 25 MB."),
                )
            else:
                header = upload.read(len(CERTIFICATE_PDF_MAGIC))
                upload.seek(0)
                if header != CERTIFICATE_PDF_MAGIC:
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


class CertificateCreateForm(CertificateBaseForm):
    """Certificate creation modal form."""


class CertificateUpdateForm(CertificateBaseForm):
    """Certificate edition modal form."""

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The usability standard, held by tests (``docs/sdk/usability-standard.md``).

A screen that follows the standard is listed here, and stays held to it :
adding a seventh field to a listed creation form, or a helper that says its
label again, fails. The list grows module by module; what is not listed yet
is not claimed to follow the standard.
"""

import pytest
from django.urls import reverse
from django.utils import translation

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from core.usability import (
    MAX_CREATION_FIELDS,
    form_findings,
    help_restates_label,
    is_bare_acronym,
)

pytestmark = pytest.mark.django_db


def _forms():
    """The forms that follow the standard : (form class, is it a creation form)."""
    from assets.forms import (
        AssetGroupCreateForm,
        AssetGroupUpdateForm,
        CertificateCreateForm,
        CertificateUpdateForm,
        ContractCreateForm,
        ContractUpdateForm,
        EssentialAssetCreateForm,
        EssentialAssetUpdateForm,
        SiteCreateForm,
        SiteUpdateForm,
        SupplierContactForm,
        SupplierSubprocessorCreateForm,
        SupplierSubprocessorForm,
        SupplierCreateForm,
        SupplierUpdateForm,
        SupportAssetCreateForm,
        SupportAssetUpdateForm,
    )
    from compliance.forms import (
        ComplianceActionPlanCreateForm,
        ComplianceActionPlanUpdateForm,
        ComplianceAssessmentCreateForm,
        ComplianceAssessmentUpdateForm,
        FindingCreateForm,
        FindingRegisterCreateForm,
        FindingRegisterUpdateForm,
        FrameworkCreateForm,
        FrameworkUpdateForm,
        RequirementCreateForm,
        RequirementUpdateForm,
    )
    from context.forms import (
        IssueCreateForm,
        IssueUpdateForm,
        ObjectiveCreateForm,
        ObjectiveUpdateForm,
        ScopeCreateForm,
        ScopeUpdateForm,
        StakeholderCreateForm,
        StakeholderExpectationForm,
        StakeholderUpdateForm,
    )
    from risks.forms import (
        ISO27005RiskCreateForm,
        ISO27005RiskUpdateForm,
        RiskAcceptanceCreateForm,
        RiskAcceptanceUpdateForm,
        RiskAssessmentCreateForm,
        RiskAssessmentUpdateForm,
        RiskCreateForm,
        RiskTreatmentPlanCreateForm,
        RiskTreatmentPlanUpdateForm,
        RiskUpdateForm,
        ThreatCreateForm,
        ThreatUpdateForm,
        TreatmentActionCreateForm,
        VulnerabilityCreateForm,
        VulnerabilityUpdateForm,
    )

    return [
        (ScopeCreateForm, True),
        (ScopeUpdateForm, False),
        (IssueCreateForm, True),
        (IssueUpdateForm, False),
        (StakeholderCreateForm, True),
        (StakeholderUpdateForm, False),
        # A row of an interested party, added and edited from its page.
        (StakeholderExpectationForm, True),
        (ObjectiveCreateForm, True),
        (ObjectiveUpdateForm, False),
        (EssentialAssetCreateForm, True),
        (EssentialAssetUpdateForm, False),
        (SupportAssetCreateForm, True),
        (SupportAssetUpdateForm, False),
        (SupplierCreateForm, True),
        (SupplierUpdateForm, False),
        (AssetGroupCreateForm, True),
        (AssetGroupUpdateForm, False),
        (SiteCreateForm, True),
        (SiteUpdateForm, False),
        (ContractCreateForm, True),
        (ContractUpdateForm, False),
        (CertificateCreateForm, True),
        (CertificateUpdateForm, False),
        (FrameworkCreateForm, True),
        (FrameworkUpdateForm, False),
        (ComplianceActionPlanCreateForm, True),
        (ComplianceActionPlanUpdateForm, False),
        (ComplianceAssessmentCreateForm, True),
        (ComplianceAssessmentUpdateForm, False),
        (RequirementCreateForm, True),
        (RequirementUpdateForm, False),
        # A finding is noted in its audit on one screen; a nonconformity is
        # raised from its register and completed on its page.
        (FindingCreateForm, True),
        (FindingRegisterCreateForm, True),
        (FindingRegisterUpdateForm, False),
        (RiskAssessmentCreateForm, True),
        (RiskAssessmentUpdateForm, False),
        # A risk is opened from its assessment (its page is tested in
        # risks/tests/test_risk_completion.py : it has no register dialog).
        (RiskCreateForm, True),
        (RiskUpdateForm, False),
        (ISO27005RiskCreateForm, True),
        (ISO27005RiskUpdateForm, False),
        (RiskTreatmentPlanCreateForm, True),
        (RiskTreatmentPlanUpdateForm, False),
        (RiskAcceptanceCreateForm, True),
        (RiskAcceptanceUpdateForm, False),
        # A row of a treatment plan, added from its page.
        (TreatmentActionCreateForm, True),
        (ThreatCreateForm, True),
        (ThreatUpdateForm, False),
        (VulnerabilityCreateForm, True),
        (VulnerabilityUpdateForm, False),
        # Rows of a supplier, created and edited from its page.
        (SupplierContactForm, True),
        (SupplierSubprocessorCreateForm, True),
        (SupplierSubprocessorForm, False),
    ]


# The detail pages that follow the standard : (view class, template).
def _pages():
    from assets.views import (
        CertificateCreateView,
        CertificateDetailView,
        ContractCreateView,
        ContractDetailView,
        GroupCreateView,
        GroupDetailView,
        EssentialAssetCreateView,
        EssentialAssetDetailView,
        SiteCreateView,
        SiteDetailView,
        SupplierCreateView,
        SupplierDetailView,
        SupportAssetCreateView,
        SupportAssetDetailView,
    )
    from compliance.views import (
        ActionPlanCreateView,
        ActionPlanDetailView,
        AssessmentCreateView,
        AssessmentDetailView,
        FindingDetailView,
        FindingRegisterCreateView,
        FrameworkCreateView,
        FrameworkDetailView,
        RequirementCreateView,
        RequirementDetailView,
    )
    from context.views import (
        IssueCreateView,
        IssueDetailView,
        ObjectiveCreateView,
        ObjectiveDetailView,
        ScopeCreateView,
        ScopeDetailView,
        StakeholderCreateView,
        StakeholderDetailView,
    )
    from risks.views import (
        ISO27005RiskCreateView,
        ISO27005RiskDetailView,
        RiskAcceptanceCreateView,
        RiskAcceptanceDetailView,
        RiskAssessmentCreateView,
        RiskAssessmentDetailView,
        ThreatCreateView,
        ThreatDetailView,
        TreatmentPlanCreateView,
        TreatmentPlanDetailView,
        VulnerabilityCreateView,
        VulnerabilityDetailView,
    )

    return [
        (ScopeCreateView, ScopeDetailView, "context/templates/context/scope_detail.html",
         "context/templates/context/scope_table_body.html"),
        (IssueCreateView, IssueDetailView, "context/templates/context/issue_detail.html",
         "context/templates/context/issue_table_body.html"),
        (StakeholderCreateView, StakeholderDetailView, "context/templates/context/stakeholder_detail.html",
         "context/templates/context/stakeholder_table_body.html"),
        (ObjectiveCreateView, ObjectiveDetailView, "context/templates/context/objective_detail.html",
         "context/templates/context/objective_table_body.html"),
        (EssentialAssetCreateView, EssentialAssetDetailView, "assets/templates/assets/essential_asset_detail.html",
         "assets/templates/assets/essential_asset_table_body.html"),
        (SupportAssetCreateView, SupportAssetDetailView, "assets/templates/assets/support_asset_detail.html",
         "assets/templates/assets/support_asset_table_body.html"),
        (SupplierCreateView, SupplierDetailView, "assets/templates/assets/supplier_detail.html",
         "assets/templates/assets/supplier_table_body.html"),
        (GroupCreateView, GroupDetailView, "assets/templates/assets/group_detail.html",
         "assets/templates/assets/group_table_body.html"),
        (SiteCreateView, SiteDetailView, "assets/templates/assets/site_detail.html",
         "assets/templates/assets/site_table_body.html"),
        (ContractCreateView, ContractDetailView, "assets/templates/assets/contract_detail.html",
         "assets/templates/assets/contract_table_body.html"),
        (CertificateCreateView, CertificateDetailView, "assets/templates/assets/certificate_detail.html",
         "assets/templates/assets/certificate_table_body.html"),
        (FrameworkCreateView, FrameworkDetailView, "compliance/templates/compliance/framework_detail.html",
         "compliance/templates/compliance/framework_table_body.html"),
        (ActionPlanCreateView, ActionPlanDetailView, "compliance/templates/compliance/action_plan_detail.html",
         "compliance/templates/compliance/action_plan_table_body.html"),
        (AssessmentCreateView, AssessmentDetailView, "compliance/templates/compliance/assessment_detail.html",
         "compliance/templates/compliance/assessment_table_body.html"),
        (RequirementCreateView, RequirementDetailView, "compliance/templates/compliance/requirement_detail.html",
         "compliance/templates/compliance/requirement_table_body.html"),
        (FindingRegisterCreateView, FindingDetailView, "compliance/templates/compliance/finding_detail.html",
         "compliance/templates/compliance/finding_register_table_body.html"),
        (RiskAssessmentCreateView, RiskAssessmentDetailView, "risks/templates/risks/assessment_detail.html",
         "risks/templates/risks/assessment_table_body.html"),
        (ISO27005RiskCreateView, ISO27005RiskDetailView, "risks/templates/risks/iso27005_risk_detail.html",
         "risks/templates/risks/iso27005_risk_table_body.html"),
        (TreatmentPlanCreateView, TreatmentPlanDetailView, "risks/templates/risks/treatment_plan_detail.html",
         "risks/templates/risks/treatment_plan_table_body.html"),
        (RiskAcceptanceCreateView, RiskAcceptanceDetailView, "risks/templates/risks/acceptance_detail.html",
         "risks/templates/risks/acceptance_table_body.html"),
        (ThreatCreateView, ThreatDetailView, "risks/templates/risks/threat_detail.html",
         "risks/templates/risks/threat_table_body.html"),
        (VulnerabilityCreateView, VulnerabilityDetailView, "risks/templates/risks/vulnerability_detail.html",
         "risks/templates/risks/vulnerability_table_body.html"),
    ]


class TestTheRules:
    def test_a_helper_that_says_its_label_again_is_caught(self):
        assert help_restates_label("Name", "Name of the scope.")
        assert help_restates_label("Description", "Description of the asset.")
        assert help_restates_label("Nom", "Nom du périmètre.")
        assert help_restates_label("Sites inclus", "Sites inclus dans le périmètre.")

    def test_a_helper_that_brings_something_is_kept(self):
        assert not help_restates_label("Name", 'For example "Head office" or "The whole company".')
        assert not help_restates_label(
            "Boundaries and exclusions", 'What is left out. Write "no exclusion" when it covers everything.',
        )
        assert not help_restates_label("Nom", "Par exemple « Siège social » ou « Toute l'entreprise ».")

    def test_an_acronym_alone_is_not_a_label(self):
        assert is_bare_acronym("RTO")
        assert is_bare_acronym("RPO")
        assert is_bare_acronym("DMT")
        assert not is_bare_acronym("Recovery time objective (RTO)")
        assert not is_bare_acronym("Name")
        assert not is_bare_acronym("Type")

    def test_a_creation_form_that_asks_too_much_is_caught(self):
        from django import forms

        from core.modal_forms import Step, SteppedFormMixin

        class TooMuch(SteppedFormMixin, forms.Form):
            a = forms.CharField()
            b = forms.CharField()
            c = forms.CharField()
            d = forms.CharField()
            e = forms.CharField()
            f = forms.CharField()
            g = forms.CharField(label="RTO", help_text="The RTO.")
            steps = [Step("One", "x", ["a", "b", "c", "d"]), Step("Two", "x", ["e", "f", "g"])]

        findings = form_findings(TooMuch(), creation=True)

        assert any("7 fields" in line for line in findings)
        assert any("one screen" in line for line in findings)
        assert any("acronym alone" in line for line in findings)
        assert any("says the label" in line for line in findings)
        # The same form, as an edit, is not held to the creation rules.
        assert not any("fields at creation" in line for line in form_findings(TooMuch()))


class TestTheFormsThatFollowTheStandard:
    @pytest.mark.parametrize("language", ["en", "fr"])
    def test_they_owe_it_nothing(self, language):
        """In the two languages shipped : a translation can say the label again too."""
        user = UserFactory(is_superuser=True)
        # Several scopes : every question a creation can ask is asked.
        ScopeFactory()
        ScopeFactory()
        findings = []
        with translation.override(language):
            for form_class, creation in _forms():
                try:
                    form = form_class(user=user)
                except TypeError:
                    form = form_class()
                findings += form_findings(form, creation=creation)

        assert findings == []

    def test_a_creation_fits_one_screen(self):
        ScopeFactory()
        ScopeFactory()
        for form_class, creation in _forms():
            if not creation:
                continue
            form = form_class()
            assert len([f for f in form.fields.values() if not f.widget.is_hidden]) <= MAX_CREATION_FIELDS
            assert not form.is_multistep

    def test_every_step_of_an_edit_form_opens_on_its_own(self):
        """Each card of the record page has its dialog : each step is a section."""
        for form_class, creation in _forms():
            if creation:
                continue
            assert all(step.key for step in form_class.steps), form_class.__name__


class TestThePagesThatFollowTheStandard:
    def test_a_creation_lands_on_the_record_which_says_what_it_needs(self):
        from core.mixins import CompleteOnRecordMixin

        for create_view, detail_view, _detail, _rows in _pages():
            assert create_view.land_on_record is True, create_view.__name__
            assert issubclass(detail_view, CompleteOnRecordMixin), detail_view.__name__
            assert detail_view.edit_url_name and detail_view.edit_permission
            assert hasattr(detail_view.model, "COMPLETENESS")
            assert hasattr(detail_view.model, "get_absolute_url")

    def test_the_record_page_lists_what_is_missing_and_edits_by_section(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        for _create, _detail_view, detail, _rows in _pages():
            source = (root / detail).read_text(encoding="utf-8")
            assert "{% completeness_card completeness edit_url=edit_url %}" in source, detail
            assert "{% section_edit edit_url " in source, detail

    def test_the_empty_register_explains_and_offers_the_first_record(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        for _create, _detail_view, _detail, rows in _pages():
            source = (root / rows).read_text(encoding="utf-8")
            assert "{% list_empty " in source, rows
            assert "create_url=" in source and "permission=" in source, rows


# ── What every listed entity does, checked through its views ────────────────

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


def _url_name(view_class):
    """The URL name that serves ``view_class``, read from the URL configuration."""
    from django.urls import get_resolver

    def walk(patterns, namespace=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                found = walk(pattern.url_patterns, f"{namespace}{pattern.namespace}:" if pattern.namespace else namespace)
                if found:
                    return found
            elif getattr(pattern.callback, "view_class", None) is view_class:
                return f"{namespace}{pattern.name}"
        return None

    return walk(get_resolver().url_patterns)


def _answer(form):
    """A minimal answer to a creation form : something for each question it requires."""
    from django import forms

    data = {}
    for name, field in form.fields.items():
        if field.widget.is_hidden or not field.required:
            continue
        if isinstance(field, forms.ModelMultipleChoiceField):
            data[name] = [str(field.queryset.first().pk)]
        elif isinstance(field, forms.ModelChoiceField):
            data[name] = str(field.queryset.first().pk)
        elif isinstance(field, forms.ChoiceField):
            for value, label in field.choices:
                if isinstance(label, (list, tuple)):  # a select with groups
                    value = label[0][0]
                if value not in ("", None):
                    data[name] = str(value)
                    break
        elif isinstance(field, forms.DateField):
            data[name] = "2030-01-01"
        elif isinstance(field, (forms.IntegerField, forms.DecimalField, forms.FloatField)):
            data[name] = "1"
        elif isinstance(field, forms.BooleanField):
            data[name] = "on"
        else:
            data[name] = "A first record"
    return data


def _current_answers(form):
    """What the dialog of ``form`` posts back when the reader changes nothing."""
    import datetime

    data = {}
    for name in form.fields:
        value = form[name].value()
        if value in (None, "", [], ()) or value is False:
            continue
        if value is True:
            data[name] = "on"
        elif isinstance(value, (datetime.date, datetime.datetime)):
            data[name] = value.isoformat()
        elif isinstance(value, (list, tuple)):
            data[name] = [str(getattr(item, "pk", item)) for item in value]
        else:
            data[name] = str(getattr(value, "pk", value))
    return data


#: What a save always moves : not part of what a section may leave alone.
_BOOKKEEPING = {"updated_at", "version"}


def _snapshot(record):
    """Every stored value of ``record``, its relations included."""
    values = {
        field.attname: getattr(record, field.attname)
        for field in record._meta.concrete_fields
        if field.name not in _BOOKKEEPING
    }
    for field in record._meta.many_to_many:
        values[field.name] = sorted(str(pk) for pk in getattr(record, field.name).values_list("pk", flat=True))
    return values


def _something_to_choose_from():
    """A required relation needs a record to point at : a certificate, its framework;
    an ISO 27005 analysis, its assessment, its threat and its vulnerability."""
    from compliance.models import Framework
    from compliance.tests.factories import FrameworkFactory
    from risks.models import RiskAssessment, Threat, Vulnerability
    from risks.tests.factories import RiskAssessmentFactory, ThreatFactory, VulnerabilityFactory

    if not Framework.objects.exists():
        FrameworkFactory()
    if not RiskAssessment.objects.filter(methodology="iso27005").exists():
        RiskAssessmentFactory(methodology="iso27005")
    if not Threat.objects.exists():
        ThreatFactory()
    if not Vulnerability.objects.exists():
        VulnerabilityFactory()
    # A treatment plan and an acceptance are about a risk.
    from risks.models import Risk
    from risks.tests.factories import RiskFactory

    if not Risk.objects.exists():
        RiskFactory()


def _page_ids():
    return [create.__name__.removesuffix("CreateView") for create, _detail, _template, _rows in _pages()]


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _create(client, admin, create_view):
    """Create a record through the dialog, answering only what is required."""
    _something_to_choose_from()
    form = create_view.form_class(user=admin)
    response = client.post(reverse(_url_name(create_view)), _answer(form), **DRAWER)
    assert response.status_code == 204, response.content.decode()[:800]
    record = create_view.model.objects.order_by("-created_at").first()
    return response, record


@pytest.mark.parametrize("page", _pages(), ids=_page_ids())
class TestEveryEntityThatFollowsTheStandard:
    def test_the_dialog_asks_six_questions_at_most_on_one_screen(self, client, admin, page):
        create_view, _detail, _template, _rows = page
        ScopeFactory()
        ScopeFactory()

        html = client.get(reverse(_url_name(create_view)), **DRAWER).content.decode()

        assert html.count('class="mform-field') <= MAX_CREATION_FIELDS or len(
            [f for f in create_view.form_class(user=admin).fields.values() if not f.widget.is_hidden]
        ) <= MAX_CREATION_FIELDS
        # One screen : no step to walk through, and a button that says Create.
        assert "data-mform-pill" not in html
        assert ">Create<" in html.replace("\n", "").replace("  ", "")

    def test_answering_what_is_required_creates_the_record_and_opens_it(self, client, admin, page):
        create_view, _detail, _template, _rows = page
        ScopeFactory()

        response, record = _create(client, admin, create_view)

        assert response["HX-Redirect"] == record.get_absolute_url()
        assert record.created_by == admin

    def test_with_one_scope_the_record_is_filed_under_it(self, client, admin, page):
        create_view, _detail, _template, _rows = page
        if not hasattr(create_view.model, "scopes"):
            pytest.skip("the entity is not filed under scopes")
        only = ScopeFactory()

        assert "scopes" not in create_view.form_class(user=admin).fields
        _response, record = _create(client, admin, create_view)

        assert list(record.scopes.all()) == [only]

    def test_the_record_page_opens_each_section_of_its_form(self, client, admin, page):
        create_view, detail_view, _template, _rows = page
        ScopeFactory()
        _response, record = _create(client, admin, create_view)
        edit = reverse(detail_view.edit_url_name, kwargs={"pk": record.pk})

        html = client.get(record.get_absolute_url()).content.decode()

        update_form = TestEveryEntityThatFollowsTheStandard._update_form(create_view.model)
        for key in update_form.section_keys():
            assert f'{edit}?section={key}"' in html, f"no card opens the section '{key}'"

    def test_saving_a_section_leaves_the_rest_of_the_record_alone(self, client, admin, page):
        """Each card is saved as the reader found it : nothing else may move.

        A section that cleared a field it does not show (a logo, a type set
        from another field) would do it here.
        """
        create_view, detail_view, _template, _rows = page
        ScopeFactory()
        _response, record = _create(client, admin, create_view)
        edit = reverse(detail_view.edit_url_name, kwargs={"pk": record.pk})
        update_form = TestEveryEntityThatFollowsTheStandard._update_form(create_view.model)
        before = _snapshot(record)

        for key in update_form.section_keys():
            response = client.get(f"{edit}?section={key}", **DRAWER)
            assert response.status_code == 200, key
            assert 'name="_section"' in response.content.decode(), key

            try:
                form = update_form(instance=record, user=admin, section=key)
            except TypeError:
                form = update_form(instance=record, section=key)
            response = client.post(edit, {**_current_answers(form), "_section": key}, **DRAWER)
            assert response.status_code == 204, f"{key} : {response.content.decode()[:600]}"

            record = type(record).objects.get(pk=record.pk)
            assert _snapshot(record) == before, f"saving the section '{key}' changed something else"

    def test_a_reader_is_offered_no_edit(self, client, page):
        create_view, detail_view, _template, _rows = page
        admin = UserFactory(is_superuser=True)
        client.force_login(admin)
        ScopeFactory()
        _response, record = _create(client, admin, create_view)

        reader = UserFactory()
        TestEveryEntityThatFollowsTheStandard._grant(reader, detail_view.permission_required)
        client.force_login(reader)
        html = client.get(record.get_absolute_url()).content.decode()

        assert "?section=" not in html

    @staticmethod
    def _update_form(model):
        from core.tests.test_completeness import TestDeclarationsHoldTogether

        return TestDeclarationsHoldTogether._update_forms()[model]

    @staticmethod
    def _grant(user, codename):
        from accounts.models import Group, Permission

        group = Group.objects.create(name=f"readers-{user.pk}")
        group.permissions.add(Permission.objects.get(codename=codename))
        group.users.add(user)

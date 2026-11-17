# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The usability standard, held by tests (``docs/sdk/usability-standard.md``).

A screen that follows the standard is listed here, and stays held to it :
adding a seventh field to a listed creation form, or a helper that says its
label again, fails. The list grows module by module; what is not listed yet
is not claimed to follow the standard.
"""

import pytest
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
    from assets.forms import EssentialAssetCreateForm, EssentialAssetUpdateForm
    from context.forms import ScopeCreateForm, ScopeUpdateForm

    return [
        (ScopeCreateForm, True),
        (ScopeUpdateForm, False),
        (EssentialAssetCreateForm, True),
        (EssentialAssetUpdateForm, False),
    ]


# The detail pages that follow the standard : (view class, template).
def _pages():
    from assets.views import EssentialAssetCreateView, EssentialAssetDetailView
    from context.views import ScopeCreateView, ScopeDetailView

    return [
        (ScopeCreateView, ScopeDetailView, "context/templates/context/scope_detail.html",
         "context/templates/context/scope_table_body.html"),
        (EssentialAssetCreateView, EssentialAssetDetailView, "assets/templates/assets/essential_asset_detail.html",
         "assets/templates/assets/essential_asset_table_body.html"),
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

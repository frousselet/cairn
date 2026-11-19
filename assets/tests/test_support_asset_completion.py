# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A support asset is created on one screen, then completed on its page.

What every entity of the usability standard does (a short creation, landing
on the record, one card per section) is checked for all of them in
``core/tests/test_usability_standard.py``. This file holds what is particular
to the support asset : its category names its type, and the security needs it
inherits are *not known* until an essential asset that relies on it is
assessed, where they used to read "negligible".
"""

import importlib

import pytest
from django.apps import apps
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.constants import SUPPORT_ASSET_CATEGORY_MAP, support_asset_category_choices, support_asset_type_for
from assets.forms import SupportAssetCreateForm, SupportAssetUpdateForm
from assets.models import SupportAsset
from assets.tests.factories import DependencyFactory, EssentialAssetFactory, SupportAssetFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


class TestTheCategoryNamesTheType:
    def test_every_category_belongs_to_one_type(self):
        seen = [category for categories in SUPPORT_ASSET_CATEGORY_MAP.values() for category in categories]

        assert len(seen) == len(set(seen))
        assert support_asset_type_for("laptop") == "hardware"
        assert support_asset_type_for("hosting_service") == "service"
        assert support_asset_type_for("no_such_category") == ""

    def test_the_form_asks_for_the_category_alone(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = SupportAssetCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "description", "category", "owner"]
        assert "type" not in SupportAssetUpdateForm(user=admin).fields

    def test_the_categories_are_grouped_under_their_type(self, admin):
        groups = dict(support_asset_category_choices())

        assert list(groups) == ["Hardware", "Software", "Network", "Person", "Service", "Paper"]
        assert ("laptop", "Laptop") in groups["Hardware"]
        choices = SupportAssetCreateForm(user=admin).fields["category"].choices
        assert choices[0][0] == "" and choices[1][0] == "Hardware"

    def test_the_type_follows_the_category(self, admin):
        ScopeFactory()
        form = SupportAssetCreateForm(
            {"name": "Hosting contract", "category": "hosting_service", "owner": str(admin.pk), "description": ""},
            user=admin,
        )

        assert form.is_valid(), form.errors
        asset = form.save()

        assert (asset.type, asset.category) == ("service", "hosting_service")

    def test_changing_the_category_changes_the_type(self, admin):
        asset = SupportAssetFactory(type="hardware", category="server")
        form = SupportAssetUpdateForm({"name": asset.name, "category": "database", "description": ""}, instance=asset, user=admin, section="identity")

        assert form.is_valid(), form.errors
        form.save()

        asset.refresh_from_db()
        assert (asset.type, asset.category) == ("software", "database")


class TestTheNeedsItInherits:
    def test_they_are_not_known_until_an_essential_asset_relies_on_it(self, client, admin):
        asset = SupportAssetFactory()

        html = client.get(asset.get_absolute_url()).content.decode()

        assert asset.inherited_availability is None
        assert "No essential asset relies on it yet" in html
        assert ">Negligible</span>" not in html

    def test_they_read_with_their_words_once_inherited(self, client, admin):
        asset = SupportAssetFactory()
        DependencyFactory(
            support_asset=asset,
            essential_asset=EssentialAssetFactory(confidentiality_level=4, integrity_level=None, availability_level=0),
        )

        html = client.get(asset.get_absolute_url()).content.decode()

        assert ">Critical</span>" in html
        assert ">Negligible</span>" in html
        # The criterion nobody assessed yet stays unknown, among known ones.
        assert ">Not assessed</span>" in html

    def test_the_register_says_not_assessed_rather_than_three_dashes(self, client, admin):
        SupportAssetFactory(name="Brand new server")

        html = client.get(reverse("assets:support-asset-list")).content.decode()

        assert "Brand new server" in html
        assert "Not assessed" in html

    def test_an_unknown_need_is_not_a_high_one_for_the_failure_points(self):
        """Rule 4a compares the inherited availability : unknown must not raise, nor count."""
        from assets.services.spof_detection import SpofDetector
        from assets.tests.test_spof_detection import _make_site, _make_site_asset_dep

        asset = SupportAssetFactory()
        dependency = _make_site_asset_dep(asset, _make_site())
        assert asset.inherited_availability is None

        results = SpofDetector().detect_all()

        row = next(d for d in results["site_asset_dependencies"] if d["id"] == str(dependency.id))
        assert "single_site_high_availability" not in row["rules"]


class TestWhatItStillNeeds:
    def test_a_new_asset_lists_what_would_make_it_useful(self, client, admin):
        asset = SupportAssetFactory(environment="", exposure_level="", end_of_life_date=None)
        edit = reverse("assets:support-asset-update", kwargs={"pk": asset.pk})

        report = completeness_of(asset)
        html = client.get(asset.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["essential_assets", "exposure", "end_of_life"]
        # Nothing holds its lifecycle back : it is advice.
        assert report.blocking_missing == [] and report.can_advance
        assert "Link the essential assets" in html
        assert f'href="{reverse("assets:dependency-list")}"' in html
        assert f'href="{edit}?section=exposure"' in html
        assert f'href="{edit}?section=dates"' in html

    def test_what_is_done_leaves_the_list(self, admin):
        from datetime import date

        asset = SupportAssetFactory(environment="production", exposure_level="internal", end_of_life_date=date(2031, 1, 1))
        DependencyFactory(support_asset=asset, essential_asset=EssentialAssetFactory())

        assert completeness_of(asset).is_complete

    def test_the_empty_register_explains_and_offers_the_first_asset(self, client, admin):
        html = client.get(reverse("assets:support-asset-list")).content.decode()

        assert "No support asset yet." in html
        create = reverse("assets:support-asset-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheMigration:
    migration = importlib.import_module("assets.migrations.0052_support_asset_needs_not_known")

    def test_a_default_that_read_as_an_assessment_becomes_unknown(self):
        orphan = SupportAssetFactory()
        relied_on = SupportAssetFactory()
        unassessed = SupportAssetFactory()
        DependencyFactory(
            support_asset=relied_on,
            essential_asset=EssentialAssetFactory(confidentiality_level=3, integrity_level=1, availability_level=4),
        )
        DependencyFactory(
            support_asset=unassessed,
            essential_asset=EssentialAssetFactory(confidentiality_level=None, integrity_level=None, availability_level=None),
        )
        # As the previous schema left them : zero everywhere nothing was inherited.
        SupportAsset.objects.filter(pk__in=[orphan.pk, unassessed.pk]).update(
            inherited_confidentiality=0, inherited_integrity=0, inherited_availability=0,
        )

        self.migration.recompute(apps, None)

        for asset in (orphan, relied_on, unassessed):
            asset.refresh_from_db()
        assert (orphan.inherited_confidentiality, orphan.inherited_integrity, orphan.inherited_availability) == (None, None, None)
        assert (relied_on.inherited_confidentiality, relied_on.inherited_integrity, relied_on.inherited_availability) == (3, 1, 4)
        assert unassessed.inherited_availability is None

    def test_going_back_reads_negligible_again(self):
        asset = SupportAssetFactory()

        self.migration.back_to_negligible(apps, None)

        asset.refresh_from_db()
        assert (asset.inherited_confidentiality, asset.inherited_integrity, asset.inherited_availability) == (0, 0, 0)

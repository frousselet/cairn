# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An essential asset is created on one screen, then completed on its page.

The pilot of the usability standard (``docs/sdk/usability-standard.md``) for
the assets module. Creation asks what the asset is and who answers for it;
its security needs start *not assessed* (no default level), are set on its
page, and are what the lifecycle waits for before the asset becomes active.
"""

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.forms import EssentialAssetCreateForm, EssentialAssetUpdateForm
from assets.models import AssetValuation, EssentialAsset
from assets.tests.factories import EssentialAssetFactory
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _not_assessed(**kwargs):
    return EssentialAssetFactory(
        confidentiality_level=None, integrity_level=None, availability_level=None, **kwargs,
    )


class TestCreationIsShort:
    def test_it_asks_what_the_asset_is_and_who_answers_for_it(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = EssentialAssetCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "description", "category", "owner"]
        assert len(form.fields) <= 6
        assert form.is_multistep is False

    def test_with_one_scope_there_is_nothing_to_choose(self, admin):
        only = ScopeFactory()

        form = EssentialAssetCreateForm(
            {"name": "Customer file", "category": "commercial_data", "owner": str(admin.pk), "description": ""},
            user=admin,
        )

        assert "scopes" not in form.fields
        assert form.is_valid(), form.errors
        asset = form.save()
        # Filed under the only scope there is.
        assert list(asset.scopes.all()) == [only]

    def test_whoever_registers_the_asset_answers_for_it_by_default(self, admin):
        assert EssentialAssetCreateForm(user=admin).fields["owner"].initial == admin.pk

    def test_the_category_names_the_type(self, admin):
        """RS-01 : the two cannot disagree, so the type is not asked."""
        form = EssentialAssetCreateForm(
            {"name": "Payroll", "category": "support_process", "owner": str(admin.pk), "description": ""}, user=admin,
        )

        assert "type" not in form.fields
        assert form.is_valid(), form.errors
        assert form.save().type == "business_process"

    def test_the_categories_are_grouped_under_their_type(self, admin):
        choices = EssentialAssetCreateForm(user=admin).fields["category"].choices
        groups = {str(label): [code for code, _ in options] for label, options in choices[1:]}

        assert choices[0][0] == ""
        assert "core_process" in groups["Business process"]
        assert "personal_data" in groups["Information"]

    def test_the_security_needs_start_not_assessed(self, admin):
        """A level is a decision somebody took, never a default (RV-07)."""
        form = EssentialAssetCreateForm(
            {"name": "Customer file", "category": "commercial_data", "owner": str(admin.pk), "description": ""},
            user=admin,
        )
        assert form.is_valid(), form.errors

        asset = form.save()

        assert (asset.confidentiality_level, asset.integrity_level, asset.availability_level) == (None, None, None)
        assert asset.security_needs_assessed is False
        assert asset.max_dic_level is None
        assert not AssetValuation.objects.filter(essential_asset=asset).exists()

    def test_creating_lands_on_the_new_asset(self, client, admin):
        response = client.post(
            reverse("assets:essential-asset-create"),
            {"name": "Customer file", "category": "commercial_data", "owner": str(admin.pk), "description": ""},
            **DRAWER,
        )

        asset = EssentialAsset.objects.get(name="Customer file")
        assert response.status_code == 204
        assert response["HX-Redirect"] == reverse("assets:essential-asset-detail", kwargs={"pk": asset.pk})
        assert asset.created_by == admin


class TestAssessingTheSecurityNeeds:
    def test_the_section_asks_the_three_questions(self, client, admin):
        asset = _not_assessed()

        response = client.get(
            reverse("assets:essential-asset-update", kwargs={"pk": asset.pk}) + "?section=security", **DRAWER,
        )

        form = response.context["form"]
        assert set(form.fields) == {
            "confidentiality_level", "integrity_level", "availability_level",
            "confidentiality_justification", "integrity_justification", "availability_justification",
        }
        assert response.context["modal_title"] == "Security needs"
        # An empty level is a state of the asset, said in words.
        assert str(form.fields["confidentiality_level"].choices[0][1]) == "Not assessed"

    def test_setting_the_needs_is_recorded_as_an_assessment(self, client, admin):
        """RV-06 : who decided what, and when."""
        from django.utils import timezone

        asset = _not_assessed()

        response = client.post(
            reverse("assets:essential-asset-update", kwargs={"pk": asset.pk}),
            {
                "_section": "security",
                "confidentiality_level": "4", "confidentiality_justification": "Personal data of every customer.",
                "integrity_level": "3", "integrity_justification": "",
                "availability_level": "2", "availability_justification": "",
            },
            **DRAWER,
        )

        asset.refresh_from_db()
        assert response.status_code == 204
        assert (asset.confidentiality_level, asset.integrity_level, asset.availability_level) == (4, 3, 2)
        assert asset.security_needs_assessed and asset.max_dic_level == 4
        valuation = AssetValuation.objects.get(essential_asset=asset)
        assert valuation.evaluated_by == admin
        assert valuation.evaluation_date == timezone.localdate()
        assert (valuation.confidentiality_level, valuation.integrity_level, valuation.availability_level) == (4, 3, 2)
        assert "Personal data of every customer." in valuation.justification

    def test_saving_again_without_changing_a_level_records_nothing_more(self, admin):
        asset = EssentialAssetFactory(confidentiality_level=4, integrity_level=3, availability_level=2)
        data = {
            "confidentiality_level": "4", "confidentiality_justification": "Reworded.",
            "integrity_level": "3", "integrity_justification": "",
            "availability_level": "2", "availability_justification": "",
        }

        form = EssentialAssetUpdateForm(data, instance=asset, user=admin, section="security")
        assert form.is_valid(), form.errors
        form.save()

        assert not AssetValuation.objects.filter(essential_asset=asset).exists()

    def test_a_partial_answer_is_kept_and_is_not_an_assessment(self, admin):
        asset = _not_assessed()
        data = {
            "confidentiality_level": "4", "confidentiality_justification": "",
            "integrity_level": "", "integrity_justification": "",
            "availability_level": "", "availability_justification": "",
        }

        form = EssentialAssetUpdateForm(data, instance=asset, user=admin, section="security")
        assert form.is_valid(), form.errors
        form.save()

        asset.refresh_from_db()
        assert asset.confidentiality_level == 4 and asset.integrity_level is None
        assert not asset.security_needs_assessed
        assert not AssetValuation.objects.filter(essential_asset=asset).exists()

    def test_another_section_does_not_touch_the_needs(self, admin):
        asset = EssentialAssetFactory(confidentiality_level=4, integrity_level=3, availability_level=2)

        form = EssentialAssetUpdateForm(
            {"max_tolerable_downtime": "2 days", "recovery_time_objective": "", "recovery_point_objective": ""},
            instance=asset, user=admin, section="continuity",
        )
        assert form.is_valid(), form.errors
        form.save()

        asset.refresh_from_db()
        assert (asset.confidentiality_level, asset.integrity_level, asset.availability_level) == (4, 3, 2)
        assert asset.max_tolerable_downtime == "2 days"

    def test_an_inherited_level_ignores_an_asset_not_assessed_yet(self):
        """RV-03 : the maximum over the assets that have a level."""
        from assets.tests.factories import DependencyFactory, SupportAssetFactory

        support = SupportAssetFactory()
        DependencyFactory(support_asset=support, essential_asset=_not_assessed())
        DependencyFactory(
            support_asset=support,
            essential_asset=EssentialAssetFactory(confidentiality_level=3, integrity_level=1, availability_level=4),
        )

        support.recalculate_inherited_dic()

        support.refresh_from_db()
        assert (support.inherited_confidentiality, support.inherited_integrity, support.inherited_availability) == (3, 1, 4)


class TestThePage:
    def test_a_level_is_shown_with_its_word(self, client, admin):
        asset = EssentialAssetFactory(confidentiality_level=4, integrity_level=None, availability_level=0)

        html = client.get(reverse("assets:essential-asset-detail", kwargs={"pk": asset.pk})).content.decode()

        assert ">Critical</span>" in html
        assert ">Negligible</span>" in html
        assert ">Not assessed</span>" in html

    def test_a_new_asset_says_what_it_needs(self, client, admin):
        asset = _not_assessed()
        edit = reverse("assets:essential-asset-update", kwargs={"pk": asset.pk})

        html = client.get(reverse("assets:essential-asset-detail", kwargs={"pk": asset.pk})).content.decode()

        assert "Assess its security needs" in html
        assert f'href="{edit}?section=security"' in html
        # What is done on another page is a link to that page.
        assert f'href="{reverse("assets:dependency-list")}"' in html
        for key in EssentialAssetUpdateForm.section_keys():
            assert f'{edit}?section={key}"' in html

    def test_the_acronyms_are_spelled_out(self, client, admin):
        asset = EssentialAssetFactory()

        html = client.get(reverse("assets:essential-asset-detail", kwargs={"pk": asset.pk})).content.decode()

        assert "Recovery time objective (RTO)" in html
        assert "Maximum tolerable downtime (MTD)" in html

    def test_the_empty_register_offers_the_first_asset(self, client, admin):
        html = client.get(reverse("assets:essential-asset-list")).content.decode()

        assert "No essential asset yet." in html
        create = reverse("assets:essential-asset-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApiAndMcpSayTheSame:
    def _api(self, user):
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user)
        return api

    def test_one_record_carries_its_completeness(self, admin):
        asset = _not_assessed()

        payload = self._api(admin).get(f"/api/v1/assets/essential-assets/{asset.pk}/").json()
        data = payload.get("data", payload)

        assert data["confidentiality_level"] is None
        assert data["completeness"]["can_advance"] is False
        assert "security_needs" in [item["key"] for item in data["completeness"]["missing"]]

    def test_a_list_does_not_run_the_checks_of_every_row(self, admin):
        _not_assessed()

        payload = self._api(admin).get("/api/v1/assets/essential-assets/").json()
        rows = payload.get("data", payload.get("results", payload))

        assert rows and "completeness" not in rows[0]

    def test_a_level_left_out_stays_empty_through_the_api(self, admin):
        response = self._api(admin).post(
            "/api/v1/assets/essential-assets/",
            {"name": "Contracts", "type": "information", "category": "legal_data", "owner": str(admin.pk)},
            format="json",
        )

        assert response.status_code == 201, response.content
        asset = EssentialAsset.objects.get(name="Contracts")
        assert asset.confidentiality_level is None

    def test_the_api_refuses_to_activate_an_asset_not_assessed(self, admin):
        asset = _not_assessed(workflow_state="identified")

        response = self._api(admin).post(
            f"/api/v1/assets/essential-assets/{asset.pk}/transition/", {"target_state": "active"}, format="json",
        )

        asset.refresh_from_db()
        assert response.status_code >= 400
        assert asset.workflow_state == "identified"
        assert "assess its security needs" in response.content.decode()

    def test_the_scope_api_carries_it_too(self, admin):
        scope = ScopeFactory()

        payload = self._api(admin).get(f"/api/v1/context/scopes/{scope.pk}/").json()
        data = payload.get("data", payload)

        assert [item["key"] for item in data["completeness"]["missing"] if item["blocking"]] == ["boundaries", "managers"]

    def test_the_mcp_get_tool_reports_what_is_missing(self, admin):
        from mcp.tools import _get_handler

        asset = _not_assessed()

        data = _get_handler(EssentialAsset, ["id", "name"])(admin, {"id": str(asset.pk)})

        assert data["completeness"]["can_advance"] is False
        assert data["completeness"]["missing"][0]["key"] == "security_needs"

    def test_the_mcp_transition_tool_says_what_remains(self, admin):
        from mcp.tools import _transition_handler

        asset = _not_assessed(workflow_state="identified")

        result = _transition_handler(EssentialAsset, "assets.essential_asset")(
            admin, {"id": str(asset.pk), "target_state": "active"},
        )

        assert "assess its security needs" in str(result)
        asset.refresh_from_db()
        assert asset.workflow_state == "identified"


class TestAStateWrittenDirectlyThroughMcp:
    """MCP create and update tools accept ``status`` (imports) : it is held to
    the same completeness as a transition."""

    WRITABLE = [
        "name", "type", "category", "status", "owner_id",
        "confidentiality_level", "integrity_level", "availability_level",
    ]

    def test_an_update_cannot_slip_an_asset_not_assessed_into_active(self, admin):
        from mcp.tools import _update_handler

        asset = _not_assessed(workflow_state="identified")

        result = _update_handler(EssentialAsset, self.WRITABLE)(admin, {"id": str(asset.pk), "status": "active"})

        asset.refresh_from_db()
        assert asset.workflow_state == "identified"
        assert "assess its security needs" in str(result)

    def test_the_refusal_rolls_the_whole_update_back(self, admin):
        from mcp.tools import _update_handler

        asset = _not_assessed(workflow_state="identified", name="Before")

        _update_handler(EssentialAsset, self.WRITABLE)(
            admin, {"id": str(asset.pk), "status": "active", "name": "After"},
        )

        asset.refresh_from_db()
        assert asset.name == "Before"

    def test_an_assessed_asset_can_be_updated_to_active(self, admin):
        from mcp.tools import _update_handler

        asset = EssentialAssetFactory(workflow_state="identified")

        _update_handler(EssentialAsset, self.WRITABLE)(admin, {"id": str(asset.pk), "status": "active"})

        asset.refresh_from_db()
        assert asset.workflow_state == "active"

    def test_an_import_cannot_create_an_active_asset_without_its_needs(self, admin):
        from mcp.tools import _create_handler

        arguments = {
            "name": "Imported", "type": "information", "category": "legal_data",
            "owner_id": str(admin.pk), "status": "active",
        }

        result = _create_handler(EssentialAsset, self.WRITABLE)(admin, arguments)

        assert "assess its security needs" in str(result)
        assert not EssentialAsset.objects.filter(name="Imported").exists()
        # With its three levels the same import goes through.
        arguments.update(confidentiality_level=3, integrity_level=2, availability_level=1)
        _create_handler(EssentialAsset, self.WRITABLE)(admin, arguments)
        assert EssentialAsset.objects.get(name="Imported").workflow_state == "active"

    def test_an_update_that_does_not_touch_the_state_is_never_held(self, admin):
        """A record already in use and incomplete stays editable."""
        from mcp.tools import _update_handler

        asset = _not_assessed(workflow_state="active")

        _update_handler(EssentialAsset, self.WRITABLE)(admin, {"id": str(asset.pk), "name": "Renamed"})

        asset.refresh_from_db()
        assert asset.name == "Renamed"

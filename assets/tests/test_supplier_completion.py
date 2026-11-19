# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A supplier is created on one screen, then completed on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the supplier : its criticality is a decision nobody takes for
the reader, its type is asked only when there are types to choose from, and
its logo survives the edit of another card.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from assets.forms import SupplierCreateForm, SupplierUpdateForm
from assets.models import Supplier, SupplierContact
from assets.tests.factories import SupplierDependencyFactory, SupplierFactory, SupplierTypeFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
#: A one-pixel PNG, as the logo widget posts it.
LOGO = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


class TestCreationIsShort:
    def test_it_asks_who_the_supplier_is_and_who_answers_for_it(self, admin):
        ScopeFactory()
        ScopeFactory()
        SupplierTypeFactory()

        form = SupplierCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "description", "type", "criticality", "owner"]
        assert form.is_multistep is False

    def test_the_type_is_not_asked_when_no_type_is_declared(self, admin):
        ScopeFactory()

        form = SupplierCreateForm(
            {"name": "Northwind Hosting", "criticality": "high", "owner": str(admin.pk), "description": ""},
            user=admin,
        )

        assert "type" not in form.fields
        assert form.is_valid(), form.errors
        assert form.save().type is None

    def test_the_criticality_is_a_decision_nobody_takes_for_the_reader(self, client, admin):
        ScopeFactory()

        html = client.get(reverse("assets:supplier-create"), **DRAWER).content.decode()
        select = html[html.index('name="criticality"'):]
        select = select[:select.index("</select>")]

        # The select opens on "Choose…" : no level is chosen for the reader.
        assert 'value="" selected>Choose…<' in select
        assert select.count("selected") == 1

    def test_leaving_the_criticality_out_is_refused_by_name(self, client, admin):
        ScopeFactory()

        response = client.post(
            reverse("assets:supplier-create"),
            {"name": "Northwind Hosting", "owner": str(admin.pk), "description": ""},
            **DRAWER,
        )

        assert response.status_code == 200
        assert "Choose a value for &quot;Criticality&quot;." in response.content.decode()
        assert not Supplier.objects.exists()

    def test_an_existing_supplier_keeps_the_criticality_it_has(self, admin):
        supplier = SupplierFactory(criticality="high")

        form = SupplierUpdateForm(instance=supplier, user=admin, section="identity")

        assert form["criticality"].value() == "high"


class TestTheLogo:
    def test_editing_another_card_keeps_it(self, client, admin):
        supplier = SupplierFactory(logo=LOGO, logo_16=LOGO, logo_32=LOGO, logo_64=LOGO)
        edit = reverse("assets:supplier-update", kwargs={"pk": supplier.pk})

        response = client.post(edit, {"_section": "coordinates", "country": "France"}, **DRAWER)

        supplier.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert supplier.country == "France"
        assert supplier.logo == LOGO and supplier.logo_64 == LOGO

    def test_the_identity_card_can_remove_it(self, client, admin):
        supplier = SupplierFactory(logo=LOGO, logo_16=LOGO, logo_32=LOGO, logo_64=LOGO)
        edit = reverse("assets:supplier-update", kwargs={"pk": supplier.pk})

        response = client.post(
            edit,
            {"_section": "identity", "name": supplier.name, "criticality": "medium", "owner": str(supplier.owner_id),
             "type": str(supplier.type_id), "logo": "", "description": ""},
            **DRAWER,
        )

        supplier.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert supplier.logo == "" and supplier.logo_64 == ""


class TestWhatItStillNeeds:
    def test_a_new_supplier_lists_what_would_make_it_useful(self, client, admin):
        supplier = SupplierFactory()
        edit = reverse("assets:supplier-update", kwargs={"pk": supplier.pk})

        report = completeness_of(supplier)
        html = client.get(supplier.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["contact", "country", "dependencies"]
        # Its assessment is what the lifecycle walks through : nothing waits here.
        assert report.blocking_missing == [] and report.can_advance
        assert "Add a contact" in html
        assert f'href="{reverse("assets:supplier-contact-create", kwargs={"supplier_pk": supplier.pk})}"' in html
        assert f'href="{edit}?section=coordinates"' in html
        assert f'href="{reverse("assets:supplier-dependency-list")}"' in html

    def test_what_is_done_leaves_the_list(self, admin):
        supplier = SupplierFactory(country="France")
        SupplierContact.objects.create(supplier=supplier, name="Ada Martin")
        SupplierDependencyFactory(supplier=supplier)

        assert completeness_of(supplier).is_complete


class TestThePage:
    def test_it_shows_who_answers_for_it_and_where_things_stand(self, client, admin):
        owner = UserFactory(first_name="Ada", last_name="Martin")
        supplier = SupplierFactory(owner=owner, status="active", notes="<p>Contract under renegotiation</p>")

        html = client.get(supplier.get_absolute_url()).content.decode()

        assert "Ada Martin" in html
        assert "Contract under renegotiation" in html
        assert ">Active<" in html.replace("\n", "")

    def test_coordinates_nobody_filled_in_read_as_one_line(self, client, admin):
        supplier = SupplierFactory(website="", country="", address="")

        html = client.get(supplier.get_absolute_url()).content.decode()

        assert "Not filled in yet : Website, Country, Address." in html

    def test_the_empty_register_explains_and_offers_the_first_supplier(self, client, admin):
        html = client.get(reverse("assets:supplier-list")).content.decode()

        assert "No supplier yet." in html
        create = reverse("assets:supplier-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApi:
    def test_one_supplier_carries_its_completeness_and_a_list_does_not(self, admin):
        supplier = SupplierFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/assets/suppliers/{supplier.pk}/").json()
        one = one.get("data", one)
        many = api.get("/api/v1/assets/suppliers/").json()
        rows = many.get("data", many.get("results", many))

        assert one["completeness"]["complete"] is False
        assert [item["key"] for item in one["completeness"]["missing"]] == ["contact", "country", "dependencies"]
        assert all(item["blocking"] is False for item in one["completeness"]["missing"])
        assert rows and "completeness" not in rows[0]

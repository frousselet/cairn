"""Address field (plain autocomplete input) + coordinates + Leaflet map display."""

import re
from urllib.parse import urlparse

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.tests.factories import SupplierFactory

HX = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.mark.django_db
class TestSupplierAddressField:
    def test_address_is_autocomplete_input_not_richtext(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory()
        html = client.get(reverse("assets:supplier-update", kwargs={"pk": s.pk}), **HX).content.decode()
        # A single-line input wired for address autocomplete...
        assert re.search(r'<input[^>]*name="address"[^>]*data-address-autocomplete', html) \
            or re.search(r'<input[^>]*data-address-autocomplete[^>]*name="address"', html)
        # ...never a <textarea> (which the global script upgrades to a pell editor).
        assert '<textarea name="address"' not in html

    def test_modal_dropped_contact_and_contract_fields(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory()
        html = client.get(reverse("assets:supplier-update", kwargs={"pk": s.pk}), **HX).content.decode()
        for f in ["contact_name", "contact_email", "contact_phone",
                  "contract_reference", "contract_start_date", "contract_end_date"]:
            assert f'name="{f}"' not in html, f

    def test_coordinates_persist_via_form(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory()
        resp = client.post(
            reverse("assets:supplier-update", kwargs={"pk": s.pk}),
            {
                "name": s.name, "owner": str(s.owner_id), "criticality": s.criticality,
                "status": s.status, "address": "17 Rue de Surene, 75008 Paris",
                "latitude": "48.8709", "longitude": "2.3199",
            },
            **HX,
        )
        assert resp.status_code in (204, 302), getattr(resp, "content", b"")
        s.refresh_from_db()
        assert s.latitude == pytest.approx(48.8709)
        assert s.longitude == pytest.approx(2.3199)


@pytest.mark.django_db
class TestSupplierMap:
    def test_map_rendered_with_coords(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory(address="17 Rue de Surene", latitude=48.87, longitude=2.32)
        html = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk})).content.decode()
        assert 'id="supplier-map"' in html
        assert 'data-lat="48.87"' in html and 'data-lon="2.32"' in html
        assert "leaflet@1.9.4/dist/leaflet.js" in html
        urls = re.findall(r'https?://[^\s"\'<>]+', html)
        assert any(urlparse(u).hostname == "basemaps.cartocdn.com" for u in urls)

    def test_no_map_without_address_or_coords(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory(address="", latitude=None, longitude=None)
        html = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk})).content.decode()
        assert 'id="supplier-map"' not in html

    def test_overview_bento_structure(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory(address="17 Rue de Surene", country="France",
                            latitude=48.87, longitude=2.32)
        html = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk})).content.decode()
        # Merged two-column bento: icon-led info column + map column with the map inside it.
        assert "supplier-overview" in html
        assert "supplier-overview__info" in html
        assert "supplier-card__map" in html  # map is now a hero background of the card
        assert "ov-row__icon" in html
        # Icon-only rows carry their name on the wrapper (no text label kept).
        assert 'role="group" aria-label="Address"' in html
        assert 'class="supplier-overview"' in html  # has a map -> full bento, no --nomap modifier

    def test_overview_nomap_is_plain_block(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory(address="", country="", website="",
                            latitude=None, longitude=None, description="x")
        html = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk})).content.decode()
        assert 'class="supplier-overview supplier-overview--nomap"' in html
        assert 'id="supplier-map"' not in html

    def test_coords_exposed_in_api(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory(latitude=48.87, longitude=2.32)
        resp = client.get(f"/api/v1/assets/suppliers/{s.pk}/")
        assert resp.status_code == 200
        data = resp.json()
        payload = data["data"] if isinstance(data, dict) and "data" in data else data
        assert payload["latitude"] == pytest.approx(48.87)
        assert payload["longitude"] == pytest.approx(2.32)

"""Tests for SupplierContact: model, CRUD views (HTMX drawer), API and display."""

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.forms import SupplierContactForm
from assets.models import SupplierContact
from assets.tests.factories import SupplierFactory

HX = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.mark.django_db
class TestSupplierContactModel:
    def test_str_and_ordering(self):
        s = SupplierFactory()
        SupplierContact.objects.create(supplier=s, name="Zoe")
        SupplierContact.objects.create(supplier=s, name="Adam")
        names = list(s.contacts.values_list("name", flat=True))
        assert names == ["Adam", "Zoe"]  # Meta.ordering = ["name"]
        assert str(SupplierContact(name="Adam")) == "Adam"

    def test_cascade_delete_with_supplier(self):
        s = SupplierFactory()
        SupplierContact.objects.create(supplier=s, name="Bob")
        s.delete()
        assert SupplierContact.objects.count() == 0


@pytest.mark.django_db
class TestSupplierContactForm:
    def test_is_multistep_with_side_arrows(self):
        # The "new modal standard" => multi-step => floating side arrows, no footer.
        assert SupplierContactForm().is_multistep is True

    def test_covers_all_fields(self):
        f = SupplierContactForm()
        covered = {n for step in f.steps for n in step.field_names()}
        assert covered == {"name", "profession", "service", "email", "phone", "role"}


@pytest.mark.django_db
class TestSupplierContactViews:
    def _login(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))

    def test_create_via_drawer_returns_204_and_persists(self, client):
        self._login(client)
        s = SupplierFactory()
        url = reverse("assets:supplier-contact-create", kwargs={"supplier_pk": s.pk})
        resp = client.post(url, {"name": "Alice", "role": "Primary"}, **HX)
        assert resp.status_code == 204
        assert resp.headers["HX-Trigger"] == "formSaved"
        ct = s.contacts.get()
        assert ct.name == "Alice" and ct.role == "Primary"

    def test_update(self, client):
        self._login(client)
        s = SupplierFactory()
        ct = SupplierContact.objects.create(supplier=s, name="Old")
        url = reverse("assets:supplier-contact-update", kwargs={"pk": ct.pk})
        resp = client.post(url, {"name": "New", "email": "n@e.test"}, **HX)
        assert resp.status_code == 204
        ct.refresh_from_db()
        assert ct.name == "New" and ct.email == "n@e.test"

    def test_delete_via_drawer(self, client):
        self._login(client)
        s = SupplierFactory()
        ct = SupplierContact.objects.create(supplier=s, name="Gone")
        url = reverse("assets:supplier-contact-delete", kwargs={"pk": ct.pk})
        resp = client.post(url, **HX)
        assert resp.status_code == 204
        assert resp.headers["HX-Trigger"] == "formSaved"
        assert not SupplierContact.objects.filter(pk=ct.pk).exists()

    def test_detail_renders_contact_with_tel_link(self, client):
        self._login(client)
        s = SupplierFactory()
        SupplierContact.objects.create(supplier=s, name="Bob", phone="+33 1 02 03 04 05")
        html = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk})).content.decode()
        assert "tel:+33 1 02 03 04 05" in html
        assert "Add contact" in html


@pytest.mark.django_db
class TestSupplierContactAPI:
    def test_create_and_list(self, client):
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory()
        create = client.post(
            "/api/v1/assets/supplier-contacts/",
            {"supplier": str(s.pk), "name": "Carol", "email": "carol@e.test"},
            content_type="application/json",
        )
        assert create.status_code == 201, create.content
        listing = client.get(f"/api/v1/assets/supplier-contacts/?supplier={s.pk}")
        assert listing.status_code == 200
        names = [c["name"] for c in listing.json()["data"]]
        assert "Carol" in names

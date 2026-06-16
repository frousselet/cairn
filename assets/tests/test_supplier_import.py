"""End-to-end tests for the supplier CSV import wizard (upload/preview/confirm)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.models import Supplier

pytestmark = pytest.mark.django_db

HEADER = (
    "name,owner,type,criticality,status,description,contact_name,contact_email,"
    "contact_phone,website,address,country,contract_reference,contract_start_date,"
    "contract_end_date,notes,scopes,tags,created_at"
)


@pytest.fixture
def superuser():
    return UserFactory(is_superuser=True)


@pytest.fixture
def client(superuser):
    c = Client()
    c.force_login(superuser)
    return c


def _upload(text="acme.csv"):
    body = f"{HEADER}\nAcme,,,high,active,,,,,,,,,,,,,\n".encode("utf-8")
    return SimpleUploadedFile("acme.csv", body, content_type="text/csv")


class TestImportForm:
    def test_full_page_get_returns_200(self, client):
        resp = client.get(reverse("imports:import", args=["supplier"]))
        assert resp.status_code == 200
        assert b"sample" in resp.content.lower()

    def test_htmx_drawer_get_uses_modal_template(self, client):
        resp = client.get(
            reverse("imports:import", args=["supplier"]),
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="drawer-form-content",
        )
        assert resp.status_code == 200
        assert "imports/import_modal.html" in [t.name for t in resp.templates]

    def test_unknown_entity_is_404(self, client):
        resp = client.get(reverse("imports:import", args=["widget"]))
        assert resp.status_code == 404

    def test_non_csv_is_rejected(self, client):
        bad = SimpleUploadedFile("x.txt", b"name\nAcme\n", content_type="text/plain")
        resp = client.post(reverse("imports:import", args=["supplier"]), {"file": bad})
        assert resp.status_code == 200  # re-renders with errors
        assert b".csv" in resp.content


class TestSampleDownload:
    def test_sample_is_csv_attachment(self, client):
        resp = client.get(reverse("imports:import-sample", args=["supplier"]))
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/csv")
        assert "sample_supplier.csv" in resp["Content-Disposition"]


class TestWizardFlow:
    def test_upload_redirects_to_preview_and_fills_session(self, client):
        resp = client.post(
            reverse("imports:import", args=["supplier"]), {"file": _upload()}
        )
        assert resp.status_code == 302
        assert resp.url == reverse("imports:import-preview", args=["supplier"])
        assert client.session["entity_import"]["entity"] == "supplier"
        assert len(client.session["entity_import"]["valid"]) == 1

    def test_preview_without_session_redirects(self, client):
        resp = client.get(reverse("imports:import-preview", args=["supplier"]))
        assert resp.status_code == 302
        assert resp.url == reverse("imports:import", args=["supplier"])

    def test_preview_shows_counts(self, client):
        client.post(reverse("imports:import", args=["supplier"]), {"file": _upload()})
        resp = client.get(reverse("imports:import-preview", args=["supplier"]))
        assert resp.status_code == 200
        assert resp.context["valid_count"] == 1

    def test_confirm_creates_suppliers_and_clears_session(self, client):
        client.post(reverse("imports:import", args=["supplier"]), {"file": _upload()})
        resp = client.post(reverse("imports:import-preview", args=["supplier"]))
        assert resp.status_code == 302
        assert resp.url == reverse("assets:supplier-list")
        assert Supplier.objects.filter(name="Acme").exists()
        assert "entity_import" not in client.session

    def test_preview_shows_replace_all_when_conflicts(self, client, superuser):
        from assets.tests.factories import SupplierFactory

        SupplierFactory(name="Acme")
        client.post(reverse("imports:import", args=["supplier"]), {"file": _upload()})
        resp = client.get(reverse("imports:import-preview", args=["supplier"]))
        assert resp.context["conflict_count"] == 1
        assert b'id="replace-all"' in resp.content

    def test_existing_name_kept_when_replace_unchecked(self, client, superuser):
        from assets.tests.factories import SupplierFactory

        SupplierFactory(name="Acme")
        client.post(reverse("imports:import", args=["supplier"]), {"file": _upload()})
        # Confirm without ticking "replace" -> the row is skipped, no duplicate.
        client.post(reverse("imports:import-preview", args=["supplier"]))
        assert Supplier.objects.filter(name="Acme").count() == 1

    def test_existing_name_updated_when_replace_checked(self, client, superuser):
        from assets.tests.factories import SupplierFactory

        existing = SupplierFactory(name="Acme", criticality="low")
        client.post(reverse("imports:import", args=["supplier"]), {"file": _upload()})
        # The uploaded row (row 2) carries criticality=high; tick replace.
        client.post(
            reverse("imports:import-preview", args=["supplier"]), {"replace": "2"}
        )
        assert Supplier.objects.filter(name="Acme").count() == 1
        existing.refresh_from_db()
        assert existing.criticality == "high"


class TestPermissions:
    def test_anonymous_redirected_to_login(self):
        resp = Client().get(reverse("imports:import", args=["supplier"]))
        assert resp.status_code in (302, 403)

    def test_user_without_create_permission_forbidden(self):
        c = Client()
        c.force_login(UserFactory())  # no permissions granted
        resp = c.get(reverse("imports:import", args=["supplier"]))
        assert resp.status_code == 403

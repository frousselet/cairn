import pytest
from django.test import Client

from accounts.tests.factories import UserFactory
from compliance.tests.factories import FrameworkFactory
from trust_center.models import TrustCenterCertification, TrustCenterSettings

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    client = Client()
    client.force_login(UserFactory(is_superuser=True))
    return client


def test_hub_requires_authentication():
    resp = Client().get("/trust-center/manage/")
    assert resp.status_code in (302, 403)


def test_hub_renders(admin_client):
    assert admin_client.get("/trust-center/manage/").status_code == 200


def test_settings_update(admin_client):
    resp = admin_client.post(
        "/trust-center/manage/settings/",
        {
            "headline": "Our security",
            "theme_accent": "#1e3a8a",
            "is_published": "on",
            "show_compliance_percentages": "on",
            "intro": "",
            "contact_email": "",
            "custom_domain": "",
        },
    )
    assert resp.status_code == 302
    settings_obj = TrustCenterSettings.get()
    assert settings_obj.headline == "Our security"
    assert settings_obj.is_published is True


def test_create_certification_via_ui(admin_client):
    fw = FrameworkFactory()
    resp = admin_client.post(
        "/trust-center/manage/certification/add/",
        {
            "framework": str(fw.pk),
            "public_label": "ISO 27001",
            "public_description": "",
            "show_percentage": "on",
            "display_order": "0",
        },
    )
    assert resp.status_code == 302
    cert = TrustCenterCertification.objects.get(public_label="ISO 27001")
    assert cert.created_by is not None


def test_detail_renders_stepper(admin_client):
    fw = FrameworkFactory()
    cert = TrustCenterCertification.objects.create(
        framework=fw, public_label="X", created_by=UserFactory()
    )
    resp = admin_client.get(f"/trust-center/manage/certification/{cert.pk}/")
    assert resp.status_code == 200
    assert b"stepper" in resp.content.lower()


def test_unknown_entity_returns_404(admin_client):
    assert admin_client.get("/trust-center/manage/bogus/add/").status_code == 404

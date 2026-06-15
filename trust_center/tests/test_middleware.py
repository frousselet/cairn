import pytest
from django.test import Client, override_settings

from trust_center.models import TrustCenterSettings

pytestmark = pytest.mark.django_db

TRUST = "trust.testserver"


def _enable():
    settings_obj = TrustCenterSettings.get()
    settings_obj.is_published = True
    settings_obj.headline = "Our posture"
    settings_obj.save()


@override_settings(TRUST_CENTER_HOST="")
def test_no_isolation_when_host_unset():
    # The internal app stays reachable (redirect to login), not 404'd.
    assert Client().get("/admin/").status_code != 404


@override_settings(TRUST_CENTER_HOST=TRUST, ALLOWED_HOSTS=["testserver", TRUST])
def test_public_host_blocks_internal_app():
    _enable()
    client = Client()
    assert client.get("/admin/", HTTP_HOST=TRUST).status_code == 404
    assert client.get("/api/v1/context/scopes/", HTTP_HOST=TRUST).status_code == 404
    assert client.get("/trust-center/manage/", HTTP_HOST=TRUST).status_code == 404


@override_settings(TRUST_CENTER_HOST=TRUST, ALLOWED_HOSTS=["testserver", TRUST])
def test_public_host_serves_trust_center():
    _enable()
    client = Client()
    assert client.get("/trust/", HTTP_HOST=TRUST).status_code == 200
    root = client.get("/", HTTP_HOST=TRUST)
    assert root.status_code == 200
    assert b"Our posture" in root.content


@override_settings(TRUST_CENTER_HOST=TRUST, ALLOWED_HOSTS=["testserver", TRUST])
def test_main_host_unaffected():
    _enable()
    client = Client()
    # On the main host the app is reachable and /trust/ also works.
    assert client.get("/admin/").status_code != 404
    assert client.get("/trust/").status_code == 200

import pytest
from django.test import Client
from rest_framework.test import APIClient

from trust_center.constants import DocumentAccess
from trust_center.models import TrustCenterSettings
from trust_center.tests.factories import (
    TrustCenterCertificationFactory,
    TrustCenterDocumentFactory,
    publish,
    validate_framework,
)

pytestmark = pytest.mark.django_db


def _enable():
    settings_obj = TrustCenterSettings.get()
    settings_obj.is_published = True
    settings_obj.headline = "Our security posture"
    settings_obj.save()
    return settings_obj


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload.keys()) == {"status", "data"}:
        return payload["data"]
    return payload


# --- Public API -------------------------------------------------------------


def test_api_overview_404_when_kill_switch_off():
    assert APIClient().get("/trust/api/").status_code == 404


def test_api_overview_anonymous_access_when_published():
    _enable()
    cert = publish(TrustCenterCertificationFactory())
    validate_framework(cert.framework)
    resp = APIClient().get("/trust/api/")
    assert resp.status_code == 200
    data = _unwrap(resp.data)
    assert len(data["certifications"]) == 1
    assert data["certifications"][0]["label"] == cert.public_label


def test_api_hides_unpublished_and_invalid_source():
    _enable()
    # Published entry whose framework is still draft -> excluded.
    publish(TrustCenterCertificationFactory())
    # Draft entry whose framework is validated -> excluded.
    validate_framework(TrustCenterCertificationFactory().framework)
    resp = APIClient().get("/trust/api/")
    assert _unwrap(resp.data)["certifications"] == []


# --- Public web page --------------------------------------------------------


def test_landing_404_when_off():
    assert Client().get("/trust/").status_code == 404


def test_landing_renders_headline_when_published():
    _enable()
    resp = Client().get("/trust/")
    assert resp.status_code == 200
    assert b"Our security posture" in resp.content


# --- Public document download ----------------------------------------------


def test_public_document_downloads():
    _enable()
    doc = publish(TrustCenterDocumentFactory())
    resp = Client().get(f"/trust/documents/{doc.id}/download/")
    assert resp.status_code == 200
    assert resp["Content-Disposition"].startswith("attachment")
    assert resp.content == b"%PDF-1.4 test content"


def test_gated_document_not_downloadable_via_public_url():
    _enable()
    doc = publish(TrustCenterDocumentFactory(access=DocumentAccess.GATED))
    resp = Client().get(f"/trust/documents/{doc.id}/download/")
    assert resp.status_code == 404

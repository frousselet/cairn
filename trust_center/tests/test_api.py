import pytest
from rest_framework.test import APIClient

from accounts.models import Group
from accounts.tests.factories import UserFactory
from trust_center.tests.factories import TrustCenterCertificationFactory

pytestmark = pytest.mark.django_db


def _detail(resp):
    data = resp.data
    if isinstance(data, dict) and set(data.keys()) == {"status", "error"}:
        data = data["error"]
    return str(data)


def test_api_transition_illegal_returns_controlled_message():
    client = APIClient()
    client.force_authenticate(UserFactory(is_superuser=True))
    cert = TrustCenterCertificationFactory()  # starts in draft
    resp = client.post(
        f"/api/v1/trust-center/certifications/{cert.id}/transition/",
        {"target_state": "unpublished"},  # not reachable from draft
        format="json",
    )
    assert resp.status_code == 400
    blob = _detail(resp)
    # A safe, fixed message - never the raw workflow exception string.
    assert "Cannot transition" not in blob
    assert "not allowed" in blob.lower()


def test_api_transition_permission_denied_is_controlled():
    user = UserFactory()  # Contributeur: has .update but not .approve
    Group.objects.get(name="Contributeur").users.add(user)
    client = APIClient()
    client.force_authenticate(user)
    cert = TrustCenterCertificationFactory()
    resp = client.post(
        f"/api/v1/trust-center/certifications/{cert.id}/transition/",
        {"target_state": "published"},  # publishing requires the approve action
        format="json",
    )
    assert resp.status_code == 403
    assert "permission" in _detail(resp).lower()

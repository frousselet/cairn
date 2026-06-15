import json

import pytest
from django.core import mail, signing
from django.test import Client, override_settings

from accounts.models import Group, Notification
from accounts.tests.factories import UserFactory
from mcp.server import McpServer
from mcp.tools import register_all_tools
from trust_center.constants import DocumentRequestState
from trust_center.models import DocumentRequest, TrustCenterSettings
from trust_center.tests.factories import (
    DocumentRequestFactory,
    GatedDocumentFactory,
    publish,
)

pytestmark = pytest.mark.django_db


def _enable():
    s = TrustCenterSettings.get()
    s.is_published = True
    s.save()
    return s


def _approver():
    user = UserFactory()
    Group.objects.get(name="Administrateur").users.add(user)
    return user


# --- Public request flow ----------------------------------------------------


def test_request_form_creates_pending_and_notifies():
    _enable()
    _approver()
    doc = publish(GatedDocumentFactory())
    resp = Client().post(
        f"/trust/documents/{doc.id}/request/",
        {
            "requester_name": "Jane Doe",
            "email": "jane@example.test",
            "company": "ACME",
            "reason": "Due diligence",
            "nda_accepted": "on",
        },
    )
    assert resp.status_code == 200
    req = DocumentRequest.objects.get(email="jane@example.test")
    assert req.workflow_state == DocumentRequestState.PENDING
    assert req.nda_accepted and req.nda_accepted_at is not None
    assert Notification.objects.filter(
        notification_type="trust_document_requested"
    ).exists()


def test_request_requires_nda_when_document_requires_it():
    _enable()
    doc = publish(GatedDocumentFactory(requires_nda=True))
    resp = Client().post(
        f"/trust/documents/{doc.id}/request/",
        {"requester_name": "Jane", "email": "j@example.test"},
    )
    assert resp.status_code == 200
    assert DocumentRequest.objects.count() == 0  # rejected by NDA validation


def test_request_honeypot_blocks_bot():
    _enable()
    doc = publish(GatedDocumentFactory(requires_nda=False))
    resp = Client().post(
        f"/trust/documents/{doc.id}/request/",
        {"requester_name": "Bot", "email": "bot@example.test", "website": "spam"},
    )
    assert resp.status_code == 200
    assert DocumentRequest.objects.count() == 0


def test_request_deduplicates_pending():
    _enable()
    doc = publish(GatedDocumentFactory(requires_nda=False))
    payload = {"requester_name": "Jane", "email": "dup@example.test"}
    Client().post(f"/trust/documents/{doc.id}/request/", payload)
    Client().post(f"/trust/documents/{doc.id}/request/", payload)
    assert DocumentRequest.objects.filter(email="dup@example.test").count() == 1


def test_request_form_404_for_public_document():
    _enable()
    from trust_center.tests.factories import TrustCenterDocumentFactory

    doc = publish(TrustCenterDocumentFactory())  # PUBLIC
    assert Client().get(f"/trust/documents/{doc.id}/request/").status_code == 404


# --- Approve -> signed link -> download -------------------------------------


def test_approve_issues_link_and_download_works():
    _enable()
    req = DocumentRequestFactory()
    publish(req.document)
    admin = UserFactory(is_superuser=True)
    client = Client()
    client.force_login(admin)

    resp = client.post(
        f"/trust-center/manage/requests/{req.id}/transition/",
        {"target_status": DocumentRequestState.APPROVED},
    )
    assert resp.status_code == 302
    req.refresh_from_db()
    assert req.workflow_state == DocumentRequestState.APPROVED
    assert req.download_link_expires_at is not None
    assert len(mail.outbox) == 1
    assert req.email in mail.outbox[0].to

    token = req.make_download_token()
    dl = Client().get(f"/trust/documents/download/{token}/")
    assert dl.status_code == 200
    assert dl["Content-Disposition"].startswith("attachment")
    req.refresh_from_db()
    assert req.download_count == 1


def test_download_rejects_tampered_token():
    _enable()
    req = DocumentRequestFactory(workflow_state=DocumentRequestState.APPROVED)
    publish(req.document)
    token = req.make_download_token() + "tampered"
    assert Client().get(f"/trust/documents/download/{token}/").status_code == 404


@override_settings(TRUST_CENTER_DOWNLOAD_TTL=-1)
def test_download_rejects_expired_token():
    _enable()
    req = DocumentRequestFactory(workflow_state=DocumentRequestState.APPROVED)
    publish(req.document)
    token = req.make_download_token()
    resp = Client().get(f"/trust/documents/download/{token}/")
    assert resp.status_code == 410


def test_download_blocked_after_document_unpublished():
    _enable()
    req = DocumentRequestFactory(workflow_state=DocumentRequestState.APPROVED)
    publish(req.document)
    token = req.make_download_token()
    assert Client().get(f"/trust/documents/download/{token}/").status_code == 200
    # Taking the document down revokes outstanding approved links too.
    req.document.workflow_state = "draft"
    req.document.save()
    assert Client().get(f"/trust/documents/download/{token}/").status_code == 404


def test_download_rejected_after_revoke():
    _enable()
    req = DocumentRequestFactory(workflow_state=DocumentRequestState.APPROVED)
    publish(req.document)
    token = req.make_download_token()
    # Revoke: approved -> rejected
    req.workflow_state = DocumentRequestState.REJECTED
    req.save()
    assert Client().get(f"/trust/documents/download/{token}/").status_code == 404


def test_token_validates_via_resolve():
    req = DocumentRequestFactory()
    token = req.make_download_token()
    resolved = DocumentRequest.resolve_token(token, max_age=600)
    assert resolved == req
    with pytest.raises(signing.BadSignature):
        DocumentRequest.resolve_token(token + "x", max_age=600)


# --- MCP approve / reject ---------------------------------------------------


def _call(srv, user, name, arguments):
    result = srv.handle_request(
        json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": name, "arguments": arguments}}
        ),
        user,
    )
    return json.loads(result["result"]["content"][0]["text"])


def test_mcp_approve_and_reject():
    srv = McpServer()
    register_all_tools(srv)
    admin = UserFactory(is_superuser=True)

    req = DocumentRequestFactory()
    out = _call(srv, admin, "approve_trust_center_document_request", {"id": str(req.id)})
    assert out["workflow_state"] == "approved"
    assert len(mail.outbox) == 1

    req2 = DocumentRequestFactory()
    out2 = _call(
        srv, admin, "reject_trust_center_document_request",
        {"id": str(req2.id), "comment": "Out of scope"},
    )
    assert out2["workflow_state"] == "rejected"

    # reject without comment is refused (workflow requires a comment)
    req3 = DocumentRequestFactory()
    out3 = _call(
        srv, admin, "reject_trust_center_document_request",
        {"id": str(req3.id), "comment": ""},
    )
    assert "error" in json.dumps(out3).lower()

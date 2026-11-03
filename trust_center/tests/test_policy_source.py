# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A Trust Center document sourced from a governed document (RG-TC-18,
RG-TC-08 second gate, RG-DOC-20, RG-DOC-21)."""

import hashlib
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from assets.constants import DataClassification
from documents.constants import POLICY_RETIRED, VERSION_SUPERSEDED
from documents.tests.factories import PolicyFactory, PolicyVersionFactory, put_in_force
from trust_center.api.serializers import PublicDocumentSerializer
from trust_center.forms import DocumentForm
from trust_center.models import TrustCenterDocument, TrustCenterSettings
from trust_center.tests.factories import TrustCenterDocumentFactory, publish

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4\n% signed copy\n"


def _public_policy(with_pdf=True, **kwargs):
    kwargs.setdefault("classification", DataClassification.PUBLIC)
    version = PolicyVersionFactory(policy=PolicyFactory(**kwargs), version_label="1.0")
    if with_pdf:
        version.set_pdf(PDF, "infosec-policy.pdf")
        version.save()
    put_in_force(version)
    policy = version.policy
    policy.refresh_from_db()
    return policy


def _policy_doc(policy, **kwargs):
    doc = TrustCenterDocument(title="Information security policy", policy=policy, **kwargs)
    doc.full_clean()
    doc.save()
    return doc


def _enable():
    settings_obj = TrustCenterSettings.get()
    settings_obj.is_published = True
    settings_obj.save()


class TestOneSourceInvariant:
    def test_policy_alone_is_a_valid_source(self):
        _policy_doc(_public_policy())

    def test_policy_and_inline_file_are_refused(self):
        doc = TrustCenterDocument(title="x", policy=_public_policy(), file_content=b"%PDF-1.4")
        with pytest.raises(ValidationError):
            doc.clean()

    def test_no_source_is_refused(self):
        with pytest.raises(ValidationError):
            TrustCenterDocument(title="x").clean()

    def test_only_a_public_document_can_be_a_source(self):
        internal = _public_policy(classification=DataClassification.INTERNAL)
        with pytest.raises(ValidationError) as exc:
            TrustCenterDocument(title="x", policy=internal).clean()
        assert "policy" in exc.value.message_dict

    def test_a_new_link_needs_a_linkable_document(self):
        draft = PolicyFactory(classification=DataClassification.PUBLIC)
        with pytest.raises(ValidationError):
            TrustCenterDocument(title="x", policy=draft).clean()

    def test_an_existing_link_survives_the_document_being_retired(self):
        policy = _public_policy()
        doc = _policy_doc(policy)
        policy.transition_to(POLICY_RETIRED, policy.owner, comment="Replaced")
        doc.refresh_from_db()
        doc.title = "Renamed"
        doc.full_clean()


class TestPublishedGate:
    def test_published_while_the_document_has_a_version_in_force(self):
        doc = publish(_policy_doc(_public_policy()))
        assert list(TrustCenterDocument.objects.published()) == [doc]

    def test_disappears_when_the_version_is_withdrawn(self):
        policy = _public_policy()
        doc = publish(_policy_doc(policy))
        policy.version_in_force.transition_to(VERSION_SUPERSEDED, policy.owner, comment="Withdrawn")
        assert doc not in TrustCenterDocument.objects.published()

    def test_disappears_when_the_document_is_retired(self):
        policy = _public_policy()
        doc = publish(_policy_doc(policy))
        policy.transition_to(POLICY_RETIRED, policy.owner, comment="Retired")
        assert doc not in TrustCenterDocument.objects.published()

    def test_disappears_when_the_document_is_reclassified(self):
        policy = _public_policy()
        doc = publish(_policy_doc(policy))
        policy.classification = DataClassification.INTERNAL
        policy.save()
        assert doc not in TrustCenterDocument.objects.published()

    def test_inline_documents_are_unaffected(self):
        doc = publish(TrustCenterDocumentFactory())
        assert doc in TrustCenterDocument.objects.published()


class TestServesTheVersionInForce:
    def test_serves_the_attached_pdf(self):
        doc = _policy_doc(_public_policy())
        assert doc.get_file_bytes() == PDF
        assert doc.effective_file_name == "infosec-policy.pdf"
        assert doc.effective_content_type == "application/pdf"
        assert doc.file_icon

    def test_follows_the_new_version_in_force(self):
        policy = _public_policy()
        doc = _policy_doc(policy)
        new = policy.new_version(policy.owner, bump="major")
        new.clear_pdf()
        new.set_pdf(b"%PDF-1.7\n% v2\n", "infosec-policy-v2.pdf")
        new.change_summary = "Second edition."
        new.save()
        put_in_force(new, policy.owner)
        assert doc.get_file_bytes() == b"%PDF-1.7\n% v2\n"
        assert doc.effective_file_name == "infosec-policy-v2.pdf"

    def test_renders_the_rich_text_when_no_pdf_is_attached(self):
        policy = _public_policy(with_pdf=False)
        doc = _policy_doc(policy)
        with mock.patch("documents.rendering.render_version_pdf", return_value=b"%PDF-rendered") as render:
            assert doc.get_file_bytes() == b"%PDF-rendered"
        render.assert_called_once()
        assert doc.effective_file_name == f"{policy.reference}-v1.0.pdf"

    def test_public_download_streams_the_version_in_force(self):
        _enable()
        doc = publish(_policy_doc(_public_policy()))
        resp = Client().get(f"/trust/documents/{doc.id}/download/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert resp.content == PDF
        assert hashlib.sha256(resp.content).hexdigest() == doc.policy.version_in_force.file_sha256

    def test_public_download_404_once_withdrawn(self):
        _enable()
        policy = _public_policy()
        doc = publish(_policy_doc(policy))
        policy.version_in_force.transition_to(VERSION_SUPERSEDED, policy.owner, comment="Withdrawn")
        assert Client().get(f"/trust/documents/{doc.id}/download/").status_code == 404


class TestSurfaces:
    def test_public_serializer_exposes_nothing_internal(self):
        doc = publish(_policy_doc(_public_policy()))
        data = PublicDocumentSerializer(doc).data
        assert set(data) == {"id", "title", "description", "access", "requires_nda"}

    def test_public_api_lists_it_without_policy_fields(self):
        _enable()
        doc = publish(_policy_doc(_public_policy()))
        body = APIClient().get("/trust/api/documents/").json()
        rows = body.get("data", body) if isinstance(body, dict) else body
        if isinstance(rows, dict):
            rows = rows.get("results", rows)
        assert any(r["id"] == str(doc.id) for r in rows)
        flat = str(rows)
        assert doc.policy.reference not in flat
        assert "owner" not in flat

    def test_form_offers_active_public_documents_only(self):
        public = _public_policy()
        internal = _public_policy(classification=DataClassification.INTERNAL)
        draft = PolicyFactory(classification=DataClassification.PUBLIC)
        choices = set(DocumentForm().fields["policy"].queryset)
        assert public in choices
        assert internal not in choices and draft not in choices

    def test_form_creates_a_policy_sourced_entry(self):
        policy = _public_policy()
        form = DocumentForm(data={
            "title": "Policy", "description": "", "access": "public",
            "policy": str(policy.pk), "display_order": 0,
        })
        assert form.is_valid(), form.errors
        doc = form.save(commit=False)
        doc.created_by = UserFactory()
        doc.save()
        assert doc.policy == policy and not doc.file_content

    def test_management_api_accepts_a_policy_source(self):
        client = APIClient()
        client.force_authenticate(UserFactory(is_superuser=True))
        policy = _public_policy()
        resp = client.post("/api/v1/trust-center/documents/", {
            "title": "Policy", "access": "public", "policy": str(policy.pk),
        }, format="json")
        assert resp.status_code == 201, resp.content
        internal = _public_policy(classification=DataClassification.INTERNAL)
        resp = client.post("/api/v1/trust-center/documents/", {
            "title": "Policy", "access": "public", "policy": str(internal.pk),
        }, format="json")
        assert resp.status_code == 400

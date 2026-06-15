import pytest

from trust_center.api.serializers import (
    PublicCertificationSerializer,
    PublicDocumentSerializer,
    PublicMeasureSerializer,
    PublicSubprocessorSerializer,
)
from trust_center.tests.factories import (
    TrustCenterCertificationFactory,
    TrustCenterDocumentFactory,
    TrustCenterMeasureFactory,
    TrustCenterSubprocessorFactory,
)

pytestmark = pytest.mark.django_db


def test_certification_serializer_field_whitelist():
    cert = TrustCenterCertificationFactory()
    data = PublicCertificationSerializer(cert).data
    assert set(data.keys()) == {"label", "description", "compliance_level", "logo"}


def test_subprocessor_serializer_hides_internal_supplier_fields():
    sub = TrustCenterSubprocessorFactory()
    sub.supplier.contact_email = "secret@vendor.test"
    sub.supplier.contract_reference = "CONTRACT-123"
    sub.supplier.notes = "internal only"
    sub.supplier.save()
    data = PublicSubprocessorSerializer(sub).data
    assert set(data.keys()) == {"name", "purpose", "country", "website", "logo"}
    blob = str(data)
    for leaked in ("secret@vendor.test", "CONTRACT-123", "internal only"):
        assert leaked not in blob


def test_measure_serializer_field_whitelist():
    measure = TrustCenterMeasureFactory()
    data = PublicMeasureSerializer(measure).data
    assert set(data.keys()) == {"title", "description", "icon", "category"}


def test_document_serializer_field_whitelist_excludes_bytes():
    doc = TrustCenterDocumentFactory()
    data = PublicDocumentSerializer(doc).data
    assert set(data.keys()) == {"id", "title", "description", "access", "requires_nda"}
    assert "file_content" not in str(data)


def test_certification_logo_is_sanitized():
    cert = TrustCenterCertificationFactory()
    cert.framework.logo_64 = (
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script>'
        '<rect width="4" height="4"/></svg>'
    )
    cert.framework.save()
    data = PublicCertificationSerializer(cert).data
    assert "script" not in data["logo"].lower()
    assert "rect" in data["logo"].lower()

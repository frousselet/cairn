import factory

from assets.tests.factories import SupplierFactory
from compliance.tests.factories import FrameworkFactory
from trust_center.constants import DocumentAccess, PublicationState
from trust_center.models import (
    DocumentRequest,
    TrustCenterCertification,
    TrustCenterDocument,
    TrustCenterMeasure,
    TrustCenterSubprocessor,
)


def validate_framework(framework):
    """Move a framework into a reportable (validated) state for gate tests."""
    framework.workflow_state = "validated"
    framework.is_approved = True
    framework.save()
    return framework


def validate_supplier(supplier):
    supplier.workflow_state = "validated"
    supplier.is_approved = True
    supplier.save()
    return supplier


class TrustCenterCertificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrustCenterCertification

    framework = factory.SubFactory(FrameworkFactory)
    public_label = factory.Sequence(lambda n: f"Certification {n}")


class TrustCenterSubprocessorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrustCenterSubprocessor

    supplier = factory.SubFactory(SupplierFactory)
    public_name = factory.Sequence(lambda n: f"Subprocessor {n}")


class TrustCenterMeasureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrustCenterMeasure

    title = factory.Sequence(lambda n: f"Measure {n}")


class TrustCenterDocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrustCenterDocument

    title = factory.Sequence(lambda n: f"Document {n}")
    access = DocumentAccess.PUBLIC
    file_name = "policy.pdf"
    content_type = "application/pdf"
    file_content = b"%PDF-1.4 test content"


class GatedDocumentFactory(TrustCenterDocumentFactory):
    access = DocumentAccess.GATED
    requires_nda = True


class DocumentRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentRequest

    document = factory.SubFactory(GatedDocumentFactory)
    email = factory.Sequence(lambda n: f"requester{n}@example.test")
    requester_name = "Jane Doe"
    company = "ACME Corp"
    reason = "Vendor security review"


def publish(instance):
    """Move any publication-workflow entity into the live 'published' state."""
    instance.workflow_state = PublicationState.PUBLISHED
    instance.save()
    return instance

import pytest
from django.core.exceptions import ValidationError

from assets.constants import SupplierStatus
from core.lifecycle import TransitionNotAllowedError
from trust_center.constants import PublicationState
from trust_center.models import TrustCenterDocument, TrustCenterSettings
from trust_center.tests.factories import (
    TrustCenterCertificationFactory,
    TrustCenterDocumentFactory,
    TrustCenterMeasureFactory,
    TrustCenterSubprocessorFactory,
    publish,
    validate_framework,
    validate_supplier,
)

pytestmark = pytest.mark.django_db


def test_certification_dual_gate():
    cert = TrustCenterCertificationFactory()
    qs = type(cert).objects
    # Neither published nor source validated.
    assert qs.published().count() == 0
    # Published entry but draft framework: still hidden.
    publish(cert)
    assert qs.published().count() == 0
    # Validate the source: now visible.
    validate_framework(cert.framework)
    assert list(qs.published()) == [cert]
    # Un-validating the source auto-hides it (stale-publish protection).
    cert.framework.workflow_state = "draft"
    cert.framework.is_approved = False
    cert.framework.save()
    assert qs.published().count() == 0


def test_subprocessor_requires_active_validated_supplier():
    sub = TrustCenterSubprocessorFactory()
    publish(sub)
    assert type(sub).objects.published().count() == 0
    validate_supplier(sub.supplier)
    assert list(type(sub).objects.published()) == [sub]
    sub.supplier.status = SupplierStatus.SUSPENDED
    sub.supplier.save()
    assert type(sub).objects.published().count() == 0


def test_measure_published_only_needs_state():
    measure = TrustCenterMeasureFactory()
    assert type(measure).objects.published().count() == 0
    publish(measure)
    assert list(type(measure).objects.published()) == [measure]


def test_document_published_with_inline_content():
    doc = TrustCenterDocumentFactory()
    publish(doc)
    assert list(type(doc).objects.published()) == [doc]


def test_public_compliance_level_respects_toggles():
    cert = TrustCenterCertificationFactory(show_percentage=True)
    cert.framework.compliance_level = 87.4
    cert.framework.save()
    assert cert.public_compliance_level == 87
    cert.show_percentage = False
    assert cert.public_compliance_level is None
    cert.show_percentage = True
    settings_obj = TrustCenterSettings.get()
    settings_obj.show_compliance_percentages = False
    settings_obj.save()
    assert cert.public_compliance_level is None


def test_settings_is_singleton():
    first = TrustCenterSettings.get()
    first.headline = "Hello"
    first.save()
    second = TrustCenterSettings.get()
    assert first.pk == second.pk
    assert TrustCenterSettings.objects.count() == 1


def test_document_clean_requires_exactly_one_source():
    no_source = TrustCenterDocument(title="x")
    with pytest.raises(ValidationError):
        no_source.clean()


def test_publish_transition_requires_approve_permission():
    from accounts.models import Group
    from accounts.tests.factories import UserFactory

    cert = TrustCenterCertificationFactory()
    user = UserFactory()
    Group.objects.get(name="Contributeur").users.add(user)  # .update but not .approve

    with pytest.raises(TransitionNotAllowedError):
        cert.transition_to(
            PublicationState.PUBLISHED, user, enforce_permission=True
        )

    # Archiving a draft only needs update, which the user has.
    cert.transition_to(
        PublicationState.ARCHIVED, user, enforce_permission=True
    )
    assert cert.workflow_state == PublicationState.ARCHIVED

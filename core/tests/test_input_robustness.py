"""Robustness tests for assorted unhandled-exception entry points (#158).

Each endpoint below raised an unhandled exception on crafted GUI input,
returning HTTP 500 (or, for the WebSocket consumer, closing the socket with
code 1011). They are grouped here for triage, mirroring the issue.
"""

import asyncio

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _superuser_client():
    user = UserFactory(is_superuser=True, is_staff=True)
    client = Client()
    client.force_login(user)
    return client, user


# ── WebSocket dashboard consumer (core/consumers.py) ────────


@pytest.mark.parametrize("frame", ["123", "[1, 2, 3]", "null", "true", "1.5", '"hi"'])
def test_consumer_non_object_frame_is_ignored(frame):
    """A valid-JSON non-object frame must be ignored, not crash the socket."""
    from core.consumers import DashboardConsumer

    user = UserFactory(is_superuser=True)
    consumer = DashboardConsumer()
    consumer.scope = {"user": user}
    sent = []

    async def mock_send(text_data=None, bytes_data=None):
        sent.append(text_data)

    consumer.send = mock_send
    # Must not raise AttributeError (which would close the socket with 1011).
    asyncio.run(consumer.receive(text_data=frame))
    assert sent == []


# ── Framework delete cascade (compliance/signals.py) ────────


def test_framework_delete_with_requirement_does_not_raise():
    from compliance.tests.factories import (
        FrameworkFactory,
        RequirementFactory,
        SectionFactory,
    )

    framework = FrameworkFactory()
    section = SectionFactory(framework=framework)
    RequirementFactory(framework=framework, section=section)
    # The cascade fires requirement post_delete, which used to raise
    # Section/Framework DoesNotExist from _recalculate_chain.
    framework.delete()


# ── Action plan comment: malformed parent (compliance/views.py) ──


def test_action_plan_comment_malformed_parent_does_not_500():
    from compliance.tests.factories import ComplianceActionPlanFactory

    client, _ = _superuser_client()
    plan = ComplianceActionPlanFactory()
    resp = client.post(
        reverse("compliance:action-plan-comments", kwargs={"pk": plan.pk}),
        {"content": "hello", "parent": "notauuid"},
    )
    assert resp.status_code != 500


# ── Dashboard indicator toggle (context/views.py) ───────────


def test_indicator_toggle_non_object_body_does_not_500():
    client, _ = _superuser_client()
    resp = client.post(
        reverse("context:dashboard-indicator-toggle"),
        data="123",
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_indicator_toggle_non_uuid_id_does_not_500():
    client, _ = _superuser_client()
    resp = client.post(
        reverse("context:dashboard-indicator-toggle"),
        data='{"indicator_id": "not-a-uuid"}',
        content_type="application/json",
    )
    assert resp.status_code in (400, 404)


# ── Indicator measurement: non-finite value (context) ───────


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_measurement_form_rejects_non_finite(bad):
    from context.forms import IndicatorMeasurementForm

    form = IndicatorMeasurementForm({"value": bad}, indicator_format="number")
    assert not form.is_valid()
    assert "value" in form.errors


@pytest.mark.parametrize("stored", ["nan", "inf", "-inf"])
def test_format_number_handles_non_finite(stored):
    from context.views import _format_number

    # Must not raise (int(nan) -> ValueError); returns the raw value instead.
    assert _format_number(stored) == stored


# ── Calendar subscribe revoke: malformed token_id (core/views.py) ──


def test_calendar_subscribe_revoke_malformed_token_does_not_500():
    client, _ = _superuser_client()
    resp = client.post(
        reverse("calendar-subscribe"),
        {"action": "revoke", "token_id": "not-a-uuid"},
    )
    assert resp.status_code == 200


# ── Trust Center download token (trust_center) ──────────────


def test_resolve_token_non_uuid_payload_returns_none():
    from trust_center.models.document_request import DocumentRequest

    # A validly signed token whose payload is not a UUID (forged with a leaked
    # SECRET_KEY) must resolve to None, not raise ValidationError.
    token = DocumentRequest._signer().sign("not-a-uuid")
    assert DocumentRequest.resolve_token(token, max_age=3600) is None

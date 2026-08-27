# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The three integration surfaces must agree.

Each of these pins a defect found by exercising the surfaces rather than
reading them: a payload the web form and DRF accept but MCP could not create,
a duplicate DRF turned into a 500 while the form refused it cleanly, and a
permission the MCP tool and the DRF route disagreed on.
"""
import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from incidents.constants import NotificationRecipientKind, NotificationRegime
from incidents.models import IncidentNotification
from incidents.tests.factories import (
    IncidentFactory,
    ReportingObligationTemplateFactory,
)


@pytest.fixture
def superuser(db):
    return UserFactory(is_superuser=True)


@pytest.mark.django_db
def test_the_rest_api_is_mounted():
    """Unmounted, the whole incidents/api/ package is dead code in production."""
    assert reverse("incidents-api:incident-list") == "/api/v1/incidents/incidents/"


@pytest.mark.django_db
def test_mcp_can_create_an_obligation_that_carries_a_statutory_deadline(superuser):
    """The GDPR Art. 33(1) 72-hour case, which is the module's normal one.

    `clean()` reads `due_at`, which `save()` derives. Validating before the
    derivation refused every obligation with a delay, on a field the caller
    never supplies and cannot supply.
    """
    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    server = McpServer()
    register_all_tools(server)
    handler = server.get_tool("create_incident_notification")["handler"]
    incident = IncidentFactory()

    result = handler(superuser, {
        "incident_id": str(incident.pk),
        "regime": NotificationRegime.GDPR_ART33_AUTHORITY,
        "recipient_kind": NotificationRecipientKind.SUPERVISORY_AUTHORITY,
        "deadline_hours": 72,
    })

    assert "error" not in str(result).lower()[:40], result
    created = IncidentNotification.objects.get(incident=incident)
    assert created.deadline_hours == 72
    assert created.due_at is not None, "the clock must be derived on create"


@pytest.mark.django_db
def test_a_duplicate_obligation_template_is_a_400_not_a_500(client, superuser):
    """A conditional UniqueConstraint is checked by validate_constraints(), which
    ModelSerializer never calls, so the duplicate reached the database."""
    client.force_login(superuser)
    existing = ReportingObligationTemplateFactory()

    response = client.post(
        reverse("incidents-api:reportingobligationtemplate-list"),
        {
            "name": "A different label, the same rule",
            "regime": existing.regime,
            "recipient_kind": existing.recipient_kind,
            "clock_hours": 72,
        },
        content_type="application/json",
    )

    assert response.status_code == 400, f"got {response.status_code}"


@pytest.mark.django_db
def test_appending_to_the_chronology_is_a_create_on_both_surfaces():
    """The MCP tool was gated on .update while the DRF route required .create."""
    import inspect

    from mcp import tools

    source = inspect.getsource(tools)
    assert 'require_perm("incidents.incident.create")(create_incident_timeline_entry)' in source
    assert 'require_perm("incidents.incident.update")(create_incident_timeline_entry)' not in source


@pytest.mark.django_db
def test_a_domain_refusal_tells_the_operator_why(client, superuser):
    """49 carefully written reasons were being replaced by "not allowed".

    `transition_error_detail` never returns `str(exc)`, to avoid leaking
    internal detail. A model that wants its own reason shown must therefore
    raise `DomainRefusalError`, whose `detail` is a display string by
    construction. Before this, every m6 gate raised a bare `LifecycleError`
    and the operator was told the move was refused with no reason at all, on
    both the web stepper and the API.
    """
    from core.lifecycle import DomainRefusalError
    from core.transition_messages import GENERIC_DETAIL, transition_error_detail

    detail = transition_error_detail(
        DomainRefusalError("Leaving the assessment requires written assessment notes.")
    )

    assert detail == "Leaving the assessment requires written assessment notes."
    assert detail != GENERIC_DETAIL


def test_no_incidents_gate_raises_a_bare_lifecycle_error():
    """A bare LifecycleError is how the reason gets lost. Keep them all typed."""
    import pathlib

    offenders = [
        path.name
        for path in sorted(pathlib.Path("incidents/models").glob("*.py"))
        if "raise LifecycleError(" in path.read_text(encoding="utf-8")
    ]

    assert offenders == [], f"these still discard their reason: {offenders}"

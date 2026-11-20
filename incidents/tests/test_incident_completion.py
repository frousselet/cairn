# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An incident file is opened short, then completed on its page.

What every entity of the usability standard does (the dialog on one screen,
the landing on the record, a card per section, a reader offered no edit) is
checked for the incident in ``core/tests/test_usability_standard.py``. This
file holds what is particular to it : the dialog asks what happened, when it
was seen, how serious it looks and who handles it, with the severity never
answered for the reader; the triage waits for an incident manager, and for
the justification of a legal awareness that postdates the detection, on every
surface.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from incidents.forms import IncidentCreateForm, IncidentForm
from incidents.models import Incident
from incidents.tests.helpers import INCIDENT_RECLASSIFIED, INCIDENT_TRIAGED, declared_incident

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
NOTHING_OWED = "No regulatory regime applies to this test perimeter."


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


class TestAnIncidentIsOpenedShort:
    def test_it_asks_what_when_how_serious_and_who(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = IncidentCreateForm(user=admin)

        assert sorted(form.fields) == ["detected_at", "incident_manager", "scopes", "severity", "summary", "title"]
        assert form.is_multistep is False
        # Whoever opens the file handles it unless they say otherwise.
        assert form.fields["incident_manager"].initial == admin.pk

    def test_the_severity_is_a_judgement_of_the_reader(self, client, admin):
        """ "Medium" was saved for whoever did not judge it."""
        severity = IncidentCreateForm(user=admin).fields["severity"]

        response = client.post(
            reverse("incidents:incident-create"), {"title": "Ransomware on the file server",
                                                   "detected_at": "2026-01-01T09:00"}, **DRAWER,
        )

        assert severity.required and [value for value, _label in severity.choices][0] == ""
        assert response.status_code == 200 and not Incident.objects.exists()

    def test_the_dialog_opens_on_the_minute_it_is_seen_and_lands_on_the_file(self, client, admin):
        html = client.get(reverse("incidents:incident-create"), **DRAWER).content.decode()
        response = client.post(reverse("incidents:incident-create"), {
            "title": "Ransomware on the file server", "detected_at": "2026-01-01T09:00", "severity": "high",
            "incident_manager": admin.pk,
        }, **DRAWER)
        incident = Incident.objects.get()

        assert timezone.localtime().strftime("%Y-%m-%dT") in html
        assert response.status_code == 204 and response["HX-Redirect"] == incident.get_absolute_url()
        assert (incident.severity, incident.incident_manager, incident.workflow_state) == ("high", admin, "draft")
        assert _missing(incident) == ([], ["summary", "affected"])


class TestWhatTheTriageWaitsFor:
    def test_it_is_not_completed_without_an_incident_manager(self, admin):
        incident = declared_incident(admin, no_obligation_justification=NOTHING_OWED)

        with pytest.raises(DomainRefusalError) as refusal:
            incident.transition_to(INCIDENT_TRIAGED, admin)
        incident.incident_manager = admin
        incident.save()
        incident.transition_to(INCIDENT_TRIAGED, admin)

        assert "assign an incident manager" in str(refusal.value)
        assert incident.workflow_state == INCIDENT_TRIAGED

    def test_a_late_awareness_is_explained_before_the_triage(self, admin):
        incident = declared_incident(admin, incident_manager=admin, no_obligation_justification=NOTHING_OWED)
        incident.awareness_at = incident.detected_at + timedelta(hours=40)
        incident.save()

        with pytest.raises(DomainRefusalError) as refusal:
            incident.transition_to(INCIDENT_TRIAGED, admin)

        assert _missing(incident)[0] == ["awareness_justification"]
        assert "fill in the awareness justification" in str(refusal.value)

    def test_the_file_lists_it_and_opens_each_card(self, client, admin):
        incident = declared_incident(admin)
        edit = reverse("incidents:incident-update", args=[incident.pk])

        html = client.get(incident.get_absolute_url()).content.decode()

        assert "Assign an incident manager" in html
        for key in IncidentForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_the_summary_typed_in_the_editor_is_shown_formatted(self, client, admin):
        """It showed its tags : "<p>Forty finance staff...</p>"."""
        incident = declared_incident(admin, summary="<p>Forty finance staff received a <b>fake</b> invoice.</p>",
                                     description="<p>Sent from a look-alike domain.</p><script>x()</script>")

        html = client.get(incident.get_absolute_url()).content.decode()

        assert "<b>fake</b>" in html and "&lt;p&gt;" not in html
        assert "<script>x()</script>" not in html

    def test_a_reclassified_file_lists_nothing_to_complete(self, client, admin):
        incident = declared_incident(admin)
        incident.transition_to(INCIDENT_RECLASSIFIED, admin, comment="A false positive of the monitoring.")

        html = client.get(incident.get_absolute_url()).content.decode()

        assert "To complete" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_says_what_the_triage_waits_for(self, admin):
        incident = declared_incident(admin)
        api = APIClient()
        api.force_authenticate(user=admin)

        body = api.get(f"/api/v1/incidents/incidents/{incident.pk}/").json()
        body = body.get("data", body)
        triaged = api.post(
            f"/api/v1/incidents/incidents/{incident.pk}/transition/", {"target_state": INCIDENT_TRIAGED},
            format="json",
        )

        assert [item["key"] for item in body["completeness"]["missing"] if item["blocking"]] == ["incident_manager"]
        assert triaged.status_code == 400 and "assign an incident manager" in triaged.content.decode()

    def test_the_mcp_server_says_what_the_triage_waits_for(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        server = McpServer()
        register_all_tools(server)
        incident = declared_incident(admin)

        read = server.get_tool("get_incident")["handler"](admin, {"id": str(incident.pk)})

        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == ["incident_manager"]

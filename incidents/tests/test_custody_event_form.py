# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A custody act is recorded by hand on the ledger of its evidence item.

The ledger is append-only : the form creates and never edits, and asks every
question of the act at once. What is particular to it : the act is chosen,
never answered for the reader (the first of the four was saved for whoever did
not choose), it is proposed as happening now, the inline form reads *Create*,
and the notes typed in the editor are shown formatted.
"""

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from incidents.constants import CustodyAction
from incidents.forms import EvidenceCustodyEventForm
from incidents.models import EvidenceCustodyEvent
from incidents.tests.factories import EvidenceCustodyEventFactory, IncidentFactory
from incidents.tests.helpers import collected_evidence

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


class TestACustodyActIsRecorded:
    def test_the_act_is_chosen_and_proposed_as_now(self, admin):
        evidence = collected_evidence(IncidentFactory(), admin)

        form = EvidenceCustodyEventForm(evidence=evidence, actor=admin, user=admin)
        action = form.fields["action"]

        assert action.required
        assert [value for value, _label in action.choices] == ["", *EvidenceCustodyEventForm.MANUAL_ACTIONS]
        assert form.initial["occurred_at"] is not None

    def test_without_a_chosen_act_nothing_is_appended(self, client, admin):
        evidence = collected_evidence(IncidentFactory(), admin)
        before = EvidenceCustodyEvent.objects.filter(evidence=evidence).count()

        response = client.post(reverse("incidents:custody-event-create", args=[evidence.pk]), {
            "occurred_at": "2026-01-01T10:00", "location": "Safe 3",
        }, **DRAWER)

        assert response.status_code == 200
        assert EvidenceCustodyEvent.objects.filter(evidence=evidence).count() == before

    def test_an_access_is_appended(self, client, admin):
        evidence = collected_evidence(IncidentFactory(), admin)

        response = client.post(reverse("incidents:custody-event-create", args=[evidence.pk]), {
            "action": CustodyAction.ACCESSED, "occurred_at": "2099-01-01T10:00", "location": "Safe 3",
        }, **DRAWER)

        assert response.status_code == 204
        assert EvidenceCustodyEvent.objects.filter(evidence=evidence, action=CustodyAction.ACCESSED).exists()


class TestTheLedger:
    def test_the_inline_form_reads_create_and_the_notes_are_formatted(self, client, admin):
        event = EvidenceCustodyEventFactory(notes="<p>Seal <b>A-1029</b> intact.</p><script>x()</script>")

        html = client.get(reverse("incidents:custody-events", args=[event.evidence.pk])).content.decode()

        assert "<b>A-1029</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html
        assert "Append to the ledger" not in html

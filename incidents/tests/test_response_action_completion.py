# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A response action is a row of the incident file : added short, edited whole.

What every form of the usability standard owes (its size, its helpers, its
labels) is checked in ``core/tests/test_usability_standard.py``. This file
holds what is particular to the row : the dialog, and the form inline on the
file, ask what is done, of which kind, by whom and for when, its kind never
answered for the reader; the row is added to the file and edited whole, on one
screen; and a step marked done still states what it achieved.
"""

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from incidents.constants import ResponseActionStatus
from incidents.forms import IncidentResponseActionCreateForm, IncidentResponseActionForm
from incidents.models import IncidentResponseAction
from incidents.tests.factories import IncidentFactory, IncidentResponseActionFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


class TestAnActionIsAddedShort:
    def test_it_asks_what_which_kind_who_and_for_when(self, admin):
        form = IncidentResponseActionCreateForm(incident=IncidentFactory(), user=admin)
        action_type = form.fields["action_type"]

        assert sorted(form.fields) == ["action_type", "description", "due_at", "owner", "title"]
        assert form.is_multistep is False
        # Whoever adds the step owns it unless they say otherwise; its kind is chosen.
        assert form.fields["owner"].initial == admin.pk
        assert action_type.required and [value for value, _label in action_type.choices][0] == ""

    def test_the_row_is_added_to_the_file_as_planned(self, client, admin):
        incident = IncidentFactory()

        response = client.post(reverse("incidents:response-action-create", args=[incident.pk]), {
            "title": "Isolate the file server", "action_type": "containment", "owner": admin.pk,
        }, **DRAWER)
        action = IncidentResponseAction.objects.get()

        assert response.status_code == 204 and response["HX-Trigger"] == "formSaved"
        assert (action.incident, action.owner, action.status) == (incident, admin, ResponseActionStatus.PLANNED)

    def test_the_file_offers_the_short_form_inline(self, client, admin):
        incident = IncidentFactory()

        html = client.get(reverse("incidents:response-actions", args=[incident.pk])).content.decode()

        assert 'name="title"' in html and 'name="due_at"' in html
        assert 'name="outcome"' not in html and 'name="status"' not in html
        assert ">Create</" in html.replace("\n", "").replace("  ", "")


    def test_the_outcome_typed_in_the_editor_reads_without_its_markup(self, client, admin):
        """The row showed "<p>Token revoked...</p>", cut at eighty characters."""
        action = IncidentResponseActionFactory(outcome="<p>Token <b>revoked</b> at the provider.</p>")

        html = client.get(reverse("incidents:response-actions", args=[action.incident.pk])).content.decode()

        assert "Token revoked at the provider." in html and "&lt;p&gt;" not in html


class TestTheRowIsEditedWhole:
    def test_on_one_screen(self, admin):
        form = IncidentResponseActionForm(instance=IncidentResponseActionFactory(), user=admin)

        assert form.is_multistep is False
        assert IncidentResponseActionForm.section_keys() == ["action"]
        assert {"status", "performed_by", "started_at", "completed_at", "outcome", "effectiveness"} <= set(form.fields)

    def test_a_step_marked_done_states_what_it_achieved(self, client, admin):
        action = IncidentResponseActionFactory(owner=admin)

        response = client.post(reverse("incidents:response-action-update", args=[action.pk]), {
            "title": action.title, "action_type": action.action_type, "status": "done",
            "completed_at": "2026-01-01T10:00",
        }, **DRAWER)
        action.refresh_from_db()

        assert response.status_code == 200 and "A completed action must state what it achieved." in response.content.decode()
        assert action.status == ResponseActionStatus.PLANNED

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A chronology entry is appended short, and corrected from the entry itself.

What every form of the usability standard owes (its size, its helpers, its
labels) is checked in ``core/tests/test_usability_standard.py``. This file
holds what is particular to the chronology : a new entry fits one screen, its
kind chosen, never answered for the reader; the response action or the
evidence item it tells about is one question, over the rows of its incident
only; a correction is appended from the entry it corrects, on that entry's
words, with its reason, and leaves the corrected entry as it was; an entry out
of the reader's reach cannot be corrected; and the detail typed in the editor
is shown formatted.
"""

import pytest
from django.urls import reverse

from accounts.models import Group, Permission
from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from incidents.constants import TimelineEntryKind
from incidents.forms import IncidentTimelineCorrectionForm, IncidentTimelineEntryForm
from incidents.models import IncidentTimelineEntry
from incidents.tests.factories import (
    IncidentEvidenceFactory,
    IncidentFactory,
    IncidentResponseActionFactory,
    IncidentTimelineEntryFactory,
)

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


class TestANewEntryFitsOneScreen:
    def test_it_asks_when_what_kind_and_what_happened(self, admin):
        form = IncidentTimelineEntryForm(incident=IncidentFactory(), author=admin, user=admin)
        kind = form.fields["entry_type"]
        offered = [value for value, _label in kind.choices]

        # No response action nor evidence item yet : the link is not asked (F2).
        assert sorted(form.fields) == ["detail", "entry_type", "is_evidence", "occurred_at", "summary"]
        assert form.is_multistep is False
        assert form.initial["occurred_at"] is not None
        # Chosen by the reader; a correction and a platform line are not appended here.
        assert kind.required and offered[0] == ""
        assert TimelineEntryKind.CORRECTION not in offered and TimelineEntryKind.SYSTEM not in offered

    def test_one_question_links_it_to_an_action_or_an_evidence_item(self, client, admin):
        incident = IncidentFactory()
        action = IncidentResponseActionFactory(incident=incident)
        IncidentEvidenceFactory(incident=incident)

        form = IncidentTimelineEntryForm(incident=incident, author=admin, user=admin)
        client.post(reverse("incidents:timeline-entry-create", args=[incident.pk]), {
            "occurred_at": "2026-01-01T10:04", "entry_type": "action", "summary": "Host isolated",
            "related": f"action:{action.pk}",
        }, **DRAWER)
        entry = IncidentTimelineEntry.objects.get()

        assert len(form.fields) == 6 and "related" in form.fields
        assert (entry.related_action, entry.related_evidence, entry.author) == (action, None, admin)

    def test_a_row_of_another_incident_is_refused(self, client, admin):
        incident = IncidentFactory()
        IncidentResponseActionFactory(incident=incident)
        elsewhere = IncidentResponseActionFactory()

        response = client.post(reverse("incidents:timeline-entry-create", args=[incident.pk]), {
            "occurred_at": "2026-01-01T10:04", "entry_type": "action", "summary": "Host isolated",
            "related": f"action:{elsewhere.pk}",
        }, **DRAWER)

        assert response.status_code == 200 and not IncidentTimelineEntry.objects.exists()

    def test_the_detail_typed_in_the_editor_is_shown_formatted(self, client, admin):
        entry = IncidentTimelineEntryFactory(detail="<p>Ran <b>netstat</b>.</p><script>x()</script>")

        html = client.get(reverse("incidents:timeline-entries", args=[entry.incident.pk])).content.decode()

        assert "<b>netstat</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html


class TestAnEntryIsCorrectedFromItself:
    def test_the_correction_opens_on_its_words(self, client, admin):
        entry = IncidentTimelineEntryFactory(summary="Host isolated at 10:04")
        url = reverse("incidents:timeline-entry-correct", args=[entry.pk])

        card = client.get(reverse("incidents:timeline-entries", args=[entry.incident.pk])).content.decode()
        html = client.get(url, **DRAWER).content.decode()

        assert f'href="{url}"' in card
        assert 'value="Host isolated at 10:04"' in html and 'name="superseded_entry"' not in html

    def test_it_is_appended_and_leaves_the_entry_as_it_was(self, client, admin):
        entry = IncidentTimelineEntryFactory(summary="Host isolated at 10:04")

        response = client.post(reverse("incidents:timeline-entry-correct", args=[entry.pk]), {
            "occurred_at": "2026-01-01T10:40", "summary": "Host isolated at 10:40",
            "correction_reason": "The time was misread from the firewall log.",
        }, **DRAWER)
        correction = IncidentTimelineEntry.objects.exclude(pk=entry.pk).get()
        entry.refresh_from_db()

        assert response.status_code == 204
        assert (correction.superseded_entry, correction.entry_type, correction.author) == (
            entry, TimelineEntryKind.CORRECTION, admin,
        )
        assert entry.summary == "Host isolated at 10:04"

    def test_a_correction_states_why(self, client, admin):
        entry = IncidentTimelineEntryFactory()

        response = client.post(reverse("incidents:timeline-entry-correct", args=[entry.pk]), {
            "occurred_at": "2026-01-01T10:40", "summary": "Host isolated at 10:40",
        }, **DRAWER)

        assert response.status_code == 200 and IncidentTimelineEntry.objects.count() == 1
        assert sorted(IncidentTimelineCorrectionForm(superseded=entry, incident=entry.incident).fields) == [
            "correction_reason", "detail", "is_evidence", "occurred_at", "summary",
        ]

    def test_an_entry_out_of_reach_cannot_be_corrected(self, client):
        mine, other = ScopeFactory(), ScopeFactory()
        reader = UserFactory()
        group = Group.objects.create(name="Incident responders, one scope")
        group.permissions.set(Permission.objects.all())
        group.allowed_scopes.set([mine])
        group.users.add(reader)
        incident = IncidentFactory()
        incident.scopes.set([other])
        entry = IncidentTimelineEntryFactory(incident=incident)
        client.force_login(reader)

        response = client.get(reverse("incidents:timeline-entry-correct", args=[entry.pk]), **DRAWER)

        assert response.status_code == 404

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A security event is reported short, then assessed on its page.

What every entity of the usability standard does is checked for the event in
``core/tests/test_usability_standard.py``. This file holds what is particular
to it : the dialog asks what was seen, when, and whether the report is
anonymous, its class never answered for the reader; whoever records it is its
reporter unless it is anonymous, which leaves no identity at all; the time it
reached the register is the time it was recorded; and the assessment is never
left without written assessment notes (G-01), by a verdict or by the archive,
on every surface, a discard comment being folded into them first (G-05).
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from incidents.forms import SecurityEventCreateForm, SecurityEventForm
from incidents.models import SecurityEvent
from incidents.tests.helpers import (
    EVENT_ARCHIVED,
    EVENT_DISCARDED,
    EVENT_UNDER_ASSESSMENT,
    reported_event,
    walk,
)
from risks.models import Vulnerability

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


def _under_assessment(user, **fields):
    """A reported event whose assessment has started, with no notes yet."""
    return walk(reported_event(user, **fields), EVENT_UNDER_ASSESSMENT, user=user)


class TestAnEventIsReportedShort:
    def test_it_asks_what_when_and_whether_it_is_anonymous(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = SecurityEventCreateForm(user=admin)

        assert sorted(form.fields) == ["description", "detected_at", "event_class", "is_anonymous", "scopes", "title"]
        assert form.is_multistep is False

    def test_an_anonymous_report_carries_no_identity(self, client, admin):
        client.post(reverse("incidents:event-create"), {
            "title": "Badge lent to a visitor", "event_class": "event", "detected_at": "2026-01-01T09:00",
            "is_anonymous": "on",
        }, **DRAWER)
        event = SecurityEvent.objects.get()

        assert event.is_anonymous and event.reporter is None
        assert not event.history.filter(reporter__isnull=False).exists()

    def test_the_class_is_a_decision_of_the_reader(self, client, admin):
        """ "Event" was saved for whoever did not choose, a weakness included."""
        event_class = SecurityEventCreateForm(user=admin).fields["event_class"]

        response = client.post(
            reverse("incidents:event-create"), {"title": "Phishing email", "detected_at": "2026-01-01T09:00"}, **DRAWER,
        )

        assert event_class.required and [value for value, _label in event_class.choices][0] == ""
        assert response.status_code == 200 and not SecurityEvent.objects.exists()

    def test_the_dialog_records_when_it_reached_the_register_and_lands_on_it(self, client, admin):
        response = client.post(reverse("incidents:event-create"), {
            "title": "Phishing email", "event_class": "event", "detected_at": "2026-01-01T09:00",
        }, **DRAWER)
        event = SecurityEvent.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == event.get_absolute_url()
        assert event.reported_at is not None and event.reported_at.second == 0
        # Whoever records a report that is not anonymous is its reporter.
        assert event.reporter == admin and event.workflow_state == "draft"


class TestNoAssessmentIsLeftUndocumented:
    def test_a_promotion_is_refused_and_creates_nothing(self, admin):
        event = _under_assessment(admin)

        with pytest.raises(DomainRefusalError) as refusal:
            event.promote_to_vulnerability(admin, comment="A flaw nobody exploited yet.")

        assert "fill in the assessment notes" in str(refusal.value)
        assert not Vulnerability.objects.exists()
        assert _missing(event)[0] == ["assessment_notes"]

    def test_an_assessment_is_not_archived_undocumented(self, admin):
        """The archive leaves the assessment too, and its comment is not the assessment."""
        event = _under_assessment(admin)
        reported = reported_event(admin)

        with pytest.raises(DomainRefusalError) as refusal:
            event.transition_to(EVENT_ARCHIVED, admin, comment="Out of date.")
        reported.transition_to(EVENT_ARCHIVED, admin, comment="Reported twice.")

        assert "fill in the assessment notes" in str(refusal.value)
        assert reported.workflow_state == EVENT_ARCHIVED
        # Asked once the assessment has started, never of a report nobody assesses yet.
        assert _missing(reported) == ([], [])

    def test_a_discard_comment_is_the_assessment(self, admin):
        event = _under_assessment(admin)

        event.transition_to(EVENT_DISCARDED, admin, comment="A known scanner of our provider.")
        event.refresh_from_db()

        assert event.workflow_state == EVENT_DISCARDED
        assert "A known scanner" in event.assessment_notes

    def test_the_page_lists_it_and_opens_each_card(self, client, admin):
        event = _under_assessment(admin)
        edit = reverse("incidents:event-update", args=[event.pk])

        html = client.get(event.get_absolute_url()).content.decode()

        assert "Fill in the assessment notes" in html
        for key in SecurityEventForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_once_the_verdict_is_reached_nothing_is_left_to_complete(self, client, admin):
        event = _under_assessment(admin)
        event.transition_to(EVENT_DISCARDED, admin, comment="A known scanner of our provider.")

        html = client.get(event.get_absolute_url()).content.decode()

        assert "To complete" not in html

    def test_the_description_typed_in_the_editor_is_shown_formatted(self, client, admin):
        event = reported_event(admin, description="<p>A <b>fake</b> invoice.</p><script>x()</script>")

        html = client.get(event.get_absolute_url()).content.decode()

        assert "<b>fake</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_and_the_mcp_server_say_what_the_verdict_waits_for(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        event = _under_assessment(admin)
        api = APIClient()
        api.force_authenticate(user=admin)
        server = McpServer()
        register_all_tools(server)

        body = api.get(f"/api/v1/incidents/security-events/{event.pk}/").json()
        body = body.get("data", body)
        read = server.get_tool("get_security_event")["handler"](admin, {"id": str(event.pk)})

        assert [item["key"] for item in body["completeness"]["missing"]] == ["assessment_notes"]
        assert [item["key"] for item in read["completeness"]["missing"]] == ["assessment_notes"]

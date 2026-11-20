# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A notification obligation is added short, then completed and filed on its page.

What every form of the usability standard owes (its size, its helpers, its
labels) is checked in ``core/tests/test_usability_standard.py``. The
obligation hangs under its incident, so its page is tested here : the dialog
asks the regime and the recipient (never answered for the reader), the body
and the clock; a duplicate obligation is refused by the form; the filing waits
for the channel and the content, the acknowledgement for its reference, on
every surface; each card opens its section, and a section saves without
touching the clock; the filing recorded from the page goes through the
obligation, as the REST API and the MCP server do, and asks no correction
question on a first filing.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from incidents.constants import ClockAnchor, NotificationRegime, TimelineEntrySource
from incidents.forms import IncidentNotificationCreateForm, IncidentNotificationForm, NotificationFilingForm
from incidents.models import IncidentNotification
from incidents.tests.factories import IncidentFactory, IncidentNotificationFactory
from incidents.tests.helpers import (
    NOTIFICATION_ACKNOWLEDGED,
    NOTIFICATION_ASSESSED,
    NOTIFICATION_DRAFTED,
    NOTIFICATION_SENT,
    assessed_obligation,
    drafted_obligation,
    triaged_incident,
    walk,
)

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


def _local(moment):
    return timezone.localtime(moment).strftime("%Y-%m-%dT%H:%M")


class TestAnObligationIsAddedShort:
    def test_it_asks_the_regime_the_recipient_the_body_and_the_clock(self, admin):
        form = IncidentNotificationCreateForm(incident=IncidentFactory(), user=admin)

        assert sorted(form.fields) == [
            "authority", "clock_anchor", "deadline_hours", "no_fixed_deadline", "recipient_kind", "regime",
        ]
        assert form.is_multistep is False
        for name in ("regime", "recipient_kind", "no_fixed_deadline"):
            field = form.fields[name]
            assert field.required and [value for value, _label in field.choices][0] == "", name
        # The anchor is proposed, in view : legal awareness, the anchor of a statutory clock.
        assert form["clock_anchor"].value() == ClockAnchor.AWARENESS_AT

    def test_the_dialog_lands_on_the_obligation(self, client, admin):
        incident = IncidentFactory()

        response = client.post(reverse("incidents:notification-create", args=[incident.pk]), {
            "regime": NotificationRegime.CONTRACTUAL_CUSTOMER, "recipient_kind": "customer",
            "clock_anchor": ClockAnchor.AWARENESS_AT, "no_fixed_deadline": "false", "deadline_hours": "48",
        }, **DRAWER)
        obligation = IncidentNotification.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == obligation.get_absolute_url()
        assert (obligation.incident, obligation.source, obligation.deadline_hours) == (incident, "manual", 48)
        assert obligation.due_at == incident.awareness_at + timedelta(hours=48)

    def test_a_duty_with_no_deadline_says_so_in_one_answer(self, client, admin):
        incident = IncidentFactory()

        client.post(reverse("incidents:notification-create", args=[incident.pk]), {
            "regime": NotificationRegime.GDPR_ART34_DATA_SUBJECT, "recipient_kind": "data_subject",
            "clock_anchor": ClockAnchor.AWARENESS_AT, "no_fixed_deadline": "true",
        }, **DRAWER)
        obligation = IncidentNotification.objects.get()

        assert (obligation.no_fixed_deadline, obligation.deadline_hours, obligation.due_at) == (True, None, None)

    def test_a_duplicate_is_refused_without_a_server_error(self, client, admin):
        existing = IncidentNotificationFactory()

        response = client.post(reverse("incidents:notification-create", args=[existing.incident.pk]), {
            "regime": existing.regime, "recipient_kind": existing.recipient_kind,
            "clock_anchor": ClockAnchor.AWARENESS_AT, "no_fixed_deadline": "false", "deadline_hours": "72",
        }, **DRAWER)

        assert response.status_code == 200
        assert "already has an obligation under this regime for this recipient" in response.content.decode()
        assert IncidentNotification.objects.count() == 1


class TestTheFilingWaitsForItsContent:
    def test_an_undecided_obligation_is_asked_its_decision_not_its_content(self, admin):
        obligation = assessed_obligation(IncidentFactory(), admin)

        assert _missing(obligation) == ([], ["obligation_reference"])

    def test_the_filing_waits_for_the_channel_and_the_content_and_stamps_nothing(self, admin):
        obligation = drafted_obligation(triaged_incident(admin), admin)

        with pytest.raises(DomainRefusalError):
            obligation.transition_to(NOTIFICATION_SENT, admin)

        assert _missing(obligation)[0] == ["channel", "content"]
        obligation.refresh_from_db()
        assert obligation.workflow_state == NOTIFICATION_DRAFTED and obligation.sent_at is None

    def test_the_acknowledgement_waits_for_its_reference(self, admin):
        obligation = drafted_obligation(triaged_incident(admin), admin, channel="email", content="Text sent.")
        walk(obligation, NOTIFICATION_SENT, user=admin)

        assert _missing(obligation)[0] == ["acknowledgement_reference"]
        with pytest.raises(DomainRefusalError):
            obligation.transition_to(NOTIFICATION_ACKNOWLEDGED, admin)

        obligation.acknowledgement_reference = "CNIL-2026-0042"
        walk(obligation, NOTIFICATION_ACKNOWLEDGED, user=admin)
        assert obligation.workflow_state == NOTIFICATION_ACKNOWLEDGED


class TestThePageOfTheObligation:
    def test_it_lists_what_is_missing_and_opens_each_card(self, client, admin):
        obligation = drafted_obligation(triaged_incident(admin), admin)
        edit = reverse("incidents:notification-update", args=[obligation.pk])

        html = client.get(obligation.get_absolute_url()).content.decode()

        assert "Choose the channel" in html and "Fill in the content" in html
        for key in IncidentNotificationForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_a_section_saves_without_touching_the_clock(self, client, admin):
        obligation = drafted_obligation(triaged_incident(admin), admin, deadline_hours=24)
        due_at = obligation.due_at
        edit = reverse("incidents:notification-update", args=[obligation.pk])

        response = client.post(f"{edit}?section=obligation", {
            "_section": "obligation", "regime": obligation.regime, "recipient_kind": obligation.recipient_kind,
            "obligation_reference": "GDPR Art. 33(1)",
        })
        obligation.refresh_from_db()

        assert response.status_code == 302
        assert (obligation.obligation_reference, obligation.deadline_hours, obligation.due_at) == (
            "GDPR Art. 33(1)", 24, due_at,
        )

    def test_the_texts_typed_in_the_editor_are_shown_formatted(self, client, admin):
        obligation = IncidentNotificationFactory(content="<p>Invoices <b>exposed</b>.</p><script>x()</script>")

        html = client.get(obligation.get_absolute_url()).content.decode()

        assert "<b>exposed</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html


class TestAFilingRecordedFromThePage:
    def test_it_goes_through_the_obligation_and_freezes_its_lateness(self, client, admin):
        obligation = drafted_obligation(triaged_incident(admin), admin, channel="email", content="Text sent.")
        submitted_at = (timezone.now() - timedelta(hours=5)).replace(second=0, microsecond=0)

        response = client.post(reverse("incidents:filing-create", args=[obligation.pk]), {
            "submitted_at": _local(submitted_at), "channel": "email", "recipient_name": "CNIL",
            "subject": "Notification", "content": "Text sent.",
        })
        obligation.refresh_from_db()

        assert response.status_code == 302
        assert obligation.workflow_state == NOTIFICATION_SENT
        assert obligation.sent_at == submitted_at and obligation.first_submitted_at == submitted_at
        assert obligation.sent_by == admin and obligation.filings.count() == 1
        assert obligation.incident.timeline_entries.filter(source=TimelineEntrySource.LIFECYCLE).exists()

    def test_a_first_filing_asks_no_correction_question_a_further_one_does(self, admin):
        obligation = drafted_obligation(triaged_incident(admin), admin, channel="email", content="Text sent.")
        first = NotificationFilingForm(notification=obligation, submitted_by=admin, user=admin)
        walk(obligation, NOTIFICATION_SENT, user=admin)
        further = NotificationFilingForm(notification=obligation, submitted_by=admin, user=admin)

        assert "is_correction" not in first.fields and "supersedes" not in first.fields
        assert "is_correction" in further.fields and "supersedes" in further.fields

    def test_the_channel_is_asked_when_the_obligation_names_none(self, admin):
        obligation = drafted_obligation(triaged_incident(admin), admin)

        form = NotificationFilingForm(notification=obligation, submitted_by=admin, user=admin)

        assert form.fields["channel"].required and form.fields["channel"].choices[0][0] == ""

    def test_it_is_offered_where_a_filing_can_be_recorded(self, client, admin):
        incident = triaged_incident(admin)
        undecided = assessed_obligation(incident, admin)
        drafted = drafted_obligation(incident, admin, regime=NotificationRegime.CONTRACTUAL_CUSTOMER,
                                     recipient_kind="customer")

        assert reverse("incidents:filing-create", args=[undecided.pk]) not in client.get(
            undecided.get_absolute_url()
        ).content.decode()
        assert reverse("incidents:filing-create", args=[drafted.pk]) in client.get(
            drafted.get_absolute_url()
        ).content.decode()

    def test_a_refused_filing_is_shown_on_the_form_and_records_nothing(self, client, admin):
        # A NIS2 early warning states three verdicts the incident does not record yet (G-03).
        obligation = drafted_obligation(
            triaged_incident(admin), admin, regime=NotificationRegime.NIS2_EARLY_WARNING,
            recipient_kind="csirt", channel="portal", content="Early warning.",
        )

        response = client.post(reverse("incidents:filing-create", args=[obligation.pk]), {
            "submitted_at": _local(timezone.now() - timedelta(minutes=5)), "channel": "portal",
            "content": "Early warning.",
        }, **DRAWER)
        obligation.refresh_from_db()

        assert response.status_code == 200 and "NIS2 early warning" in response.content.decode()
        assert obligation.workflow_state == NOTIFICATION_DRAFTED and obligation.filings.count() == 0


class TestTheOtherSurfaces:
    def test_the_rest_api_and_the_mcp_server_say_what_the_filing_waits_for(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        obligation = drafted_obligation(triaged_incident(admin), admin)
        api = APIClient()
        api.force_authenticate(user=admin)
        server = McpServer()
        register_all_tools(server)

        body = api.get(f"/api/v1/incidents/notifications/{obligation.pk}/").json()
        body = body.get("data", body)
        read = server.get_tool("get_incident_notification")["handler"](admin, {"id": str(obligation.pk)})

        assert [item["key"] for item in body["completeness"]["missing"] if item["blocking"]] == ["channel", "content"]
        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == ["channel", "content"]

    def test_an_assessed_step_is_reached_without_any_content(self, admin):
        obligation = IncidentNotificationFactory()

        walk(obligation, NOTIFICATION_ASSESSED, user=admin)

        assert obligation.workflow_state == NOTIFICATION_ASSESSED


class TestTheFilingLog:
    def test_the_transmitted_content_is_shown_formatted(self, client, admin):
        obligation = drafted_obligation(triaged_incident(admin), admin, channel="email", content="Text sent.")
        obligation.record_filing(admin, channel="email", content="<p>Invoices <b>exposed</b>.</p><script>x()</script>")

        html = client.get(obligation.get_absolute_url()).content.decode()

        # Escaped only in the textarea of the next filing, which quotes it.
        assert '<div class="small mt-1 ov-rich"><p>Invoices <b>exposed</b>.</p>' in html
        assert "<script>x()</script>" not in html

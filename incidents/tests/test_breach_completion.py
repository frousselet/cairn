# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A personal data qualification is opened short, then written on its page.

What every form of the usability standard owes (its size, its helpers, its
labels) is checked in ``core/tests/test_usability_standard.py``. The
qualification hangs under its incident, so its page is tested here : the
dialog asks the capacity (never answered for the reader), the nature and the
volumes; a second qualification of the same incident is refused by the form;
the confirmation waits for the Art. 33(3) content, the Art. 34 verdict and,
when a ground is claimed, its justification, on every surface, and a refused
confirmation stamps nothing; each card opens its section; the texts typed in
the editor are shown formatted.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from incidents.constants import Art34Ground
from incidents.forms import PersonalDataBreachCreateForm, PersonalDataBreachForm
from incidents.models import PersonalDataBreach
from incidents.tests.factories import IncidentFactory, PersonalDataBreachFactory
from incidents.tests.helpers import BREACH_CONFIRMED, BREACH_UNDER_QUALIFICATION, walk

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
ARTICLE_33_3 = ["nature", "dpo_contact", "likely_consequences", "measures_taken"]


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


def _under_qualification(admin, **fields):
    return walk(PersonalDataBreachFactory(**fields), BREACH_UNDER_QUALIFICATION, user=admin)


class TestAQualificationIsOpenedShort:
    def test_it_asks_the_capacity_the_nature_and_the_volumes(self, admin):
        form = PersonalDataBreachCreateForm(incident=IncidentFactory(), user=admin)
        role = form.fields["controller_role"]

        assert sorted(form.fields) == [
            "approximate_data_subjects", "approximate_records", "controller_role", "nature",
        ]
        assert form.is_multistep is False
        # "Controller" was saved for whoever did not choose, and it alone decides the duties.
        assert role.required and [value for value, _label in role.choices][0] == ""

    def test_the_dialog_lands_on_the_qualification(self, client, admin):
        incident = IncidentFactory()

        response = client.post(reverse("incidents:breach-create", args=[incident.pk]), {
            "controller_role": "processor", "nature": "Invoices readable by other customers.",
        }, **DRAWER)
        breach = PersonalDataBreach.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == breach.get_absolute_url()
        assert (breach.incident, breach.controller_role) == (incident, "processor")

    def test_a_second_qualification_is_refused_without_a_server_error(self, client, admin):
        breach = PersonalDataBreachFactory()

        response = client.post(reverse("incidents:breach-create", args=[breach.incident.pk]), {
            "controller_role": "controller",
        }, **DRAWER)

        assert response.status_code == 200 and "already has its personal data qualification" in response.content.decode()
        assert PersonalDataBreach.objects.count() == 1


class TestTheConfirmationWaitsForItsContent:
    def test_it_waits_for_the_article_33_3_content_and_the_verdict_and_stamps_nothing(self, admin):
        breach = _under_qualification(admin)

        with pytest.raises(DomainRefusalError) as refusal:
            breach.transition_to(BREACH_CONFIRMED, admin, comment="Confirmed with the DPO.")

        assert _missing(breach)[0] == [*ARTICLE_33_3, "high_risk_to_rights"]
        assert "fill in the nature" in str(refusal.value)
        assert breach.qualified_at is None
        breach.refresh_from_db()
        assert breach.workflow_state == BREACH_UNDER_QUALIFICATION and breach.qualified_at is None

    def test_a_claimed_exemption_waits_for_its_justification(self, admin):
        breach = _under_qualification(
            admin, nature="Leak.", dpo_contact="dpo@example.org", likely_consequences="Phishing.",
            measures_taken="Passwords reset.", high_risk_to_rights=True,
        )
        # The database refuses the pair outright; the page still names the line.
        breach.article_34_exemption = Art34Ground.ENCRYPTION

        assert _missing(breach)[0] == ["article_34_exemption_justification"]

    def test_the_confirmation_is_reached_once_all_is_stated(self, admin):
        breach = _under_qualification(
            admin, nature="Leak.", dpo_contact="dpo@example.org", likely_consequences="Phishing.",
            measures_taken="Passwords reset.", high_risk_to_rights=False,
            high_risk_justification="The data was encrypted at rest.",
        )

        walk(breach, BREACH_CONFIRMED, user=admin, comment="Confirmed with the DPO.")

        assert breach.workflow_state == BREACH_CONFIRMED and breach.qualified_by == admin


class TestThePageOfTheQualification:
    def test_it_lists_what_is_missing_and_opens_each_card(self, client, admin):
        breach = _under_qualification(admin)
        edit = reverse("incidents:breach-update", args=[breach.pk])

        html = client.get(breach.get_absolute_url()).content.decode()

        assert "Fill in the nature" in html and "Assess the high risk to rights and freedoms" in html
        for key in PersonalDataBreachForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_the_texts_typed_in_the_editor_are_shown_formatted(self, client, admin):
        breach = PersonalDataBreachFactory(nature="<p>Invoices <b>exposed</b>.</p><script>x()</script>")

        html = client.get(breach.get_absolute_url()).content.decode()

        assert "<b>exposed</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_and_the_mcp_server_say_what_the_confirmation_waits_for(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        breach = _under_qualification(admin)
        api = APIClient()
        api.force_authenticate(user=admin)
        server = McpServer()
        register_all_tools(server)

        body = api.get(f"/api/v1/incidents/personal-data-breaches/{breach.pk}/").json()
        body = body.get("data", body)
        read = server.get_tool("get_personal_data_breach")["handler"](admin, {"id": str(breach.pk)})

        blocking = [*ARTICLE_33_3, "high_risk_to_rights"]
        assert [item["key"] for item in body["completeness"]["missing"] if item["blocking"]] == blocking
        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == blocking

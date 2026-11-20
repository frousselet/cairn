# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An obligation template enters the catalogue short, then is completed on its page.

What every entity of the usability standard does (the dialog on one screen,
the landing on the record, a card per section, a reader offered no edit, the
empty register) is checked for the template in
``core/tests/test_usability_standard.py``. This file holds what is particular
to it : the dialog asks the name, the regime, the recipient, the authority and
the clock the database requires; the page lists the legal reference and the
content requirements every generated obligation copies, on every surface; the
checklist typed in the editor is shown formatted.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from core.completeness import completeness_of
from incidents.forms import ReportingObligationTemplateCreateForm, ReportingObligationTemplateForm
from incidents.models import ReportingObligationTemplate
from incidents.tests.factories import ReportingObligationTemplateFactory

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


class TestATemplateIsCreatedShort:
    def test_it_asks_the_rule_and_its_clock(self, admin):
        form = ReportingObligationTemplateCreateForm(user=admin)

        assert sorted(form.fields) == [
            "authority", "clock_hours", "name", "no_fixed_deadline", "recipient_kind", "regime",
        ]
        assert form.is_multistep is False

    def test_a_rule_with_no_clock_is_refused_on_the_field(self, client, admin):
        response = client.post(reverse("incidents:obligation-template-create"), {
            "name": "Customer notice", "regime": "gdpr_art34_data_subject", "recipient_kind": "data_subject",
            "no_fixed_deadline": "false",
        }, **DRAWER)
        deadline = ReportingObligationTemplateCreateForm(user=admin).fields["no_fixed_deadline"]

        assert response.status_code == 200 and not ReportingObligationTemplate.objects.exists()
        assert "State the statutory delay in hours" in response.content.decode()
        # Asked, never answered for the reader.
        assert deadline.required and [value for value, _label in deadline.choices][0] == ""

    def test_the_dialog_lands_on_the_rule_which_lists_what_it_lacks(self, client, admin):
        response = client.post(reverse("incidents:obligation-template-create"), {
            "name": "Customer notice", "regime": "gdpr_art34_data_subject", "recipient_kind": "data_subject",
            "no_fixed_deadline": "true",
        }, **DRAWER)
        template = ReportingObligationTemplate.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == template.get_absolute_url()
        assert _missing(template) == ([], ["legal_reference", "content_requirements"])


class TestThePageOfTheTemplate:
    def test_it_lists_what_is_missing_and_opens_each_card(self, client, admin):
        template = ReportingObligationTemplateFactory(legal_reference="", content_requirements="")
        edit = reverse("incidents:obligation-template-update", args=[template.pk])

        html = client.get(template.get_absolute_url()).content.decode()

        assert "Fill in the legal reference" in html and "Fill in the content requirements" in html
        for key in ReportingObligationTemplateForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_the_checklist_typed_in_the_editor_is_shown_formatted(self, client, admin):
        template = ReportingObligationTemplateFactory(
            content_requirements="<p>Describe the <b>categories</b>.</p><script>x()</script>",
        )

        html = client.get(template.get_absolute_url()).content.decode()

        assert "<b>categories</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_and_the_mcp_server_say_what_the_rule_lacks(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        template = ReportingObligationTemplateFactory(legal_reference="", content_requirements="")
        api = APIClient()
        api.force_authenticate(user=admin)
        server = McpServer()
        register_all_tools(server)

        body = api.get(f"/api/v1/incidents/obligation-templates/{template.pk}/").json()
        body = body.get("data", body)
        read = server.get_tool("get_obligation_template")["handler"](admin, {"id": str(template.pk)})

        expected = ["legal_reference", "content_requirements"]
        assert [item["key"] for item in body["completeness"]["missing"]] == expected
        assert [item["key"] for item in read["completeness"]["missing"]] == expected

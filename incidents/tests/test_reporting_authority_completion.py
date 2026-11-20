# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A reporting authority enters the catalogue short, then is completed on its page.

What every entity of the usability standard does (the dialog on one screen,
the landing on the record, a card per section, a reader offered no edit, the
empty register) is checked for the authority in
``core/tests/test_usability_standard.py``. This file holds what is particular
to it : the dialog asks the name, the type (never answered for the reader),
the regime and the jurisdiction; the page lists the filing channel and the
filing procedure it lacks, on every surface; the procedure typed in the
editor is shown formatted.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from core.completeness import completeness_of
from incidents.forms import ReportingAuthorityCreateForm, ReportingAuthorityForm
from incidents.models import ReportingAuthority
from incidents.tests.factories import ReportingAuthorityFactory

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


class TestAnAuthorityIsCreatedShort:
    def test_it_asks_its_name_its_type_its_regime_and_its_jurisdiction(self, admin):
        form = ReportingAuthorityCreateForm(user=admin)
        authority_type = form.fields["authority_type"]

        assert sorted(form.fields) == [
            "authority_type", "jurisdiction_country", "name", "primary_regime", "short_name",
        ]
        assert form.is_multistep is False
        # "Other" was saved for whoever did not choose.
        assert authority_type.required and [value for value, _label in authority_type.choices][0] == ""

    def test_the_dialog_lands_on_the_entry_which_lists_what_it_lacks(self, client, admin):
        response = client.post(reverse("incidents:reporting-authority-create"), {
            "name": "Commission nationale de l'informatique et des libertés", "short_name": "CNIL",
            "authority_type": "supervisory_authority", "primary_regime": "gdpr_art33_authority",
            "jurisdiction_country": "FR",
        }, **DRAWER)
        authority = ReportingAuthority.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == authority.get_absolute_url()
        assert _missing(authority) == ([], ["filing_channel", "procedure"])


class TestThePageOfTheAuthority:
    def test_it_lists_what_is_missing_and_opens_each_card(self, client, admin):
        authority = ReportingAuthorityFactory()
        edit = reverse("incidents:reporting-authority-update", args=[authority.pk])

        html = client.get(authority.get_absolute_url()).content.decode()

        assert "Fill in the filing channel" in html and "Fill in the filing procedure" in html
        for key in ReportingAuthorityForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_any_channel_is_enough(self, admin):
        authority = ReportingAuthorityFactory(contact_phone="+33 1 53 73 22 22")

        assert "filing_channel" not in _missing(authority)[1]

    def test_the_procedure_typed_in_the_editor_is_shown_formatted(self, client, admin):
        authority = ReportingAuthorityFactory(procedure="<p>File on the <b>teleservice</b>.</p><script>x()</script>")

        html = client.get(authority.get_absolute_url()).content.decode()

        assert "<b>teleservice</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_and_the_mcp_server_say_what_the_entry_lacks(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        authority = ReportingAuthorityFactory()
        api = APIClient()
        api.force_authenticate(user=admin)
        server = McpServer()
        register_all_tools(server)

        body = api.get(f"/api/v1/incidents/reporting-authorities/{authority.pk}/").json()
        body = body.get("data", body)
        read = server.get_tool("get_reporting_authority")["handler"](admin, {"id": str(authority.pk)})

        assert [item["key"] for item in body["completeness"]["missing"]] == ["filing_channel", "procedure"]
        assert [item["key"] for item in read["completeness"]["missing"]] == ["filing_channel", "procedure"]

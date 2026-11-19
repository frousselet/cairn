# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An acknowledgement campaign is created short, then completed on its page.

What every entity of the usability standard does (the dialog on one screen,
the landing on the record, a card per section, a reader offered no edit) is
checked for the campaign in ``core/tests/test_usability_standard.py``. This
file holds what is particular to it : it is created with what is to be
acknowledged and by when; its audience is asked before the launch, on every
surface, and a campaign opened on a document takes the roles the document is
addressed to. A launched campaign is frozen : nothing is left to complete.
"""

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.tests.factories import RoleFactory, ScopeFactory
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from documents.constants import CAMPAIGN_RUNNING
from documents.forms import AcknowledgementCampaignForm, CampaignCreateForm
from documents.models import AcknowledgementCampaign
from documents.tests.factories import AcknowledgementCampaignFactory, PolicyVersionFactory, put_in_force

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


@pytest.fixture
def version():
    return put_in_force(PolicyVersionFactory())


def _due():
    return (timezone.localdate() + timezone.timedelta(days=30)).isoformat()


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


class TestACampaignIsCreatedShort:
    def test_it_asks_the_name_the_version_and_the_due_date(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = CampaignCreateForm(user=admin)

        assert sorted(form.fields) == ["due_date", "name", "policy_version", "scopes"]
        assert form.is_multistep is False

    def test_opened_on_a_document_it_takes_the_roles_the_document_addresses(self, client, admin, version):
        role = RoleFactory(workflow_state="validated")
        version.policy.applies_to_roles.add(role)
        url = reverse("documents:campaign-create") + f"?version={version.pk}"

        response = client.post(url, {"name": "All staff", "policy_version": version.pk, "due_date": _due()}, **DRAWER)
        campaign = AcknowledgementCampaign.objects.get()

        assert response.status_code == 204, response.content.decode()[:600]
        assert response["HX-Redirect"] == campaign.get_absolute_url()
        assert list(campaign.audience_roles.all()) == [role]
        assert _missing(campaign) == ([], [])

    def test_with_no_role_to_take_it_asks_for_its_audience(self, client, admin, version):
        client.post(
            reverse("documents:campaign-create"),
            {"name": "All staff", "policy_version": version.pk, "due_date": _due()}, **DRAWER,
        )
        campaign = AcknowledgementCampaign.objects.get()

        html = client.get(campaign.get_absolute_url()).content.decode()

        assert _missing(campaign) == (["audience"], [])
        assert "Choose the audience" in html
        edit = reverse("documents:campaign-update", args=[campaign.pk])
        for key in AcknowledgementCampaignForm.section_keys():
            assert f'{edit}?section={key}"' in html, key


class TestWhatACampaignStillNeeds:
    def test_it_is_not_launched_before_its_audience_is_chosen(self, admin, version):
        campaign = AcknowledgementCampaignFactory(policy_version=version)

        with pytest.raises(DomainRefusalError) as refusal:
            campaign.transition_to(CAMPAIGN_RUNNING, admin)
        campaign.audience_users.add(UserFactory())
        campaign.transition_to(CAMPAIGN_RUNNING, admin)

        assert "choose the audience" in str(refusal.value)
        assert campaign.workflow_state == CAMPAIGN_RUNNING and campaign.acknowledgements.count() == 1

    def test_an_audience_with_nobody_active_is_refused_with_its_own_sentence(self, admin, version):
        campaign = AcknowledgementCampaignFactory(policy_version=version)
        campaign.audience_users.add(UserFactory(is_active=False))

        with pytest.raises(DomainRefusalError) as refusal:
            campaign.transition_to(CAMPAIGN_RUNNING, admin)

        assert "Nobody in the audience is active" in str(refusal.value)

    def test_a_launched_campaign_has_nothing_left_to_complete(self, client, admin, version):
        campaign = AcknowledgementCampaignFactory(policy_version=version)
        campaign.audience_users.add(admin)
        campaign.transition_to(CAMPAIGN_RUNNING, admin)

        html = client.get(campaign.get_absolute_url()).content.decode()

        assert "?section=" not in html and "To complete" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_takes_the_document_roles_and_says_what_is_missing(self, admin, version):
        role = RoleFactory(workflow_state="validated")
        version.policy.applies_to_roles.add(role)
        api = APIClient()
        api.force_authenticate(user=admin)

        created = api.post("/api/v1/documents/acknowledgement-campaigns/", {
            "name": "All staff", "policy_version": str(version.pk), "due_date": _due(),
        }, format="json")
        body = created.json()
        body = body.get("data", body)
        empty = AcknowledgementCampaignFactory(policy_version=PolicyVersionFactory())
        read = api.get(f"/api/v1/documents/acknowledgement-campaigns/{empty.pk}/").json()
        read = read.get("data", read)

        assert created.status_code == 201, created.content
        assert body["audience_roles"] == [str(role.pk)] and body["completeness"]["can_advance"] is True
        assert [item["key"] for item in read["completeness"]["missing"]] == ["audience"]

    def test_the_mcp_server_takes_the_document_roles_and_says_what_is_missing(self, admin, version):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        server = McpServer()
        register_all_tools(server)
        role = RoleFactory(workflow_state="validated")
        version.policy.applies_to_roles.add(role)

        created = server.get_tool("create_acknowledgement_campaign")["handler"](
            admin, {"name": "All staff", "policy_version_id": str(version.pk), "due_date": _due()},
        )
        empty = AcknowledgementCampaignFactory(policy_version=PolicyVersionFactory())
        read = server.get_tool("get_acknowledgement_campaign")["handler"](admin, {"id": str(empty.pk)})

        assert created["audience_roles"] == [str(role.pk)]
        assert [item["key"] for item in read["completeness"]["missing"]] == ["audience"]

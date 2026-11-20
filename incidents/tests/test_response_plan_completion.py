# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A response plan is created short, then written on its page.

What every entity of the usability standard does (the dialog on one screen,
the landing on the record, a card per section, a reader offered no edit) is
checked for the plan in ``core/tests/test_usability_standard.py``. This file
holds what is particular to it : the dialog asks the name, the owner and what
the plan is for; the plan is neither submitted nor put into force without its
procedure, on every surface, the demo seed's path included; and the long texts
typed in the editor are shown formatted.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from incidents.forms import IncidentResponsePlanCreateForm, IncidentResponsePlanForm
from incidents.models import IncidentResponsePlan
from incidents.tests.factories import IncidentResponsePlanFactory
from incidents.tests.helpers import COMMENT, walk

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
# The steps of the core default lifecycle the plan runs (validated : in force).
PENDING, VALIDATED, ARCHIVED = "pending", "validated", "archived"
PROCEDURE = "<p>Detect, assess, respond, learn.</p>"


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


class TestAPlanIsCreatedShort:
    def test_it_asks_its_name_its_owner_and_what_it_is_for(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = IncidentResponsePlanCreateForm(user=admin)

        assert sorted(form.fields) == ["name", "owner", "purpose", "scopes"]
        assert form.is_multistep is False
        # Whoever writes the plan maintains it unless they say otherwise.
        assert form.fields["owner"].initial == admin.pk

    def test_the_dialog_lands_on_the_plan_which_says_what_it_needs(self, client, admin):
        response = client.post(reverse("incidents:response-plan-create"), {
            "name": "ISMS incident response procedure", "owner": admin.pk,
        }, **DRAWER)
        plan = IncidentResponsePlan.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == plan.get_absolute_url()
        assert (plan.owner, plan.workflow_state) == (admin, "draft")
        assert _missing(plan) == (["procedure"], ["classification_scale", "applicable_regimes", "review_date"])


class TestNoPlanInForceWithoutAProcedure:
    def test_it_is_not_submitted_without_one(self, admin):
        plan = IncidentResponsePlanFactory(owner=admin)

        with pytest.raises(DomainRefusalError) as refusal:
            plan.transition_to(PENDING, admin)
        plan.procedure = PROCEDURE
        plan.save()
        walk(plan, PENDING, VALIDATED, user=admin, comment=COMMENT)

        assert "fill in the procedure" in str(refusal.value)
        assert plan.is_in_force

    def test_the_seed_path_is_refused_too(self, admin):
        """put_into_force() walks the same transitions : no plan in force is empty."""
        plan = IncidentResponsePlanFactory(owner=admin)

        with pytest.raises(DomainRefusalError):
            plan.put_into_force(admin, comment=COMMENT)
        plan.refresh_from_db()

        assert plan.workflow_state == "draft"

    def test_the_page_lists_it_and_opens_each_card(self, client, admin):
        plan = IncidentResponsePlanFactory(owner=admin)
        edit = reverse("incidents:response-plan-update", args=[plan.pk])

        html = client.get(plan.get_absolute_url()).content.decode()

        assert "Fill in the procedure" in html
        for key in IncidentResponsePlanForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_the_procedure_typed_in_the_editor_is_shown_formatted(self, client, admin):
        """It showed its tags : "<p>Detect, assess...</p>"."""
        plan = IncidentResponsePlanFactory(
            owner=admin, procedure="<p>Call the <b>duty officer</b>.</p><script>x()</script>",
        )

        html = client.get(plan.get_absolute_url()).content.decode()

        assert "<b>duty officer</b>" in html and "&lt;p&gt;" not in html
        assert "<script>x()</script>" not in html

    def test_an_archived_plan_lists_nothing_to_complete(self, client, admin):
        plan = IncidentResponsePlanFactory(owner=admin, procedure=PROCEDURE)
        walk(plan, PENDING, VALIDATED, ARCHIVED, user=admin, comment=COMMENT)

        html = client.get(plan.get_absolute_url()).content.decode()

        assert "To complete" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_says_what_the_submission_waits_for(self, admin):
        plan = IncidentResponsePlanFactory(owner=admin)
        api = APIClient()
        api.force_authenticate(user=admin)

        body = api.get(f"/api/v1/incidents/response-plans/{plan.pk}/").json()
        body = body.get("data", body)
        submitted = api.post(
            f"/api/v1/incidents/response-plans/{plan.pk}/transition/", {"target_state": PENDING}, format="json",
        )

        assert [item["key"] for item in body["completeness"]["missing"] if item["blocking"]] == ["procedure"]
        assert submitted.status_code == 400 and "fill in the procedure" in submitted.content.decode()

    def test_the_mcp_server_says_what_the_submission_waits_for(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        server = McpServer()
        register_all_tools(server)
        plan = IncidentResponsePlanFactory(owner=admin)

        read = server.get_tool("get_incident_response_plan")["handler"](admin, {"id": str(plan.pk)})

        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == ["procedure"]

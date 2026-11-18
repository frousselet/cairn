# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A role and an activity are created on one screen, then completed on their page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to these two : a role is held, not owned; a person who left stays
on the roles they hold until someone decides otherwise; and an activity says
what it helps to reach, links the interface never let anyone set or read.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.forms import ActivityCreateForm, ActivityUpdateForm, RoleCreateForm, RoleUpdateForm
from context.models import Activity, Role
from context.tests.factories import (
    ActivityFactory,
    ObjectiveFactory,
    ResponsibilityFactory,
    RoleFactory,
    ScopeFactory,
    StakeholderFactory,
)
from core.completeness import completeness_of

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _user_with(*codenames, scopes=()):
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    for codename in codenames:
        group.permissions.add(PermissionFactory(codename=codename))
    for scope in scopes:
        group.allowed_scopes.add(scope)
    group.users.add(user)
    return user


def _mcp(user, tool, arguments):
    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    server = McpServer()
    register_all_tools(server)
    answer = server.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }), user)
    return json.loads(answer["result"]["content"][0]["text"])


class TestARole:
    def test_creation_asks_what_it_is_called_what_kind_it_is_and_who_holds_it(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = RoleCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "description", "type", "assigned_users"]
        assert form.is_multistep is False
        # A role is held, not owned : whoever creates it is not put on it.
        assert not form.fields["assigned_users"].initial

    def test_it_is_created_and_lands_on_its_page(self, client, admin):
        holder = UserFactory()

        response = client.post(
            reverse("context:role-create"),
            {"name": "Information security officer", "type": "governance", "assigned_users": [str(holder.pk)],
             "description": ""},
            **DRAWER,
        )

        role = Role.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == role.get_absolute_url()
        assert list(role.assigned_users.all()) == [holder]

    def test_its_page_asks_who_holds_it_and_what_it_answers_for(self, client, admin):
        role = RoleFactory()
        edit = reverse("context:role-update", kwargs={"pk": role.pk})

        report = completeness_of(role)
        html = client.get(role.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["holder", "responsibilities"]
        assert report.blocking_missing == [] and report.can_advance
        assert f'href="{edit}?section=identity"' in html and f'href="{edit}?section=assignment"' in html
        # Its responsibilities are rows of the page : the line leads to their card.
        assert f'href="{role.get_absolute_url()}#responsibilities-section"' in html
        assert 'id="responsibilities-section"' in html

    def test_a_holder_and_a_responsibility_answer_both_lines(self):
        role = RoleFactory()
        role.assigned_users.add(UserFactory())
        ResponsibilityFactory(role=role)

        assert completeness_of(role).is_complete

    def test_the_card_of_its_holders_sets_them_and_leaves_the_rest_alone(self, client, admin):
        role = RoleFactory(name="Data protection officer", is_mandatory=True)
        holder = UserFactory()

        response = client.post(
            reverse("context:role-update", kwargs={"pk": role.pk}),
            {"_section": "assignment", "assigned_users": [str(holder.pk)]},
            **DRAWER,
        )

        role.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert list(role.assigned_users.all()) == [holder]
        assert (role.name, role.is_mandatory) == ("Data protection officer", True)

    def test_a_person_who_left_stays_on_the_role_until_someone_decides(self, client, admin):
        """The picker offered active accounts only : saving the holders again
        refused the form, or dropped whoever had left, without a word."""
        role = RoleFactory()
        gone, present = UserFactory(is_active=False), UserFactory()
        role.assigned_users.add(gone)

        offered = RoleUpdateForm(instance=role, user=admin, section="assignment").fields["assigned_users"].queryset
        elsewhere = RoleCreateForm(user=admin).fields["assigned_users"].queryset
        response = client.post(
            reverse("context:role-update", kwargs={"pk": role.pk}),
            {"_section": "assignment", "assigned_users": [str(gone.pk), str(present.pk)]},
            **DRAWER,
        )

        assert gone in offered and gone not in elsewhere
        assert response.status_code == 204, response.content.decode()[:400]
        assert set(role.assigned_users.all()) == {gone, present}

    def test_a_mandatory_role_nobody_holds_is_still_flagged(self, client, admin):
        role = RoleFactory(is_mandatory=True)

        assert "Mandatory role without assigned user" in client.get(role.get_absolute_url()).content.decode()


class TestAnActivity:
    def test_creation_asks_what_is_done_how_much_it_matters_and_who_answers(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = ActivityCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "description", "type", "criticality", "owner"]
        assert form.is_multistep is False
        # Whoever creates it answers for it unless they say otherwise.
        assert form.fields["owner"].initial == admin.pk

    def test_it_is_created_and_lands_on_its_page(self, client, admin):
        response = client.post(
            reverse("context:activity-create"),
            {"name": "Billing customers", "type": "core_business", "criticality": "high", "owner": str(admin.pk),
             "description": ""},
            **DRAWER,
        )

        activity = Activity.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == activity.get_absolute_url()

    def test_its_page_asks_what_it_covers_and_what_it_helps_to_reach(self, client, admin):
        activity = ActivityFactory()
        edit = reverse("context:activity-update", kwargs={"pk": activity.pk})

        report = completeness_of(activity)
        html = client.get(activity.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["description", "objectives"]
        assert report.blocking_missing == [] and report.can_advance
        assert f'href="{edit}?section=identity"' in html and f'href="{edit}?section=relations"' in html

    def test_its_relations_are_set_from_its_card_among_what_can_be_linked(self, client, admin):
        """The objectives it helps to reach and the stakeholders it serves
        existed in the model, the REST API and the MCP server only."""
        objective = ObjectiveFactory(name="Invoices go out within two days", workflow_state="validated")
        draft = ObjectiveFactory(name="A draft objective")
        stakeholder = StakeholderFactory(name="Our clients", workflow_state="validated")
        activity = ActivityFactory()

        offered = ActivityUpdateForm(instance=activity, user=admin, section="relations").fields["related_objectives"].queryset
        response = client.post(
            reverse("context:activity-update", kwargs={"pk": activity.pk}),
            {"_section": "relations", "related_objectives": [str(objective.pk)],
             "related_stakeholders": [str(stakeholder.pk)], "parent_activity": ""},
            **DRAWER,
        )
        html = client.get(activity.get_absolute_url()).content.decode()

        assert objective in offered and draft not in offered
        assert response.status_code == 204, response.content.decode()[:400]
        assert "Invoices go out within two days" in html and "Our clients" in html

    def test_an_activity_is_not_a_part_of_itself(self, admin):
        activity = ActivityFactory(workflow_state="validated")
        other = ActivityFactory(workflow_state="validated")

        offered = ActivityUpdateForm(instance=activity, user=admin, section="relations").fields["parent_activity"].queryset

        assert other in offered and activity not in offered

    def test_a_record_of_another_scope_is_not_named_on_its_page(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        activity = ActivityFactory(scopes=[mine])
        activity.related_objectives.add(
            ObjectiveFactory(name="An objective of the other scope", scopes=[theirs]),
            ObjectiveFactory(name="An objective of my scope", scopes=[mine]),
        )
        ActivityFactory(name="A part filed elsewhere", parent_activity=activity, scopes=[theirs])
        client.force_login(_user_with("context.activity.read", scopes=[mine]))

        html = client.get(activity.get_absolute_url()).content.decode()

        assert "An objective of my scope" in html
        assert "An objective of the other scope" not in html and "A part filed elsewhere" not in html


class TestTheRegisters:
    @pytest.mark.parametrize("list_name, create_name, title", [
        ("context:role-list", "context:role-create", "No role yet."),
        ("context:activity-list", "context:activity-create", "No activity yet."),
    ])
    def test_an_empty_one_explains_and_offers_the_first(self, client, admin, list_name, create_name, title):
        html = client.get(reverse(list_name)).content.decode()

        assert title in html
        create = reverse(create_name)
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApiAndTheMcpServer:
    def test_they_report_the_completeness_of_one_record(self, admin):
        role, activity = RoleFactory(), ActivityFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/context/roles/{role.pk}/").json()
        one = one.get("data", one)
        other = api.get(f"/api/v1/context/activities/{activity.pk}/").json()
        other = other.get("data", other)

        assert [item["key"] for item in one["completeness"]["missing"]] == ["holder", "responsibilities"]
        assert [item["key"] for item in other["completeness"]["missing"]] == ["description", "objectives"]
        assert [item["key"] for item in _mcp(admin, "get_role", {"id": str(role.pk)})["completeness"]["missing"]] == [
            "holder", "responsibilities",
        ]
        assert [
            item["key"] for item in _mcp(admin, "get_activity", {"id": str(activity.pk)})["completeness"]["missing"]
        ] == ["description", "objectives"]

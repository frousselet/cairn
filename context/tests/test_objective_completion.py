# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An objective is created on one screen, then completed on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the objective : it answers issues and stakeholders, links the
model always had and the interface never let anyone set or read; a link
targets what its lifecycle makes linkable; and an objective opened from an
issue answers that issue.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.forms import IssueUpdateForm, ObjectiveCreateForm, ObjectiveUpdateForm
from context.models import Objective
from context.tests.factories import IssueFactory, ObjectiveFactory, ScopeFactory, StakeholderFactory
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


class TestCreationIsShort:
    def test_it_asks_what_is_aimed_at_what_it_serves_who_answers_and_for_when(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = ObjectiveCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "category", "type", "owner", "target_date"]
        assert form.is_multistep is False
        # Whoever creates it answers for it unless they say otherwise.
        assert form.fields["owner"].initial == admin.pk

    def test_an_objective_is_created_and_lands_on_its_page(self, client, admin):
        response = client.post(
            reverse("context:objective-create"),
            {"name": "Every newcomer is trained within a month", "category": "operational", "type": "security",
             "owner": str(admin.pk), "target_date": "2027-06-30"},
            **DRAWER,
        )

        objective = Objective.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == objective.get_absolute_url()
        assert objective.owner == admin and str(objective.target_date) == "2027-06-30"


class TestWhatItStillNeeds:
    def test_a_bare_objective_lists_what_would_make_it_useful(self, client, admin):
        objective = ObjectiveFactory()
        edit = reverse("context:objective-update", kwargs={"pk": objective.pk})

        report = completeness_of(objective)
        html = client.get(objective.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["measure", "deadline", "issues"]
        # Advice : nothing holds its lifecycle back.
        assert report.blocking_missing == [] and report.can_advance
        for section in ("identity", "measurement", "progress", "relations"):
            assert f'href="{edit}?section={section}"' in html

    def test_the_card_of_its_measurement_sets_it_and_leaves_the_rest_alone(self, client, admin):
        objective = ObjectiveFactory(name="Train every newcomer", current_value="40")
        edit = reverse("context:objective-update", kwargs={"pk": objective.pk})

        response = client.post(
            edit, {"_section": "measurement", "target_value": "95", "unit": "%",
                   "measurement_method": "<p>Trained newcomers over arrivals.</p>", "measurement_frequency": "monthly"},
            **DRAWER,
        )

        objective.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert (objective.target_value, objective.unit, objective.measurement_frequency) == ("95", "%", "monthly")
        assert (objective.name, objective.current_value) == ("Train every newcomer", "40")

    def test_how_it_is_measured_is_shown_formatted_not_as_markup(self, client, admin):
        """The method is typed in the rich-text editor : the page printed its tags."""
        objective = ObjectiveFactory(measurement_method="<p>Trained newcomers over <strong>arrivals</strong>.</p>")

        html = client.get(objective.get_absolute_url()).content.decode()

        assert "<p>Trained newcomers over <strong>arrivals</strong>.</p>" in html
        assert "&lt;p&gt;" not in html

    def test_an_achieved_objective_must_be_at_100(self, client, admin):
        """Rule RS-02, said where the answer is given : status and progress sit in the same card."""
        objective = ObjectiveFactory(progress_percentage=60)
        edit = reverse("context:objective-update", kwargs={"pk": objective.pk})

        refused = client.post(
            edit, {"_section": "progress", "status": "achieved", "progress_percentage": "60", "current_value": "",
                   "target_date": "", "review_date": ""},
            **DRAWER,
        )
        accepted = client.post(
            edit, {"_section": "progress", "status": "achieved", "progress_percentage": "100", "current_value": "",
                   "target_date": "", "review_date": ""},
            **DRAWER,
        )

        objective.refresh_from_db()
        assert refused.status_code == 200 and "An achieved objective must have 100% progress." in refused.content.decode()
        assert accepted.status_code == 204, accepted.content.decode()[:400]
        assert objective.status == "achieved"


class TestWhatItAnswers:
    """An objective answers issues and stakeholders : the links existed in the
    model, the REST API and the MCP server, and nowhere in the interface."""

    def test_its_relations_are_picked_among_what_can_be_linked(self, admin):
        validated = IssueFactory(name="A directive comes into force", workflow_state="validated")
        draft = IssueFactory(name="A rumour of reorganisation")
        objective = ObjectiveFactory()

        offered = ObjectiveUpdateForm(instance=objective, user=admin, section="relations").fields["related_issues"].queryset

        assert validated in offered and draft not in offered

    def test_a_link_made_earlier_survives_its_target_leaving_that_step(self, admin):
        issue = IssueFactory(workflow_state="validated")
        objective = ObjectiveFactory()
        objective.related_issues.add(issue)
        issue.workflow_state = "archived"
        issue.save()

        offered = ObjectiveUpdateForm(instance=objective, user=admin, section="relations").fields["related_issues"].queryset

        assert issue in offered

    def test_an_objective_is_not_its_own_parent(self, admin):
        objective = ObjectiveFactory(workflow_state="validated")
        other = ObjectiveFactory(workflow_state="validated")

        offered = ObjectiveUpdateForm(instance=objective, user=admin, section="relations").fields["parent_objective"].queryset

        assert other in offered and objective not in offered

    def test_they_are_set_from_its_card_and_read_on_the_three_pages(self, client, admin):
        issue = IssueFactory(name="A directive comes into force", workflow_state="validated")
        stakeholder = StakeholderFactory(name="The national agency", workflow_state="validated")
        objective = ObjectiveFactory(name="Report an incident within a day")

        response = client.post(
            reverse("context:objective-update", kwargs={"pk": objective.pk}),
            {"_section": "relations", "related_issues": [str(issue.pk)], "related_stakeholders": [str(stakeholder.pk)],
             "parent_objective": ""},
            **DRAWER,
        )

        assert response.status_code == 204, response.content.decode()[:400]
        assert list(objective.related_issues.all()) == [issue]
        assert "A directive comes into force" in client.get(objective.get_absolute_url()).content.decode()
        assert "Report an incident within a day" in client.get(issue.get_absolute_url()).content.decode()
        assert "Report an incident within a day" in client.get(stakeholder.get_absolute_url()).content.decode()

    def test_an_issue_names_whoever_it_concerns(self, client, admin):
        stakeholder = StakeholderFactory(name="The national agency", workflow_state="validated")
        issue = IssueFactory()

        form = IssueUpdateForm(instance=issue, user=admin, section="relations")
        response = client.post(
            reverse("context:issue-update", kwargs={"pk": issue.pk}),
            {"_section": "relations", "related_stakeholders": [str(stakeholder.pk)]},
            **DRAWER,
        )

        assert list(form.fields) == ["related_stakeholders"]
        assert response.status_code == 204, response.content.decode()[:400]
        assert "The national agency" in client.get(issue.get_absolute_url()).content.decode()
        assert issue.name in client.get(stakeholder.get_absolute_url()).content.decode()


class TestOpenedFromAnIssue:
    def test_a_validated_issue_offers_an_objective_that_answers_it(self, client, admin):
        issue = IssueFactory(workflow_state="validated")
        create = reverse("context:objective-create")

        page = client.get(issue.get_absolute_url()).content.decode()
        dialog = client.get(create, {"issue": str(issue.pk)}, **DRAWER).content.decode()

        assert f'href="{create}?issue={issue.pk}"' in page
        assert f'<input type="hidden" name="related_issues" value="{issue.pk}"' in dialog

    def test_the_objective_created_there_answers_that_issue(self, client, admin):
        issue = IssueFactory(workflow_state="validated")

        response = client.post(
            reverse("context:objective-create") + f"?issue={issue.pk}",
            {"name": "Report an incident within a day", "category": "compliance", "type": "compliance",
             "owner": str(admin.pk), "target_date": "", "related_issues": [str(issue.pk)]},
            **DRAWER,
        )

        objective = Objective.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert list(objective.related_issues.all()) == [issue]
        assert [item.key for item in completeness_of(objective).advised_missing] == ["measure", "deadline"]

    def test_a_draft_issue_says_when_it_can_be_answered(self, client, admin):
        """A link targets what its lifecycle makes linkable : a draft is not answered yet."""
        issue = IssueFactory()
        create = reverse("context:objective-create")

        page = client.get(issue.get_absolute_url()).content.decode()
        dialog = client.get(create, {"issue": str(issue.pk)}, **DRAWER).content.decode()

        assert f"{create}?issue=" not in page
        assert "An objective can answer this issue once it is validated." in page
        assert 'name="related_issues"' not in dialog

    def test_a_malformed_or_unknown_issue_in_the_address_does_not_raise(self, client, admin):
        create = reverse("context:objective-create")

        for value in ("garbage", "5f0c5b9e-8a43-4e6f-9d0f-7c1d3a2b4c5d"):
            assert client.get(create, {"issue": value}).status_code == 200

    def test_an_issue_of_another_scope_is_not_carried(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        issue = IssueFactory(workflow_state="validated", scopes=[theirs])
        client.force_login(_user_with("context.objective.create", scopes=[mine]))

        dialog = client.get(reverse("context:objective-create"), {"issue": str(issue.pk)}, **DRAWER).content.decode()

        assert 'name="related_issues"' not in dialog and str(issue.pk) not in dialog


class TestTheRelationsStayWithinReach:
    def test_a_record_of_another_scope_is_not_named_on_the_page(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        objective = ObjectiveFactory(scopes=[mine])
        hidden = IssueFactory(name="An issue of the other scope", workflow_state="validated", scopes=[theirs])
        shown = IssueFactory(name="An issue of my scope", workflow_state="validated", scopes=[mine])
        objective.related_issues.add(hidden, shown)
        client.force_login(_user_with("context.objective.read", scopes=[mine]))

        html = client.get(objective.get_absolute_url()).content.decode()

        assert "An issue of my scope" in html
        assert "An issue of the other scope" not in html


class TestThePage:
    def test_the_empty_register_explains_and_offers_the_first_objective(self, client, admin):
        html = client.get(reverse("context:objective-list")).content.decode()

        assert "No objective yet." in html
        create = reverse("context:objective-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApiAndTheMcpServer:
    def test_they_report_the_completeness_of_one_objective(self, admin):
        objective = ObjectiveFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/context/objectives/{objective.pk}/").json()
        one = one.get("data", one)
        many = api.get("/api/v1/context/objectives/").json()
        rows = many.get("data", many.get("results", many))
        read = _mcp(admin, "get_objective", {"id": str(objective.pk)})

        assert [item["key"] for item in one["completeness"]["missing"]] == ["measure", "deadline", "issues"]
        assert rows and "completeness" not in rows[0]
        assert [item["key"] for item in read["completeness"]["missing"]] == ["measure", "deadline", "issues"]

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An issue and a stakeholder are created on one screen, then completed on their page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to these two : how much they weigh is a decision nobody takes for
the reader; an issue is internal or external by its category, which is the
only one of the two asked; and what a stakeholder expects, which could only be
recorded over the API, is added, edited and removed from its page.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.forms import IssueCreateForm, IssueUpdateForm, StakeholderCreateForm, StakeholderExpectationForm
from context.models import Issue, Stakeholder, StakeholderExpectation
from context.tests.factories import (
    IssueFactory,
    ScopeFactory,
    StakeholderExpectationFactory,
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


class TestAnIssue:
    def test_creation_asks_what_the_fact_is_and_how_much_it_weighs(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = IssueCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "description", "category", "impact_level"]
        assert form.is_multistep is False

    def test_its_category_says_whether_it_is_internal_or_external(self, admin):
        """Rule RS-01 : a category belongs to one type. The select shows which,
        so the type is not a second question the answer could contradict."""
        groups = [
            (str(group), [value for value, _label in options])
            for group, options in IssueCreateForm(user=admin).fields["category"].choices if group
        ]

        assert groups == [
            ("Internal", ["strategic", "organizational", "human_resources", "technical", "financial", "cultural"]),
            ("External", ["political", "economic", "social", "technological", "legal", "environmental",
                          "competitive", "regulatory"]),
        ]

    def test_it_is_created_and_lands_on_its_page(self, client, admin):
        response = client.post(
            reverse("context:issue-create"),
            {"name": "Two thirds of the staff work remotely", "category": "organizational",
             "impact_level": "high", "description": ""},
            **DRAWER,
        )

        issue = Issue.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == issue.get_absolute_url()
        assert issue.type == "internal"

    def test_an_external_category_makes_an_external_issue(self, client, admin):
        response = client.post(
            reverse("context:issue-create"),
            {"name": "A directive on network security comes into force", "category": "regulatory",
             "impact_level": "critical", "description": ""},
            **DRAWER,
        )

        assert response.status_code == 204, response.content.decode()[:400]
        assert Issue.objects.get().type == "external"

    def test_changing_its_category_changes_its_type_with_it(self, client, admin):
        issue = IssueFactory(type="internal", category="strategic")
        form = IssueUpdateForm(instance=issue, user=admin, section="identity")

        response = client.post(
            reverse("context:issue-update", kwargs={"pk": issue.pk}),
            {"_section": "identity", "name": issue.name, "category": "legal", "source": "", "description": ""},
            **DRAWER,
        )

        issue.refresh_from_db()
        assert "type" not in form.fields
        assert response.status_code == 204, response.content.decode()[:400]
        assert (issue.type, issue.category) == ("external", "legal")

    def test_the_other_card_leaves_its_type_alone(self, client, admin):
        issue = IssueFactory(type="external", category="legal")

        response = client.post(
            reverse("context:issue-update", kwargs={"pk": issue.pk}),
            {"_section": "assessment", "impact_level": "low", "trend": "", "review_date": "2027-03-01",
             "status": "monitored"},
            **DRAWER,
        )

        issue.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert (issue.type, issue.category, issue.impact_level) == ("external", "legal", "low")

    def test_how_much_it_weighs_is_not_answered_for_the_reader(self, client, admin):
        response = client.post(
            reverse("context:issue-create"),
            {"name": "Two thirds of the staff work remotely", "category": "organizational"},
            **DRAWER,
        )

        assert response.status_code == 200
        assert not Issue.objects.exists()

    def test_its_page_asks_why_it_matters_and_when_it_is_reviewed(self, client, admin):
        issue = IssueFactory()
        edit = reverse("context:issue-update", kwargs={"pk": issue.pk})

        report = completeness_of(issue)
        html = client.get(issue.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["description", "review_date"]
        assert report.blocking_missing == [] and report.can_advance
        assert f'href="{edit}?section=identity"' in html
        assert f'href="{edit}?section=assessment"' in html

    def test_the_empty_register_explains_and_offers_the_first_issue(self, client, admin):
        html = client.get(reverse("context:issue-list")).content.decode()

        assert "No issue yet." in html
        create = reverse("context:issue-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestAStakeholder:
    def test_creation_asks_who_it_is_and_how_much_it_weighs(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = StakeholderCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "type", "category", "influence_level", "interest_level"]
        assert form.is_multistep is False

    def test_it_is_created_and_lands_on_its_page(self, client, admin):
        response = client.post(
            reverse("context:stakeholder-create"),
            {"name": "The data protection authority", "type": "external", "category": "regulators",
             "influence_level": "high", "interest_level": "medium"},
            **DRAWER,
        )

        stakeholder = Stakeholder.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == stakeholder.get_absolute_url()

    def test_its_page_asks_first_what_it_expects(self, client, admin):
        stakeholder = StakeholderFactory()
        edit = reverse("context:stakeholder-update", kwargs={"pk": stakeholder.pk})
        add = reverse("context:stakeholder-expectation-create", args=[stakeholder.pk])

        report = completeness_of(stakeholder)
        html = client.get(stakeholder.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["expectations", "contact"]
        assert report.blocking_missing == [] and report.can_advance
        assert "Note what it expects of you" in html
        assert html.count(f'href="{add}"') == 2  # the line of the list, and the button of the card
        assert f'href="{edit}?section=contact"' in html

    def test_an_email_alone_names_who_to_write_to(self):
        stakeholder = StakeholderFactory(contact_email="dpo@example.org")
        StakeholderExpectationFactory(stakeholder=stakeholder)

        assert completeness_of(stakeholder).is_complete

    def test_the_empty_register_explains_and_offers_the_first_stakeholder(self, client, admin):
        html = client.get(reverse("context:stakeholder-list")).content.decode()

        assert "No stakeholder yet." in html
        create = reverse("context:stakeholder-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestWhatAStakeholderExpects:
    """It could be read on the page and written over the API only."""

    def test_the_dialog_fits_one_screen(self):
        form = StakeholderExpectationForm()

        assert list(form.fields) == ["description", "type", "priority", "is_applicable"]
        assert form.is_multistep is False

    def test_an_expectation_is_added_from_the_page_of_the_stakeholder(self, client, admin):
        stakeholder = StakeholderFactory()

        response = client.post(
            reverse("context:stakeholder-expectation-create", args=[stakeholder.pk]),
            {"description": "To be told of a data breach within 72 hours", "type": "requirement",
             "priority": "high", "is_applicable": "on"},
            **DRAWER,
        )

        expectation = StakeholderExpectation.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert expectation.stakeholder == stakeholder and expectation.type == "requirement"
        assert "To be told of a data breach" in client.get(stakeholder.get_absolute_url()).content.decode()

    def test_it_is_edited_and_removed_from_its_row(self, client, admin):
        expectation = StakeholderExpectationFactory(description="To see a certificate")
        page = expectation.stakeholder.get_absolute_url()
        edit = reverse("context:stakeholder-expectation-update", args=[expectation.pk])
        delete = reverse("context:stakeholder-expectation-delete", args=[expectation.pk])

        html = client.get(page).content.decode()
        edited = client.post(
            edit, {"description": "To see a certificate every year", "type": "expectation", "priority": "low"},
            **DRAWER,
        )
        expectation.refresh_from_db()

        assert f'href="{edit}"' in html and f'href="{delete}"' in html
        assert edited.status_code == 204, edited.content.decode()[:400]
        assert expectation.description == "To see a certificate every year" and expectation.is_applicable is False

        removed = client.post(delete, HTTP_HX_REQUEST="true")

        assert removed.status_code == 204
        assert not StakeholderExpectation.objects.exists()

    def test_what_was_typed_in_the_editor_is_shown_formatted_and_sanitised(self, client, admin):
        """The description is rich text on every surface (the MCP server says
        so to its clients) : the row shows it formatted, never as markup."""
        expectation = StakeholderExpectationFactory(
            description='<p onclick="steal()">To see a <strong>certificate</strong></p><script>alert(1)</script>',
        )
        edit = reverse("context:stakeholder-expectation-update", args=[expectation.pk])

        html = client.get(expectation.stakeholder.get_absolute_url()).content.decode()

        assert '<td class="cell-text cell-rich"><p>To see a <strong>certificate</strong></p></td>' in html
        assert "&lt;p" not in html and "<p onclick" not in html and "<script>alert(1)" not in html
        # The buttons of its row name it in words.
        row = html[html.index(f'href="{edit}"'):]
        assert 'aria-label="Edit : To see a certificate"' in row[:600]

    def test_the_mcp_server_reads_and_writes_whether_it_is_taken_into_account(self, admin):
        stakeholder = StakeholderFactory()

        created = _mcp(admin, "create_expectation", {
            "stakeholder_id": str(stakeholder.pk), "description": "<p>To see a certificate</p>",
            "type": "expectation", "priority": "low", "is_applicable": False,
        })
        listed = _mcp(admin, "list_expectations", {"stakeholder_id": str(stakeholder.pk)})

        expectation = StakeholderExpectation.objects.get()
        assert "error" not in created, created
        assert expectation.is_applicable is False
        assert listed["items"][0]["is_applicable"] is False

    def test_a_reader_is_offered_none_of_it(self, client):
        expectation = StakeholderExpectationFactory()
        stakeholder = expectation.stakeholder
        client.force_login(_user_with("context.stakeholder.read"))

        html = client.get(stakeholder.get_absolute_url()).content.decode()
        refused = client.post(
            reverse("context:stakeholder-expectation-create", args=[stakeholder.pk]),
            {"description": "Anything", "type": "need", "priority": "low"},
        )

        assert "expectations/" not in html
        # Refused as every missing permission is : sent away, nothing written.
        assert refused.status_code in (302, 403)
        assert StakeholderExpectation.objects.count() == 1

    def test_a_stakeholder_of_another_scope_answers_as_an_unknown_one(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        stakeholder = StakeholderFactory(scopes=[theirs])
        expectation = StakeholderExpectationFactory(stakeholder=stakeholder)
        client.force_login(_user_with(
            "context.stakeholder.read", "context.expectation.create", "context.expectation.update",
            "context.expectation.delete", scopes=[mine],
        ))

        add = client.post(
            reverse("context:stakeholder-expectation-create", args=[stakeholder.pk]),
            {"description": "Anything", "type": "need", "priority": "low"},
        )
        edit = client.post(
            reverse("context:stakeholder-expectation-update", args=[expectation.pk]),
            {"description": "Rewritten", "type": "need", "priority": "low"},
        )
        delete = client.post(reverse("context:stakeholder-expectation-delete", args=[expectation.pk]))

        expectation.refresh_from_db()
        assert (add.status_code, edit.status_code, delete.status_code) == (404, 404, 404)
        assert StakeholderExpectation.objects.count() == 1 and expectation.description != "Rewritten"


class TestTheApiAndTheMcpServer:
    def test_they_report_the_completeness_of_one_record(self, admin):
        issue, stakeholder = IssueFactory(), StakeholderFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/context/issues/{issue.pk}/").json()
        one = one.get("data", one)
        other = api.get(f"/api/v1/context/stakeholders/{stakeholder.pk}/").json()
        other = other.get("data", other)

        assert [item["key"] for item in one["completeness"]["missing"]] == ["description", "review_date"]
        assert [item["key"] for item in other["completeness"]["missing"]] == ["expectations", "contact"]
        assert [item["key"] for item in _mcp(admin, "get_issue", {"id": str(issue.pk)})["completeness"]["missing"]] == [
            "description", "review_date",
        ]
        assert [
            item["key"] for item in _mcp(admin, "get_stakeholder", {"id": str(stakeholder.pk)})["completeness"]["missing"]
        ] == ["expectations", "contact"]

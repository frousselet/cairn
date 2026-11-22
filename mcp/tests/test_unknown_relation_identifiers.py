# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An identifier that names no record, in a relation written through MCP.

The generic create, update and batch tools write a many-to-many relation with
``.set(ids)``. For a caller whose reach is not limited to some scopes (an
administrator, a group allowed every scope), nothing checked the identifiers
first : one that matches no row reached the database, whose foreign key
refused it with its own message (on PostgreSQL, ``insert or update on table
... violates foreign key constraint``), and a string that is no identifier
came back as Django's raw ``['... is not a valid UUID.']``. SQLite checks its
foreign keys at the end of a transaction, which the test suite rolls back :
there the row was written without a word.

They are refused before anything is written, in the words of an unknown
identifier : ``<Model> not found (<parameter>)``.
"""

import json
import uuid

import pytest

from accounts.tests.factories import UserFactory
from context.models import StakeholderFeedback
from context.tests.factories import IssueFactory, ScopeFactory, StakeholderFeedbackFactory
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db


def _call(user, tool, arguments):
    server = McpServer()
    register_all_tools(server)
    result = server.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments},
    }), user)
    return result["result"]


@pytest.fixture
def admin():
    return UserFactory(is_superuser=True)


class TestAnUnknownIdentifierIsRefused:
    def test_on_an_update_nothing_is_written(self, admin):
        feedback = StakeholderFeedbackFactory(subject="Before")
        known = IssueFactory()

        result = _call(admin, "update_stakeholder_feedback", {
            "id": str(feedback.pk), "subject": "After", "linked_issue_ids": [str(known.pk), str(uuid.uuid4())],
        })

        assert result.get("isError") is True
        assert "Issue not found (linked_issue_ids)" in result["content"][0]["text"]
        feedback.refresh_from_db()
        assert feedback.subject == "Before"
        assert not feedback.linked_issues.exists()

    def test_a_string_that_is_no_identifier_reads_the_same(self, admin):
        feedback = StakeholderFeedbackFactory()

        result = _call(admin, "update_stakeholder_feedback", {"id": str(feedback.pk), "linked_issue_ids": ["not-a-uuid"]})

        text = result["content"][0]["text"]
        assert "Issue not found (linked_issue_ids)" in text
        assert "is not a valid UUID" not in text

    def test_a_single_identifier_instead_of_a_list_is_refused(self, admin):
        feedback = StakeholderFeedbackFactory()
        issue = IssueFactory()

        result = _call(admin, "update_stakeholder_feedback", {"id": str(feedback.pk), "linked_issue_ids": str(issue.pk)})

        assert "linked_issue_ids : give a list of identifiers." in result["content"][0]["text"]
        assert not feedback.linked_issues.exists()

    def test_a_relation_to_people_is_checked_too(self, admin):
        """The scopes and the issues are scoped models, which a limited caller
        had checked already; people are not, and nobody checked them."""
        scope = ScopeFactory()

        result = _call(admin, "update_scope", {"id": str(scope.pk), "manager_ids": [str(uuid.uuid4())]})

        assert "User not found (manager_ids)" in result["content"][0]["text"]
        assert not scope.managers.exists()

    def test_a_batch_refuses_the_item_and_keeps_the_others(self, admin):
        scope = ScopeFactory()

        result = _call(admin, "batch_create_scopes", {"items": [
            {"name": "Good", "description": "The head office.", "manager_ids": [str(admin.pk)]},
            {"name": "Bad", "description": "A branch.", "manager_ids": [str(uuid.uuid4())]},
        ]})

        text = result["content"][0]["text"]
        assert "User not found (manager_ids)" in text
        assert scope.__class__.objects.filter(name="Good").exists()
        assert not scope.__class__.objects.filter(name="Bad").exists()


class TestKnownIdentifiersAreStillWritten:
    def test_an_update_links_what_exists(self, admin):
        feedback = StakeholderFeedbackFactory()
        issue = IssueFactory()

        _call(admin, "update_stakeholder_feedback", {"id": str(feedback.pk), "linked_issue_ids": [str(issue.pk)]})

        assert list(StakeholderFeedback.objects.get(pk=feedback.pk).linked_issues.all()) == [issue]

    def test_an_empty_list_clears_the_relation(self, admin):
        feedback = StakeholderFeedbackFactory()
        feedback.linked_issues.set([IssueFactory()])

        _call(admin, "update_stakeholder_feedback", {"id": str(feedback.pk), "linked_issue_ids": []})

        assert not feedback.linked_issues.exists()

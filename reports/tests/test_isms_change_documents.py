# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Module 7 integration with the management review (README §1.3, RG-DOC-20) :
`IsmsChange.affected_documents` and the "Documents due for review" card."""

import json
from datetime import date, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Group
from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from documents.constants import POLICY_RETIRED
from documents.tests.factories import PolicyFactory, PolicyVersionFactory, put_in_force
from mcp.server import McpServer
from mcp.tools import register_all_tools
from reports.forms import IsmsChangeForm
from reports.management_review_views import documents_due_for_review
from reports.tests.factories import IsmsChangeFactory, ManagementReviewFactory

pytestmark = pytest.mark.django_db


def _active_policy(**kwargs):
    version = PolicyVersionFactory(policy=PolicyFactory(**kwargs))
    put_in_force(version)
    policy = version.policy
    policy.refresh_from_db()
    return policy


def _data(response):
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


class TestIsmsChangeForm:
    def test_picker_offers_active_documents_only(self):
        active = _active_policy()
        draft = PolicyFactory()
        choices = set(IsmsChangeForm().fields["affected_documents"].queryset)
        assert active in choices
        assert draft not in choices

    def test_picker_keeps_a_link_to_a_document_retired_since(self):
        policy = _active_policy()
        change = IsmsChangeFactory()
        change.affected_documents.add(policy)
        policy.transition_to(POLICY_RETIRED, policy.owner, comment="Replaced")
        choices = set(IsmsChangeForm(instance=change).fields["affected_documents"].queryset)
        assert policy in choices
        assert policy not in set(IsmsChangeForm().fields["affected_documents"].queryset)

    def test_legacy_free_text_field_is_kept(self):
        assert "affected_policies" in IsmsChangeForm().fields


class TestIsmsChangeAPI:
    def setup_method(self):
        self.client = APIClient()
        self.client.force_authenticate(UserFactory(is_superuser=True))

    def test_create_with_affected_document_ids(self):
        policy = _active_policy()
        review = ManagementReviewFactory()
        owner = UserFactory()
        response = self.client.post("/api/v1/reports/isms-changes/", {
            "review": str(review.pk), "change_type": "policy", "title": "Revise",
            "description": "d", "owner": str(owner.pk), "status": "proposed",
            "affected_document_ids": [str(policy.pk)],
        }, format="json")
        assert response.status_code == 201, response.content
        assert _data(response)["affected_document_ids"] == [str(policy.pk)]
        assert list(policy.isms_changes.all())[0].title == "Revise"

    def test_refuses_to_link_a_draft_document(self):
        draft = PolicyFactory()
        review = ManagementReviewFactory()
        response = self.client.post("/api/v1/reports/isms-changes/", {
            "review": str(review.pk), "change_type": "policy", "title": "Revise",
            "description": "d", "owner": str(UserFactory().pk), "status": "proposed",
            "affected_document_ids": [str(draft.pk)],
        }, format="json")
        assert response.status_code == 400

    def test_update_keeps_an_existing_link_to_a_retired_document(self):
        policy = _active_policy()
        change = IsmsChangeFactory()
        change.affected_documents.add(policy)
        policy.transition_to(POLICY_RETIRED, policy.owner, comment="Replaced")
        response = self.client.patch(
            f"/api/v1/reports/isms-changes/{change.pk}/",
            {"title": "Renamed", "affected_document_ids": [str(policy.pk)]}, format="json",
        )
        assert response.status_code == 200, response.content


class TestIsmsChangeMCP:
    def setup_method(self):
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def _call(self, name, arguments):
        result = self.srv.handle_request(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }), self.user)
        return json.loads(result["result"]["content"][0]["text"])

    def test_create_and_list_with_documents(self):
        policy = _active_policy()
        review = ManagementReviewFactory()
        created = self._call("create_isms_change", {
            "review_id": str(review.pk), "title": "Revise the policy", "description": "d",
            "owner_id": str(UserFactory().pk), "affected_document_ids": [str(policy.pk)],
        })
        assert created["affected_document_ids"] == [str(policy.pk)]
        listed = self._call("list_isms_changes", {"review_id": str(review.pk)})
        assert listed[0]["affected_document_ids"] == [str(policy.pk)]

    def test_create_refuses_a_draft_document(self):
        review = ManagementReviewFactory()
        result = self._call("create_isms_change", {
            "review_id": str(review.pk), "title": "x", "description": "d",
            "owner_id": str(UserFactory().pk), "affected_document_ids": [str(PolicyFactory().pk)],
        })
        assert "error" in json.dumps(result).lower()
        assert not review.isms_changes.exists()


class TestDocumentsDueForReview:
    def _review(self, **kwargs):
        today = date.today()
        defaults = dict(period_start=today - timedelta(days=180), period_end=today + timedelta(days=30),
                        planned_date=today + timedelta(days=10))
        defaults.update(kwargs)
        return ManagementReviewFactory(**defaults)

    def test_lists_documents_due_in_the_period_or_overdue(self):
        today = date.today()
        in_period = _active_policy(next_review_override=today + timedelta(days=20))
        overdue = _active_policy(next_review_override=today - timedelta(days=400))
        later = _active_policy(next_review_override=today + timedelta(days=200))
        review = self._review()
        rows = documents_due_for_review(review, UserFactory(is_superuser=True))
        listed = {r["policy"] for r in rows}
        assert in_period in listed and overdue in listed
        assert later not in listed
        flags = {r["policy"]: r["overdue_at_review"] for r in rows}
        assert flags[overdue] is True
        assert flags[in_period] is False

    def test_draft_and_retired_documents_are_left_out(self):
        today = date.today()
        draft = PolicyFactory(next_review_override=today)
        retired = _active_policy(next_review_override=today)
        retired.transition_to(POLICY_RETIRED, retired.owner, comment="Gone")
        rows = documents_due_for_review(self._review(), UserFactory(is_superuser=True))
        listed = {r["policy"] for r in rows}
        assert draft not in listed and retired not in listed

    def test_review_scopes_narrow_the_register(self):
        today = date.today()
        mine, other = ScopeFactory(), ScopeFactory()
        inside = _active_policy(next_review_override=today)
        inside.scopes.set([mine])
        outside = _active_policy(next_review_override=today)
        outside.scopes.set([other])
        review = self._review()
        review.scopes.set([mine])
        listed = {r["policy"] for r in documents_due_for_review(review, UserFactory(is_superuser=True))}
        assert inside in listed and outside not in listed

    def test_hidden_without_the_read_permission(self):
        assert documents_due_for_review(self._review(), UserFactory()) is None

    def test_detail_page_renders_the_card_and_the_linked_documents(self):
        today = date.today()
        due = _active_policy(title="Access control policy", next_review_override=today)
        review = self._review()
        change = IsmsChangeFactory(review=review)
        change.affected_documents.add(due)
        user = UserFactory()
        Group.objects.get(name="Administrateur").users.add(user)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("reports:management-review-detail", args=[review.pk]))
        assert response.status_code == 200
        body = response.content.decode()
        assert "Documents due for review" in body
        assert due.reference in body
        assert reverse("documents:policy-detail", args=[due.pk]) in body

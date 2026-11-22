# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Stakeholder feedback has its pages.

What a stakeholder tells you about your security (a survey answer, a
complaint, a remark in a meeting) is an input of the management review (ISO
27001:2022 clause 9.3.2.e). It was recorded by the REST API and the MCP
server only : no page of the interface showed or wrote it. It has a register,
a page per feedback completed card by card, and a card on the page of its
stakeholder. The generic rules of the usability standard are held by
``core/tests/test_usability_standard.py``; what is particular to feedback is
held here.
"""

import json

import pytest
from django.urls import reverse

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from context.models import StakeholderFeedback
from context.tests.factories import (
    ScopeFactory,
    StakeholderExpectationFactory,
    StakeholderFactory,
    StakeholderFeedbackFactory,
)
from core.models import LifecycleEvent

pytestmark = pytest.mark.django_db


def _user_with(*codenames, scopes=None):
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    group.users.add(user)
    if scopes is not None:
        group.allowed_scopes.set(scopes)
        group.all_scopes = False
        group.save()
    return user


DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


class TestTheRegister:
    def test_it_lists_the_feedback_with_its_handling_and_its_step(self, client):
        feedback = StakeholderFeedbackFactory(subject="Late notice of the outage", status="addressed")
        client.force_login(_user_with("context.stakeholder_feedback.read"))

        html = client.get(reverse("context:feedback-list")).content.decode()

        assert "Late notice of the outage" in html
        assert feedback.get_absolute_url() in html
        assert "Addressed" in html

    def test_it_is_a_view_of_the_stakeholders_entry(self, client):
        """One menu line for the stakeholders and their feedback, a switcher between the two registers."""
        client.force_login(_user_with("context.stakeholder.read", "context.stakeholder_feedback.read"))

        html = client.get(reverse("context:feedback-list")).content.decode()

        feedback_list = reverse("context:feedback-list")
        assert f'href="{feedback_list}" class="page-switcher__link is-current" aria-current="page"' in html
        assert f'href="{reverse("context:stakeholder-list")}" class="page-switcher__link"' in html
        assert f'{reverse("context:stakeholder-list")} {feedback_list}' in html  # one entry, both addresses

    def test_who_may_not_read_feedback_is_refused(self, client):
        client.force_login(_user_with("context.stakeholder.read"))

        assert client.get(reverse("context:feedback-list")).status_code in (302, 403)

    def test_an_empty_register_says_what_a_feedback_is(self, client):
        client.force_login(UserFactory(is_superuser=True))

        html = client.get(reverse("context:feedback-list")).content.decode()

        assert "No feedback yet." in html


class TestCreatingAFeedback:
    def test_from_the_page_of_its_stakeholder_it_is_not_asked_again(self, client):
        stakeholder = StakeholderFactory()
        client.force_login(UserFactory(is_superuser=True))
        url = reverse("context:feedback-create") + f"?stakeholder={stakeholder.pk}"

        html = client.get(url, **DRAWER).content.decode()

        assert f'type="hidden" name="stakeholder" value="{stakeholder.pk}"' in html

    def test_it_lands_on_the_page_of_the_feedback(self, client):
        stakeholder = StakeholderFactory()
        client.force_login(UserFactory(is_superuser=True))

        response = client.post(reverse("context:feedback-create") + f"?stakeholder={stakeholder.pk}", {
            "stakeholder": str(stakeholder.pk), "channel": "complaint", "received_date": "2026-11-02",
            "subject": "Late notice", "content": "We learned of the outage too late.",
        }, **DRAWER)

        feedback = StakeholderFeedback.objects.get()
        assert response.status_code == 204
        assert feedback.get_absolute_url() in response.headers.get("HX-Redirect", "") + response.headers.get("HX-Location", "")
        assert (feedback.stakeholder, feedback.status) == (stakeholder, "new")

    def test_a_stakeholder_out_of_reach_is_not_the_answer(self, client):
        mine, other = ScopeFactory(), ScopeFactory()
        stakeholder = StakeholderFactory(scopes=[other])
        client.force_login(_user_with(
            "context.stakeholder_feedback.create", "context.stakeholder.read", "context.scope.read", scopes=[mine],
        ))

        html = client.get(reverse("context:feedback-create") + f"?stakeholder={stakeholder.pk}", **DRAWER).content.decode()

        assert f'value="{stakeholder.pk}"' not in html


class TestThePageOfAFeedback:
    def test_it_shows_its_sections_and_its_lifecycle_bar(self, client):
        feedback = StakeholderFeedbackFactory()
        client.force_login(UserFactory(is_superuser=True))

        html = client.get(feedback.get_absolute_url()).content.decode()

        assert "data-lc-bar" in html
        for section in ("feedback", "assessment", "handling"):
            assert f"?section={section}" in html

    def test_it_lists_what_would_make_it_useful(self, client):
        feedback = StakeholderFeedbackFactory(status="addressed")
        client.force_login(UserFactory(is_superuser=True))

        html = client.get(feedback.get_absolute_url()).content.decode()

        assert "Assess the severity" in html
        assert "Write the response" in html

    def test_the_response_is_asked_once_the_feedback_is_handled(self):
        from core.completeness import completeness_of

        feedback = StakeholderFeedbackFactory(severity="low", status="new")
        assert [r.key for r in completeness_of(feedback).missing] == []
        feedback.status = "closed"
        assert [r.key for r in completeness_of(feedback).missing] == ["response"]

    def test_a_feedback_of_another_scope_answers_as_an_unknown_one(self, client):
        mine, other = ScopeFactory(), ScopeFactory()
        feedback = StakeholderFeedbackFactory(scopes=[other])
        client.force_login(_user_with("context.stakeholder_feedback.read", scopes=[mine]))

        assert client.get(feedback.get_absolute_url()).status_code == 404

    def test_the_stakeholder_page_lists_its_feedback(self, client):
        feedback = StakeholderFeedbackFactory(subject="Phishing drills seen as too frequent")
        client.force_login(UserFactory(is_superuser=True))

        html = client.get(feedback.stakeholder.get_absolute_url()).content.decode()

        assert "Phishing drills seen as too frequent" in html
        assert f'{reverse("context:feedback-create")}?stakeholder={feedback.stakeholder.pk}' in html


class TestItsLifecycle:
    def _url(self, feedback):
        return reverse("workflow:transition", kwargs={
            "app_label": "context", "model": "stakeholderfeedback", "pk": feedback.pk,
        })

    def test_who_may_change_it_submits_it_and_who_may_approve_validates_it(self, client):
        feedback = StakeholderFeedbackFactory()

        client.force_login(_user_with("context.stakeholder_feedback.read", "context.stakeholder_feedback.update"))
        client.post(self._url(feedback), {"target_status": "pending"})
        client.post(self._url(feedback), {"target_status": "validated"})
        feedback.refresh_from_db()
        assert feedback.workflow_state == "pending"

        client.force_login(_user_with(
            "context.stakeholder_feedback.read", "context.stakeholder_feedback.update",
            "context.stakeholder_feedback.approve",
        ))
        client.post(self._url(feedback), {"target_status": "validated"})
        feedback.refresh_from_db()
        assert feedback.workflow_state == "validated"
        assert LifecycleEvent.objects.filter(object_id=str(feedback.pk), to_step="validated").exists()

    def test_the_steering_role_holds_approve_and_a_contributor_does_not(self):
        from accounts.constants import SYSTEM_GROUPS

        assert SYSTEM_GROUPS["RSSI / DPO"]["filter"]("context.stakeholder_feedback.approve")
        assert not SYSTEM_GROUPS["Contributeur"]["filter"]("context.stakeholder_feedback.approve")


class TestTheOtherSurfaces:
    def _call(self, user, tool, arguments):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        server = McpServer()
        register_all_tools(server)
        result = server.handle_request(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments},
        }), user)
        return json.loads(result["result"]["content"][0]["text"])

    def test_mcp_reads_completes_moves_and_deletes_a_feedback(self):
        feedback = StakeholderFeedbackFactory(status="addressed")
        expectation = StakeholderExpectationFactory(stakeholder=feedback.stakeholder)
        admin = UserFactory(is_superuser=True)

        read = self._call(admin, "get_stakeholder_feedback", {"id": str(feedback.pk)})
        assert [line["key"] for line in read["completeness"]["missing"]] == ["severity", "response"]

        self._call(admin, "update_stakeholder_feedback", {
            "id": str(feedback.pk), "severity": "high", "response": "Notice moved to ten days ahead.",
            "linked_expectation_ids": [str(expectation.pk)],
        })
        feedback.refresh_from_db()
        assert (feedback.severity, list(feedback.linked_expectations.all())) == ("high", [expectation])

        self._call(admin, "transition_stakeholder_feedback", {"id": str(feedback.pk), "target_state": "pending"})
        feedback.refresh_from_db()
        assert feedback.workflow_state == "pending"

        # A feedback past its draft is kept : the lifecycle protects it.
        self._call(admin, "delete_stakeholder_feedback", {"id": str(feedback.pk)})
        assert StakeholderFeedback.objects.filter(pk=feedback.pk).exists()
        draft = StakeholderFeedbackFactory()
        self._call(admin, "delete_stakeholder_feedback", {"id": str(draft.pk)})
        assert not StakeholderFeedback.objects.filter(pk=draft.pk).exists()

    def test_mcp_refuses_a_validation_to_who_may_not_approve(self):
        feedback = StakeholderFeedbackFactory(workflow_state="pending")
        editor = _user_with("context.stakeholder_feedback.read", "context.stakeholder_feedback.update")

        self._call(editor, "transition_stakeholder_feedback", {"id": str(feedback.pk), "target_state": "validated"})

        feedback.refresh_from_db()
        assert feedback.workflow_state == "pending"

    def test_the_rest_api_gives_its_completeness_and_its_step(self, client):
        feedback = StakeholderFeedbackFactory()
        client.force_login(UserFactory(is_superuser=True))

        data = client.get(f"/api/v1/context/stakeholder-feedback/{feedback.pk}/").json()

        assert data["workflow_state"] == "draft"
        assert [line["key"] for line in data["completeness"]["missing"]] == ["severity"]

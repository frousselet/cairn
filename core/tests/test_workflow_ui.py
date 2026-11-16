# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Tests for the generic workflow UI surfaces (issue #105, phase 7a).

Covers the stepper context mixin, the shared transition endpoint and the
state badge tag, piloted on the Issue detail page (default workflow). Scope used
to be the pilot but it now runs the standardised lifecycle engine
(``core/lifecycle.py``), so the generic *default-workflow* UI is exercised here
on another entity that still runs ``core/workflow.py``.
"""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.models import Issue
from context.tests.factories import IssueFactory

pytestmark = pytest.mark.django_db


def _user_with_perms(*codenames):
    user = UserFactory()
    group = GroupFactory()
    for codename in codenames:
        module, feature, action = codename.split(".")
        perm = PermissionFactory(
            codename=codename, module=module, feature=feature, action=action,
        )
        group.permissions.add(perm)
    group.users.add(user)
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


class TestStepperContext:
    def test_draft_issue_offers_submit(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        response = client.get(reverse("context:issue-detail", args=[issue.pk]))
        assert response.status_code == 200
        steps = response.context["lc_steps"]
        assert [s["value"] for s in steps] == ["draft", "pending", "validated"]
        assert steps[0]["state"] == "current"
        assert steps[1]["actionable"] is True  # submit -> pending
        # Archived renders as a detached exit, not a main step.
        exits = response.context["lc_exits"]
        assert exits[0]["value"] == "archived"
        assert exits[0]["actionable"] is False  # draft cannot archive

    def test_pending_without_approve_permission_hides_validate(self):
        user = _user_with_perms("context.issue.read", "context.issue.update")
        issue = IssueFactory()
        issue.transition_to("pending")
        response = _client(user).get(reverse("context:issue-detail", args=[issue.pk]))
        steps = {s["value"]: s for s in response.context["lc_steps"]}
        assert steps["pending"]["state"] == "current"
        assert steps["validated"]["actionable"] is False  # not offered without .approve
        # Send back to draft (update) is offered.
        assert steps["draft"]["actionable"] is True

    def test_validated_issue_offers_archive_branch(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory(workflow_state="validated")
        response = client.get(reverse("context:issue-detail", args=[issue.pk]))
        archived = next(e for e in response.context["lc_exits"] if e["value"] == "archived")
        assert archived["actionable"] is True  # validated can archive

    def test_stepper_renders_in_page(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        response = client.get(reverse("context:issue-detail", args=[issue.pk]))
        content = response.content.decode()
        assert "lifecycle-stepper-" in content
        assert "lifecycleCommentModal" in content


class TestTransitionEndpoint:
    def _url(self, issue):
        return reverse(
            "workflow:transition",
            kwargs={"app_label": "context", "model": "issue", "pk": issue.pk},
        )

    def test_submit_transition(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        response = client.post(self._url(issue), {"target_status": "pending"})
        assert response.status_code == 302
        issue.refresh_from_db()
        assert issue.workflow_state == "pending"

    def test_permission_denied_keeps_state(self):
        user = _user_with_perms("context.issue.read", "context.issue.update")
        issue = IssueFactory()
        issue.transition_to("pending")
        response = _client(user).post(self._url(issue), {"target_status": "validated"})
        assert response.status_code == 302
        issue.refresh_from_db()
        assert issue.workflow_state == "pending"

    def test_illegal_transition_keeps_state(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        response = client.post(self._url(issue), {"target_status": "archived"})
        assert response.status_code == 302
        issue.refresh_from_db()
        assert issue.workflow_state == "draft"

    def test_unsafe_referer_falls_back_to_root(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        response = client.post(
            self._url(issue),
            {"target_status": "pending"},
            HTTP_REFERER="https://evil.example.com/phish",
        )
        assert response.status_code == 302
        assert response["Location"] == "/"

    def test_safe_next_is_honoured(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        detail = reverse("context:issue-detail", args=[issue.pk])
        response = client.post(
            self._url(issue), {"target_status": "pending", "next": detail},
        )
        assert response["Location"] == detail

    def test_unknown_model_is_404(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        url = self._url(issue).replace("/issue/", "/nope/")
        response = client.post(url, {"target_status": "pending"})
        assert response.status_code == 404

    def test_comment_required_transition_rejected_without_comment(self):
        """A requires_comment transition fails politely without a comment."""
        from compliance.constants import ActionPlanStatus
        from compliance.tests.factories import ComplianceActionPlanFactory

        client = _client(UserFactory(is_superuser=True))
        plan = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        url = reverse(
            "workflow:transition",
            kwargs={"app_label": "compliance", "model": "complianceactionplan", "pk": plan.pk},
        )
        response = client.post(url, {"target_status": "to_define"})
        assert response.status_code == 302
        plan.refresh_from_db()
        assert plan.status == "to_validate"
        response = client.post(
            url, {"target_status": "to_define", "comment": "Too vague"},
        )
        plan.refresh_from_db()
        assert plan.status == "to_define"


class TestStepperRollout:
    def test_risk_detail_renders_generic_stepper(self):
        from risks.tests.factories import RiskFactory

        client = _client(UserFactory(is_superuser=True))
        risk = RiskFactory()
        response = client.get(reverse("risks:risk-detail", args=[risk.pk]))
        assert response.status_code == 200
        assert "lifecycle-stepper-" in response.content.decode()
        steps = response.context["lc_steps"]
        assert steps[0]["value"] == "draft"
        assert steps[0]["state"] == "current"

    def test_assessment_detail_uses_bespoke_transition_url(self):
        from datetime import date

        from compliance.tests.factories import (
            ComplianceAssessmentFactory,
            FrameworkFactory,
        )

        client = _client(UserFactory(is_superuser=True))
        assessment = ComplianceAssessmentFactory(
            assessment_start_date=date(2026, 1, 1),
            assessment_end_date=date(2026, 6, 30),
        )
        assessment.frameworks.add(FrameworkFactory())
        response = client.get(
            reverse("compliance:assessment-detail", args=[assessment.pk])
        )
        assert response.status_code == 200
        assert response.context["lc_transition_url"] == reverse(
            "compliance:assessment-transition", args=[assessment.pk]
        )
        # The bespoke endpoint (required-fields gating, close side effects)
        # accepts the shared component's parameter name.
        response = client.post(
            response.context["lc_transition_url"], {"target_status": "planned"},
        )
        assessment.refresh_from_db()
        assert assessment.status == "planned"
        assert assessment.workflow_state == "planned"


class TestWorkflowBadgeTag:
    def test_badge_renders_tone_and_label(self):
        from helpers.templatetags.workflow_tags import workflow_badge

        issue = IssueFactory(workflow_state="validated")
        ctx = workflow_badge(issue)
        assert ctx["badge_class"] == "success"
        assert str(ctx["label"])  # translated label present

    def test_badge_handles_stale_state(self):
        from helpers.templatetags.workflow_tags import workflow_badge

        issue = IssueFactory()
        Issue.objects.filter(pk=issue.pk).update(workflow_state="ghost")
        issue.refresh_from_db()
        ctx = workflow_badge(issue)
        assert ctx["badge_class"] == "secondary"


class TestLifecycleBar:
    """The compact bar that shows the lifecycle on every detail page."""

    def test_the_bar_is_the_default_rendering_and_the_graph_stays_available(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        content = client.get(reverse("context:issue-detail", args=[issue.pk])).content.decode()
        assert 'class="lc-bar' in content
        # The full directed graph is still in the page, in a collapsed panel
        # opened by the toggle, and is not drawn until then.
        assert "data-lc-graph-panel" in content
        assert 'class="collapse lc-bar__graph"' in content
        assert "lc-bar__toggle" in content
        assert "data-lc-nodes" in content

    def test_a_possible_move_is_a_button_named_after_the_transition(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        response = client.get(reverse("context:issue-detail", args=[issue.pk]))
        steps = {s["value"]: s for s in response.context["lc_bar_steps"]}
        assert steps["draft"]["path"] == "current"
        assert steps["pending"]["path"] == "ahead"
        assert steps["pending"]["direction"] == "forward"
        content = response.content.decode()
        # The button reads "Submit" (the transition), not "Pending" (the step).
        assert str(steps["pending"]["action_label"]) in content
        assert 'name="target_status" value="pending"' in content

    def test_a_way_back_is_offered_as_a_quiet_button(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory()
        issue.transition_to("pending")
        response = client.get(reverse("context:issue-detail", args=[issue.pk]))
        steps = {s["value"]: s for s in response.context["lc_bar_steps"]}
        assert steps["draft"]["path"] == "done"
        assert steps["draft"]["actionable"] is True
        assert steps["draft"]["direction"] == "back"
        assert steps["validated"]["direction"] == "forward"

    def test_the_exit_is_only_shown_when_it_can_be_taken(self):
        client = _client(UserFactory(is_superuser=True))
        draft = IssueFactory()
        response = client.get(reverse("context:issue-detail", args=[draft.pk]))
        assert response.context["lc_bar_exits"] == []  # a draft cannot be archived

        validated = IssueFactory(workflow_state="validated")
        response = client.get(reverse("context:issue-detail", args=[validated.pk]))
        exits = response.context["lc_bar_exits"]
        assert [e["value"] for e in exits] == ["archived"]
        assert exits[0]["direction"] == "exit"

    def test_a_branch_that_was_not_taken_is_left_off_the_bar(self):
        """A compliant supplier never went through the non-compliant branch :
        the declaration order alone would list (and tick) those steps."""
        from assets.tests.factories import SupplierFactory

        client = _client(UserFactory(is_superuser=True))
        supplier = SupplierFactory(workflow_state="compliant")
        response = client.get(reverse("assets:supplier-detail", args=[supplier.pk]))
        steps = {s["value"]: s for s in response.context["lc_steps"]}
        assert steps["evaluation"]["path"] == "done"
        assert steps["compliant"]["path"] == "current"
        assert steps["non_compliant"]["path"] == "off"
        assert steps["compensatory_measures"]["path"] == "off"
        on_bar = [s["value"] for s in response.context["lc_bar_steps"]]
        assert "non_compliant" not in on_bar
        assert "compensatory_measures" not in on_bar
        # The new review cycle loops back to an earlier step : a way back.
        assert steps["risk_questionnaire"]["actionable"] is True
        assert steps["risk_questionnaire"]["direction"] == "back"
        # The graph payload still describes the whole lifecycle.
        import json

        node_ids = {n["id"] for n in json.loads(response.context["lc_graph_nodes"])}
        assert {"non_compliant", "compensatory_measures"} <= node_ids

    def test_a_long_lifecycle_folds_its_completed_steps(self):
        from risks.tests.factories import RiskFactory

        client = _client(UserFactory(is_superuser=True))
        risk = RiskFactory(workflow_state="treatment_in_progress")
        response = client.get(reverse("risks:risk-detail", args=[risk.pk]))
        assert response.context["lc_bar_dense"] is True
        assert "lc-bar--dense" in response.content.decode()

    def test_an_archived_record_shows_its_exit_as_the_current_step(self):
        client = _client(UserFactory(is_superuser=True))
        issue = IssueFactory(workflow_state="archived")
        response = client.get(reverse("context:issue-detail", args=[issue.pk]))
        exits = response.context["lc_bar_exits"]
        assert exits and exits[0]["path"] == "current"
        assert all(s["path"] != "current" for s in response.context["lc_bar_steps"])

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

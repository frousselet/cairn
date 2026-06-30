"""API tests for the persistent management review workflow."""

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from compliance.models import ComplianceActionPlan
from reports.constants import ManagementReviewStatus
from reports.models import ManagementReview

from .factories import (
    IsmsChangeFactory,
    ManagementReviewDecisionFactory,
    ManagementReviewFactory,
)


pytestmark = pytest.mark.django_db


def _data(response):
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


class TestManagementReviewAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        ManagementReviewFactory.create_batch(3)
        response = self.client.get("/api/v1/reports/management-reviews/")
        assert response.status_code == 200
        data = _data(response)
        # DRF default pagination returns a dict with "results"; non-paginated returns a list
        items = data["results"] if isinstance(data, dict) and "results" in data else data
        assert len(items) == 3

    def test_create(self):
        today = date.today()
        response = self.client.post(
            "/api/v1/reports/management-reviews/",
            {
                "title": "Revue annuelle 2026",
                "frequency": "annual",
                "period_start": (today - timedelta(days=365)).isoformat(),
                "period_end": today.isoformat(),
                "planned_date": today.isoformat(),
                "facilitator": str(self.user.pk),
            },
            format="json",
        )
        assert response.status_code == 201
        assert ManagementReview.objects.filter(
            title="Revue annuelle 2026",
        ).exists()

    def test_retrieve_detail_includes_decisions(self):
        review = ManagementReviewFactory()
        ManagementReviewDecisionFactory.create_batch(2, review=review)
        response = self.client.get(
            f"/api/v1/reports/management-reviews/{review.pk}/",
        )
        assert response.status_code == 200
        data = _data(response)
        assert "decisions" in data
        assert len(data["decisions"]) == 2

    def test_transition_forward(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        response = self.client.post(
            f"/api/v1/reports/management-reviews/{review.pk}/transition/",
            {"target_status": "in_preparation"},
            format="json",
        )
        assert response.status_code == 200
        review.refresh_from_db()
        assert review.status == ManagementReviewStatus.IN_PREPARATION

    def test_transition_invalid_returns_400(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        response = self.client.post(
            f"/api/v1/reports/management-reviews/{review.pk}/transition/",
            {"target_status": "closed"},
            format="json",
        )
        assert response.status_code == 400

    def test_cancellation_requires_comment(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        response = self.client.post(
            f"/api/v1/reports/management-reviews/{review.pk}/transition/",
            {"target_status": "cancelled", "comment": ""},
            format="json",
        )
        assert response.status_code == 400

    def test_closure_creates_snapshot(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.HELD)
        ManagementReviewDecisionFactory(review=review)
        response = self.client.post(
            f"/api/v1/reports/management-reviews/{review.pk}/transition/",
            {"target_status": "closed"},
            format="json",
        )
        assert response.status_code == 200
        review.refresh_from_db()
        assert review.status == ManagementReviewStatus.CLOSED
        assert review.has_snapshot

    def test_list_decisions_for_review(self):
        review = ManagementReviewFactory()
        ManagementReviewDecisionFactory.create_batch(3, review=review)
        response = self.client.get(
            f"/api/v1/reports/management-reviews/{review.pk}/decisions/",
        )
        assert response.status_code == 200
        data = _data(response)
        assert len(data) == 3

    def test_add_decision_via_nested_endpoint(self):
        review = ManagementReviewFactory()
        response = self.client.post(
            f"/api/v1/reports/management-reviews/{review.pk}/decisions/",
            {
                "category": "improvement",
                "title": "New decision",
                "description": "desc",
                "priority": "medium",
                "status": "pending",
            },
            format="json",
        )
        assert response.status_code == 201
        assert review.decisions.count() == 1

    def test_export_docx(self):
        review = ManagementReviewFactory()
        response = self.client.get(
            f"/api/v1/reports/management-reviews/{review.pk}/export/?fmt=docx",
        )
        assert response.status_code == 200
        assert response["Content-Type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml",
        )
        assert response.content[:2] == b"PK"  # ZIP magic bytes

    def test_unsupported_export_format(self):
        review = ManagementReviewFactory()
        response = self.client.get(
            f"/api/v1/reports/management-reviews/{review.pk}/export/?fmt=xyz",
        )
        assert response.status_code == 400


class TestDecisionPromoteAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_promote_creates_action_plan(self):
        decision = ManagementReviewDecisionFactory()
        response = self.client.post(
            f"/api/v1/reports/decisions/{decision.pk}/promote/",
            format="json",
        )
        assert response.status_code == 201
        decision.refresh_from_db()
        assert decision.linked_action_plan_id is not None
        plan = ComplianceActionPlan.objects.get(pk=decision.linked_action_plan_id)
        assert plan.originating_review == decision.review

    def test_promote_refuses_when_already_linked(self):
        decision = ManagementReviewDecisionFactory()
        # First promote
        self.client.post(
            f"/api/v1/reports/decisions/{decision.pk}/promote/",
            format="json",
        )
        # Second promote
        response = self.client.post(
            f"/api/v1/reports/decisions/{decision.pk}/promote/",
            format="json",
        )
        assert response.status_code == 400


class TestIsmsChangeAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        IsmsChangeFactory.create_batch(2)
        response = self.client.get("/api/v1/reports/isms-changes/")
        assert response.status_code == 200

    def test_add_via_nested_endpoint(self):
        review = ManagementReviewFactory()
        response = self.client.post(
            f"/api/v1/reports/management-reviews/{review.pk}/isms-changes/",
            {
                "change_type": "policy",
                "title": "Policy update",
                "description": "desc",
                "owner": str(self.user.pk),
                "status": "proposed",
            },
            format="json",
        )
        assert response.status_code == 201
        assert review.isms_changes.count() == 1


class TestPermissionGates:
    def setup_method(self):
        self.client = APIClient()
        # Non-superuser, no perms
        self.user = UserFactory(is_superuser=False)
        self.client.force_authenticate(user=self.user)

    def _grant(self, codename):
        from accounts.tests.factories import GroupFactory, PermissionFactory
        perm = PermissionFactory(codename=codename)
        group = GroupFactory()
        group.permissions.add(perm)
        group.users.add(self.user)

    def test_list_denied_without_perm(self):
        response = self.client.get("/api/v1/reports/management-reviews/")
        assert response.status_code == 403

    def test_list_allowed_with_read_perm(self):
        self._grant("reports.management_review.read")
        response = self.client.get("/api/v1/reports/management-reviews/")
        assert response.status_code == 200

    def test_closure_denied_without_approve_perm(self):
        self._grant("reports.management_review.read")
        self._grant("reports.management_review.update")
        review = ManagementReviewFactory(status=ManagementReviewStatus.HELD)
        ManagementReviewDecisionFactory(review=review)
        response = self.client.post(
            f"/api/v1/reports/management-reviews/{review.pk}/transition/",
            {"target_status": "closed"},
            format="json",
        )
        assert response.status_code == 403


class TestStakeholderFeedbackAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_create_feedback(self):
        from context.models import Stakeholder
        from context.tests.factories import ScopeFactory
        stakeholder = Stakeholder.objects.create(
            name="SH", type="internal",
            category="employees", influence_level="medium",
            interest_level="medium", status="active",
        )
        scope = ScopeFactory()
        response = self.client.post(
            "/api/v1/context/stakeholder-feedback/",
            {
                "stakeholder": str(stakeholder.pk),
                "channel": "complaint",
                "received_date": date.today().isoformat(),
                "subject": "Request",
                "content": "Some content",
                "status": "new",
                "scopes": [str(scope.pk)],
            },
            format="json",
        )
        assert response.status_code == 201

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A management review is planned short, then completed on its page.

What every entity of the usability standard owes (the dialog, the landing,
the sections, the empty register) is checked in
``core/tests/test_usability_standard.py``. Here, what is the review's own :
the dialog asks the frequency (never answered for the reader) and makes the
planner its facilitator; the closure waits for an owner and a due date on
every decision, on every surface; the page lists what is advised and leads to
the participants, which are listed on their own form; the texts typed in the
editor are shown formatted.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from reports.constants import ManagementReviewStatus
from reports.forms import ManagementReviewCreateForm
from reports.models import ManagementReview
from reports.tests.factories import ManagementReviewDecisionFactory, ManagementReviewFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


def _held(admin, **fields):
    review = ManagementReviewFactory(**fields)
    review.transition_to(ManagementReviewStatus.IN_PREPARATION, admin)
    review.transition_to(ManagementReviewStatus.HELD, admin)
    return review


class TestAReviewIsPlannedShort:
    def test_it_asks_the_title_the_frequency_the_period_the_date_and_the_scopes(self, admin):
        ScopeFactory()
        ScopeFactory()
        form = ManagementReviewCreateForm(user=admin)
        frequency = form.fields["frequency"]

        assert sorted(form.fields) == ["frequency", "period_end", "period_start", "planned_date", "scopes", "title"]
        assert frequency.required and [value for value, _label in frequency.choices][0] == ""

    def test_whoever_plans_it_facilitates_it(self, client, admin):
        scope = ScopeFactory()

        response = client.post(reverse("reports:management-review-new"), {
            "title": "Annual management review 2026", "frequency": "annual", "scopes": [str(scope.pk)],
            "period_start": "2026-01-01", "period_end": "2026-12-31", "planned_date": "2027-01-15",
        }, **DRAWER)
        review = ManagementReview.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == review.get_absolute_url()
        assert (review.facilitator, review.created_by) == (admin, admin)


class TestTheClosureWaitsForItsDecisions:
    def test_a_fresh_review_is_advised_what_to_prepare(self, admin):
        review = ManagementReviewFactory()

        assert _missing(review) == ([], ["approver", "agenda", "participants", "next_review_date"])

    def test_the_closure_waits_for_an_owner_and_a_due_date_on_every_decision(self, admin):
        review = _held(admin, summary="Security held up.")
        ManagementReviewDecisionFactory(review=review, owner=None)

        assert _missing(review)[0] == ["decisions"]
        with pytest.raises(ValueError):
            review.transition_to(ManagementReviewStatus.CLOSED, admin)
        review.refresh_from_db()
        assert review.status == ManagementReviewStatus.HELD

        review.decisions.update(owner=admin)
        review.transition_to(ManagementReviewStatus.CLOSED, admin)
        assert review.status == ManagementReviewStatus.CLOSED

    def test_once_held_the_executive_summary_is_advised(self, admin):
        review = _held(admin)

        assert "summary" in _missing(review)[1]


class TestThePageOfTheReview:
    def test_it_lists_what_is_missing_and_leads_to_the_participants(self, client, admin):
        review = ManagementReviewFactory()
        participants = reverse("reports:management-review-participants", args=[review.pk])

        html = client.get(review.get_absolute_url()).content.decode()

        assert "Fill in the agenda" in html and "List the participants" in html
        assert f'href="{participants}"' in html

    def test_the_participants_are_listed_on_their_own_form(self, client, admin):
        review = ManagementReviewFactory()
        url = reverse("reports:management-review-participants", args=[review.pk])
        prefix = "participants"

        assert client.get(url).status_code == 200
        response = client.post(url, {
            f"{prefix}-TOTAL_FORMS": "1", f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-0-user": "", f"{prefix}-0-external_name": "Board chair",
            f"{prefix}-0-external_role": "Chief executive", f"{prefix}-0-role": "decision_maker",
        })

        assert response.status_code == 302 and response["Location"] == review.get_absolute_url()
        assert [p.external_name for p in review.participants.all()] == ["Board chair"]

    def test_the_texts_typed_in_the_editor_are_shown_formatted(self, client, admin):
        review = ManagementReviewFactory(agenda="<p>Review the <b>incidents</b>.</p><script>x()</script>")

        html = client.get(review.get_absolute_url()).content.decode()

        assert "<b>incidents</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_and_the_mcp_server_say_what_the_closure_waits_for(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        review = _held(admin)
        ManagementReviewDecisionFactory(review=review, due_date=None)
        api = APIClient()
        api.force_authenticate(user=admin)
        server = McpServer()
        register_all_tools(server)

        body = api.get(f"/api/v1/reports/management-reviews/{review.pk}/").json()
        body = body.get("data", body)
        read = server.get_tool("get_management_review")["handler"](admin, {"id": str(review.pk)})

        assert [item["key"] for item in body["completeness"]["missing"] if item["blocking"]] == ["decisions"]
        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == ["decisions"]


class TestTheRowsOfThePage:
    def test_a_comment_typed_in_the_editor_is_shown_formatted(self, client, admin):
        from reports.tests.factories import ManagementReviewCommentFactory

        comment = ManagementReviewCommentFactory(content="<p>Agreed <b>budget</b>.</p><script>x()</script>")

        html = client.get(comment.review.get_absolute_url()).content.decode()

        assert "<b>budget</b>" in html and "<script>x()</script>" not in html

    def test_only_a_saved_participant_offers_its_deletion(self, client, admin):
        from reports.tests.factories import ManagementReviewParticipantFactory

        participant = ManagementReviewParticipantFactory()
        url = reverse("reports:management-review-participants", args=[participant.review.pk])

        html = client.get(url).content.decode()

        assert html.count('name="participants-0-DELETE"') == 1 and 'name="participants-1-DELETE"' not in html

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A post-incident review is opened short, then written on its page.

What every form of the usability standard owes (its size, its helpers, its
labels) is checked in ``core/tests/test_usability_standard.py``. The review
hangs under its incident, so its page is tested here : the dialog asks when it
is held, who runs it and who takes part, the response plan being the
incident's; it lands on the review; each step waits for its part (the root
cause and the search for similar incidents before the submission, the
effectiveness review date before the approval, the verdict and its reviewer
before the verification), on every surface, and a refused verification stamps
nothing; each card opens its section; the texts typed in the editor are shown
formatted.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from incidents.forms import PostIncidentReviewCreateForm, PostIncidentReviewForm
from incidents.models import PostIncidentReview
from incidents.tests.factories import IncidentFactory, IncidentResponsePlanFactory
from incidents.tests.helpers import (
    REVIEW_APPROVED,
    REVIEW_IN_PROGRESS,
    REVIEW_SUBMITTED,
    REVIEW_VERIFIED,
    approved_review,
    incident_in_review_phase,
    walk,
)

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


def _held_review(admin):
    """The incident's own review, held and not yet written."""
    review = incident_in_review_phase(admin).post_incident_review
    review.facilitator = admin
    review.save()
    return walk(review, REVIEW_IN_PROGRESS, user=admin)


class TestAReviewIsOpenedShort:
    def test_it_asks_when_who_runs_it_and_who_takes_part(self, admin):
        form = PostIncidentReviewCreateForm(incident=IncidentFactory(), user=admin)

        assert sorted(form.fields) == ["facilitator", "participants", "scheduled_date"]
        assert form.is_multistep is False
        # Whoever opens the review runs it unless they say otherwise.
        assert form.fields["facilitator"].initial == admin.pk

    def test_the_dialog_lands_on_the_review_under_the_incident_plan(self, client, admin):
        incident = IncidentFactory(response_plan=IncidentResponsePlanFactory())

        response = client.post(reverse("incidents:review-create", args=[incident.pk]), {
            "scheduled_date": "2026-02-01", "facilitator": admin.pk,
        }, **DRAWER)
        review = PostIncidentReview.objects.get()

        assert response.status_code == 204 and response["HX-Redirect"] == review.get_absolute_url()
        # The plan it concludes on is the incident's : the file knows it.
        assert (review.incident, review.facilitator, review.response_plan) == (
            incident, admin, incident.response_plan,
        )


    def test_a_second_review_is_refused_without_a_server_error(self, client, admin):
        incident = incident_in_review_phase(admin)

        response = client.post(reverse("incidents:review-create", args=[incident.pk]), {
            "scheduled_date": "2026-02-01", "facilitator": admin.pk,
        }, **DRAWER)

        assert response.status_code == 200 and "already has its post-incident review" in response.content.decode()
        assert PostIncidentReview.objects.filter(incident=incident).count() == 1


class TestEachStepWaitsForItsPart:
    def test_the_submission_waits_for_the_root_cause_and_the_search(self, admin):
        review = _held_review(admin)

        with pytest.raises(DomainRefusalError) as refusal:
            review.transition_to(REVIEW_SUBMITTED, admin)

        assert _missing(review)[0] == ["root_cause", "similar_incidents_checked"]
        assert "fill in the root cause" in str(refusal.value)

    def test_nothing_is_asked_of_a_review_not_yet_held(self, admin):
        review = incident_in_review_phase(admin).post_incident_review

        assert _missing(review)[0] == []

    def test_the_verification_waits_for_its_verdict_and_stamps_nothing(self, admin):
        review = approved_review(incident_in_review_phase(admin), admin)

        with pytest.raises(DomainRefusalError) as refusal:
            review.transition_to(REVIEW_VERIFIED, admin, comment="Checked a month later.")

        assert _missing(review)[0] == ["effectiveness_verdict", "effectiveness_reviewed_by"]
        assert "choose the effectiveness verdict" in str(refusal.value)
        assert review.effectiveness_reviewed_at is None
        review.refresh_from_db()
        assert review.workflow_state == REVIEW_APPROVED and review.effectiveness_reviewed_at is None

    def test_the_approval_waits_for_the_effectiveness_review_date(self, admin):
        review = _held_review(admin)
        review.root_cause = "An unpatched edge appliance."
        review.similar_incidents_checked = True
        review.save()
        walk(review, REVIEW_SUBMITTED, user=admin)

        with pytest.raises(DomainRefusalError) as refusal:
            review.transition_to(REVIEW_APPROVED, admin, comment="Reviewed with the board.")

        assert "set the effectiveness review date" in str(refusal.value)


class TestThePageOfTheReview:
    def test_it_lists_what_is_missing_and_opens_each_card(self, client, admin):
        review = _held_review(admin)
        edit = reverse("incidents:review-update", args=[review.pk])

        html = client.get(review.get_absolute_url()).content.decode()

        assert "Fill in the root cause" in html and "Check for similar incidents" in html
        for key in PostIncidentReviewForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_the_texts_typed_in_the_editor_are_shown_formatted(self, client, admin):
        review = _held_review(admin)
        review.root_cause = "<p>An <b>unpatched</b> appliance.</p><script>x()</script>"
        review.save()

        html = client.get(review.get_absolute_url()).content.decode()

        assert "<b>unpatched</b>" in html and "&lt;p&gt;" not in html and "<script>x()</script>" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_and_the_mcp_server_say_what_the_submission_waits_for(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        review = _held_review(admin)
        api = APIClient()
        api.force_authenticate(user=admin)
        server = McpServer()
        register_all_tools(server)

        body = api.get(f"/api/v1/incidents/post-incident-reviews/{review.pk}/").json()
        body = body.get("data", body)
        read = server.get_tool("get_post_incident_review")["handler"](admin, {"id": str(review.pk)})

        blocking = ["root_cause", "similar_incidents_checked"]
        assert [item["key"] for item in body["completeness"]["missing"] if item["blocking"]] == blocking
        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == blocking

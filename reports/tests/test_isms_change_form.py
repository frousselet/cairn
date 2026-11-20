# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An ISMS change is a row of the page of its review, created short.

What every form of the usability standard owes (its size, its helpers, its
labels) is checked in ``core/tests/test_usability_standard.py``. Here, what
is the row's own : the dialog, opened from the review, asks what changes, its
type (never answered for the reader), its owner (whoever records it, unless
they name someone else) and its target date, and goes back to the review; the
row is edited whole, on one screen; its relations offer only what the user
may reach.
"""

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from core.tests.test_scoping import _member_of_one_scope
from reports.forms import IsmsChangeCreateForm, IsmsChangeForm
from reports.models import IsmsChange
from reports.tests.factories import IsmsChangeFactory, ManagementReviewFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


class TestAChangeIsRecordedShort:
    def test_it_asks_what_changes_its_type_its_owner_and_its_target_date(self, admin):
        form = IsmsChangeCreateForm(review=ManagementReviewFactory(), user=admin)
        change_type = form.fields["change_type"]

        assert sorted(form.fields) == ["change_type", "description", "owner", "target_date", "title"]
        assert form.is_multistep is False
        assert change_type.required and [value for value, _label in change_type.choices][0] == ""
        assert form["owner"].value() == admin.pk

    def test_the_dialog_opened_from_the_review_goes_back_to_it(self, client, admin):
        review = ManagementReviewFactory()

        response = client.post(reverse("reports:isms-change-create", args=[review.pk]), {
            "title": "Bring the industrial sites into the ISMS scope", "change_type": "scope",
            "description": "Extend the certified perimeter.", "owner": str(admin.pk),
        }, **DRAWER)
        change = IsmsChange.objects.get()

        assert response.status_code == 204 and response["HX-Trigger"] == "formSaved"
        assert (change.review, change.owner, change.change_type) == (review, admin, "scope")

    def test_opened_by_its_address_its_cancel_leads_back_to_the_review(self, client, admin):
        review = ManagementReviewFactory()

        html = client.get(reverse("reports:isms-change-create", args=[review.pk])).content.decode()

        assert f'href="{review.get_absolute_url()}"' in html


class TestTheRowIsEditedWhole:
    def test_on_one_screen(self, client, admin):
        change = IsmsChangeFactory()

        form = IsmsChangeForm(instance=change, user=admin)
        response = client.post(reverse("reports:isms-change-edit", args=[change.pk]), {
            "change_type": change.change_type, "status": "approved", "title": change.title,
            "description": change.description, "owner": str(change.owner_id),
        }, **DRAWER)
        change.refresh_from_db()

        assert form.is_multistep is False and IsmsChangeForm.section_keys() == ["change"]
        assert response.status_code == 204 and change.status == "approved"

    def test_its_scopes_are_those_the_user_may_reach(self, admin):
        mine, theirs = ScopeFactory(workflow_state="in_force"), ScopeFactory(workflow_state="in_force")
        user = _member_of_one_scope(mine)

        offered = IsmsChangeCreateForm(review=ManagementReviewFactory(), user=user)
        edit = IsmsChangeForm(instance=IsmsChangeFactory(), user=user).fields["affected_scopes"].queryset

        assert "affected_scopes" not in offered.fields
        assert mine in edit and theirs not in edit

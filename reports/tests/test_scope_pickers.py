# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The management review and ISMS change forms offer scopes by lifecycle.

Both forms used to filter scopes on a ``status`` field that Scope no longer
has (it runs a lifecycle), so opening either form raised a FieldError (500).
"""
import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from reports.forms import IsmsChangeForm, ManagementReviewModelForm
from reports.tests.factories import IsmsChangeFactory, ManagementReviewFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    c = Client()
    c.force_login(UserFactory(is_superuser=True))
    return c


def test_management_review_create_and_edit_pages_render(client):
    assert client.get(reverse("reports:management-review-new")).status_code == 200
    review = ManagementReviewFactory()
    assert client.get(reverse("reports:management-review-edit", args=[review.pk])).status_code == 200


def test_isms_change_edit_page_renders(client):
    change = IsmsChangeFactory()
    assert client.get(reverse("reports:isms-change-edit", args=[change.pk])).status_code == 200


def test_archived_scope_is_offered_only_when_already_linked():
    active = ScopeFactory(workflow_state="in_force")
    archived = ScopeFactory(workflow_state="archived")
    assert archived not in ManagementReviewModelForm().fields["scopes"].queryset
    assert active in ManagementReviewModelForm().fields["scopes"].queryset

    review = ManagementReviewFactory()
    review.scopes.add(archived)
    assert archived in ManagementReviewModelForm(instance=review).fields["scopes"].queryset

    change = IsmsChangeFactory()
    assert archived not in IsmsChangeForm(instance=change).fields["affected_scopes"].queryset
    change.affected_scopes.add(archived)
    assert archived in IsmsChangeForm(instance=change).fields["affected_scopes"].queryset

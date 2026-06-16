"""Tests for the generic lazy-loaded history panel endpoint."""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


def _url(obj):
    return reverse(
        "history:partial",
        kwargs={
            "app_label": obj._meta.app_label,
            "model": obj._meta.model_name,
            "pk": obj.pk,
        },
    )


def _client(user):
    client = Client()
    client.force_login(user)
    return client


def test_superuser_gets_rendered_timeline():
    scope = ScopeFactory()
    scope.name = "Renamed"
    scope.save()
    response = _client(UserFactory(is_superuser=True)).get(_url(scope))
    assert response.status_code == 200
    assert b"history-event" in response.content


def test_login_required():
    scope = ScopeFactory()
    response = Client().get(_url(scope))
    assert response.status_code in (302, 403)


def test_read_permission_required():
    scope = ScopeFactory()
    user = UserFactory()  # no permissions, not superuser
    response = _client(user).get(_url(scope))
    assert response.status_code == 403


def test_unknown_model_is_404():
    user = UserFactory(is_superuser=True)
    url = reverse(
        "history:partial",
        kwargs={"app_label": "context", "model": "doesnotexist",
                "pk": "00000000-0000-0000-0000-000000000000"},
    )
    assert _client(user).get(url).status_code == 404

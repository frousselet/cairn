"""Robustness tests for unbounded ?q= search input (#156).

A very long ?q= built an equally long SQL LIKE pattern, raising
OperationalError ("LIKE or GLOB pattern too complex") on SQLite (HTTP 500) and
acting as an unbounded-work DoS vector on any backend. The query is now clamped
before it reaches the database, on both the global search endpoint and the
shared list toolbar search.
"""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _superuser_client():
    user = UserFactory(is_superuser=True, is_staff=True)
    client = Client()
    client.force_login(user)
    return client, user


def test_global_search_long_query_does_not_500():
    client, _ = _superuser_client()
    resp = client.get(reverse("global-search"), {"q": "a" * 50000})
    assert resp.status_code == 200


def test_global_search_clamps_query_length():
    from core.views import GlobalSearchView

    assert GlobalSearchView.MAX_QUERY_LENGTH <= 256


def test_list_toolbar_long_query_does_not_500():
    client, _ = _superuser_client()
    resp = client.get(reverse("risks:risk-list"), {"q": "a" * 50000})
    assert resp.status_code == 200

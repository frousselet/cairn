# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The pages of an API list neither repeat nor skip a row."""

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.api.pagination import stable_order
from context.models import Issue
from context.tests.factories import IssueFactory

pytestmark = pytest.mark.django_db


def _order(queryset):
    return list(queryset.query.order_by)


def test_an_unordered_list_is_served_oldest_first_with_the_key_as_tie_breaker():
    assert not Issue.objects.all().ordered  # the premise : no default order
    ordered = stable_order(Issue.objects.all())
    assert ordered.ordered
    assert _order(ordered) == ["created_at", "pk"]


def test_an_order_with_ties_gets_the_key_as_tie_breaker():
    """`?ordering=impact_level` ties on every row sharing a level."""
    assert _order(stable_order(Issue.objects.order_by("-impact_level"))) == ["-impact_level", "pk"]


def test_an_order_already_ending_on_the_key_is_left_alone():
    queryset = Issue.objects.order_by("name", "-pk")
    assert _order(stable_order(queryset)) == ["name", "-pk"]


def test_a_values_query_is_left_alone():
    """Adding a column to its order would change what an aggregate groups by."""
    queryset = Issue.objects.values("type")
    assert stable_order(queryset) is queryset


def test_the_pages_of_a_list_partition_it():
    for _ in range(23):
        IssueFactory()
    client = APIClient()
    client.force_authenticate(UserFactory(is_superuser=True))
    seen = []
    for page in (1, 2, 3):
        response = client.get("/api/v1/context/issues/", {"page": page, "page_size": 10})
        assert response.status_code == 200
        seen.extend(row["id"] for row in response.json()["data"])
    assert len(seen) == 23
    assert len(set(seen)) == 23

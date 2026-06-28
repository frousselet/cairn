"""Robustness tests for the shared AdvancedFilterMixin ?rule= builder (#155).

A malformed rule (a non-dict, a non-UUID value for a relation field, an
oversized integer, or an out-of-calendar date) used to crash every list that
mounts the mixin with HTTP 500. These tests assert each path now degrades to a
200 (the bad rule is ignored).
"""

import json

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


# (url_name, raw ?rule= value) for each reported crash path.
_MALFORMED_RULES = [
    # Non-dict rule -> used to raise AttributeError ('int' has no 'get').
    ("reports:report-list", "5"),
    ("reports:report-list", json.dumps([1, 2, 3])),
    ("reports:report-list", "null"),
    # Relation field, non-UUID value -> used to raise ValidationError.
    ("context:scope-list", json.dumps({"f": "parent_scope", "o": "in", "v": ["bad"]})),
    # Relation field (Group, integer PK), oversized value -> used to OverflowError.
    ("accounts:user-list", json.dumps({"f": "groups", "o": "in", "v": [9 * 10**24]})),
    ("accounts:user-list", json.dumps({"f": "groups", "o": "in", "v": ["9" * 25]})),
    # Date field, out-of-calendar value -> used to raise ValueError.
    ("assets:support-asset-list", json.dumps({"f": "end_of_life_date", "o": "eq", "v": "2024-02-30"})),
]


@pytest.mark.parametrize("url_name,rule", _MALFORMED_RULES)
def test_malformed_rule_does_not_500(url_name, rule):
    client, _ = _superuser_client()
    resp = client.get(reverse(url_name), {"rule": rule})
    assert resp.status_code == 200, f"{url_name} rule={rule} -> {resp.status_code}"


def test_garbage_json_rule_ignored():
    client, _ = _superuser_client()
    resp = client.get(reverse("context:scope-list"), {"rule": "{not json"})
    assert resp.status_code == 200


def test_valid_relation_rule_still_filters():
    """A well-formed rule must still apply (the hardening only drops bad ids)."""
    from context.tests.factories import ScopeFactory

    client, _ = _superuser_client()
    parent = ScopeFactory()
    child = ScopeFactory(parent_scope=parent)
    rule = json.dumps({"f": "parent_scope", "o": "in", "v": [str(parent.pk)]})
    resp = client.get(reverse("context:scope-list"), {"rule": rule})
    assert resp.status_code == 200
    objects = list(resp.context["object_list"])
    assert child in objects
    assert parent not in objects

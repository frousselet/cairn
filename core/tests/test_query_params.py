"""Tests for the safe request-parameter coercion helpers and the list/detail
endpoints that use them (issue #154).

Every endpoint below used to feed a raw query/POST value straight into an ORM
filter on a typed column, returning HTTP 500 on a malformed value. The
integration tests assert the malformed request now degrades gracefully (never
a 500), mirroring the adversarial control valid -> 200, empty -> 200,
malformed -> (no longer) 500.
"""

import uuid
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from core.query_params import parse_date_param, parse_int, parse_uuid

pytestmark = pytest.mark.django_db


# ── Unit tests for the helpers ──────────────────────────────


class TestParseUuid:
    def test_valid_string(self):
        u = uuid.uuid4()
        assert parse_uuid(str(u)) == u

    def test_uuid_instance_passes_through(self):
        u = uuid.uuid4()
        assert parse_uuid(u) == u

    @pytest.mark.parametrize("value", ["notauuid", "", "123", None, True, "x" * 40])
    def test_invalid_returns_none(self, value):
        assert parse_uuid(value) is None


class TestParseInt:
    @pytest.mark.parametrize("value,expected", [("5", 5), (" 7 ", 7), ("-3", -3), (0, 0)])
    def test_valid(self, value, expected):
        assert parse_int(value) == expected

    @pytest.mark.parametrize(
        "value",
        ["notanint", "", None, True, "9999999999999999999999999999", "1.5"],
    )
    def test_invalid_or_out_of_range_returns_none(self, value):
        assert parse_int(value) is None

    def test_custom_bounds(self):
        assert parse_int("11", max_value=10) is None
        assert parse_int("10", max_value=10) == 10


class TestParseDateParam:
    def test_valid_iso(self):
        assert parse_date_param("2026-06-28") == date(2026, 6, 28)

    def test_date_instance_passes_through(self):
        d = date(2026, 1, 1)
        assert parse_date_param(d) is d

    @pytest.mark.parametrize("value", ["notadate", "2020-13-45", "", None, "2026/06/28"])
    def test_invalid_returns_none(self, value):
        assert parse_date_param(value) is None


# ── Endpoint robustness (malformed filter value -> never 500) ──


def _superuser_client():
    user = UserFactory(is_superuser=True, is_staff=True)
    client = Client()
    client.force_login(user)
    return client, user


# GET list/detail endpoints + the malformed param that used to crash them.
_MALFORMED_GET_CASES = [
    ("risks:risk-list", {"assessment": "notauuid"}),
    ("risks:risk-list", {"date_after": "notadate"}),
    ("risks:risk-list", {"date_before": "2020-13-45"}),
    ("risks:risk-list", {"essential_asset": "xx"}),
    ("risks:risk-table-body", {"assessment": "x"}),
    ("risks:risk-register-export-xlsx", {"assessment": "x"}),
    ("risks:treatment-plan-list", {"assessment": "x"}),
    ("risks:acceptance-list", {"assessment": "notauuid"}),
    ("risks:threat-list", {"assessment": "notauuid"}),
    ("risks:vulnerability-list", {"assessment": "notauuid"}),
    ("risks:iso27005-list", {"assessment": "notauuid"}),
    ("risks:iso27005-table-body", {"assessment": "notauuid"}),
    ("risks:api-scale-choices", {"assessment": "notauuid"}),
    ("compliance:requirement-list", {"framework": "notauuid"}),
    ("assets:supplier-list", {"supplier_type": "notanint"}),
    ("calendar-events", {"start": "notadate", "end": "alsonotadate"}),
]


@pytest.mark.parametrize("url_name,params", _MALFORMED_GET_CASES)
def test_malformed_get_param_does_not_500(url_name, params):
    client, _ = _superuser_client()
    resp = client.get(reverse(url_name), params)
    assert resp.status_code != 500, f"{url_name} {params} -> {resp.status_code}"


def test_supplier_int_overflow_does_not_500():
    client, _ = _superuser_client()
    resp = client.get(reverse("assets:supplier-list"), {"supplier_type": "9" * 30})
    assert resp.status_code == 200


def test_bulk_action_malformed_ids_does_not_500():
    client, _ = _superuser_client()
    resp = client.post(
        reverse("risks:risk-bulk-action"),
        {"action": "approve", "risk_ids": "notauuid"},
    )
    # No valid ids -> "no risks selected" redirect, never a 500.
    assert resp.status_code in (302, 200)

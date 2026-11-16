# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The cache backend degrades to a miss when Redis is unreachable."""

import logging

import pytest
from django.core.cache import caches
from django.test import override_settings

# Nothing listens on port 1 : every call fails at once with a refused connection.
UNREACHABLE = {
    "default": {
        "BACKEND": "core.cache.ResilientRedisCache",
        "LOCATION": "redis://127.0.0.1:1/1",
        "OPTIONS": {"socket_connect_timeout": 1, "socket_timeout": 1},
    }
}


@pytest.fixture
def dead_cache():
    with override_settings(CACHES=UNREACHABLE):
        yield caches["default"]


def test_a_read_misses_instead_of_raising(dead_cache):
    assert dead_cache.get("key") is None
    assert dead_cache.get("key", "fallback") == "fallback"
    assert dead_cache.get_many(["a", "b"]) == {}
    assert dead_cache.has_key("key") is False


def test_a_write_is_dropped_instead_of_raising(dead_cache):
    assert dead_cache.set("key", "value", 30) is None
    assert dead_cache.set_many({"a": 1, "b": 2}) == ["a", "b"]
    assert dead_cache.delete("key") is False
    dead_cache.delete_many(["a", "b"])
    assert dead_cache.touch("key") is False
    assert dead_cache.clear() is False


def test_add_reports_that_nothing_was_stored(dead_cache):
    """A caller using add() as a lock must not believe it acquired it."""
    assert dead_cache.add("lock", "1", 30) is False


def test_incr_fails_as_on_a_missing_key(dead_cache):
    with pytest.raises(ValueError):
        dead_cache.incr("counter")


def test_the_outage_is_logged_once_not_on_every_call(dead_cache, caplog):
    type(dead_cache)._last_warning = 0.0
    with caplog.at_level(logging.WARNING, logger="core.cache"):
        dead_cache.get("a")
        dead_cache.get("b")
        dead_cache.set("c", 1)
    assert len([r for r in caplog.records if "Cache unreachable" in r.message]) == 1


@pytest.mark.django_db
def test_the_update_check_survives_a_cache_outage(client, dead_cache, monkeypatch):
    """The About dialog asked the cache first and answered a server error
    whenever Redis was down."""
    from accounts.tests.factories import UserFactory
    from core import updates

    monkeypatch.setattr(updates, "cache", dead_cache)
    monkeypatch.setattr(updates.httpx, "get", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    client.force_login(UserFactory(is_superuser=True))
    response = client.get("/update-check/")
    assert response.status_code == 200

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


# ── Locks : "not stored" must not read as "someone else holds it" ──────────


@pytest.fixture
def no_local_locks():
    from core.cache import reset_local_locks

    reset_local_locks()
    caches["default"].clear()
    yield
    reset_local_locks()
    caches["default"].clear()


def test_the_backend_can_be_asked_without_its_guard(dead_cache):
    """What lets a caller tell an unreachable cache from an empty one."""
    with pytest.raises(Exception) as failure:
        dead_cache.unguarded("add")("key", "1", 60)

    assert "refused" in str(failure.value).lower() or "connect" in str(failure.value).lower()


def test_a_lock_is_shared_when_the_cache_answers(no_local_locks):
    from core.cache import acquire_lock, lock_held, release_lock

    assert acquire_lock("job", 60) is True
    assert acquire_lock("job", 60) is False
    assert lock_held("job") is True

    release_lock("job")

    assert lock_held("job") is False
    assert acquire_lock("job", 60) is True


def test_a_lock_falls_back_to_this_process_when_the_cache_is_unreachable(dead_cache, no_local_locks):
    """Nobody holds a lock nobody can reach : the job still runs, once per process."""
    from core.cache import acquire_lock, lock_held, release_lock

    assert dead_cache.add("job", "1", 60) is False  # what the backend alone answers
    assert acquire_lock("job", 60) is True
    assert acquire_lock("job", 60) is False
    assert lock_held("job") is True

    release_lock("job")

    assert lock_held("job") is False
    assert acquire_lock("job", 60) is True


def test_a_lock_of_this_process_expires(dead_cache, no_local_locks, monkeypatch):
    import core.cache as cache_module

    now = [1000.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: now[0])

    assert cache_module.acquire_lock("job", 300) is True
    now[0] += 299
    assert cache_module.acquire_lock("job", 300) is False
    now[0] += 2
    assert cache_module.lock_held("job") is False
    assert cache_module.acquire_lock("job", 300) is True


def test_the_semantic_index_is_still_rebuilt_without_a_shared_cache(dead_cache, no_local_locks, settings):
    import threading

    from assistant import semantic

    settings.AI_ASSISTANT_SEMANTIC_ENABLED = True
    ran = threading.Event()

    def rebuild(**kwargs):
        ran.set()
        return {"embedded": 0, "pruned": 0}

    from unittest.mock import patch

    from django.db import connections

    with patch.object(semantic, "rebuild_index", rebuild), patch.object(connections, "close_all"):
        assert semantic.rebuild_index_async() is True
        assert ran.wait(5), "the rebuild never ran"


def test_the_spof_detection_takes_its_turn_through_the_same_lock():
    """The scheduler must not read an unreachable cache as "another worker runs it"."""
    import inspect

    from assets.services import spof_scheduler

    source = inspect.getsource(spof_scheduler._run_spof_loop)

    assert "acquire_lock(_RUN_LOCK_KEY, SPOF_REFRESH_INTERVAL)" in source
    assert "cache.add(" not in source

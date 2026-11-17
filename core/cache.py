# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A Redis cache that degrades to a miss instead of failing the request.

The cache only ever holds derived data (the latest published release, an
assistant briefing, a rate-limit counter, a scheduler lock) : nothing in it is
a record. Django's Redis backend nevertheless raises on every call when the
server is unreachable, which turned a Redis restart into a server error on
each page that touched the cache. This backend answers as an empty cache would
(a read misses, a write is dropped) and logs the outage, so the application
keeps serving from the database until Redis is back.

One answer of an empty cache is wrong for a lock. ``add`` then says *not
stored*, which a caller taking a lock reads as *someone else holds it* : when
nobody can reach the cache, nobody holds anything, and a job gated that way
would never run again. A new instance stayed on its installation screen for
ever that way, the migrations waiting for a lock no one could take. What takes
a lock goes through :func:`acquire_lock`, which tells the two apart and falls
back to a lock of its own process.
"""

import logging
import threading
import time

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.redis import RedisCache

logger = logging.getLogger(__name__)

# Seconds between two warnings about the same outage : one line a minute tells
# the operator Redis is down without burying the log under one line per call.
WARNING_INTERVAL = 60.0


class ResilientRedisCache(RedisCache):
    """``RedisCache`` whose operations never raise on a connection failure."""

    _last_warning = 0.0

    def _degrade(self, operation, exc):
        now = time.monotonic()
        if now - type(self)._last_warning >= WARNING_INTERVAL:
            type(self)._last_warning = now
            logger.warning(
                "Cache unreachable (%s failed : %s). Serving without it.", operation, exc
            )

    def _guard(self, operation, fallback, call, *args, **kwargs):
        # redis is imported lazily, like the parent backend does, so the module
        # stays importable where the client library is absent.
        from redis.exceptions import RedisError

        try:
            return call(*args, **kwargs)
        except (RedisError, OSError) as exc:
            self._degrade(operation, exc)
            return fallback

    def unguarded(self, operation):
        """``operation`` as the parent backend runs it : it raises when Redis is unreachable.

        For the callers that must tell a cache nobody can reach from a cache
        that holds nothing (:func:`acquire_lock`, the first-run coordination
        of ``core.onboarding.runner``).
        """
        return getattr(super(), operation)

    def get(self, key, default=None, version=None):
        return self._guard("get", default, super().get, key, default, version)

    def get_many(self, keys, version=None):
        return self._guard("get_many", {}, super().get_many, keys, version)

    def has_key(self, key, version=None):
        return self._guard("has_key", False, super().has_key, key, version)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return self._guard("set", None, super().set, key, value, timeout, version)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        # Nothing was stored : False is the honest answer, and what a caller
        # using add() as a lock must hear (it did not acquire it).
        return self._guard("add", False, super().add, key, value, timeout, version)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        return self._guard("touch", False, super().touch, key, timeout, version)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        # Every key failed to be stored, which is how set_many reports it.
        return self._guard("set_many", list(data), super().set_many, data, timeout, version)

    def delete(self, key, version=None):
        return self._guard("delete", False, super().delete, key, version)

    def delete_many(self, keys, version=None):
        return self._guard("delete_many", None, super().delete_many, keys, version)

    def clear(self):
        return self._guard("clear", False, super().clear)

    def incr(self, key, delta=1, version=None):
        # incr() on a missing key raises ValueError : an unreachable cache holds
        # no key, so callers get the error they already handle.
        from redis.exceptions import RedisError

        try:
            return super().incr(key, delta, version)
        except (RedisError, OSError) as exc:
            self._degrade("incr", exc)
            raise ValueError(f"Key '{key}' not found") from exc


# ── Locks ───────────────────────────────────────────────────────────────────

# The locks taken while the shared cache could not be reached : key -> the
# monotonic time it expires at. Per process, by nature.
_local_locks = {}
_local_locks_guard = threading.Lock()


def unguarded(cache, operation):
    """``operation`` of ``cache`` with a connection failure left to the caller."""
    escape = getattr(cache, "unguarded", None)
    return escape(operation) if escape else getattr(cache, operation)


def acquire_lock(key, ttl, *, alias="default"):
    """Take the lock ``key`` for ``ttl`` seconds; say whether this caller holds it.

    Normally a lock shared by every worker (an atomic ``add``) : one of them
    wins it, the others are told ``False``.

    When the cache cannot be reached there is no shared lock to win or lose.
    The caller is then given the lock of its own process, so the job still
    runs : once per worker instead of once for all of them, which costs some
    duplicated work for the time of the outage. The other answer, ``False``
    to everyone, is a job that silently stops for as long as the cache is
    away, and for ever on an instance that has none.
    """
    from django.core.cache import caches

    cache = caches[alias]
    try:
        return bool(unguarded(cache, "add")(key, "1", ttl))
    except Exception as exc:  # noqa: BLE001 - any failure of the backend is an outage
        logger.warning("Cache unreachable, taking the lock '%s' for this process only : %s", key, exc)
    now = time.monotonic()
    with _local_locks_guard:
        expires = _local_locks.get(key)
        if expires is not None and expires > now:
            return False
        _local_locks[key] = now + ttl
        return True


def lock_held(key, *, alias="default"):
    """Whether someone holds the lock ``key`` : in the shared cache, or in this process."""
    from django.core.cache import caches

    with _local_locks_guard:
        expires = _local_locks.get(key)
        if expires is not None and expires > time.monotonic():
            return True
    try:
        return unguarded(caches[alias], "get")(key) is not None
    except Exception:  # noqa: BLE001 - an unreachable cache holds no lock
        return False


def release_lock(key, *, alias="default"):
    """Give the lock ``key`` back, wherever it was taken."""
    from django.core.cache import caches

    with _local_locks_guard:
        _local_locks.pop(key, None)
    try:
        unguarded(caches[alias], "delete")(key)
    except Exception:  # noqa: BLE001 - an unreachable cache holds no lock to give back
        pass


def reset_local_locks():
    """Forget the locks of this process (used by tests)."""
    with _local_locks_guard:
        _local_locks.clear()

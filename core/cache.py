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
"""

import logging
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

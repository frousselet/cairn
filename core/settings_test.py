# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Test settings - SQLite in-memory, fast password hashing, migrations bypassed."""

import os

# The settings refuse to load outside DEBUG with the public placeholder key.
# The suite runs with DEBUG off, like production, so it brings a key of its own.
os.environ.setdefault("SECRET_KEY", "test-suite-only-key-never-used-by-a-running-instance")

from core.settings import *  # noqa: E402, F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = []

# Keep the first-run onboarding redirect out of the way of the rest of the
# suite; onboarding tests opt back in with @override_settings.
ONBOARDING_REDIRECT_ENABLED = False

# Use in-memory channel layer for tests (no Redis dependency)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Local-memory cache for tests: the suite is single-process, so this behaves
# like the shared Redis cache used in production without needing a live server.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}


# Bypass migrations entirely: Django builds the schema directly from current
# model state (CREATE TABLE) instead of replaying the ~150 historical
# migrations. Data migrations (permissions, system groups, default risk
# criteria) are replayed by the session-scoped fixture in conftest.py.
class _DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = _DisableMigrations()


# The suite never reaches the network : the front-end mirror is a deployment
# concern, exercised by core/tests/test_vendoring.py against a temporary root,
# and the release check is exercised against a stubbed GitHub.
VENDOR_ASSETS_AUTO_DOWNLOAD = False
UPDATE_CHECK_ENABLED = True

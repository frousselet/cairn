"""Test settings - SQLite in-memory, fast password hashing, migrations bypassed."""

from core.settings import *  # noqa: F401, F403

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

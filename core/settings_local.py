# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Local dev settings - run the whole stack in pure Python, no Docker.

Overrides the Docker-oriented defaults (Postgres + Redis) so the app boots
with zero external services:

- SQLite stored in a file (``db.sqlite3``) so data persists across restarts,
  unlike the in-memory database used by the test suite.
- In-memory channel layer, so Channels / WebSockets work without Redis.
- Local-memory cache, so nothing waits on a Redis that is not there.

Activate it by setting ``DJANGO_SETTINGS_MODULE=core.settings_local`` (the
VS Code launch configurations do this for you).
"""

import os

# A development setup : tracebacks in the browser, static files served by
# runserver, the console email backend. Set DEBUG=False in the environment to
# try the production behaviour locally (it then needs a real SECRET_KEY).
os.environ.setdefault("DEBUG", "True")

from core.settings import *  # noqa: E402, F401, F403
from core.settings import BASE_DIR  # noqa: E402

# SQLite on disk - no Postgres needed.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# In-memory channel layer - no Redis needed.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Local-memory cache - no Redis needed. The dev server is a single process, so
# this behaves like the shared cache used in production.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

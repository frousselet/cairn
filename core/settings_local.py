"""Local dev settings - run the whole stack in pure Python, no Docker.

Overrides the Docker-oriented defaults (Postgres + Redis) so the app boots
with zero external services:

- SQLite stored in a file (``db.sqlite3``) so data persists across restarts,
  unlike the in-memory database used by the test suite.
- In-memory channel layer, so Channels / WebSockets work without Redis.

Activate it by setting ``DJANGO_SETTINGS_MODULE=core.settings_local`` (the
VS Code launch configurations do this for you).
"""

from core.settings import *  # noqa: F401, F403
from core.settings import BASE_DIR

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

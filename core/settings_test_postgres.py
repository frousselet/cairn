# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Test settings for the PostgreSQL run : the production engine, real migrations.

The default test settings (``core.settings_test``) build an in-memory SQLite
schema straight from the models, with migrations switched off. That is what
makes the suite fast enough to run on every save, and it is also two blind
spots : nothing replays the migrations a deployment will actually run, and
nothing exercises the engine it will run on (SQLite is lax where PostgreSQL is
strict : types, case sensitivity, ``DISTINCT`` with ``ORDER BY``, grouping,
constraint timing).

This module closes both. It keeps everything from the fast settings except the
database, which is PostgreSQL, and the migrations, which are replayed from the
first one. CI runs the whole suite a second time with it::

    pytest --ds=core.settings_test_postgres

The connection comes from the same ``POSTGRES_*`` variables as production.
"""

import os

from core.settings_test import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "cairn"),
        "USER": os.environ.get("POSTGRES_USER", "cairn"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "cairn"),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Replay every migration, as a deployment does.
MIGRATION_MODULES = {}

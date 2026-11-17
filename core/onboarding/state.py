# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""First-run detection and (read-only) database migration status."""

from django.db import DatabaseError, connections

# Sticky process-level flag: once we observe that the instance has at least one
# user, it is initialised for good and ``is_first_run`` can answer without
# touching the database on every request. It only ever transitions to ``True``
# (initialised); tests reset it via ``reset_onboarding_state``.
_initialised = False

# Sticky flag for "the schema is fully migrated". A running process never gains
# new migrations without a code deploy (which restarts it), so once we confirm
# the schema is up to date we can stop rebuilding the migration graph on every
# request. Reset by tests.
_schema_ready = False


# The tables this process has seen. A table does not go away under a running
# process, so a table seen once is not looked for again.
_known_tables = set()


def reset_onboarding_state():
    """Forget the cached flags (used by tests)."""
    global _initialised, _schema_ready
    _initialised = False
    _schema_ready = False
    _known_tables.clear()


def has_table(name):
    """Whether the database holds the table ``name``, asked without an error.

    On a new database the first screens are served before any migration ran.
    Code that reads a table there used to try, fail and carry on : harmless
    for the page, but each attempt leaves an ``ERROR: relation ... does not
    exist`` in the database log, hundreds of them while the installation
    screen polls. Asking the catalogue first costs one query until the table
    is there, and nothing afterwards.

    ``False`` as well when the database cannot be asked at all, whatever the
    reason : it is unreachable, or the code runs where no query is allowed (a
    module imported while tests are collected). The callers then take the
    path they take for a missing table, as they did when their own query
    failed.
    """
    if name in _known_tables:
        return True
    try:
        connection = connections["default"]
        with connection.cursor() as cursor:
            present = name in connection.introspection.table_names(cursor)
    except Exception:  # noqa: BLE001 - any failure to ask is "not readable now"
        return False
    if present:
        _known_tables.add(name)
    return present


def is_first_run():
    """Return ``True`` while the instance has no users yet.

    A missing ``accounts_user`` table (migrations not applied) is treated as a
    first run as well, so the onboarding screen can still render and show the
    migration state.
    """
    global _initialised
    if _initialised:
        return False

    from accounts.models import User

    if not has_table(User._meta.db_table):
        # No table yet (migrations not applied) -> still a first run.
        return True
    try:
        has_users = User.objects.exists()
    except DatabaseError:
        # Database not ready -> still a first run.
        return True

    if has_users:
        _initialised = True
        return False
    return True


def mark_initialised():
    """Flag the instance as initialised after the first user is created."""
    global _initialised
    _initialised = True


def schema_ready():
    """Whether the database schema is fully migrated.

    Cached once confirmed (a process cannot gain migrations without a restart),
    so the common up-to-date path costs nothing after the first request.
    """
    global _schema_ready
    if _schema_ready:
        return True
    status = migration_status()
    if status["available"] and status["up_to_date"]:
        _schema_ready = True
        return True
    return False


def instance_ready():
    """Whether the instance is ready for background database work.

    ``True`` once the schema is fully migrated *and* the first user exists.
    Background jobs (SPOF detection, semantic-index rebuild) gate their database
    access on this so they never query tables that the first-run onboarding
    migrations have not created yet, nor contend with the migration in flight.

    ``schema_ready()`` is checked first and short-circuits, so an un-migrated
    database never reaches the user query.
    """
    return schema_ready() and not is_first_run()


def migration_status():
    """Return the database migration state without applying anything.

    Shape::

        {"available": bool, "up_to_date": bool,
         "applied": int, "total": int, "pending": ["app.0001_name", ...]}

    ``available`` is ``False`` when the migration state cannot be read (database
    unreachable); the UI then shows an "unknown" card instead of crashing.
    """
    from django.db.migrations.executor import MigrationExecutor

    try:
        connection = connections["default"]
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        total = len(executor.loader.graph.nodes)
        applied = len(executor.loader.applied_migrations)
        pending = [f"{migration.app_label}.{migration.name}" for migration, _backwards in plan]
        return {
            "available": True,
            "up_to_date": not plan,
            "applied": applied,
            "total": total,
            "pending": pending,
        }
    except Exception:
        return {
            "available": False,
            "up_to_date": False,
            "applied": 0,
            "total": 0,
            "pending": [],
        }

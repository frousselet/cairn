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


def reset_onboarding_state():
    """Forget the cached flags (used by tests)."""
    global _initialised, _schema_ready
    _initialised = False
    _schema_ready = False


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

    try:
        has_users = User.objects.exists()
    except DatabaseError:
        # Table or database not ready yet -> still a first run.
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

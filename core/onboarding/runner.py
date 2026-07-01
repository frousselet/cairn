"""Run database migrations and the demo seed in the background, with progress.

Both jobs run on a worker thread and publish their progress to the **shared
cache** (Redis in production, see ``settings.CACHES``), which a tiny JSON
endpoint polls (``OnboardingProgressView``). Polling, not WebSockets, is
deliberate: on a brand-new database the session and auth tables do not exist
yet, so the Channels auth stack (and DB-backed sessions) cannot run during the
*migration* phase. A plain cache read over GET needs neither the app database
nor the session, so it works before any table exists.

Why the *shared* cache and not a process global: production runs several
uvicorn workers. Each web request (and therefore each ``start_migrations`` call
from the onboarding landing view) can land on a different worker. With a
per-process flag, every worker would believe no job is running and would launch
its **own** concurrent migration - several processes applying the same DDL to
the same database at once, which fails with duplicate-column / duplicate-type
errors and makes the progress bar jump around. A single cross-worker lock
(``cache.add``, atomic SET-NX in Redis) guarantees exactly one worker runs the
job; the others observe its progress through the same shared keys.

Progress is best-effort UI sugar; correctness is decided by real state
(migrations applied, users created), never by these events.
"""

import logging

from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)

SEED_PATH = settings.BASE_DIR / "scripts" / "seed_demo_data.py"

# Shared-cache keys. The lock is the source of truth for "a job is running"
# (its mere presence), so it is refreshed by a heartbeat during the run and
# self-heals if a worker dies mid-job (it expires after LOCK_TTL). The state key
# carries the progress snapshot the poller renders.
_CACHE_ALIAS = "default"
_LOCK_KEY = "onboarding:runner:lock"
_STATE_KEY = "onboarding:runner:state"
# Long enough that no single migration/seed phase outlives it (the heartbeat
# refreshes it on every step), short enough that a crashed worker frees the
# instance within a few minutes instead of wedging onboarding indefinitely.
_LOCK_TTL = 600
_STATE_TTL = 3600

_IDLE = {
    "kind": "",
    "status": "idle",
    "label": "",
    "current": 0,
    "total": 0,
    "error": "",
    "upgrade": False,
}


def _store():
    return caches[_CACHE_ALIAS]


def is_running():
    """Whether a migration or seed job is in flight anywhere in the fleet.

    Backed by the shared lock key, so every worker agrees. Read by the
    onboarding middleware and by the background schedulers (SPOF, semantic index)
    to stay off the database while the first-run job owns it.
    """
    return _store().get(_LOCK_KEY) is not None


def progress_snapshot():
    """The last published progress snapshot (shared across workers)."""
    snap = _store().get(_STATE_KEY)
    return dict(snap) if snap else dict(_IDLE)


def reset_runner_state():
    """Forget the shared lock and progress (used by tests)."""
    store = _store()
    store.delete(_LOCK_KEY)
    store.delete(_STATE_KEY)


def _set(**fields):
    store = _store()
    snap = store.get(_STATE_KEY)
    state = dict(snap) if snap else dict(_IDLE)
    state.update(fields)
    store.set(_STATE_KEY, state, _STATE_TTL)


def _heartbeat():
    """Extend the lock TTL so a long-running job keeps ownership."""
    _store().touch(_LOCK_KEY, _LOCK_TTL)


def _start(kind, target, **extra):
    """Start ``target`` on a background thread unless a job is already running.

    The ``cache.add`` is an atomic cross-worker compare-and-set: only the worker
    that wins it runs the job; any other worker (or a second request on the same
    worker) gets ``False`` and simply watches the shared progress.
    """
    import threading

    if not _store().add(_LOCK_KEY, "1", _LOCK_TTL):
        return False
    _set(kind=kind, status="running", label="", current=0, total=0, error="", **extra)
    threading.Thread(target=lambda: _guarded(target), name=f"onboarding-{kind}", daemon=True).start()
    return True


def _guarded(target):
    """Run ``target`` and always release the shared lock afterwards."""
    try:
        target()
    finally:
        _store().delete(_LOCK_KEY)


def start_migrations(upgrade=False):
    return _start("migrate", _run_migrations, upgrade=upgrade)


def start_seed():
    return _start("seed", _run_seed, upgrade=False)


def _run_migrations():
    from django.core.management.sql import emit_post_migrate_signal
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor

    try:
        connection = connections["default"]
        executor = MigrationExecutor(connection, progress_callback=_migration_callback)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        _set(total=len(plan))
        print(f"Applying {len(plan)} database migrations...", flush=True)
        executor.migrate(targets, plan=plan)
        print("Database migrations applied.", flush=True)
        # MigrationExecutor.migrate() does not fire post_migrate (the management
        # command does). Emit it so ContentTypes and built-in permissions are
        # created - the demo seed and generic relations depend on them.
        emit_post_migrate_signal(verbosity=1, interactive=False, db=connection.alias)
        _set(status="done", current=len(plan), total=len(plan))
    except Exception as exc:  # noqa: BLE001 - report any failure to the UI
        logger.exception("Database migration failed during onboarding")
        _set(status="error", error=str(exc))
    finally:
        connections.close_all()


def _migration_callback(action, migration=None, fake=False):
    # Update the progress bar AND echo to the server terminal, mirroring the
    # familiar "Applying app.0001... OK" output of `manage.py migrate`.
    if action == "apply_start" and migration is not None:
        label = f"{migration.app_label}.{migration.name}"
        _set(label=label)
        _heartbeat()
        print(f"  Applying {label}...", end="", flush=True)
    elif action == "apply_success":
        snap = progress_snapshot()
        _set(current=snap["current"] + 1)
        _heartbeat()
        print(" OK", flush=True)


def _run_seed():
    from django.db import connections

    try:
        source = SEED_PATH.read_text()
        total = source.count('_phase("')
        counter = {"n": 0}

        def progress(label):
            counter["n"] += 1
            _set(label=label, current=counter["n"], total=total)
            _heartbeat()

        _set(total=total)

        namespace = {
            "SEED_PROGRESS": progress,
            "SEED_BASE_DIR": str(settings.BASE_DIR),
            "__name__": "seed_demo_data",
        }
        exec(compile(source, str(SEED_PATH), "exec"), namespace)

        _set(status="done", current=total, total=total)
    except Exception as exc:  # noqa: BLE001 - report any failure to the UI
        logger.exception("Demo seed failed during onboarding")
        _set(status="error", error=str(exc))
    finally:
        connections.close_all()

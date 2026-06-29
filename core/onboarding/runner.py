"""Run database migrations and the demo seed in the background, with progress.

Both jobs run on a worker thread and publish their progress to a single
process-global store that a tiny JSON endpoint polls (``OnboardingProgressView``).
Polling, not WebSockets, is deliberate: on a brand-new database the session and
auth tables do not exist yet, so the Channels auth stack (and DB-backed sessions)
cannot run during the *migration* phase. A plain in-memory store touched over GET
needs neither the database nor the session, so it works before any table exists.

Progress is best-effort UI sugar; correctness is decided by real state (migrations
applied, users created), never by these events.
"""

import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

SEED_PATH = settings.BASE_DIR / "scripts" / "seed_demo_data.py"

_lock = threading.Lock()
_running = False

# Snapshot consumed by the progress poller. ``kind`` is "migrate" or "seed";
# ``status`` is one of idle / running / done / error; ``upgrade`` distinguishes a
# migration of an already-initialised instance from a first-run setup.
_progress = {
    "kind": "",
    "status": "idle",
    "label": "",
    "current": 0,
    "total": 0,
    "error": "",
    "upgrade": False,
}


def is_running():
    return _running


def progress_snapshot():
    with _lock:
        return dict(_progress)


def _set(**fields):
    with _lock:
        _progress.update(fields)


def _start(kind, target, **extra):
    """Start ``target`` on a background thread unless a job is already running."""
    global _running
    with _lock:
        if _running:
            return False
        _running = True
        _progress.update(kind=kind, status="running", label="", current=0, total=0, error="", **extra)

    threading.Thread(target=target, name=f"onboarding-{kind}", daemon=True).start()
    return True


def start_migrations(upgrade=False):
    return _start("migrate", _run_migrations, upgrade=upgrade)


def start_seed():
    return _start("seed", _run_seed, upgrade=False)


def _run_migrations():
    global _running
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
        _running = False


def _migration_callback(action, migration=None, fake=False):
    # Update the progress bar AND echo to the server terminal, mirroring the
    # familiar "Applying app.0001... OK" output of `manage.py migrate`.
    if action == "apply_start" and migration is not None:
        label = f"{migration.app_label}.{migration.name}"
        _set(label=label)
        print(f"  Applying {label}...", end="", flush=True)
    elif action == "apply_success":
        with _lock:
            _progress["current"] += 1
        print(" OK", flush=True)


def _run_seed():
    global _running
    from django.db import connections

    try:
        source = SEED_PATH.read_text()
        total = source.count('_phase("')
        counter = {"n": 0}

        def progress(label):
            counter["n"] += 1
            _set(label=label, current=counter["n"], total=total)

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
        _running = False

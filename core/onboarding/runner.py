# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
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

Two things hold when the shared cache cannot be reached (Redis down, or an
instance started without one) :

- the job still starts. The lock and the progress then live in this process
  (``_ResilientStore``), which is enough for one worker and lets the others
  start their own;
- two workers never apply the migrations at once, whatever each believes
  about the lock : the job takes a lock of the database itself
  (``_database_lock``, a PostgreSQL advisory lock), so a second runner waits
  for the first and then finds nothing left to apply.
"""

import logging
import threading
import time
from contextlib import contextmanager

from django.conf import settings
from django.core.cache import caches

from core.cache import unguarded

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


class _SharedCacheDown(Exception):
    """The shared cache could not be reached : the operation is carried out locally."""


class _ResilientStore:
    """Onboarding coordination store that survives a shared-cache outage.

    Every operation goes to the shared cache (Redis in production). When that
    backend cannot be reached, the operation is carried out on a process-local
    store instead. Both halves matter :

    - a read must not raise : the onboarding middleware reads the lock on
      **every** request during the un-initialised window, and an unguarded
      failure there turns the whole site into a 500;
    - a failed ``add`` must not read as *the lock is held* : nobody holds a
      lock nobody can reach, and the migrations of a new instance would wait
      for it for ever. The cache backend of the project answers a connection
      failure as an empty cache would (``core.cache.ResilientRedisCache``),
      so the store asks for its operations unguarded and decides itself.

    A key written locally stays read locally until it is deleted : the job
    that took its lock during an outage keeps a coherent view of it if the
    cache comes back before it ends.

    The local store is per process, so it cannot coordinate several uvicorn
    workers. Each may then start a job; ``_database_lock`` is what keeps two
    of them from running at once.

    After a failure the shared cache is left alone for ``_RETRY_AFTER``
    seconds. A cache that refuses the connection fails at once, but one that
    does not answer costs its whole timeout on every call : the screen polls
    twice a second and a migration writes its progress at every step, so
    without the pause an installation of five minutes would take an hour.
    """

    _local = {}
    _lock = threading.Lock()
    # Monotonic time before which the shared cache is not tried again.
    _down_until = 0.0
    _RETRY_AFTER = 15.0

    @classmethod
    def reset(cls):
        """Forget what is held locally and that the cache was down (used by tests)."""
        with cls._lock:
            cls._local.clear()
        cls._down_until = 0.0

    def _cache(self):
        return caches[_CACHE_ALIAS]

    def _call(self, operation, *args):
        return unguarded(self._cache(), operation)(*args)

    def _shared(self, operation, *args):
        """Run ``operation`` on the shared cache, or raise ``_SharedCacheDown``."""
        cls = type(self)
        if time.monotonic() < cls._down_until:
            raise _SharedCacheDown
        try:
            return self._call(operation, *args)
        except Exception as exc:  # noqa: BLE001 - any backend error degrades to local
            cls._down_until = time.monotonic() + cls._RETRY_AFTER
            # One line per pause, not one per call.
            logger.warning(
                "Onboarding shared cache unreachable, using the process-local store for %ds : %s",
                cls._RETRY_AFTER, exc,
            )
            raise _SharedCacheDown from exc

    def get(self, key, default=None):
        with self._lock:
            if key in self._local:
                return self._local[key]
        try:
            return self._shared("get", key, default)
        except _SharedCacheDown:
            return default

    def set(self, key, value, timeout=None):
        try:
            self._shared("set", key, value, timeout)
        except _SharedCacheDown:
            with self._lock:
                self._local[key] = value
        else:
            with self._lock:
                if key in self._local:
                    self._local[key] = value

    def add(self, key, value, timeout=None):
        with self._lock:
            if key in self._local:
                return False
        try:
            return bool(self._shared("add", key, value, timeout))
        except _SharedCacheDown:
            with self._lock:
                if key in self._local:
                    return False
                self._local[key] = value
                return True

    def delete(self, key):
        with self._lock:
            self._local.pop(key, None)
        try:
            self._shared("delete", key)
        except _SharedCacheDown:
            pass

    def touch(self, key, timeout=None):
        try:
            self._shared("touch", key, timeout)
        except _SharedCacheDown:
            pass  # a missed heartbeat only shortens the lock TTL


def _store():
    return _ResilientStore()


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


def progress_report():
    """What the progress screen polls : the snapshot, and whether a job is alive.

    ``alive`` is the presence of the lock. A snapshot that still reads
    *running* while nothing holds the lock is a job that died (a worker
    killed mid-run), and a screen that reads *idle* is one whose job never
    started : in both cases the screen goes back to the landing page, which
    starts what is pending, instead of waiting for ever.
    """
    report = progress_snapshot()
    report["alive"] = is_running()
    return report


def reset_runner_state():
    """Forget the shared lock and progress (used by tests)."""
    _ResilientStore.reset()
    store = _store()
    store.delete(_LOCK_KEY)
    store.delete(_STATE_KEY)


# The database's own lock, for the time of a job. Any 64-bit number no other
# application of the same database would pick : the letters "CAIRN" and a
# trailing 1.
_DATABASE_LOCK_ID = 0x43414952_4E01


@contextmanager
def _database_lock(connection):
    """Hold the lock of the database itself for the time of a job (PostgreSQL).

    The cache lock says who *starts* a job; this one is what makes two jobs
    impossible at the same time, even between workers that cannot reach the
    cache and each believe they are alone. A second runner blocks here until
    the first has finished. It is a session lock : it is released when the
    block ends, and in any case when the connection closes.

    Other databases (SQLite, in development and in tests) serve a single
    process : there is nothing to take.
    """
    if connection.vendor != "postgresql":
        yield
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [_DATABASE_LOCK_ID])
    try:
        yield
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [_DATABASE_LOCK_ID])
        except Exception:  # noqa: BLE001 - the lock ends with the connection anyway
            logger.warning("The onboarding database lock could not be released; it ends with the connection.")


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
        with _database_lock(connection):
            # Read after the lock is held : a runner that waited for another
            # one sees what that one applied, and has nothing left to do.
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
        with _database_lock(connections["default"]):
            # The sample data is loaded into an instance nobody uses yet. A
            # runner that waited for another one finds its users, and loads
            # nothing on top of them.
            from accounts.models import User

            if User.objects.exists():
                logger.info("The instance already has users : the sample data is not loaded a second time.")
            else:
                exec(compile(source, str(SEED_PATH), "exec"), namespace)

        _set(status="done", current=total, total=total)
    except Exception as exc:  # noqa: BLE001 - report any failure to the UI
        logger.exception("Demo seed failed during onboarding")
        _set(status="error", error=str(exc))
    finally:
        connections.close_all()

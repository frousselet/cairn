import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

SPOF_REFRESH_INTERVAL = int(os.environ.get("SPOF_REFRESH_INTERVAL", 300))  # seconds
# How often to re-probe readiness while the instance is still being set up
# (first-run onboarding: migrations running, no user yet).
READINESS_POLL_INTERVAL = 5  # seconds

# Fleet-wide single-runner gate. Production runs several uvicorn workers, each
# with its own scheduler thread; without this every worker would run detection
# on the same interval, mutating the same rows concurrently. The shared-cache
# SET-NX (``cache.add``) lets exactly one worker per interval win the run, and
# the key is left to expire on its own so the next run is one interval later
# fleet-wide rather than once per worker.
_RUN_LOCK_KEY = "assets:spof:run-lock"

_started = False
_lock = threading.Lock()


def _run_spof_loop():
    """Background loop: apply SPOF detection every SPOF_REFRESH_INTERVAL seconds."""
    from django.core.cache import cache
    from django.db import connections

    from assets.services.spof_detection import SpofDetector
    from core.onboarding import runner
    from core.onboarding.state import instance_ready

    while True:
        # On a fresh database the first-run migrations have not created the asset
        # tables yet. Wait for the instance to be migrated and initialised before
        # touching the ORM. While an onboarding migration or seed is in flight,
        # stay completely off the database (no readiness probe either): on SQLite
        # a stray read contends with the job's write lock and stalls it.
        if runner.is_running() or not instance_ready():
            connections.close_all()
            time.sleep(READINESS_POLL_INTERVAL)
            continue
        # Exactly one worker runs detection per interval across the fleet.
        if cache.add(_RUN_LOCK_KEY, "1", SPOF_REFRESH_INTERVAL):
            try:
                result = SpofDetector().apply()
                logger.info(
                    "SPOF auto-detection: %d SPOF found, %d changes applied.",
                    result["total_spof"],
                    result["total_changed"],
                )
            except Exception:
                logger.exception("SPOF auto-detection failed")
        time.sleep(SPOF_REFRESH_INTERVAL)


def start_spof_scheduler():
    """Start the background SPOF scheduler (once per process)."""
    global _started
    with _lock:
        if _started:
            return
        _started = True

    t = threading.Thread(target=_run_spof_loop, name="spof-scheduler", daemon=True)
    t.start()
    logger.info("SPOF scheduler started (interval=%ds).", SPOF_REFRESH_INTERVAL)

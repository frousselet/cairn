# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Tool calls answered with a task (the ``io.modelcontextprotocol/tasks`` extension).

A tool marked with :func:`runs_as_task` (report generation, batch creation)
answers a client that declares the extension on its request with a
``CreateTaskResult`` instead of making it wait : the call is recorded
(:class:`mcp.models.McpTask`), the record is committed, then the tool runs on
a thread of the worker that took the call. The client polls ``tasks/get``
until the task reaches ``completed`` (the tool's result, refusals included as
``isError``) or ``failed`` (a JSON-RPC error, never the text of an exception).

What holds it together :

- **the person** : a task is read, updated and cancelled by the person it ran
  as, and by no one else (an unknown, foreign or expired identifier answers
  ``-32602``). The tool runs as that person, with their permissions and
  scopes at the time it runs, in their language;
- **the worker** : the thread signs a heartbeat every
  :data:`HEARTBEAT_SECONDS`. A task whose worker stopped (a restart, a
  crash) answers ``failed`` once :data:`STALE_AFTER_SECONDS` pass without
  one, rather than ``working`` for ever;
- **cancellation** is cooperative, as the extension allows : a Cairn tool
  cannot be interrupted half way through without leaving a partial change, so
  ``tasks/cancel`` is acknowledged and recorded, and the task reports what
  really happened;
- **retention** : :data:`TASK_TTL_MS` from creation (the job plus well over
  an hour, as clients that resume a session later need), after which the task
  is deleted.
"""

import logging
import threading
from datetime import UTC, timedelta

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.utils import timezone, translation

from mcp.models import McpTask, McpTaskStatus
from mcp.server import INTERNAL_ERROR, INVALID_PARAMS, InvalidParamsError, ProtocolError, wrap_tool_result

logger = logging.getLogger(__name__)

TASK_TTL_MS = 2 * 60 * 60 * 1000  # two hours from creation
POLL_INTERVAL_MS = 2000
HEARTBEAT_SECONDS = 15
STALE_AFTER_SECONDS = 120


def runs_as_task(handler):
    """Mark a tool handler as one that may answer with a task.

    ``functools.wraps`` (used by ``require_perm``) carries the attribute to the
    wrapper.
    """
    handler.mcp_task = True
    return handler


# ── Wire format ───────────────────────────────────────────


def _iso(moment):
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _payload(task, *, detailed):
    """The ``Task`` object of the extension; ``detailed`` adds the outcome."""
    body = {
        "taskId": str(task.id),
        "status": task.status,
        "createdAt": _iso(task.created_at),
        "lastUpdatedAt": _iso(task.updated_at),
        "ttlMs": task.ttl_ms,
    }
    if not task.is_terminal:
        body["pollIntervalMs"] = task.poll_interval_ms
    if task.status_message:
        body["statusMessage"] = task.status_message
    if detailed:
        if task.status == McpTaskStatus.COMPLETED and task.result is not None:
            body["result"] = task.result
        elif task.status == McpTaskStatus.FAILED:
            body["error"] = task.error or {"code": INTERNAL_ERROR, "message": "Internal error"}
    return body


# ── Lifecycle of a task ───────────────────────────────────


def purge_expired():
    """Forget the tasks whose retention is over."""
    McpTask.objects.filter(expires_at__lt=timezone.now()).delete()


def create(tool_def, user, arguments):
    """Record the call, start it once the record is committed, answer the task."""
    purge_expired()
    now = timezone.now()
    task = McpTask.objects.create(
        user=user,
        tool_name=tool_def["name"],
        arguments=arguments,
        status=McpTaskStatus.WORKING,
        language=getattr(user, "language", "") or translation.get_language() or "",
        heartbeat_at=now,
        expires_at=now + timedelta(milliseconds=TASK_TTL_MS),
        ttl_ms=TASK_TTL_MS,
        poll_interval_ms=POLL_INTERVAL_MS,
    )
    task_id = task.pk
    transaction.on_commit(lambda: spawn(task_id))
    answer = _payload(task, detailed=False)
    answer["resultType"] = "task"
    return answer


def spawn(task_id):
    """Run the task on a thread of this worker (replaced in tests by :func:`execute`)."""
    threading.Thread(target=_run_thread, args=(task_id,), name=f"mcp-task-{task_id}", daemon=True).start()


def _run_thread(task_id):
    close_old_connections()
    try:
        execute(task_id)
    finally:
        connection.close()


def _beat(task_id, stop):
    """Sign the task's heartbeat until ``stop`` is set (own connection)."""
    try:
        while not stop.wait(HEARTBEAT_SECONDS):
            try:
                McpTask.objects.filter(pk=task_id, status=McpTaskStatus.WORKING).update(
                    heartbeat_at=timezone.now()
                )
            except Exception:  # noqa: BLE001 - one missed beat must not stop the next ones
                logger.warning("MCP task %s : a heartbeat could not be written", task_id)
                connection.close()
    finally:
        connection.close()


def execute(task_id, *, heartbeat=True):
    """Run the tool of ``task_id`` as its person and record the outcome."""
    from mcp.api.views_mcp import get_mcp_server

    try:
        task = McpTask.objects.select_related("user").get(pk=task_id)
    except McpTask.DoesNotExist:
        return
    if task.status != McpTaskStatus.WORKING:
        return

    stop = threading.Event()
    beater = None
    if heartbeat:
        beater = threading.Thread(target=_beat, args=(task_id, stop), name=f"mcp-task-beat-{task_id}", daemon=True)
        beater.start()

    status, result, error, message = McpTaskStatus.COMPLETED, None, None, ""
    try:
        tool_def = get_mcp_server().get_tool(task.tool_name)
        if tool_def is None:
            raise InvalidParamsError(f"Unknown tool: {task.tool_name}")
        with translation.override(task.language or None):
            result = wrap_tool_result(tool_def["handler"](task.user, task.arguments))
    except InvalidParamsError:
        status, error, message = (
            McpTaskStatus.FAILED, {"code": INVALID_PARAMS, "message": "Invalid params"}, "Invalid params",
        )
    except Exception:
        logger.exception("MCP task %s (%s) failed", task_id, task.tool_name)
        status, error, message = (
            McpTaskStatus.FAILED, {"code": INTERNAL_ERROR, "message": "Internal error"}, "Internal error",
        )
    finally:
        stop.set()
        if beater is not None:
            beater.join()

    # A terminal status does not change : a task declared failed meanwhile
    # (its worker looked stopped) keeps that answer.
    McpTask.objects.filter(pk=task_id, status=McpTaskStatus.WORKING).update(
        status=status,
        result=result,
        error=error,
        status_message=message,
        finished_at=timezone.now(),
        updated_at=timezone.now(),
    )


# ── Methods of the extension ──────────────────────────────


def _owned(user, task_id):
    """The person's task, failed if its worker stopped; else ``-32602``."""
    try:
        task = McpTask.objects.get(pk=task_id, user=user)
    except (McpTask.DoesNotExist, ValueError, TypeError, ValidationError):
        raise ProtocolError(INVALID_PARAMS, "Failed to retrieve task: Task not found", http_status=200) from None
    now = timezone.now()
    if task.expires_at < now:
        task.delete()
        raise ProtocolError(INVALID_PARAMS, "Failed to retrieve task: Task has expired", http_status=200)
    if (
        task.status == McpTaskStatus.WORKING
        and task.heartbeat_at is not None
        and task.heartbeat_at < now - timedelta(seconds=STALE_AFTER_SECONDS)
    ):
        message = "The worker running the task stopped before it finished."
        McpTask.objects.filter(pk=task.pk, status=McpTaskStatus.WORKING).update(
            status=McpTaskStatus.FAILED,
            error={"code": INTERNAL_ERROR, "message": message},
            status_message=message,
            finished_at=now,
            updated_at=now,
        )
        task.refresh_from_db()
    return task


def get(user, task_id):
    return _payload(_owned(user, task_id), detailed=True)


def update(user, task_id):
    """Acknowledge ``tasks/update`` : no Cairn task waits for input, so answers are ignored."""
    _owned(user, task_id)
    return {}


def cancel(user, task_id):
    """Record the request; a running tool finishes and reports its real outcome."""
    task = _owned(user, task_id)
    if not task.is_terminal and not task.cancel_requested:
        McpTask.objects.filter(pk=task.pk).update(
            cancel_requested=True,
            status_message="Cancellation requested : the operation cannot be interrupted "
                           "and will report its real outcome.",
            updated_at=timezone.now(),
        )
    return {}

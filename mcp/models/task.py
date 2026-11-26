# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A tool call answered with a task (``io.modelcontextprotocol/tasks``)."""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class McpTaskStatus(models.TextChoices):
    WORKING = "working", _("Working")
    INPUT_REQUIRED = "input_required", _("Input required")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    CANCELLED = "cancelled", _("Cancelled")


TERMINAL_STATUSES = (McpTaskStatus.COMPLETED, McpTaskStatus.FAILED, McpTaskStatus.CANCELLED)


class McpTask(models.Model):
    """A tool call that runs after its answer, polled with ``tasks/get``.

    The row exists before the answer is sent, so the identifier it gives is
    always one ``tasks/get`` resolves. It belongs to the person the call ran
    as : no one else reads, updates or cancels it. Its identifier is a random
    UUID, which nobody can guess. A task is kept until ``expires_at`` (its
    ``ttlMs`` counted from its creation), then forgotten.

    A technical record of the MCP transport, like an access token : it is not
    a domain element, runs no lifecycle and keeps no history; what the tool
    changed is recorded by the records themselves.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mcp_tasks",
        verbose_name=_("User"),
    )
    tool_name = models.CharField(_("Tool"), max_length=200)
    arguments = models.JSONField(_("Arguments"), default=dict, blank=True)
    status = models.CharField(
        _("Status"), max_length=20, choices=McpTaskStatus.choices, default=McpTaskStatus.WORKING
    )
    status_message = models.TextField(_("Status message"), blank=True, default="")
    result = models.JSONField(_("Result"), null=True, blank=True)
    error = models.JSONField(_("Error"), null=True, blank=True)
    cancel_requested = models.BooleanField(_("Cancellation requested"), default=False)
    language = models.CharField(_("Language"), max_length=10, blank=True, default="")
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    heartbeat_at = models.DateTimeField(_("Last sign of life"), null=True, blank=True)
    finished_at = models.DateTimeField(_("Finished at"), null=True, blank=True)
    expires_at = models.DateTimeField(_("Expires at"), db_index=True)
    ttl_ms = models.PositiveBigIntegerField(_("Retention (ms)"))
    poll_interval_ms = models.PositiveIntegerField(_("Poll interval (ms)"))

    class Meta:
        verbose_name = _("MCP task")
        verbose_name_plural = _("MCP tasks")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tool_name} ({self.status})"

    @property
    def is_terminal(self):
        return self.status in TERMINAL_STATUSES

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A file sent out of band to a tool (the ``io.modelcontextprotocol/files`` extension)."""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def _staging_path(instance, filename):
    """``mcp_uploads/<upload id>`` : the name the client gave is never a path."""
    return f"mcp_uploads/{instance.pk}"


class McpUpload(models.Model):
    """The staging place of one file a tool call asked for.

    Created with the ``upload_required`` answer, written once by ``PUT`` with
    the credential of the person it was issued to (``mcp.api.views_uploads``),
    consumed once by the retry that runs the tool, then deleted. A technical
    record of the MCP transport, like an access token : no lifecycle, no
    history; the record the tool writes keeps its own.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mcp_uploads", verbose_name=_("User"),
    )
    tool_name = models.CharField(_("Tool"), max_length=200)
    file_id = models.CharField(_("File identifier"), max_length=128)
    name = models.CharField(_("File name"), max_length=255, blank=True, default="")
    mime_type = models.CharField(_("Content type"), max_length=255, blank=True, default="")
    size = models.PositiveBigIntegerField(_("Size (bytes)"))
    file = models.FileField(_("File"), upload_to=_staging_path, max_length=200, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    received_at = models.DateTimeField(_("Received at"), null=True, blank=True)
    consumed_at = models.DateTimeField(_("Consumed at"), null=True, blank=True)
    expires_at = models.DateTimeField(_("Expires at"), db_index=True)

    class Meta:
        verbose_name = _("MCP upload")
        verbose_name_plural = _("MCP uploads")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tool_name} : {self.file_id}"

    def discard(self):
        """Delete the staged bytes and the row."""
        if self.file:
            self.file.delete(save=False)
        self.delete()

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Where a client sends a file a tool call asked for : ``PUT /api/v1/mcp/uploads/<id>``.

The target of an ``upload_required`` answer (``mcp/files.py``), with
``credentials: "include"`` : the client sends the bytes with the bearer token
of its MCP requests. The upload is written once, by the person it was issued
to, before it expires, and exactly as many bytes as the call declared. Anyone
else, an unknown or expired identifier, answers 404, as a record out of reach
does. Nothing here echoes the address or the bytes in a log or an error.
"""

import tempfile

from django.core.files import File
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from mcp.api.authentication import OAuthTokenAuthentication
from mcp.api.views_mcp import origin_allowed
from mcp.models import McpUpload

CHUNK = 64 * 1024


def _refuse(status, error):
    return JsonResponse({"error": error}, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class McpUploadView(View):
    http_method_names = ["put"]

    def put(self, request, pk):
        if not origin_allowed(request):
            return _refuse(403, "forbidden_origin")
        try:
            authenticated = OAuthTokenAuthentication().authenticate(request)
        except Exception:  # noqa: BLE001 - an unreadable credential is no credential
            authenticated = None
        if authenticated is None:
            return _refuse(401, "authentication_required")
        user = authenticated[0]
        if not user.is_superuser and not user.has_perm("system.mcp.access"):
            return _refuse(403, "access_denied")

        upload = McpUpload.objects.filter(pk=pk, user=user, expires_at__gte=timezone.now()).first()
        if upload is None:
            return _refuse(404, "not_found")
        if upload.received_at is not None:
            return _refuse(409, "already_received")
        try:
            declared = int(request.headers.get("Content-Length", ""))
        except ValueError:
            return _refuse(411, "length_required")
        if declared != upload.size:
            return _refuse(400, "size_mismatch")

        received = 0
        with tempfile.TemporaryFile() as buffer:
            while True:
                chunk = request.read(CHUNK)
                if not chunk:
                    break
                received += len(chunk)
                if received > upload.size:
                    return _refuse(413, "too_large")
                buffer.write(chunk)
            if received != upload.size:
                return _refuse(400, "size_mismatch")
            buffer.seek(0)
            # Written once : a second write of the same target is refused above,
            # and the row is claimed before the file is stored.
            claimed = McpUpload.objects.filter(pk=upload.pk, received_at__isnull=True).update(
                received_at=timezone.now()
            )
            if not claimed:
                return _refuse(409, "already_received")
            upload.file.save(str(upload.pk), File(buffer), save=False)
            McpUpload.objects.filter(pk=upload.pk).update(file=upload.file.name)
        return HttpResponse(status=201)

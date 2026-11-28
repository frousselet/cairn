# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""
MCP Streamable HTTP transport endpoint.

Serves the stateless MCP ``2026-07-28`` revision and, for the clients that
predate it, the ``2025-03-26`` one (see :mod:`mcp.server`):
- POST /mcp: Accept JSON-RPC requests, return JSON-RPC responses
- GET /mcp: SSE stream of the 2025-03-26 revision (it carries no notification)
- DELETE /mcp: end a 2025-03-26 session and revoke its token

A request whose ``Origin`` header names another site is refused : a page open
in the browser of someone holding a token must not reach the endpoint (DNS
rebinding). Requests sent by a program carry no ``Origin``; a browser-based
client is admitted by naming its origin in ``CSRF_TRUSTED_ORIGINS``.
"""

import json
import logging
import time
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from mcp.api.authentication import OAuthTokenAuthentication
from mcp.server import MODERN_PROTOCOL_VERSION, McpServer
from mcp.tools import register_all_tools

logger = logging.getLogger(__name__)

#: Seconds between two purges of the expired tasks and staged uploads, per worker.
PURGE_EVERY = 60
_last_purge = 0.0


def purge_expired_transport_records():
    """Forget the expired tasks and staged uploads, at most once a minute per worker.

    Run on the requests of the MCP endpoint, so what expired goes even when no
    one creates a task or asks for an upload again.
    """
    global _last_purge
    now = time.monotonic()
    if _last_purge and now - _last_purge < PURGE_EVERY:
        return
    _last_purge = now
    from mcp import files, tasks

    try:
        tasks.purge_expired()
        files.purge_expired()
    except Exception:  # noqa: BLE001 - housekeeping never fails a request
        logger.exception("The expired MCP tasks and uploads could not be purged")

# Singleton server instance (tools registered once)
_server = None
_server_lock = False


def get_mcp_server():
    """Get or create the singleton MCP server with all tools registered."""
    global _server, _server_lock
    if _server is None and not _server_lock:
        _server_lock = True
        srv = McpServer()
        register_all_tools(srv)
        _server = srv
        _server_lock = False
    return _server


def origin_allowed(request):
    """Whether the ``Origin`` of ``request``, when it sends one, may call the endpoint.

    The instance's own origin and those listed in ``CSRF_TRUSTED_ORIGINS`` may.
    """
    origin = request.headers.get("Origin")
    if origin is None:
        return True
    try:
        parts = urlsplit(origin)
    except ValueError:
        return False
    if not parts.scheme or not parts.netloc:
        return False
    if f"{parts.scheme}://{parts.netloc}".lower() in {o.lower().rstrip("/") for o in settings.CSRF_TRUSTED_ORIGINS}:
        return True
    return parts.scheme == request.scheme and parts.netloc.lower() == request.get_host().lower()


@method_decorator(csrf_exempt, name="dispatch")
class McpEndpointView(View):
    """MCP Streamable HTTP endpoint."""

    def dispatch(self, request, *args, **kwargs):
        if not origin_allowed(request):
            return JsonResponse(
                {"error": "forbidden_origin", "message": "Origin not allowed."},
                status=403,
            )

        # Allow DELETE without strict authentication so clients can always
        # disconnect (e.g. when the token has already expired).
        if request.method == "DELETE":
            self._try_authenticate(request)
            return self.delete(request)

        # Authenticate via OAuth Bearer token
        auth = OAuthTokenAuthentication()
        try:
            result = auth.authenticate(request)
        except Exception as e:
            logger.exception("Authentication error in MCP endpoint")
            return JsonResponse(
                {
                    "error": "authentication_failed",
                    "message": "Authentication failed.",
                },
                status=401,
            )

        if result is None:
            return JsonResponse(
                {"error": "authentication_required", "message": "Bearer token required."},
                status=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.user, request.auth = result

        # Check MCP access permission
        user = request.user
        if not user.is_superuser and not user.has_perm("system.mcp.access"):
            return JsonResponse(
                {"error": "access_denied", "message": "MCP access not permitted."},
                status=403,
            )

        return super().dispatch(request, *args, **kwargs)

    def _try_authenticate(self, request):
        """Best-effort authentication for DELETE - never raises."""
        from django.contrib.auth.models import AnonymousUser

        request.auth = None
        if not hasattr(request, "user") or request.user is None:
            request.user = AnonymousUser()
        try:
            auth = OAuthTokenAuthentication()
            result = auth.authenticate(request)
            if result is not None:
                request.user, request.auth = result
        except Exception:
            pass

    def post(self, request):
        """Handle JSON-RPC requests from MCP clients."""
        content_type = request.content_type or ""
        if "json" not in content_type and content_type != "":
            return JsonResponse(
                {"error": "invalid_content_type", "message": "Content-Type must be application/json"},
                status=415,
            )

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
                status=200,
            )

        server = get_mcp_server()
        purge_expired_transport_records()
        base_url = request.build_absolute_uri("/").rstrip("/")
        result, status = server.handle_http(body, request.user, request.headers, base_url)

        if result is None:
            # Notification: accepted, with no body
            return HttpResponse(status=202)

        response = JsonResponse(result, safe=False, status=status)
        # The 2025-03-26 session identifier is echoed to the clients of that
        # revision; the stateless revision has no session.
        session_id = request.headers.get("Mcp-Session-Id")
        if session_id and request.headers.get("MCP-Protocol-Version") != MODERN_PROTOCOL_VERSION:
            response["Mcp-Session-Id"] = session_id
        return response

    def get(self, request):
        """SSE stream for server-initiated notifications.
        Currently returns an empty stream since we don't have server-push features yet.
        """
        def event_stream():
            # Send initial comment to keep connection alive
            yield ": MCP SSE stream connected\n\n"
            # We don't currently have server-initiated notifications
            # The stream stays open for future use
            yield "event: endpoint\ndata: /api/v1/mcp\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        session_id = request.headers.get("Mcp-Session-Id")
        if session_id:
            response["Mcp-Session-Id"] = session_id
        return response

    def delete(self, request):
        """Terminate an MCP session and revoke the access token."""
        # Revoke the access token so the session is truly closed.
        if getattr(request, "auth", None) is not None:
            try:
                request.auth.delete()
            except Exception:
                logger.debug("Token already deleted during session termination")
        return JsonResponse({"status": "session_terminated"}, status=200)


@csrf_exempt
def mcp_metadata_view(request):
    """
    OAuth 2.0 Protected Resource Metadata (RFC 9728).
    Helps MCP clients discover the authorization server.
    """
    if request.method != "GET":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    # Build base URL from request
    scheme = request.scheme
    host = request.get_host()
    base_url = f"{scheme}://{host}"

    return JsonResponse({
        "resource": f"{base_url}/api/v1/mcp",
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{base_url}/api/v1/mcp/.well-known/oauth-protected-resource",
    })

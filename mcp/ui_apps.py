# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Interfaces a host shows beside a tool result (the ``io.modelcontextprotocol/ui`` extension, MCP Apps).

A tool marked with :func:`shows_app` names a ``ui://cairn/<name>`` resource in
its ``_meta.ui.resourceUri``, for a client that declares the extension with
the ``text/html;profile=mcp-app`` type. The host reads that resource
(``resources/read``), runs its HTML in a sandboxed frame of its own origin,
and hands it the tool's result : the ``structuredContent`` Cairn adds for such
a client, beside the text the model reads.

The pages are Django templates (``mcp/templates/mcp/apps/``) rendered in the
language of the person reading, self-contained : no script, style or font is
loaded from anywhere, so they declare no CSP domain and the host's restrictive
default applies. They only display what the tool returned; they call no tool
and send nothing.
"""

from django.template.loader import render_to_string
from django.utils import translation

UI_EXTENSION = "io.modelcontextprotocol/ui"
MIME_TYPE = "text/html;profile=mcp-app"
URI_PREFIX = "ui://cairn/"

#: ``ui://`` resource -> (template, title)
APPS = {
    f"{URI_PREFIX}risk-heatmap": ("mcp/apps/risk_heatmap.html", "Risk heat map"),
    f"{URI_PREFIX}compliance-summary": ("mcp/apps/compliance_summary.html", "Compliance summary"),
}


def shows_app(uri):
    """Mark a tool handler as one whose result a host may show in the app at ``uri``."""
    if uri not in APPS:
        raise ValueError(f"No MCP app is served at {uri}")

    def decorator(handler):
        handler.mcp_app = uri
        return handler
    return decorator


def client_shows_apps(ctx):
    """True when the client declared MCP Apps with the HTML profile, for this request."""
    if not ctx.modern:
        return False
    extension = (ctx.client_capabilities.get("extensions") or {}).get(UI_EXTENSION)
    return isinstance(extension, dict) and MIME_TYPE in (extension.get("mimeTypes") or [])


def tool_meta(uri):
    """The ``_meta`` of a tool that shows an app (the flat key is the deprecated form some hosts read)."""
    return {"ui": {"resourceUri": uri}, "ui/resourceUri": uri}


def resource(uri):
    """The ``Resource`` entry of an app, for ``resources/list``."""
    return {"uri": uri, "name": APPS[uri][1], "mimeType": MIME_TYPE}


def read(uri, user):
    """The contents of the app at ``uri``, rendered in the language of ``user``; ``None`` if unknown."""
    if uri not in APPS:
        return None
    template, _title = APPS[uri]
    language = getattr(user, "language", "") or translation.get_language() or "en"
    with translation.override(language):
        html = render_to_string(template, {"language": language})
    return {"uri": uri, "mimeType": MIME_TYPE, "text": html, "_meta": {"ui": {"prefersBorder": True}}}

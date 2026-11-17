# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Content Security Policy : what a page may load and run.

Every page is sent with a ``Content-Security-Policy`` header that tells the
browser to run a script only when it comes from the instance's own static
files or carries the nonce of this very response. A script injected into a
page (through a field that escaped sanitising, a tampered record, a hostile
link) has neither, so the browser refuses it : the policy is the second line
behind output escaping and the rich-text sanitiser.

What it means for a template :

- an inline ``<script>`` carries ``nonce="{% csp_nonce %}"``;
- there is no inline event handler (``onclick=``...) : an element names an
  action registered in ``window.cairnActions`` (``data-on-click="..."``);
- nothing is loaded from another origin, except what a setting names (the map
  tiles, the geocoder).

Styles are allowed inline. A style cannot run code, the libraries in use
(Bootstrap, Tom Select, Leaflet, ECharts) position their elements with style
attributes, and refusing them would break those for no protection worth it.

``CSP_MODE`` switches the header to report-only or off (see the settings).
"""

import contextvars
import re
import secrets
from urllib.parse import urlsplit

from django.conf import settings

NONCE_BYTES = 18

# The request being answered, for ``{% csp_nonce %}``. A template context is
# not enough to carry the nonce : a form widget and an inclusion tag are
# rendered with a context of their own, where a context variable would be
# empty and the script silently refused. The tag reads the request from here,
# wherever in the response it is rendered.
_request = contextvars.ContextVar("cairn_csp_request", default=None)


def current_nonce():
    """The nonce of the response being rendered, created on first use.

    Empty outside a request (an e-mail, a PDF) : nothing there is subject to
    the policy.
    """
    request = _request.get()
    return request.csp_nonce() if request is not None else ""


def _origin(url):
    """The CSP source of a URL template : scheme and host, a ``{s}`` subdomain
    placeholder (tile servers) widened to a wildcard. ``None`` if not absolute."""
    parts = urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    host = re.sub(r"\{[a-z]+\}", "*", parts.netloc)
    return f"{parts.scheme}://{host}"


def _sources(*urls):
    seen = []
    for url in urls:
        origin = _origin(url)
        if origin and origin not in seen:
            seen.append(origin)
    return seen


def build_policy(request, nonce=None, exclude=()):
    """The policy of one response, as ``{directive: [sources]}``."""
    host = request.get_host()
    script = ["'self'"]
    if nonce:
        script.append(f"'nonce-{nonce}'")
    frame_ancestors = "'self'" if getattr(settings, "X_FRAME_OPTIONS", "DENY").upper() == "SAMEORIGIN" else "'none'"
    policy = {
        "default-src": ["'self'"],
        "script-src": script,
        "style-src": ["'self'", "'unsafe-inline'"],
        # data: for the logos and avatars stored inline, blob: for the charts
        # and files a page builds; the map tiles come from their provider.
        "img-src": ["'self'", "data:", "blob:", *_sources(settings.MAP_TILE_URL, settings.MAP_TILE_URL_DARK)],
        "font-src": ["'self'", "data:"],
        # The page's own WebSocket (same host, another scheme) and, when one
        # is set, the geocoder the maps ask for an address they have no
        # coordinates for.
        "connect-src": ["'self'", f"ws://{host}", f"wss://{host}", *_sources(settings.MAP_GEOCODER_URL)],
        "frame-src": ["'self'", "blob:"],
        "worker-src": ["'self'", "blob:"],
        "manifest-src": ["'self'"],
        "media-src": ["'self'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": [frame_ancestors],
    }
    for directive in exclude:
        policy.pop(directive, None)
    return policy


def serialize(policy):
    return "; ".join(f"{directive} {' '.join(sources)}" for directive, sources in policy.items())


class ContentSecurityPolicyMiddleware:
    """Send the policy with every response, and give templates their nonce.

    The nonce is created the first time a template asks for it
    (``{% csp_nonce %}``), so a response with no inline script carries none. A view may drop a directive that cannot hold for it by
    setting ``response.csp_exclude = {"form-action"}`` : the OAuth consent
    page posts to itself and is then redirected to the client's own address,
    which ``form-action`` would forbid.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._csp_nonce = None

        def nonce():
            if request._csp_nonce is None:
                request._csp_nonce = secrets.token_urlsafe(NONCE_BYTES)
            return request._csp_nonce

        request.csp_nonce = nonce
        token = _request.set(request)
        try:
            response = self.get_response(request)
        finally:
            _request.reset(token)

        mode = getattr(settings, "CSP_MODE", "enforce")
        if mode == "off":
            return response
        # Django's own debug error page is made of inline scripts : left alone
        # under DEBUG, where it is the page the developer needs to read.
        if settings.DEBUG and response.status_code >= 500:
            return response
        header = "Content-Security-Policy-Report-Only" if mode == "report" else "Content-Security-Policy"
        if header not in response:
            policy = build_policy(request, request._csp_nonce, getattr(response, "csp_exclude", ()))
            response[header] = serialize(policy)
        return response

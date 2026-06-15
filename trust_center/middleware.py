"""Optional dedicated-domain isolation for the public Trust Center.

When ``settings.TRUST_CENTER_HOST`` is set and a request arrives on that host,
only the public Trust Center surface is reachable: the landing page, its public
API and gated downloads (all under ``/trust/``), static assets, the i18n
endpoint and ``/.well-known/`` (TLS/ACME). Everything else (the authenticated
app, ``/admin/``, the internal API, MCP) returns 404, so the internal product is
not exposed on the public domain.

When ``TRUST_CENTER_HOST`` is empty the middleware is a no-op: the Trust Center
remains reachable only at the ``/trust/`` sub-path on the main host.

The host is read from settings on every request (not cached) so tests can use
``override_settings``.
"""

from django.conf import settings
from django.http import Http404


class TrustCenterHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _static_prefix(self):
        static_url = settings.STATIC_URL or "/static/"
        return static_url if static_url.startswith("/") else "/" + static_url

    def __call__(self, request):
        trust_host = (getattr(settings, "TRUST_CENTER_HOST", "") or "").strip().lower()
        if not trust_host:
            return self.get_response(request)

        host = request.get_host().split(":")[0].lower()
        if host != trust_host:
            return self.get_response(request)

        path = request.path_info
        # Serve the landing at the domain root by rewriting "/" to "/trust/".
        if path == "/":
            request.path_info = "/trust/"
            request.path = "/trust/"
            return self.get_response(request)

        allowed_prefixes = (
            "/trust/",
            self._static_prefix(),
            "/i18n/",
            "/.well-known/",
        )
        if any(path.startswith(prefix) for prefix in allowed_prefixes):
            return self.get_response(request)

        raise Http404()

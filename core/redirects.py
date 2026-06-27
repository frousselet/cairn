"""Open-redirect guard for views that redirect to user-supplied URLs."""

from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_target(request, url, fallback="/"):
    """Return ``url`` only if it points to the current host (no open redirect).

    Guards against CodeQL ``py/url-redirection``: ``next`` parameters and the
    ``Referer`` header are attacker-controlled, so validate them before passing
    the value to ``redirect()``. Falls back to ``fallback`` (a safe internal
    target) when the URL is missing or points off-site.
    """
    if url and url_has_allowed_host_and_scheme(
        url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return url
    return fallback

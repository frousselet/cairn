# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Whether a newer Cairn release is published.

The instance asks GitHub for the latest release of its own repository and
compares it with the version it is running. This is the one outbound call the
interface makes, and it is deliberate on both counts :

* it fires only when someone opens the About modal, never on a page load, so an
  instance nobody asks stays silent;
* it can be switched off entirely (``UPDATE_CHECK_ENABLED=False``), for an
  air-gapped deployment or one whose policy forbids calling out.

The answer is cached across workers (the shared Redis cache), so a fleet of
uvicorn workers asks once per period rather than once per curious user. Failures
are cached too, for a shorter time : a GitHub outage or a blocked egress must
not turn every About modal into a five-second wait.
"""
import re

import httpx
from django.conf import settings
from django.core.cache import cache

#: The repository whose releases describe this application.
RELEASES_API = "https://api.github.com/repos/frousselet/cairn/releases/latest"
RELEASES_PAGE = "https://github.com/frousselet/cairn/releases"

CACHE_KEY = "cairn:latest-release"
CACHE_TTL = 6 * 60 * 60
#: Short, so a transient failure is retried soon without hammering the API.
FAILURE_CACHE_TTL = 15 * 60

REQUEST_TIMEOUT = 5.0


def _version_tuple(version):
    """``"v1.2.10"`` -> ``(1, 2, 10)``. ``None`` for anything not a release
    number : ``dev``, a git description, an empty string."""
    if not version:
        return None
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version.strip())
    return tuple(int(part) for part in match.groups()) if match else None


def fetch_latest_release():
    """The latest published release, or ``None`` when it cannot be read.

    Draft and pre-release entries are excluded by the endpoint itself, so what
    comes back is what a user would be told to install.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached or None  # "" is the cached failure

    try:
        response = httpx.get(
            RELEASES_API,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "cairn"},
        )
        response.raise_for_status()
        payload = response.json()
        release = {
            "version": (payload.get("tag_name") or "").lstrip("v"),
            "url": payload.get("html_url") or RELEASES_PAGE,
            "published_at": payload.get("published_at") or "",
        }
    except Exception:
        # Network, DNS, rate limit, malformed payload : all mean "unknown", and
        # none of them is worth surfacing to someone who opened an About modal.
        cache.set(CACHE_KEY, "", FAILURE_CACHE_TTL)
        return None

    if not release["version"]:
        cache.set(CACHE_KEY, "", FAILURE_CACHE_TTL)
        return None

    cache.set(CACHE_KEY, release, CACHE_TTL)
    return release


def update_status():
    """What the About modal shows, as a plain dict.

    ``state`` is one of :

    ``disabled``
        The check is switched off for this instance.
    ``unknown``
        GitHub could not be reached, or this build has no release number to
        compare (a development build, an untagged image).
    ``current``
        This instance runs the latest published release.
    ``outdated``
        A newer release exists; ``latest_version`` and ``url`` point at it.
    """
    current = getattr(settings, "APP_VERSION", "") or ""
    result = {
        "state": "unknown",
        "current_version": current,
        "latest_version": "",
        "url": RELEASES_PAGE,
    }

    if not getattr(settings, "UPDATE_CHECK_ENABLED", True):
        result["state"] = "disabled"
        return result

    release = fetch_latest_release()
    if not release:
        return result

    result["latest_version"] = release["version"]
    result["url"] = release["url"]

    running = _version_tuple(current)
    latest = _version_tuple(release["version"])
    if running is None or latest is None:
        # A development build has no place on this scale : it is not "behind"
        # the last release, it is simply not one.
        return result

    result["state"] = "outdated" if latest > running else "current"
    return result

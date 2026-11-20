# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""What a crawl of the interface follows, and how it tells two pages apart.

Shared by the interface sweep (``core/tests/test_site_sweep.py``), which
follows every link of the demo dataset through the test client, and by the
browser audit (``scripts/a11y_audit.py --crawl``), which follows the same
links on a running instance and audits each kind of page once.
"""

import re

#: Links a crawl does not follow.
SKIP = re.compile(
    r"^/(?:static|media|admin|api|i18n|oauth|authorize|\.well-known)(?:/|$)"  # not the web UI
    r"|logout"                # would end the crawl's own session
    r"|/impersonate"          # would change who the crawl is
)
#: The links a page offers : its anchors and the URLs it loads over HTMX.
LINK = re.compile(r"""(?:href|hx-get)=["']([^"'#]+)""")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def page_type(url):
    """The URL with its record ids blanked : one entry per page type."""
    path, _, query = url.partition("?")
    path = re.sub(r"/\d+(?=/|$)", "/<n>", UUID.sub("<id>", path))
    keys = sorted(part.split("=")[0] for part in query.split("&")) if query else []
    return path + ("?" + "&".join(keys) if keys else "")


def links_of(html):
    """The same-site links of a page a crawl follows, in the order they appear."""
    for link in LINK.findall(html):
        link = link.replace("&amp;", "&")
        if link.startswith("/") and not link.startswith("//") and not SKIP.search(link):
            yield link

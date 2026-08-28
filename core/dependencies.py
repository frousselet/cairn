# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The third-party components Cairn is built on.

The list is curated rather than derived : the running application has no single
machine-readable inventory to read from (Python distributions come from
``requirements.txt``, front-end libraries are declared below). Keeping one
registry means the About modal, the REST API and the MCP tool all answer the
same thing.

Versions of the Python distributions are resolved at runtime from the installed
metadata, so they cannot drift. Front-end libraries are pinned here **and this
registry is what actually loads them** : every file listed in a dependency's
``assets`` is downloaded into ``static/vendor/`` by ``manage.py vendor_assets``
and served from there, so a running instance never calls a CDN. The templates
reference those files through ``{% static %}`` and carry no version of their
own, which is why the pin below cannot drift from what the browser gets.

Adding, removing or upgrading a library : update this registry in the same
commit, then re-run ``manage.py vendor_assets --upgrade`` to refresh the local
copies and their integrity digests (``--print-hashes`` prints the new ones).
"""
from dataclasses import dataclass
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version
from urllib.parse import urlsplit

from django.utils.translation import gettext_lazy as _

BACKEND = "backend"
FRONTEND = "frontend"
DEVELOPMENT = "development"

GROUP_LABELS = {
    BACKEND: _("Backend (Python)"),
    FRONTEND: _("Frontend (JavaScript, CSS, fonts)"),
    DEVELOPMENT: _("Development and testing"),
}


@lru_cache(maxsize=None)
def _installed_version(distribution: str) -> str:
    """Version of an installed Python distribution, or "" when it cannot be read
    (a partial install, or a documentation build outside the app environment)."""
    try:
        return _distribution_version(distribution)
    except PackageNotFoundError:
        return ""


@dataclass(frozen=True)
class VendorAsset:
    """One file of a front-end library, mirrored under ``static/vendor/``.

    ``path`` is relative to ``static/vendor/`` and must keep the layout the
    library's own files expect : ``bootstrap-icons.min.css`` asks for
    ``fonts/bootstrap-icons.woff2`` and ``leaflet.css`` for
    ``images/marker-icon.png``, both relative to themselves.

    ``sha384`` is the Subresource-Integrity digest of the published file. The
    download is rejected when it does not match, so a compromised or truncated
    mirror can never end up served to a browser.
    """

    url: str
    path: str
    sha384: str


@dataclass(frozen=True)
class Dependency:
    """One third-party component, with the official repository it is published from."""

    name: str
    url: str
    purpose: str
    group: str = BACKEND
    #: Python distribution name, when the version can be read from the installed metadata.
    distribution: str = ""
    #: Version pinned here and mirrored under ``static/vendor/`` (front-end only).
    pinned_version: str = ""
    #: Files mirrored locally so the instance loads the library offline (front-end only).
    assets: tuple = ()

    @property
    def version(self) -> str:
        if self.distribution:
            return _installed_version(self.distribution)
        return self.pinned_version

    @property
    def owner(self) -> str:
        """The account the library is published under, read from its repository
        URL : the organisation or user owning it (``twbs`` for Bootstrap). Shown
        next to the name so the About modal names a provenance, not just a
        package : two libraries can share a name, an owner and a name cannot."""
        path = urlsplit(self.url).path.strip("/")
        return path.split("/")[0] if path else ""

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "owner": self.owner,
            "version": self.version,
            "url": self.url,
            "purpose": self.purpose,
            "group": self.group,
        }


#: jsDelivr mirrors every npm package under one immutable, versioned URL space.
NPM = "https://cdn.jsdelivr.net/npm/"

DEPENDENCIES = (
    # ── Backend ────────────────────────────────────────────
    Dependency("Django", "https://github.com/django/django",
               "Web framework : ORM, templating, authentication, admin.",
               BACKEND, distribution="Django"),
    Dependency("Django REST framework", "https://github.com/encode/django-rest-framework",
               "REST API layer serving /api/v1.",
               BACKEND, distribution="djangorestframework"),
    Dependency("django-filter", "https://github.com/carltongibson/django-filter",
               "Query-string filtering for API and list views.",
               BACKEND, distribution="django-filter"),
    Dependency("django-simple-history", "https://github.com/jazzband/django-simple-history",
               "Audit trail : historical records on every model.",
               BACKEND, distribution="django-simple-history"),
    Dependency("django-htmx", "https://github.com/adamchainz/django-htmx",
               "HTMX request helpers for Django views.",
               BACKEND, distribution="django-htmx"),
    Dependency("djangorestframework-simplejwt", "https://github.com/jazzband/djangorestframework-simplejwt",
               "JWT authentication for the REST API and the MCP server.",
               BACKEND, distribution="djangorestframework-simplejwt"),
    Dependency("Channels", "https://github.com/django/channels",
               "ASGI and WebSocket support (live notifications).",
               BACKEND, distribution="channels"),
    Dependency("channels-redis", "https://github.com/django/channels_redis",
               "Redis channel layer for Channels.",
               BACKEND, distribution="channels-redis"),
    Dependency("redis-py", "https://github.com/redis/redis-py",
               "Redis client : shared cache backend and channel layer.",
               BACKEND, distribution="redis"),
    Dependency("psycopg", "https://github.com/psycopg/psycopg",
               "PostgreSQL database driver.",
               BACKEND, distribution="psycopg"),
    Dependency("Gunicorn", "https://github.com/benoitc/gunicorn",
               "Production process manager.",
               BACKEND, distribution="gunicorn"),
    Dependency("Uvicorn", "https://github.com/encode/uvicorn",
               "ASGI server.",
               BACKEND, distribution="uvicorn"),
    Dependency("Daphne", "https://github.com/django/daphne",
               "ASGI server used by the Channels development stack.",
               BACKEND, distribution="daphne"),
    Dependency("WhiteNoise", "https://github.com/evansd/whitenoise",
               "Static file serving from the application process.",
               BACKEND, distribution="whitenoise"),
    Dependency("HTTPX", "https://github.com/encode/httpx",
               "HTTP client for outbound calls (AI assistant providers, webhooks).",
               BACKEND, distribution="httpx"),
    Dependency("WeasyPrint", "https://github.com/Kozea/WeasyPrint",
               "HTML to PDF rendering for reports and evidence packs.",
               BACKEND, distribution="weasyprint"),
    Dependency("openpyxl", "https://foss.heptapod.net/openpyxl/openpyxl",
               "Excel import and export (frameworks, registers).",
               BACKEND, distribution="openpyxl"),
    Dependency("python-pptx", "https://github.com/scanny/python-pptx",
               "PowerPoint generation for management review decks.",
               BACKEND, distribution="python-pptx"),
    Dependency("python-docx", "https://github.com/python-openxml/python-docx",
               "Word document generation for reports.",
               BACKEND, distribution="python-docx"),
    Dependency("Pillow", "https://github.com/python-pillow/Pillow",
               "Image processing for uploaded logos and attachments.",
               BACKEND, distribution="Pillow"),
    Dependency("python-fido2", "https://github.com/Yubico/python-fido2",
               "WebAuthn / passkey authentication.",
               BACKEND, distribution="fido2"),
    Dependency("icalendar", "https://github.com/collective/icalendar",
               "iCalendar feeds for the compliance calendar.",
               BACKEND, distribution="icalendar"),

    # ── Frontend ───────────────────────────────────────────
    # Every file below is mirrored under ``static/vendor/`` and served from
    # there : the running instance never reaches a CDN. ``url`` is only the
    # upstream Cairn fetches from at build time (Docker) or first launch.
    Dependency("Bootstrap", "https://github.com/twbs/bootstrap",
               "UI component framework and grid.",
               FRONTEND, pinned_version="5.3.8", assets=(
                   VendorAsset(f"{NPM}bootstrap@5.3.8/dist/css/bootstrap.min.css",
                               "bootstrap/bootstrap.min.css",
                               "sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB"),
                   VendorAsset(f"{NPM}bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js",
                               "bootstrap/bootstrap.bundle.min.js",
                               "sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI"),
               )),
    Dependency("Bootstrap Icons", "https://github.com/twbs/icons",
               "The single icon set used across the interface.",
               FRONTEND, pinned_version="1.13.1", assets=(
                   VendorAsset(f"{NPM}bootstrap-icons@1.13.1/font/bootstrap-icons.min.css",
                               "bootstrap-icons/bootstrap-icons.min.css",
                               "sha384-CK2SzKma4jA5H/MXDUU7i1TqZlCFaD4T01vtyDFvPlD97JQyS+IsSh1nI2EFbpyk"),
                   # The stylesheet asks for these two by a relative "fonts/" path.
                   VendorAsset(f"{NPM}bootstrap-icons@1.13.1/font/fonts/bootstrap-icons.woff2",
                               "bootstrap-icons/fonts/bootstrap-icons.woff2",
                               "sha384-xEoI56EFpIZiDZZKBZxsn3gO3u/FvXtOpHbtkMWmSdfzDw3x9XdVc3i70O9hm4SC"),
                   VendorAsset(f"{NPM}bootstrap-icons@1.13.1/font/fonts/bootstrap-icons.woff",
                               "bootstrap-icons/fonts/bootstrap-icons.woff",
                               "sha384-IYfD9pNP/nesQsPyYtTdGCb4uhEWUmNF8GxaCvqcJFH+Of3c1b0VbH6hdHUonDSC"),
               )),
    Dependency("htmx", "https://github.com/bigskysoftware/htmx",
               "HTML-over-the-wire partial updates.",
               FRONTEND, pinned_version="2.0.10", assets=(
                   VendorAsset(f"{NPM}htmx.org@2.0.10/dist/htmx.min.js",
                               "htmx/htmx.min.js",
                               "sha384-H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V"),
               )),
    Dependency("Tom Select", "https://github.com/orchidjs/tom-select",
               "Searchable single and multi-select widgets.",
               FRONTEND, pinned_version="2.6.2", assets=(
                   VendorAsset(f"{NPM}tom-select@2.6.2/dist/css/tom-select.bootstrap5.min.css",
                               "tom-select/tom-select.bootstrap5.min.css",
                               "sha384-qNqaCnsmyTrYVwmqv4/4PcwMK8ZFAQnYPpVjWor+6cX6rKsPhebzu8vO2J3s+VZg"),
                   VendorAsset(f"{NPM}tom-select@2.6.2/dist/js/tom-select.complete.min.js",
                               "tom-select/tom-select.complete.min.js",
                               "sha384-1mYKSrq1Nu5YJmWrIU9cvwWQlUyyukJJM9XMkAxY03nb/T69CK+Sn7rjFxVU3SSM"),
               )),
    Dependency("pell", "https://github.com/jaredreich/pell",
               "Rich text editor for long-form fields.",
               FRONTEND, pinned_version="1.0.6", assets=(
                   VendorAsset(f"{NPM}pell@1.0.6/dist/pell.min.css",
                               "pell/pell.min.css",
                               "sha384-5A/u54uTOLVDcH2/EkSGtmIFDw5ZGPakPcL3p5azX51R6lBn37DIL6rpmpLOJMns"),
                   VendorAsset(f"{NPM}pell@1.0.6/dist/pell.min.js",
                               "pell/pell.min.js",
                               "sha384-OdpVdpmcYA4eVE3sgp68n24zLKUZtn6GeGSiO5jl7iLloVVT1Vn8Pw+P5vQDEKoC"),
               )),
    Dependency("DOMPurify", "https://github.com/cure53/DOMPurify",
               "Sanitises rich text before it is rendered.",
               FRONTEND, pinned_version="3.4.14", assets=(
                   VendorAsset(f"{NPM}dompurify@3.4.14/dist/purify.min.js",
                               "dompurify/purify.min.js",
                               "sha384-46dPGH1XlTmj7bc50bqLjTdORXs/3EP2QpA/6EWbelYWOY9VGp+87RT61S3Mcslb"),
               )),
    Dependency("Sortable", "https://github.com/SortableJS/Sortable",
               "Drag and drop for the dashboard grid and kanban boards.",
               FRONTEND, pinned_version="1.15.7", assets=(
                   VendorAsset(f"{NPM}sortablejs@1.15.7/Sortable.min.js",
                               "sortablejs/Sortable.min.js",
                               "sha384-DgmC6Xe2bSN2WjTDXzWYbUbxyhNP+NNkGDR/g78pCXV7E7rcVTGxVg0uIVCUUcBc"),
               )),
    Dependency("ECharts", "https://github.com/apache/echarts",
               "Dashboard and report charts.",
               FRONTEND, pinned_version="5.6.0", assets=(
                   VendorAsset(f"{NPM}echarts@5.6.0/dist/echarts.min.js",
                               "echarts/echarts.min.js",
                               "sha384-pPi0zxBAoDu6+JXW/C68UZLvBUUtU+7zonhif43rqj7pxsGyqyqzcian2Rj37Rss"),
               )),
    Dependency("D3", "https://github.com/d3/d3",
               "Rendering of the lifecycle graph.",
               FRONTEND, pinned_version="7.9.0", assets=(
                   VendorAsset(f"{NPM}d3@7.9.0/dist/d3.min.js",
                               "d3/d3.min.js",
                               "sha384-CjloA8y00+1SDAUkjs099PVfnY2KmDC2BZnws9kh8D/lX1s46w6EPhpXdqMfjK6i"),
               )),
    Dependency("dagre", "https://github.com/dagrejs/dagre",
               "Layered layout of the lifecycle graph.",
               FRONTEND, pinned_version="0.8.5", assets=(
                   VendorAsset(f"{NPM}dagre@0.8.5/dist/dagre.min.js",
                               "dagre/dagre.min.js",
                               "sha384-2IH3T69EIKYC4c+RXZifZRvaH5SRUdacJW7j6HtE5rQbvLhKKdawxq6vpIzJ7j9M"),
               )),
    Dependency("Leaflet", "https://github.com/Leaflet/Leaflet",
               "Maps on site and supplier pages.",
               FRONTEND, pinned_version="1.9.4", assets=(
                   VendorAsset(f"{NPM}leaflet@1.9.4/dist/leaflet.css",
                               "leaflet/leaflet.css",
                               "sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H"),
                   VendorAsset(f"{NPM}leaflet@1.9.4/dist/leaflet.js",
                               "leaflet/leaflet.js",
                               "sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH"),
                   # Control and marker sprites, referenced by a relative "images/" path
                   # from leaflet.css and from the library's own default icon.
                   VendorAsset(f"{NPM}leaflet@1.9.4/dist/images/layers.png",
                               "leaflet/images/layers.png",
                               "sha384-80x85ZS+G189o0xL8E8D7BnfhuNss6EwUPHzG7e+qByRD2xnpxikZ6UQU4Re5nNy"),
                   VendorAsset(f"{NPM}leaflet@1.9.4/dist/images/layers-2x.png",
                               "leaflet/images/layers-2x.png",
                               "sha384-+F2ZWK/HTpkV9kN2HnMGCQOTM/cnQJLs770FLOeHznwVWRfDESI8z4JwcGYmy2Au"),
                   VendorAsset(f"{NPM}leaflet@1.9.4/dist/images/marker-icon.png",
                               "leaflet/images/marker-icon.png",
                               "sha384-wg83fCOXjBtqzFAWhTL9Sd9vmLUNhfEEzfmNUX9zwv2igKlz/YQbdapF4ObdxF+R"),
                   VendorAsset(f"{NPM}leaflet@1.9.4/dist/images/marker-icon-2x.png",
                               "leaflet/images/marker-icon-2x.png",
                               "sha384-bDEa1RhAAKIr/VQnMZ7gUhhXwmKYB4V0g8AsxOvCEPwGxfHCUEzAEMAEEzkjuxiA"),
                   VendorAsset(f"{NPM}leaflet@1.9.4/dist/images/marker-shadow.png",
                               "leaflet/images/marker-shadow.png",
                               "sha384-dB8ivfvPGb1MSIzX8oWTakCxmq+VwqP/QL1TX4jT4INR3pM5T4FgF3Gx4mN3NTMq"),
               )),
    Dependency("GitLab Sans", "https://gitlab.com/gitlab-org/frontend/fonts",
               "The interface typeface (OFL-1.1).",
               FRONTEND, pinned_version="1.3.1", assets=(
                   VendorAsset(f"{NPM}@gitlab/fonts@1.3.1/gitlab-sans/GitLabSans.woff2",
                               "gitlab-sans/GitLabSans.woff2",
                               "sha384-QsKDIActT1q/eB88LpugOg6KctetwJLwvbCKYFpx81uskIZ+cvwDlxGOmdua8DRy"),
                   VendorAsset(f"{NPM}@gitlab/fonts@1.3.1/gitlab-sans/GitLabSans-Italic.woff2",
                               "gitlab-sans/GitLabSans-Italic.woff2",
                               "sha384-gmv07pWyqKBHBZWr4+te+Ve5pHJprX/PMOmzVxJQZyxEgUcpKEVLjppqGUAFrGLz"),
               )),

    # ── Development and testing ────────────────────────────
    Dependency("Ruff", "https://github.com/astral-sh/ruff",
               "Linter enforced in CI.",
               DEVELOPMENT, distribution="ruff"),
    Dependency("pytest", "https://github.com/pytest-dev/pytest",
               "Test runner.",
               DEVELOPMENT, distribution="pytest"),
    Dependency("pytest-django", "https://github.com/pytest-dev/pytest-django",
               "Django fixtures and database handling for pytest.",
               DEVELOPMENT, distribution="pytest-django"),
    Dependency("pytest-cov", "https://github.com/pytest-dev/pytest-cov",
               "Coverage measurement.",
               DEVELOPMENT, distribution="pytest-cov"),
    Dependency("pytest-asyncio", "https://github.com/pytest-dev/pytest-asyncio",
               "Async test support (Channels, MCP).",
               DEVELOPMENT, distribution="pytest-asyncio"),
    Dependency("pytest-xdist", "https://github.com/pytest-dev/pytest-xdist",
               "Parallel test execution.",
               DEVELOPMENT, distribution="pytest-xdist"),
    Dependency("factory_boy", "https://github.com/FactoryBoy/factory_boy",
               "Test data factories.",
               DEVELOPMENT, distribution="factory-boy"),
)


def _sort_key(dependency):
    """Owner first, then library : the order the About modal lists them in.

    Grouping by owner puts a publisher's libraries together (all of Django's,
    all of Encode's), which reads as an inventory rather than as a pile. Case is
    folded so ``Yubico`` does not sort ahead of ``adamchainz``.
    """
    return (dependency.owner.lower(), dependency.name.lower())


def dependencies_by_group():
    """The registry as ``[(group_key, label, [Dependency, ...]), ...]`` : the
    groups in their declared order, the libraries inside each sorted by owner
    then name."""
    return [
        (group, GROUP_LABELS[group],
         sorted((d for d in DEPENDENCIES if d.group == group), key=_sort_key))
        for group in (BACKEND, FRONTEND, DEVELOPMENT)
    ]


def serialize_dependencies():
    """The registry as plain dicts, for the REST API and the MCP tool.

    Same order as the About modal, so an integrator diffing two instances sees
    only real differences.
    """
    return [d.as_dict() for _key, _label, deps in dependencies_by_group() for d in deps]


def vendor_assets():
    """Every file to mirror under ``static/vendor/``, across all libraries."""
    return [asset for dep in DEPENDENCIES for asset in dep.assets]

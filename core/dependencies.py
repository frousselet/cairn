# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The third-party components Cairn is built on.

The list is curated rather than derived : the running application has no single
machine-readable inventory to read from (Python distributions come from
``requirements.txt``, front-end libraries are pinned by URL in ``base.html``,
two of them are vendored under ``static/vendor/``). Keeping one registry means
the About modal, the REST API and the MCP tool all answer the same thing.

Versions of the Python distributions are resolved at runtime from the installed
metadata, so they cannot drift; front-end versions are pinned here and checked
against the templates by ``core/tests/test_dependencies.py``.

Adding or removing a library : update this registry in the same commit.
"""
from dataclasses import dataclass
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

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
class Dependency:
    """One third-party component, with the official repository it is published from."""

    name: str
    url: str
    purpose: str
    group: str = BACKEND
    #: Python distribution name, when the version can be read from the installed metadata.
    distribution: str = ""
    #: Version pinned in a template or vendored under ``static/vendor/`` (front-end only).
    pinned_version: str = ""

    @property
    def version(self) -> str:
        if self.distribution:
            return _installed_version(self.distribution)
        return self.pinned_version

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "url": self.url,
            "purpose": self.purpose,
            "group": self.group,
        }


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
    Dependency("Bootstrap", "https://github.com/twbs/bootstrap",
               "UI component framework and grid.",
               FRONTEND, pinned_version="5.3.8"),
    Dependency("Bootstrap Icons", "https://github.com/twbs/icons",
               "The single icon set used across the interface.",
               FRONTEND, pinned_version="1.11.3"),
    Dependency("htmx", "https://github.com/bigskysoftware/htmx",
               "HTML-over-the-wire partial updates.",
               FRONTEND, pinned_version="2.0.4"),
    Dependency("Tom Select", "https://github.com/orchidjs/tom-select",
               "Searchable single and multi-select widgets.",
               FRONTEND, pinned_version="2.4.1"),
    Dependency("pell", "https://github.com/jaredreich/pell",
               "Rich text editor for long-form fields.",
               FRONTEND, pinned_version="1.0.6"),
    Dependency("DOMPurify", "https://github.com/cure53/DOMPurify",
               "Sanitises rich text before it is rendered.",
               FRONTEND, pinned_version="3.2.4"),
    Dependency("SortableJS", "https://github.com/SortableJS/Sortable",
               "Drag and drop for the dashboard grid and kanban boards.",
               FRONTEND, pinned_version="1.15.6"),
    Dependency("Apache ECharts", "https://github.com/apache/echarts",
               "Dashboard and report charts.",
               FRONTEND, pinned_version="5.5.1"),
    Dependency("D3", "https://github.com/d3/d3",
               "Rendering of the lifecycle graph.",
               FRONTEND, pinned_version="7.9.0"),
    Dependency("dagre", "https://github.com/dagrejs/dagre",
               "Layered layout of the lifecycle graph.",
               FRONTEND, pinned_version="0.8.5"),
    Dependency("Leaflet", "https://github.com/Leaflet/Leaflet",
               "Maps on site and supplier pages.",
               FRONTEND, pinned_version="1.9.4"),
    Dependency("GitLab Sans", "https://gitlab.com/gitlab-org/frontend/fonts",
               "The interface typeface (OFL-1.1).",
               FRONTEND, pinned_version="1.3.1"),

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


def dependencies_by_group():
    """The registry as ``[(group_key, label, [Dependency, ...]), ...]``, in the
    declared order : backend, frontend, then development."""
    return [
        (group, GROUP_LABELS[group], [d for d in DEPENDENCIES if d.group == group])
        for group in (BACKEND, FRONTEND, DEVELOPMENT)
    ]


def serialize_dependencies():
    """The registry as plain dicts, for the REST API and the MCP tool."""
    return [d.as_dict() for d in DEPENDENCIES]

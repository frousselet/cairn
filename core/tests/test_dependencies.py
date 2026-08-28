# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The third-party registry must describe the components actually shipped.

The registry in ``core/dependencies.py`` is what the About modal, the REST
endpoint and the ``list_dependencies`` MCP tool all answer from, so a library
added to ``requirements.txt`` or pinned in a template without a registry entry
would make the instance state an inventory that is not its own.
"""
import pathlib
import re

import pytest

from accounts.tests.factories import UserFactory
from core.dependencies import (
    BACKEND,
    DEPENDENCIES,
    DEVELOPMENT,
    FRONTEND,
    dependencies_by_group,
    serialize_dependencies,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: How each front-end library's pinned version is written where it is loaded.
FRONTEND_VERSION_MARKERS = {
    "Bootstrap": "bootstrap@{version}/",
    "Bootstrap Icons": "bootstrap-icons@{version}/",
    "htmx": "htmx.org@{version}",
    "Tom Select": "tom-select@{version}/",
    "pell": "pell@{version}/",
    "DOMPurify": "dompurify@{version}/",
    "SortableJS": "sortablejs@{version}/",
    "Apache ECharts": "echarts@{version}/",
    "Leaflet": "leaflet@{version}/",
    "GitLab Sans": "@gitlab/fonts@{version}/",
    "dagre": "dagre@{version}/",
    # Vendored: the version only exists in the file's own header.
    "D3": "d3js.org v{version}",
}


def _normalise(name):
    return name.lower().replace("_", "-")


def _requirements():
    """The distributions declared in requirements.txt, extras and comments stripped."""
    raw = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    names = []
    for line in raw.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        names.append(_normalise(re.split(r"[\[<>=!;]", line)[0].strip()))
    return names


def _asset_sources():
    """Every template and static asset, concatenated : where front-end pins live."""
    roots = [REPO_ROOT / "templates", REPO_ROOT / "static"]
    roots += sorted(REPO_ROOT.glob("*/templates"))
    chunks = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".html", ".js", ".css"}:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def test_every_entry_is_complete_and_points_at_a_repository():
    for dep in DEPENDENCIES:
        assert dep.name, "a dependency has no name"
        assert dep.purpose, f"{dep.name} has no purpose"
        assert dep.group in (BACKEND, FRONTEND, DEVELOPMENT), f"{dep.name} has an unknown group"
        assert dep.url.startswith("https://"), f"{dep.name} must link to an https repository"

    names = [d.name for d in DEPENDENCIES]
    assert len(names) == len(set(names)), "duplicate dependency name"
    urls = [d.url for d in DEPENDENCIES]
    assert len(urls) == len(set(urls)), "duplicate repository URL"


def test_registry_matches_requirements_txt():
    declared = set(_requirements())
    registered = {_normalise(d.distribution) for d in DEPENDENCIES if d.distribution}

    assert declared - registered == set(), "requirement missing from core/dependencies.py"
    assert registered - declared == set(), "registry lists a distribution that is not required"


def test_python_versions_resolve_from_the_installed_metadata():
    for dep in DEPENDENCIES:
        if dep.distribution:
            assert dep.version, f"{dep.name} : version unreadable from the installed metadata"


def test_frontend_versions_match_the_pins_in_the_templates():
    sources = _asset_sources()
    frontend = [d for d in DEPENDENCIES if d.group == FRONTEND]

    assert {d.name for d in frontend} == set(FRONTEND_VERSION_MARKERS), (
        "add the new front-end library to FRONTEND_VERSION_MARKERS"
    )
    for dep in frontend:
        marker = FRONTEND_VERSION_MARKERS[dep.name].format(version=dep.pinned_version)
        assert marker in sources, f"{dep.name} {dep.pinned_version} is not the version actually loaded"


def test_grouping_covers_every_entry_in_declaration_order():
    grouped = dependencies_by_group()

    assert [key for key, _label, _deps in grouped] == [BACKEND, FRONTEND, DEVELOPMENT]
    assert sum(len(deps) for _key, _label, deps in grouped) == len(DEPENDENCIES)


@pytest.mark.django_db
def test_about_modal_lists_the_libraries_with_their_repository(client):
    client.force_login(UserFactory())
    html = client.get("/").content.decode()

    assert "Open source libraries" in html
    assert "https://github.com/django/django" in html
    assert "https://github.com/twbs/bootstrap" in html
    # The list is collapsed by default so the modal stays an identity card.
    assert 'id="aboutLibraries"' in html


@pytest.mark.django_db
def test_dependencies_endpoint_returns_the_same_registry(client):
    client.force_login(UserFactory())
    response = client.get("/api/v1/dependencies/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(DEPENDENCIES)
    assert payload["data"] == serialize_dependencies()


@pytest.mark.django_db
def test_dependencies_endpoint_requires_authentication(client):
    assert client.get("/api/v1/dependencies/").status_code in (401, 403)

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The third-party registry must describe the components actually shipped.

The registry in ``core/dependencies.py`` is what the About modal, the REST
endpoint and the ``list_dependencies`` MCP tool all answer from, so a library
added to ``requirements.txt`` without a registry entry would make the instance
state an inventory that is not its own.

For the front-end the registry does more than describe : it is what loads the
libraries, by declaring the files mirrored under ``static/vendor/``. The tests
below hold that contract together - a pinned version has to appear in the URLs
actually fetched, every ``{% static "vendor/..." %}`` a template asks for has to
be a declared file, and no template may reach a CDN.
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
    vendor_assets,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Hosts that publish the libraries. A template reaching one of these directly
#: would put a third party back in the page's critical path - the whole point of
#: mirroring is that the browser only ever talks to this instance.
LIBRARY_CDN_HOSTS = (
    "cdn.jsdelivr.net",
    "unpkg.com",
    "cdnjs.cloudflare.com",
    "d3js.org",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
)


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


def _template_sources():
    """Every template and hand-written static file, as ``(path, text)`` pairs.

    ``static/vendor/`` is excluded : those are the mirrored libraries themselves,
    which legitimately mention the CDN they were published from.
    """
    roots = [REPO_ROOT / "templates", REPO_ROOT / "static"]
    roots += sorted(REPO_ROOT.glob("*/templates"))
    mirror = REPO_ROOT / "static" / "vendor"
    sources = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in {".html", ".js", ".css"}:
                continue
            if mirror in path.parents:
                continue
            sources.append((path, path.read_text(encoding="utf-8", errors="ignore")))
    return sources


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


def test_every_frontend_library_declares_the_files_it_is_loaded_from():
    for dep in DEPENDENCIES:
        if dep.group != FRONTEND:
            continue
        assert dep.pinned_version, f"{dep.name} : front-end libraries are pinned by version"
        assert dep.assets, (
            f"{dep.name} : declare the files to mirror, or the instance cannot serve it offline"
        )


def test_pinned_versions_are_the_versions_actually_fetched():
    """The pin is not a label : it has to be in the URL the file comes from."""
    for dep in DEPENDENCIES:
        for asset in dep.assets:
            assert f"@{dep.pinned_version}/" in asset.url, (
                f"{dep.name} : {asset.url} does not fetch the pinned {dep.pinned_version}"
            )


def test_every_mirrored_file_is_verifiable_and_lands_inside_the_mirror():
    paths = [a.path for a in vendor_assets()]
    assert len(paths) == len(set(paths)), "two libraries would overwrite the same file"

    for asset in vendor_assets():
        assert asset.url.startswith("https://"), f"{asset.path} : fetched over plain HTTP"
        assert asset.sha384.startswith("sha384-") and len(asset.sha384) > 40, (
            f"{asset.path} : no usable integrity digest"
        )
        assert not asset.path.startswith("/") and ".." not in asset.path.split("/"), (
            f"{asset.path} : must stay inside static/vendor/"
        )


def test_templates_only_load_libraries_declared_in_the_registry():
    """A ``{% static "vendor/..." %}`` path that nothing mirrors is a 404 waiting
    to happen : the file would simply never be downloaded."""
    declared = {a.path for a in vendor_assets()}
    referenced = set()
    for path, text in _template_sources():
        for match in re.finditer(r"vendor/([A-Za-z0-9][A-Za-z0-9._@/-]*\.[A-Za-z0-9]+)", text):
            referenced.add((path, match.group(1)))

    unknown = {(p.relative_to(REPO_ROOT).as_posix(), ref) for p, ref in referenced if ref not in declared}
    assert unknown == set(), f"referenced but not mirrored : {sorted(unknown)}"


def test_no_template_loads_a_library_from_a_third_party():
    """The offline guarantee, enforced : the interface must not need a CDN."""
    offenders = []
    for path, text in _template_sources():
        for host in LIBRARY_CDN_HOSTS:
            if host in text:
                offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()} -> {host}")
    assert offenders == [], (
        "load the library from static/vendor/ instead, and declare it in "
        f"core/dependencies.py : {offenders}"
    )


def test_grouping_covers_every_entry_in_declaration_order():
    grouped = dependencies_by_group()

    assert [key for key, _label, _deps in grouped] == [BACKEND, FRONTEND, DEVELOPMENT]
    assert sum(len(deps) for _key, _label, deps in grouped) == len(DEPENDENCIES)


def test_each_group_is_listed_by_owner_then_library():
    for _key, _label, deps in dependencies_by_group():
        keys = [(d.owner.lower(), d.name.lower()) for d in deps]
        assert keys == sorted(keys), "the About modal would list them out of order"


@pytest.mark.django_db
def test_about_modal_lists_the_libraries_with_their_repository(client):
    client.force_login(UserFactory())
    html = client.get("/").content.decode()

    assert "Open source libraries" in html
    assert "https://github.com/django/django" in html
    assert "https://github.com/twbs/bootstrap" in html
    # Rendered as "owner / library • version".
    assert ">twbs&nbsp;/</span> Bootstrap" in html
    assert "&bull; 5.3.8" in html
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

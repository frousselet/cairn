# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The front-end mirror : what guarantees an instance loads its libraries offline.

Nothing here reaches the network. The download is stubbed and the mirror points
at a temporary directory, so the tests exercise the machinery - integrity
checks, atomic writes, what counts as missing, when a start-up fetch fires - and
never the CDN.
"""
import pathlib

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from core import vendoring
from core.apps import _is_serving
from core.dependencies import VendorAsset

BODY = b"/* a library */"
DIGEST = vendoring.digest(BODY)


@pytest.fixture
def mirror(tmp_path, monkeypatch):
    """A ``static/vendor/`` of our own, holding two declared assets."""
    root = tmp_path / "vendor"
    monkeypatch.setattr(vendoring, "vendor_root", lambda: root)
    assets = [
        VendorAsset("https://example.test/lib.js", "lib/lib.js", DIGEST),
        VendorAsset("https://example.test/lib.css", "lib/lib.css", DIGEST),
    ]
    monkeypatch.setattr(vendoring, "vendor_assets", lambda: assets)
    return root, assets


def _serve(monkeypatch, body=BODY):
    """Answer every download with ``body``, without touching the network."""
    monkeypatch.setattr(vendoring, "fetch", lambda asset: body)


# ── Integrity ──────────────────────────────────────────────────────────


def test_a_payload_that_does_not_match_its_digest_is_refused(monkeypatch):
    """A tampered or truncated mirror must never reach a browser."""
    asset = VendorAsset("https://example.test/lib.js", "lib/lib.js", DIGEST)

    class _Response:
        def read(self):
            return b"/* something else */"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(vendoring.urllib.request, "urlopen", lambda *a, **k: _Response())

    with pytest.raises(vendoring.VendorAssetError, match="integrity check failed"):
        vendoring.fetch(asset)


def test_a_network_failure_is_reported_as_a_vendor_error(monkeypatch):
    asset = VendorAsset("https://example.test/lib.js", "lib/lib.js", DIGEST)

    def _boom(*args, **kwargs):
        raise OSError("no route to host")

    monkeypatch.setattr(vendoring.urllib.request, "urlopen", _boom)

    with pytest.raises(vendoring.VendorAssetError, match="cannot fetch"):
        vendoring.fetch(asset)


# ── Storing ────────────────────────────────────────────────────────────


def test_storing_creates_the_directory_layout_the_library_expects(mirror):
    """Bootstrap Icons and Leaflet reference their fonts and sprites by a
    relative path, so the sub-directories have to be recreated verbatim."""
    root, (asset, _) = mirror

    path = vendoring.store(asset, BODY)

    assert path == root / "lib/lib.js"
    assert path.read_bytes() == BODY


def test_storing_leaves_no_partial_file_behind(mirror):
    root, (asset, _) = mirror

    vendoring.store(asset, BODY)

    assert [p.name for p in (root / "lib").iterdir()] == ["lib.js"]


# ── What counts as missing ─────────────────────────────────────────────


def test_everything_is_missing_before_the_first_download(mirror):
    _root, assets = mirror

    assert vendoring.missing_assets() == assets


def test_a_stored_file_stops_being_missing(mirror):
    _root, (asset, other) = mirror

    vendoring.store(asset, BODY)

    assert vendoring.missing_assets() == [other]


def test_a_truncated_file_is_treated_as_missing(mirror):
    """A download killed mid-write leaves a zero-byte file : re-fetch it rather
    than serve an empty stylesheet."""
    root, (asset, _other) = mirror
    path = root / asset.path
    path.parent.mkdir(parents=True)
    path.write_bytes(b"")

    assert asset in vendoring.missing_assets()


def test_a_file_whose_content_drifted_is_reported_as_corrupt(mirror):
    _root, (asset, _other) = mirror
    vendoring.store(asset, b"/* not what was pinned */")

    assert vendoring.corrupt_assets() == [asset]


# ── First launch ───────────────────────────────────────────────────────


def test_the_first_launch_fetches_what_is_missing(mirror, monkeypatch):
    _root, assets = mirror
    _serve(monkeypatch)

    assert vendoring.ensure_present() == len(assets)
    assert vendoring.missing_assets() == []


def test_a_later_launch_downloads_nothing(mirror, monkeypatch):
    _root, _assets = mirror
    _serve(monkeypatch)
    vendoring.ensure_present()

    def _never(asset):
        raise AssertionError("a start with the mirror in place must not download")

    monkeypatch.setattr(vendoring, "fetch", _never)

    assert vendoring.ensure_present() == 0


def test_an_unreachable_mirror_does_not_stop_the_instance_from_booting(mirror, monkeypatch):
    """The interface degrades; the application still starts, so the operator can
    read the message and run the command once connected."""
    _root, _assets = mirror

    def _boom(asset):
        raise vendoring.VendorAssetError("cannot fetch")

    monkeypatch.setattr(vendoring, "fetch", _boom)
    said = []

    assert vendoring.ensure_present(log=said.append) == 0
    assert any("vendor_assets" in message for message in said)


# ── Which processes fetch on start-up ──────────────────────────────────


@pytest.mark.parametrize("argv", [
    ["manage.py", "runserver"],
    ["manage.py", "collectstatic", "--noinput"],
    ["/usr/local/bin/uvicorn", "core.asgi:application"],
    ["/usr/local/bin/gunicorn", "core.wsgi"],
])
def test_a_process_that_serves_the_interface_fetches_on_start(argv):
    assert _is_serving(argv) is True


@pytest.mark.parametrize("argv", [
    ["manage.py", "migrate"],
    ["manage.py", "shell"],
    ["manage.py", "vendor_assets"],  # the command downloads on its own terms
    ["/usr/bin/pytest", "-q"],
    [],
])
def test_a_process_that_does_not_serve_stays_offline(argv):
    assert _is_serving(argv) is False


# ── The management command ─────────────────────────────────────────────


def test_the_command_is_idempotent(mirror, monkeypatch, capsys):
    _root, assets = mirror
    _serve(monkeypatch)

    call_command("vendor_assets")
    monkeypatch.setattr(vendoring, "fetch", lambda a: pytest.fail("re-downloaded"))
    call_command("vendor_assets")

    assert "already mirrored" in capsys.readouterr().out


def test_force_re_downloads_everything(mirror, monkeypatch):
    _root, assets = mirror
    _serve(monkeypatch)
    call_command("vendor_assets")

    fetched = []
    monkeypatch.setattr(vendoring, "fetch", lambda a: fetched.append(a) or BODY)
    call_command("vendor_assets", force=True)

    assert fetched == assets


def test_check_fails_when_the_mirror_is_incomplete(mirror):
    with pytest.raises(CommandError, match="missing or corrupt"):
        call_command("vendor_assets", check=True)


def test_check_passes_on_a_complete_mirror(mirror, monkeypatch):
    _serve(monkeypatch)
    call_command("vendor_assets")

    call_command("vendor_assets", check=True)  # does not raise


# ── The shipped declaration ────────────────────────────────────────────


def test_the_repository_carries_no_copy_of_the_libraries():
    """``static/vendor/`` is generated, never committed : a stale copy in git
    would silently outrank the pins in the registry."""
    import subprocess

    repo = pathlib.Path(__file__).resolve().parents[2]
    tracked = subprocess.run(
        ["git", "ls-files", "static/vendor"],
        cwd=repo, capture_output=True, text=True, check=False,
    ).stdout.strip()

    assert tracked == "", f"remove these from git : {tracked}"

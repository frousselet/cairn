# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Mirroring of the front-end libraries into ``static/vendor/``.

Cairn serves every JavaScript, CSS and font file from its own origin : an
instance on an isolated network works, no third party learns who browses it,
and the interface cannot break because a CDN did. Nothing here is committed to
the repository - the files are fetched from the pins in ``core.dependencies``:

* **Docker** : ``manage.py vendor_assets`` runs during the image build, so the
  published image already carries them and the container needs no network.
* **Direct Python** : the first launch fetches whatever is missing (see
  ``ensure_present``), then every later start finds the files in place.

Downloads are verified against the Subresource-Integrity digest declared with
each asset, so a tampered or truncated mirror is refused rather than served.
"""
import base64
import hashlib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.conf import settings

from core.dependencies import vendor_assets

#: Long enough for the largest asset (~1 MB of ECharts) on a slow link.
DOWNLOAD_TIMEOUT = 60

#: jsDelivr answers 403 to a request with no User-Agent.
USER_AGENT = "cairn-vendor-assets"

#: Parallel downloads. The mirror is a CDN : a handful of connections is plenty.
MAX_WORKERS = 8


class VendorAssetError(RuntimeError):
    """A library file could not be fetched, or did not match its digest."""


def vendor_root() -> Path:
    """Where the mirrored files live : ``static/vendor/``, inside the source tree
    so ``collectstatic`` picks them up like any other static file."""
    return Path(settings.BASE_DIR) / "static" / "vendor"


def destination(asset) -> Path:
    return vendor_root() / asset.path


def digest(body: bytes) -> str:
    """The Subresource-Integrity digest of a payload, in the ``sha384-…`` form."""
    return "sha384-" + base64.b64encode(hashlib.sha384(body).digest()).decode()


def missing_assets():
    """The declared assets that are not on disk yet. Cheap : one stat per file,
    so it can run on every application start."""
    return [a for a in vendor_assets() if not _present(destination(a))]


def corrupt_assets():
    """The assets on disk whose content does not match the declared digest.
    Reads every file, so this is for ``--check``, not for the start-up path."""
    corrupt = []
    for asset in vendor_assets():
        path = destination(asset)
        if _present(path) and digest(path.read_bytes()) != asset.sha384:
            corrupt.append(asset)
    return corrupt


def _present(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def fetch(asset) -> bytes:
    """Download one asset and check its digest. Raises ``VendorAssetError``."""
    request = urllib.request.Request(asset.url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            body = response.read()
    except (urllib.error.URLError, OSError) as exc:  # network, DNS, TLS, timeout
        raise VendorAssetError(f"{asset.path} : cannot fetch {asset.url} ({exc})") from exc

    got = digest(body)
    if got != asset.sha384:
        raise VendorAssetError(
            f"{asset.path} : integrity check failed for {asset.url}\n"
            f"  expected {asset.sha384}\n  got      {got}"
        )
    return body


def store(asset, body: bytes) -> Path:
    """Write an asset to its place under ``static/vendor/``.

    The write goes through a temporary file in the same directory and is then
    renamed : a reader (the web server serving static files, a parallel
    ``collectstatic``) never sees a half-written library.
    """
    path = destination(asset)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_bytes(body)
    temporary.replace(path)
    return path


def sync(assets, on_done=None):
    """Fetch and store every asset in ``assets``, a few at a time.

    ``on_done`` is called with each asset as it lands, for progress output. The
    first failure aborts and propagates : a half-mirrored set would leave the
    interface subtly broken, which is worse than a loud error.
    """
    assets = list(assets)
    if not assets:
        return []

    def one(asset):
        stored = store(asset, fetch(asset))
        if on_done:
            on_done(asset)
        return stored

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        return list(pool.map(one, assets))


def ensure_present(log=None) -> int:
    """Mirror whatever is missing, and report how many files were fetched.

    Called on the first launch of a direct (non-Docker) install, where nothing
    has run the management command. A failure is reported but never fatal : an
    instance that cannot reach the mirror must still boot, so the operator can
    read the message and run ``manage.py vendor_assets`` once connected.
    """
    missing = missing_assets()
    if not missing:
        return 0

    def say(message):
        if log:
            log(message)

    say(f"Front-end libraries : downloading {len(missing)} missing file(s) into static/vendor/…")
    try:
        sync(missing)
    except VendorAssetError as exc:
        say(
            f"Front-end libraries : {exc}\n"
            "The interface will render unstyled until this is resolved. "
            "Run `python manage.py vendor_assets` once the mirror is reachable."
        )
        return 0
    say(f"Front-end libraries : {len(missing)} file(s) ready.")
    return len(missing)

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Mirror the front-end libraries declared in ``core.dependencies`` locally.

Run without arguments it is idempotent : it downloads only what is missing, so
it is safe in an image build, in an entrypoint and by hand.
"""
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand, CommandError

from core import vendoring
from core.dependencies import DEPENDENCIES, FRONTEND
from core.vendoring import VendorAssetError


class Command(BaseCommand):
    help = (
        "Download the front-end libraries into static/vendor/ so the instance "
        "serves them from its own origin instead of a CDN."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-download every file, even the ones already present (after a version bump).",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Verify that every file is present and matches its digest, and download nothing. "
                 "Exits non-zero otherwise.",
        )
        parser.add_argument(
            "--print-hashes",
            action="store_true",
            help="Fetch the declared URLs and print their sha384 digests, to paste into "
                 "core/dependencies.py when a library is upgraded.",
        )

    def handle(self, *args, **options):
        if options["print_hashes"]:
            return self._print_hashes()
        if options["check"]:
            return self._check()

        declared = vendoring.vendor_assets()
        assets = declared if options["force"] else vendoring.missing_assets()
        if not assets:
            self.stdout.write(self.style.SUCCESS(
                f"Front-end libraries already mirrored in {vendoring.vendor_root()} "
                f"({len(declared)} files)."
            ))
            return

        self.stdout.write(f"Downloading {len(assets)} file(s) into {vendoring.vendor_root()}…")
        try:
            vendoring.sync(assets, on_done=lambda a: self.stdout.write(f"  {a.path}"))
        except VendorAssetError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"{len(assets)} file(s) mirrored."))

    def _check(self):
        missing = vendoring.missing_assets()
        corrupt = vendoring.corrupt_assets()
        for asset in missing:
            self.stderr.write(self.style.ERROR(f"missing  {asset.path}"))
        for asset in corrupt:
            self.stderr.write(self.style.ERROR(f"corrupt  {asset.path}"))
        if missing or corrupt:
            raise CommandError(
                f"{len(missing) + len(corrupt)} front-end file(s) missing or corrupt. "
                "Run `python manage.py vendor_assets --force`."
            )
        self.stdout.write(self.style.SUCCESS(
            f"All {len(vendoring.vendor_assets())} front-end files present and verified."
        ))

    def _print_hashes(self):
        """Fetch each declared URL and print its digest, whatever the pin says.

        This is the one path that must not verify : it exists precisely to
        produce the digests of a version that has just been bumped.
        """
        for dep in DEPENDENCIES:
            if dep.group != FRONTEND or not dep.assets:
                continue
            self.stdout.write(f"{dep.name} {dep.pinned_version}")
            for asset in dep.assets:
                try:
                    body = _fetch_unverified(asset)
                except VendorAssetError as exc:
                    self.stderr.write(self.style.ERROR(f"  {exc}"))
                    continue
                self.stdout.write(f'  {asset.path}\n    "{vendoring.digest(body)}"')


def _fetch_unverified(asset):
    """``core.vendoring.fetch`` without the digest comparison : this path exists
    to produce a digest, so it cannot require one."""
    request = urllib.request.Request(asset.url, headers={"User-Agent": vendoring.USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=vendoring.DOWNLOAD_TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, OSError) as exc:
        raise VendorAssetError(f"{asset.path} : cannot fetch {asset.url} ({exc})") from exc

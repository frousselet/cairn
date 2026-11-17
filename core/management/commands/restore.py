# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""``manage.py restore`` : put the instance back in the state of an archive."""

import tarfile
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections

from core import backup


class Command(BaseCommand):
    help = (
        "Replace the database and the media directory with the content of an archive made by "
        "`manage.py backup`. Every checksum is verified first, and a safety backup of the "
        "current state is taken before anything is replaced."
    )

    def add_arguments(self, parser):
        parser.add_argument("archive", help="Path of the archive to restore.")
        parser.add_argument(
            "--check", action="store_true",
            help="Verify the archive and say whether it can be restored here, without changing anything.",
        )
        parser.add_argument(
            "--yes", action="store_true",
            help="Do not ask for confirmation (for a scripted restore).",
        )
        parser.add_argument(
            "--no-safety-backup", action="store_true",
            help="Skip the backup of the current state taken before the restore (an empty instance has nothing to save).",
        )

    def handle(self, *args, **options):
        archive = Path(options["archive"])
        database = settings.DATABASES["default"]
        try:
            manifest = backup.verify_archive(archive)
            pending = backup.check_compatible(manifest, database)
        except backup.BackupError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            f"{archive.name} : made {manifest['created_at']} by Cairn "
            f"{manifest.get('app_version') or 'unknown'}, {manifest['database']['engine']} "
            f"{manifest['database']['server_version']}, {manifest['media_files']} media file(s). "
            "Every checksum matches."
        )
        if options["check"]:
            self.stdout.write(self.style.SUCCESS("This archive can be restored on this instance."))
            self._report_pending(pending)
            return

        if not options["yes"]:
            self.stdout.write(self.style.WARNING(
                f"This replaces the database `{database['NAME']}` and every file under "
                f"{settings.MEDIA_ROOT} with the content of the archive."
            ))
            if input("Type 'restore' to go on : ").strip() != "restore":
                raise CommandError("Restore cancelled.")

        try:
            if not options["no_safety_backup"]:
                safety = backup.create_backup(
                    archive.resolve().parent,
                    database=database,
                    media_root=settings.MEDIA_ROOT,
                    connection=connection,
                    app_version=settings.APP_VERSION,
                    prefix=backup.SAFETY_PREFIX,
                )
                self.stdout.write(f"Current state saved to {safety}")

            # No connection of this process may hold the tables being replaced.
            connections.close_all()
            with tempfile.TemporaryDirectory(prefix="cairn-restore-") as scratch:
                member = manifest["database"]["member"]
                with tarfile.open(archive, mode="r") as tar:
                    tar.extract(member, path=scratch, filter="data")
                backup.load_database(database, Path(scratch) / member)
            self.stdout.write("Database restored.")
            count = backup.restore_media(archive, settings.MEDIA_ROOT)
            self.stdout.write(f"Media restored ({count} file(s)).")
        except backup.BackupError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(self.style.SUCCESS("Restore complete."))
        self._report_pending(pending)

    def _report_pending(self, pending):
        if pending:
            self.stdout.write(self.style.WARNING(
                f"The archive is {len(pending)} migration(s) behind this release : "
                "run `python manage.py migrate` after the restore."
            ))

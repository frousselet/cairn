# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""``manage.py backup`` : the database and the media directory, as one archive."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from core import backup


class Command(BaseCommand):
    help = (
        "Write one archive holding the database and the media directory, with a manifest "
        "and a checksum for every file. Restore it with `manage.py restore`."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", default=None,
            help="Directory the archive is written to (default : the BACKUP_DIR setting).",
        )
        parser.add_argument(
            "--keep", type=int, default=None, metavar="N",
            help="After a successful backup, delete all but the N most recent archives of the directory.",
        )

    def handle(self, *args, **options):
        output = options["output"] or settings.BACKUP_DIR
        try:
            archive = backup.create_backup(
                output,
                database=settings.DATABASES["default"],
                media_root=settings.MEDIA_ROOT,
                connection=connection,
                app_version=settings.APP_VERSION,
            )
            # Read back what was just written : a backup that cannot be
            # verified is reported now, not on the day it is needed.
            manifest = backup.verify_archive(archive)
            removed = backup.prune(output, options["keep"]) if options["keep"] is not None else []
        except backup.BackupError as error:
            raise CommandError(str(error)) from error

        size = archive.stat().st_size
        self.stdout.write(self.style.SUCCESS(f"Backup written : {archive}"))
        self.stdout.write(
            f"  {manifest['database']['engine']} {manifest['database']['server_version']}, "
            f"{manifest['media_files']} media file(s), {size / 1_048_576:.1f} MB, verified."
        )
        for path in removed:
            self.stdout.write(f"  removed {path.name}")

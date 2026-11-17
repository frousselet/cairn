# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Backup and restore (``core/backup.py``, ``manage.py backup`` / ``restore``).

An untested backup is a hypothesis. The archive logic is exercised on scratch
databases and directories; the commands are exercised end to end, as a
deployment runs them, on a throwaway instance : back up, damage the instance,
restore, and find it as it was. The PostgreSQL mechanics (``pg_dump``, the
single-transaction reload) run in the PostgreSQL job of the CI.
"""

import json
import os
import sqlite3
import subprocess
import sys
import tarfile
from datetime import UTC, datetime

import pytest
from django.conf import settings

from core import backup

SQLITE = "django.db.backends.sqlite3"


def _database(path, rows=("alpha", "beta")):
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE record (name TEXT)")
    connection.executemany("INSERT INTO record VALUES (?)", [(row,) for row in rows])
    connection.commit()
    connection.close()
    return {"ENGINE": SQLITE, "NAME": str(path)}


def _rows(path):
    connection = sqlite3.connect(path)
    try:
        return [row[0] for row in connection.execute("SELECT name FROM record ORDER BY name")]
    finally:
        connection.close()


def _media(root, files):
    for name, content in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return root


def _listing(root):
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


@pytest.fixture
def instance(tmp_path):
    database = _database(tmp_path / "db.sqlite3")
    media = _media(tmp_path / "media", {"evidence/log.txt": b"first capture", "logo.png": b"\x89PNG"})
    return database, media, tmp_path / "backups"


def _backup(instance, **kwargs):
    database, media, output = instance
    return backup.create_backup(output, database=database, media_root=media, app_version="1.2.3", **kwargs)


class TestArchive:
    def test_it_holds_the_database_the_media_and_a_manifest(self, instance):
        archive = _backup(instance)
        assert archive.name.startswith("cairn-backup-") and archive.suffix == ".tar"
        with tarfile.open(archive) as tar:
            names = set(tar.getnames())
        assert names == {"manifest.json", "database.sqlite3", "media/evidence/log.txt", "media/logo.png"}
        manifest = backup.read_manifest(archive)
        assert manifest["format"] == backup.FORMAT
        assert manifest["app_version"] == "1.2.3"
        assert manifest["database"]["engine"] == "sqlite"
        assert manifest["media_files"] == 2
        assert set(manifest["members"]) == names - {"manifest.json"}

    def test_it_is_readable_by_its_owner_only(self, instance):
        """It holds password hashes, sessions and every record."""
        archive = _backup(instance)
        assert archive.stat().st_mode & 0o777 == 0o600

    def test_no_partial_file_is_left_behind(self, instance):
        _backup(instance)
        assert not list(instance[2].glob("*.partial"))
        assert [path for path in instance[2].iterdir() if path.is_dir()] == []

    def test_a_failed_backup_leaves_no_archive(self, tmp_path):
        missing = {"ENGINE": SQLITE, "NAME": str(tmp_path / "absent.sqlite3")}
        with pytest.raises(backup.BackupError, match="does not exist"):
            backup.create_backup(tmp_path / "out", database=missing, media_root=tmp_path / "media")
        assert list((tmp_path / "out").iterdir()) == []

    def test_an_in_memory_database_is_refused(self, tmp_path):
        with pytest.raises(backup.BackupError, match="in-memory"):
            backup.dump_database({"ENGINE": SQLITE, "NAME": ":memory:"}, tmp_path / "x")

    def test_an_unknown_engine_is_refused(self):
        with pytest.raises(backup.BackupError, match="Unsupported"):
            backup.engine_of({"ENGINE": "django.db.backends.oracle"})


class TestVerification:
    def test_a_sound_archive_verifies(self, instance):
        assert backup.verify_archive(_backup(instance))["media_files"] == 2

    def _rewrite(self, archive, tmp_path, mutate):
        """Rebuild the archive with ``mutate(name, data)`` applied to each member."""
        scratch = tmp_path / "rewritten.tar"
        with tarfile.open(archive) as source, tarfile.open(scratch, "w") as target:
            for member in source:
                data = source.extractfile(member).read()
                result = mutate(member.name, data)
                if result is None:
                    continue
                name, data = result
                info = tarfile.TarInfo(name)
                info.size = len(data)
                import io
                target.addfile(info, io.BytesIO(data))
        return scratch

    def test_a_damaged_file_is_detected(self, instance, tmp_path):
        archive = self._rewrite(
            _backup(instance), tmp_path,
            lambda name, data: (name, b"tampered data" if name == "media/evidence/log.txt" else data),
        )
        with pytest.raises(backup.BackupError, match="damaged"):
            backup.verify_archive(archive)

    def test_a_missing_file_is_detected(self, instance, tmp_path):
        archive = self._rewrite(
            _backup(instance), tmp_path,
            lambda name, data: None if name == "media/logo.png" else (name, data),
        )
        with pytest.raises(backup.BackupError, match="missing"):
            backup.verify_archive(archive)

    def test_a_file_the_manifest_does_not_list_is_refused(self, instance, tmp_path):
        archive = _backup(instance)
        with tarfile.open(archive, "a") as tar:
            extra = tmp_path / "extra.txt"
            extra.write_text("smuggled")
            tar.add(extra, arcname="media/extra.txt")
        with pytest.raises(backup.BackupError, match="not listed"):
            backup.verify_archive(archive)

    def test_a_file_that_is_not_a_backup_is_refused(self, tmp_path):
        plain = tmp_path / "notes.tar"
        with tarfile.open(plain, "w") as tar:
            source = tmp_path / "notes.txt"
            source.write_text("hello")
            tar.add(source, arcname="notes.txt")
        with pytest.raises(backup.BackupError, match="not a Cairn backup"):
            backup.verify_archive(plain)
        garbage = tmp_path / "garbage.tar"
        garbage.write_bytes(b"not a tar at all")
        with pytest.raises(backup.BackupError, match="not a readable archive"):
            backup.verify_archive(garbage)

    def test_another_format_version_is_refused(self, instance, tmp_path):
        def bump(name, data):
            if name == "manifest.json":
                manifest = json.loads(data)
                manifest["format"] = 99
                data = json.dumps(manifest).encode()
            return name, data

        with pytest.raises(backup.BackupError, match="format 99"):
            backup.verify_archive(self._rewrite(_backup(instance), tmp_path, bump))

    def test_a_path_leaving_the_archive_is_refused(self):
        assert backup._safe_member("evidence/log.txt")
        assert not backup._safe_member("../../etc/passwd")
        assert not backup._safe_member("/etc/passwd")
        assert not backup._safe_member("a/../../b")


class TestRestore:
    def test_the_database_comes_back_as_it_was(self, instance, tmp_path):
        database, _media_root, _output = instance
        archive = _backup(instance)
        connection = sqlite3.connect(database["NAME"])
        connection.execute("DELETE FROM record")
        connection.execute("CREATE TABLE added_since (x INTEGER)")
        connection.commit()
        connection.close()
        with tarfile.open(archive) as tar:
            tar.extract("database.sqlite3", path=tmp_path / "x", filter="data")
        backup.load_database(database, tmp_path / "x" / "database.sqlite3")
        assert _rows(database["NAME"]) == ["alpha", "beta"]
        connection = sqlite3.connect(database["NAME"])
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        connection.close()
        # Exactly the archive : a table created since the backup is gone.
        assert tables == {"record"}

    def test_the_media_comes_back_as_it_was(self, instance):
        _database_, media, _output = instance
        before = _listing(media)
        archive = _backup(instance)
        (media / "evidence" / "log.txt").write_bytes(b"overwritten")
        (media / "logo.png").unlink()
        _media(media, {"added/since.txt": b"not in the backup"})
        assert backup.restore_media(archive, media) == 2
        assert _listing(media) == before
        assert not [path for path in media.iterdir() if path.name.startswith(".restore-")]

    def test_an_interrupted_restore_is_not_backed_up_as_media(self, instance):
        _database_, media, _output = instance
        _media(media, {".restore-abc/half.txt": b"left by a crash"})
        manifest = backup.read_manifest(_backup(instance))
        assert not [name for name in manifest["members"] if ".restore-" in name]


class TestCompatibility:
    def _manifest(self, engine="sqlite", migrations=()):
        return {"database": {"engine": engine}, "migrations": [list(m) for m in migrations], "app_version": "9.9.9"}

    def test_another_engine_is_refused(self):
        with pytest.raises(backup.BackupError, match="postgresql database; this instance runs on sqlite"):
            backup.check_compatible(self._manifest("postgresql"), {"ENGINE": SQLITE})

    def test_an_archive_from_a_newer_release_is_refused(self):
        """Its schema has columns this code does not know : loading it would
        leave an instance that fails in ways nobody can read."""
        known = sorted(backup.known_migrations())[:3]
        future = [*known, ("accounts", "9999_from_the_future")]
        with pytest.raises(backup.BackupError, match="newer release"):
            backup.check_compatible(self._manifest(migrations=future), {"ENGINE": SQLITE})

    def test_an_older_archive_reports_what_is_left_to_migrate(self):
        known = sorted(backup.known_migrations())
        pending = backup.check_compatible(self._manifest(migrations=known[:-2]), {"ENGINE": SQLITE})
        assert pending == known[-2:]

    def test_a_current_archive_has_nothing_pending(self):
        known = sorted(backup.known_migrations())
        assert backup.check_compatible(self._manifest(migrations=known), {"ENGINE": SQLITE}) == []


class TestRotation:
    def test_it_keeps_the_most_recent(self, instance):
        made = [
            _backup(instance, now=datetime(2026, 11, day, 3, 0, tzinfo=UTC))
            for day in (1, 2, 3, 4, 5)
        ]
        removed = backup.prune(instance[2], keep=2)
        assert sorted(path.name for path in removed) == sorted(path.name for path in made[:3])
        assert sorted(path.name for path in instance[2].glob("*.tar")) == sorted(path.name for path in made[3:])

    def test_a_safety_backup_is_not_rotated_away(self, instance):
        safety = _backup(instance, prefix=backup.SAFETY_PREFIX, now=datetime(2026, 1, 1, tzinfo=UTC))
        _backup(instance, now=datetime(2026, 11, 1, tzinfo=UTC))
        _backup(instance, now=datetime(2026, 11, 2, tzinfo=UTC))
        backup.prune(instance[2], keep=1)
        assert safety.exists()

    def test_keeping_nothing_is_refused(self, instance):
        with pytest.raises(backup.BackupError, match="at least 1"):
            backup.prune(instance[2], keep=0)


def test_the_client_tools_follow_the_server_everywhere():
    """pg_dump and pg_restore must be of the server's major (see
    ``_require_matching_tools``) : the image, the compose file and the CI job
    name the same one, so moving the server moves the tools with it."""
    import re

    root = settings.BASE_DIR
    image = re.search(r"^ARG POSTGRES_MAJOR=(\d+)$", (root / "Dockerfile").read_text(), re.M).group(1)
    compose = re.search(r"image: postgres:(\d+)", (root / "docker-compose.yml").read_text()).group(1)
    workflow = (root / ".github" / "workflows" / "tests.yml").read_text()
    service = re.search(r"image: postgres:(\d+)", workflow).group(1)
    client = re.search(r"postgresql-client-(\d+)", workflow).group(1)
    assert image == compose == service == client
    assert f"/usr/lib/postgresql/{client}/bin" in workflow
    assert 'REQUIRE_BACKUP_TOOLS: "1"' in workflow


def _manage(env, *arguments, stdin=None):
    return subprocess.run(  # noqa: S603 - the project's own manage.py
        [sys.executable, "manage.py", *arguments],
        cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, input=stdin, check=False,
    )


def _shell(env, code):
    result = _manage(env, "shell", "-c", code)
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout.strip().splitlines()[-1]


@pytest.mark.sweep
def test_an_instance_is_restored_from_its_backup_end_to_end(tmp_path):
    """The commands, as a deployment runs them : a real instance with a
    record and an uploaded file is backed up, damaged, then restored."""
    media = tmp_path / "media"
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "core.settings_local",
        "SQLITE_PATH": str(tmp_path / "instance.sqlite3"),
        "SCHEMA_FROM_MODELS": "1",
        "BACKUP_DIR": str(tmp_path / "backups"),
        "MEDIA_ROOT": str(media),
    }
    assert _manage(env, "migrate", "--run-syncdb", "--noinput").returncode == 0
    _shell(env, (
        "from accounts.models import User; from django.conf import settings; import pathlib;"
        "User.objects.create_user(email='keeper@example.com', password='x', first_name='K', last_name='P');"
        "p = pathlib.Path(settings.MEDIA_ROOT) / 'evidence' / 'capture.txt';"
        "p.parent.mkdir(parents=True, exist_ok=True); p.write_text('the original evidence'); print('ok')"
    ))

    made = _manage(env, "backup")
    assert made.returncode == 0, made.stderr[-2000:]
    assert "verified" in made.stdout
    archives = sorted((tmp_path / "backups").glob("cairn-backup-*.tar"))
    assert len(archives) == 1

    # Damage : the user is deleted, the evidence overwritten, a file added.
    _shell(env, (
        "from accounts.models import User; from django.conf import settings; import pathlib;"
        "User.objects.filter(email='keeper@example.com').delete();"
        "User.objects.create_user(email='intruder@example.com', password='x', first_name='I', last_name='N');"
        "root = pathlib.Path(settings.MEDIA_ROOT);"
        "(root / 'evidence' / 'capture.txt').write_text('tampered');"
        "(root / 'planted.txt').write_text('x'); print('ok')"
    ))

    checked = _manage(env, "restore", str(archives[0]), "--check")
    assert checked.returncode == 0 and "can be restored" in checked.stdout
    assert _shell(env, "from accounts.models import User; print(User.objects.filter(email='intruder@example.com').count())") == "1"

    refused = _manage(env, "restore", str(archives[0]), stdin="no\n")
    assert refused.returncode != 0 and "cancelled" in refused.stderr

    restored = _manage(env, "restore", str(archives[0]), "--yes")
    assert restored.returncode == 0, restored.stderr[-2000:]
    assert "Restore complete" in restored.stdout

    emails = _shell(env, "from accounts.models import User; print(sorted(User.objects.values_list('email', flat=True)))")
    assert emails == "['keeper@example.com']"
    assert (media / "evidence" / "capture.txt").read_text() == "the original evidence"
    assert not (media / "planted.txt").exists()
    # What the restore replaced was saved first, and holds the damaged state.
    safety = sorted((tmp_path / "backups").glob("cairn-before-restore-*.tar"))
    assert len(safety) == 1
    assert "media/planted.txt" in backup.verify_archive(safety[0])["members"]

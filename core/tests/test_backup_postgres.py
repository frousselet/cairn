# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Backup and restore on PostgreSQL : ``pg_dump``, and the load into a new
database that then takes the place of the current one.

Runs with the PostgreSQL settings (``pytest --ds=core.settings_test_postgres``)
where the client tools of the server's version are installed : the CI job and
the application image. Each test works on a scratch database of its own, never
on the one the suite uses.
"""

import os
import shutil
import uuid

import pytest
from django.conf import settings

from core import backup

IS_POSTGRES = settings.DATABASES["default"]["ENGINE"].endswith("postgresql")
HAS_TOOLS = all(shutil.which(tool) for tool in ("pg_dump", "pg_restore", "psql"))
# The CI job installs the tools and sets this, so that a missing tool fails
# the job instead of quietly skipping the only test of the production path.
REQUIRED = os.environ.get("REQUIRE_BACKUP_TOOLS") == "1"

pytestmark = [
    pytest.mark.skipif(not IS_POSTGRES, reason="PostgreSQL settings only"),
    pytest.mark.skipif(IS_POSTGRES and not HAS_TOOLS and not REQUIRED, reason="PostgreSQL client tools not installed"),
]


def _execute(database, *statements, fetch=False):
    import psycopg

    with psycopg.connect(
        dbname=database["NAME"], user=database["USER"], password=database["PASSWORD"],
        host=database["HOST"], port=database["PORT"], autocommit=True,
    ) as connection:
        result = None
        for statement in statements:
            cursor = connection.execute(statement)
            if fetch:
                result = cursor.fetchall()
        return result


@pytest.fixture
def scratch():
    """A database created for one test, with a table, a sequence and binary data."""
    server = dict(settings.DATABASES["default"])
    name = f"cairn_backup_{uuid.uuid4().hex[:12]}"
    maintenance = {**server, "NAME": "postgres"}
    _execute(maintenance, f'CREATE DATABASE "{name}"')
    database = {**server, "NAME": name}
    _execute(
        database,
        "CREATE TABLE record (id serial PRIMARY KEY, name text NOT NULL, payload bytea)",
        "INSERT INTO record (name, payload) VALUES ('alpha', '\\x00ff10'), ('beta', NULL)",
        "CREATE TABLE child (id serial PRIMARY KEY, record_id integer REFERENCES record(id))",
        "INSERT INTO child (record_id) VALUES (1)",
    )
    try:
        yield database
    finally:
        _execute(maintenance, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def _state(database):
    return {
        "records": _execute(database, "SELECT id, name, payload FROM record ORDER BY id", fetch=True),
        "children": _execute(database, "SELECT id, record_id FROM child ORDER BY id", fetch=True),
        "tables": _execute(
            database,
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename", fetch=True,
        ),
    }


def test_the_tools_are_there_when_the_job_requires_them():
    assert HAS_TOOLS, "pg_dump / pg_restore / psql are missing where REQUIRE_BACKUP_TOOLS=1"


def test_a_database_is_restored_exactly(scratch, tmp_path):
    before = _state(scratch)
    dump = tmp_path / "database.pgdump"
    info = backup.dump_database(scratch, dump)
    assert info["engine"] == "postgresql" and dump.stat().st_size > 0

    _execute(
        scratch,
        "DELETE FROM child",
        "UPDATE record SET name = 'tampered' WHERE id = 1",
        "INSERT INTO record (name) VALUES ('added since')",
        "CREATE TABLE added_since (x integer)",
        "ALTER TABLE record ADD COLUMN extra text",
    )
    assert _state(scratch) != before

    backup.load_database(scratch, dump)
    # The dump and nothing else : the rows, the column and the table added
    # since are gone, the binary value and the foreign key are back.
    assert _state(scratch) == before
    columns = _execute(
        scratch, "SELECT column_name FROM information_schema.columns WHERE table_name = 'record' ORDER BY 1", fetch=True,
    )
    assert [row[0] for row in columns] == ["id", "name", "payload"]
    # The sequence continues where the dump left it.
    _execute(scratch, "INSERT INTO record (name) VALUES ('after restore')")
    assert _execute(scratch, "SELECT max(id) FROM record", fetch=True) == [(3,)]
    assert _leftovers(scratch) == []


def test_a_restore_can_be_repeated(scratch, tmp_path):
    """A dump taken from a restored database restores as well as the first one."""
    first = tmp_path / "first.pgdump"
    backup.dump_database(scratch, first)
    backup.load_database(scratch, first)
    second = tmp_path / "second.pgdump"
    backup.dump_database(scratch, second)
    before = _state(scratch)
    _execute(scratch, "DELETE FROM child", "DELETE FROM record")
    backup.load_database(scratch, second)
    assert _state(scratch) == before


def _leftovers(scratch):
    rows = _execute(
        {**scratch, "NAME": "postgres"},
        f"SELECT datname FROM pg_database WHERE datname LIKE '{scratch['NAME']}\\_re%'", fetch=True,
    )
    return [row[0] for row in rows]


def test_a_failed_reload_leaves_the_database_as_it_was(scratch, tmp_path):
    """The dump is loaded beside the live database : one that cannot be loaded
    to the end costs the scratch database, never the current one."""
    dump = tmp_path / "database.pgdump"
    backup.dump_database(scratch, dump)
    truncated = tmp_path / "truncated.pgdump"
    truncated.write_bytes(dump.read_bytes()[: dump.stat().st_size // 2])
    _execute(scratch, "INSERT INTO record (name) VALUES ('written after the backup')")
    before = _state(scratch)
    with pytest.raises(backup.BackupError, match="pg_restore"):
        backup.load_database(scratch, truncated)
    assert _state(scratch) == before
    assert len(before["records"]) == 3
    assert _leftovers(scratch) == []


def test_a_restore_goes_through_while_the_application_is_connected(scratch, tmp_path):
    """Sessions left open on the database being replaced are closed, not waited for."""
    import psycopg

    dump = tmp_path / "database.pgdump"
    backup.dump_database(scratch, dump)
    before = _state(scratch)
    _execute(scratch, "DELETE FROM child", "DELETE FROM record")
    with psycopg.connect(
        dbname=scratch["NAME"], user=scratch["USER"], password=scratch["PASSWORD"],
        host=scratch["HOST"], port=scratch["PORT"], autocommit=True,
    ) as held:
        held.execute("SELECT 1")
        backup.load_database(scratch, dump)
        with pytest.raises(psycopg.Error):
            held.execute("SELECT 1")
    assert _state(scratch) == before
    assert _leftovers(scratch) == []


def test_a_role_that_cannot_create_a_database_is_told_so(scratch, tmp_path):
    role = f"limited_{uuid.uuid4().hex[:8]}"
    maintenance = {**scratch, "NAME": "postgres"}
    _execute(maintenance, f"CREATE ROLE {role} LOGIN PASSWORD 'limited' NOCREATEDB")
    try:
        dump = tmp_path / "database.pgdump"
        backup.dump_database(scratch, dump)
        before = _state(scratch)
        with pytest.raises(backup.BackupError, match="CREATEDB"):
            backup.load_database({**scratch, "USER": role, "PASSWORD": "limited"}, dump)
        assert _state(scratch) == before
    finally:
        _execute(maintenance, f"DROP ROLE IF EXISTS {role}")


def test_an_archive_round_trip_through_the_commands_layer(scratch, tmp_path):
    media = tmp_path / "media"
    (media / "evidence").mkdir(parents=True)
    (media / "evidence" / "capture.bin").write_bytes(b"\x00\x01evidence")
    archive = backup.create_backup(tmp_path / "out", database=scratch, media_root=media, app_version="test")
    manifest = backup.verify_archive(archive)
    assert manifest["database"]["member"] == "database.pgdump"
    assert manifest["database"]["server_version"].split(".")[0].isdigit()
    assert manifest["media_files"] == 1


@pytest.mark.parametrize("tools", [9, 99])
def test_client_tools_of_another_major_are_refused(scratch, tmp_path, monkeypatch, tools):
    """Older tools cannot dump the server; newer ones write a restore script
    it rejects. Both are refused up front, for the backup as for the restore."""
    dump = tmp_path / "database.pgdump"
    backup.dump_database(scratch, dump)
    before = _state(scratch)
    monkeypatch.setattr(backup, "_pg_dump_major", lambda: tools)
    with pytest.raises(backup.BackupError, match="must be the same major"):
        backup.dump_database(scratch, tmp_path / "x.pgdump")
    with pytest.raises(backup.BackupError, match="must be the same major"):
        backup.load_database(scratch, dump)
    assert _state(scratch) == before

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Backup and restore : the database and the media directory, as one archive.

An instance is two things that only make sense together. The database holds
the records, their history and the access log; the media directory holds the
files those records point at (evidence artefacts, proof-of-filing documents).
A restore with one and not the other is not a restore : an evidence register
whose artefacts are missing still claims they exist.

``create_backup`` writes both into a single tar archive with a manifest :

    cairn-backup-20261117-081500Z.tar
        manifest.json       format, version, engine, applied migrations,
                            size and SHA-256 of every other member
        database.pgdump     pg_dump custom format   (PostgreSQL)
        database.sqlite3    a consistent copy       (SQLite)
        media/...           every file under MEDIA_ROOT

``restore_backup`` puts an instance back in the exact state of an archive. It
verifies every checksum first, refuses an archive made by a newer release,
takes a safety backup of what it is about to replace, then loads the database
beside the live one before swapping them (a failure leaves it untouched) and
replaces the media files.

The commands are ``manage.py backup`` and ``manage.py restore``; the
procedure is in ``docs/technical/operations.md``.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

FORMAT = 1
PREFIX = "cairn-backup-"
SAFETY_PREFIX = "cairn-before-restore-"
MANIFEST = "manifest.json"
MEDIA_DIR = "media"
DATABASE_MEMBER = {"postgresql": "database.pgdump", "sqlite": "database.sqlite3"}
CHUNK = 1024 * 1024


class BackupError(Exception):
    """A backup or a restore that cannot go on. The message is for the operator."""


# ── Database ──────────────────────────────────────────────────────────────


def engine_of(database):
    """``postgresql`` or ``sqlite`` for a ``DATABASES`` entry."""
    engine = database.get("ENGINE", "")
    if engine.endswith("postgresql") or engine.endswith("postgis"):
        return "postgresql"
    if engine.endswith("sqlite3"):
        return "sqlite"
    raise BackupError(f"Unsupported database engine : {engine or 'none'}.")


def _pg_environment(database):
    env = dict(os.environ)
    if database.get("PASSWORD"):
        env["PGPASSWORD"] = str(database["PASSWORD"])
    return env


def _pg_connection_arguments(database):
    arguments = ["--dbname", str(database["NAME"])]
    if database.get("HOST"):
        arguments += ["--host", str(database["HOST"])]
    if database.get("PORT"):
        arguments += ["--port", str(database["PORT"])]
    if database.get("USER"):
        arguments += ["--username", str(database["USER"])]
    return arguments


def _pg_tool(name):
    path = shutil.which(name)
    if path is None:
        raise BackupError(
            f"`{name}` is not installed where this command runs. The Cairn image ships the "
            "PostgreSQL client tools; elsewhere, install the client package of your server's "
            "major version."
        )
    return path


def _run(command, database, **kwargs):
    result = subprocess.run(  # noqa: S603 - fixed tool, arguments from the settings
        command, env=_pg_environment(database), capture_output=True, text=True, check=False, **kwargs,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        raise BackupError(f"`{Path(command[0]).name}` failed : {' '.join(detail[-3:]) or 'no output'}")
    return result.stdout


def _pg_server_version(database):
    """``(major, full)`` of the server, asked through psql."""
    full = _run(
        [_pg_tool("psql"), *_pg_connection_arguments(database), "--no-psqlrc", "--tuples-only",
         "--no-align", "--command", "SHOW server_version"],
        database,
    ).strip()
    return int(full.split(".")[0]), full


def _pg_dump_major():
    output = subprocess.run(  # noqa: S603 - fixed tool
        [_pg_tool("pg_dump"), "--version"], capture_output=True, text=True, check=True,
    ).stdout
    # "pg_dump (PostgreSQL) 18.1 (Debian 18.1-1.pgdg13+2)"
    return int(output.split(")")[1].strip().split(".")[0].split()[0])


def _require_matching_tools(database):
    """The server's full version, once the client tools are known to match it.

    pg_dump refuses a server newer than itself, and a newer pg_restore writes
    statements an older server rejects (17 sets a parameter 16 does not have).
    Rather than work in one direction and fail in the other on the day of the
    restore, both commands ask for the same major on both sides.
    """
    major, full = _pg_server_version(database)
    tools = _pg_dump_major()
    if tools != major:
        raise BackupError(
            f"The PostgreSQL client tools here are version {tools} and the server is version {major} : "
            "they must be the same major. The Cairn image ships the tools of the server its compose "
            f"file runs; for another server, build it with `--build-arg POSTGRES_MAJOR={major}`, or "
            "use pg_dump from the database container (see docs/technical/operations.md)."
        )
    return full


def dump_database(database, destination):
    """Write a consistent copy of ``database`` to ``destination``.

    Returns ``{"engine", "server_version"}``. PostgreSQL goes through
    ``pg_dump`` (custom format, one snapshot), SQLite through its online backup
    API (safe while the application writes).
    """
    engine = engine_of(database)
    if engine == "sqlite":
        name = str(database["NAME"])
        if name == ":memory:" or "mode=memory" in name:
            raise BackupError("An in-memory database cannot be backed up.")
        if not Path(name).exists():
            raise BackupError(f"The database file {name} does not exist.")
        source = sqlite3.connect(f"file:{name}?mode=ro", uri=True)
        target = sqlite3.connect(str(destination))
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return {"engine": engine, "server_version": sqlite3.sqlite_version}

    full = _require_matching_tools(database)
    _run(
        [_pg_tool("pg_dump"), *_pg_connection_arguments(database), "--format=custom",
         "--file", str(destination)],
        database,
    )
    return {"engine": engine, "server_version": full}


def load_database(database, source):
    """Replace the content of ``database`` with the dump at ``source``.

    The result is the dump and nothing else : whatever the database held is
    gone, including tables the dump does not know. On PostgreSQL the dump is
    loaded into a new database that then takes the place of the current one,
    so a dump that fails to load leaves the current database as it was.
    """
    engine = engine_of(database)
    if engine == "sqlite":
        dump = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        target = sqlite3.connect(str(database["NAME"]))
        try:
            dump.backup(target)
        finally:
            target.close()
            dump.close()
        return

    _load_postgresql(database, source)


def _identifier(name):
    return '"' + str(name).replace('"', '""') + '"'


def _literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def _psql(database, *commands):
    arguments = [_pg_tool("psql"), *_pg_connection_arguments(database), "--no-psqlrc", "--quiet",
                 "--tuples-only", "--no-align", "--set", "ON_ERROR_STOP=1"]
    for command in commands:
        arguments += ["--command", command]
    return _run(arguments, database)


def _load_postgresql(database, source):
    """Load the dump into a new database, then give it the name of the current one.

    Reloading in place would mean dropping and recreating every table in one
    transaction to stay atomic, and an application schema of a few hundred
    tables exhausts the server's lock table doing so. Loading beside the live
    database has the same guarantee by construction : until the last step the
    current database is not touched, and a dump that fails to load only costs
    the scratch database. The swap itself is two renames.

    The role needs the CREATEDB privilege and must own the database, which is
    the case of the role a compose deployment creates.
    """
    _require_matching_tools(database)
    name = str(database["NAME"])
    stamp = os.urandom(4).hex()
    staging = f"{name[:40]}_restoring_{stamp}"
    retired = f"{name[:40]}_replaced_{stamp}"
    # Renaming or dropping a database is done from another one.
    maintenance = {**database, "NAME": "postgres"}

    try:
        _psql(maintenance, f"CREATE DATABASE {_identifier(staging)}")
    except BackupError as error:
        raise BackupError(
            f"Cannot create the database the archive is loaded into ({error}). The role "
            f"`{database.get('USER')}` needs the CREATEDB privilege and access to the `postgres` "
            "database : `ALTER ROLE ... CREATEDB`, or run the restore as a role that has it."
        ) from error

    try:
        _run(
            [_pg_tool("pg_restore"), *_pg_connection_arguments({**database, "NAME": staging}),
             "--no-owner", "--no-privileges", "--exit-on-error", str(source)],
            database,
        )
    except BackupError:
        _psql(maintenance, f"DROP DATABASE IF EXISTS {_identifier(staging)} WITH (FORCE)")
        raise

    # The application may still be connected : its sessions are closed and the
    # rename retried, since a new one can slip in between the two statements.
    disconnect = (
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = {_literal(name)} AND pid <> pg_backend_pid()"
    )
    last_error = None
    for _attempt in range(10):
        try:
            _psql(maintenance, disconnect, f"ALTER DATABASE {_identifier(name)} RENAME TO {_identifier(retired)}")
            last_error = None
            break
        except BackupError as error:
            last_error = error
    if last_error is not None:
        _psql(maintenance, f"DROP DATABASE IF EXISTS {_identifier(staging)} WITH (FORCE)")
        raise BackupError(
            f"The current database could not be set aside ({last_error}). Nothing was changed. "
            "Stop the application and run the restore again."
        )
    try:
        _psql(maintenance, f"ALTER DATABASE {_identifier(staging)} RENAME TO {_identifier(name)}")
    except BackupError as error:
        # Put the current database back under its name : the instance must not
        # be left without one.
        _psql(maintenance, f"ALTER DATABASE {_identifier(retired)} RENAME TO {_identifier(name)}")
        _psql(maintenance, f"DROP DATABASE IF EXISTS {_identifier(staging)} WITH (FORCE)")
        raise BackupError(f"The restored database could not take its place ({error}). Nothing was changed.") from error
    try:
        _psql(maintenance, f"DROP DATABASE IF EXISTS {_identifier(retired)} WITH (FORCE)")
    except BackupError as error:
        raise BackupError(
            f"The restore succeeded, but the replaced database is still there as `{retired}` "
            f"({error}). Drop it once you no longer need it."
        ) from error


# ── Archive ───────────────────────────────────────────────────────────────


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _media_files(media_root):
    """Every regular file under ``media_root``, as ``(relative posix path, path)``."""
    root = Path(media_root)
    if not root.is_dir():
        return []
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        # A restore in progress, or left behind by an interrupted one.
        if relative.parts and relative.parts[0].startswith(".restore-"):
            continue
        if path.is_file() and not path.is_symlink():
            files.append((relative.as_posix(), path))
    return files


def applied_migrations(connection):
    """``[[app, name], ...]`` recorded in the database, sorted."""
    from django.db.migrations.recorder import MigrationRecorder

    recorder = MigrationRecorder(connection)
    if not recorder.has_table():
        return []
    return sorted([app, name] for app, name in recorder.applied_migrations())


def known_migrations():
    """``{(app, name)}`` of every migration this release ships."""
    from django.db.migrations.loader import MigrationLoader

    return set(MigrationLoader(None, ignore_no_migrations=True).disk_migrations)


def create_backup(output_dir, *, database, media_root, connection=None, app_version="", prefix=PREFIX, now=None):
    """Write an archive of ``database`` and ``media_root`` into ``output_dir``.

    Returns its path. The archive is written under a temporary name and
    renamed once complete, so a file with the final name is always whole.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    moment = now or datetime.now(UTC)
    final = output / f"{prefix}{moment:%Y%m%d-%H%M%S}Z.tar"
    if final.exists():
        raise BackupError(f"{final} already exists.")
    partial = final.with_suffix(".tar.partial")

    engine = engine_of(database)
    members = {}
    try:
        with tempfile.TemporaryDirectory(prefix="cairn-backup-", dir=output) as scratch:
            dump = Path(scratch) / DATABASE_MEMBER[engine]
            info = dump_database(database, dump)
            descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "wb") as raw, tarfile.open(fileobj=raw, mode="w") as archive:
                archive.add(dump, arcname=dump.name)
                members[dump.name] = {"size": dump.stat().st_size, "sha256": _sha256(dump)}
                for relative, path in _media_files(media_root):
                    name = f"{MEDIA_DIR}/{relative}"
                    archive.add(path, arcname=name)
                    members[name] = {"size": path.stat().st_size, "sha256": _sha256(path)}
                manifest = {
                    "format": FORMAT,
                    "created_at": moment.isoformat(timespec="seconds"),
                    "app_version": app_version,
                    "database": {**info, "member": dump.name},
                    "migrations": applied_migrations(connection) if connection is not None else [],
                    "media_files": sum(1 for name in members if name.startswith(f"{MEDIA_DIR}/")),
                    "members": members,
                }
                payload = json.dumps(manifest, indent=1, sort_keys=True).encode()
                entry = tarfile.TarInfo(MANIFEST)
                entry.size = len(payload)
                entry.mtime = int(moment.timestamp())
                entry.mode = 0o600
                archive.addfile(entry, io.BytesIO(payload))
        os.replace(partial, final)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return final


def read_manifest(archive_path):
    """The manifest of an archive, after checking it is one of ours."""
    path = Path(archive_path)
    if not path.is_file():
        raise BackupError(f"{path} is not a file.")
    try:
        with tarfile.open(path, mode="r") as archive:
            try:
                handle = archive.extractfile(MANIFEST)
            except KeyError:
                handle = None
            if handle is None:
                raise BackupError(f"{path.name} has no manifest : it is not a Cairn backup.")
            manifest = json.load(handle)
    except tarfile.TarError as error:
        raise BackupError(f"{path.name} is not a readable archive : {error}") from error
    if manifest.get("format") != FORMAT:
        raise BackupError(
            f"{path.name} uses backup format {manifest.get('format')!r}; this release reads format {FORMAT}."
        )
    return manifest


def _safe_member(name):
    """Refuse a member that would land outside the directory it is extracted to."""
    parts = PurePosixPath(name).parts
    return bool(parts) and not PurePosixPath(name).is_absolute() and ".." not in parts


def verify_archive(archive_path):
    """Check every member against the manifest. Returns the manifest.

    An archive is only trusted when it holds exactly the members its manifest
    lists, each with the recorded size and SHA-256.
    """
    manifest = read_manifest(archive_path)
    expected = dict(manifest.get("members", {}))
    name = Path(archive_path).name
    with tarfile.open(archive_path, mode="r") as archive:
        for member in archive:
            if member.name == MANIFEST:
                continue
            record = expected.pop(member.name, None)
            if record is None:
                raise BackupError(f"{name} : {member.name} is not listed in the manifest.")
            if not member.isfile() or not _safe_member(member.name):
                raise BackupError(f"{name} : {member.name} is not a plain file inside the archive.")
            digest, size = hashlib.sha256(), 0
            handle = archive.extractfile(member)
            while chunk := handle.read(CHUNK):
                digest.update(chunk)
                size += len(chunk)
            if size != record["size"] or digest.hexdigest() != record["sha256"]:
                raise BackupError(f"{name} : {member.name} is damaged (checksum mismatch).")
    if expected:
        raise BackupError(f"{name} : {len(expected)} file(s) listed in the manifest are missing, e.g. {next(iter(expected))}.")
    return manifest


def check_compatible(manifest, database):
    """Refuse an archive this instance cannot load. Returns the migrations the
    archive lacks (to run after the restore)."""
    engine = engine_of(database)
    archived = manifest["database"]["engine"]
    if archived != engine:
        raise BackupError(f"The archive holds a {archived} database; this instance runs on {engine}.")
    known = known_migrations()
    recorded = {tuple(item) for item in manifest.get("migrations", [])}
    unknown = sorted(recorded - known)
    if unknown:
        app, migration = unknown[0]
        raise BackupError(
            f"The archive was made by a newer release ({manifest.get('app_version') or 'unknown version'}) : "
            f"it has {len(unknown)} migration(s) this release does not know, e.g. {app}.{migration}. "
            "Restore it with that release, or a later one."
        )
    # An archive with no migration record (schema built from the models) says
    # nothing about what is pending.
    return sorted(known - recorded) if recorded else []


def restore_media(archive_path, media_root):
    """Replace the content of ``media_root`` with the archive's media files.

    The files are extracted beside the live ones first; the live directory is
    only emptied once every file is on disk. Returns the number of files.
    """
    root = Path(media_root)
    root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".restore-", dir=root))
    count = 0
    try:
        with tarfile.open(archive_path, mode="r") as archive:
            for member in archive:
                if not member.name.startswith(f"{MEDIA_DIR}/") or not member.isfile():
                    continue
                relative = member.name[len(MEDIA_DIR) + 1:]
                if not _safe_member(relative):
                    raise BackupError(f"{member.name} would be written outside the media directory.")
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, open(target, "wb") as handle:
                    shutil.copyfileobj(source, handle, CHUNK)
                count += 1
        for entry in root.iterdir():
            if entry == staging:
                continue
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        for entry in staging.iterdir():
            shutil.move(str(entry), str(root / entry.name))
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return count


def prune(output_dir, keep, prefix=PREFIX):
    """Delete all but the ``keep`` most recent archives. Returns what was deleted."""
    if keep < 1:
        raise BackupError("--keep needs at least 1 : a rotation that keeps nothing deletes the backup just made.")
    archives = sorted(Path(output_dir).glob(f"{prefix}*.tar"), key=lambda path: path.name, reverse=True)
    removed = archives[keep:]
    for path in removed:
        path.unlink()
    return removed

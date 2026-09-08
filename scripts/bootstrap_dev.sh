#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
#
# Provision an ephemeral development sandbox for Cairn : install every system
# and Python dependency the Docker image carries, so the application can be
# started. Written for a throwaway Debian/Ubuntu container (Codespace,
# devcontainer, cloud sandbox) where Docker itself is not available.
#
# It installs an environment and nothing more : no migration is applied and no
# data is written : a fresh database is set up from the first-run onboarding
# screen, which is where that belongs.
#
# By default the stack runs in pure Python on SQLite (core.settings_local) with
# a local Redis, which is what the Docker stack gives minus PostgreSQL; pass
# --with-postgres for full parity.
#
# Everything is idempotent : re-running it on a provisioned sandbox only fills
# in what is missing.
#
#   scripts/bootstrap_dev.sh                  # system libraries, venv, .env, Redis
#   scripts/bootstrap_dev.sh --with-postgres  # ... plus a PostgreSQL server
#   scripts/bootstrap_dev.sh --with-chrome    # ... plus headless Chrome (screenshots)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR="${VENV_DIR:-$REPO_ROOT/.venv}"
PYTHON_BIN="${PYTHON:-python3}"
MIN_PYTHON="3.12"

WITH_CHROME=0
WITH_POSTGRES=0
SKIP_APT=0

usage() {
    cat <<'USAGE'
Provision a development sandbox for Cairn : install every system and Python
dependency the Docker image carries, so the application can be started. Written
for a throwaway Debian/Ubuntu machine where Docker is not available. It sets up
an environment only : no migration is applied and no data is written, a fresh
database being set up from the first-run onboarding screen. Every step is
idempotent.

Usage: scripts/bootstrap_dev.sh [options]

  --with-postgres   set the stack up on PostgreSQL (core.settings) instead of
                    SQLite : server, role and empty database
  --with-chrome     also install headless Chrome, for scripts/capture_screenshots.py
  --skip-apt        touch no system package
  -h, --help        show this help

Environment: PYTHON=/path/to/python selects the interpreter, VENV_DIR the
virtual environment location (default .venv).
USAGE
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --with-chrome)   WITH_CHROME=1 ;;
        --with-postgres) WITH_POSTGRES=1 ;;
        --skip-apt)      SKIP_APT=1 ;;
        -h|--help)       usage ;;
        *) echo "Unknown option: $1 (try --help)" >&2; exit 2 ;;
    esac
    shift
done

step() { printf '\n\033[1;34m==>\033[0m \033[1m%s\033[0m\n' "$1"; }
info() { printf '    %s\n' "$1"; }
warn() { printf '\033[1;33m    warning: %s\033[0m\n' "$1" >&2; }
die()  { printf '\033[1;31merror: %s\033[0m\n' "$1" >&2; exit 1; }

if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
elif command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi

# ---------------------------------------------------------------------------
# 1. System packages
#
# The first block mirrors the Dockerfile (libpq, gettext, and the Pango / Cairo
# stack WeasyPrint loads at runtime to render PDF reports : without it every
# `import weasyprint` dies on a missing libgobject). The rest is what compose
# provides as a service (Redis) or what the base image happens to ship (fonts,
# MIME database, the venv module).
# ---------------------------------------------------------------------------
APT_PACKAGES=(
    gettext libpq-dev libffi-dev
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0
    libglib2.0-0 libglib2.0-0t64
    fontconfig fonts-dejavu-core shared-mime-info
    redis-server
    python3-venv python3-dev
    curl ca-certificates
)

apt_install() {
    # Install only the packages this release actually has : Ubuntu 24.04 renamed
    # part of the GLib stack to a "t64" suffix, so the list above deliberately
    # carries both spellings and we keep whichever exists.
    local wanted=("$@") available=()
    local pkg
    for pkg in "${wanted[@]}"; do
        if apt-cache show "$pkg" >/dev/null 2>&1; then
            available+=("$pkg")
        fi
    done
    [ ${#available[@]} -gt 0 ] || return 0
    DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y --no-install-recommends "${available[@]}"
}

if [ "$SKIP_APT" -eq 1 ]; then
    step "System packages (skipped)"
elif ! command -v apt-get >/dev/null 2>&1; then
    step "System packages"
    warn "apt-get not found : install the Dockerfile's packages by hand (gettext, libpq, Pango/Cairo, Redis)."
else
    step "System packages"
    $SUDO apt-get update -qq
    apt_install "${APT_PACKAGES[@]}"
    if [ "$WITH_POSTGRES" -eq 1 ]; then
        apt_install postgresql postgresql-client
    fi
    if [ "$WITH_CHROME" -eq 1 ] && ! command -v google-chrome-stable >/dev/null 2>&1; then
        info "Adding the Google Chrome repository"
        curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
            | $SUDO gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
            | $SUDO tee /etc/apt/sources.list.d/google-chrome.list >/dev/null
        $SUDO apt-get update -qq
        apt_install google-chrome-stable
    fi
fi

# ---------------------------------------------------------------------------
# 2. Python virtual environment
# ---------------------------------------------------------------------------
step "Python environment"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "$PYTHON_BIN not found : install Python >= $MIN_PYTHON or set PYTHON=/path/to/python."
"$PYTHON_BIN" - "$MIN_PYTHON" <<'PY' || die "Python >= 3.12 is required (Django 5.2+)."
import sys
minimum = tuple(int(part) for part in sys.argv[1].split("."))
sys.exit(0 if sys.version_info[:2] >= minimum else 1)
PY
# A venv may already be active in the calling shell, in which case `python3`
# points inside it : build the sandbox environment from the interpreter that
# venv was itself created from, never from a nested one.
BASE_PYTHON="$("$PYTHON_BIN" -c 'import os, sys; print(os.path.join(sys.base_prefix, "bin", "python3"))')"
if [ -x "$BASE_PYTHON" ]; then PYTHON_BIN="$BASE_PYTHON"; fi
info "Interpreter : $("$PYTHON_BIN" -V) ($(command -v "$PYTHON_BIN"))"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    info "Creating the virtual environment in $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
VENV_PY="$VENV_DIR/bin/python"

"$VENV_PY" -m pip install --quiet --upgrade pip
info "Installing requirements.txt"
# autobahn (via daphne) refuses a pure-Python wheel when its optional NVX C
# extension cannot compile, exactly as in the Dockerfile.
AUTOBAHN_USE_NVX=0 "$VENV_PY" -m pip install --quiet -r requirements.txt

# ---------------------------------------------------------------------------
# 3. Environment file
# ---------------------------------------------------------------------------
step "Environment file"

if [ -f .env ]; then
    info ".env already exists, left untouched"
else
    cp .env.example .env
    SECRET="$("$VENV_PY" -c 'import secrets; print(secrets.token_urlsafe(50))')"
    "$VENV_PY" - "$SECRET" <<'PY'
import pathlib, sys

secret = sys.argv[1]
# Point the service hosts at localhost (compose resolves them as "db" / "redis")
# and give the sandbox its own random SECRET_KEY.
replacements = {
    "SECRET_KEY=": f"SECRET_KEY={secret}",
    "POSTGRES_HOST=": "POSTGRES_HOST=127.0.0.1",
    "# REDIS_HOST=": "REDIS_HOST=127.0.0.1",
    "# REDIS_PORT=": "REDIS_PORT=6379",
}
path = pathlib.Path(".env")
lines = []
for line in path.read_text().splitlines():
    for prefix, new in replacements.items():
        if line.startswith(prefix):
            line = new
            break
    lines.append(line)
path.write_text("\n".join(lines) + "\n")
PY
    info "Created .env from .env.example with a random SECRET_KEY"
fi

# Outside Docker nothing reads .env : compose injects it as env_file, while
# `manage.py` sees only the process environment. Export it here so the steps
# below (and the commands printed at the end) reach the right hosts instead of
# falling back to the compose names "db" and "redis".
set -a
# shellcheck disable=SC1091
. ./.env
set +a

# An .env written for compose names the services "db" and "redis", which resolve
# to nothing here. Keep the file as it is and override the two hosts for this run.
for var in POSTGRES_HOST:db REDIS_HOST:redis; do
    name="${var%%:*}"
    compose_name="${var##*:}"
    if [ "$(eval "echo \${$name:-}")" = "$compose_name" ]; then
        export "$name=127.0.0.1"
        info "$name=$compose_name is a compose service name : using 127.0.0.1 instead"
    fi
done

# ---------------------------------------------------------------------------
# 4. Services : Redis (always) and PostgreSQL (opt-in)
#
# A sandbox container has no init system, so the daemons are started directly.
# Redis keeps its snapshot out of the working tree, and persistence is off : the
# cache and the Channels layer are both disposable.
# ---------------------------------------------------------------------------
step "Services"

if "$VENV_PY" - <<'PY' >/dev/null 2>&1
import socket; socket.create_connection(("127.0.0.1", 6379), timeout=1).close()
PY
then
    info "Redis already listening on 127.0.0.1:6379"
elif command -v redis-server >/dev/null 2>&1; then
    redis-server --daemonize yes --port 6379 --bind 127.0.0.1 \
        --dir /tmp --save '' --appendonly no --logfile /tmp/redis-cairn.log
    info "Redis started (snapshotting off, log in /tmp/redis-cairn.log)"
else
    warn "Redis is not installed : the shared cache and real-time features will not work."
fi

DJANGO_SETTINGS="core.settings_local"
if [ "$WITH_POSTGRES" -eq 1 ]; then
    DJANGO_SETTINGS="core.settings"
    command -v pg_isready >/dev/null 2>&1 || die "PostgreSQL is not installed (re-run without --skip-apt)."
    if ! pg_isready -h 127.0.0.1 -q 2>/dev/null; then
        CLUSTER="$(pg_lsclusters -h 2>/dev/null | awk 'NR==1 {print $1, $2}')"
        if [ -n "$CLUSTER" ]; then
            # shellcheck disable=SC2086
            $SUDO pg_ctlcluster $CLUSTER start || true
        fi
    fi
    pg_isready -h 127.0.0.1 -q 2>/dev/null || die "PostgreSQL did not start."
    DB_NAME="${POSTGRES_DB:-open_grc}"
    DB_USER="${POSTGRES_USER:-postgres}"
    DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
    # The distribution already ships a passwordless "postgres" role, so the
    # password is (re)set unconditionally : creating the role is not enough to
    # make the credentials in .env work over TCP.
    DB_PASSWORD_SQL="${DB_PASSWORD//\'/\'\'}"
    $SUDO -u postgres psql -tAc \
        "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 \
        || $SUDO -u postgres psql -qc "CREATE ROLE \"${DB_USER}\" LOGIN SUPERUSER"
    $SUDO -u postgres psql -qc \
        "ALTER ROLE \"${DB_USER}\" WITH LOGIN SUPERUSER PASSWORD '${DB_PASSWORD_SQL}'"
    $SUDO -u postgres psql -tAc \
        "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 \
        || $SUDO -u postgres createdb -O "${DB_USER}" "${DB_NAME}"
    info "PostgreSQL ready : database ${DB_NAME} owned by ${DB_USER}"
else
    info "Database : SQLite (db.sqlite3) through ${DJANGO_SETTINGS}"
fi

export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS"

# ---------------------------------------------------------------------------
# 5. Application assets
# ---------------------------------------------------------------------------
step "Front-end libraries and translations"

# Django opens the SQLite file on its first connection, even for a command that
# reads nothing from it, so the steps below would leave an empty db.sqlite3
# behind. This script provisions an environment : whatever it creates that is
# not one, it removes again.
SQLITE_FILE="$REPO_ROOT/db.sqlite3"
SQLITE_PREEXISTING=0
if [ -e "$SQLITE_FILE" ]; then SQLITE_PREEXISTING=1; fi

# Mirrors Bootstrap, htmx, Leaflet, the interface font... into static/vendor/
# from the pins in core/dependencies.py, exactly as the image build does.
"$VENV_PY" manage.py vendor_assets
"$VENV_PY" manage.py compilemessages --verbosity 0

# ---------------------------------------------------------------------------
# 6. Verification
# ---------------------------------------------------------------------------
step "Verification"

"$VENV_PY" - <<'PY'
import importlib, socket, sys

ok = True

try:
    import weasyprint  # noqa: F401
    print("    weasyprint  : OK (PDF reports)")
except Exception as exc:  # pragma: no cover - sandbox diagnostics
    ok = False
    print(f"    weasyprint  : FAILED ({exc})")

for module, label in (("pptx", "python-pptx"), ("docx", "python-docx"), ("openpyxl", "openpyxl")):
    try:
        importlib.import_module(module)
        print(f"    {label:<12}: OK")
    except Exception as exc:
        ok = False
        print(f"    {label:<12}: FAILED ({exc})")

try:
    socket.create_connection(("127.0.0.1", 6379), timeout=1).close()
    print("    redis       : OK")
except OSError as exc:
    ok = False
    print(f"    redis       : FAILED ({exc})")

sys.exit(0 if ok else 1)
PY

# The schema is not this script's business, but an unreachable server would be
# an incomplete environment : check the connection, not what is inside it.
if [ "$WITH_POSTGRES" -eq 1 ]; then
    "$VENV_PY" - <<'PY'
import os
import sys

import psycopg

try:
    psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "open_grc"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
        connect_timeout=5,
    ).close()
    print("    postgres    : OK (server reachable)")
except Exception as exc:
    print(f"    postgres    : FAILED ({exc})")
    sys.exit(1)
PY
fi

"$VENV_PY" manage.py check

if [ "$SQLITE_PREEXISTING" -eq 0 ] && [ -f "$SQLITE_FILE" ] && [ ! -s "$SQLITE_FILE" ]; then
    rm -f "$SQLITE_FILE"
fi

step "Ready"
cat <<EOF
    source ${VENV_DIR}/bin/activate
    set -a && source .env && set +a          # compose injects it, a shell does not
    export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS}
    python manage.py runserver 0.0.0.0:8000

    The database is empty : the first-run screen applies the migrations and
    offers to create your company or load the Voltara Energy demo dataset.
EOF

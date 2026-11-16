#!/bin/sh
set -e

# ── Drop privileges ────────────────────────────────────────────────────
# The container starts as root so that it can hand the writable directories
# to the account the application runs as, then it restarts this script as that
# account : nothing below this block, and no web worker, runs as root.
#
# Which account : the owner of /app. In the image that is `cairn`. With the
# development bind-mount (.:/app) it is whoever owns the checkout on the host,
# so the files the container generates there (translations, collected static,
# uploads) stay theirs. A root-owned /app (some bind-mount drivers report
# that) falls back to `cairn`.
#
# Started as anything other than root (`docker run --user`, an orchestrator's
# runAsUser), the script runs as given and this block is skipped.
if [ "$(id -u)" = "0" ]; then
    run_uid=$(stat -c %u /app)
    run_gid=$(stat -c %g /app)
    if [ "$run_uid" = "0" ]; then
        run_uid=$(id -u cairn)
        run_gid=$(id -g cairn)
    fi
    # Uploads and collected static written by an earlier, root-running version
    # of the image (a media volume, typically) : hand them over once. Only
    # root-owned directories are touched, never a directory a host user owns.
    for dir in /app/media /app/staticfiles; do
        mkdir -p "$dir"
        if [ "$(stat -c %u "$dir")" = "0" ]; then
            chown -R "$run_uid:$run_gid" "$dir"
        fi
    done
    # An account with no passwd entry (a host uid) has no home of its own.
    if [ "$run_uid" != "$(id -u cairn)" ]; then
        export HOME=/tmp
    else
        export HOME=/home/cairn
    fi
    exec setpriv --reuid="$run_uid" --regid="$run_gid" --clear-groups "$0" "$@"
fi

# Clear stale bytecode from image layer that may conflict with bind-mounted source
find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "Waiting for database to be ready…"
max_retries=30
retry_count=0
until python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
connection.ensure_connection()
" 2>/dev/null; do
    retry_count=$((retry_count + 1))
    if [ "$retry_count" -ge "$max_retries" ]; then
        echo "Error: Database not available after $max_retries attempts, exiting."
        exit 1
    fi
    echo "Database not ready yet (attempt $retry_count/$max_retries), waiting 1s…"
    sleep 1
done
echo "Database is ready."

# A fresh, un-initialised database is migrated from the first-run onboarding
# screen instead, so the operator sees live progress. Only auto-migrate here when
# the instance already has users (an upgrade) or when a super-admin is being
# provisioned non-interactively via env vars (automated setup, no onboarding).
INITIALISED=$(python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
try:
    from accounts.models import User
    print('yes' if User.objects.exists() else 'no')
except Exception:
    print('no')
" 2>/dev/null || echo "no")

if [ "$INITIALISED" = "yes" ] || [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Applying database migrations…"
    # One-time fixup: migration 0022_company_settings was renamed to 0023_company_settings
    python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute(\"SELECT 1 FROM django_migrations WHERE app='accounts' AND name='0022_company_settings'\")
    if c.fetchone():
        c.execute(\"UPDATE django_migrations SET name='0023_company_settings' WHERE app='accounts' AND name='0022_company_settings'\")
" 2>/dev/null || true
    python manage.py migrate --noinput
else
    echo "Fresh database detected: migrations will be applied from the onboarding screen."
fi

# The image already carries the front-end libraries, but the compose bind-mount
# (.:/app) shadows them with the host's static/vendor/, which a fresh clone does
# not have. Idempotent: it downloads only what is missing, and is a no-op in a
# plain `docker run` of the published image.
echo "Checking front-end libraries…"
python manage.py vendor_assets || echo "Warning: front-end libraries could not be mirrored; the interface may render unstyled."

# Non-fatal : the image already carries the compiled catalogues, and an
# account that cannot write next to them (an arbitrary `--user`) must still
# be able to start.
echo "Compiling translation files…"
python manage.py compilemessages || echo "Warning: translations could not be recompiled; using the ones shipped in the image."

# Refresh collected static at runtime, not just at image build. The compose
# bind-mount (.:/app) shadows the image's build-time staticfiles/, and deploys
# that pull new code without rebuilding never re-run collectstatic. Without this,
# newly added assets (e.g. js/lifecycle_graph.js) are absent from STATIC_ROOT, so
# the proxy serves an HTML 404 that nosniff blocks. Keep it non-fatal so a
# read-only STATIC_ROOT can't stop the app from booting.
echo "Collecting static files…"
python manage.py collectstatic --noinput || echo "Warning: collectstatic failed; static assets may be stale."

# Create the initial super-admin if configured and not already present.
# Requires DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD in the environment.
if [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py createsuperuser \
        --noinput \
        --email "$DJANGO_SUPERUSER_EMAIL" \
        --first_name "${DJANGO_SUPERUSER_FIRST_NAME:-Admin}" \
        --last_name "${DJANGO_SUPERUSER_LAST_NAME:-}" \
        2>/dev/null || true
    echo "Super-admin check complete."
fi

exec "$@"

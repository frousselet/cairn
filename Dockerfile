FROM python:slim

LABEL org.opencontainers.image.source="https://github.com/frousselet/cairn"
LABEL org.opencontainers.image.description="Cairn - Governance, Risk & Compliance platform"
LABEL org.opencontainers.image.licenses="AGPL-3.0-or-later"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG APP_VERSION=dev

WORKDIR /app

# The account the application runs as. The container starts as root only long
# enough for the entrypoint to hand over the writable directories, then drops
# to this user (see entrypoint.sh) : the web process never holds root.
RUN groupadd --gid 1000 cairn \
    && useradd --uid 1000 --gid cairn --create-home --shell /usr/sbin/nologin cairn \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R cairn:cairn /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev gettext \
       libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
       libffi-dev libcairo2 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# autobahn (transitive dep of daphne) refuses to emit a pure-Python wheel when
# its optional NVX C extension can't compile (no gcc in python:slim). Opt out of
# the native extension so the pure-Python build is allowed.
RUN AUTOBAHN_USE_NVX=0 pip install --no-cache-dir -r requirements.txt

COPY --chown=cairn:cairn . .

RUN echo "${APP_VERSION}" > /etc/app-version

# The build steps below load the Django settings, which refuse to start
# outside DEBUG without a real SECRET_KEY. The value they are given exists for
# the duration of each command only : it is not stored in the image
# environment, and the running container must be given its own.

# Generated files (mirrored libraries, compiled translations, collected
# static) belong to the unprivileged account, which refreshes them at start.
USER cairn

# Mirror the front-end libraries into static/vendor/ so the running container
# never contacts a CDN. Unlike the two commands below this one must NOT be
# tolerated to fail: an image shipped without them renders an unstyled
# interface, and the build machine is the only place with a mirror to reach.
RUN SECRET_KEY=build-time-only python manage.py vendor_assets

RUN SECRET_KEY=build-time-only python manage.py compilemessages 2>/dev/null || true
RUN SECRET_KEY=build-time-only python manage.py collectstatic --noinput 2>/dev/null || true

# Back to root for the entrypoint's hand-over; it drops privileges itself.
USER root

EXPOSE 8000

# Healthy once the entrypoint has migrated and the server answers with the
# database reachable. The start period covers migrations and collectstatic.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "core.asgi:application", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "3", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--access-log"]

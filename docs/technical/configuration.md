# Configuration

Cairn reads its entire configuration from the environment. `.env.example` is the
template : copy it to `.env` and edit. Nothing is configured in a database table
that an operator needs to reach before first boot, and nothing needs a rebuild.

The exhaustive list, generated from the settings modules themselves, is
[reference/generated/settings.md](../reference/generated/settings.md). This page
covers what to think about rather than what exists.

## The four you must not leave alone

| Variable | Why |
| --- | --- |
| `SECRET_KEY` | Signs sessions, password-reset links and Trust Center download links. The shipped default is a public placeholder; a deployment that kept it could have its sessions forged, so **Cairn refuses to start with a placeholder key once `DEBUG` is off**. Generate 50+ random characters : `python -c "import secrets; print(secrets.token_urlsafe(64))"`. |
| `DEBUG` | Off by default, and must stay off in production : left on, a crash returns a full traceback page including settings and local variables. Development turns it on (`.env.example` does, and so does `core.settings_local`). |
| `ALLOWED_HOSTS` | The hostnames the application answers on. A wildcard reopens the Host-header attacks Django's check exists to close. |
| `POSTGRES_PASSWORD` | The compose file ships `postgres/postgres`. |

## Backing services

PostgreSQL and Redis are both required. Redis is not a cache you can skip : it
carries the Channels layer and the cross-worker locks, and the reasons are in
[architecture.md](architecture.md#redis-is-not-optional).

```bash
POSTGRES_DB=cairn
POSTGRES_USER=cairn
POSTGRES_PASSWORD=<generated>
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_HOST=redis
REDIS_PORT=6379
```

## Behind a reverse proxy

Cairn trusts `X-Forwarded-Proto` (`SECURE_PROXY_SSL_HEADER`), so the proxy must
set it and must not let a client forge it.

```bash
ALLOWED_HOSTS=grc.example.com
CSRF_TRUSTED_ORIGINS=https://grc.example.com
SITE_URL=https://grc.example.com
```

`SITE_URL` is what makes links in notification and invitation emails absolute.
Leave it empty and the links are relative, which means they do not work in a
mail client.

## HTTPS hardening

Every hardening flag defaults to off, so upgrading an HTTP-only deployment never
breaks it. Turn them on once TLS terminates in front of the application, in this
order, checking that you can still sign in between each step.

```bash
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

HSTS is last and deserves a pause : a browser remembers it for the whole
`max-age` even after you unset the header, so a wrong value locks your own users
out of an HTTP fallback for a year. Start with a short `SECURE_HSTS_SECONDS`
(say 300), confirm, then raise it.

Run `python manage.py check --deploy` to have Django audit the result.

## Email

Notifications, invitations and password resets go out by email. Under `DEBUG`
the console backend prints them instead, so no SMTP is needed in development.

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=cairn@example.com
EMAIL_HOST_PASSWORD=<secret>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=cairn@example.com
```

## Passkeys

`WEBAUTHN_RP_ID` and `WEBAUTHN_ORIGIN` are derived from the request when unset,
which is correct for a single-domain deployment. Set them explicitly behind a
proxy that rewrites the host, otherwise the browser refuses the credential
because the relying-party id does not match what it sees.

## Trust Center on its own domain

Setting `TRUST_CENTER_HOST` turns on host isolation : on that hostname only the
public Trust Center is reachable, and the application, the admin and the
internal API return 404. Add the host to `ALLOWED_HOSTS` and its https origin to
`CSRF_TRUSTED_ORIGINS`.

```bash
TRUST_CENTER_HOST=trust.example.com
TRUST_CENTER_DOWNLOAD_TTL=604800
```

## Ask Cairn

Off by default, and deliberately so : enabling it sends the question text and
the compact record fields used for routing to the configured provider. Choose
the provider with that in mind; `ollama` keeps everything on your own
infrastructure.

```bash
AI_ASSISTANT_ENABLED=True
AI_ASSISTANT_PROVIDER=mistral      # or openai, anthropic, ollama
AI_ASSISTANT_API_KEY=<secret>
AI_ASSISTANT_MODEL=mistral-small-latest
```

Provider setup, model guidance and the data-egress detail are in the
[assistant specification](../specs/assistant/README.md). The tuning knobs
(timeouts, tool rounds, record caps, token ceiling) are listed in the
[generated settings reference](../reference/generated/settings.md); their
defaults are conservative on purpose, so a slow provider degrades the command
palette rather than the whole application.

## Logging

```bash
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING or ERROR, for the whole application
LOG_LEVEL_SQL=WARNING   # set to DEBUG to log every SQL statement (verbose)
```

Everything is written to the console (stderr), where the container runtime
collects it, in production as under `DEBUG`. That includes the traceback of an
unhandled request error : the user sees the error page, the operator finds the
cause in the log.

## Files and backups

```bash
MEDIA_ROOT=/app/media     # uploaded files : evidence artefacts, filed documents
BACKUP_DIR=/app/backups   # where `manage.py backup` writes its archives
```

Both default to a directory beside the code, and both must outlive the
container : mount a volume on the first and a host directory on the second.
The backup and restore procedure is in [Operations](operations.md#backups).

## Maps

```bash
MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png   # empty : no map
MAP_TILE_URL_DARK=                                            # tiles for the dark theme
MAP_TILE_ATTRIBUTION=...                                      # credit line (HTML)
```

The scope, site and supplier pages show their location on a map. The tiles are
fetched **by the reader's browser**, straight from the provider : the instance
itself makes no call. The default is OpenStreetMap's own tile service, which
needs no account and is meant for moderate use with visible attribution. For
heavier use, or for another style, point `MAP_TILE_URL` at any XYZ tile
provider, with its key in the URL when it needs one. Without
`MAP_TILE_URL_DARK` the same tiles are dimmed under the dark theme. Whatever
the provider, the tiles are desaturated so the map stays a backdrop.

Set `MAP_TILE_URL` to an empty value where browsers must not reach an outside
service : the pages then show no map. The address lookup of the site and
supplier forms (Photon) is a second browser-side call, made only when someone
types an address.

## What the instance calls out to

Two knobs, both defaulting to on, both about traffic leaving the instance.

```bash
VENDOR_ASSETS_AUTO_DOWNLOAD=True   # mirror the front-end libraries when missing
UPDATE_CHECK_ENABLED=True          # let the About modal ask GitHub for the latest release
```

`VENDOR_ASSETS_AUTO_DOWNLOAD` is a **setup-time** call, not a runtime one : the
front-end libraries are always served from `static/vendor/`, and this only says
whether a launch that finds them missing may fetch them. A Docker image already
has them. Set it to `False` when the files are placed by your own build or
image, and the instance will never reach out.

`UPDATE_CHECK_ENABLED` is the only call the *running* interface can make. It
fires when someone opens the About modal, never on a page load; it asks GitHub
for the latest release of the Cairn repository and caches the answer for six
hours across all workers. Nothing about the instance is sent : it is a plain
read of a public endpoint. Set it to `False` where policy forbids the
application originating outbound traffic at all.

## Lifecycle definitions across workers

```bash
LIFECYCLE_CACHE_TTL=5   # seconds a worker trusts its in-memory lifecycle definitions
```

The lifecycles edited under *Administration > Lifecycles* are cached in each
worker process. A worker checks the table again at most every
`LIFECYCLE_CACHE_TTL` seconds, so an edit saved by one worker is applied by the
others within that delay. Lower it for a faster propagation at the cost of one
small query more often; there is rarely a reason to raise it.

## Superuser bootstrap

`DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` are read by the
container entrypoint, not by the settings, and create an administrator on first
startup. They are an alternative to the
[first-run onboarding screen](../specs/m0-accounts/onboarding.md), which is the
better path for a human operator because it also configures the company.

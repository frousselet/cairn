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
| `SECRET_KEY` | Signs sessions, password-reset links and Trust Center download links. The shipped default is a placeholder; a deployment that keeps it can have its sessions forged. Generate 50+ random characters. |
| `DEBUG` | Must be `False` in production. Left on, a crash returns a full traceback page including settings and local variables. |
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

## Superuser bootstrap

`DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` are read by the
container entrypoint, not by the settings, and create an administrator on first
startup. They are an alternative to the
[first-run onboarding screen](../specs/m0-accounts/onboarding.md), which is the
better path for a human operator because it also configures the company.

<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the settings modules (`core/settings.py`, `assets/services/spof_scheduler.py`) and `.env.example` by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# Environment variables

Cairn is configured entirely through the environment. This page lists every variable the code reads, taken from the settings modules themselves rather than from the template, so a variable that exists in the code but not in `.env.example` still shows up here.

The **In template** column says whether `.env.example` mentions it. Copy that file to `.env` to get started; anything absent from it falls back to the default below. Setting them up is covered in [../../technical/configuration.md](../../technical/configuration.md).

**48 variables** are read by the code.

## Variables

| Variable | Default | In template | Notes |
| --- | --- | --- | --- |
| `AI_ASSISTANT_API_KEY` | - | yes |  |
| `AI_ASSISTANT_BASE_URL` | - | yes |  |
| `AI_ASSISTANT_CONNECT_TIMEOUT` | `2` | yes | Assistant tuning. Defaults are deliberately conservative: a slow or chatty provider degrades the command palette rather than the whole application. |
| `AI_ASSISTANT_EMBED_MODEL` | `mistral-embed` | yes |  |
| `AI_ASSISTANT_ENABLED` | `False` | yes | Optional - "Ask Cairn" AI assistant (third-party LLM, Mistral AI by default). Risk/compliance record data is sent to the provider; enable deliberately. |
| `AI_ASSISTANT_MAX_RECORDS_PER_TOOL` | `5` | yes |  |
| `AI_ASSISTANT_MAX_TOKENS` | `1024` | yes |  |
| `AI_ASSISTANT_MAX_TOOL_ROUNDS` | `3` | yes |  |
| `AI_ASSISTANT_MODEL` | `mistral-small-latest` | yes |  |
| `AI_ASSISTANT_NUM_CTX` | `8192` | yes | Ollama only: context window, and whether the routing call may "think" first. |
| `AI_ASSISTANT_OLLAMA_URL` | `http://ollama:11434` | yes |  |
| `AI_ASSISTANT_PROVIDER` | `mistral` | yes |  |
| `AI_ASSISTANT_ROUTING_THINK` | `False` | yes |  |
| `AI_ASSISTANT_SEMANTIC_ENABLED` | `False` | yes | Semantic (meaning-based, cross-language) requirement search. After enabling, build the index: docker compose exec web python manage.py rebuild_semantic_index |
| `AI_ASSISTANT_TIMEOUT` | `30` | yes |  |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | yes |  |
| `CSRF_COOKIE_SECURE` | `False` | yes |  |
| `CSRF_TRUSTED_ORIGINS` | - | yes | Reverse proxy: trusted origins for CSRF (include scheme) |
| `DEBUG` | `True` | yes |  |
| `DEFAULT_FROM_EMAIL` | `cairn@localhost` | yes |  |
| `EMAIL_BACKEND` | `'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'` | yes | Outgoing email (notifications, invitations, password resets). The console backend is the default under DEBUG, SMTP otherwise. |
| `EMAIL_HOST` | `localhost` | yes |  |
| `EMAIL_HOST_PASSWORD` | - | yes |  |
| `EMAIL_HOST_USER` | - | yes |  |
| `EMAIL_PORT` | `25` | yes |  |
| `EMAIL_USE_TLS` | `False` | yes |  |
| `POSTGRES_DB` | `open_grc` | yes |  |
| `POSTGRES_HOST` | `db` | yes |  |
| `POSTGRES_PASSWORD` | `postgres` | yes |  |
| `POSTGRES_PORT` | `5432` | yes |  |
| `POSTGRES_USER` | `postgres` | yes |  |
| `REDIS_HOST` | `redis` | yes | Redis - Channels layer (real-time) and the shared cache. Required: several cross-worker locks (onboarding runner, semantic index rebuild, SPOF scheduler, Trust Center rate limiter) coordinate through it. |
| `REDIS_PORT` | `6379` | yes |  |
| `SECRET_KEY` | `django-insecure-change-me-in-production` | yes |  |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` | yes |  |
| `SECURE_HSTS_PRELOAD` | `False` | yes |  |
| `SECURE_HSTS_SECONDS` | `0` | yes |  |
| `SECURE_SSL_REDIRECT` | `False` | yes |  |
| `SESSION_COOKIE_SECURE` | `False` | yes | HTTPS hardening. All default to off so an HTTP-only deployment keeps working; turn them on once TLS terminates in front of the app. Enable the two cookie flags first, confirm you can still sign in, then add the redirect, and only then HSTS - a browser remembers HSTS for the whole max-age even if you undo it. |
| `SITE_URL` | - | yes | Absolute URL prefix used in notification emails and invitation links. Leave empty and links are relative, which breaks them in an email client. |
| `SPOF_REFRESH_INTERVAL` | `300` | yes | How often (seconds) the background SPOF detector re-scans the dependency graph. |
| `TRUST_CENTER_DOWNLOAD_TTL` | `604800` | yes | Lifetime (seconds) of a gated-document download link (default 7 days). |
| `TRUST_CENTER_HOST` | - | yes | Optional - Trust Center on a dedicated public domain. Leave empty to serve it only at /trust/ on the main host. When set, only the public Trust Center is reachable on this host (the app, admin and internal API return 404). Also add the host to ALLOWED_HOSTS and its https origin to CSRF_TRUSTED_ORIGINS. |
| `UPDATE_CHECK_ENABLED` | `True` | yes | Whether the About modal may ask GitHub whether a newer release exists. It is the only outbound call the interface makes, it fires only when someone opens that modal, and the answer is cached. Set to False where policy forbids the instance calling out. |
| `VENDOR_ASSETS_AUTO_DOWNLOAD` | `True` | yes | The front-end libraries (Bootstrap, htmx, Leaflet, the interface font...) are served from this instance, never from a CDN. A Docker image mirrors them at build time; a direct install downloads what is missing on its first launch. Set to False for an air-gapped install that puts the files in place itself. |
| `WEBAUTHN_ORIGIN` | - | yes |  |
| `WEBAUTHN_RP_ID` | - | yes | Passkeys / WebAuthn. Both are derived from the request when unset, which is correct for a single-domain deployment; set them explicitly behind a proxy that rewrites the host, or the browser refuses the credential. |
| `WEBAUTHN_RP_NAME` | `Cairn` | yes |  |

## In `.env.example`, not read by the settings modules

Consumed elsewhere than the settings (the container entrypoint, `docker-compose.yml`) rather than unused.

`DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_FIRST_NAME`, `DJANGO_SUPERUSER_LAST_NAME`, `DJANGO_SUPERUSER_PASSWORD`

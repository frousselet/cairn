<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the settings modules (`core/settings.py`, `assets/services/spof_scheduler.py`) and `.env.example` by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# Environment variables

Cairn is configured entirely through the environment. This page lists every variable the code reads, taken from the settings modules themselves rather than from the template, so a variable that exists in the code but not in `.env.example` still shows up here.

The **In template** column says whether `.env.example` mentions it. Copy that file to `.env` to get started; anything absent from it falls back to the default below. Setting them up is covered in [../../technical/configuration.md](../../technical/configuration.md).

**60 variables** are read by the code.

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
| `BACKUP_DIR` | - | yes | Directory `manage.py backup` writes its archives to. In a container, mount a volume or a host directory there (default : backups/ beside the code). |
| `CSP_MODE` | `enforce` | yes | Content Security Policy sent with every page : enforce (default), report (nothing blocked, violations in the browser console) or off. |
| `CSRF_COOKIE_SECURE` | `_secure_cookies` | yes |  |
| `CSRF_TRUSTED_ORIGINS` | - | yes | Reverse proxy: trusted origins for CSRF (include scheme) |
| `DEBUG` | `False` | yes |  |
| `DEFAULT_FROM_EMAIL` | `cairn@localhost` | yes |  |
| `EMAIL_BACKEND` | `'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'` | yes | Outgoing email (notifications, invitations, password resets). The console backend is the default under DEBUG, SMTP otherwise. |
| `EMAIL_HOST` | `localhost` | yes |  |
| `EMAIL_HOST_PASSWORD` | - | yes |  |
| `EMAIL_HOST_USER` | - | yes |  |
| `EMAIL_PORT` | `25` | yes |  |
| `EMAIL_USE_TLS` | `False` | yes |  |
| `LIFECYCLE_CACHE_TTL` | `5` | yes | Seconds a worker process trusts its in-memory lifecycle definitions before checking the table again : how long the other workers may keep applying the previous version of a lifecycle edited in the administration. |
| `LOG_LEVEL` | `INFO` | yes | Verbosity of the application log, written to the console in production as under DEBUG : DEBUG, INFO, WARNING or ERROR. |
| `LOG_LEVEL_SQL` | `WARNING` | yes | Set to DEBUG to log every SQL statement (verbose, for a diagnosis only). |
| `MAP_GEOCODER_URL` | - | yes | Geocoder the maps and the address fields ask for the position of an address (a Photon-compatible API). Off unless set : the address is sent to it by the reader's browser. |
| `MAP_TILE_ATTRIBUTION` | `&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors` | yes | Credit line shown on the map, as the provider's terms require (HTML). |
| `MAP_TILE_URL` | - | yes | Basemap of the maps on the scope, site and supplier pages. Off unless set : the tiles are fetched by the reader's browser, straight from this provider, which learns who looks at which place. Any XYZ tile URL works, with its key when the provider needs one. |
| `MAP_TILE_URL_DARK` | - | yes | Tiles to use under the dark theme. Empty : the tiles above are dimmed. |
| `MEDIA_ROOT` | - | yes | Directory of the uploaded files (evidence artefacts, filed documents). Mount a volume there : it must outlive the container (default : media/ beside the code). |
| `OAUTH_ACCESS_TOKEN_LIFETIME_DAYS` | `90` | yes | Days an OAuth access token (MCP clients, API scripts) stays valid. |
| `POSTGRES_DB` | `open_grc` | yes |  |
| `POSTGRES_HOST` | `db` | yes |  |
| `POSTGRES_PASSWORD` | `postgres` | yes |  |
| `POSTGRES_PORT` | `5432` | yes |  |
| `POSTGRES_USER` | `postgres` | yes |  |
| `REDIS_HOST` | `redis` | yes | Redis - Channels layer (real-time) and the shared cache. Required: several cross-worker locks (onboarding runner, semantic index rebuild, SPOF scheduler, Trust Center rate limiter) coordinate through it. |
| `REDIS_PORT` | `6379` | yes |  |
| `SECRET_KEY` | `django-insecure-change-me-in-production` | yes | This file is a development configuration. For a deployment : give SECRET_KEY a long random value of your own (Cairn refuses to start on this placeholder once DEBUG is off) and remove the DEBUG line, which is off by default. |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` | yes |  |
| `SECURE_HSTS_PRELOAD` | `False` | yes |  |
| `SECURE_HSTS_SECONDS` | `0` | yes |  |
| `SECURE_SSL_REDIRECT` | `False` | yes | The redirect and HSTS are opt-in : add the redirect once the proxy forwards X-Forwarded-Proto, and only then HSTS - a browser remembers HSTS for the whole max-age even if you undo it. |
| `SESSION_COOKIE_AGE` | `str(12 * 60 * 60)` | yes | Seconds a session lasts from sign-in (12 hours by default). |
| `SESSION_COOKIE_SECURE` | `_secure_cookies` | yes | HTTPS hardening. With DEBUG off the session and CSRF cookies are only sent over HTTPS : an instance is meant to sit behind a proxy terminating TLS. Set them to False only for an instance deliberately reached without TLS. |
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

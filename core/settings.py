# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""
Django settings for Cairn project.
"""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-me-in-production",
)

# Off unless asked for : an instance started with no configuration must not
# serve tracebacks, settings and local variables to whoever triggers an error.
# Development sets DEBUG=True (.env.example does, core.settings_local too).
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")

# The placeholder keys are public : they ship in this file and in .env.example.
# Outside DEBUG a deployment that kept one would sign its sessions, its
# password-reset links and its Trust Center download links with a key anyone
# can read, so it refuses to start instead of running forgeable.
_PLACEHOLDER_SECRET_KEYS = {
    "django-insecure-change-me-in-production",
    "change-me-to-a-random-secret-key",
}
if not DEBUG and SECRET_KEY in _PLACEHOLDER_SECRET_KEYS:
    raise ImproperlyConfigured(
        "SECRET_KEY is still the public placeholder while DEBUG is off. Set "
        "SECRET_KEY to a long random value (for example : python -c \"import "
        "secrets; print(secrets.token_urlsafe(64))\") before starting Cairn. "
        "For local development, load your .env (it sets DEBUG=True) or use "
        "--settings=core.settings_local."
    )


def _detect_version():
    """Return app version from /etc/app-version, version.txt, or 'dev'."""
    for path in (Path("/etc/app-version"), BASE_DIR / "version.txt"):
        try:
            version = path.read_text().strip()
            if version:
                return version
        except Exception:
            pass
    return "dev"


APP_VERSION = _detect_version()

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Reverse proxy support - trust X-Forwarded-Proto so Django knows the
# original request was HTTPS (required for secure cookies, CSRF, etc.).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HTTPS hardening.
#
# The session and CSRF cookies are only sent over HTTPS, outside DEBUG : a
# session cookie that travels in clear is a session anyone on the path can
# take over. An instance has to be reached over HTTPS (a reverse proxy
# terminating TLS is enough); the sign-in page says so when it is opened over
# plain http. Set them to False only for an instance that is deliberately
# reached without TLS, on a network you answer for.
#
# The redirect and HSTS stay opt-in : turned on before TLS terminates in front
# of the application they loop or lock a host out, and HSTS cannot be taken
# back. The security documentation gives the order.
_secure_cookies = "False" if DEBUG else "True"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", _secure_cookies).lower() in ("true", "1", "yes")
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", _secure_cookies).lower() in ("true", "1", "yes")
# Seconds a session lasts from sign-in, whatever the activity (12 hours) : a
# working day, not the two weeks Django defaults to. A stolen or forgotten
# session ends by itself.
SESSION_COOKIE_AGE = int(os.environ.get("SESSION_COOKIE_AGE", str(12 * 60 * 60)))
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False").lower() in ("true", "1", "yes")
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() in ("true", "1", "yes")
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "False").lower() in ("true", "1", "yes")

# Origins allowed to make cross-site requests (needed behind a reverse proxy).
# Example: CSRF_TRUSTED_ORIGINS=https://grc.example.com,https://grc.rslt.fr
_trusted = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _trusted.split(",") if o.strip()]

INSTALLED_APPS = [
    # "daphne" must come first so its ASGI-aware runserver replaces Django's
    # default WSGI one (Channels 4 requirement). Without it, `manage.py
    # runserver` serves WSGI only and every /ws/ WebSocket route returns 404.
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "django_htmx",
    "core",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "simple_history",
    "accounts",
    "helpers",
    "context",
    "assets",
    "compliance",
    "risks",
    "incidents",
    "documents",
    "controls",
    "reports",
    "mcp",
    "assistant",
    "trust_center",
]

MIDDLEWARE = [
    # First on purpose : a health probe calls by IP with no session, and must
    # be answered before host validation, redirects or session handling.
    "core.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Serve collected static files directly from the ASGI app (uvicorn does not
    # serve static, and core/urls.py only wires them under DEBUG). Without this,
    # every /static/ request falls through to Django's 404 (text/html), which
    # X-Content-Type-Options: nosniff then blocks. Must sit right after
    # SecurityMiddleware. In DEBUG, staticfiles/runserver handle serving instead.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Outside everything that renders a page (the onboarding, the Trust Center
    # host routing, the views) : each of their responses carries the policy,
    # with the nonce its template asked for.
    "core.csp.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "trust_center.middleware.TrustCenterHostMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.OnboardingMiddleware",
    "accounts.middleware.UserLanguageMiddleware",
    "accounts.middleware.ImpersonationMiddleware",
    "accounts.middleware.AuthenticationRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            # {% csp_nonce %} in every template without a {% load %} : an inline
            # script that forgets its nonce does nothing in a browser.
            "builtins": ["core.templatetags.csp"],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "core.context_processors.app_version",
                "core.context_processors.third_party_dependencies",
                "core.context_processors.accessibility_statement",
                "core.context_processors.assistant_enabled",
                "core.context_processors.map_tiles",
                "core.context_processors.company",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# Django Channels
#
# RedisPubSubChannelLayer instead of the historical RedisChannelLayer:
# the former uses Redis pub/sub (push) and the latter polls BLPOP with
# a finite socket read timeout. With BLPOP the dashboard WebSocket
# consumer crashed every few seconds with redis.exceptions.TimeoutError
# when no event was published in the polling window, the WS reconnected,
# and the boot log filled with stack traces. PubSub has no polling
# timeout because there is nothing to poll: Redis pushes when a message
# arrives. Trade-off: messages are not queued for consumers that drop
# briefly, which is fine here because the broadcast events are dashboard
# refresh hints (the next save broadcasts another one) rather than
# durable work items.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": {
            "hosts": [(os.environ.get("REDIS_HOST", "redis"), int(os.environ.get("REDIS_PORT", 6379)))],
        },
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "open_grc"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
    }
}

# Cache
#
# Redis-backed and therefore *shared across worker processes*. This is a
# correctness requirement, not just an optimisation: the app runs several
# uvicorn workers in production (see the Dockerfile CMD), and multiple code
# paths coordinate across those processes through the cache - the first-run
# onboarding runner (single migration/seed across the fleet), the semantic
# index rebuild lock, the SPOF scheduler's single-runner gate and the trust
# centre rate limiter. The default per-process LocMemCache would make each of
# those locks/counters local to one worker and silently ineffective.
# Redis is already a hard dependency (Channels layer), so this adds no new
# infrastructure. The test settings override this with a local-memory cache
# (the suite is single-process and must not need a live Redis).
# The cache only holds derived data, so an unreachable Redis must cost a cache
# miss, not a server error : core.cache.ResilientRedisCache degrades instead of
# raising, and the socket timeouts keep a silent Redis (network partition, host
# frozen) from holding every request for the kernel's connect timeout.
CACHES = {
    "default": {
        "BACKEND": "core.cache.ResilientRedisCache",
        "LOCATION": "redis://{host}:{port}/1".format(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
        ),
        "KEY_PREFIX": "cairn",
        "OPTIONS": {
            "socket_connect_timeout": 2,
            "socket_timeout": 2,
        },
    }
}

# Everything is logged to the console (stderr), where a container runtime
# collects it. Django's own default only writes there under DEBUG : in
# production an unhandled error left no traceback anywhere, only a 500 line in
# the access log. LOG_LEVEL filters the whole tree (DEBUG, INFO, WARNING, ERROR).
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "format": "%(asctime)s %(levelname)s %(name)s : %(message)s",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        # Replaces Django's DEBUG-only console handler : request errors
        # (django.request, with their traceback) are logged in production too.
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        # One line per SQL statement at DEBUG : only on explicit request.
        "django.db.backends": {"level": os.environ.get("LOG_LEVEL_SQL", "WARNING").upper()},
    },
}

# A URL typed without a scheme ("example.org") is completed with https, not
# http. That is the behaviour Django adopts from 6.0 on; this transitional
# setting gives it on the 5.2 LTS line, and is simply ignored by later versions.
FORMS_URLFIELD_ASSUME_HTTPS = True

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailAuthBackend",
    "accounts.backends.PasskeyAuthBackend",
    "accounts.backends.GroupPermissionBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "accounts.validators.ComplexityValidator"},
]

LANGUAGE_CODE = "en"

# Day-first numeric dates in English as well (core/formats/en/formats.py).
FORMAT_MODULE_PATH = ["core.formats"]

LANGUAGES = [
    ("en", "English"),
    ("fr", "Français"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "Europe/Paris"

USE_I18N = True

USE_THOUSAND_SEPARATOR = True

USE_TZ = True

STATIC_URL = "static/"

STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = BASE_DIR / "staticfiles"

# The front-end libraries are served from static/vendor/, never from a CDN. A
# Docker image mirrors them at build time; a direct install fetches whatever is
# missing on its first launch. Set to False to manage them yourself (an air-gapped
# install that copies the files in, or a build step that already ran
# `manage.py vendor_assets`).
VENDOR_ASSETS_AUTO_DOWNLOAD = os.environ.get(
    "VENDOR_ASSETS_AUTO_DOWNLOAD", "True"
).lower() in ("true", "1", "yes")

# Whether the About modal may ask GitHub for the latest published release. It is
# the only outbound call the interface makes, it fires only when the modal is
# opened, and the answer is cached. Set to False for an air-gapped deployment or
# where policy forbids the instance calling out.
UPDATE_CHECK_ENABLED = os.environ.get(
    "UPDATE_CHECK_ENABLED", "True"
).lower() in ("true", "1", "yes")

# Basemap of the maps on the scope, site and supplier pages. Off by default :
# the tiles are fetched by the reader's browser straight from the provider,
# which learns who looks at which place. Nothing leaves a browser unless the
# operator names a provider here : any XYZ tile URL, with its key when it
# needs one (OpenStreetMap's own service, which needs no account, is
# https://tile.openstreetmap.org/{z}/{x}/{y}.png).
MAP_TILE_URL = os.environ.get("MAP_TILE_URL", "").strip()
# Tiles to use under the dark theme. Empty : the tiles above are dimmed.
MAP_TILE_URL_DARK = os.environ.get("MAP_TILE_URL_DARK", "").strip()
# Geocoder the maps and the address fields ask for the position of an address
# (a Photon-compatible API, such as https://photon.komoot.io/api/ or one you
# host). Off by default : it is called by the reader's browser with the
# address as its query, so the address of a site or a supplier leaves the
# instance. Without it the maps only place what has a latitude and a
# longitude, and address fields have no type-ahead.
MAP_GEOCODER_URL = os.environ.get("MAP_GEOCODER_URL", "").strip()
# Credit line shown on the map, as the provider's terms require (HTML).
MAP_TILE_ATTRIBUTION = os.environ.get(
    "MAP_TILE_ATTRIBUTION",
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
)

# Content Security Policy (core/csp.py) : `enforce` (the default) makes the
# browser refuse what the policy does not allow, `report` only logs it in the
# browser console (to try the policy on an instance behind a proxy that
# rewrites pages), `off` sends no policy.
CSP_MODE = os.environ.get("CSP_MODE", "enforce").strip().lower()
if CSP_MODE not in ("enforce", "report", "off"):
    raise ImproperlyConfigured(f"CSP_MODE must be enforce, report or off, not {CSP_MODE!r}.")

# Seconds a worker process trusts its in-memory lifecycle definitions before
# checking the table again. A lifecycle edited in the administration is saved
# by one worker; this bounds how long the others keep applying the previous one.
LIFECYCLE_CACHE_TTL = float(os.environ.get("LIFECYCLE_CACHE_TTL", "5"))

MEDIA_URL = "media/"
# Uploaded files (evidence artefacts, proof-of-filing documents). MEDIA_ROOT
# moves them out of the code directory, onto a mounted volume for instance.
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT") or BASE_DIR / "media")

# Where `manage.py backup` writes its archives. In a container, mount a volume
# (or a host directory) there : an archive kept inside the container goes with
# it, and one kept on the same disk as the database goes with the disk.
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR") or BASE_DIR / "backups")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "mcp.api.authentication.OAuthTokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "context.api.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "context.api.renderers.StandardJSONRenderer",
    ],
    # Throttling is opt-in per view (public Trust Center read endpoints only,
    # via AnonRateThrottle); the authenticated app is not throttled. The public
    # gated-request form is a Django view rate-limited separately in its view.
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/hour",
        # The two OAuth endpoints anyone can call : registering a client
        # writes a row, the token endpoint checks a secret or a code.
        "oauth_register": "30/hour",
        "oauth_token": "300/hour",
    },
}

# Days an OAuth access token (MCP clients, API scripts) stays valid. A bearer
# token works for whoever holds it : it has to end. A client simply asks for a
# new one (client credentials), or sends its user through the consent page
# again (authorization code).
OAUTH_ACCESS_TOKEN_LIFETIME_DAYS = int(os.environ.get("OAUTH_ACCESS_TOKEN_LIFETIME_DAYS", "90"))
if OAUTH_ACCESS_TOKEN_LIFETIME_DAYS < 1:
    raise ImproperlyConfigured("OAUTH_ACCESS_TOKEN_LIFETIME_DAYS must be at least 1.")

# Email (notifications)
# Defaults to the console backend in DEBUG so no SMTP setup is needed in dev.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False").lower() in ("true", "1", "yes")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "cairn@localhost")
# Absolute URL prefix used in notification emails (e.g. https://grc.example.com).
SITE_URL = os.environ.get("SITE_URL", "")

# Trust Center
# Time-to-live (seconds) of a gated-document download link signed for an
# approved request. Default: 7 days.
TRUST_CENTER_DOWNLOAD_TTL = int(os.environ.get("TRUST_CENTER_DOWNLOAD_TTL", "604800"))
# Host that serves the public Trust Center on a dedicated domain. Empty disables
# dedicated-domain mode (the Trust Center is then reachable only at /trust/).
TRUST_CENTER_HOST = os.environ.get("TRUST_CENTER_HOST", "").strip().lower()
# Defensive: make sure the dedicated host is accepted so it does not 400 before
# the isolation middleware can route it. The operator should still add it (and
# its https origin) to ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS explicitly.
if TRUST_CENTER_HOST and TRUST_CENTER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(TRUST_CENTER_HOST)

# Simple JWT
# WebAuthn / Passkeys
# When not set, RPID and origin are derived from the request automatically.
WEBAUTHN_RP_ID = os.environ.get("WEBAUTHN_RP_ID")
WEBAUTHN_RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "Cairn")
WEBAUTHN_ORIGIN = os.environ.get("WEBAUTHN_ORIGIN")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# AI assistant ("Ask Cairn"): optional natural-language question mode in the
# command palette, backed by a pluggable LLM provider. Disabled by default;
# the rest of the application works normally without it. The default provider
# is Mistral AI (third-party, EU-hosted). "openai" targets OpenAI (ChatGPT) or
# any OpenAI-compatible endpoint via AI_ASSISTANT_BASE_URL. "anthropic" targets
# Claude through the native Messages API (set AI_ASSISTANT_MODEL to a Claude
# model id; no embeddings, so semantic search needs another provider). The
# self-hosted "ollama" provider stays selectable for those pointing at their
# own instance.
AI_ASSISTANT_ENABLED = os.environ.get("AI_ASSISTANT_ENABLED", "False").lower() in ("true", "1", "yes")
AI_ASSISTANT_PROVIDER = os.environ.get("AI_ASSISTANT_PROVIDER", "mistral")
AI_ASSISTANT_API_KEY = os.environ.get("AI_ASSISTANT_API_KEY", "")
# Empty by default: each provider falls back to its own endpoint (Mistral ->
# api.mistral.ai, openai -> api.openai.com, anthropic -> api.anthropic.com). Set
# it to target a custom OpenAI-compatible gateway (vLLM, LiteLLM, LocalAI,
# Together, Groq...).
AI_ASSISTANT_BASE_URL = os.environ.get("AI_ASSISTANT_BASE_URL", "")
AI_ASSISTANT_MODEL = os.environ.get("AI_ASSISTANT_MODEL", "mistral-small-latest")
AI_ASSISTANT_CONNECT_TIMEOUT = float(os.environ.get("AI_ASSISTANT_CONNECT_TIMEOUT", "2"))
AI_ASSISTANT_TIMEOUT = float(os.environ.get("AI_ASSISTANT_TIMEOUT", "30"))
AI_ASSISTANT_MAX_TOOL_ROUNDS = int(os.environ.get("AI_ASSISTANT_MAX_TOOL_ROUNDS", "3"))
AI_ASSISTANT_MAX_RECORDS_PER_TOOL = int(os.environ.get("AI_ASSISTANT_MAX_RECORDS_PER_TOOL", "5"))
# Cap on the completion length (Mistral / OpenAI / OpenAI-compatible backends).
AI_ASSISTANT_MAX_TOKENS = int(os.environ.get("AI_ASSISTANT_MAX_TOKENS", "1024"))
# Semantic search over requirement content (embeddings + in-Python cosine).
# Opt-in: build the index with `manage.py rebuild_semantic_index` after enabling.
AI_ASSISTANT_SEMANTIC_ENABLED = os.environ.get("AI_ASSISTANT_SEMANTIC_ENABLED", "False").lower() in ("true", "1", "yes")
AI_ASSISTANT_EMBED_MODEL = os.environ.get("AI_ASSISTANT_EMBED_MODEL", "mistral-embed")
# Ollama provider only: local instance URL, context window, and chain-of-thought
# during routing (thinking models such as qwen3). Ignored by the Mistral provider.
AI_ASSISTANT_OLLAMA_URL = os.environ.get("AI_ASSISTANT_OLLAMA_URL", "http://ollama:11434")
AI_ASSISTANT_NUM_CTX = int(os.environ.get("AI_ASSISTANT_NUM_CTX", "8192"))
AI_ASSISTANT_ROUTING_THINK = os.environ.get("AI_ASSISTANT_ROUTING_THINK", "False").lower() in ("true", "1", "yes")

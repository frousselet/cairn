# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import hashlib
import hmac
import secrets
import uuid
from urllib.parse import urlsplit

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _generate_client_id():
    return f"ogrc_{secrets.token_hex(16)}"


def _generate_client_secret():
    return secrets.token_urlsafe(48)


# Hosts a native application may be redirected to over plain http (RFC 8252,
# section 7.3) : the loopback interface of the user's own machine.
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")
# Schemes that run or read something in the browser instead of handing the
# authorization code to an application.
FORBIDDEN_REDIRECT_SCHEMES = ("javascript", "data", "vbscript", "file", "blob", "about", "view-source")
MAX_REDIRECT_URIS = 10


def redirect_uri_problem(uri):
    """Why ``uri`` cannot be registered as a redirect address, or ``None``.

    An authorization code is as good as the account it was issued for, and it
    is sent to this address. Accepted : ``https``, ``http`` on the loopback
    interface (a desktop client listening locally), or a private scheme an
    installed application registered (``cursor://``...). Refused : plain http
    to another machine, a scheme the browser itself interprets, a fragment,
    embedded credentials.
    """
    if not isinstance(uri, str) or not uri or len(uri) > 2000:
        return "must be a non-empty string of at most 2000 characters"
    if any(character.isspace() for character in uri):
        return "must not contain whitespace"
    try:
        parts = urlsplit(uri)
        host = parts.hostname
    except ValueError:
        return "is not a valid URI"
    scheme = parts.scheme.lower()
    if not scheme:
        return "must be an absolute URI"
    if scheme in FORBIDDEN_REDIRECT_SCHEMES:
        return f"uses the {scheme}: scheme, which a browser interprets itself"
    if parts.fragment:
        return "must not contain a fragment"
    if parts.username or parts.password:
        return "must not embed credentials"
    if scheme == "https":
        return None if host else "has no host"
    if scheme == "http":
        return None if host in LOOPBACK_HOSTS else "uses plain http to a host other than the loopback interface"
    return None


class OAuthApplication(models.Model):
    """OAuth 2.0 client credentials for MCP access, owned by a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Application name"), max_length=255)
    client_id = models.CharField(
        _("Client ID"),
        max_length=255,
        unique=True,
        default=_generate_client_id,
    )
    client_secret_hash = models.CharField(
        _("Client secret (hashed)"),
        max_length=128,
        blank=True,
        default="",
    )
    redirect_uris = models.TextField(
        _("Redirect URIs (JSON)"),
        blank=True,
        default="",
        help_text=_("JSON-encoded list of allowed redirect URIs for public clients."),
    )
    token_endpoint_auth_method = models.CharField(
        _("Token endpoint auth method"),
        max_length=20,
        default="client_secret_post",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oauth_applications",
        verbose_name=_("Owner"),
    )
    is_active = models.BooleanField(_("Active"), default=True)
    last_used_at = models.DateTimeField(_("Last used"), null=True, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("OAuth application")
        verbose_name_plural = _("OAuth applications")

    def __str__(self):
        return f"{self.name} ({self.client_id})"

    @staticmethod
    def hash_secret(raw_secret):
        return hashlib.sha256(raw_secret.encode()).hexdigest()

    def set_secret(self, raw_secret):
        self.client_secret_hash = self.hash_secret(raw_secret)

    def verify_secret(self, raw_secret):
        # Constant time : the comparison must not tell how much of it matched.
        return bool(self.client_secret_hash) and hmac.compare_digest(
            self.client_secret_hash, self.hash_secret(raw_secret or ""),
        )

    @property
    def is_public_client(self):
        return self.token_endpoint_auth_method == "none"

    def get_redirect_uris(self):
        if not self.redirect_uris:
            return []
        import json
        try:
            return json.loads(self.redirect_uris)
        except (json.JSONDecodeError, TypeError):
            return []

    def validate_redirect_uri(self, uri):
        """Whether an authorization code may be sent to ``uri``.

        Exact match against the addresses the application registered. An
        application that registered none (a client-credentials application,
        created from a profile) has no authorization-code flow at all : it
        used to accept any address, which let anyone have a code sent wherever
        they liked.
        """
        allowed = self.get_redirect_uris()
        return isinstance(uri, str) and uri in allowed and redirect_uri_problem(uri) is None


class OAuthAccessToken(models.Model):
    """OAuth 2.0 access tokens issued to MCP clients."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        OAuthApplication,
        on_delete=models.CASCADE,
        related_name="access_tokens",
        verbose_name=_("Application"),
    )
    token_hash = models.CharField(
        _("Token (hashed)"),
        max_length=128,
        unique=True,
        db_index=True,
    )
    # Who the token acts as : the person who consented (authorization code),
    # or the owner of the application (client credentials). Never inferred
    # from the application alone : a public client is shared by everyone who
    # authorizes it, and its tokens used to act as whoever authorized it first.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="oauth_access_tokens",
        verbose_name=_("User"),
    )
    expires_at = models.DateTimeField(_("Expires at"))
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("OAuth access token")
        verbose_name_plural = _("OAuth access tokens")

    def __str__(self):
        return f"Token for {self.application.name}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def acting_user(self):
        """The account the token acts as (see ``user``). A token issued before
        tokens carried their user belongs to a confidential application, and
        acts as its owner."""
        return self.user or self.application.user

    @staticmethod
    def hash_token(raw_token):
        # Use a computationally expensive key-derivation function (PBKDF2)
        # instead of a single fast SHA-256 hash to better protect stored
        # access token hashes against brute-force attacks.
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            raw_token.encode("utf-8"),
            b"mcp_oauth_access_token_salt_v1",
            100_000,
        )
        return dk.hex()

    @classmethod
    def create_token(cls, application, user=None):
        """Create an access token acting as ``user`` and return (instance, raw_token).

        ``user`` defaults to the owner of the application (client credentials).
        The token lives ``OAUTH_ACCESS_TOKEN_LIFETIME_DAYS`` days : a bearer
        token that never expires stays usable for ever by whoever copied it.
        """
        raw_token = secrets.token_urlsafe(48)
        token = cls(
            application=application,
            user=user or application.user,
            token_hash=cls.hash_token(raw_token),
            expires_at=timezone.now() + timezone.timedelta(days=settings.OAUTH_ACCESS_TOKEN_LIFETIME_DAYS),
        )
        token.save()
        return token, raw_token

    @property
    def expires_in(self):
        """Seconds left, for the token response."""
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))


class OAuthAuthorizationCode(models.Model):
    """OAuth 2.0 authorization codes for the Authorization Code + PKCE flow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code_hash = models.CharField(
        _("Code (hashed)"),
        max_length=64,
        unique=True,
        db_index=True,
    )
    client_id = models.CharField(_("Client ID"), max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oauth_authorization_codes",
        verbose_name=_("User"),
    )
    redirect_uri = models.CharField(_("Redirect URI"), max_length=2048)
    code_challenge = models.CharField(_("PKCE code challenge"), max_length=128)
    code_challenge_method = models.CharField(
        _("PKCE code challenge method"),
        max_length=10,
        default="S256",
    )
    scope = models.CharField(_("Scope"), max_length=512, blank=True, default="")
    expires_at = models.DateTimeField(_("Expires at"))
    used = models.BooleanField(_("Used"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("OAuth authorization code")
        verbose_name_plural = _("OAuth authorization codes")

    def __str__(self):
        return f"Auth code for {self.client_id} (user: {self.user})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @staticmethod
    def hash_code(raw_code):
        return hashlib.sha256(raw_code.encode()).hexdigest()

    @classmethod
    def create_code(cls, client_id, user, redirect_uri, code_challenge, code_challenge_method, scope="", lifetime_seconds=600):
        """Create a new authorization code and return (instance, raw_code)."""
        raw_code = secrets.token_urlsafe(48)
        code = cls(
            code_hash=cls.hash_code(raw_code),
            client_id=client_id,
            user=user,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            scope=scope,
            expires_at=timezone.now() + timezone.timedelta(seconds=lifetime_seconds),
        )
        code.save()
        return code, raw_code

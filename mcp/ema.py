# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Enterprise Managed Auth : an identity assertion of the organization's IdP exchanged for a token.

The identity provider of the organization (or Claude, on its behalf) signs an
Identity Assertion JWT Authorization Grant (ID-JAG) for a person; the client
posts it to the token endpoint with ``grant_type=urn:ietf:params:oauth:
grant-type:jwt-bearer`` and receives an access token acting as that person,
with no consent page (MCP extension
``io.modelcontextprotocol/enterprise-managed-authorization``,
draft-ietf-oauth-identity-assertion-authz-grant).

Off until ``MCP_EMA_ISSUER`` names the one issuer this instance trusts. The
assertion is then checked in this order, and any failure answers
``invalid_grant`` :

1. its ``iss`` is that issuer, exactly, before any key is fetched;
2. the keys come from the issuer's OpenID configuration (whose ``issuer``
   must be that same string) and its ``jwks_uri``, never from the assertion;
3. the signature is ES256 or RS256, nothing else;
4. its ``typ`` is ``oauth-id-jag+jwt``;
5. its ``aud`` is the issuer of this authorization server, alone;
6. its ``client_id`` is the client that authenticated the request;
7. it names a person (``sub``, and ``email`` for the account);
8. it is in its validity window, with sixty seconds of leeway;
9. its ``jti`` was never exchanged before.

The person is the active account whose email is the assertion's ``email``,
holding ``system.mcp.access``. The token lasts
``MCP_EMA_ACCESS_TOKEN_LIFETIME_HOURS`` and comes with no refresh token.
"""

from datetime import UTC, datetime, timedelta

import httpx
import jwt
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
GRANT_PROFILE = "urn:ietf:params:oauth:grant-profile:id-jag"
EXTENSION = "io.modelcontextprotocol/enterprise-managed-authorization"
ASSERTION_TYPE = "oauth-id-jag+jwt"
ALGORITHMS = ["ES256", "RS256"]
LEEWAY = 60
HTTP_TIMEOUT = 10

_jwk_clients = {}


class AssertionRefused(Exception):
    """The assertion cannot be exchanged : ``error`` is the OAuth error code."""

    def __init__(self, description, error="invalid_grant"):
        super().__init__(description)
        self.error = error
        self.description = description


def enabled():
    return bool(settings.MCP_EMA_ISSUER)


def _keys_for(issuer):
    """The JWK client of ``issuer``, from its OpenID configuration."""
    client = _jwk_clients.get(issuer)
    if client is not None:
        return client
    try:
        response = httpx.get(f"{issuer.rstrip('/')}/.well-known/openid-configuration", timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        configuration = response.json()
    except (httpx.HTTPError, ValueError):
        raise AssertionRefused("The configuration of the issuer could not be read.") from None
    if not isinstance(configuration, dict):
        raise AssertionRefused("The configuration of the issuer could not be read.")
    jwks_uri = configuration.get("jwks_uri")
    if configuration.get("issuer") != issuer or not isinstance(jwks_uri, str) or not jwks_uri.startswith("https://"):
        raise AssertionRefused("The configuration of the issuer does not name it or its keys.")
    client = jwt.PyJWKClient(jwks_uri, cache_keys=True, lifespan=300, timeout=HTTP_TIMEOUT)
    _jwk_clients[issuer] = client
    return client


def verify(assertion, *, client_id, audience, resource_url):
    """The claims of ``assertion`` once every check passed; :class:`AssertionRefused` otherwise."""
    if not isinstance(assertion, str) or assertion.count(".") != 2:
        raise AssertionRefused("The assertion is not a JWT.")
    try:
        header = jwt.get_unverified_header(assertion)
        unverified = jwt.decode(assertion, options={"verify_signature": False})
    except jwt.PyJWTError:
        raise AssertionRefused("The assertion is not a JWT.") from None

    issuer = settings.MCP_EMA_ISSUER
    if unverified.get("iss") != issuer:
        raise AssertionRefused("The assertion was not issued by the trusted issuer.")
    if header.get("alg") not in ALGORITHMS:
        raise AssertionRefused("The assertion is not signed with ES256 or RS256.")
    if header.get("typ") != ASSERTION_TYPE:
        raise AssertionRefused("The assertion is not an identity assertion grant.")

    try:
        key = _keys_for(issuer).get_signing_key_from_jwt(assertion)
        claims = jwt.decode(
            assertion, key.key, algorithms=ALGORITHMS, issuer=issuer, audience=audience, leeway=LEEWAY,
            options={"require": ["iss", "sub", "aud", "exp", "iat", "jti"]},
        )
    except AssertionRefused:
        raise
    except jwt.PyJWTError:
        raise AssertionRefused("The assertion failed verification.") from None

    aud = claims.get("aud")
    if isinstance(aud, list) and len(aud) != 1:
        raise AssertionRefused("The assertion must name this server alone as its audience.")
    if claims.get("client_id") != client_id:
        raise AssertionRefused("The assertion was issued to another client.")
    resource = claims.get("resource")
    if resource is not None:
        resources = resource if isinstance(resource, list) else [resource]
        if resource_url not in resources:
            raise AssertionRefused("The assertion is for another resource.")
    if not str(claims.get("sub") or "").strip():
        raise AssertionRefused("The assertion names no subject.")
    return claims


def spend(claims):
    """Record the ``jti`` of ``claims`` : refused when it was exchanged before."""
    from mcp.models import OAuthAssertionUse

    OAuthAssertionUse.objects.filter(expires_at__lt=timezone.now()).delete()
    expires = datetime.fromtimestamp(int(claims["exp"]), tz=UTC) + timedelta(seconds=LEEWAY)
    try:
        with transaction.atomic():
            OAuthAssertionUse.objects.create(issuer=claims["iss"], jti=str(claims["jti"])[:255], expires_at=expires)
    except IntegrityError:
        raise AssertionRefused("The assertion was already exchanged.") from None


def person(claims):
    """The account the assertion names, by its email."""
    from accounts.models import User

    email = str(claims.get("email") or "").strip()
    if not email:
        raise AssertionRefused("The assertion carries no email to find the account by.")
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        raise AssertionRefused("No active account has the email of the assertion.")
    if not user.is_superuser and not user.has_perm("system.mcp.access"):
        raise AssertionRefused("The account does not have MCP access.", error="access_denied")
    return user


def lifetime():
    return timedelta(hours=settings.MCP_EMA_ACCESS_TOKEN_LIFETIME_HOURS)


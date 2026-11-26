# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Enterprise Managed Auth : an identity assertion (ID-JAG) of the trusted
issuer exchanged for an access token, and every check that refuses one."""

import time
import uuid
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from mcp import ema
from mcp.models import OAuthAccessToken, OAuthApplication
from mcp.models.oauth import _generate_client_secret

pytestmark = pytest.mark.django_db

ISSUER = "https://idp.example.com/oauth2/default"
AS_ISSUER = "http://testserver"
TOKEN_URL = "/api/v1/oauth/token/"


@pytest.fixture
def key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def trusted(settings, key, monkeypatch):
    settings.MCP_EMA_ISSUER = ISSUER
    monkeypatch.setattr(ema, "_keys_for", lambda issuer: SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())
    ))
    return key


@pytest.fixture
def application():
    owner = UserFactory()
    secret = _generate_client_secret()
    app = OAuthApplication(name="Claude", user=owner)
    app.set_secret(secret)
    app.save()
    return app, secret


@pytest.fixture
def person():
    user = UserFactory(email="ada@voltara.example")
    group = GroupFactory()
    group.permissions.add(PermissionFactory(codename="system.mcp.access"))
    group.users.add(user)
    return user


def _assertion(key, request_client_id, *, headers=None, algorithm="ES256", **overrides):
    now = int(time.time())
    claims = {
        "iss": ISSUER, "sub": "00u1", "email": "ada@voltara.example", "aud": AS_ISSUER,
        "client_id": request_client_id,
        "iat": now, "nbf": now, "exp": now + 60, "jti": str(uuid.uuid4()),
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=algorithm, headers={"typ": "oauth-id-jag+jwt", **(headers or {})})


def _exchange(client, client_id, secret, assertion, **extra):
    data = {"grant_type": ema.GRANT_TYPE, "assertion": assertion, "client_id": client_id,
            "client_secret": secret, **extra}
    return client.post(TOKEN_URL, data=data)


class TestDisabledByDefault:
    def test_the_grant_is_not_offered(self, client, application, key):
        app, secret = application
        response = _exchange(client, app.client_id, secret, _assertion(key, app.client_id))
        assert response.status_code == 400
        assert response.json()["error"] == "unsupported_grant_type"
        metadata = client.get("/.well-known/oauth-authorization-server").json()
        assert ema.GRANT_TYPE not in metadata["grant_types_supported"]
        assert "authorization_grant_profiles_supported" not in metadata


class TestExchange:
    def test_a_valid_assertion_signs_its_person_in(self, client, trusted, application, person):
        app, secret = application
        response = _exchange(client, app.client_id, secret, _assertion(trusted, app.client_id),
                             resource="http://testserver/api/v1/mcp", scope="claudeai")
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["token_type"] == "Bearer"
        assert "refresh_token" not in body
        assert 8 * 3600 - 60 <= body["expires_in"] <= 8 * 3600
        token = OAuthAccessToken.objects.get(application=app)
        assert token.user == person

    def test_the_metadata_offers_the_grant(self, client, trusted):
        metadata = client.get("/.well-known/oauth-authorization-server").json()
        assert ema.GRANT_TYPE in metadata["grant_types_supported"]
        assert metadata["authorization_grant_profiles_supported"] == [ema.GRANT_PROFILE]
        assert metadata["issuer"] == AS_ISSUER

    def test_an_assertion_is_exchanged_once(self, client, trusted, application, person):
        app, secret = application
        assertion = _assertion(trusted, app.client_id)
        assert _exchange(client, app.client_id, secret, assertion).status_code == 200
        again = _exchange(client, app.client_id, secret, assertion)
        assert again.status_code == 400 and again.json()["error"] == "invalid_grant"

    @pytest.mark.parametrize("overrides", [
        {"iss": "https://other.example.com"},
        {"aud": "https://elsewhere.example.com"},
        {"aud": [AS_ISSUER, "https://elsewhere.example.com"]},
        {"client_id": "another-client"},
        {"exp": int(time.time()) - 3600, "iat": int(time.time()) - 7200, "nbf": int(time.time()) - 7200},
        {"iat": int(time.time()) + 3600},
        {"jti": None},
        {"sub": None},
        {"resource": "https://another.example.com/mcp"},
    ])
    def test_a_claim_out_of_place_is_refused(self, client, trusted, application, person, overrides):
        app, secret = application
        response = _exchange(client, app.client_id, secret, _assertion(trusted, app.client_id, **overrides))
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_grant"
        assert not OAuthAccessToken.objects.exists()

    def test_another_type_is_refused(self, client, trusted, application, person):
        app, secret = application
        response = _exchange(client, app.client_id, secret,
                             _assertion(trusted, app.client_id, headers={"typ": "JWT"}))
        assert response.json()["error"] == "invalid_grant"

    def test_a_symmetric_signature_is_refused(self, client, trusted, application, person):
        app, secret = application
        forged = _assertion("a-shared-secret-of-at-least-thirty-two-bytes!!", app.client_id, algorithm="HS256")
        response = _exchange(client, app.client_id, secret, forged)
        assert response.json()["error"] == "invalid_grant"

    def test_a_signature_of_another_key_is_refused(self, client, trusted, application, person):
        app, secret = application
        other = ec.generate_private_key(ec.SECP256R1())
        response = _exchange(client, app.client_id, secret, _assertion(other, app.client_id))
        assert response.json()["error"] == "invalid_grant"

    def test_the_client_must_authenticate(self, client, trusted, application, person):
        app, _secret = application
        response = _exchange(client, app.client_id, "wrong", _assertion(trusted, app.client_id))
        assert response.status_code == 401 and response.json()["error"] == "invalid_client"

    def test_another_resource_is_refused(self, client, trusted, application, person):
        app, secret = application
        response = _exchange(client, app.client_id, secret, _assertion(trusted, app.client_id),
                             resource="https://another.example.com/mcp")
        assert response.json()["error"] == "invalid_target"

    def test_the_person_must_exist_and_have_access(self, client, trusted, application, person):
        app, secret = application
        unknown = _exchange(client, app.client_id, secret,
                            _assertion(trusted, app.client_id, email="nobody@voltara.example"))
        assert unknown.json()["error"] == "invalid_grant"
        UserFactory(email="reader@voltara.example")
        denied = _exchange(client, app.client_id, secret,
                           _assertion(trusted, app.client_id, email="reader@voltara.example"))
        assert denied.status_code == 403 and denied.json()["error"] == "access_denied"


class TestIssuerKeys:
    def test_a_configuration_that_names_another_issuer_is_refused(self, settings, monkeypatch):
        settings.MCP_EMA_ISSUER = ISSUER
        ema._jwk_clients.clear()
        monkeypatch.setattr(ema.httpx, "get", lambda url, timeout: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"issuer": "https://evil.example.com", "jwks_uri": "https://evil.example.com/keys"},
        ))
        with pytest.raises(ema.AssertionRefused):
            ema._keys_for(ISSUER)
        assert ISSUER not in ema._jwk_clients

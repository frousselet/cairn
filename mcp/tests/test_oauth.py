# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Tests for OAuth models and token endpoint."""

import json

import pytest

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from mcp.models import OAuthAccessToken, OAuthApplication
from mcp.models.oauth import _generate_client_id, _generate_client_secret

pytestmark = pytest.mark.django_db


class TestOAuthApplication:
    def test_create_application(self):
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test App", user=user)
        app.set_secret(raw_secret)
        app.save()
        assert app.client_id.startswith("ogrc_")
        assert app.verify_secret(raw_secret)
        assert not app.verify_secret("wrong_secret")

    def test_client_id_generation(self):
        cid = _generate_client_id()
        assert cid.startswith("ogrc_")
        assert len(cid) > 10

    def test_hash_secret_deterministic(self):
        secret = "test_secret_123"
        h1 = OAuthApplication.hash_secret(secret)
        h2 = OAuthApplication.hash_secret(secret)
        assert h1 == h2

    def test_different_secrets_different_hashes(self):
        h1 = OAuthApplication.hash_secret("secret1")
        h2 = OAuthApplication.hash_secret("secret2")
        assert h1 != h2


class TestOAuthAccessToken:
    def test_create_token(self):
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        token_obj, raw_token = OAuthAccessToken.create_token(app)
        assert raw_token
        assert not token_obj.is_expired
        assert token_obj.application == app

    def test_token_hash_lookup(self):
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        token_obj, raw_token = OAuthAccessToken.create_token(app)
        token_hash = OAuthAccessToken.hash_token(raw_token)
        found = OAuthAccessToken.objects.get(token_hash=token_hash)
        assert found.pk == token_obj.pk

    def test_a_token_ends(self):
        """A bearer token works for whoever holds it : it has a lifetime."""
        from datetime import timedelta

        from django.conf import settings
        from django.utils import timezone

        user = UserFactory()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(_generate_client_secret())
        app.save()

        token_obj, _ = OAuthAccessToken.create_token(app)
        assert not token_obj.is_expired
        lifetime = token_obj.expires_at - timezone.now()
        assert timedelta(days=settings.OAUTH_ACCESS_TOKEN_LIFETIME_DAYS - 1) < lifetime
        assert lifetime <= timedelta(days=settings.OAUTH_ACCESS_TOKEN_LIFETIME_DAYS)
        token_obj.expires_at = timezone.now() - timedelta(seconds=1)
        assert token_obj.is_expired

    def test_a_token_acts_as_the_owner_of_a_confidential_application(self):
        user = UserFactory()
        app = OAuthApplication(name="Script", user=user)
        app.set_secret(_generate_client_secret())
        app.save()
        token_obj, _ = OAuthAccessToken.create_token(app)
        assert token_obj.user == user and token_obj.acting_user == user

    def test_a_secret_is_compared_in_constant_time_and_never_matches_empty(self):
        app = OAuthApplication(name="Public", user=UserFactory())
        assert app.client_secret_hash == ""
        assert not app.verify_secret("")
        assert not app.verify_secret(None)


class TestOAuthTokenEndpoint:
    def _setup_user_with_mcp_access(self):
        user = UserFactory()
        perm = PermissionFactory(codename="system.mcp.access")
        group = GroupFactory()
        group.permissions.add(perm)
        group.users.add(user)
        return user

    def test_token_endpoint_success(self, client):
        user = self._setup_user_with_mcp_access()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": app.client_id,
                "client_secret": raw_secret,
            }),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert 0 < data["expires_in"] <= 90 * 86400

    def test_token_endpoint_invalid_grant_type(self, client):
        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({"grant_type": "password"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_token_endpoint_invalid_client(self, client):
        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": "fake_id",
                "client_secret": "fake_secret",
            }),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_token_endpoint_wrong_secret(self, client):
        user = self._setup_user_with_mcp_access()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": app.client_id,
                "client_secret": "wrong_secret",
            }),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_token_endpoint_no_mcp_permission(self, client):
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": app.client_id,
                "client_secret": raw_secret,
            }),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_token_endpoint_inactive_app(self, client):
        user = self._setup_user_with_mcp_access()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user, is_active=False)
        app.set_secret(raw_secret)
        app.save()

        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": app.client_id,
                "client_secret": raw_secret,
            }),
            content_type="application/json",
        )
        assert response.status_code == 401


class TestOAuthApplicationManagement:
    def _setup_user_with_oauth_perms(self):
        user = UserFactory()
        perms = [
            PermissionFactory(codename="system.oauth.create"),
            PermissionFactory(codename="system.oauth.read"),
            PermissionFactory(codename="system.oauth.delete"),
        ]
        group = GroupFactory()
        group.permissions.add(*perms)
        group.users.add(user)
        return user

    def test_create_application(self, client):
        user = self._setup_user_with_oauth_perms()
        client.force_login(user)
        response = client.post(
            "/api/v1/oauth/applications/",
            data=json.dumps({"name": "My App"}),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "client_id" in data["data"]
        assert "client_secret" in data["data"]

    def test_list_applications(self, client):
        user = self._setup_user_with_oauth_perms()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        client.force_login(user)
        response = client.get("/api/v1/oauth/applications/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        # client_secret should NOT be in list response
        assert "client_secret" not in data["data"][0]

    def test_delete_application(self, client):
        user = self._setup_user_with_oauth_perms()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        client.force_login(user)
        response = client.delete(f"/api/v1/oauth/applications/{app.id}/")
        assert response.status_code == 204
        assert not OAuthApplication.objects.filter(pk=app.pk).exists()

    def test_cannot_see_other_users_apps(self, client):
        user1 = self._setup_user_with_oauth_perms()
        user2 = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Other User App", user=user2)
        app.set_secret(raw_secret)
        app.save()

        client.force_login(user1)
        response = client.get("/api/v1/oauth/applications/")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 0

    def test_no_permission_blocked(self, client):
        user = UserFactory()
        client.force_login(user)
        response = client.post(
            "/api/v1/oauth/applications/",
            data=json.dumps({"name": "Test"}),
            content_type="application/json",
        )
        assert response.status_code == 403


class TestOAuthConsent:
    """The consent page (``/authorize``) and what answering it redirects to."""

    REDIRECT = "https://client.example/callback"

    def _app(self, user):
        import json

        app = OAuthApplication(name="Desk client", user=user, redirect_uris=json.dumps([self.REDIRECT]))
        app.set_secret(_generate_client_secret())
        app.save()
        return app

    def _form(self, app, redirect_uri, action):
        return {
            "client_id": app.client_id, "redirect_uri": redirect_uri, "code_challenge": "c" * 43,
            "code_challenge_method": "S256", "state": "xyz", "action": action,
        }

    def test_the_consent_page_may_be_answered_by_a_redirect_to_the_client(self, client):
        """Its form posts to the instance and is redirected to the client's
        own address : ``form-action 'self'`` is left out of its policy, and
        only of its policy."""
        user = _mcp_user()
        app = self._app(user)
        client.force_login(user)
        response = client.get("/authorize", {
            "response_type": "code", "client_id": app.client_id, "redirect_uri": self.REDIRECT,
            "code_challenge": "c" * 43, "code_challenge_method": "S256",
        })
        assert response.status_code == 200
        policy = response["Content-Security-Policy"]
        assert "form-action" not in policy
        assert "script-src 'self' 'nonce-" in policy

    def test_a_refusal_is_sent_to_the_registered_address(self, client):
        user = UserFactory()
        app = self._app(user)
        client.force_login(user)
        response = client.post("/authorize", self._form(app, self.REDIRECT, "deny"))
        assert response.status_code == 302
        assert response["Location"].startswith(self.REDIRECT + "?")
        assert "error=access_denied" in response["Location"]

    def test_a_refusal_is_not_sent_to_an_address_the_form_was_given(self, client):
        """The refusal used to redirect before the address was checked : a
        tampered consent form could send its user anywhere."""
        user = UserFactory()
        app = self._app(user)
        client.force_login(user)
        response = client.post("/authorize", self._form(app, "https://evil.example/landing", "deny"))
        assert response.status_code == 400
        assert "Location" not in response

    def test_a_refusal_for_an_unknown_client_goes_nowhere(self, client):
        user = UserFactory()
        client.force_login(user)
        form = {"client_id": "ogrc_unknown", "redirect_uri": "https://evil.example/", "action": "deny", "state": "s"}
        response = client.post("/authorize", form)
        assert response.status_code == 400
        assert "Location" not in response


def _pkce():
    import base64
    import hashlib
    import secrets

    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _mcp_user():
    user = UserFactory()
    perm = PermissionFactory(codename="system.mcp.access")
    group = GroupFactory()
    group.permissions.add(perm)
    group.users.add(user)
    return user


class TestAuthorizationCodeFlow:
    """Dynamic registration, consent, code, token : end to end."""

    REDIRECT = "http://127.0.0.1:53682/callback"

    def _register(self, client, **overrides):
        payload = {"client_name": "Desk client", "redirect_uris": [self.REDIRECT], **overrides}
        return client.post("/api/v1/oauth/register/", data=json.dumps(payload), content_type="application/json")

    def _token_for(self, user, client_id):
        """Run consent and code exchange as ``user`` : the raw token response."""
        from urllib.parse import parse_qs, urlsplit

        from django.test import Client

        browser = Client()
        browser.force_login(user)
        verifier, challenge = _pkce()
        form = {
            "client_id": client_id, "redirect_uri": self.REDIRECT, "code_challenge": challenge,
            "code_challenge_method": "S256", "state": "s", "action": "approve",
        }
        approved = browser.post("/authorize", form)
        assert approved.status_code == 302, approved.content
        code = parse_qs(urlsplit(approved["Location"]).query)["code"][0]
        return Client().post("/api/v1/oauth/token/", data=json.dumps({
            "grant_type": "authorization_code", "code": code, "client_id": client_id,
            "redirect_uri": self.REDIRECT, "code_verifier": verifier,
        }), content_type="application/json"), code, verifier

    def _whoami(self, raw_token):
        from rest_framework.test import APIRequestFactory

        from mcp.api.authentication import OAuthTokenAuthentication

        request = APIRequestFactory().get("/api/v1/mcp", HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        user, _token = OAuthTokenAuthentication().authenticate(request)
        return user

    def test_a_token_acts_as_the_person_who_consented(self, client):
        """The flaw this closes : a public client is shared, and its tokens
        acted as whoever authorized it first. A second user who authorized
        the same client received a token acting as the first."""
        alice, bob = _mcp_user(), _mcp_user()
        client_id = self._register(client).json()["client_id"]

        first, _code, _verifier = self._token_for(alice, client_id)
        second, _code, _verifier = self._token_for(bob, client_id)
        assert first.status_code == 200 and second.status_code == 200

        assert self._whoami(first.json()["access_token"]) == alice
        assert self._whoami(second.json()["access_token"]) == bob
        # And the first token did not change hands when the second was issued.
        assert self._whoami(first.json()["access_token"]) == alice

    def test_a_code_is_spent_once(self, client):
        user = _mcp_user()
        client_id = self._register(client).json()["client_id"]
        first, code, verifier = self._token_for(user, client_id)
        assert first.status_code == 200
        again = client.post("/api/v1/oauth/token/", data=json.dumps({
            "grant_type": "authorization_code", "code": code, "client_id": client_id,
            "redirect_uri": self.REDIRECT, "code_verifier": verifier,
        }), content_type="application/json")
        assert again.status_code == 400
        assert again.json()["error"] == "invalid_grant"

    def test_an_account_without_mcp_access_is_not_offered_consent(self, client):
        client_id = self._register(client).json()["client_id"]
        client.force_login(UserFactory())
        _verifier, challenge = _pkce()
        response = client.get("/authorize", {
            "response_type": "code", "client_id": client_id, "redirect_uri": self.REDIRECT,
            "code_challenge": challenge, "code_challenge_method": "S256",
        })
        assert response.status_code == 403

    def test_the_consent_page_says_where_the_access_goes(self, client):
        client_id = self._register(client, client_name="Trusted assistant").json()["client_id"]
        client.force_login(_mcp_user())
        _verifier, challenge = _pkce()
        html = client.get("/authorize", {
            "response_type": "code", "client_id": client_id, "redirect_uri": self.REDIRECT,
            "code_challenge": challenge, "code_challenge_method": "S256",
        }).content.decode()
        assert "Trusted assistant" in html
        assert "127.0.0.1:53682" in html

    def test_an_expired_token_is_refused(self, client):
        from datetime import timedelta

        from django.utils import timezone
        from rest_framework.exceptions import AuthenticationFailed

        user = _mcp_user()
        client_id = self._register(client).json()["client_id"]
        response, _code, _verifier = self._token_for(user, client_id)
        raw = response.json()["access_token"]
        OAuthAccessToken.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        with pytest.raises(AuthenticationFailed, match="expired"):
            self._whoami(raw)


class TestClientRegistration:
    """Registration is open to anyone : what it accepts decides where an
    authorization code can be sent."""

    def _register(self, client, redirect_uris, **extra):
        return client.post(
            "/api/v1/oauth/register/",
            data=json.dumps({"client_name": "Client", "redirect_uris": redirect_uris, **extra}),
            content_type="application/json",
        )

    @pytest.mark.parametrize("uri", [
        "https://app.example/callback",
        "http://localhost:8123/callback",
        "http://127.0.0.1/callback",
        "http://[::1]:9000/cb",
        "cursor://anysphere.cursor-retrieval/oauth/callback",
    ])
    def test_an_address_a_code_may_go_to_is_accepted(self, client, uri):
        response = self._register(client, [uri])
        assert response.status_code == 201, response.content
        app = OAuthApplication.objects.get(client_id=response.json()["client_id"])
        assert app.validate_redirect_uri(uri)

    @pytest.mark.parametrize("uris", [
        [],
        ["http://evil.example/callback"],
        ["javascript:alert(1)"],
        ["data:text/html,<script>1</script>"],
        ["https://user:secret@app.example/cb"],
        ["https://app.example/cb#fragment"],
        ["/relative/path"],
        [""],
        [42],
        ["https://app.example/cb", "http://evil.example/cb"],
        [f"https://app.example/{index}" for index in range(11)],
    ])
    def test_an_address_a_code_must_not_go_to_is_refused(self, client, uris):
        before = OAuthApplication.objects.count()
        response = self._register(client, uris)
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_redirect_uri"
        assert OAuthApplication.objects.count() == before

    def test_a_registered_client_is_always_public(self, client):
        """It cannot ask to be a confidential client with an empty secret."""
        response = self._register(client, ["https://app.example/cb"], token_endpoint_auth_method="client_secret_post")
        app = OAuthApplication.objects.get(client_id=response.json()["client_id"])
        assert app.is_public_client and response.json()["token_endpoint_auth_method"] == "none"
        assert not app.verify_secret("")

    def test_an_application_with_no_registered_address_has_no_code_flow(self):
        """It used to accept any address ("legacy") : a code could be sent anywhere."""
        app = OAuthApplication(name="Script", user=UserFactory())
        app.set_secret(_generate_client_secret())
        app.save()
        assert not app.validate_redirect_uri("https://anything.example/cb")
        assert not app.validate_redirect_uri("")
        assert not app.validate_redirect_uri(None)

    def test_only_the_exact_address_matches(self, client):
        response = self._register(client, ["https://app.example/callback"])
        app = OAuthApplication.objects.get(client_id=response.json()["client_id"])
        assert not app.validate_redirect_uri("https://app.example/callback/extra")
        assert not app.validate_redirect_uri("https://app.example.evil.test/callback")
        assert not app.validate_redirect_uri("https://app.example/callback?x=1")

    def test_the_open_endpoints_are_rate_limited(self):
        from django.conf import settings

        from mcp.api.views_oauth import OAuthRegisterThrottle, OAuthRegisterView, OAuthTokenThrottle, OAuthTokenView

        assert OAuthRegisterView.throttle_classes == [OAuthRegisterThrottle]
        assert OAuthTokenView.throttle_classes == [OAuthTokenThrottle]
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        assert rates["oauth_register"] and rates["oauth_token"]


class TestExistingTokensMigration:
    """What migration 0004 does to the tokens issued before it."""

    def test_public_client_tokens_are_revoked_and_the_others_bound_and_bounded(self):
        from datetime import timedelta
        from importlib import import_module

        from django.apps import apps
        from django.conf import settings
        from django.utils import timezone

        owner = UserFactory()
        confidential = OAuthApplication(name="Script", user=owner)
        confidential.set_secret(_generate_client_secret())
        confidential.save()
        public = OAuthApplication.objects.create(name="Desk", user=owner, token_endpoint_auth_method="none")
        forever = timezone.now() + timedelta(days=36500)
        kept = OAuthAccessToken.objects.create(application=confidential, token_hash="a" * 64, expires_at=forever)
        OAuthAccessToken.objects.create(application=public, token_hash="b" * 64, expires_at=forever)

        import_module("mcp.migrations.0004_oauth_token_user").bind_and_expire(apps, None)

        assert list(OAuthAccessToken.objects.values_list("pk", flat=True)) == [kept.pk]
        kept.refresh_from_db()
        assert kept.user == owner
        assert kept.expires_at <= timezone.now() + timedelta(days=settings.OAUTH_ACCESS_TOKEN_LIFETIME_DAYS)

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""What an instance does when nobody configured anything.

The safe behaviour is the default one, and the unsafe one is an explicit
choice of the operator : these tests read the settings as a fresh process
loads them, with and without the relevant variables.
"""

import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from core.downloads import OPAQUE, safe_content_type


def _settings(names, **environment):
    """The value of ``names`` in a fresh process, with ``environment`` set."""
    env = {key: value for key, value in os.environ.items() if key not in (
        "DEBUG", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "SESSION_COOKIE_AGE",
        "MAP_TILE_URL", "MAP_GEOCODER_URL", "OAUTH_ACCESS_TOKEN_LIFETIME_DAYS", "DJANGO_SETTINGS_MODULE",
        "MCP_EMA_ISSUER", "MCP_EMA_ACCESS_TOKEN_LIFETIME_HOURS",
    )}
    env.update({"SECRET_KEY": "a-key-for-this-test-only-never-used-anywhere-else", **environment})
    code = "import core.settings as s; print(repr([getattr(s, n) for n in %r]))" % (list(names),)
    result = subprocess.run(  # noqa: S603 - the project's own settings, fixed code
        [sys.executable, "-c", code], cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr[-1500:]
    return eval(result.stdout.strip().splitlines()[-1])  # noqa: S307 - our own repr of a list of literals


class TestDefaults:
    def test_cookies_only_travel_over_https(self):
        assert _settings(["SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE"]) == [True, True]

    def test_an_operator_can_run_without_tls_but_has_to_say_so(self):
        assert _settings(["SESSION_COOKIE_SECURE"], SESSION_COOKIE_SECURE="False") == [False]

    def test_a_development_instance_works_over_http(self):
        assert _settings(["SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE"], DEBUG="True") == [False, False]

    def test_a_session_lasts_a_working_day(self):
        assert _settings(["SESSION_COOKIE_AGE"]) == [12 * 60 * 60]
        assert _settings(["SESSION_COOKIE_AGE"], SESSION_COOKIE_AGE="3600") == [3600]

    def test_no_browser_is_sent_to_an_outside_service(self):
        """Map tiles and geocoding are fetched by the reader's browser from a
        third party : off until the operator names one."""
        assert _settings(["MAP_TILE_URL", "MAP_GEOCODER_URL"]) == ["", ""]

    def test_access_tokens_end(self):
        assert _settings(["OAUTH_ACCESS_TOKEN_LIFETIME_DAYS"]) == [90]

    def test_no_identity_provider_is_trusted_until_named(self):
        """Enterprise Managed Auth fetches the keys of an issuer and lets its
        assertions sign people in : off until the operator names that issuer."""
        assert _settings(["MCP_EMA_ISSUER", "MCP_EMA_ACCESS_TOKEN_LIFETIME_HOURS"]) == ["", 8]

    def test_a_token_lifetime_of_zero_is_refused(self):
        env = {key: value for key, value in os.environ.items() if key != "DJANGO_SETTINGS_MODULE"}
        env.update({"SECRET_KEY": "a-key-for-this-test-only-never-used-anywhere-else", "OAUTH_ACCESS_TOKEN_LIFETIME_DAYS": "0"})
        result = subprocess.run(  # noqa: S603 - the project's own settings
            [sys.executable, "-c", "import core.settings"], cwd=settings.BASE_DIR, env=env,
            capture_output=True, text=True, check=False,
        )
        assert result.returncode != 0 and "OAUTH_ACCESS_TOKEN_LIFETIME_DAYS" in result.stderr


@pytest.mark.django_db
class TestSignInOverPlainHttp:
    def test_the_sign_in_page_warns_where_signing_in_cannot_work(self, settings):
        """With HTTPS-only cookies, a sign-in over plain http fails without a
        word : the page says why, when it is opened that way."""
        settings.SESSION_COOKIE_SECURE = True
        html = Client().get(reverse("accounts:login")).content.decode()
        assert 'id="insecure-transport-notice"' in html and "hidden" in html
        assert "location.protocol !== 'https:'" in html

    def test_no_warning_where_plain_http_is_the_chosen_setup(self, settings):
        settings.SESSION_COOKIE_SECURE = False
        assert "insecure-transport-notice" not in Client().get(reverse("accounts:login")).content.decode()


class TestDownloads:
    @pytest.mark.parametrize("recorded", [
        "text/javascript", "application/javascript", "text/html", "image/svg+xml",
        "application/xhtml+xml", "text/css", "application/x-httpd-php", "", None, "nonsense",
        "TEXT/HTML; charset=utf-8",
    ])
    def test_a_type_a_browser_would_run_or_render_is_served_as_bytes(self, recorded):
        assert safe_content_type(recorded) == OPAQUE

    @pytest.mark.parametrize("recorded,served", [
        ("application/pdf", "application/pdf"),
        ("Application/PDF", "application/pdf"),
        ("image/png", "image/png"),
        ("text/plain; charset=utf-8", "text/plain"),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ])
    def test_an_inert_type_is_kept(self, recorded, served):
        assert safe_content_type(recorded) == served

    @pytest.mark.django_db
    def test_a_contract_declared_as_a_script_is_not_served_as_one(self, client):
        """The recorded type is what the uploading browser said. A "PDF"
        declared text/javascript, served as is from the instance's own origin,
        would be a script the Content Security Policy accepts."""
        from assets.tests.factories import ContractFactory

        contract = ContractFactory(
            file_content=b"alert(document.cookie)", file_name="terms.pdf", content_type="text/javascript",
        )
        client.force_login(UserFactory(is_superuser=True))
        response = client.get(reverse("assets:contract-document", kwargs={"pk": contract.pk}))
        assert response.status_code == 200
        assert response["Content-Type"] == OPAQUE
        assert response["Content-Disposition"].startswith("attachment")
        assert response["X-Content-Type-Options"] == "nosniff"


class TestProxyTrust:
    def test_the_image_lets_the_operator_say_which_proxy_to_believe(self):
        dockerfile = (settings.BASE_DIR / "Dockerfile").read_text()
        assert 'ENV FORWARDED_ALLOW_IPS="*"' in dockerfile
        # Not hard-wired on the command line, where an environment variable
        # could not override it.
        assert "--forwarded-allow-ips" not in dockerfile

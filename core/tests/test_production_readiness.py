# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""What a deployment relies on : the health probe, the error pages, the
logging of request errors and the refusal of the placeholder secret key."""

import importlib
import logging

import pytest
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, override_settings
from django.views import defaults


class TestHealthProbe:
    @pytest.mark.django_db
    def test_answers_ok_without_a_session(self):
        response = Client().get("/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response["Cache-Control"] == "no-store"

    @pytest.mark.django_db
    def test_is_not_refused_for_an_unknown_host(self):
        """A probe calls by IP : ALLOWED_HOSTS must not turn it into a 400."""
        with override_settings(ALLOWED_HOSTS=["grc.example.org"]):
            response = Client().get("/health/", HTTP_HOST="10.0.0.12:8000")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_is_not_redirected_by_the_onboarding_funnel(self):
        with override_settings(ONBOARDING_REDIRECT_ENABLED=True):
            response = Client().get("/health/")
        assert response.status_code == 200

    def test_reports_unavailable_when_the_database_is_down(self, monkeypatch):
        from core import middleware

        class Broken:
            def cursor(self):
                raise OSError("connection refused")

        monkeypatch.setattr(middleware, "connection", Broken())
        response = Client().get("/health/")
        assert response.status_code == 503
        # No error text, no host, no version : the endpoint is public.
        assert response.json() == {"status": "unavailable"}

    @pytest.mark.django_db
    def test_only_answers_read_methods(self):
        assert Client().post("/health/").status_code == 405


class TestErrorPages:
    @pytest.mark.django_db
    def test_unknown_page_renders_the_branded_404(self):
        response = Client().get("/no/such/page/")
        assert response.status_code == 404
        html = response.content.decode()
        assert "Page not found" in html
        assert "Back to the dashboard" in html

    @pytest.mark.django_db  # rendered with the request : context processors run
    def test_403_and_400_render(self):
        request = RequestFactory().get("/x/")
        forbidden = defaults.permission_denied(request, Exception("no"))
        bad = defaults.bad_request(request, Exception("no"))
        assert forbidden.status_code == 403 and b"Access denied" in forbidden.content
        assert bad.status_code == 400 and b"Bad request" in bad.content

    def test_500_renders_with_no_context_and_no_database(self):
        """The 500 page is rendered with an empty context, possibly because the
        database is what failed : it must need neither."""
        response = defaults.server_error(RequestFactory().get("/x/"))
        assert response.status_code == 500
        html = response.content.decode()
        assert "Something went wrong on our side" in html
        # Self-contained : it must not pull the application shell.
        assert "sidebar" not in html
        assert render_to_string("500.html")  # no request, no context

    @pytest.mark.django_db
    def test_csrf_refusal_explains_what_to_do(self):
        from django.views.csrf import csrf_failure

        response = csrf_failure(RequestFactory().post("/x/"), reason="token missing")
        assert response.status_code == 403
        assert b"This form has expired" in response.content

    @pytest.mark.parametrize("name", ["400.html", "403.html", "403_csrf.html", "404.html", "500.html"])
    def test_error_pages_are_translated(self, name):
        from django.utils import translation

        with translation.override("fr"):
            html = render_to_string(name)
        assert "Retour au tableau de bord" in html


class TestRequestErrorLogging:
    def test_request_errors_reach_the_console_outside_debug(self):
        """Django's default console handler only fires under DEBUG : in
        production an unhandled error left no traceback anywhere."""
        from django.conf import settings

        assert settings.LOGGING["loggers"]["django"]["handlers"] == ["console"]
        assert "filters" not in settings.LOGGING["handlers"]["console"]
        handlers = logging.getLogger("django").handlers
        assert any(isinstance(h, logging.StreamHandler) and not h.filters for h in handlers)


class TestSecretKeyGuard:
    def _reload_settings(self, monkeypatch, **env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import core.settings

        return importlib.reload(core.settings)

    @pytest.fixture(autouse=True)
    def _restore_settings_module(self, monkeypatch):
        yield
        monkeypatch.undo()
        import core.settings

        importlib.reload(core.settings)

    @pytest.mark.parametrize("key", ["django-insecure-change-me-in-production", "change-me-to-a-random-secret-key"])
    def test_a_placeholder_key_refuses_to_start_outside_debug(self, monkeypatch, key):
        from django.core.exceptions import ImproperlyConfigured

        with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
            self._reload_settings(monkeypatch, DEBUG="False", SECRET_KEY=key)

    def test_a_placeholder_key_is_tolerated_under_debug(self, monkeypatch):
        module = self._reload_settings(
            monkeypatch, DEBUG="True", SECRET_KEY="change-me-to-a-random-secret-key"
        )
        assert module.DEBUG is True

    def test_a_real_key_starts_outside_debug(self, monkeypatch):
        module = self._reload_settings(monkeypatch, DEBUG="False", SECRET_KEY="x" * 64)
        assert module.DEBUG is False

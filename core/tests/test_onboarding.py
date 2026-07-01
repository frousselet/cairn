"""Tests for the first-run onboarding flow.

The onboarding redirect middleware is disabled for the suite at large
(``ONBOARDING_REDIRECT_ENABLED = False`` in ``core.settings_test``); the
middleware tests opt back in via the ``settings`` fixture.
"""

from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from core.onboarding import state as ob_state
from core.onboarding.state import instance_ready, is_first_run, migration_status

PENDING = {"available": True, "up_to_date": False, "applied": 1, "total": 3, "pending": ["a.0002", "a.0003"]}


@pytest.fixture(autouse=True)
def _reset_onboarding_state():
    """Reset the cross-test shared state around each test.

    The sticky 'initialised' flag is process-global, and the runner now keeps
    its progress and lock in the (process-local, in test) cache: clear both so
    tests do not leak a "running" job or an initialised flag into one another.
    """
    from django.core.cache import cache

    ob_state.reset_onboarding_state()
    cache.clear()
    yield
    ob_state.reset_onboarding_state()
    cache.clear()


@pytest.mark.django_db
class TestIsFirstRun:
    def test_true_when_no_users(self):
        assert is_first_run() is True

    def test_false_when_user_exists(self):
        UserFactory()
        ob_state.reset_onboarding_state()
        assert is_first_run() is False

    def test_sticky_once_initialised(self):
        UserFactory()
        ob_state.reset_onboarding_state()
        assert is_first_run() is False
        User.objects.all().delete()
        # Cached as initialised -> stays False without re-querying.
        assert is_first_run() is False

    def test_database_error_treated_as_first_run(self, monkeypatch):
        def boom():
            raise DatabaseError("relation accounts_user does not exist")

        monkeypatch.setattr(User.objects, "exists", boom)
        assert is_first_run() is True


@pytest.mark.django_db
class TestInstanceReady:
    """``instance_ready`` gates background jobs (SPOF, semantic index) off the
    database until the schema is migrated and the first user exists."""

    def test_false_when_schema_not_ready(self, monkeypatch):
        # Schema not migrated: must short-circuit and never query the user table.
        def _should_not_run():
            raise AssertionError("is_first_run queried while schema not ready")

        monkeypatch.setattr(ob_state, "schema_ready", lambda: False)
        monkeypatch.setattr(ob_state, "is_first_run", _should_not_run)
        assert instance_ready() is False

    def test_false_when_first_run(self, monkeypatch):
        monkeypatch.setattr(ob_state, "schema_ready", lambda: True)
        monkeypatch.setattr(ob_state, "is_first_run", lambda: True)
        assert instance_ready() is False

    def test_true_when_ready_and_initialised(self, monkeypatch):
        monkeypatch.setattr(ob_state, "schema_ready", lambda: True)
        monkeypatch.setattr(ob_state, "is_first_run", lambda: False)
        assert instance_ready() is True


@pytest.mark.django_db
class TestMigrationStatus:
    def test_shape(self):
        status = migration_status()
        assert set(status) == {"available", "up_to_date", "applied", "total", "pending"}
        assert status["available"] is True
        assert isinstance(status["pending"], list)


@pytest.mark.django_db
class TestMiddleware:
    @pytest.fixture(autouse=True)
    def _enable_redirect(self, settings):
        settings.ONBOARDING_REDIRECT_ENABLED = True

    def test_redirects_to_onboarding_when_no_users(self, client):
        resp = client.get("/")
        assert resp.status_code == 302
        assert resp.url == reverse("onboarding:landing")

    def test_landing_reachable_during_first_run(self, client):
        resp = client.get(reverse("onboarding:landing"))
        assert resp.status_code == 200

    def test_static_assets_bypass_redirect(self, client):
        resp = client.get("/static/whatever.css")
        assert not (resp.status_code == 302 and resp.url == reverse("onboarding:landing"))

    def test_onboarding_hidden_once_initialised(self, client):
        UserFactory()
        ob_state.reset_onboarding_state()
        resp = client.get(reverse("onboarding:landing"))
        assert resp.status_code == 302
        assert resp.url == "/"

    def test_complete_reachable_once_initialised(self, client):
        UserFactory(is_superuser=True)
        ob_state.reset_onboarding_state()
        resp = client.get(reverse("onboarding:complete"))
        assert resp.status_code == 302
        assert resp.url == "/"  # bounced home (no session flag), NOT forced by middleware

    def test_progress_poll_reachable_once_initialised(self, client):
        UserFactory()
        ob_state.reset_onboarding_state()
        resp = client.get(reverse("onboarding:progress"))
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "application/json"

    def test_pending_migrations_funnel_even_when_initialised(self, client):
        # Upgrade scenario: users exist but the schema has pending migrations.
        UserFactory()
        ob_state.reset_onboarding_state()
        with patch("core.onboarding.state.migration_status", return_value=PENDING):
            resp = client.get("/")
        assert resp.status_code == 302
        assert resp.url == reverse("onboarding:landing")


@pytest.mark.django_db
class TestLanding:
    def test_auto_starts_migrations_when_pending(self, client):
        with patch("core.onboarding.views.migration_status", return_value=PENDING), \
             patch("core.onboarding.views.start_migrations") as started:
            resp = client.get(reverse("onboarding:landing"))
        assert resp.status_code == 200
        assert b"onboarding/progress.json" in resp.content
        started.assert_called_once()

    def test_shows_choices_when_up_to_date(self, client):
        resp = client.get(reverse("onboarding:landing"))
        assert resp.status_code == 200
        assert reverse("onboarding:seed").encode() in resp.content
        assert reverse("onboarding:scratch").encode() in resp.content

    def test_upgrade_migration_targets_app_root(self, client):
        # Initialised instance with pending migrations -> migrate, then back to /.
        with patch("core.onboarding.views.migration_status", return_value=PENDING), \
             patch("core.onboarding.views.is_first_run", return_value=False), \
             patch("core.onboarding.views.start_migrations") as started:
            resp = client.get(reverse("onboarding:landing"))
        assert resp.status_code == 200
        assert b"onboarding/progress.json" in resp.content
        assert b"completeUrl = '/'" in resp.content
        started.assert_called_once_with(upgrade=True)


@pytest.mark.django_db
class TestProgressView:
    def test_returns_snapshot_json(self, client):
        resp = client.get(reverse("onboarding:progress"))
        assert resp.status_code == 200
        data = resp.json()
        assert set(data) == {"kind", "status", "label", "current", "total", "error", "upgrade"}


@pytest.mark.django_db
class TestScratch:
    VALID = {
        "email": "admin@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "password1": "Sup3rSecret!pw",
        "password2": "Sup3rSecret!pw",
    }

    def test_get_renders_company_and_admin_steps(self, client):
        resp = client.get(reverse("onboarding:scratch"))
        assert resp.status_code == 200
        # Both wizard steps are present in the single page / single form.
        assert b'id="ob-panel-1"' in resp.content
        assert b'id="ob-panel-2"' in resp.content
        assert b'id="id_name"' in resp.content        # company step field
        assert b'id="id_email"' in resp.content        # admin step field

    def test_creates_superuser_and_signs_in(self, client):
        resp = client.post(reverse("onboarding:scratch"), self.VALID)
        assert resp.status_code == 302
        assert resp.url == "/"
        user = User.objects.get(email="admin@example.com")
        assert user.is_superuser is True
        assert client.session.get("_auth_user_id") == str(user.pk)

    def test_password_mismatch_rejected(self, client):
        data = dict(self.VALID, password2="different")
        resp = client.post(reverse("onboarding:scratch"), data)
        assert resp.status_code == 200
        assert User.objects.count() == 0

    def test_blocked_when_users_exist(self, client):
        UserFactory()
        ob_state.reset_onboarding_state()
        resp = client.post(reverse("onboarding:scratch"), self.VALID)
        assert resp.status_code == 302
        assert resp.url == "/"
        assert User.objects.count() == 1

    def test_company_settings_saved_with_admin(self, client):
        from accounts.models import CompanySettings

        data = dict(self.VALID, name="Voltara Energy", app_name="Voltara GRC", accent_color="2563EB")
        resp = client.post(reverse("onboarding:scratch"), data)
        assert resp.status_code == 302
        assert resp.url == "/"
        company = CompanySettings.objects.get()
        assert company.name == "Voltara Energy"
        assert company.app_name == "Voltara GRC"
        assert company.accent_color == "#2563EB"  # normalised by the form

    def test_nothing_persisted_when_admin_invalid(self, client):
        from accounts.models import CompanySettings

        # Valid company step, but the passwords do not match: the whole submit is
        # rejected and neither the admin nor the company settings are written.
        data = dict(self.VALID, password2="different", name="Voltara Energy")
        resp = client.post(reverse("onboarding:scratch"), data)
        assert resp.status_code == 200
        assert User.objects.count() == 0
        assert CompanySettings.objects.count() == 0

    def test_invalid_accent_colour_rejected(self, client):
        from accounts.models import CompanySettings

        data = dict(self.VALID, accent_color="not-a-colour")
        resp = client.post(reverse("onboarding:scratch"), data)
        assert resp.status_code == 200
        assert User.objects.count() == 0
        assert CompanySettings.objects.count() == 0


@pytest.mark.django_db
class TestSeed:
    def test_post_starts_seed_and_renders_progress(self, client):
        with patch("core.onboarding.views.start_seed", return_value=True) as started:
            resp = client.post(reverse("onboarding:seed"))
        assert resp.status_code == 200
        assert b"onboarding/progress.json" in resp.content
        assert reverse("onboarding:complete").encode() in resp.content
        assert client.session.get("onboarding_seeding") is True
        started.assert_called_once()

    def test_post_blocked_when_migrations_pending(self, client):
        with patch("core.onboarding.views.migration_status", return_value=PENDING), \
             patch("core.onboarding.views.start_seed") as started:
            resp = client.post(reverse("onboarding:seed"))
        assert resp.status_code == 302
        assert resp.url == reverse("onboarding:landing")
        started.assert_not_called()

    def test_post_blocked_when_users_exist(self, client):
        UserFactory()
        ob_state.reset_onboarding_state()
        with patch("core.onboarding.views.start_seed") as started:
            resp = client.post(reverse("onboarding:seed"))
        assert resp.status_code == 302
        assert resp.url == "/"
        started.assert_not_called()

    def test_get_redirects_to_landing_when_not_seeding(self, client):
        resp = client.get(reverse("onboarding:seed"))
        assert resp.status_code == 302
        assert resp.url == reverse("onboarding:landing")


@pytest.mark.django_db
class TestComplete:
    def test_without_session_flag_redirects_home(self, client):
        resp = client.get(reverse("onboarding:complete"))
        assert resp.status_code == 302
        assert resp.url == "/"

    def test_signs_in_the_seeded_admin(self, client):
        admin = UserFactory(is_superuser=True)
        ob_state.reset_onboarding_state()
        session = client.session
        session["onboarding_seeding"] = True
        session.save()
        resp = client.get(reverse("onboarding:complete"))
        assert resp.status_code == 302
        assert resp.url == "/"
        assert client.session.get("_auth_user_id") == str(admin.pk)

    def test_no_superuser_redirects_to_landing(self, client):
        session = client.session
        session["onboarding_seeding"] = True
        session.save()
        resp = client.get(reverse("onboarding:complete"))
        assert resp.status_code == 302
        assert resp.url == reverse("onboarding:landing")


class TestRunner:
    def test_start_skips_when_a_job_holds_the_lock(self):
        """Only one worker may run a migration/seed at a time. The lock lives in
        the shared cache, so a job started on any worker blocks starts on all of
        them - this is what stops several workers racing the same DDL."""
        from core.onboarding import runner

        # Simulate a job already running on another worker: it holds the lock.
        assert runner._store().add(runner._LOCK_KEY, "1", runner._LOCK_TTL) is True
        assert runner.is_running() is True
        # No new job is launched (and, crucially, no background thread spawned).
        assert runner.start_seed() is False
        assert runner.start_migrations() is False

    def test_is_running_reflects_shared_lock(self):
        from core.onboarding import runner

        assert runner.is_running() is False
        runner._store().add(runner._LOCK_KEY, "1", runner._LOCK_TTL)
        assert runner.is_running() is True
        runner.reset_runner_state()
        assert runner.is_running() is False

    def test_progress_is_published_to_the_shared_cache(self):
        """Progress written by the running worker is visible to every other
        worker (they render the same bar) because it lives in the shared cache."""
        from core.onboarding import runner

        runner._set(kind="migrate", status="running", current=5, total=10)
        snap = runner.progress_snapshot()
        assert snap["status"] == "running"
        assert (snap["current"], snap["total"]) == (5, 10)

    def test_progress_snapshot_keys(self):
        from core.onboarding.runner import progress_snapshot

        assert set(progress_snapshot()) == {"kind", "status", "label", "current", "total", "error", "upgrade"}

    def test_seed_exposes_phase_markers(self):
        from core.onboarding.runner import SEED_PATH

        # The seed runner derives the progress total from these markers.
        assert SEED_PATH.read_text().count('_phase("') >= 15

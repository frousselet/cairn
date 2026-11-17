# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
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

    from core.onboarding import runner

    ob_state.reset_onboarding_state()
    runner._ResilientStore.reset()
    cache.clear()
    yield
    ob_state.reset_onboarding_state()
    runner._ResilientStore.reset()
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
        assert set(data) == {"kind", "status", "label", "current", "total", "error", "upgrade", "alive"}
        # The poll is never answered from a cache : it is the live state.
        assert resp["Cache-Control"] == "no-store"

    def test_the_poll_says_whether_a_job_is_alive(self, client):
        """A screen whose job never started, or died, must be able to tell."""
        from core.onboarding import runner

        assert client.get(reverse("onboarding:progress")).json()["alive"] is False

        runner._store().add(runner._LOCK_KEY, "1", runner._LOCK_TTL)

        assert client.get(reverse("onboarding:progress")).json()["alive"] is True

    def test_the_screen_goes_back_to_the_landing_page_when_no_job_is_behind_it(self, client):
        with patch("core.onboarding.views.migration_status", return_value=PENDING), \
             patch("core.onboarding.views.start_migrations"):
            body = client.get(reverse("onboarding:landing")).content.decode()

        assert "data.alive === false" in body
        assert "The installation is not progressing." in body


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

    def test_store_degrades_to_local_when_cache_unreachable(self):
        """A shared-cache outage must never 500 the request path. When the
        backend raises (Redis down), the store falls back to a process-local
        map so the onboarding middleware's ``is_running`` read still answers."""
        from core.onboarding import runner

        class _DeadCache:
            def get(self, *a, **k):
                raise ConnectionError("redis down")

            def set(self, *a, **k):
                raise ConnectionError("redis down")

            def add(self, *a, **k):
                raise ConnectionError("redis down")

            def delete(self, *a, **k):
                raise ConnectionError("redis down")

            def touch(self, *a, **k):
                raise ConnectionError("redis down")

        # Clear any process-local carry-over from a prior degraded test.
        runner._ResilientStore.reset()
        with patch.object(runner._ResilientStore, "_cache", return_value=_DeadCache()):
            # No lock yet: reads answer False instead of raising.
            assert runner.is_running() is False
            # A start can still acquire the (now local) lock exactly once.
            assert runner._store().add(runner._LOCK_KEY, "1", runner._LOCK_TTL) is True
            assert runner._store().add(runner._LOCK_KEY, "1", runner._LOCK_TTL) is False
            assert runner.is_running() is True
        runner._ResilientStore.reset()

    def test_a_cache_that_is_down_is_left_alone_for_a_while(self):
        """A cache that does not answer costs its timeout on every call : after a
        failure it is not tried again at once, or the polls and the migration
        steps of one installation would wait for it hundreds of times."""
        from core.onboarding import runner

        calls = []

        class _SilentCache:
            def get(self, *a, **k):
                calls.append("get")
                raise TimeoutError("no answer")

            def set(self, *a, **k):
                calls.append("set")
                raise TimeoutError("no answer")

        runner._ResilientStore.reset()
        with patch.object(runner._ResilientStore, "_cache", return_value=_SilentCache()):
            for _ in range(20):
                runner.is_running()
                runner._set(current=1)
            assert len(calls) == 1
            # The pause over, the cache is tried again.
            runner._ResilientStore._down_until = 0.0
            runner.is_running()
            assert len(calls) == 2
        runner._ResilientStore.reset()


# Nothing listens on port 1 : every call fails at once with a refused connection.
UNREACHABLE_CACHE = {
    "default": {
        "BACKEND": "core.cache.ResilientRedisCache",
        "LOCATION": "redis://127.0.0.1:1/1",
        "OPTIONS": {"socket_connect_timeout": 1, "socket_timeout": 1},
    }
}


def _wait_until(condition, seconds=5.0):
    import time

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


class TestWithoutASharedCache:
    """An instance whose Redis cannot be reached still installs itself.

    The cache backend of the project answers an unreachable Redis as an empty
    cache would : ``add`` returns ``False``. Taken as "the lock is held", that
    answer left a new instance on its installation screen for ever, the
    migrations waiting for a lock nobody could take. These tests use the real
    backend, pointed at a port where nothing listens.
    """

    @pytest.fixture(autouse=True)
    def _no_redis(self):
        from django.test import override_settings

        from core.onboarding import runner

        runner._ResilientStore.reset()
        with override_settings(CACHES=UNREACHABLE_CACHE):
            yield
        runner._ResilientStore.reset()

    def test_the_backend_alone_would_refuse_the_lock(self):
        """What the store must not take at face value."""
        from django.core.cache import caches

        assert caches["default"].add("anything", "1", 60) is False

    def test_the_migrations_start_and_only_once(self):
        import threading

        from core.onboarding import runner

        started, release = threading.Event(), threading.Event()

        def job():
            started.set()
            release.wait(5)

        with patch.object(runner, "_run_migrations", job):
            assert runner.start_migrations() is True
            assert started.wait(5)
            # The job is seen as running, and a second request starts no rival.
            assert runner.is_running() is True
            assert runner.start_migrations() is False
            report = runner.progress_report()
            assert (report["status"], report["kind"], report["alive"]) == ("running", "migrate", True)
            release.set()
            assert _wait_until(lambda: not runner.is_running())

        # The lock is given back : the next job (the sample data) can start.
        with patch.object(runner, "_run_seed", lambda: None):
            assert runner.start_seed() is True
            assert _wait_until(lambda: not runner.is_running())

    def test_the_progress_is_kept_for_the_screen(self):
        from core.onboarding import runner

        runner._set(kind="migrate", status="running", current=3, total=9, label="accounts.0003")

        snap = runner.progress_snapshot()

        assert (snap["current"], snap["total"], snap["label"]) == (3, 9, "accounts.0003")

    @pytest.mark.django_db
    def test_the_landing_page_starts_the_pending_migrations(self, client):
        import threading

        from core.onboarding import runner

        ran = threading.Event()
        with patch("core.onboarding.views.migration_status", return_value=PENDING), \
             patch.object(runner, "_run_migrations", ran.set):
            resp = client.get(reverse("onboarding:landing"))
            assert ran.wait(5), "the migrations never started"
            assert _wait_until(lambda: not runner.is_running())

        assert resp.status_code == 200
        assert b"onboarding/progress.json" in resp.content

    def test_a_key_taken_here_stays_read_here_if_the_cache_comes_back(self):
        """The job that took its lock during an outage keeps a coherent view of it."""
        from django.test import override_settings

        from core.onboarding import runner

        assert runner._store().add(runner._LOCK_KEY, "1", runner._LOCK_TTL) is True
        # The cache answers again (the in-memory cache of the test settings).
        with override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}):
            assert runner.is_running() is True
            assert runner._store().add(runner._LOCK_KEY, "1", runner._LOCK_TTL) is False
            runner._store().delete(runner._LOCK_KEY)
            assert runner.is_running() is False


@pytest.mark.django_db
class TestTheDatabaseLock:
    """Two runners never work at once, whatever each believes about the cache."""

    def test_nothing_is_asked_of_a_database_that_serves_one_process(self, django_assert_num_queries):
        from django.db import connection

        from core.onboarding import runner

        if connection.vendor == "postgresql":
            pytest.skip("covered by the PostgreSQL test below")
        with django_assert_num_queries(0), runner._database_lock(connection):
            pass

    def test_a_second_session_cannot_take_it_while_it_is_held(self):
        from django.db import connection

        from core.onboarding import runner

        if connection.vendor != "postgresql":
            pytest.skip("advisory locks are a PostgreSQL feature")
        other = connection.copy()
        try:
            with runner._database_lock(connection):
                with other.cursor() as cursor:
                    cursor.execute("SELECT pg_try_advisory_lock(%s)", [runner._DATABASE_LOCK_ID])
                    assert cursor.fetchone()[0] is False
            with other.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", [runner._DATABASE_LOCK_ID])
                assert cursor.fetchone()[0] is True
                cursor.execute("SELECT pg_advisory_unlock(%s)", [runner._DATABASE_LOCK_ID])
        finally:
            other.close()

    def test_the_sample_data_is_not_loaded_on_top_of_existing_users(self, tmp_path, monkeypatch):
        """A runner that waited for another one finds its users, and loads nothing more."""
        from django.db import connections

        from core.onboarding import runner

        seed = tmp_path / "seed.py"
        seed.write_text('_phase("only")\nraise RuntimeError("the seed ran")\n')
        monkeypatch.setattr(runner, "SEED_PATH", seed)
        UserFactory()

        with patch.object(connections, "close_all"):
            runner._run_seed()

        assert runner.progress_snapshot()["status"] == "done"

    def test_the_sample_data_is_loaded_into_an_empty_instance(self, tmp_path, monkeypatch):
        from django.db import connections

        from core.onboarding import runner

        seed = tmp_path / "seed.py"
        seed.write_text('SEED_PROGRESS("only")  # _phase("only")\n')
        monkeypatch.setattr(runner, "SEED_PATH", seed)

        with patch.object(connections, "close_all"):
            runner._run_seed()

        snap = runner.progress_snapshot()
        assert (snap["status"], snap["current"], snap["total"]) == ("done", 1, 1)


@pytest.mark.django_db
class TestNoQueryBeforeTheSchemaExists:
    """A new database is not asked for tables it does not hold yet.

    Each such query was caught and harmless for the page, and left an
    ``ERROR: relation ... does not exist`` in the database log : three per
    poll of the installation screen for a browser that still held a session
    cookie, hundreds of lines for one installation.
    """

    def test_has_table(self):
        assert ob_state.has_table(User._meta.db_table) is True
        assert ob_state.has_table("no_such_table") is False

    def test_a_table_seen_once_is_not_looked_for_again(self, django_assert_num_queries):
        ob_state.has_table(User._meta.db_table)

        with django_assert_num_queries(0):
            assert ob_state.has_table(User._meta.db_table) is True

    @pytest.mark.parametrize("failure", [DatabaseError("unreachable"), RuntimeError("Database access not allowed")])
    def test_a_database_that_cannot_be_asked_holds_no_table(self, monkeypatch, failure):
        """Unreachable, or asked where no query is allowed (a module imported
        while tests are collected) : the caller takes its "no table" path."""
        from django.db import connections

        def refuse(*args, **kwargs):
            raise failure

        monkeypatch.setattr(connections["default"], "cursor", refuse)

        assert ob_state.has_table("anything") is False
        # And nothing is remembered : the next call asks again.
        assert "anything" not in ob_state._known_tables

    def test_the_first_run_is_decided_without_asking_a_missing_table(self, monkeypatch, django_assert_num_queries):
        monkeypatch.setattr(ob_state, "has_table", lambda name: False)

        with django_assert_num_queries(0):
            assert is_first_run() is True

    def test_the_company_settings_are_not_read_before_their_table_exists(self, rf, monkeypatch, django_assert_num_queries):
        from core.context_processors import company

        monkeypatch.setattr(ob_state, "has_table", lambda name: False)

        with django_assert_num_queries(0):
            context = company(rf.get("/onboarding/"))

        assert context["company"] is None
        assert context["APP_NAME"] == "Cairn"

    def test_a_lifecycle_falls_back_to_its_code_default_without_a_query(self, monkeypatch, django_assert_num_queries):
        from core.lifecycle import LIFECYCLE_REGISTRY, clear_lifecycle_cache, get_lifecycle

        monkeypatch.setattr(ob_state, "has_table", lambda name: False)
        clear_lifecycle_cache()

        with django_assert_num_queries(0):
            assert get_lifecycle("scope") is LIFECYCLE_REGISTRY["scope"]
        clear_lifecycle_cache()

    def test_nobody_is_signed_in_while_the_schema_is_not_ready(self, client, settings, django_assert_num_queries):
        """A session cookie kept from an earlier instance must cost no query."""
        settings.ONBOARDING_REDIRECT_ENABLED = True
        client.force_login(UserFactory())
        ob_state.reset_onboarding_state()
        ob_state.has_table("django_session")  # seen once, never looked for again

        with patch("core.middleware.schema_ready", return_value=False), django_assert_num_queries(0):
            response = client.get(reverse("onboarding:progress"))

        assert response.status_code == 200
        assert response.json()["status"] == "idle"

    def test_nobody_is_signed_in_before_the_session_table_exists(self, rf, settings):
        """Static files and the language switch go past the onboarding rules : they
        must not look a session up in a database that has no session table."""
        from django.contrib.auth.models import AnonymousUser

        from core.middleware import OnboardingMiddleware

        settings.ONBOARDING_REDIRECT_ENABLED = True
        seen = {}

        def view(request):
            seen["user"] = request.user
            return "response"

        request = rf.get(settings.STATIC_URL + "css/cairn/00-tokens.css")
        request.user = "a lazy user that would read the session"

        with patch("core.middleware.has_table", return_value=False):
            assert OnboardingMiddleware(view)(request) == "response"

        assert isinstance(seen["user"], AnonymousUser)

    def test_the_session_is_read_again_once_the_schema_is_ready(self, client, settings):
        settings.ONBOARDING_REDIRECT_ENABLED = True
        user = UserFactory()
        client.force_login(user)

        response = client.get(reverse("home"))

        assert response.status_code == 200
        assert response.wsgi_request.user == user

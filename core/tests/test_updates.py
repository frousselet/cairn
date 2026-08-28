# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The "a newer version is available" check.

GitHub is stubbed throughout : the suite never leaves the machine. What matters
here is that the instance tells the truth about its own version - claiming an
update that does not exist, or staying silent on one that does, both misinform
an operator deciding whether to upgrade.
"""
import pytest
from django.core.cache import cache
from django.urls import reverse

from accounts.tests.factories import UserFactory
from core import updates


@pytest.fixture(autouse=True)
def _clear_cache():
    """The answer is cached across workers, so it must not leak between tests."""
    cache.delete(updates.CACHE_KEY)
    yield
    cache.delete(updates.CACHE_KEY)


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _github(monkeypatch, tag="v1.2.3", calls=None):
    def _get(url, **kwargs):
        if calls is not None:
            calls.append(url)
        return _Response({
            "tag_name": tag,
            "html_url": f"https://github.com/frousselet/cairn/releases/tag/{tag}",
            "published_at": "2026-08-01T10:00:00Z",
        })

    monkeypatch.setattr(updates.httpx, "get", _get)


def _unreachable(monkeypatch):
    def _get(url, **kwargs):
        raise OSError("no route to host")

    monkeypatch.setattr(updates.httpx, "get", _get)


# ── Comparing versions ─────────────────────────────────────────────────


@pytest.mark.parametrize("version,expected", [
    ("1.2.3", (1, 2, 3)),
    ("v1.2.3", (1, 2, 3)),
    ("0.35.10", (0, 35, 10)),
    ("dev", None),
    ("", None),
    (None, None),
    ("1.2", None),
    ("1.2.3-rc1", None),
])
def test_only_a_release_number_is_placed_on_the_scale(version, expected):
    assert updates._version_tuple(version) == expected


def test_a_ten_is_newer_than_a_nine(monkeypatch, settings):
    """String comparison would put 0.35.9 ahead of 0.35.10."""
    settings.APP_VERSION = "0.35.9"
    _github(monkeypatch, tag="v0.35.10")

    assert updates.update_status()["state"] == "outdated"


# ── What the modal is told ─────────────────────────────────────────────


def test_a_newer_release_is_reported_with_where_to_read_about_it(monkeypatch, settings):
    settings.APP_VERSION = "1.0.0"
    _github(monkeypatch, tag="v1.2.3")

    status = updates.update_status()

    assert status["state"] == "outdated"
    assert status["latest_version"] == "1.2.3"
    assert status["url"].endswith("/releases/tag/v1.2.3")


def test_the_latest_release_reports_as_current(monkeypatch, settings):
    settings.APP_VERSION = "1.2.3"
    _github(monkeypatch, tag="v1.2.3")

    assert updates.update_status()["state"] == "current"


def test_a_newer_instance_than_the_last_release_is_not_outdated(monkeypatch, settings):
    """A build running ahead of the last tag must not be told to downgrade."""
    settings.APP_VERSION = "2.0.0"
    _github(monkeypatch, tag="v1.2.3")

    assert updates.update_status()["state"] == "current"


def test_a_development_build_is_not_placed_on_the_scale(monkeypatch, settings):
    settings.APP_VERSION = "dev"
    _github(monkeypatch, tag="v1.2.3")

    assert updates.update_status()["state"] == "unknown"


def test_an_unreachable_github_is_unknown_rather_than_an_error(monkeypatch, settings):
    settings.APP_VERSION = "1.0.0"
    _unreachable(monkeypatch)

    assert updates.update_status()["state"] == "unknown"


def test_the_check_can_be_switched_off(monkeypatch, settings):
    settings.APP_VERSION = "1.0.0"
    settings.UPDATE_CHECK_ENABLED = False
    monkeypatch.setattr(updates.httpx, "get", lambda *a, **k: pytest.fail("called out"))

    assert updates.update_status()["state"] == "disabled"


# ── Caching ────────────────────────────────────────────────────────────


def test_the_answer_is_asked_for_once_and_shared(monkeypatch, settings):
    settings.APP_VERSION = "1.0.0"
    calls = []
    _github(monkeypatch, calls=calls)

    updates.update_status()
    updates.update_status()

    assert len(calls) == 1


def test_a_failure_is_cached_too_so_the_modal_stays_fast(monkeypatch, settings):
    settings.APP_VERSION = "1.0.0"
    calls = []

    def _get(url, **kwargs):
        calls.append(url)
        raise OSError("down")

    monkeypatch.setattr(updates.httpx, "get", _get)

    updates.update_status()
    updates.update_status()

    assert len(calls) == 1


# ── The surfaces ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_the_modal_asks_for_the_check_only_when_it_opens(client):
    """Rendered on every page, so it must not fetch on every page."""
    client.force_login(UserFactory())
    html = client.get("/").content.decode()

    assert 'hx-get="/update-check/"' in html
    assert 'hx-trigger="shown.bs.modal from:#aboutModal once"' in html


@pytest.mark.django_db
def test_the_partial_offers_the_release_when_one_is_newer(client, monkeypatch, settings):
    settings.APP_VERSION = "1.0.0"
    _github(monkeypatch, tag="v1.2.3")
    client.force_login(UserFactory())

    html = client.get(reverse("update-check")).content.decode()

    assert "1.2.3" in html
    assert "/releases/tag/v1.2.3" in html


@pytest.mark.django_db
def test_the_partial_says_nothing_when_nothing_can_be_said(client, monkeypatch, settings):
    settings.APP_VERSION = "1.0.0"
    _unreachable(monkeypatch)
    client.force_login(UserFactory())

    assert client.get(reverse("update-check")).content.decode().strip() == ""


@pytest.mark.django_db
def test_the_partial_requires_authentication(client):
    response = client.get(reverse("update-check"))

    assert response.status_code == 302


@pytest.mark.django_db
def test_the_api_reports_the_same_status(client, monkeypatch, settings):
    settings.APP_VERSION = "1.0.0"
    _github(monkeypatch, tag="v1.2.3")
    client.force_login(UserFactory())

    payload = client.get("/api/v1/update-check/").json()

    assert payload["data"]["state"] == "outdated"
    assert payload["data"]["current_version"] == "1.0.0"
    assert payload["data"]["latest_version"] == "1.2.3"


@pytest.mark.django_db
def test_the_api_requires_authentication(client):
    assert client.get("/api/v1/update-check/").status_code in (401, 403)

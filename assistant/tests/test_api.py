"""Tests for the DRF endpoint POST /api/v1/assistant/ask/."""

import pytest

from accounts.tests.factories import UserFactory
from assistant.engine import AskOutcome, ToolRun
from assistant.ollama import AssistantDisabled, OllamaUnreachable

API_URL = "/api/v1/assistant/ask/"


class StubEngine:
    outcome = None
    error = None

    def __init__(self, user, language="en", client=None):
        self.language = language

    def ask(self, question):
        if type(self).error is not None:
            raise type(self).error
        return type(self).outcome


@pytest.fixture
def stub_engine(monkeypatch):
    StubEngine.outcome = None
    StubEngine.error = None
    monkeypatch.setattr("assistant.api.views.AssistantEngine", StubEngine)
    return StubEngine


@pytest.fixture
def logged_client(client, db):
    client.force_login(UserFactory())
    return client


@pytest.mark.django_db
def test_authentication_required(client):
    assert client.post(API_URL, {"q": "test ?"}).status_code in (401, 403)


def test_empty_question_is_400(logged_client):
    response = logged_client.post(API_URL, {"q": ""})
    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_disabled_returns_503_with_code(logged_client, stub_engine):
    stub_engine.error = AssistantDisabled()
    response = logged_client.post(API_URL, {"q": "Quelles décisions ?"})
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "assistant_disabled"


def test_unreachable_returns_503_with_code(logged_client, stub_engine):
    stub_engine.error = OllamaUnreachable("down")
    response = logged_client.post(API_URL, {"q": "Quelles décisions ?"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "assistant_unreachable"


def test_happy_path_shape(logged_client, stub_engine):
    run = ToolRun(
        tool="list_management_review_decisions",
        label="Decisions",
        icon="bi-check2-square",
        arguments={},
        records=[{"id": "x"}],
        cards=[{
            "title": "DECS-1",
            "subtitle": "completed",
            "url": "/reports/decisions/abc/",
            "icon": "bi-check2-square",
        }],
    )
    stub_engine.outcome = AskOutcome(
        question="q?", language="fr",
        summary="Une décision.", tool_runs=[run],
    )
    response = logged_client.post(API_URL, {"q": "Quelles décisions ?", "language": "fr"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"] == "Une décision."
    assert data["language"] == "fr"
    assert data["degraded"] is False
    result = data["results"][0]
    assert result["tool"] == "list_management_review_decisions"
    assert result["records"][0]["url"] == "/reports/decisions/abc/"


def test_language_passed_to_engine(logged_client, stub_engine):
    captured = {}
    original_init = StubEngine.__init__

    def spy_init(self, user, language="en", client=None):
        captured["language"] = language
        original_init(self, user, language=language, client=client)

    StubEngine.__init__ = spy_init
    try:
        stub_engine.outcome = AskOutcome(question="q", language="fr")
        logged_client.post(API_URL, {"q": "Une question ?", "language": "fr"})
    finally:
        StubEngine.__init__ = original_init
    assert captured["language"] == "fr"

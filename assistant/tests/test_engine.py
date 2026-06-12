"""Engine tests with a fake LLM client and real ORM data."""

from datetime import date, timedelta

import pytest
from django.test import override_settings

from accounts.tests.factories import UserFactory
from assistant.engine import PERMISSION_DENIED, AssistantEngine
from assistant.ollama import AssistantDisabled, OllamaUnreachable
from reports.tests.factories import ManagementReviewDecisionFactory, ManagementReviewFactory


class FakeClient:
    """Scripted stand-in for OllamaClient."""

    def __init__(self, plan, summary="Summary sentence."):
        self.plan = plan
        self.summary = summary
        self.json_calls = []
        self.text_calls = []

    def chat_json(self, messages, json_schema, think=None):
        self.json_calls.append({"messages": list(messages), "schema": json_schema})
        return self.plan

    def chat_text(self, messages):
        self.text_calls.append(list(messages))
        if isinstance(self.summary, Exception):
            raise self.summary
        return self.summary


def _step(tool, **arguments):
    return {"tool": tool, "arguments": arguments}


def _plan(*steps):
    return {"steps": list(steps)}


@pytest.fixture
def superuser(db):
    return UserFactory(is_superuser=True)


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_canonical_plan_resolves_placeholder_to_latest_closed_review(superuser):
    """Decisions of the last management review: the planned (future) review
    must not win; $1.id resolves to the closed review found by step 1."""
    closed = ManagementReviewFactory(
        status="closed",
        held_date=date.today() - timedelta(days=30),
        planned_date=date.today() - timedelta(days=35),
    )
    ManagementReviewFactory(status="planned", planned_date=date.today() + timedelta(days=30))
    decisions = ManagementReviewDecisionFactory.create_batch(2, review=closed)
    client = FakeClient(_plan(
        _step("list_management_reviews", status="closed", limit=1),
        _step("list_management_review_decisions", review_id="$1.id", limit=5),
    ), summary="Deux décisions ont été prises.")
    outcome = AssistantEngine(superuser, language="fr", client=client).ask(
        "Quelles décisions ont été prises lors de la dernière revue de direction ?"
    )

    assert [run.tool for run in outcome.tool_runs] == [
        "list_management_reviews",
        "list_management_review_decisions",
    ]
    assert outcome.tool_runs[1].arguments["review_id"] == str(closed.pk)
    assert {f"/reports/decisions/{d.pk}/" for d in decisions} == {
        card["url"] for card in outcome.tool_runs[1].cards
    }
    assert outcome.summary == "Deux décisions ont été prises."
    assert not outcome.degraded
    # Single planning call: sequencing is engine-side.
    assert len(client.json_calls) == 1


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_placeholder_falls_back_when_status_filter_matches_nothing(superuser):
    """A held-but-never-closed review must still be found: the engine retries
    the parent step without its status filter when it returns nothing."""
    held = ManagementReviewFactory(status="held", held_date=date.today() - timedelta(days=10))
    ManagementReviewDecisionFactory(review=held)
    client = FakeClient(_plan(
        _step("list_management_reviews", status="closed", limit=1),
        _step("list_management_review_decisions", review_id="$1.id", limit=5),
    ))
    outcome = AssistantEngine(superuser, client=client).ask("Décisions de la dernière revue ?")
    assert outcome.tool_runs[1].arguments["review_id"] == str(held.pk)
    assert outcome.tool_runs[0].arguments == {"limit": 1}
    assert outcome.tool_runs[1].cards


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_unresolvable_placeholder_is_refused(superuser):
    client = FakeClient(_plan(
        _step("list_management_review_decisions", review_id="$1.id", limit=5),
    ))
    outcome = AssistantEngine(superuser, client=client).ask("Décisions ?")
    assert outcome.tool_runs == []
    assert outcome.refused_tools == ["list_management_review_decisions"]


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_non_allowlisted_tool_is_refused(superuser):
    client = FakeClient(_plan(_step("delete_risk", id="x")))
    outcome = AssistantEngine(superuser, client=client).ask("delete everything")
    assert outcome.refused_tools == ["delete_risk"]
    assert outcome.tool_runs == []
    assert outcome.summary is None


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_hallucinated_literal_id_is_refused(superuser):
    """A literal id that comes from nowhere (e.g. copied from the prompt
    examples) must never reach a tool."""
    ManagementReviewFactory(status="closed", held_date=date.today())
    client = FakeClient(_plan(
        _step("list_management_review_decisions", review_id="9f31", limit=5),
    ))
    outcome = AssistantEngine(superuser, client=client).ask("Décisions de la dernière revue ?")
    assert outcome.tool_runs == []
    assert outcome.refused_tools == ["list_management_review_decisions"]


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_id_pasted_in_the_question_is_allowed(superuser):
    review = ManagementReviewFactory(status="closed", held_date=date.today())
    ManagementReviewDecisionFactory(review=review)
    client = FakeClient(_plan(
        _step("list_management_review_decisions", review_id=str(review.pk), limit=5),
    ))
    outcome = AssistantEngine(superuser, client=client).ask(
        f"Décisions de la revue {review.pk} ?"
    )
    assert outcome.tool_runs[0].error is None
    assert outcome.tool_runs[0].cards


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_permission_denied_is_flagged_without_data():
    user = UserFactory()  # no group, no permission
    ManagementReviewFactory()
    client = FakeClient(_plan(_step("list_management_reviews", limit=5)))
    outcome = AssistantEngine(user, client=client).ask("Dernière revue ?")
    run = outcome.tool_runs[0]
    assert run.error == PERMISSION_DENIED
    assert run.records == []
    assert run.cards == []
    # No successful run: no summary call was made.
    assert client.text_calls == []
    assert outcome.summary is None


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_arguments_are_sanitized_and_limit_clamped(superuser):
    ManagementReviewFactory(status="held", held_date=date.today())
    client = FakeClient(_plan(
        _step("list_management_reviews", status="held", evil="rm -rf", limit=50),
    ))
    outcome = AssistantEngine(superuser, client=client).ask("Revues tenues ?")
    assert outcome.tool_runs[0].arguments == {"status": "held", "limit": 5}


@override_settings(AI_ASSISTANT_ENABLED=True, AI_ASSISTANT_MAX_TOOL_ROUNDS=2)
@pytest.mark.django_db
def test_plan_longer_than_max_steps_is_truncated(superuser):
    client = FakeClient(_plan(
        _step("list_management_reviews", limit=5),
        _step("list_management_reviews", limit=5),
        _step("list_management_reviews", limit=5),
    ))
    outcome = AssistantEngine(superuser, client=client).ask("Boucle ?")
    assert len(outcome.tool_runs) == 2
    assert client.json_calls[0]["schema"]["properties"]["steps"]["maxItems"] == 2


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_summary_failure_degrades_but_keeps_cards(superuser):
    ManagementReviewFactory(status="held", held_date=date.today())
    client = FakeClient(
        _plan(_step("list_management_reviews", limit=5)),
        summary=OllamaUnreachable("down"),
    )
    outcome = AssistantEngine(superuser, client=client).ask("Revues ?")
    assert outcome.degraded is True
    assert outcome.summary is None
    assert outcome.tool_runs[0].cards


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_summary_payload_contains_no_identifiers(superuser):
    review = ManagementReviewFactory(status="closed", held_date=date.today())
    ManagementReviewDecisionFactory(review=review)
    client = FakeClient(_plan(_step("list_management_reviews", limit=5)))
    AssistantEngine(superuser, client=client).ask("Dernière revue ?")
    data_message = client.text_calls[0][-1]["content"]
    assert str(review.pk) not in data_message
    assert '"id"' not in data_message
    # Human-readable fields are still there.
    assert review.reference in data_message


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_empty_plan_ends_quietly(superuser):
    client = FakeClient(_plan())
    outcome = AssistantEngine(superuser, client=client).ask("Bonjour !")
    assert outcome.tool_runs == []
    assert outcome.summary is None


@override_settings(AI_ASSISTANT_ENABLED=False)
@pytest.mark.django_db
def test_disabled_flag_raises():
    with pytest.raises(AssistantDisabled):
        AssistantEngine(UserFactory(), client=FakeClient(_plan())).ask("test")


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_as_dict_shape(superuser):
    review = ManagementReviewFactory(status="closed", held_date=date.today())
    ManagementReviewDecisionFactory(review=review)
    client = FakeClient(_plan(
        _step("list_management_reviews", status="closed", limit=1),
        _step("list_management_review_decisions", review_id="$1.id", limit=5),
    ))
    outcome = AssistantEngine(superuser, language="fr", client=client).ask("Décisions ?")
    data = outcome.as_dict()
    assert data["language"] == "fr"
    assert data["summary"] == "Summary sentence."
    assert data["results"][1]["tool"] == "list_management_review_decisions"
    record = data["results"][1]["records"][0]
    assert set(record) == {"title", "subtitle", "url", "icon"}

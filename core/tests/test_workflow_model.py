"""Tests for the BaseModel lifecycle API.

Exercised through a concrete model (context.Issue, on the default lifecycle).
"""

import pytest

from accounts.tests.factories import UserFactory
from context.models import Issue
from context.tests.factories import IssueFactory
from core.lifecycle import IllegalTransitionError, LifecycleProtectedError, resolve_lifecycle


@pytest.mark.django_db
class TestLifecycleDefaults:
    def test_new_object_is_draft(self):
        issue = IssueFactory()
        assert issue.workflow_state == "draft"
        assert issue.counts_in_reports is False
        assert issue.is_linkable is False
        assert issue.is_deletable is True

    def test_resolves_to_default_lifecycle(self):
        assert resolve_lifecycle(Issue).name == "default"

    def test_validated_state_counts_and_links(self):
        issue = IssueFactory(workflow_state="validated")
        assert issue.workflow_state == "validated"
        assert issue.counts_in_reports is True
        assert issue.is_linkable is True
        assert issue.is_deletable is False


@pytest.mark.django_db
class TestTransitions:
    def test_submit_moves_to_pending(self):
        user = UserFactory()
        issue = IssueFactory()
        issue.transition_to("pending", user)
        assert issue.workflow_state == "pending"
        assert issue.counts_in_reports is False  # pending does not count in reports

    def test_pending_is_not_clobbered_by_save(self):
        user = UserFactory()
        issue = IssueFactory()
        issue.transition_to("pending", user)
        issue.refresh_from_db()
        assert issue.workflow_state == "pending"

    def test_validate_moves_to_validated(self):
        user = UserFactory()
        issue = IssueFactory()
        issue.transition_to("pending", user)
        issue.transition_to("validated", user)
        assert issue.workflow_state == "validated"
        assert issue.counts_in_reports is True

    def test_archive_stops_counting(self):
        user = UserFactory()
        issue = IssueFactory()
        issue.transition_to("pending", user)
        issue.transition_to("validated", user)
        issue.transition_to("archived", user)
        assert issue.workflow_state == "archived"
        assert issue.counts_in_reports is False  # archived no longer counts in reports

    def test_illegal_transition_raises_and_keeps_state(self):
        issue = IssueFactory()
        with pytest.raises(IllegalTransitionError):
            issue.transition_to("validated")
        assert issue.workflow_state == "draft"

    def test_available_transitions_lists_outgoing(self):
        issue = IssueFactory()
        assert {t.target for t in issue.available_transitions()} == {"pending"}
        issue.transition_to("pending")
        assert {t.target for t in issue.available_transitions()} == {"draft", "validated"}


@pytest.mark.django_db
def test_reportable_and_linkable_queryset_helpers():
    from core.lifecycle import linkable, reportable

    IssueFactory()  # draft
    IssueFactory(workflow_state="validated")
    assert reportable(Issue.objects.all()).count() == 1
    assert linkable(Issue.objects.all()).count() == 1


@pytest.mark.django_db
def test_linkable_or_linked_keeps_existing_links():
    from core.lifecycle import linkable_or_linked

    draft = IssueFactory()
    validated = IssueFactory(workflow_state="validated")
    archived = IssueFactory(workflow_state="validated")
    archived.transition_to("archived")

    # Without a linked queryset: only linkable (validated) elements.
    offered = linkable_or_linked(Issue.objects.all())
    assert set(offered) == {validated}

    # An already-linked archived element stays offered so edits keep the link.
    offered = linkable_or_linked(
        Issue.objects.all(), Issue.objects.filter(pk=archived.pk)
    )
    assert set(offered) == {validated, archived}
    assert draft not in offered


@pytest.mark.django_db
class TestDeletionGuard:
    def test_draft_object_can_be_deleted(self):
        issue = IssueFactory()  # draft, deletable
        pk = issue.pk
        issue.delete()
        assert not Issue.objects.filter(pk=pk).exists()

    def test_validated_object_cannot_be_deleted(self):
        issue = IssueFactory(workflow_state="validated")  # not deletable
        with pytest.raises(LifecycleProtectedError):
            issue.delete()
        assert Issue.objects.filter(pk=issue.pk).exists()

    def test_pending_object_cannot_be_deleted(self):
        issue = IssueFactory()
        issue.transition_to("pending")
        with pytest.raises(LifecycleProtectedError):
            issue.delete()
        assert Issue.objects.filter(pk=issue.pk).exists()

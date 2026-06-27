"""Tests for the BaseModel lifecycle API and the is_approved <-> workflow_state sync.

Exercised through a concrete model (context.Issue, on the default workflow).
"""

import pytest

from accounts.tests.factories import UserFactory
from context.models import Issue
from context.tests.factories import IssueFactory
from core.models import VersioningConfig
from core.workflow import (
    DEFAULT_WORKFLOW,
    WORKFLOW_REGISTRY,
    IllegalTransitionError,
    LifecycleProtectedError,
    State,
    Transition,
    Workflow,
    register_workflow,
)

# A throwaway workflow registered once, used by the assignment test below.
_ASSIGN_WF = "test_assignment_workflow"
if _ASSIGN_WF not in WORKFLOW_REGISTRY:
    register_workflow(
        Workflow(
            _ASSIGN_WF,
            [
                State("open", "Open", is_initial=True),
                State("done", "Done", is_terminal=True, counts_in_reports=True),
            ],
            [Transition("open", "done", "Finish")],
        )
    )


@pytest.mark.django_db
class TestLifecycleDefaults:
    def test_new_object_is_draft(self):
        issue = IssueFactory()
        assert issue.workflow_state == "draft"
        assert issue.counts_in_reports is False
        assert issue.is_linkable is False
        assert issue.is_deletable is True

    def test_get_workflow_is_default(self):
        assert IssueFactory().get_workflow() is DEFAULT_WORKFLOW


@pytest.mark.django_db
class TestApprovalSync:
    def test_creating_approved_syncs_to_validated(self):
        issue = IssueFactory(is_approved=True)
        assert issue.workflow_state == "validated"
        assert issue.counts_in_reports is True
        assert issue.is_linkable is True
        assert issue.is_deletable is False

    def test_legacy_approve_promotes_state(self):
        issue = IssueFactory()
        assert issue.workflow_state == "draft"
        issue.is_approved = True
        issue.save()
        assert issue.workflow_state == "validated"

    def test_legacy_unapprove_resets_state(self):
        issue = IssueFactory(is_approved=True)
        assert issue.workflow_state == "validated"
        issue.is_approved = False
        issue.save()
        assert issue.workflow_state == "draft"

    def test_update_fields_save_persists_state_sync(self):
        issue = IssueFactory()
        issue.is_approved = True
        issue.save(update_fields=["is_approved", "approved_at"])
        issue.refresh_from_db()
        assert issue.workflow_state == "validated"


@pytest.mark.django_db
class TestTransitions:
    def test_submit_moves_to_pending(self):
        user = UserFactory()
        issue = IssueFactory()
        issue.transition_to("pending", user)
        assert issue.workflow_state == "pending"
        assert issue.is_approved is False  # pending does not count in reports

    def test_pending_is_not_clobbered_by_sync(self):
        user = UserFactory()
        issue = IssueFactory()
        issue.transition_to("pending", user)
        issue.refresh_from_db()
        assert issue.workflow_state == "pending"

    def test_validate_stamps_approval(self):
        user = UserFactory()
        issue = IssueFactory()
        issue.transition_to("pending", user)
        issue.transition_to("validated", user)
        assert issue.workflow_state == "validated"
        assert issue.is_approved is True
        assert issue.approved_by == user
        assert issue.approved_at is not None

    def test_archive_clears_approval(self):
        user = UserFactory()
        issue = IssueFactory()
        issue.transition_to("pending", user)
        issue.transition_to("validated", user)
        issue.transition_to("archived", user)
        assert issue.workflow_state == "archived"
        assert issue.is_approved is False  # archived no longer counts in reports

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
class TestWorkflowAssignment:
    def setup_method(self):
        VersioningConfig.clear_cache()

    def teardown_method(self):
        VersioningConfig.clear_cache()

    def test_blank_assignment_uses_default(self):
        VersioningConfig.objects.create(model_name="context.issue", workflow_name="")
        assert IssueFactory().get_workflow() is DEFAULT_WORKFLOW

    def test_unknown_assignment_falls_back_to_default(self):
        VersioningConfig.objects.create(model_name="context.issue", workflow_name="nope")
        assert IssueFactory().get_workflow() is DEFAULT_WORKFLOW

    def test_assigned_workflow_is_resolved(self):
        VersioningConfig.objects.create(model_name="context.issue", workflow_name=_ASSIGN_WF)
        assert IssueFactory().get_workflow().name == _ASSIGN_WF


@pytest.mark.django_db
def test_reportable_and_linkable_queryset_helpers():
    from core.workflow import linkable, reportable

    IssueFactory()  # draft
    IssueFactory(is_approved=True)  # validated
    assert reportable(Issue.objects.all()).count() == 1
    assert linkable(Issue.objects.all()).count() == 1


@pytest.mark.django_db
def test_linkable_or_linked_keeps_existing_links():
    from core.workflow import linkable_or_linked

    draft = IssueFactory()
    validated = IssueFactory(is_approved=True)
    archived = IssueFactory(is_approved=True)
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
        issue = IssueFactory(is_approved=True)  # validated, not deletable
        with pytest.raises(LifecycleProtectedError):
            issue.delete()
        assert Issue.objects.filter(pk=issue.pk).exists()

    def test_pending_object_cannot_be_deleted(self):
        issue = IssueFactory()
        issue.transition_to("pending")
        with pytest.raises(LifecycleProtectedError):
            issue.delete()
        assert Issue.objects.filter(pk=issue.pk).exists()

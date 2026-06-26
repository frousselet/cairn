"""Tests for the rebuilt lifecycle engine (core.lifecycle) and its service."""

import pytest
from django import forms
from django.core.exceptions import ValidationError

from context.constants import RoleType
from context.models.role import Role
from context.tests.factories import IssueFactory, ScopeFactory
from core.lifecycle import (
    ANY,
    CommentRequiredError,
    IllegalTransitionError,
    Lifecycle,
    LifecycleError,
    Step,
    StepKind,
    Transition,
    TransitionNotAllowedError,
    UnknownStepError,
    archived_step,
    available_transitions,
    draft_step,
    user_can_perform,
    validate_transition,
)


# --- builders ---------------------------------------------------------------


def linear_lifecycle():
    """Draft -> Active -> Suspended, plus 'any -> Archived' (the exit)."""
    return Lifecycle(
        name="test_linear",
        steps=[
            draft_step(),
            Step("active", "Active", kind=StepKind.INTERMEDIATE, counts_in_reports=True, linkable=True),
            Step("suspended", "Suspended", kind=StepKind.INTERMEDIATE, counts_in_reports=True),
            archived_step(),
        ],
        transitions=[
            Transition("active", source="draft", label="Activate"),
            Transition("suspended", source="active", label="Suspend"),
            Transition("active", source="suspended", label="Reactivate"),
            Transition("archived", source=ANY, label="Archive"),  # from any state
            Transition("draft", source="archived", label="Restore"),  # leaving archived
        ],
    )


# --- schema validation ------------------------------------------------------


class TestLifecycleValidation:
    def test_requires_exactly_one_draft(self):
        with pytest.raises(LifecycleError, match="exactly one Draft"):
            Lifecycle("x", [archived_step()], [])
        with pytest.raises(LifecycleError, match="exactly one Draft"):
            Lifecycle("x", [draft_step("d1"), draft_step("d2"), archived_step()], [])

    def test_requires_an_archived_step(self):
        with pytest.raises(LifecycleError, match="at least one Archived"):
            Lifecycle("x", [draft_step(), Step("a", "A")], [])

    def test_rejects_duplicate_codes(self):
        with pytest.raises(LifecycleError, match="duplicate"):
            Lifecycle("x", [draft_step(), draft_step()], [])  # both "draft" code

    def test_rejects_unknown_transition_endpoints(self):
        with pytest.raises(LifecycleError, match="target"):
            Lifecycle("x", [draft_step(), archived_step()], [Transition("ghost", source="draft")])
        with pytest.raises(LifecycleError, match="source"):
            Lifecycle("x", [draft_step(), archived_step()], [Transition("archived", source="ghost")])

    def test_wildcard_source_is_valid(self):
        lc = linear_lifecycle()
        assert lc.initial_step.code == "draft"
        assert [s.code for s in lc.archived_steps] == ["archived"]


# --- traversal --------------------------------------------------------------


class TestTraversal:
    def test_transitions_from_includes_wildcard_excludes_self(self):
        lc = linear_lifecycle()
        targets = {t.target for t in lc.transitions_from("active")}
        # active -> suspended (explicit) and any -> archived (wildcard)
        assert targets == {"suspended", "archived"}

    def test_from_draft(self):
        lc = linear_lifecycle()
        assert {t.target for t in lc.transitions_from("draft")} == {"active", "archived"}

    def test_can_leave_archived_restore(self):
        lc = linear_lifecycle()
        assert {t.target for t in lc.transitions_from("archived")} == {"draft"}

    def test_find_transition_prefers_explicit_over_wildcard(self):
        lc = Lifecycle(
            "x",
            [draft_step(), archived_step()],
            [
                Transition("archived", source=ANY, label="any"),
                Transition("archived", source="draft", label="explicit"),
            ],
        )
        assert lc.find_transition("draft", "archived").label == "explicit"

    def test_governance_code_sets(self):
        lc = linear_lifecycle()
        assert lc.reportable_step_codes == frozenset({"active", "suspended"})
        assert lc.linkable_step_codes == frozenset({"active"})
        assert lc.deletable_step_codes == frozenset({"draft"})


# --- validate_transition ----------------------------------------------------


class TestValidateTransition:
    def test_unknown_step(self):
        lc = linear_lifecycle()
        with pytest.raises(UnknownStepError):
            validate_transition(lc, "nope", "active")

    def test_illegal_move(self):
        lc = linear_lifecycle()
        with pytest.raises(IllegalTransitionError):
            validate_transition(lc, "draft", "suspended")

    def test_comment_required(self):
        lc = Lifecycle(
            "x",
            [draft_step(), archived_step()],
            [Transition("archived", source="draft", requires_comment=True)],
        )
        with pytest.raises(CommentRequiredError):
            validate_transition(lc, "draft", "archived", comment=" ")
        # a non-empty comment passes
        assert validate_transition(lc, "draft", "archived", comment="done").target == "archived"

    def test_wildcard_archive_from_any_state(self):
        lc = linear_lifecycle()
        assert validate_transition(lc, "suspended", "archived").label == "Archive"


# --- restriction (roles / users), DB-backed --------------------------------


@pytest.mark.django_db
class TestRestrictions:
    def test_open_transition_allows_anyone(self):
        from accounts.tests.factories import UserFactory

        lc = linear_lifecycle()
        t = lc.find_transition("draft", "active")
        issue = IssueFactory()
        assert user_can_perform(t, issue, UserFactory()) is True

    def test_superuser_always_passes_restricted(self):
        from accounts.tests.factories import UserFactory

        t = Transition("archived", source="draft", allowed_roles=(RoleType.GOVERNANCE,))
        issue = IssueFactory()
        assert user_can_perform(t, issue, UserFactory(is_superuser=True)) is True

    def test_role_restriction_scoped(self):
        from accounts.tests.factories import UserFactory

        scope = ScopeFactory()
        issue = IssueFactory(scopes=[scope])
        member = UserFactory()
        outsider = UserFactory()
        role = Role.objects.create(name="CISO", type=RoleType.GOVERNANCE)
        role.scopes.add(scope)
        role.assigned_users.add(member)

        t = Transition("archived", source="draft", allowed_roles=(RoleType.GOVERNANCE,))
        assert user_can_perform(t, issue, member) is True
        assert user_can_perform(t, issue, outsider) is False

    def test_role_restriction_respects_scope_isolation(self):
        from accounts.tests.factories import UserFactory

        scope_a = ScopeFactory()
        scope_b = ScopeFactory()
        issue = IssueFactory(scopes=[scope_a])
        member = UserFactory()
        role = Role.objects.create(name="CISO", type=RoleType.GOVERNANCE)
        role.scopes.add(scope_b)  # different scope than the issue
        role.assigned_users.add(member)

        t = Transition("archived", source="draft", allowed_roles=(RoleType.GOVERNANCE,))
        assert user_can_perform(t, issue, member) is False

    def test_allowed_users_resolver(self):
        from accounts.tests.factories import UserFactory

        owner = UserFactory()
        other = UserFactory()
        issue = IssueFactory(created_by=owner)
        t = Transition("archived", source="draft", allowed_users=lambda obj: [obj.created_by])
        assert user_can_perform(t, issue, owner) is True
        assert user_can_perform(t, issue, other) is False

    def test_available_transitions_filtered_by_user(self):
        from accounts.tests.factories import UserFactory

        scope = ScopeFactory()
        issue = IssueFactory(scopes=[scope])
        user = UserFactory()
        lc = Lifecycle(
            "restricted",
            [draft_step(), archived_step()],
            [Transition("archived", source="draft", allowed_roles=(RoleType.GOVERNANCE,))],
        )
        # user holds no role -> the restricted transition is hidden
        assert available_transitions(lc, "draft", instance=issue, user=user) == ()
        with pytest.raises(TransitionNotAllowedError):
            validate_transition(lc, "draft", "archived", instance=issue, user=user)


# --- service: perform + record event ---------------------------------------


class _CommentForm(forms.Form):
    reason = forms.CharField()

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)


@pytest.mark.django_db
class TestPerformTransition:
    def test_sets_step_and_records_event(self):
        from accounts.tests.factories import UserFactory
        from core.lifecycle_service import perform_transition
        from core.models import LifecycleEvent

        lc = linear_lifecycle()
        issue = IssueFactory()  # workflow_state defaults to "draft"
        user = UserFactory()
        event, transition = perform_transition(
            issue, "active", user=user, lifecycle=lc, enforce_permission=False
        )
        issue.refresh_from_db()
        assert issue.workflow_state == "active"
        assert transition.target == "active"
        assert event.from_step == "draft"
        assert event.to_step == "active"
        assert event.actor == user
        assert LifecycleEvent.for_instance(issue).count() == 1

    def test_form_required_and_stored(self):
        from core.lifecycle_service import perform_transition

        lc = Lifecycle(
            "with_form",
            [draft_step(), archived_step()],
            [Transition("archived", source="draft", form_class=_CommentForm)],
        )
        issue = IssueFactory()
        # missing form data -> ValidationError
        with pytest.raises(ValidationError):
            perform_transition(issue, "archived", lifecycle=lc, enforce_permission=False)
        # valid form data -> stored on the event
        event, _ = perform_transition(
            issue, "archived", lifecycle=lc, data={"reason": "obsolete"}, enforce_permission=False
        )
        assert event.form_data == {"reason": "obsolete"}
        issue.refresh_from_db()
        assert issue.workflow_state == "archived"

    def test_permission_enforced(self):
        from accounts.tests.factories import UserFactory
        from core.lifecycle_service import perform_transition

        lc = Lifecycle(
            "guarded",
            [draft_step(), archived_step()],
            [Transition("archived", source="draft", allowed_roles=(RoleType.CONTROL,))],
        )
        issue = IssueFactory()
        with pytest.raises(TransitionNotAllowedError):
            perform_transition(
                issue, "archived", user=UserFactory(), lifecycle=lc, enforce_permission=True
            )

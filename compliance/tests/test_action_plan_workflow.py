"""Tests for the action plan lifecycle (standardised core.lifecycle engine)."""

import pytest

from accounts.tests.factories import UserFactory
from compliance.constants import ActionPlanStatus
from compliance.models import ActionPlanTransition, ComplianceActionPlan
from compliance.tests.factories import ComplianceActionPlanFactory
from core.lifecycle import (
    CommentRequiredError,
    IllegalTransitionError,
    get_lifecycle,
    resolve_lifecycle,
)

pytestmark = pytest.mark.django_db


class TestActionPlanLifecycleDefinition:
    def test_model_resolves_to_specific_lifecycle(self):
        lifecycle = resolve_lifecycle(ComplianceActionPlan)
        assert lifecycle.name == "action_plan"
        assert lifecycle.initial_step.code == "new"

    def test_step_codes_match_status_values(self):
        lifecycle = resolve_lifecycle(ComplianceActionPlan)
        assert {s.code for s in lifecycle.steps} == {s.value for s in ActionPlanStatus}

    def test_governance_flags(self):
        lifecycle = get_lifecycle("action_plan")
        assert lifecycle.deletable_step_codes == {"new", "to_define"}
        assert lifecycle.linkable_step_codes == {
            "to_implement", "implementation_to_validate", "validated",
        }
        assert lifecycle.reportable_step_codes == {
            "to_validate", "to_implement", "implementation_to_validate",
            "validated", "closed",
        }

    def test_terminal_states(self):
        lifecycle = resolve_lifecycle(ComplianceActionPlan)
        assert {s.code for s in lifecycle.steps if s.is_archived} == {"closed", "cancelled"}

    def test_refusals_require_a_comment(self):
        lifecycle = resolve_lifecycle(ComplianceActionPlan)
        assert lifecycle.find_transition("to_validate", "to_define").requires_comment is True
        assert lifecycle.find_transition("implementation_to_validate", "to_implement").requires_comment is True


class TestActionPlanStateSync:
    def test_creation_aligns_workflow_state_with_status(self):
        plan = ComplianceActionPlanFactory()  # status=new
        assert plan.workflow_state == "new"
        plan2 = ComplianceActionPlanFactory(status=ActionPlanStatus.VALIDATED)
        assert plan2.workflow_state == "validated"

    def test_legacy_status_write_mirrors_to_workflow_state(self):
        plan = ComplianceActionPlanFactory()
        plan.status = ActionPlanStatus.TO_DEFINE
        plan.save()
        plan.refresh_from_db()
        assert plan.workflow_state == "to_define"

    def test_lifecycle_write_mirrors_to_status(self):
        plan = ComplianceActionPlanFactory()
        plan.workflow_state = "to_define"
        plan.save()
        plan.refresh_from_db()
        assert plan.status == "to_define"


class TestActionPlanTransitions:
    def test_legacy_contract_happy_path(self):
        user = UserFactory()
        plan = ComplianceActionPlanFactory()
        plan.transition_to(ActionPlanStatus.TO_DEFINE, user)
        plan.refresh_from_db()
        assert plan.status == "to_define"
        assert plan.workflow_state == "to_define"
        log = ActionPlanTransition.objects.get(action_plan=plan)
        assert log.from_status == "new"
        assert log.to_status == "to_define"
        assert log.performed_by == user
        assert log.is_refusal is False

    def test_illegal_transition_raises_valueerror(self):
        user = UserFactory()
        plan = ComplianceActionPlanFactory()
        with pytest.raises(ValueError):
            plan.transition_to(ActionPlanStatus.VALIDATED, user)
        with pytest.raises(IllegalTransitionError):
            plan.transition_to(ActionPlanStatus.VALIDATED, user)

    def test_refusal_requires_comment(self):
        user = UserFactory()
        plan = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        with pytest.raises(ValueError):
            plan.transition_to(ActionPlanStatus.TO_DEFINE, user)
        with pytest.raises(CommentRequiredError):
            plan.transition_to(ActionPlanStatus.TO_DEFINE, user, comment="  ")
        plan.transition_to(ActionPlanStatus.TO_DEFINE, user, comment="Not specific enough")
        log = ActionPlanTransition.objects.get(action_plan=plan)
        assert log.is_refusal is True
        assert log.comment == "Not specific enough"

    def test_closing_sets_completion_fields(self):
        user = UserFactory()
        plan = ComplianceActionPlanFactory(status=ActionPlanStatus.VALIDATED)
        plan.transition_to(ActionPlanStatus.CLOSED, user)
        plan.refresh_from_db()
        assert plan.status == "closed"
        assert plan.progress_percentage == 100
        assert plan.completion_date is not None

    def test_cancel_from_any_active_state(self):
        user = UserFactory()
        plan = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_IMPLEMENT)
        plan.transition_to(ActionPlanStatus.CANCELLED, user)
        plan.refresh_from_db()
        assert plan.workflow_state == "cancelled"

    def test_terminal_state_locked(self):
        user = UserFactory()
        plan = ComplianceActionPlanFactory(status=ActionPlanStatus.CLOSED)
        with pytest.raises(ValueError):
            plan.transition_to(ActionPlanStatus.VALIDATED, user)


class TestActionPlanGovernance:
    def test_only_drafting_states_deletable(self):
        plan = ComplianceActionPlanFactory()  # new
        assert plan.is_deletable is True
        validated = ComplianceActionPlanFactory(status=ActionPlanStatus.VALIDATED)
        assert validated.is_deletable is False

    def test_delete_guard_applies(self):
        from core.workflow import LifecycleProtectedError

        plan = ComplianceActionPlanFactory(status=ActionPlanStatus.VALIDATED)
        with pytest.raises(LifecycleProtectedError):
            plan.delete()

    def test_linkable_uses_specific_states(self):
        from core.workflow import linkable

        ComplianceActionPlanFactory()  # new: not linkable
        live = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_IMPLEMENT)
        assert set(linkable(ComplianceActionPlan.objects.all())) == {live}


class TestActionPlanGenericMCPTool:
    def setup_method(self):
        import json

        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        self.srv = McpServer()
        register_all_tools(self.srv)
        self.superuser = UserFactory(is_superuser=True)
        self._json = json

    def _call(self, user, name, arguments=None):
        result = self.srv.handle_request(self._json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }), user)
        return self._json.loads(result["result"]["content"][0]["text"])

    def test_generic_transition_drives_status_and_logs(self):
        plan = ComplianceActionPlanFactory()
        result = self._call(
            self.superuser, "transition_action_plan",
            {"id": str(plan.pk), "target_state": "to_define"},
        )
        assert result["workflow_state"] == "to_define"
        plan.refresh_from_db()
        assert plan.status == "to_define"
        assert ActionPlanTransition.objects.filter(action_plan=plan).count() == 1

    def test_generic_refusal_requires_comment(self):
        plan = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        result = self._call(
            self.superuser, "transition_action_plan",
            {"id": str(plan.pk), "target_state": "to_define"},
        )
        assert "error" in result
        result = self._call(
            self.superuser, "transition_action_plan",
            {"id": str(plan.pk), "target_state": "to_define", "comment": "Refused: too vague"},
        )
        assert result["workflow_state"] == "to_define"

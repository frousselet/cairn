# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The MCP surface of module 8 (README §6) : the same RG-CTL rules as the web
form and the REST API, with the MCP client acting as the authenticated user."""
import datetime

import pytest
from django.utils import timezone

from accounts.tests.factories import UserFactory
from compliance.constants import FindingSource
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from context.tests.factories import ScopeFactory
from controls.constants import (
    CONTROL_DRAFT,
    CONTROL_IMPLEMENTED,
    CONTROL_PLANNED,
    RUN_IN_REVIEW,
    RUN_VALIDATED,
    TEST_ACTIVE,
    ControlEffectiveness,
    RunResult,
)
from controls.models import Control, ControlTest, ControlTestRun
from controls.tests.factories import (
    ControlFactory,
    ControlTestFactory,
    ControlTestRunFactory,
    active_test,
    implemented_control,
    validated_run,
)
from controls.tests.test_api import (
    CONTROL_APPROVER,
    CONTROL_CONTRIBUTOR,
    CONTROL_READ,
    TEST_APPROVER,
    TEST_CONTRIBUTOR,
    TEST_READ,
    make_user,
    scoped_control,
    scoped_requirement,
    upload,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def server():
    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    instance = McpServer()
    register_all_tools(instance)
    return instance


@pytest.fixture
def call(server):
    def _call(tool_name, user, /, **arguments):
        return server.get_tool(tool_name)["handler"](user, arguments)
    return _call


@pytest.fixture
def superuser():
    return UserFactory(is_superuser=True)


def is_error(result):
    return isinstance(result, dict) and result.get("isError") is True


def error_text(result):
    return result["content"][0]["text"]


def item_ids(result):
    return {item["id"] for item in result["items"]}


CRUD = {
    f"{verb}_{entity}"
    for entity in ("control", "control_test", "control_test_run")
    for verb in ("get", "create", "update", "delete", "transition")
} | {
    name
    for entity in ("control", "control_test", "control_test_run")
    for name in (f"list_{entity}s", f"batch_create_{entity}s", f"{entity}_allowed_transitions", f"get_{entity}_history")
}


class TestRegistry:
    EXPECTED = CRUD | {
        "create_controls_from_requirements", "get_control_effectiveness", "list_overdue_control_tests",
        "list_my_control_tests_due", "raise_finding_from_run", "get_requirement_coverage",
    }

    def test_every_controls_tool_is_registered(self, server):
        names = {tool["name"] for tool in server.iter_tools()}
        assert self.EXPECTED <= names, sorted(self.EXPECTED - names)

    def test_every_tool_and_parameter_is_described(self, server):
        for name in self.EXPECTED:
            tool = server.get_tool(name)
            assert tool["description"].strip(), name
            for param, schema in tool["inputSchema"].get("properties", {}).items():
                assert schema.get("description"), (name, param)

    def test_derived_fields_are_not_writable(self, server):
        for name in ("create_control", "update_control"):
            props = server.get_tool(name)["inputSchema"]["properties"]
            assert "effectiveness" not in props and "effectiveness_updated_at" not in props
        for name in ("create_control_test", "update_control_test"):
            props = server.get_tool(name)["inputSchema"]["properties"]
            assert "next_due_date" not in props and "activated_on" not in props
        props = server.get_tool("update_control_test_run")["inputSchema"]["properties"]
        assert "reviewed_by_id" not in props and "test_id" not in props

    def test_help_has_a_controls_topic(self, call, superuser):
        guide = call("help", superuser)
        assert "CTRL" in guide and "CTST" in guide and "CTRN" in guide
        topic = call("help", superuser, topic="controls")
        assert "RG-CTL-11" in topic and "raise_finding_from_run" in topic


class TestPermissionsAndScopes:
    def test_tools_require_their_permission(self, call):
        nobody = make_user(scopes=[ScopeFactory()])
        control = ControlFactory()
        run = validated_run(result=RunResult.FAIL)
        expectations = {
            ("list_controls", "controls.control.read"): {},
            ("create_control", "controls.control.create"): {"name": "x", "description": "y"},
            ("get_control_effectiveness", "controls.control.read"): {"control_id": str(control.pk)},
            ("get_requirement_coverage", "controls.control.read"): {"framework_id": str(FrameworkFactory().pk)},
            ("create_controls_from_requirements", "controls.control.create"): {"framework_id": str(FrameworkFactory().pk)},
            ("list_control_tests", "controls.test.read"): {},
            ("list_overdue_control_tests", "controls.test.read"): {},
            ("list_my_control_tests_due", "controls.test.read"): {},
            ("get_control_test_run", "controls.test.read"): {"id": str(run.pk)},
            ("create_control_test_run", "controls.test.create"): {"test_id": str(run.test_id)},
            ("raise_finding_from_run", "controls.test.approve"): {"run_id": str(run.pk), "finding_type": "minor_nc"},
        }
        for (tool, codename), arguments in expectations.items():
            result = call(tool, nobody, **arguments)
            assert is_error(result) and codename in error_text(result), tool

    def test_lists_and_reads_are_scope_filtered(self, call):
        scope = ScopeFactory()
        mine = scoped_control(scope)
        theirs = scoped_control(ScopeFactory())
        my_run = validated_run(active_test(mine))
        their_run = validated_run(active_test(theirs))
        reader = make_user(*(CONTROL_READ + TEST_READ), scopes=[scope])
        assert item_ids(call("list_controls", reader)) == {str(mine.pk)}
        assert item_ids(call("list_control_tests", reader)) == {str(my_run.test_id)}
        assert item_ids(call("list_control_test_runs", reader)) == {str(my_run.pk)}
        assert is_error(call("get_control", reader, id=str(theirs.pk)))
        assert is_error(call("get_control_test_run", reader, id=str(their_run.pk)))
        assert is_error(call("get_control_effectiveness", reader, control_id=str(theirs.pk)))

    def test_links_must_be_in_scope_and_linkable(self, call):
        scope = ScopeFactory()
        contributor = make_user(*CONTROL_CONTRIBUTOR, scopes=[scope])
        base = {"name": "Access review", "description": "Quarterly.", "scope_ids": [str(scope.pk)]}
        for requirement in (scoped_requirement(ScopeFactory()), scoped_requirement(scope, workflow_state="draft")):
            result = call("create_control", contributor, **base, requirement_ids=[str(requirement.pk)])
            assert is_error(result) and "requirement_ids" in error_text(result)
        assert is_error(call("create_control", contributor, **{**base, "scope_ids": [str(ScopeFactory().pk)]}))
        linkable = scoped_requirement(scope)
        created = call("create_control", contributor, **base, requirement_ids=[str(linkable.pk)])
        assert not is_error(created), created
        control = Control.objects.get(pk=created["id"])
        assert list(control.requirements.all()) == [linkable]
        batch = call("batch_create_controls", contributor, items=[
            {**base, "requirement_ids": [str(scoped_requirement(ScopeFactory()).pk)]},
        ])
        assert is_error(batch)
        outside = scoped_requirement(ScopeFactory())
        refused = call("update_control", contributor, id=created["id"], requirement_ids=[str(outside.pk)])
        assert is_error(refused)
        assert list(control.requirements.all()) == [linkable]

    def test_a_co_owned_control_keeps_its_other_scopes(self, call):
        scope, other = ScopeFactory(), ScopeFactory()
        control = scoped_control(scope)
        control.scopes.add(other)
        contributor = make_user(*CONTROL_CONTRIBUTOR, scopes=[scope])
        kept = call("update_control", contributor, id=str(control.pk), scope_ids=[str(scope.pk), str(other.pk)])
        assert not is_error(kept), kept
        added = call("update_control", contributor, id=str(control.pk), scope_ids=[str(ScopeFactory().pk)])
        assert is_error(added)

    def test_tests_and_runs_cannot_target_out_of_scope_parents(self, call):
        scope = ScopeFactory()
        contributor = make_user(*TEST_CONTRIBUTOR, scopes=[scope])
        theirs = scoped_control(ScopeFactory())
        assert is_error(call("create_control_test", contributor, control_id=str(theirs.pk), name="t"))
        their_test = active_test(theirs)
        assert is_error(call("create_control_test_run", contributor, test_id=str(their_test.pk)))
        assert not ControlTestRun.objects.filter(test=their_test).exists()


class TestControlTools:
    def test_full_cycle_through_mcp(self, call):
        scope = ScopeFactory()
        owner = make_user(*(CONTROL_APPROVER + TEST_APPROVER), scopes=[scope])
        tester = make_user(*(CONTROL_READ + TEST_CONTRIBUTOR), scopes=[scope])
        created = call("create_control", owner, name="Encrypted backups", description="Off-site, AES-256.",
                       scope_ids=[str(scope.pk)], theme="technological")
        assert created["reference"].startswith("CTRL-") and created["workflow_state"] == CONTROL_DRAFT
        assert created["effectiveness"] == ControlEffectiveness.NOT_TESTED
        assert not is_error(call("transition_control", owner, id=created["id"], target_state=CONTROL_PLANNED))
        test = call("create_control_test", owner, control_id=created["id"], name="Restore drill",
                    procedure="Restore one backup.", acceptance_criteria="Restore succeeds.",
                    frequency_months=6, tester_id=str(tester.pk))
        assert test["reference"].startswith("CTST-")
        assert not is_error(call("transition_control_test", owner, id=test["id"], target_state=TEST_ACTIVE))
        run = call("create_control_test_run", tester, test_id=test["id"], result="pass")
        assert run["performed_by"] == str(tester.pk) and run["reference"].startswith("CTRN-")
        assert not is_error(call("transition_control_test_run", tester, id=run["id"], target_state=RUN_IN_REVIEW))
        validated = call("transition_control_test_run", owner, id=run["id"], target_state=RUN_VALIDATED)
        assert not is_error(validated), validated
        effectiveness = call("get_control_effectiveness", owner, control_id=created["id"])
        assert effectiveness["effectiveness"] == ControlEffectiveness.EFFECTIVE
        [active] = effectiveness["active_tests"]
        assert active["latest_validated_run"]["id"] == run["id"]
        assert active["latest_validated_run"]["reviewed_by_id"] == str(owner.pk)
        assert active["next_due_date"] == ControlTest.objects.get(pk=test["id"]).next_due_date.isoformat()

    def test_effectiveness_hides_the_tests_without_test_read(self, call):
        scope = ScopeFactory()
        control = scoped_control(scope)
        active_test(control)
        reader = make_user(*CONTROL_READ, scopes=[scope])
        result = call("get_control_effectiveness", reader, control_id=str(control.pk))
        assert result["active_tests"] is None

    def test_derived_effectiveness_cannot_be_written(self, call, superuser):
        control = implemented_control()
        call("update_control", superuser, id=str(control.pk), effectiveness=ControlEffectiveness.EFFECTIVE, name="New")
        control.refresh_from_db()
        assert control.name == "New"
        assert control.effectiveness == ControlEffectiveness.NOT_TESTED

    def test_list_filters(self, call, superuser):
        requirement = RequirementFactory()
        late = implemented_control()
        late.requirements.add(requirement)
        active_test(late, first_due_date=timezone.localdate() - datetime.timedelta(days=3))
        implemented_control()
        assert item_ids(call("list_controls", superuser, test_overdue=True)) == {str(late.pk)}
        assert item_ids(call("list_controls", superuser, requirement_id=str(requirement.pk))) == {str(late.pk)}
        assert len(call("list_controls", superuser, workflow_state=CONTROL_IMPLEMENTED)["items"]) == 2

    def test_delete_a_control_with_tests_is_a_tool_error(self, call, superuser):
        control = ControlFactory()
        ControlTestFactory(control=control)
        result = call("delete_control", superuser, id=str(control.pk))
        assert is_error(result) and "referenced" in error_text(result)
        assert Control.objects.filter(pk=control.pk).exists()
        bare = ControlFactory()
        assert call("delete_control", superuser, id=str(bare.pk))["deleted"] is True

    def test_create_controls_from_requirements(self, call):
        scope = ScopeFactory()
        framework = FrameworkFactory()
        framework.scopes.add(scope)
        fresh = RequirementFactory(framework=framework)
        covered = RequirementFactory(framework=framework)
        ControlFactory().requirements.add(covered)
        user = make_user(*(CONTROL_CONTRIBUTOR + ("compliance.framework.read",)), scopes=[scope])
        result = call("create_controls_from_requirements", user, framework_id=str(framework.pk))
        assert result["created_count"] == 1 and result["skipped_count"] == 1
        assert result["created"][0]["requirement_ids"] == [str(fresh.pk)]
        assert result["skipped"][0]["reason"] == "already_covered"
        assert result["created"][0]["scopes"] == [str(scope.pk)]
        no_framework = make_user(*CONTROL_CONTRIBUTOR, scopes=[scope])
        assert "compliance.framework.read" in error_text(
            call("create_controls_from_requirements", no_framework, framework_id=str(framework.pk))
        )
        outsider = make_user(*(CONTROL_CONTRIBUTOR + ("compliance.framework.read",)), scopes=[ScopeFactory()])
        assert is_error(call("create_controls_from_requirements", outsider, framework_id=str(framework.pk)))

    def test_requirement_coverage_lists_only_visible_reportable_controls(self, call):
        scope = ScopeFactory()
        framework = FrameworkFactory()
        framework.scopes.add(scope)
        requirement = RequirementFactory(framework=framework, workflow_state="validated")
        uncovered = RequirementFactory(framework=framework, workflow_state="validated")
        mine = scoped_control(scope)
        theirs = scoped_control(ScopeFactory())
        proposed = scoped_control(scope, implemented=False)
        for control in (mine, theirs, proposed):
            control.requirements.add(requirement)
        reader = make_user(*(CONTROL_READ + ("compliance.framework.read",)), scopes=[scope])
        result = call("get_requirement_coverage", reader, framework_id=str(framework.pk))
        rows = {row["requirement_id"]: row for row in result["rows"]}
        assert [c["id"] for c in rows[str(requirement.pk)]["controls"]] == [str(mine.pk)]
        assert rows[str(requirement.pk)]["implementation"] == "implemented"
        assert rows[str(uncovered.pk)]["implementation"] == "none"
        assert result["totals"] == {"implemented": 1, "none": 1}


class TestTestAndRunTools:
    def test_overdue_and_my_due_lists(self, call):
        scope = ScopeFactory()
        tester = make_user(*TEST_READ, scopes=[scope])
        control = scoped_control(scope)
        late = active_test(control, tester=tester, first_due_date=timezone.localdate() - datetime.timedelta(days=1))
        soon = active_test(control, tester=tester, first_due_date=timezone.localdate() + datetime.timedelta(days=10))
        active_test(control, tester=tester, first_due_date=timezone.localdate() + datetime.timedelta(days=90))
        active_test(scoped_control(ScopeFactory()), first_due_date=timezone.localdate() - datetime.timedelta(days=5))
        overdue = call("list_overdue_control_tests", tester)
        assert item_ids(overdue) == {str(late.pk)}
        assert overdue["items"][0]["is_overdue"] is True
        assert [i["id"] for i in call("list_my_control_tests_due", tester)["items"]] == [str(late.pk), str(soon.pk)]
        assert len(call("list_my_control_tests_due", tester, within_days=120)["items"]) == 3

    def test_rg_ctl_09_update_refuses_a_frozen_field(self, call, superuser):
        run = ControlTestRunFactory(result=RunResult.PASS)
        assert not is_error(call("update_control_test_run", superuser, id=str(run.pk), sample_description="25 logins"))
        run.transition_to(RUN_IN_REVIEW, run.performed_by)
        for field, value in (("result", "fail"), ("observations", "Rewritten."), ("performed_on", "2020-01-01")):
            result = call("update_control_test_run", superuser, id=str(run.pk), **{field: value})
            assert is_error(result) and "RG-CTL-09" in error_text(result), field
        run.refresh_from_db()
        assert run.result == RunResult.PASS
        assert not is_error(call("update_control_test_run", superuser, id=str(run.pk), result="pass"))
        moved = call("update_control_test_run", superuser, id=str(run.pk), test_id=str(active_test().pk))
        assert is_error(moved)

    def test_rg_ctl_11_the_performer_cannot_validate_through_mcp(self, call):
        scope = ScopeFactory()
        performer = make_user(*TEST_APPROVER, scopes=[scope])
        reviewer = make_user(*TEST_APPROVER, scopes=[scope])
        run = ControlTestRunFactory(test=active_test(scoped_control(scope)), performed_by=performer, result=RunResult.PASS)
        assert not is_error(call("transition_control_test_run", performer, id=str(run.pk), target_state=RUN_IN_REVIEW))
        refused = call("transition_control_test_run", performer, id=str(run.pk), target_state=RUN_VALIDATED)
        assert is_error(refused) and "cannot validate" in error_text(refused)
        assert not is_error(call("transition_control_test_run", reviewer, id=str(run.pk), target_state=RUN_VALIDATED))
        run.refresh_from_db()
        assert run.reviewed_by == reviewer

    def test_a_superuser_performer_cannot_validate_either(self, call, superuser):
        run = ControlTestRunFactory(performed_by=superuser, result=RunResult.PASS)
        run.transition_to(RUN_IN_REVIEW, superuser)
        refused = call("transition_control_test_run", superuser, id=str(run.pk), target_state=RUN_VALIDATED)
        assert is_error(refused)

    def test_run_payload_lists_evidence_metadata(self, call, superuser, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        run = ControlTestRunFactory(result=RunResult.PASS)
        item = upload(run)
        payload = call("get_control_test_run", superuser, id=str(run.pk))
        assert payload["evidence"][0]["sha256"] == item.sha256
        assert payload["evidence"][0]["download_url"].endswith(f"/evidence/{item.pk}/download/")
        assert "file" not in payload["evidence"][0]

    def test_raise_finding_once(self, call):
        scope = ScopeFactory()
        run = validated_run(active_test(scoped_control(scope)), result=RunResult.FAIL, observations="3 of 25 without MFA.")
        approver = make_user(*TEST_APPROVER, scopes=[scope])
        assert is_error(call("raise_finding_from_run", approver, run_id=str(run.pk), finding_type="strength"))
        finding = call("raise_finding_from_run", approver, run_id=str(run.pk), finding_type="major_nc")
        assert not is_error(finding), finding
        assert finding["source"] == FindingSource.CONTROL_TEST
        assert finding["control_test_run_id"] == str(run.pk)
        assert finding["assessor_id"] == str(approver.pk)
        again = call("raise_finding_from_run", approver, run_id=str(run.pk), finding_type="major_nc")
        assert is_error(again) and "already" in error_text(again)
        passed = validated_run()
        assert is_error(call("raise_finding_from_run", approver, run_id=str(passed.pk), finding_type="observation"))
        outsider = make_user(*TEST_APPROVER, scopes=[ScopeFactory()])
        assert is_error(call("raise_finding_from_run", outsider, run_id=str(run.pk), finding_type="observation"))

    def test_findings_list_by_control_test_source(self, call, superuser):
        run = validated_run(result=RunResult.PARTIAL, observations="Partial.")
        finding = run.raise_finding(superuser, "observation")
        listed = call("list_findings", superuser, source="control_test")
        assert item_ids(listed) == {str(finding.pk)}
        assert listed["items"][0]["control_test_run_reference"] == run.reference
        assert item_ids(call("list_findings", superuser, control_test_run_id=str(run.pk))) == {str(finding.pk)}
        # A finding raised outside an audit has no assessment to re-apply.
        assert call("delete_finding", superuser, id=str(finding.pk))["deleted"] is True

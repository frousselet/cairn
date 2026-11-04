# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Domain rules of module 8 (controls) : RG-CTL-01 to RG-CTL-16."""

import datetime

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.constants import NotificationType
from accounts.models import Notification
from accounts.tests.factories import UserFactory
from compliance.constants import FindingSource, FindingType
from controls.constants import (
    CONTROL_DRAFT,
    CONTROL_IMPLEMENTED,
    CONTROL_PLANNED,
    CONTROL_RETIRED,
    RUN_DRAFT,
    RUN_IN_REVIEW,
    RUN_VALIDATED,
    RUN_WITHDRAWN,
    TEST_ACTIVE,
    TEST_RETIRED,
    ControlEffectiveness,
    RunResult,
)
from controls.models import Control, ControlTest, ControlTestEvidence, ControlTestRun
from controls.models.control import effectiveness_from_results
from controls.tests.factories import (
    ControlFactory,
    ControlTestFactory,
    ControlTestRunFactory,
    active_test,
    implemented_control,
    validated_run,
)
from core.lifecycle import DomainRefusalError, reportable
from documents.models.policy import add_months

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate


def test_each_model_runs_its_own_lifecycle():
    assert Control().get_lifecycle().name == "control"
    assert ControlTest().get_lifecycle().name == "control_test"
    assert ControlTestRun().get_lifecycle().name == "control_test_run"


def test_lifecycles_declare_no_restore_edge():
    for model in (Control, ControlTest, ControlTestRun):
        lifecycle = model().get_lifecycle()
        assert not [t for t in lifecycle.transitions if t.source == "archived"], model


def test_references_use_the_module_prefixes():
    run = validated_run()
    assert run.test.control.reference.startswith("CTRL-")
    assert run.test.reference.startswith("CTST-")
    assert run.reference.startswith("CTRN-")


# --- Controls (RG-CTL-01 to RG-CTL-03) ----------------------------------------


def test_declaring_implemented_stamps_the_date():
    control = ControlFactory()
    control.transition_to(CONTROL_IMPLEMENTED, control.owner)
    control.refresh_from_db()
    assert control.workflow_state == CONTROL_IMPLEMENTED
    assert control.implemented_on == TODAY()


def test_an_earlier_implementation_date_is_kept():
    control = ControlFactory(implemented_on=datetime.date(2024, 5, 1))
    control.transition_to(CONTROL_IMPLEMENTED, control.owner)
    control.refresh_from_db()
    assert control.implemented_on == datetime.date(2024, 5, 1)


def test_a_future_implementation_date_is_refused():
    control = ControlFactory(implemented_on=TODAY() + datetime.timedelta(days=3))
    with pytest.raises(ValidationError):
        control.full_clean()
    with pytest.raises(DomainRefusalError):
        control.transition_to(CONTROL_IMPLEMENTED, control.owner)


def test_planned_and_implemented_controls_are_reportable():
    draft = ControlFactory()
    planned = ControlFactory()
    planned.transition_to(CONTROL_PLANNED, planned.owner)
    implemented = implemented_control()
    ids = set(reportable(Control.objects.all()).values_list("pk", flat=True))
    assert ids == {planned.pk, implemented.pk}
    assert draft.workflow_state == CONTROL_DRAFT


def test_back_to_planned_requires_a_comment():
    control = implemented_control()
    with pytest.raises(Exception):
        control.transition_to(CONTROL_PLANNED, control.owner)
    control.transition_to(CONTROL_PLANNED, control.owner, comment="The MFA provider was removed.")
    control.refresh_from_db()
    assert control.workflow_state == CONTROL_PLANNED
    assert control.implemented_on == TODAY()


def test_retiring_a_control_retires_its_tests():
    test = active_test()
    draft_test = ControlTestFactory(control=test.control)
    control = test.control
    control.transition_to(CONTROL_RETIRED, control.owner, comment="Replaced by CTRL-9.")
    test.refresh_from_db()
    draft_test.refresh_from_db()
    assert test.workflow_state == TEST_RETIRED
    assert draft_test.workflow_state == TEST_RETIRED
    assert test.next_due_date is None


def test_relations_expose_the_controls_accessor():
    from compliance.tests.factories import RequirementFactory

    control = ControlFactory()
    requirement = RequirementFactory()
    control.requirements.add(requirement)
    assert list(requirement.controls.all()) == [control]


# --- Tests (RG-CTL-06 to RG-CTL-08) -------------------------------------------


def test_a_test_of_a_proposed_control_cannot_be_activated():
    test = ControlTestFactory()
    with pytest.raises(DomainRefusalError):
        test.transition_to(TEST_ACTIVE, test.control.owner)


def test_a_test_needs_a_procedure_and_criteria_to_activate():
    control = implemented_control()
    test = ControlTestFactory(control=control, acceptance_criteria="")
    with pytest.raises(DomainRefusalError):
        test.transition_to(TEST_ACTIVE, control.owner)


def test_next_due_date_starts_at_activation_or_first_due_date():
    test = active_test()
    assert test.activated_on == TODAY()
    assert test.next_due_date == TODAY()
    first = TODAY() + datetime.timedelta(days=20)
    other = active_test(first_due_date=first)
    assert other.next_due_date == first


def test_next_due_date_follows_the_latest_validated_run():
    test = active_test(frequency_months=3)
    performed = TODAY() - datetime.timedelta(days=10)
    validated_run(test=test, performed_on=performed)
    test.refresh_from_db()
    assert test.next_due_date == add_months(performed, 3)
    assert not test.is_overdue


def test_changing_the_frequency_recomputes_the_due_date():
    test = active_test(frequency_months=3)
    run = validated_run(test=test)
    test.refresh_from_db()
    test.frequency_months = 6
    test.save()
    test.refresh_from_db()
    assert test.next_due_date == add_months(run.performed_on, 6)


def test_a_tested_test_cannot_move_to_another_control():
    run = validated_run()
    test = run.test
    test.control = implemented_control()
    with pytest.raises(ValidationError):
        test.save()


# --- Runs (RG-CTL-09 to RG-CTL-13) --------------------------------------------


def test_a_run_needs_an_active_test():
    test = ControlTestFactory()
    with pytest.raises(ValidationError):
        ControlTestRunFactory(test=test)


def test_submitting_needs_a_result():
    run = ControlTestRunFactory()
    with pytest.raises(DomainRefusalError):
        run.transition_to(RUN_IN_REVIEW, run.performed_by)


def test_a_failed_result_needs_observations():
    run = ControlTestRunFactory(result=RunResult.FAIL, observations="")
    with pytest.raises(DomainRefusalError):
        run.transition_to(RUN_IN_REVIEW, run.performed_by)


def test_the_period_must_precede_the_test_date():
    run = ControlTestRunFactory(
        result=RunResult.PASS, performed_on=TODAY() - datetime.timedelta(days=5),
        period_start=TODAY() - datetime.timedelta(days=30), period_end=TODAY() - datetime.timedelta(days=1),
    )
    with pytest.raises(ValidationError):
        run.full_clean()
    with pytest.raises(DomainRefusalError):
        run.transition_to(RUN_IN_REVIEW, run.performed_by)


def test_a_submitted_run_is_frozen():
    run = ControlTestRunFactory(result=RunResult.PASS)
    run.transition_to(RUN_IN_REVIEW, run.performed_by)
    run.refresh_from_db()
    run.result = RunResult.FAIL
    with pytest.raises(ValidationError):
        run.save()


def test_sending_back_reopens_the_run():
    run = ControlTestRunFactory(result=RunResult.PASS)
    run.transition_to(RUN_IN_REVIEW, run.performed_by)
    run.transition_to(RUN_DRAFT, UserFactory(), comment="Attach the login export.")
    run.refresh_from_db()
    run.observations = "Export attached."
    run.save()


def test_the_performer_cannot_validate_their_own_run_even_as_superuser():
    performer = UserFactory(is_superuser=True)
    run = ControlTestRunFactory(result=RunResult.PASS, performed_by=performer)
    run.transition_to(RUN_IN_REVIEW, performer)
    with pytest.raises(DomainRefusalError):
        run.transition_to(RUN_VALIDATED, performer)


def test_validation_stamps_the_reviewer():
    reviewer = UserFactory()
    run = validated_run(reviewer=reviewer)
    assert run.reviewed_by == reviewer
    assert run.reviewed_at is not None


def test_submission_notifies_the_reviewers():
    from accounts.models import Group, Permission

    reviewer = UserFactory()
    group = Group.objects.create(name="Second line")
    group.permissions.add(Permission.objects.get(codename="controls.test.approve"))
    group.users.add(reviewer)
    run = ControlTestRunFactory(result=RunResult.PASS)
    run.transition_to(RUN_IN_REVIEW, run.performed_by)
    assert Notification.objects.filter(
        recipient=reviewer, notification_type=NotificationType.LIFECYCLE_SUBMITTED,
    ).exists()


# --- Effectiveness (RG-CTL-14, RG-CTL-15) -------------------------------------


@pytest.mark.parametrize(
    ("results", "expected"),
    [
        ([], ControlEffectiveness.NOT_TESTED),
        ([RunResult.PASS], ControlEffectiveness.EFFECTIVE),
        ([RunResult.PASS, None], ControlEffectiveness.NOT_TESTED),
        ([RunResult.PASS, RunResult.PARTIAL], ControlEffectiveness.PARTIALLY_EFFECTIVE),
        ([RunResult.PARTIAL, RunResult.FAIL, None], ControlEffectiveness.NOT_EFFECTIVE),
    ],
)
def test_effectiveness_rule(results, expected):
    assert effectiveness_from_results(results) == expected


def test_validating_a_run_updates_the_effectiveness():
    test = active_test()
    control = test.control
    assert control.effectiveness == ControlEffectiveness.NOT_TESTED
    validated_run(test=test)
    control.refresh_from_db()
    assert control.effectiveness == ControlEffectiveness.EFFECTIVE
    assert control.effectiveness_updated_at is not None


def test_the_latest_validated_run_wins():
    test = active_test()
    validated_run(test=test, result=RunResult.FAIL, performed_on=TODAY() - datetime.timedelta(days=40))
    validated_run(test=test, result=RunResult.PASS, performed_on=TODAY() - datetime.timedelta(days=2))
    test.control.refresh_from_db()
    assert test.control.effectiveness == ControlEffectiveness.EFFECTIVE


def test_withdrawing_a_run_recomputes_the_effectiveness():
    run = validated_run(result=RunResult.FAIL)
    control = run.test.control
    control.refresh_from_db()
    assert control.effectiveness == ControlEffectiveness.NOT_EFFECTIVE
    run.transition_to(RUN_WITHDRAWN, UserFactory(), comment="Sample taken from the wrong system.")
    control.refresh_from_db()
    assert control.effectiveness == ControlEffectiveness.NOT_TESTED


def test_retiring_a_test_recomputes_the_effectiveness():
    control = implemented_control()
    passing = active_test(control=control)
    failing = active_test(control=control)
    validated_run(test=passing)
    validated_run(test=failing, result=RunResult.FAIL)
    control.refresh_from_db()
    assert control.effectiveness == ControlEffectiveness.NOT_EFFECTIVE
    failing.transition_to(TEST_RETIRED, control.owner, comment="Merged into the other test.")
    control.refresh_from_db()
    assert control.effectiveness == ControlEffectiveness.EFFECTIVE


def test_an_overdue_test_flags_the_effectiveness_as_stale():
    test = active_test(frequency_months=1)
    validated_run(test=test, performed_on=TODAY() - datetime.timedelta(days=60))
    control = test.control
    control.refresh_from_db()
    assert control.is_test_overdue
    assert control.is_effectiveness_stale
    assert control.effectiveness == ControlEffectiveness.EFFECTIVE


def test_a_failed_validated_run_notifies_the_control_owner():
    run = validated_run(result=RunResult.FAIL)
    assert Notification.objects.filter(
        recipient=run.test.control.owner, notification_type=NotificationType.CONTROL_TEST_FAILED,
    ).exists()


# --- Findings (RG-CTL-16) -----------------------------------------------------


def test_a_finding_is_raised_once_from_a_failed_run():
    from compliance.tests.factories import RequirementFactory

    run = validated_run(result=RunResult.FAIL, observations="3 of 25 logins had no second factor.")
    requirement = RequirementFactory()
    run.test.control.requirements.add(requirement)
    user = UserFactory()
    finding = run.raise_finding(user, FindingType.MINOR_NON_CONFORMITY)
    assert finding.source == FindingSource.CONTROL_TEST
    assert finding.control_test_run == run
    assert finding.description == "3 of 25 logins had no second factor."
    assert list(finding.requirements.all()) == [requirement]
    assert finding.assessor == user
    assert not run.needs_finding
    with pytest.raises(DomainRefusalError):
        run.raise_finding(user, FindingType.MINOR_NON_CONFORMITY)


def test_no_finding_from_a_passing_run():
    run = validated_run()
    with pytest.raises(DomainRefusalError):
        run.raise_finding(UserFactory(), FindingType.OBSERVATION)


# --- Evidence (RG-CTL-13) -----------------------------------------------------


def _upload(run, name="export.csv", data=b"login,mfa\nalice,yes\n"):
    return ControlTestEvidence.objects.create(
        run=run, file=SimpleUploadedFile(name, data), original_filename=name, uploaded_by=run.performed_by,
    )


def test_evidence_records_its_fingerprint(settings, tmp_path):
    import hashlib

    settings.MEDIA_ROOT = tmp_path
    run = ControlTestRunFactory(result=RunResult.PASS)
    item = _upload(run)
    assert item.sha256 == hashlib.sha256(b"login,mfa\nalice,yes\n").hexdigest()
    assert item.size == 20


def test_evidence_is_frozen_with_the_run(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    run = ControlTestRunFactory(result=RunResult.PASS)
    item = _upload(run)
    run.transition_to(RUN_IN_REVIEW, run.performed_by)
    with pytest.raises(ValidationError):
        _upload(run, "late.csv")
    with pytest.raises(ValidationError):
        item.delete()
    with pytest.raises(ValidationError):
        item.save()


def test_deleting_a_draft_run_removes_its_evidence(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    run = ControlTestRunFactory(result=RunResult.PASS)
    item = _upload(run)
    path = tmp_path / item.file.name
    assert path.exists()
    run.delete()
    assert not ControlTestEvidence.objects.exists()
    assert not path.exists()


def test_a_disallowed_extension_is_refused():
    run = ControlTestRunFactory(result=RunResult.PASS)
    item = ControlTestEvidence(run=run, file=SimpleUploadedFile("tool.exe", b"MZ"))
    with pytest.raises(ValidationError):
        item.full_clean()


# --- Permissions ---------------------------------------------------------------


def test_permissions_are_attached_to_the_system_groups():
    from accounts.models import Group

    codenames = lambda name: set(  # noqa: E731
        Group.objects.get(name=name).permissions.filter(module="controls").values_list("codename", flat=True)
    )
    if not Group.objects.filter(name="Lecteur").exists():
        pytest.skip("System groups are not seeded in this database.")
    assert codenames("Lecteur") == {"controls.control.read", "controls.test.read"}
    assert "controls.test.approve" in codenames("RSSI / DPO")
    assert "controls.control.delete" not in codenames("Contributeur")
    assert len(codenames("Administrateur")) == 10


# --- Services (RG-CTL-05, RG-CTL-18) ------------------------------------------


def test_create_controls_from_requirements_skips_covered_and_not_applicable():
    from compliance.tests.factories import FrameworkFactory, RequirementFactory
    from context.tests.factories import ScopeFactory
    from controls.services import create_controls_from_requirements

    scope = ScopeFactory()
    framework = FrameworkFactory()
    framework.scopes.add(scope)
    free = RequirementFactory(framework=framework, name="Access rights")
    covered = RequirementFactory(framework=framework)
    out = RequirementFactory(framework=framework, is_applicable=False, applicability_justification="No site.")
    ControlFactory().requirements.add(covered)
    user = UserFactory()
    created, skipped = create_controls_from_requirements(framework, user)
    assert [c.name for c in created] == ["Access rights"]
    control = created[0]
    assert control.workflow_state == CONTROL_DRAFT
    assert list(control.requirements.all()) == [free]
    assert list(control.scopes.all()) == [scope]
    assert control.created_by == user
    assert set(skipped) == {covered, out}
    again, _ = create_controls_from_requirements(framework, user)
    assert again == []


def _validate(obj):
    """Walk a default-lifecycle row to its reportable step."""
    lifecycle = obj.get_lifecycle()
    for step in ("pending", "validated"):
        if step in {s.code for s in lifecycle.steps}:
            obj.transition_to(step, None)


def test_requirement_coverage_summarises_the_implementation():
    from compliance.tests.factories import FrameworkFactory, RequirementFactory
    from controls.services import ImplementationSummary, requirement_coverage

    framework = FrameworkFactory()
    full = RequirementFactory(framework=framework, requirement_number="A.1")
    partial = RequirementFactory(framework=framework, requirement_number="A.2")
    bare = RequirementFactory(framework=framework, requirement_number="A.3")
    implemented_control().requirements.add(full, partial)
    planned = ControlFactory()
    planned.transition_to(CONTROL_PLANNED, planned.owner)
    planned.requirements.add(partial)
    ControlFactory().requirements.add(bare)  # proposed : not reportable
    for req in (full, partial, bare):
        _validate(req)
    rows = {row["requirement"].pk: row for row in requirement_coverage(framework)}
    assert rows[full.pk]["implementation"] == ImplementationSummary.IMPLEMENTED
    assert rows[partial.pk]["implementation"] == ImplementationSummary.PARTIAL
    assert rows[bare.pk]["implementation"] == ImplementationSummary.NONE
    assert rows[bare.pk]["controls"] == []


def test_the_recorder_cannot_validate_a_run_recorded_for_someone_else():
    recorder = UserFactory()
    run = ControlTestRunFactory(result=RunResult.PASS, created_by=recorder)
    run.transition_to(RUN_IN_REVIEW, recorder)
    with pytest.raises(DomainRefusalError):
        run.transition_to(RUN_VALIDATED, recorder)
    run.transition_to(RUN_VALIDATED, UserFactory())


def test_pacs_measures_under_way_are_linkable():
    from core.lifecycle import linkable_states

    assert {"planned", "in_progress", "overdue"} <= set(linkable_states("risks.PACSMeasure"))


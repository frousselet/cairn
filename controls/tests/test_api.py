# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The REST surface of module 8 (README §5) : permissions, tenancy and the
RG-CTL rules as a client meets them."""
import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Group, Permission
from accounts.tests.factories import UserFactory
from compliance.api.filters import FindingFilter
from compliance.api.serializers import FindingSerializer
from compliance.constants import FindingSource
from compliance.models import Finding
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from context.tests.factories import ScopeFactory
from controls.constants import (
    CONTROL_DRAFT,
    CONTROL_IMPLEMENTED,
    CONTROL_RETIRED,
    RUN_IN_REVIEW,
    RUN_VALIDATED,
    TEST_ACTIVE,
    ControlEffectiveness,
    RunResult,
)
from controls.models import Control, ControlTestEvidence, ControlTestRun
from controls.tests.factories import (
    ControlFactory,
    ControlTestFactory,
    ControlTestRunFactory,
    active_test,
    implemented_control,
    validated_run,
)
from risks.tests.factories import RiskFactory

pytestmark = pytest.mark.django_db

BASE = "/api/v1/controls"

CONTROL_READ = ("controls.control.read",)
CONTROL_CONTRIBUTOR = CONTROL_READ + ("controls.control.create", "controls.control.update")
CONTROL_APPROVER = CONTROL_CONTRIBUTOR + ("controls.control.approve", "controls.control.delete")
TEST_READ = ("controls.test.read",)
TEST_CONTRIBUTOR = TEST_READ + ("controls.test.create", "controls.test.update")
TEST_APPROVER = TEST_CONTRIBUTOR + ("controls.test.approve", "controls.test.delete")
FROZEN_MESSAGE = "A submitted test run is frozen : its content can no longer be changed."


def make_user(*codenames, scopes=()):
    """A user whose only group grants ``codenames`` within ``scopes``.

    A group with no allowed scope is unrestricted, so a test that wants a
    restricted user always passes at least one scope.
    """
    user = UserFactory()
    group = Group.objects.create(name=f"g-{user.pk}")
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    if scopes:
        group.allowed_scopes.set(scopes)
    group.users.add(user)
    return user


def api(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def data(response):
    """The payload, unwrapped from the success envelope (a lifecycle entity
    carries its own ``status`` key and is left unwrapped)."""
    body = response.json()
    if isinstance(body, dict) and "data" in body and set(body) <= {"status", "data", "meta"}:
        return body["data"]
    return body


def error(response):
    return response.json()["error"]


def ids(response):
    return {row["id"] for row in data(response)}


@pytest.fixture
def superuser():
    return UserFactory(is_superuser=True)


@pytest.fixture
def scope():
    return ScopeFactory()


def scoped_control(scope, implemented=True, **kwargs):
    control = implemented_control(**kwargs) if implemented else ControlFactory(**kwargs)
    control.scopes.add(scope)
    return control


def scoped_requirement(scope, **kwargs):
    framework = FrameworkFactory()
    framework.scopes.add(scope)
    kwargs.setdefault("workflow_state", "validated")
    return RequirementFactory(framework=framework, **kwargs)


def upload(run, name="export.csv", content=b"login,mfa\nalice,yes\n"):
    return ControlTestEvidence.objects.create(
        run=run, file=SimpleUploadedFile(name, content), original_filename=name, uploaded_by=run.performed_by,
    )


class TestRouting:
    def test_the_rest_api_is_mounted(self):
        assert reverse("controls-api:control-list") == f"{BASE}/controls/"
        assert reverse("controls-api:control-from-requirements") == f"{BASE}/controls/from-requirements/"
        assert reverse("controls-api:controltest-list") == f"{BASE}/tests/"
        assert reverse("controls-api:controltestrun-list") == f"{BASE}/runs/"

    def test_tests_and_runs_publish_no_put(self, superuser):
        test = ControlTestFactory()
        assert api(superuser).put(f"{BASE}/tests/{test.pk}/", {}, format="json").status_code == 405


class TestControlEndpoints:
    def test_create_is_proposed_with_derived_fields_read_only(self, superuser, scope):
        response = api(superuser).post(f"{BASE}/controls/", {
            "name": "MFA on remote access", "description": "Every remote login needs a second factor.",
            "scopes": [str(scope.pk)], "status": CONTROL_IMPLEMENTED,
            "effectiveness": ControlEffectiveness.EFFECTIVE, "effectiveness_updated_at": "2020-01-01T00:00:00Z",
        }, format="json")
        assert response.status_code == 201, response.content
        body = data(response)
        assert body["status"] == CONTROL_DRAFT
        assert body["reference"].startswith("CTRL-")
        assert body["effectiveness"] == ControlEffectiveness.NOT_TESTED
        assert body["effectiveness_updated_at"] is None
        assert Control.objects.get(pk=body["id"]).created_by == superuser

    def test_a_future_implementation_date_is_a_400(self, superuser):
        control = ControlFactory()
        future = (timezone.localdate() + datetime.timedelta(days=3)).isoformat()
        response = api(superuser).patch(f"{BASE}/controls/{control.pk}/", {"implemented_on": future}, format="json")
        assert response.status_code == 400
        assert "implemented_on" in error(response)

    def test_permissions_gate_each_verb(self, scope):
        control = scoped_control(scope)
        reader = make_user(*CONTROL_READ, scopes=[scope])
        assert api(reader).get(f"{BASE}/controls/").status_code == 200
        assert api(reader).get(f"{BASE}/controls/{control.pk}/history/").status_code == 200
        assert api(reader).post(f"{BASE}/controls/", {"name": "x", "description": "y"}, format="json").status_code == 403
        assert api(reader).patch(f"{BASE}/controls/{control.pk}/", {"name": "y"}, format="json").status_code == 403
        nobody = make_user(scopes=[scope])
        assert api(nobody).get(f"{BASE}/controls/").status_code == 403
        assert api(nobody).get(f"{BASE}/tests/").status_code == 403

    def test_scope_tenancy_on_controls_tests_and_runs(self, scope):
        mine = scoped_control(scope)
        theirs = scoped_control(ScopeFactory())
        their_run = validated_run(active_test(theirs))
        reader = make_user(*(CONTROL_READ + TEST_READ), scopes=[scope])
        client = api(reader)
        assert ids(client.get(f"{BASE}/controls/")) == {str(mine.pk)}
        assert client.get(f"{BASE}/controls/{theirs.pk}/").status_code == 404
        assert client.get(f"{BASE}/tests/{their_run.test_id}/").status_code == 404
        assert client.get(f"{BASE}/runs/{their_run.pk}/").status_code == 404
        assert ids(client.get(f"{BASE}/tests/")) == set()
        assert ids(client.get(f"{BASE}/runs/")) == set()

    def test_links_are_scoped_and_linkable(self, scope):
        contributor = make_user(*CONTROL_CONTRIBUTOR, scopes=[scope])
        client = api(contributor)
        payload = {"name": "Access review", "description": "Quarterly review.", "scopes": [str(scope.pk)]}
        out_of_scope = scoped_requirement(ScopeFactory())
        draft = scoped_requirement(scope, workflow_state="draft")
        linkable = scoped_requirement(scope)
        for requirement in (out_of_scope, draft):
            refused = client.post(f"{BASE}/controls/", {**payload, "requirements": [str(requirement.pk)]}, format="json")
            assert refused.status_code == 400, requirement.workflow_state
            assert "requirements" in error(refused)
        refused = client.post(f"{BASE}/controls/", {**payload, "scopes": [str(ScopeFactory().pk)]}, format="json")
        assert refused.status_code == 400
        assert "scopes" in error(refused)
        response = client.post(f"{BASE}/controls/", {**payload, "requirements": [str(linkable.pk)]}, format="json")
        assert response.status_code == 201, response.content
        # A link already in place survives its target leaving a linkable step.
        type(linkable).objects.filter(pk=linkable.pk).update(workflow_state="archived")
        control_id = data(response)["id"]
        kept = client.patch(
            f"{BASE}/controls/{control_id}/", {"requirements": [str(linkable.pk)], "name": "Renamed"}, format="json",
        )
        assert kept.status_code == 200, kept.content

    def test_a_co_owned_control_keeps_the_scopes_the_caller_cannot_see(self, scope):
        other = ScopeFactory()
        control = scoped_control(scope)
        control.scopes.add(other)
        contributor = make_user(*CONTROL_CONTRIBUTOR, scopes=[scope])
        url = f"{BASE}/controls/{control.pk}/"
        kept = api(contributor).patch(url, {"scopes": [str(scope.pk), str(other.pk)]}, format="json")
        assert kept.status_code == 200, kept.content
        added = api(contributor).patch(url, {"scopes": [str(scope.pk), str(ScopeFactory().pk)]}, format="json")
        assert added.status_code == 400

    def test_filters(self, superuser):
        requirement = RequirementFactory()
        risk = RiskFactory()
        linked = implemented_control(theme="people")
        linked.requirements.add(requirement)
        linked.risks.add(risk)
        overdue_test = active_test(linked, first_due_date=timezone.localdate() - datetime.timedelta(days=2))
        tested = implemented_control()
        validated_run(active_test(tested))
        draft = ControlFactory()
        client = api(superuser)
        assert ids(client.get(f"{BASE}/controls/?requirement_id={requirement.pk}")) == {str(linked.pk)}
        assert ids(client.get(f"{BASE}/controls/?risk_id={risk.pk}")) == {str(linked.pk)}
        assert ids(client.get(f"{BASE}/controls/?theme=people")) == {str(linked.pk)}
        assert ids(client.get(f"{BASE}/controls/?test_overdue=true")) == {str(linked.pk)}
        assert str(linked.pk) not in ids(client.get(f"{BASE}/controls/?test_overdue=false"))
        assert ids(client.get(f"{BASE}/controls/?effectiveness=effective")) == {str(tested.pk)}
        assert ids(client.get(f"{BASE}/controls/?status={CONTROL_DRAFT}")) == {str(draft.pk)}
        row = next(r for r in data(client.get(f"{BASE}/controls/")) if r["id"] == str(linked.pk))
        assert row["is_test_overdue"] is True
        assert row["next_test_due"] == overdue_test.next_due_date.isoformat()
        assert row["requirement_count"] == 1

    def test_transitions_go_through_the_lifecycle(self, scope):
        control = scoped_control(scope, implemented=False)
        contributor = make_user(*CONTROL_CONTRIBUTOR, scopes=[scope])
        approver = make_user(*CONTROL_APPROVER, scopes=[scope])
        url = f"{BASE}/controls/{control.pk}/transition/"
        assert api(contributor).post(url, {"target_state": CONTROL_IMPLEMENTED}, format="json").status_code == 403
        allowed = data(api(approver).get(url))["allowed_transitions"]
        assert CONTROL_IMPLEMENTED in {t["target"] for t in allowed}
        response = api(approver).post(url, {"target_state": CONTROL_IMPLEMENTED}, format="json")
        assert response.status_code == 200, response.content
        assert data(response)["status"] == CONTROL_IMPLEMENTED
        control.refresh_from_db()
        assert control.implemented_on == timezone.localdate()
        # Retiring requires a comment (RG-CTL-03).
        assert api(approver).post(url, {"target_state": CONTROL_RETIRED}, format="json").status_code == 400

    def test_delete_only_a_proposed_control_without_tests(self, superuser):
        client = api(superuser)
        proposed = ControlFactory()
        assert client.delete(f"{BASE}/controls/{proposed.pk}/").status_code == 204
        with_test = ControlFactory()
        ControlTestFactory(control=with_test)
        assert client.delete(f"{BASE}/controls/{with_test.pk}/").status_code == 409
        implemented = implemented_control()
        assert client.delete(f"{BASE}/controls/{implemented.pk}/").status_code == 409


class TestFromRequirements:
    URL = f"{BASE}/controls/from-requirements/"

    def test_creates_one_control_per_uncovered_applicable_requirement(self, superuser, scope):
        framework = FrameworkFactory()
        framework.scopes.add(scope)
        fresh = RequirementFactory(framework=framework)
        covered = RequirementFactory(framework=framework)
        ControlFactory().requirements.add(covered)
        excluded = RequirementFactory(framework=framework, is_applicable=False)
        client = api(superuser)
        response = client.post(self.URL, {"framework_id": str(framework.pk)}, format="json")
        assert response.status_code == 201, response.content
        body = data(response)
        assert [row["name"] for row in body["created"]] == [fresh.name]
        assert {row["id"]: row["reason"] for row in body["skipped"]} == {
            str(covered.pk): "already_covered", str(excluded.pk): "not_applicable",
        }
        control = Control.objects.get(pk=body["created"][0]["id"])
        assert control.workflow_state == CONTROL_DRAFT
        assert list(control.scopes.all()) == [scope]
        again = client.post(self.URL, {"framework_id": str(framework.pk)}, format="json")
        assert again.status_code == 200
        assert data(again)["created"] == []

    def test_needs_create_and_a_readable_framework(self, scope):
        framework = FrameworkFactory()
        framework.scopes.add(scope)
        RequirementFactory(framework=framework)
        body = {"framework_id": str(framework.pk)}
        no_create = make_user(*(CONTROL_READ + ("compliance.framework.read",)), scopes=[scope])
        assert api(no_create).post(self.URL, body, format="json").status_code == 403
        no_framework = make_user(*CONTROL_CONTRIBUTOR, scopes=[scope])
        assert api(no_framework).post(self.URL, body, format="json").status_code == 403
        outsider = make_user(*(CONTROL_CONTRIBUTOR + ("compliance.framework.read",)), scopes=[ScopeFactory()])
        refused = api(outsider).post(self.URL, body, format="json")
        assert refused.status_code == 400
        assert "framework_id" in error(refused)
        insider = make_user(*(CONTROL_CONTRIBUTOR + ("compliance.framework.read",)), scopes=[scope])
        refused = api(insider).post(self.URL, {**body, "scope_ids": [str(ScopeFactory().pk)]}, format="json")
        assert refused.status_code == 400
        assert api(insider).post(self.URL, body, format="json").status_code == 201


class TestControlTestEndpoints:
    def test_create_activate_and_derive_the_due_date(self, superuser):
        control = implemented_control()
        client = api(superuser)
        response = client.post(f"{BASE}/tests/", {
            "control": str(control.pk), "name": "Quarterly sample", "procedure": "Sample 25 logins.",
            "acceptance_criteria": "All used MFA.", "frequency_months": 3,
            "next_due_date": "2020-01-01", "activated_on": "2020-01-01",
        }, format="json")
        assert response.status_code == 201, response.content
        body = data(response)
        assert body["next_due_date"] is None and body["activated_on"] is None
        activated = client.post(f"{BASE}/tests/{body['id']}/transition/", {"target_state": TEST_ACTIVE}, format="json")
        assert activated.status_code == 200, activated.content
        assert data(activated)["next_due_date"] == timezone.localdate().isoformat()

    def test_activation_gate_is_a_400(self, superuser):
        test = ControlTestFactory(control=ControlFactory())
        response = api(superuser).post(f"{BASE}/tests/{test.pk}/transition/", {"target_state": TEST_ACTIVE}, format="json")
        assert response.status_code == 400
        assert "Plan or implement" in error(response)["detail"]

    def test_a_test_cannot_target_an_out_of_scope_or_retired_control(self, scope):
        contributor = make_user(*TEST_CONTRIBUTOR, scopes=[scope])
        theirs = scoped_control(ScopeFactory())
        payload = {"name": "t", "procedure": "p", "acceptance_criteria": "a"}
        refused = api(contributor).post(f"{BASE}/tests/", {**payload, "control": str(theirs.pk)}, format="json")
        assert refused.status_code == 400
        assert "control" in error(refused)
        retired = scoped_control(scope)
        retired.transition_to(CONTROL_RETIRED, retired.owner, comment="Gone.")
        refused = api(contributor).post(f"{BASE}/tests/", {**payload, "control": str(retired.pk)}, format="json")
        assert refused.status_code == 400

    def test_filters(self, superuser):
        late = active_test(first_due_date=timezone.localdate() - datetime.timedelta(days=1))
        later = active_test(first_due_date=timezone.localdate() + datetime.timedelta(days=60))
        draft = ControlTestFactory()
        client = api(superuser)
        assert ids(client.get(f"{BASE}/tests/?overdue=true")) == {str(late.pk)}
        soon = (timezone.localdate() + datetime.timedelta(days=30)).isoformat()
        assert ids(client.get(f"{BASE}/tests/?due_before={soon}")) == {str(late.pk)}
        assert ids(client.get(f"{BASE}/tests/?control_id={later.control_id}")) == {str(later.pk)}
        assert ids(client.get(f"{BASE}/tests/?tester_id={draft.tester_id}")) == {str(draft.pk)}
        assert ids(client.get(f"{BASE}/tests/?status=draft")) == {str(draft.pk)}


class TestRunEndpoints:
    def test_create_defaults_the_performer_and_needs_an_active_test(self, scope):
        test = active_test(scoped_control(scope))
        contributor = make_user(*TEST_CONTRIBUTOR, scopes=[scope])
        response = api(contributor).post(f"{BASE}/runs/", {"test": str(test.pk), "result": "pass"}, format="json")
        assert response.status_code == 201, response.content
        assert data(response)["performed_by"] == str(test.tester_id)
        assert data(response)["status"] == "draft"
        inactive = ControlTestFactory(control=test.control)
        refused = api(contributor).post(f"{BASE}/runs/", {"test": str(inactive.pk)}, format="json")
        assert refused.status_code == 400

    def test_a_run_cannot_target_an_out_of_scope_test(self, scope):
        contributor = make_user(*TEST_CONTRIBUTOR, scopes=[scope])
        theirs = active_test(scoped_control(ScopeFactory()))
        refused = api(contributor).post(f"{BASE}/runs/", {"test": str(theirs.pk)}, format="json")
        assert refused.status_code == 400
        assert "test" in error(refused)

    def test_rg_ctl_09_a_submitted_run_refuses_a_content_patch(self, superuser):
        run = ControlTestRunFactory(result=RunResult.PASS)
        client = api(superuser)
        url = f"{BASE}/runs/{run.pk}/"
        assert client.patch(url, {"sample_description": "25 logins"}, format="json").status_code == 200
        submitted = client.post(f"{url}transition/", {"target_state": RUN_IN_REVIEW}, format="json")
        assert submitted.status_code == 200, submitted.content
        for field, value in (("result", "fail"), ("observations", "Rewritten."), ("performed_on", "2020-01-01")):
            refused = client.patch(url, {field: value}, format="json")
            assert refused.status_code == 400, field
            assert error(refused)[field] == [FROZEN_MESSAGE]
        run.refresh_from_db()
        assert run.result == RunResult.PASS
        # The stored value, replayed, is not a change.
        assert client.patch(url, {"result": "pass"}, format="json").status_code == 200

    def test_a_submitted_run_still_takes_its_tags(self, superuser):
        run = ControlTestRunFactory(result=RunResult.PASS)
        run.transition_to(RUN_IN_REVIEW, run.performed_by)
        response = api(superuser).patch(f"{BASE}/runs/{run.pk}/", {"tags": []}, format="json")
        assert response.status_code == 200

    def test_evidence_is_listed_without_the_file(self, superuser, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        run = ControlTestRunFactory(result=RunResult.PASS)
        item = upload(run)
        body = data(api(superuser).get(f"{BASE}/runs/{run.pk}/"))
        assert body["evidence"] == [{
            "id": str(item.pk), "file_name": "export.csv", "size": item.size, "sha256": item.sha256,
            "description": "", "uploaded_by": str(run.performed_by_id),
            "uploaded_by_name": run.performed_by.display_name, "uploaded_at": item.uploaded_at.isoformat(),
            "download_url": reverse("controls:evidence-download", kwargs={"pk": item.pk}),
        }]
        assert "file" not in body["evidence"][0]

    def test_rg_ctl_11_the_performer_cannot_validate(self, scope):
        test = active_test(scoped_control(scope))
        performer = make_user(*TEST_APPROVER, scopes=[scope])
        reviewer = make_user(*TEST_APPROVER, scopes=[scope])
        run = ControlTestRunFactory(test=test, performed_by=performer, result=RunResult.PASS)
        run.transition_to(RUN_IN_REVIEW, performer)
        url = f"{BASE}/runs/{run.pk}/transition/"
        refused = api(performer).post(url, {"target_state": RUN_VALIDATED}, format="json")
        assert refused.status_code == 400
        assert "cannot validate" in error(refused)["detail"]
        response = api(reviewer).post(url, {"target_state": RUN_VALIDATED}, format="json")
        assert response.status_code == 200, response.content
        body = data(response)
        assert body["reviewed_by"] == str(reviewer.pk)
        assert body["reviewed_at"]
        control = test.control
        control.refresh_from_db()
        assert control.effectiveness == ControlEffectiveness.EFFECTIVE

    def test_superuser_performer_cannot_validate_either(self, superuser):
        run = ControlTestRunFactory(performed_by=superuser, result=RunResult.PASS)
        run.transition_to(RUN_IN_REVIEW, superuser)
        response = api(superuser).post(f"{BASE}/runs/{run.pk}/transition/", {"target_state": RUN_VALIDATED}, format="json")
        assert response.status_code == 400

    def test_raise_finding_once_from_a_failed_run(self, scope):
        run = validated_run(active_test(scoped_control(scope)), result=RunResult.FAIL, observations="3 of 25 without MFA.")
        requirement = RequirementFactory()
        run.test.control.requirements.add(requirement)
        url = f"{BASE}/runs/{run.pk}/raise-finding/"
        contributor = make_user(*TEST_CONTRIBUTOR, scopes=[scope])
        assert api(contributor).post(url, {"finding_type": "minor_nc"}, format="json").status_code == 403
        approver = make_user(*TEST_APPROVER, scopes=[scope])
        client = api(approver)
        assert client.post(url, {"finding_type": "strength"}, format="json").status_code == 400
        response = client.post(url, {"finding_type": "minor_nc", "recommendation": "Enforce MFA."}, format="json")
        assert response.status_code == 201, response.content
        body = data(response)
        assert body["source"] == FindingSource.CONTROL_TEST
        assert body["control_test_run"] == str(run.pk)
        assert body["control_test_run_reference"] == run.reference
        assert body["requirements"] == [str(requirement.pk)]
        assert body["assessor"] == str(approver.pk)
        again = client.post(url, {"finding_type": "minor_nc"}, format="json")
        assert again.status_code == 400
        assert "already" in error(again)["detail"]
        detail = data(client.get(f"{BASE}/runs/{run.pk}/"))
        assert detail["finding"]["id"] == body["id"]
        assert detail["needs_finding"] is False

    def test_raise_finding_on_a_passed_run_is_refused(self, superuser):
        run = validated_run()
        response = api(superuser).post(f"{BASE}/runs/{run.pk}/raise-finding/", {"finding_type": "observation"}, format="json")
        assert response.status_code == 400

    def test_filters(self, superuser):
        passed = validated_run()
        failed = validated_run(result=RunResult.FAIL)
        draft = ControlTestRunFactory()
        client = api(superuser)
        assert ids(client.get(f"{BASE}/runs/?result=fail")) == {str(failed.pk)}
        assert ids(client.get(f"{BASE}/runs/?control_id={passed.test.control_id}")) == {str(passed.pk)}
        assert ids(client.get(f"{BASE}/runs/?test_id={draft.test_id}")) == {str(draft.pk)}
        assert ids(client.get(f"{BASE}/runs/?performed_by_id={failed.performed_by_id}")) == {str(failed.pk)}
        assert ids(client.get(f"{BASE}/runs/?status=validated")) == {str(passed.pk), str(failed.pk)}

    def test_delete_only_a_draft_run(self, superuser):
        client = api(superuser)
        draft = ControlTestRunFactory()
        assert client.delete(f"{BASE}/runs/{draft.pk}/").status_code == 204
        assert not ControlTestRun.objects.filter(pk=draft.pk).exists()
        assert client.delete(f"{BASE}/runs/{validated_run().pk}/").status_code == 409


class TestFindingExposure:
    def test_a_finding_names_its_run_read_only_and_filters_by_source(self, superuser):
        run = validated_run(result=RunResult.PARTIAL, observations="Partial.")
        finding = run.raise_finding(superuser, "observation")
        body = FindingSerializer(finding).data
        assert body["control_test_run"] == run.pk
        assert body["control_test_run_reference"] == run.reference
        assert "control_test_run" in FindingSerializer.Meta.read_only_fields
        matched = FindingFilter({"source": "control_test"}, queryset=Finding.objects.all()).qs
        assert list(matched) == [finding]
        by_run = FindingFilter({"control_test_run_id": str(run.pk)}, queryset=Finding.objects.all()).qs
        assert list(by_run) == [finding]

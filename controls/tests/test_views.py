# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The web interface of module 8 (controls) : pages, acts, tenancy and the frozen run."""

import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from compliance.constants import FindingSource, FindingType
from compliance.models import Finding
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from context.tests.factories import ScopeFactory
from controls.constants import (
    CONTROL_DRAFT,
    RUN_DRAFT,
    RUN_IN_REVIEW,
    TEST_ACTIVE,
    RunResult,
)
from controls.models import Control, ControlTest, ControlTestEvidence, ControlTestRun
from controls.tests.factories import (
    ControlFactory,
    ControlTestFactory,
    ControlTestRunFactory,
    active_test,
    implemented_control,
    validated_run,
)

pytestmark = pytest.mark.django_db

HTMX_DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}
HTMX_TABLE = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "item-table-body"}
READ = ("controls.control.read", "controls.test.read")


def _user(*codenames, scopes=()):
    user = UserFactory()
    group = GroupFactory()
    for codename in codenames:
        group.permissions.add(PermissionFactory(codename=codename))
    if scopes:
        group.allowed_scopes.add(*scopes)
    group.users.add(user)
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


def _validate(obj):
    """Walk a default-lifecycle row to its reportable step."""
    lifecycle = obj.get_lifecycle()
    for step in ("pending", "validated"):
        if step in {s.code for s in lifecycle.steps}:
            obj.transition_to(step, None)


@pytest.fixture
def admin():
    return UserFactory(is_superuser=True)


@pytest.fixture
def admin_client(admin):
    return _client(admin)


@pytest.fixture
def scope():
    return ScopeFactory()


@pytest.fixture
def control(scope):
    control = implemented_control(name="Multi-factor authentication")
    control.scopes.add(scope)
    return control


@pytest.fixture
def test(control):
    return active_test(control=control, name="Quarterly sample of remote logins")


@pytest.fixture
def draft_run(test):
    return ControlTestRunFactory(test=test)


def _upload(name="export.csv", content=b"login,mfa\nalice,yes\n"):
    return SimpleUploadedFile(name, content, content_type="text/csv")


# --- Pages ------------------------------------------------------------------


class TestPagesRender:
    def test_every_page_renders(self, admin_client, control, test, draft_run):
        failed = validated_run(test=test, result=RunResult.FAIL, observations="Two logins without MFA.")
        evidence = ControlTestEvidence.objects.create(run=draft_run, file=_upload())
        framework = FrameworkFactory()
        urls = [
            reverse("controls:control-list"),
            reverse("controls:control-create"),
            reverse("controls:control-from-requirements"),
            reverse("controls:control-from-requirements") + f"?framework={framework.pk}",
            reverse("controls:control-detail", args=[control.pk]),
            reverse("controls:control-update", args=[control.pk]),
            reverse("controls:control-delete", args=[control.pk]),
            reverse("controls:controltest-list"),
            reverse("controls:controltest-create", args=[control.pk]),
            reverse("controls:controltest-detail", args=[test.pk]),
            reverse("controls:controltest-update", args=[test.pk]),
            reverse("controls:controltest-delete", args=[test.pk]),
            reverse("controls:controltestrun-create", args=[test.pk]),
            reverse("controls:controltestrun-detail", args=[draft_run.pk]),
            reverse("controls:controltestrun-detail", args=[failed.pk]),
            reverse("controls:controltestrun-update", args=[draft_run.pk]),
            reverse("controls:controltestrun-delete", args=[draft_run.pk]),
            reverse("controls:controltestrun-raise-finding", args=[failed.pk]),
            reverse("controls:evidence-upload", args=[draft_run.pk]),
            reverse("controls:evidence-delete", args=[evidence.pk]),
        ]
        for url in urls:
            response = admin_client.get(url)
            assert response.status_code == 200, url
            drawer = admin_client.get(url, **HTMX_DRAWER)
            assert drawer.status_code == 200, url

    def test_lists_answer_their_own_table_refresh(self, admin_client, control, test):
        for url, needle in (
            (reverse("controls:control-list"), control.reference),
            (reverse("controls:controltest-list"), test.reference),
        ):
            response = admin_client.get(url, **HTMX_TABLE)
            html = response.content.decode()
            assert response.status_code == 200
            assert needle in html
            assert "<html" not in html
            assert "hx-swap-oob" in html

    def test_pages_carry_the_controls_accent_and_breadcrumb(self, admin_client, control):
        html = admin_client.get(reverse("controls:control-detail", args=[control.pk])).content.decode()
        assert "page-header--accent-controls" in html
        assert reverse("controls:control-list") in html
        assert "lifecycle-stepper" in html or "lc-step" in html

    def test_list_facets_filter_the_register(self, admin_client, control):
        other = ControlFactory(name="Visitor badges")
        overdue = active_test(control=control, first_due_date=timezone.localdate() - timezone.timedelta(days=3))
        assert overdue.is_overdue
        html = admin_client.get(reverse("controls:control-list") + "?tests=overdue").content.decode()
        assert control.reference in html
        assert other.name not in html
        html = admin_client.get(reverse("controls:controltest-list") + "?due=overdue").content.decode()
        assert overdue.reference in html

    def test_control_detail_shows_tests_runs_and_links(self, admin_client, control, test):
        run = validated_run(test=test, result=RunResult.PASS)
        requirement = RequirementFactory(name="Secure authentication")
        control.requirements.add(requirement)
        html = admin_client.get(reverse("controls:control-detail", args=[control.pk])).content.decode()
        assert test.name in html
        assert run.reference in html
        assert "Secure authentication" in html
        assert reverse("controls:controltest-create", args=[control.pk]) in html

    def test_sidebar_lists_the_section_for_readers_only(self, control):
        reader = _client(_user(*READ))
        html = reader.get(reverse("controls:control-list")).content.decode()
        assert reverse("controls:controltest-list") in html
        nobody = _client(_user("documents.policy.read"))
        html = nobody.get(reverse("documents:policy-list")).content.decode()
        assert reverse("controls:control-list") not in html


# --- Permissions and tenancy ------------------------------------------------


class TestPermissionsAndScopes:
    def test_without_permission_every_page_is_refused(self, control, test, draft_run):
        client = _client(_user())
        for url in (
            reverse("controls:control-list"),
            reverse("controls:control-detail", args=[control.pk]),
            reverse("controls:controltest-list"),
            reverse("controls:controltest-detail", args=[test.pk]),
            reverse("controls:controltestrun-detail", args=[draft_run.pk]),
        ):
            response = client.get(url)
            assert response.status_code == 302, url
            assert response.url == "/", url

    def test_reader_cannot_open_the_forms(self, control, test, draft_run):
        client = _client(_user(*READ))
        for url in (
            reverse("controls:control-create"),
            reverse("controls:control-from-requirements"),
            reverse("controls:control-update", args=[control.pk]),
            reverse("controls:controltest-create", args=[control.pk]),
            reverse("controls:controltestrun-create", args=[test.pk]),
            reverse("controls:evidence-upload", args=[draft_run.pk]),
        ):
            assert client.get(url).status_code == 302, url

    def test_out_of_scope_rows_are_404(self, control, test, draft_run):
        outsider = _client(_user(*READ, "controls.test.update", "controls.control.update", scopes=[ScopeFactory()]))
        evidence = ControlTestEvidence.objects.create(run=draft_run, file=_upload())
        for url in (
            reverse("controls:control-detail", args=[control.pk]),
            reverse("controls:control-update", args=[control.pk]),
            reverse("controls:controltest-detail", args=[test.pk]),
            reverse("controls:controltestrun-detail", args=[draft_run.pk]),
            reverse("controls:controltestrun-update", args=[draft_run.pk]),
            reverse("controls:evidence-upload", args=[draft_run.pk]),
            reverse("controls:evidence-download", args=[evidence.pk]),
        ):
            assert outsider.get(url).status_code == 404, url
        html = outsider.get(reverse("controls:control-list")).content.decode()
        assert control.reference not in html

    def test_in_scope_reader_sees_the_rows(self, scope, control, test):
        client = _client(_user(*READ, scopes=[scope]))
        assert client.get(reverse("controls:control-detail", args=[control.pk])).status_code == 200
        assert test.reference in client.get(reverse("controls:controltest-list")).content.decode()


# --- Control forms ----------------------------------------------------------


class TestControlForms:
    def test_create_a_control_in_the_drawer(self, admin_client, scope):
        requirement = RequirementFactory()
        _validate(requirement)
        response = admin_client.post(reverse("controls:control-create"), {
            "name": "Encrypted off-site backups",
            "description": "<p>Daily backups, encrypted, copied off site.</p>",
            "theme": "technological", "nature": "corrective", "automation": "automated",
            "requirements": [requirement.pk], "scopes": [scope.pk],
        }, **HTMX_DRAWER)
        assert response.status_code == 204
        control = Control.objects.get(name="Encrypted off-site backups")
        assert control.workflow_state == CONTROL_DRAFT
        assert list(control.requirements.all()) == [requirement]
        assert control.created_by is not None

    def test_pickers_offer_linkable_targets_only(self, admin_client):
        draft = RequirementFactory(name="Draft requirement")
        live = RequirementFactory(name="Validated requirement")
        _validate(live)
        html = admin_client.get(reverse("controls:control-create")).content.decode()
        assert "Validated requirement" in html
        assert "Draft requirement" not in html
        assert draft.pk

    def test_edit_keeps_links_the_editor_cannot_see(self, scope, control):
        hidden_scope = ScopeFactory()
        hidden_framework = FrameworkFactory()
        hidden_framework.scopes.add(hidden_scope)
        hidden = RequirementFactory(framework=hidden_framework)
        _validate(hidden)
        control.requirements.add(hidden)
        editor = _client(_user(*READ, "controls.control.update", scopes=[scope]))
        response = editor.post(reverse("controls:control-update", args=[control.pk]), {
            "name": "Renamed control", "description": control.description,
            "theme": control.theme, "nature": control.nature, "automation": control.automation,
            "scopes": [scope.pk],
        })
        assert response.status_code == 302
        control.refresh_from_db()
        assert control.name == "Renamed control"
        assert hidden in control.requirements.all()

    def test_derived_effectiveness_is_not_editable(self, admin_client, control):
        admin_client.post(reverse("controls:control-update", args=[control.pk]), {
            "name": control.name, "description": control.description, "theme": control.theme,
            "nature": control.nature, "automation": control.automation, "effectiveness": "effective",
        })
        control.refresh_from_db()
        assert control.effectiveness == "not_tested"

    def test_a_retired_control_opens_frozen(self, admin, admin_client, control):
        control.transition_to("archived", admin, comment="Replaced by a new control.")
        response = admin_client.get(reverse("controls:control-update", args=[control.pk]))
        assert response.context["form"].frozen_note
        response = admin_client.post(reverse("controls:control-update", args=[control.pk]), {
            "name": "Changed", "description": "x", "theme": "people", "nature": "preventive", "automation": "manual",
        })
        assert response.status_code == 200
        control.refresh_from_db()
        assert control.name != "Changed"

    def test_delete_a_proposed_control_only(self, admin_client, control):
        proposed = ControlFactory()
        response = admin_client.post(reverse("controls:control-delete", args=[proposed.pk]))
        assert response.status_code == 302
        assert not Control.objects.filter(pk=proposed.pk).exists()
        response = admin_client.post(reverse("controls:control-delete", args=[control.pk]))
        assert response.status_code == 302
        assert Control.objects.filter(pk=control.pk).exists()


class TestCreateFromRequirements:
    def _framework(self, scope):
        framework = FrameworkFactory(short_name="ISO 27001")
        framework.scopes.add(scope)
        _validate(framework)
        return framework

    def test_checklist_lists_uncovered_applicable_requirements(self, admin_client, scope):
        framework = self._framework(scope)
        free = RequirementFactory(framework=framework, name="Access rights")
        covered = RequirementFactory(framework=framework, name="Covered one")
        excluded = RequirementFactory(framework=framework, name="Not applicable", is_applicable=False, applicability_justification="No site.")
        for req in (free, covered, excluded):
            _validate(req)
        ControlFactory().requirements.add(covered)
        url = reverse("controls:control-from-requirements") + f"?framework={framework.pk}"
        html = admin_client.get(url, **HTMX_DRAWER).content.decode()
        assert "Access rights" in html
        assert "Covered one" not in html
        assert "Not applicable" not in html

    def test_creates_and_skips(self, admin_client, scope):
        framework = self._framework(scope)
        first = RequirementFactory(framework=framework, name="Access rights")
        second = RequirementFactory(framework=framework, name="Logging")
        for req in (first, second):
            _validate(req)
        # Covered between the drawer opening and the submission : skipped, not doubled.
        ControlFactory().requirements.add(second)
        response = admin_client.post(reverse("controls:control-from-requirements"), {
            "framework": framework.pk, "requirements": [first.pk, second.pk],
        }, follow=True)
        assert response.status_code == 200
        created = Control.objects.filter(requirements=first)
        assert created.count() == 1
        assert created.get().workflow_state == CONTROL_DRAFT
        assert list(created.get().scopes.all()) == [scope]
        assert Control.objects.filter(requirements=second).count() == 1
        text = " ".join(str(m) for m in response.context["messages"])
        assert "1 proposed control was created" in text
        assert "1 requirement was skipped" in text

    def test_drawer_redirects_to_the_list(self, admin_client, scope):
        framework = self._framework(scope)
        req = RequirementFactory(framework=framework)
        _validate(req)
        response = admin_client.post(reverse("controls:control-from-requirements"), {
            "framework": framework.pk, "requirements": [req.pk],
        }, **HTMX_DRAWER)
        assert response.status_code == 204
        assert response["HX-Redirect"] == reverse("controls:control-list")

    def test_requires_create_permission(self, scope):
        framework = self._framework(scope)
        req = RequirementFactory(framework=framework)
        _validate(req)
        client = _client(_user(*READ))
        client.post(reverse("controls:control-from-requirements"), {"framework": framework.pk, "requirements": [req.pk]})
        assert not Control.objects.filter(requirements=req).exists()

    def test_out_of_scope_framework_is_not_offered(self, scope):
        framework = self._framework(ScopeFactory())
        req = RequirementFactory(framework=framework)
        _validate(req)
        client = _client(_user(*READ, "controls.control.create", scopes=[scope]))
        response = client.post(reverse("controls:control-from-requirements"), {
            "framework": framework.pk, "requirements": [req.pk],
        })
        assert response.status_code == 200
        assert "framework" in response.context["form"].errors
        assert not Control.objects.filter(requirements=req).exists()


# --- Tests and runs ---------------------------------------------------------


class TestTestAndRunForms:
    def test_create_a_test_from_its_control(self, admin_client, control):
        response = admin_client.post(reverse("controls:controltest-create", args=[control.pk]), {
            "name": "Annual design review", "method": "inspection", "frequency_months": 12,
            "procedure": "Review the configuration.", "acceptance_criteria": "MFA enforced.",
        })
        assert response.status_code == 302
        test = ControlTest.objects.get(name="Annual design review")
        assert test.control == control
        assert test.next_due_date is None

    def test_a_retired_control_takes_no_new_test(self, admin, admin_client, control):
        control.transition_to("archived", admin, comment="Retired.")
        response = admin_client.get(reverse("controls:controltest-create", args=[control.pk]))
        assert response.status_code == 302

    def test_run_form_is_prefilled_with_the_tester_and_today(self, admin_client, test):
        response = admin_client.get(reverse("controls:controltestrun-create", args=[test.pk]), **HTMX_DRAWER)
        form = response.context["form"]
        assert form.initial["performed_by"] == test.tester_id
        assert form.initial["performed_on"] == timezone.localdate()

    def test_run_form_falls_back_to_the_user_without_tester(self, admin, admin_client, control):
        test = active_test(control=control, tester=None)
        response = admin_client.get(reverse("controls:controltestrun-create", args=[test.pk]))
        assert response.context["form"].initial["performed_by"] == admin.pk

    def test_record_a_run(self, admin, admin_client, test):
        response = admin_client.post(reverse("controls:controltestrun-create", args=[test.pk]), {
            "performed_by": admin.pk, "performed_on": timezone.localdate().isoformat(),
            "result": RunResult.PASS, "sample_description": "25 logins",
        })
        assert response.status_code == 302
        run = ControlTestRun.objects.get(test=test)
        assert run.workflow_state == RUN_DRAFT
        assert run.created_by == admin

    def test_no_run_on_a_draft_test(self, admin_client, control):
        draft = ControlTestFactory(control=control)
        response = admin_client.get(reverse("controls:controltestrun-create", args=[draft.pk]))
        assert response.status_code == 302
        assert not ControlTestRun.objects.filter(test=draft).exists()

    def test_future_date_is_refused(self, admin, admin_client, test):
        response = admin_client.post(reverse("controls:controltestrun-create", args=[test.pk]), {
            "performed_by": admin.pk, "performed_on": (timezone.localdate() + timezone.timedelta(days=2)).isoformat(),
        })
        assert response.status_code == 200
        assert "performed_on" in response.context["form"].errors

    def test_update_of_a_submitted_run_is_refused(self, admin_client, draft_run):
        draft_run.result = RunResult.PASS
        draft_run.save()
        draft_run.transition_to(RUN_IN_REVIEW, draft_run.performed_by)
        url = reverse("controls:controltestrun-update", args=[draft_run.pk])
        assert admin_client.get(url).status_code == 302
        response = admin_client.post(url, {
            "performed_by": draft_run.performed_by_id, "performed_on": draft_run.performed_on.isoformat(),
            "result": RunResult.FAIL, "observations": "Changed after submission.",
        })
        assert response.status_code == 302
        draft_run.refresh_from_db()
        assert draft_run.result == RunResult.PASS
        drawer = admin_client.get(url, **HTMX_DRAWER)
        assert drawer.status_code == 204
        assert drawer["HX-Redirect"] == reverse("controls:controltestrun-detail", args=[draft_run.pk])

    def test_delete_a_draft_run_only(self, admin_client, test, draft_run):
        validated = validated_run(test=test)
        admin_client.post(reverse("controls:controltestrun-delete", args=[validated.pk]))
        assert ControlTestRun.objects.filter(pk=validated.pk).exists()
        admin_client.post(reverse("controls:controltestrun-delete", args=[draft_run.pk]))
        assert not ControlTestRun.objects.filter(pk=draft_run.pk).exists()


# --- Evidence ---------------------------------------------------------------


class TestEvidence:
    def test_upload_stamps_size_and_sha256(self, admin_client, draft_run):
        content = b"login,mfa\nalice,yes\n"
        response = admin_client.post(
            reverse("controls:evidence-upload", args=[draft_run.pk]),
            {"file": _upload(content=content), "description": "Q3 export"}, **HTMX_DRAWER,
        )
        assert response.status_code == 204
        item = draft_run.evidence.get()
        assert item.sha256 == hashlib.sha256(content).hexdigest()
        assert item.size == len(content)
        assert item.original_filename == "export.csv"
        html = admin_client.get(reverse("controls:controltestrun-detail", args=[draft_run.pk])).content.decode()
        assert item.sha256 in html
        assert reverse("controls:evidence-download", args=[item.pk]) in html
        assert item.file.url not in html

    def test_disallowed_extension_is_refused(self, admin_client, draft_run):
        response = admin_client.post(
            reverse("controls:evidence-upload", args=[draft_run.pk]),
            {"file": SimpleUploadedFile("run.exe", b"MZ", content_type="application/octet-stream")},
        )
        assert response.status_code == 200
        assert not draft_run.evidence.exists()

    def test_upload_refused_once_submitted(self, admin_client, draft_run):
        draft_run.result = RunResult.PASS
        draft_run.save()
        draft_run.transition_to(RUN_IN_REVIEW, draft_run.performed_by)
        response = admin_client.post(reverse("controls:evidence-upload", args=[draft_run.pk]), {"file": _upload()})
        assert response.status_code == 302
        assert not draft_run.evidence.exists()

    def test_download_serves_an_attachment(self, scope, draft_run):
        item = ControlTestEvidence.objects.create(run=draft_run, file=_upload(name='a"b.csv'))
        client = _client(_user(*READ, scopes=[scope]))
        response = client.get(reverse("controls:evidence-download", args=[item.pk]))
        assert response.status_code == 200
        assert response["Content-Type"] == "application/octet-stream"
        assert response["Content-Disposition"].startswith("attachment;")
        assert '"' not in response["Content-Disposition"].split('filename="', 1)[1].split('";', 1)[0]
        assert response.content == b"login,mfa\nalice,yes\n"

    def test_download_needs_the_read_permission(self, draft_run):
        item = ControlTestEvidence.objects.create(run=draft_run, file=_upload())
        response = _client(_user("controls.control.read")).get(reverse("controls:evidence-download", args=[item.pk]))
        assert response.status_code == 302

    def test_delete_only_while_in_progress(self, admin_client, test):
        open_run = ControlTestRunFactory(test=test)
        item = ControlTestEvidence.objects.create(run=open_run, file=_upload())
        response = admin_client.post(reverse("controls:evidence-delete", args=[item.pk]))
        assert response.status_code == 302
        assert not ControlTestEvidence.objects.filter(pk=item.pk).exists()

        frozen = ControlTestRunFactory(test=test, result=RunResult.PASS)
        kept = ControlTestEvidence.objects.create(run=frozen, file=_upload())
        frozen.transition_to(RUN_IN_REVIEW, frozen.performed_by)
        response = admin_client.post(reverse("controls:evidence-delete", args=[kept.pk]), follow=True)
        assert ControlTestEvidence.objects.filter(pk=kept.pk).exists()
        assert any("in progress" in str(m) for m in response.context["messages"])


# --- Raise a finding (RG-CTL-16) --------------------------------------------


class TestRaiseFinding:
    def test_raise_once_from_a_failed_run(self, admin, admin_client, test):
        run = validated_run(test=test, result=RunResult.FAIL, observations="Two logins without MFA.")
        assert run.needs_finding
        url = reverse("controls:controltestrun-raise-finding", args=[run.pk])
        response = admin_client.post(url, {"finding_type": FindingType.MINOR_NON_CONFORMITY, "recommendation": "Enforce MFA."})
        finding = Finding.objects.get(control_test_run=run)
        assert response.status_code == 302
        assert response.url == reverse("compliance:finding-detail", args=[finding.pk])
        assert finding.source == FindingSource.CONTROL_TEST
        assert finding.assessor == admin
        html = admin_client.get(reverse("controls:controltestrun-detail", args=[run.pk])).content.decode()
        assert finding.reference in html
        assert url not in html
        again = admin_client.post(url, {"finding_type": FindingType.OBSERVATION})
        assert again.status_code == 302
        assert Finding.objects.filter(control_test_run=run).count() == 1

    def test_not_offered_on_a_passed_run(self, admin_client, test):
        run = validated_run(test=test, result=RunResult.PASS)
        url = reverse("controls:controltestrun-raise-finding", args=[run.pk])
        assert url not in admin_client.get(reverse("controls:controltestrun-detail", args=[run.pk])).content.decode()
        admin_client.post(url, {"finding_type": FindingType.MINOR_NON_CONFORMITY})
        assert not Finding.objects.filter(control_test_run=run).exists()

    def test_requires_the_approve_permission(self, scope, test):
        run = validated_run(test=test, result=RunResult.PARTIAL, observations="Partial.")
        client = _client(_user(*READ, "controls.test.update", scopes=[scope]))
        client.post(reverse("controls:controltestrun-raise-finding", args=[run.pk]), {"finding_type": FindingType.OBSERVATION})
        assert not Finding.objects.filter(control_test_run=run).exists()

    def test_strength_is_not_a_raisable_type(self, admin_client, test):
        run = validated_run(test=test, result=RunResult.FAIL, observations="Failed.")
        response = admin_client.post(
            reverse("controls:controltestrun-raise-finding", args=[run.pk]), {"finding_type": FindingType.STRENGTH},
        )
        assert response.status_code == 200
        assert not Finding.objects.filter(control_test_run=run).exists()


def test_test_detail_offers_a_run_only_when_active(admin_client, control):
    draft = ControlTestFactory(control=control)
    html = admin_client.get(reverse("controls:controltest-detail", args=[draft.pk])).content.decode()
    assert reverse("controls:controltestrun-create", args=[draft.pk]) not in html
    draft.transition_to(TEST_ACTIVE, control.owner)
    html = admin_client.get(reverse("controls:controltest-detail", args=[draft.pk])).content.decode()
    assert reverse("controls:controltestrun-create", args=[draft.pk]) in html


def test_a_finding_raised_from_markup_observations_renders_escaped(client):
    """Regression : observations are plain text; the finding page sanitizes."""
    run = validated_run(result=RunResult.FAIL, observations='<img src=x onerror="alert(1)">Gap')
    user = UserFactory(is_superuser=True)
    finding = run.raise_finding(user, FindingType.MINOR_NON_CONFORMITY)
    client.force_login(user)
    response = client.get(reverse("compliance:finding-detail", kwargs={"pk": finding.pk}))
    assert response.status_code == 200
    assert b"onerror=\"alert(1)\"" not in response.content
    assert b"Gap" in response.content

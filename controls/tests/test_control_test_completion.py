# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A test and a run are created short, then completed on their page.

A test is created from the page of its control and a run from the page of its
test : their creation addresses carry that record, so the generic checks of
``core/tests/test_usability_standard.py`` (which create from a register) are
made here, through the dialogs, with what is particular to each :

- a test is created with its name, its method, its frequency and its tester;
  its procedure and acceptance criteria are asked before it is activated
  (RG-CTL-06), on every surface;
- a run is recorded with who tested, when and, once known, its result; the
  result, and the observations of a partial or failed one, are asked before it
  is submitted (RG-CTL-10). A submitted run is frozen : nothing is left to
  complete on it.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from controls.constants import RUN_IN_REVIEW, TEST_ACTIVE, TEST_RETIRED, RunResult
from controls.forms import ControlTestCreateForm, ControlTestForm, ControlTestRunCreateForm, ControlTestRunForm
from controls.models import ControlTest, ControlTestRun
from controls.tests.factories import (
    ControlFactory,
    ControlTestFactory,
    ControlTestRunFactory,
    active_test,
    implemented_control,
)
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError
from core.tests.test_usability_standard import _current_answers, _snapshot

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _missing(record):
    report = completeness_of(record)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


def _bare_test(**kwargs):
    """A test as the dialog creates it : a name, a method, a frequency, a tester."""
    return ControlTestFactory(procedure="", acceptance_criteria="", **kwargs)


def _reader(client, codename="controls.test.read"):
    from accounts.models import Group, Permission

    reader = UserFactory()
    group = Group.objects.create(name=f"readers-{reader.pk}")
    group.permissions.add(Permission.objects.get(codename=codename))
    group.users.add(reader)
    client.force_login(reader)
    return reader


def _each_section_leaves_the_rest_alone(client, admin, record, form_class, edit_name):
    """Each card is saved as the reader found it : nothing else may move."""
    edit = reverse(edit_name, args=[record.pk])
    record = type(record).objects.get(pk=record.pk)
    before = _snapshot(record)
    for key in form_class.section_keys():
        response = client.get(f"{edit}?section={key}", **DRAWER)
        assert response.status_code == 200, key
        assert 'name="_section"' in response.content.decode(), key

        form = form_class(instance=record, user=admin, section=key)
        response = client.post(edit, {**_current_answers(form), "_section": key}, **DRAWER)
        assert response.status_code == 204, f"{key} : {response.content.decode()[:600]}"

        record = type(record).objects.get(pk=record.pk)
        assert _snapshot(record) == before, f"saving the section '{key}' changed something else"


# ── The test ────────────────────────────────────────────────────────────────


class TestATestIsCreatedShort:
    def test_it_asks_the_name_the_method_the_frequency_and_the_tester(self, admin):
        form = ControlTestCreateForm(user=admin)

        assert sorted(form.fields) == ["frequency_months", "method", "name", "tester"]
        assert form.is_multistep is False
        assert form.fields["frequency_months"].initial == 12 or form.initial.get("frequency_months") == 12

    def test_the_method_is_a_decision_of_the_reader(self, client, admin):
        """ "Inspection" was saved for whoever did not choose."""
        control = implemented_control()
        method = ControlTestCreateForm(user=admin).fields["method"]

        response = client.post(
            reverse("controls:controltest-create", args=[control.pk]),
            {"name": "Quarterly sample", "frequency_months": 3}, **DRAWER,
        )

        assert method.required and [value for value, _label in method.choices][0] == ""
        assert response.status_code == 200 and not ControlTest.objects.exists()

    def test_the_dialog_creates_the_test_and_opens_it(self, client, admin):
        control = implemented_control()

        response = client.post(
            reverse("controls:controltest-create", args=[control.pk]),
            {"name": "Quarterly sample", "method": "reperformance", "frequency_months": 3}, **DRAWER,
        )
        test = ControlTest.objects.get()

        assert response.status_code == 204, response.content.decode()[:600]
        assert response["HX-Redirect"] == test.get_absolute_url()
        assert (test.control, test.method, test.frequency_months, test.created_by) == (
            control, "reperformance", 3, admin,
        )
        assert _missing(test)[0] == ["procedure", "acceptance_criteria"]

    def test_the_owner_of_the_control_tests_it_unless_said_otherwise(self, client, admin):
        owned, ownerless = implemented_control(), implemented_control()
        ownerless.owner = None
        ownerless.save()

        owned_html = client.get(reverse("controls:controltest-create", args=[owned.pk]), **DRAWER).content.decode()
        ownerless_html = client.get(
            reverse("controls:controltest-create", args=[ownerless.pk]), **DRAWER,
        ).content.decode()

        assert f'<option value="{owned.owner.pk}" selected>' in owned_html
        # With no owner, whoever creates the test.
        assert f'<option value="{admin.pk}" selected>' in ownerless_html


class TestWhatATestStillNeeds:
    def test_it_is_not_activated_before_its_procedure_and_its_criteria(self, admin):
        test = _bare_test(control=implemented_control())

        with pytest.raises(DomainRefusalError) as refusal:
            test.transition_to(TEST_ACTIVE, admin)
        test.procedure = "Draw 25 remote logins of the quarter and check each used a second factor."
        test.acceptance_criteria = "Every login of the sample used a second factor."
        test.save()
        test.transition_to(TEST_ACTIVE, admin)
        test.refresh_from_db()

        assert "fill in the procedure" in str(refusal.value)
        assert "fill in the acceptance criteria" in str(refusal.value)
        assert test.workflow_state == TEST_ACTIVE and test.activated_on is not None

    def test_its_control_is_planned_first(self, admin):
        """A refusal about another record is said before what the test lacks."""
        test = _bare_test(control=ControlFactory())

        with pytest.raises(DomainRefusalError) as refusal:
            test.transition_to(TEST_ACTIVE, admin)

        assert "Plan or implement the control" in str(refusal.value)

    def test_a_test_nobody_performs_is_told_to_name_a_tester(self):
        assert _missing(_bare_test(tester=None))[1] == ["tester"]
        assert _missing(_bare_test())[1] == []

    def test_the_page_lists_it_and_opens_each_card(self, client, admin):
        test = _bare_test()
        edit = reverse("controls:controltest-update", args=[test.pk])

        html = client.get(test.get_absolute_url()).content.decode()

        assert "Fill in the procedure" in html and "Fill in the acceptance criteria" in html
        for key in ControlTestForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_saving_a_card_leaves_the_rest_of_the_test_alone(self, client, admin):
        test = ControlTestFactory(objective="Operating effectiveness.", first_due_date="2030-01-01")

        _each_section_leaves_the_rest_alone(client, admin, test, ControlTestForm, "controls:controltest-update")

    def test_a_reader_is_offered_no_edit(self, client):
        test = _bare_test()
        _reader(client)

        html = client.get(test.get_absolute_url()).content.decode()

        assert "?section=" not in html and "To complete" in html

    def test_a_retired_test_has_nothing_left_to_complete(self, client, admin):
        test = _bare_test()
        test.transition_to(TEST_RETIRED, admin, comment="Replaced by an automated check.")

        html = client.get(test.get_absolute_url()).content.decode()

        assert "?section=" not in html and "To complete" not in html

    def test_the_empty_register_says_what_a_test_is(self, client, admin):
        html = client.get(reverse("controls:controltest-list")).content.decode()

        assert "A test says how a control is checked" in html


# ── The run ─────────────────────────────────────────────────────────────────


class TestARunIsRecordedShort:
    def test_it_asks_who_tested_when_and_with_what_result(self, admin):
        form = ControlTestRunCreateForm(user=admin)

        assert sorted(form.fields) == ["observations", "performed_by", "performed_on", "result"]
        assert form.is_multistep is False
        assert form.fields["result"].required is False

    def test_the_dialog_records_the_run_and_opens_it(self, client, admin):
        test = active_test()
        url = reverse("controls:controltestrun-create", args=[test.pk])

        html = client.get(url, **DRAWER).content.decode()
        response = client.post(url, {"performed_by": test.tester.pk, "performed_on": "2026-01-15"}, **DRAWER)
        run = ControlTestRun.objects.get()

        # Prefilled with the tester of the test.
        assert f'<option value="{test.tester.pk}" selected>' in html
        assert response.status_code == 204, response.content.decode()[:600]
        assert response["HX-Redirect"] == run.get_absolute_url()
        assert (run.test, run.performed_by, run.result, run.created_by) == (test, test.tester, "", admin)


class TestWhatARunStillNeeds:
    def test_it_is_not_submitted_before_its_result(self, admin):
        run = ControlTestRunFactory()

        with pytest.raises(DomainRefusalError) as refusal:
            run.transition_to(RUN_IN_REVIEW, run.performed_by)

        assert _missing(run) == (["result"], ["evidence"])
        assert "record the result" in str(refusal.value)

    def test_a_partial_or_failed_result_says_what_was_found(self, admin):
        run = ControlTestRunFactory(result=RunResult.FAIL, observations="")

        with pytest.raises(DomainRefusalError) as refusal:
            run.transition_to(RUN_IN_REVIEW, run.performed_by)
        run.observations = "3 of the 25 logins had no second factor."
        run.save()
        run.transition_to(RUN_IN_REVIEW, run.performed_by)

        assert "fill in the observations" in str(refusal.value)
        assert run.workflow_state == RUN_IN_REVIEW

    def test_a_pass_needs_no_observation(self, admin):
        run = ControlTestRunFactory(result=RunResult.PASS, observations="")

        assert _missing(run)[0] == []
        run.transition_to(RUN_IN_REVIEW, run.performed_by)
        assert run.workflow_state == RUN_IN_REVIEW

    def test_the_page_lists_it_opens_each_card_and_leads_to_the_evidence(self, client, admin):
        run = ControlTestRunFactory()
        edit = reverse("controls:controltestrun-update", args=[run.pk])

        html = client.get(run.get_absolute_url()).content.decode()

        assert "Record the result" in html and "Add evidence" in html
        assert f'href="{run.get_absolute_url()}#evidence"' in html and 'id="evidence"' in html
        for key in ControlTestRunForm.section_keys():
            assert f'{edit}?section={key}"' in html, key

    def test_saving_a_card_leaves_the_rest_of_the_run_alone(self, client, admin):
        run = ControlTestRunFactory(
            result=RunResult.PARTIAL, observations="2 of 25 lacked a second factor.",
            sample_description="25 of 1,240 remote logins.",
        )

        _each_section_leaves_the_rest_alone(client, admin, run, ControlTestRunForm, "controls:controltestrun-update")

    def test_a_reader_is_offered_no_edit(self, client):
        run = ControlTestRunFactory()
        _reader(client)

        html = client.get(run.get_absolute_url()).content.decode()

        assert "?section=" not in html

    def test_a_submitted_run_is_frozen_and_has_nothing_left_to_complete(self, client, admin):
        run = ControlTestRunFactory(result=RunResult.PASS)
        run.transition_to(RUN_IN_REVIEW, run.performed_by)

        html = client.get(run.get_absolute_url()).content.decode()

        assert "?section=" not in html and "To complete" not in html


# ── The REST API and the MCP server ─────────────────────────────────────────


class TestTheOtherSurfaces:
    @staticmethod
    def _api(user):
        api = APIClient()
        api.force_authenticate(user=user)
        return api

    @staticmethod
    def _body(response):
        body = response.json()
        return body.get("data", body)

    def test_the_rest_api_says_what_a_test_needs_and_refuses_to_activate_it(self, admin):
        api = self._api(admin)
        control = implemented_control()

        created = api.post(
            "/api/v1/controls/tests/", {"control": str(control.pk), "name": "Quarterly sample"}, format="json",
        )
        body = self._body(created)
        read = self._body(api.get(f"/api/v1/controls/tests/{body['id']}/"))
        activated = api.post(
            f"/api/v1/controls/tests/{body['id']}/transition/", {"target_state": TEST_ACTIVE}, format="json",
        )

        assert created.status_code == 201, created.content
        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == [
            "procedure", "acceptance_criteria",
        ]
        assert activated.status_code == 400 and "fill in the procedure" in activated.content.decode()

    def test_the_rest_api_says_what_a_run_needs(self, admin):
        run = ControlTestRunFactory()

        read = self._body(self._api(admin).get(f"/api/v1/controls/runs/{run.pk}/"))

        assert read["completeness"]["can_advance"] is False
        assert [item["key"] for item in read["completeness"]["missing"]] == ["result", "evidence"]

    def test_the_mcp_server_says_what_a_test_and_a_run_need(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        server = McpServer()
        register_all_tools(server)
        test, run = _bare_test(), ControlTestRunFactory(result=RunResult.FAIL)

        read_test = server.get_tool("get_control_test")["handler"](admin, {"id": str(test.pk)})
        read_run = server.get_tool("get_control_test_run")["handler"](admin, {"id": str(run.pk)})

        assert [item["key"] for item in read_test["completeness"]["missing"] if item["blocking"]] == [
            "procedure", "acceptance_criteria",
        ]
        assert [item["key"] for item in read_run["completeness"]["missing"] if item["blocking"]] == ["observations"]

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A control is created with its name, then completed on its page.

What every entity of the usability standard does (the dialog on one screen,
the landing on the record, a card per section, a reader offered no edit) is
checked for all of them in ``core/tests/test_usability_standard.py``. This
file holds what is particular to a control : its description may wait until it
is planned, its three classifications are answered by nobody but the reader,
a control created from a requirement included, and an implemented control
nobody tests is told so.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from context.tests.factories import ScopeFactory
from controls.constants import CONTROL_DRAFT, CONTROL_IMPLEMENTED, CONTROL_PLANNED
from controls.forms import ControlCreateForm, ControlForm
from controls.models import Control
from controls.services import create_controls_from_requirements
from controls.tests.factories import ControlFactory, ControlTestFactory, implemented_control
from core.completeness import completeness_of
from core.lifecycle import DomainRefusalError

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _bare(**kwargs):
    """A control as the dialog creates it : a name, a theme, somebody who answers for it."""
    return ControlFactory(description="", nature="", automation="", **kwargs)


def _missing(control):
    report = completeness_of(control)
    return [item.key for item in report.blocking_missing], [item.key for item in report.advised_missing]


class TestCreation:
    def test_it_asks_the_name_the_theme_the_owner_and_the_description(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = ControlCreateForm(user=admin)

        assert sorted(form.fields) == ["description", "name", "owner", "scopes", "theme"]
        assert form.is_multistep is False
        # Whoever creates the control answers for it unless they say otherwise.
        assert form.fields["owner"].initial == admin.pk
        assert form.fields["description"].required is False

    def test_the_theme_is_a_decision_of_the_reader(self, client, admin):
        """ "Technological" was saved for whoever did not choose."""
        form = ControlCreateForm(user=admin)
        theme = form.fields["theme"]

        response = client.post(reverse("controls:control-create"), {"name": "Clear desk"}, **DRAWER)

        assert theme.required and not form.initial.get("theme")
        assert [value for value, _label in theme.choices][0] == ""
        assert response.status_code == 200 and not Control.objects.exists()
        assert "Choose the theme" in response.content.decode() or "theme" in response.context["form"].errors

    def test_the_nature_and_the_automation_wait_on_the_page(self, client, admin):
        ScopeFactory()

        # The dialog opens with whoever creates the control as its owner.
        client.post(
            reverse("controls:control-create"), {"name": "Clear desk", "theme": "physical", "owner": admin.pk}, **DRAWER,
        )
        control = Control.objects.get()

        assert (control.theme, control.nature, control.automation) == ("physical", "", "")
        assert control.workflow_state == CONTROL_DRAFT and control.owner == admin
        assert _missing(control) == (["description"], ["classification", "answers"])

    def test_an_unanswered_classification_reads_not_set(self, admin):
        control = _bare()

        form = ControlForm(instance=control, user=admin, section="identity")

        for name in ("theme", "nature", "automation"):
            assert str(form.fields[name].choices[0][1]) == "Not set", name
            assert form.fields[name].required is False


class TestAControlCreatedFromARequirement:
    def test_it_carries_no_answer_nobody_gave(self, client, admin):
        """Each one was technological, preventive and manual : three answers
        the requirement does not hold and nobody had chosen."""
        framework = FrameworkFactory(workflow_state="validated")
        requirement = RequirementFactory(
            framework=framework, workflow_state="validated", name="Clear desk and clear screen",
            description="Rules for papers and removable media are defined and enforced.",
        )

        created, _skipped = create_controls_from_requirements(framework, admin, [requirement.pk])
        control = created[0]
        html = client.get(control.get_absolute_url()).content.decode()

        assert (control.theme, control.nature, control.automation) == ("", "", "")
        # Its description comes from the requirement, its classification from the reader.
        assert _missing(control)[0] == []
        assert "classification" in _missing(control)[1]
        assert "Choose the theme, the nature and the automation" in html

    def test_its_row_of_the_register_names_no_theme(self, client, admin):
        _bare(name="Clear desk", theme="")

        html = client.get(reverse("controls:control-list")).content.decode()

        assert '<span class="cell-sub">0 requirements</span>' in html.replace("\n", "")


class TestWhatAControlStillNeeds:
    def test_it_is_not_planned_before_its_description_is_written(self, admin):
        control = _bare()

        with pytest.raises(DomainRefusalError) as refusal:
            control.transition_to(CONTROL_PLANNED, admin)
        control.description = "<p>Papers are locked away at the end of the day.</p>"
        control.save()
        control.transition_to(CONTROL_PLANNED, admin)
        control.refresh_from_db()

        assert "fill in the description" in str(refusal.value)
        assert control.workflow_state == CONTROL_PLANNED

    def test_the_page_lists_it_and_opens_the_card_that_fills_it(self, client, admin):
        control = _bare()
        edit = reverse("controls:control-update", args=[control.pk])

        html = client.get(control.get_absolute_url()).content.decode()

        assert "Fill in the description" in html
        assert f'{edit}?section=description"' in html

    def test_an_implemented_control_nobody_tests_is_told_to_add_a_test(self, client, admin):
        proposed, running = ControlFactory(), implemented_control()

        html = client.get(running.get_absolute_url()).content.decode()

        assert "tests" not in _missing(proposed)[1]
        assert "tests" in _missing(running)[1]
        assert f'href="{running.get_absolute_url()}#tests"' in html and 'id="tests"' in html
        ControlTestFactory(control=running)
        assert "tests" not in _missing(running)[1]

    def test_a_retired_control_has_nothing_left_to_complete(self, client, admin):
        control = implemented_control()
        control.transition_to("archived", admin, comment="Replaced by a new control.")

        html = client.get(control.get_absolute_url()).content.decode()

        assert "?section=" not in html and "To complete" not in html


class TestTheOtherSurfaces:
    def test_the_rest_api_creates_with_a_name_and_says_what_is_missing(self, admin):
        scope = ScopeFactory()
        api = APIClient()
        api.force_authenticate(user=admin)

        created = api.post("/api/v1/controls/controls/", {"name": "Clear desk", "scopes": [str(scope.pk)]}, format="json")
        body = created.json()
        body = body.get("data", body)
        planned = api.post(
            f"/api/v1/controls/controls/{body['id']}/transition/", {"target_state": CONTROL_PLANNED}, format="json",
        )

        assert created.status_code == 201, created.content
        assert (body["theme"], body["nature"], body["automation"], body["description"]) == ("", "", "", "")
        assert [item["key"] for item in body["completeness"]["missing"] if item["blocking"]] == ["description"]
        assert body["completeness"]["can_advance"] is False
        assert planned.status_code == 400 and "fill in the description" in planned.content.decode()

    def test_the_mcp_server_creates_with_a_name_and_says_what_is_missing(self, admin):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        server = McpServer()
        register_all_tools(server)
        scope = ScopeFactory()

        created = server.get_tool("create_control")["handler"](admin, {"name": "Clear desk", "scope_ids": [str(scope.pk)]})
        read = server.get_tool("get_control")["handler"](admin, {"id": created["id"]})
        schema = server.get_tool("create_control")["inputSchema"]

        assert schema["required"] == ["name"]
        assert (created["theme"], created["nature"], created["automation"]) == ("", "", "")
        assert [item["key"] for item in read["completeness"]["missing"] if item["blocking"]] == ["description"]

    def test_declaring_it_implemented_waits_for_the_description_too(self, admin):
        control = _bare()

        with pytest.raises(DomainRefusalError):
            control.transition_to(CONTROL_IMPLEMENTED, admin)

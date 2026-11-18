# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A requirement is created on one screen, then completed on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the requirement : it hangs under a framework, whose sections
are the only ones it may sit in; its risks survive the edit of another card;
and the applicability a framework derives from risks is not edited by hand.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, UserFactory
from compliance.forms import RequirementCreateForm, RequirementUpdateForm
from compliance.models import Requirement
from compliance.tests.factories import FrameworkFactory, RequirementFactory, SectionFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from risks.tests.factories import RiskFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _mcp(user, tool, arguments):
    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    server = McpServer()
    register_all_tools(server)
    answer = server.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }), user)
    return json.loads(answer["result"]["content"][0]["text"])


def _linkable_risk():
    risk = RiskFactory()
    type(risk).objects.filter(pk=risk.pk).update(workflow_state=_a_linkable_state(type(risk)))
    risk.refresh_from_db()
    return risk


def _a_linkable_state(model):
    from core.lifecycle import linkable_states

    return sorted(linkable_states(model))[0]


class TestCreationIsShort:
    def test_it_asks_where_it_comes_from_and_what_it_asks(self, admin):
        form = RequirementCreateForm(user=admin)

        assert list(form.fields) == ["framework", "section", "requirement_number", "name", "type", "description"]
        assert form.is_multistep is False

    def test_a_requirement_is_created_and_lands_on_its_page(self, client, admin):
        framework = FrameworkFactory()

        response = client.post(
            reverse("compliance:requirement-create"),
            {"framework": str(framework.pk), "requirement_number": "A.5.1",
             "name": "Policies for information security", "type": "mandatory",
             "description": "<p>A policy is defined and approved by management.</p>"},
            **DRAWER,
        )

        requirement = Requirement.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == requirement.get_absolute_url()
        # Who answers for meeting it is decided on its page, not assumed.
        assert requirement.owner is None and requirement.created_by == admin


class TestItsSectionIsOneOfItsFramework:
    def test_opened_from_a_framework_it_offers_the_sections_of_that_framework(self, admin):
        framework = FrameworkFactory()
        mine = SectionFactory(framework=framework, name="Organizational controls")
        SectionFactory(name="A section of another text")

        form = RequirementCreateForm(user=admin, initial={"framework": framework.pk})

        assert list(form.fields["section"].queryset) == [mine]

    def test_with_no_framework_known_each_section_says_where_it_belongs(self, admin):
        framework = FrameworkFactory(short_name="ISO 27001")
        section = SectionFactory(framework=framework, name="Organizational controls")

        form = RequirementCreateForm(user=admin)

        assert form.fields["section"].label_from_instance(section) == "ISO 27001 : Organizational controls"

    def test_a_section_of_another_framework_is_refused_in_words(self, admin):
        framework = FrameworkFactory()
        elsewhere = SectionFactory()

        form = RequirementCreateForm(
            {"framework": str(framework.pk), "section": str(elsewhere.pk), "name": "Policies",
             "type": "mandatory", "description": "A policy is defined."},
            user=admin,
        )

        assert not form.is_valid()
        assert form.errors["section"] == ["This section belongs to another framework."]

    def test_an_existing_requirement_offers_the_sections_of_its_framework(self, admin):
        requirement = RequirementFactory()
        mine = SectionFactory(framework=requirement.framework)
        SectionFactory()

        form = RequirementUpdateForm(instance=requirement, user=admin, section="identity")

        assert list(form.fields["section"].queryset) == [mine]


class TestWhatItStillNeeds:
    def test_a_new_requirement_asks_who_answers_for_it(self, client, admin):
        requirement = RequirementFactory()
        edit = reverse("compliance:requirement-update", kwargs={"pk": requirement.pk})

        report = completeness_of(requirement)
        html = client.get(requirement.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["owner"]
        # Advice : nothing holds the lifecycle of a requirement back.
        assert report.blocking_missing == [] and report.can_advance
        assert "Name who answers for meeting it" in html
        assert f'href="{edit}?section=follow_up"' in html

    def test_an_exclusion_asks_for_its_reason(self):
        excluded = RequirementFactory(is_applicable=False, owner=UserFactory())
        justified = RequirementFactory(
            is_applicable=False, owner=UserFactory(), applicability_justification="<p>We host nothing ourselves.</p>",
        )

        assert [item.key for item in completeness_of(excluded).advised_missing] == ["exclusion"]
        assert completeness_of(justified).is_complete


class TestItsRisks:
    def test_editing_another_card_keeps_them(self, client, admin):
        requirement = RequirementFactory()
        risk = _linkable_risk()
        requirement.linked_risks.add(risk)
        edit = reverse("compliance:requirement-update", kwargs={"pk": requirement.pk})

        response = client.post(edit, {"_section": "follow_up", "owner": str(admin.pk), "status": "active"}, **DRAWER)

        requirement.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert requirement.owner == admin
        assert list(requirement.linked_risks.all()) == [risk]

    def test_the_card_of_the_relationships_sets_them(self, client, admin):
        requirement = RequirementFactory()
        risk = _linkable_risk()
        edit = reverse("compliance:requirement-update", kwargs={"pk": requirement.pk})

        response = client.post(edit, {"_section": "relationships", "linked_risks": [str(risk.pk)]}, **DRAWER)

        assert response.status_code == 204, response.content.decode()[:400]
        assert list(requirement.linked_risks.all()) == [risk]


class TestApplicabilityDerivedFromRisks:
    def test_it_is_not_edited_by_hand(self, admin):
        framework = FrameworkFactory(applicability_managed_by_risks=True)
        requirement = RequirementFactory(framework=framework)

        form = RequirementUpdateForm(instance=requirement, user=admin, section="applicability")

        assert form.fields["is_applicable"].disabled
        assert form.fields["applicability_justification"].disabled
        assert str(form.fields["is_applicable"].help_text) == (
            "Managed automatically from linked risks for this framework."
        )


class TestThePage:
    def test_it_shows_what_it_protects_and_who_expects_it(self, client, admin):
        requirement = RequirementFactory()

        html = client.get(requirement.get_absolute_url()).content.decode()

        assert "Not filled in yet : Linked essential assets, Linked stakeholder expectations." in html

    def test_the_empty_register_explains_and_offers_the_first_requirement(self, client, admin):
        html = client.get(reverse("compliance:requirement-list")).content.decode()

        assert "No requirement yet." in html
        create = reverse("compliance:requirement-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestWhatAUserLimitedToScopesIsOffered:
    def test_the_frameworks_of_their_scopes_alone(self):
        mine, theirs = ScopeFactory(), ScopeFactory()
        group = GroupFactory()
        group.allowed_scopes.add(mine)
        user = UserFactory(is_superuser=False)
        group.users.add(user)
        reachable, out_of_reach = FrameworkFactory(), FrameworkFactory()
        reachable.scopes.add(mine)
        out_of_reach.scopes.add(theirs)

        form = RequirementCreateForm(user=user)

        assert list(form.fields["framework"].queryset) == [reachable]


class TestTheApi:
    def test_one_requirement_carries_its_completeness_and_a_list_does_not(self, admin):
        requirement = RequirementFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/compliance/requirements/{requirement.pk}/").json()
        one = one.get("data", one)
        many = api.get("/api/v1/compliance/requirements/").json()
        rows = many.get("data", many.get("results", many))

        assert one["completeness"]["complete"] is False
        assert [item["key"] for item in one["completeness"]["missing"]] == ["owner"]
        assert rows and "completeness" not in rows[0]

    def test_the_mcp_server_reports_the_same_list(self, admin):
        record = RequirementFactory()

        read = _mcp(admin, "get_requirement", {"id": str(record.pk)})

        assert [item["key"] for item in read["completeness"]["missing"]] == ["owner"]

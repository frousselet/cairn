# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A finding is noted on one screen; a nonconformity is completed on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the finding : how a nonconformity came to light is a decision
nobody takes for the reader, what is recommended and whether the correction
worked are written on its page, and the page shows the action plans that
correct it.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from compliance.constants import FindingSource, FindingType
from compliance.forms import FindingCreateForm, FindingRegisterCreateForm, FindingRegisterUpdateForm
from compliance.models import Finding
from compliance.tests.factories import (
    ComplianceActionPlanFactory,
    ComplianceAssessmentFactory,
    FindingFactory,
    RequirementFactory,
)
from core.completeness import completeness_of

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


def _nonconformity(**fields):
    """A nonconformity raised from the register, outside any audit."""
    fields.setdefault("source", FindingSource.COMPLAINT)
    fields.setdefault("finding_type", FindingType.MINOR_NON_CONFORMITY)
    fields.setdefault("assessment", None)
    return FindingFactory(**fields)


class TestAFindingIsNotedOnOneScreen:
    def test_the_dialog_of_an_audit_has_no_second_step(self):
        form = FindingCreateForm(assessment=ComplianceAssessmentFactory())

        assert list(form.fields) == ["finding_type", "requirements", "description", "recommendation", "evidence"]
        assert form.is_multistep is False


class TestRaisingANonconformityIsShort:
    def test_it_asks_how_it_came_to_light_and_what_it_is(self, admin):
        form = FindingRegisterCreateForm(user=admin)

        assert list(form.fields) == ["source", "finding_type", "description", "requirements"]
        assert form.is_multistep is False

    def test_its_source_and_its_type_are_decisions_nobody_takes_for_the_reader(self, client, admin):
        html = client.get(reverse("compliance:finding-register-create"), **DRAWER).content.decode()

        for name in ("source", "finding_type"):
            select = html[html.index(f'name="{name}"'):]
            select = select[:select.index("</select>")]
            assert 'value="" selected' in select, name
            assert select.count("selected") == 1, name

    def test_the_sources_offered_are_those_the_register_can_record(self, admin):
        offered = [value for value, _label in FindingRegisterCreateForm(user=admin).fields["source"].choices]

        # An audit finding is raised in its audit, a control test finding from its run.
        assert offered == ["", "incident", "management_review", "monitoring", "complaint"]

    def test_a_nonconformity_is_raised_and_lands_on_its_page(self, client, admin):
        response = client.post(
            reverse("compliance:finding-register-create"),
            {"source": "complaint", "finding_type": "minor_nc",
             "description": "<p>A customer received another customer's report.</p>"},
            **DRAWER,
        )

        raised = Finding.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == raised.get_absolute_url()
        assert raised.assessor == admin and raised.assessment is None
        assert raised.recommendation == ""


class TestWhatItStillNeeds:
    def test_a_new_nonconformity_lists_what_would_make_it_useful(self, client, admin):
        finding = _nonconformity()
        edit = reverse("compliance:finding-register-update", kwargs={"pk": finding.pk})

        report = completeness_of(finding)
        html = client.get(finding.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["requirements", "recommendation"]
        # Advice : nothing holds its lifecycle back.
        assert report.blocking_missing == [] and report.can_advance
        assert "Fill in the recommendation" in html
        assert f'href="{edit}?section=nonconformity"' in html
        assert f'href="{edit}?section=treatment"' in html

    def test_a_strength_calls_for_no_recommendation(self):
        strength = _nonconformity(finding_type=FindingType.STRENGTH)
        strength.requirements.add(RequirementFactory())

        assert completeness_of(strength).is_complete

    def test_the_card_of_the_treatment_fills_it_and_leaves_the_rest_alone(self, client, admin):
        finding = _nonconformity(description="<p>A customer received another customer's report.</p>")
        edit = reverse("compliance:finding-register-update", kwargs={"pk": finding.pk})

        response = client.post(
            edit, {"_section": "treatment", "recommendation": "<p>Assert the recipient before sending.</p>",
                   "evidence": ""},
            **DRAWER,
        )

        finding.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert "Assert the recipient" in finding.recommendation
        assert finding.source == FindingSource.COMPLAINT
        assert "another customer" in finding.description

    def test_a_section_without_the_source_does_not_fail(self, admin):
        finding = _nonconformity()

        form = FindingRegisterUpdateForm(instance=finding, user=admin, section="effectiveness")

        assert list(form.fields) == [
            "effectiveness_verdict", "effectiveness_reviewed_at", "effectiveness_reviewed_by",
        ]


class TestThePage:
    def test_it_shows_the_action_plans_that_correct_it(self, client, admin):
        finding = _nonconformity()
        plan = ComplianceActionPlanFactory(name="Assert the recipient of a report")
        plan.findings.add(finding)

        html = client.get(finding.get_absolute_url()).content.decode()

        assert "Assert the recipient of a report" in html
        assert f'href="{plan.get_absolute_url()}"' in html

    def test_with_no_action_plan_it_says_where_one_is_linked(self, client, admin):
        html = client.get(_nonconformity().get_absolute_url()).content.decode()

        assert "No action plan corrects this nonconformity yet." in html

    def test_the_empty_register_explains_and_offers_to_raise_the_first(self, client, admin):
        html = client.get(reverse("compliance:finding-list")).content.decode()

        assert "No nonconformity yet." in html
        create = reverse("compliance:finding-register-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApi:
    def test_one_finding_carries_its_completeness(self, admin):
        # The REST API serves the findings of an assessment.
        finding = FindingFactory(finding_type=FindingType.MINOR_NON_CONFORMITY)
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/compliance/assessments/{finding.assessment_id}/findings/{finding.pk}/").json()
        one = one.get("data", one)

        assert one["completeness"]["complete"] is False
        assert [item["key"] for item in one["completeness"]["missing"]] == ["requirements", "recommendation"]
        assert all(item["blocking"] is False for item in one["completeness"]["missing"])

    def test_the_mcp_server_reports_the_same_list(self, admin):
        record = _nonconformity()

        read = _mcp(admin, "get_finding", {"id": str(record.pk)})

        assert [item["key"] for item in read["completeness"]["missing"]] == ["requirements", "recommendation"]

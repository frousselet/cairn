# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Workshop 5 of an EBIOS RM study : the summary and the measures of the security improvement plan.

What every form of the usability standard does is checked for all of them in
``core/tests/test_usability_standard.py``, and what a workshop page does in
``test_ebios_w1_completion.py``. This file holds what is particular to
workshop 5 : the summary is edited one card at a time, a measure of the plan is
created with five fields and belongs to whoever adds it, and what it links to
is picked in its own study.
"""

import json

import pytest
from django.urls import reverse

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from core.completeness import completeness_of
from risks.constants import EbiosWorkshopNumber
from risks.forms_ebios import EbiosSummaryForm, PACSMeasureCreateForm, PACSMeasureForm
from risks.models import PACSMeasure
from risks.tests.factories import (
    BaselineGapFactory,
    EbiosAssessmentFactory,
    PACSMeasureFactory,
    RiskCriteriaFactory,
    RiskLevelFactory,
)

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _user_with(*codenames, scopes=()):
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    for scope in scopes:
        group.allowed_scopes.add(scope)
    group.users.add(user)
    return user


def _study(**kwargs):
    """A study, its summary and the page of its workshop 5."""
    assessment = EbiosAssessmentFactory(**kwargs)
    workshop = assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W5)
    # The page builds the summary of a study that has none yet.
    from risks.signals import ensure_ebios_artifacts

    ensure_ebios_artifacts(assessment)
    return assessment, assessment.ebios_summary, workshop


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


class TestTheSummary:
    def test_its_form_has_a_section_for_each_card_of_the_page(self, admin):
        _assessment, summary, _workshop = _study()

        assert EbiosSummaryForm.section_keys() == ["strategy", "monitoring", "plan"]
        assert list(EbiosSummaryForm(instance=summary, user=admin, section="monitoring").fields) == [
            "monitoring_plan", "next_strategic_cycle_date", "next_operational_cycle_date",
        ]

    def test_a_card_sets_its_own_fields_and_leaves_the_others(self, client, admin):
        _assessment, summary, workshop = _study()
        summary.pacs_summary = "<p>Two structuring measures.</p>"
        summary.save()

        response = client.post(
            reverse("risks:ebios-summary-update", kwargs={"pk": summary.pk}),
            {"_section": "strategy", "residual_risk_strategy": "<p>Accepted for <strong>one</strong> cycle.</p>"},
            **DRAWER,
        )
        html = client.get(workshop.get_absolute_url()).content.decode()

        summary.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert summary.pacs_summary == "<p>Two structuring measures.</p>"
        # What was typed in the editor is shown formatted, not with its tags.
        assert "Accepted for <strong>one</strong> cycle." in html and "&lt;p&gt;" not in html
        for section in ("strategy", "monitoring", "plan"):
            assert f'?section={section}"' in html


class TestAMeasureOfThePlan:
    def test_creation_asks_its_name_its_type_its_priority_its_owner_and_its_target_date(self, admin):
        _assessment, summary, _workshop = _study()

        form = PACSMeasureCreateForm(summary=summary, user=admin)

        assert list(form.fields) == ["name", "measure_type", "priority", "owner", "target_date"]
        assert form.is_multistep is False
        # Whoever adds the measure carries it unless they say otherwise.
        assert form.fields["owner"].initial == admin.pk
        # "Protection" and "Medium" are not chosen for the reader.
        for name in ("measure_type", "priority"):
            assert form.fields[name].required and not form.initial.get(name)

    def test_it_is_added_from_the_side_panel_and_comes_last(self, client, admin):
        _assessment, summary, _workshop = _study()
        PACSMeasureFactory(summary=summary, order=1)

        response = client.post(
            reverse("risks:ebios-pacs-measure-create", kwargs={"summary_pk": summary.pk}),
            {"name": "Separate the office network from the industrial network", "measure_type": "protection",
             "priority": "high", "owner": str(admin.pk), "target_date": "2027-06-30"},
            **DRAWER,
        )

        measure = PACSMeasure.objects.get(name__startswith="Separate")
        assert response.status_code == 204, response.content.decode()[:400]
        assert (measure.summary, measure.owner, measure.created_by, measure.order) == (summary, admin, admin, 2)

    def test_editing_it_has_three_sections(self, admin):
        _assessment, summary, _workshop = _study()
        measure = PACSMeasureFactory(summary=summary)

        form = PACSMeasureForm(instance=measure, summary=summary, user=admin, section="planning")

        assert PACSMeasureForm.section_keys() == ["measure", "planning", "relations"]
        assert list(form.fields) == [
            "owner", "start_date", "target_date", "completion_date", "progress_percentage", "order",
        ]

    def test_what_it_links_to_is_picked_in_its_own_study(self, admin):
        """The pickers listed the baseline gaps of every study, and every requirement of the instance."""
        assessment, summary, _workshop = _study()
        other, _other_summary, _other_workshop = _study()
        ours = BaselineGapFactory(baseline=assessment.ebios_security_baseline)
        BaselineGapFactory(baseline=other.ebios_security_baseline)
        applied, elsewhere = FrameworkFactory(workflow_state="validated"), FrameworkFactory(workflow_state="validated")
        assessment.ebios_security_baseline.baseline_references.add(applied)
        wanted = RequirementFactory(framework=applied, workflow_state="validated")
        RequirementFactory(framework=elsewhere, workflow_state="validated")
        measure = PACSMeasureFactory(summary=summary)

        form = PACSMeasureForm(instance=measure, summary=summary, user=admin)

        assert list(form.fields["linked_baseline_gaps"].queryset) == [ours]
        assert list(form.fields["linked_requirements"].queryset) == [wanted]

    def test_its_relations_are_set_from_their_section(self, client, admin):
        assessment, summary, _workshop = _study()
        gap = BaselineGapFactory(baseline=assessment.ebios_security_baseline)
        measure = PACSMeasureFactory(summary=summary, name="Segmentation", priority="high")

        response = client.post(
            reverse("risks:ebios-pacs-measure-update", kwargs={"pk": measure.pk}),
            {"_section": "relations", "linked_baseline_gaps": [str(gap.pk)]},
            **DRAWER,
        )

        measure.refresh_from_db()
        assert response.status_code == 204, response.content.decode()[:400]
        assert list(measure.linked_baseline_gaps.all()) == [gap]
        assert (measure.name, measure.priority) == ("Segmentation", "high")


class TestThePageOfTheWorkshop:
    def test_an_empty_workshop_says_what_to_do_first(self, client, admin):
        _assessment, summary, workshop = _study()
        new_measure = reverse("risks:ebios-pacs-measure-create", kwargs={"summary_pk": summary.pk})

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "No PACS measure yet." in html
        assert html.count(f'hx-get="{new_measure}"') == 2  # the card and its empty state
        assert "Capture before treatment" in html and "Capture after treatment" in html

    def test_a_snapshot_reads_its_levels_by_name(self, client, admin):
        criteria = RiskCriteriaFactory()
        RiskLevelFactory(criteria=criteria, level=3, name="Significant")
        _assessment, summary, workshop = _study(risk_criteria=criteria)
        summary.risk_mapping_before = {"total": 4, "by_current_risk_level": {"3": 4}}
        summary.save()

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert '<span class="tabular-nums">3</span> - Significant : <span class="tabular-nums">4</span>' in html

    def test_a_reader_is_offered_nothing_to_change(self, client):
        assessment, summary, workshop = _study()
        measure = PACSMeasureFactory(summary=summary)
        client.force_login(_user_with("risks.ebios_assessment.read", "risks.ebios_summary.read"))

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert measure.name in html
        for fragment in ("/create/", "/edit/", "/delete/", "capture-mappings"):
            assert fragment not in html.split('id="residual-risk-strategy"')[1], fragment


class TestWhatTheWorkshopStillNeeds:
    def test_a_new_study_lists_what_workshop_5_needs(self, client, admin):
        _assessment, _summary, workshop = _study()

        report = completeness_of(workshop)
        html = client.get(workshop.get_absolute_url()).content.decode()

        assert [item.key for item in report.blocking_missing] == ["w5_measures", "w5_strategy"]
        assert [item.key for item in report.advised_missing] == ["w5_monitoring"]
        for anchor in ("pacs-measures", "residual-risk-strategy", "monitoring-plan"):
            assert f'href="{workshop.get_absolute_url()}#{anchor}"' in html and f'id="{anchor}"' in html

    def test_a_measure_nobody_carries_is_pointed_out(self):
        _assessment, summary, workshop = _study()
        PACSMeasureFactory(summary=summary, owner=None, target_date=None)

        assert "w5_owners" in [item.key for item in completeness_of(workshop).advised_missing]

    def test_it_is_not_validated_without_a_measure_and_a_strategy(self, client, admin):
        assessment, summary, workshop = _study()
        type(workshop).objects.filter(pk=workshop.pk).update(workflow_state="under_review")
        url = reverse("risks:ebios-workshop-validate", kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk})

        refused = client.post(url, follow=True)
        workshop.refresh_from_db()
        state = workshop.workflow_state
        PACSMeasureFactory(summary=summary)
        summary.residual_risk_strategy = "<p>Accepted for one cycle.</p>"
        summary.save()
        client.post(url)
        workshop.refresh_from_db()

        assert state == "under_review"
        assert "add a measure to the security improvement plan (PACS)" in refused.content.decode()
        assert workshop.workflow_state == "validated"


class TestTheMcpServer:
    def test_it_sets_what_a_measure_links_to(self, admin):
        """The three relations of a measure were set by the page and the REST API only."""
        assessment, summary, _workshop = _study()
        measure = PACSMeasureFactory(summary=summary)
        gap = BaselineGapFactory(baseline=assessment.ebios_security_baseline)
        requirement = RequirementFactory(workflow_state="validated")

        answer = _mcp(admin, "update_ebios_pacs_measure", {
            "id": str(measure.pk), "linked_baseline_gap_ids": [str(gap.pk)],
            "linked_requirement_ids": [str(requirement.pk)],
        })

        assert "error" not in json.dumps(answer).lower(), answer
        assert list(measure.linked_baseline_gaps.all()) == [gap]
        assert list(measure.linked_requirements.all()) == [requirement]

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Workshop 3 of an EBIOS RM study : the ecosystem, the strategic scenarios and their attack paths.

What every form of the usability standard does is checked for all of them in
``core/tests/test_usability_standard.py``, and what a workshop page does in
``test_ebios_w1_completion.py``. This file holds what is particular to
workshop 3 : the four ratings of an ecosystem stakeholder read by name, a
scenario is built on what its own study retained, its two levels are named
levels of the criteria, and a step of an attack path is not asked its rank.
"""

import json

import pytest
from django.urls import reverse
from django.utils import translation

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from assets.tests.factories import SupportAssetFactory
from context.tests.factories import ScopeFactory
from core.completeness import completeness_of
from risks.constants import EbiosWorkshopNumber
from risks.forms_ebios import (
    AttackPathStepCreateForm,
    AttackPathStepForm,
    EcosystemStakeholderCreateForm,
    EcosystemStakeholderForm,
    StrategicScenarioCreateForm,
    StrategicScenarioForm,
)
from risks.models import AttackPathStep, EcosystemStakeholder, StrategicScenario
from risks.tests.factories import (
    AttackPathStepFactory,
    EbiosAssessmentFactory,
    EcosystemStakeholderFactory,
    FearedEventFactory,
    RiskCriteriaFactory,
    RiskLevelFactory,
    RiskSourceObjectivePairFactory,
    ScaleLevelFactory,
    StrategicScenarioFactory,
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
    """A study and the page of its workshop 3."""
    assessment = EbiosAssessmentFactory(**kwargs)
    return assessment, assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W3)


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


class TestAnEcosystemStakeholder:
    def test_creation_asks_its_name_its_category_and_its_four_ratings(self, admin):
        assessment, _workshop = _study()

        form = EcosystemStakeholderCreateForm(assessment=assessment, user=admin)

        assert list(form.fields) == ["name", "category", "dependency", "penetration", "maturity", "trust"]
        assert form.is_multistep is False
        assert form.fields["category"].required and not form.initial.get("category")

    def test_a_rating_says_what_each_level_means(self, admin):
        """A reader picked "3" on four scales without being told what a 3 is."""
        assessment, _workshop = _study()

        form = EcosystemStakeholderCreateForm(assessment=assessment, user=admin)

        assert [label for _value, label in form.fields["dependency"].choices] == [
            "Not assessed", "1 - Not needed", "2 - Useful", "3 - Essential, with a substitute",
            "4 - Essential, without a substitute",
        ]
        assert str(form.fields["trust"].choices[1][1]) == "1 - Intentions unknown"
        with translation.override("fr"):
            assert str(EcosystemStakeholder._meta.get_field("maturity").choices[3][1]) == "4 - Risques gérés et revus"

    def test_it_is_added_from_the_side_panel_and_lands_in_its_zone(self, client, admin):
        assessment, _workshop = _study()

        response = client.post(
            reverse("risks:ebios-ecosystem-create", kwargs={"assessment_pk": assessment.pk}),
            {"name": "The maintenance subcontractor", "category": "subcontractor", "dependency": "4",
             "penetration": "4", "maturity": "2", "trust": "2"},
            **DRAWER,
        )

        stakeholder = EcosystemStakeholder.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert (stakeholder.assessment, stakeholder.created_by) == (assessment, admin)
        assert (float(stakeholder.threat_level), stakeholder.threat_zone) == (4.0, "danger")

    def test_one_that_is_not_rated_is_not_assessed(self, client, admin):
        assessment, workshop = _study()

        client.post(
            reverse("risks:ebios-ecosystem-create", kwargs={"assessment_pk": assessment.pk}),
            {"name": "A client", "category": "customer", "dependency": "", "penetration": "", "maturity": "",
             "trust": ""},
        )
        html = client.get(workshop.get_absolute_url()).content.decode()

        assert EcosystemStakeholder.objects.get().threat_level is None
        assert "Not assessed" in html

    def test_editing_it_has_a_section_for_what_it_is_and_one_for_its_threat_level(self, client, admin):
        assessment, _workshop = _study()
        server, laptop = SupportAssetFactory(workflow_state="active"), SupportAssetFactory(workflow_state="active")
        assessment.ebios_security_baseline.support_assets.add(server)
        stakeholder = EcosystemStakeholderFactory(assessment=assessment)

        form = EcosystemStakeholderForm(instance=stakeholder, assessment=assessment, user=admin)
        response = client.post(
            reverse("risks:ebios-ecosystem-update", kwargs={"pk": stakeholder.pk}),
            {"name": stakeholder.name, "category": "supplier", "description": "", "stakeholder": "", "supplier": "",
             "accessible_support_assets": [str(server.pk)], "dependency": "2", "penetration": "2", "maturity": "2",
             "trust": "2", "is_attack_vector": "on",
             "attack_vector_justification": "<p>A permanent remote access.</p>"},
            **DRAWER,
        )

        stakeholder.refresh_from_db()
        assert EcosystemStakeholderForm.section_keys() == ["stakeholder", "threat"]
        # The support assets it reaches are those of the study.
        assert list(form.fields["accessible_support_assets"].queryset) == [server] and laptop.pk
        assert response.status_code == 204, response.content.decode()[:400]
        assert stakeholder.is_attack_vector and list(stakeholder.accessible_support_assets.all()) == [server]


class TestAStrategicScenario:
    def _criteria(self):
        criteria = RiskCriteriaFactory()
        ScaleLevelFactory(criteria=criteria, scale_type="impact", level=4, name="Critical")
        ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=2, name="Unlikely")
        return criteria

    def test_creation_asks_its_name_its_pair_its_feared_events_and_its_two_levels(self, admin):
        assessment, _workshop = _study()

        form = StrategicScenarioCreateForm(assessment=assessment, user=admin)

        assert list(form.fields) == [
            "name", "sr_ov_pair", "targeted_feared_events", "gravity_level", "likelihood_level",
        ]
        assert form.is_multistep is False

    def test_it_is_built_on_what_its_own_study_retained(self, admin):
        assessment, _workshop = _study()
        other, _other_workshop = _study()
        retained = RiskSourceObjectivePairFactory(assessment=assessment)
        RiskSourceObjectivePairFactory(assessment=assessment, is_retained=False)
        RiskSourceObjectivePairFactory(assessment=other)
        ours = FearedEventFactory(baseline=assessment.ebios_security_baseline)
        FearedEventFactory(baseline=other.ebios_security_baseline)

        form = StrategicScenarioCreateForm(assessment=assessment, user=admin)

        assert list(form.fields["sr_ov_pair"].queryset) == [retained]
        assert list(form.fields["targeted_feared_events"].queryset) == [ours]

    def test_the_pair_a_scenario_is_built_on_stays_offered_once_set_aside(self, admin):
        scenario = StrategicScenarioFactory()
        type(scenario.sr_ov_pair).objects.filter(pk=scenario.sr_ov_pair_id).update(is_retained=False)

        form = StrategicScenarioForm(instance=scenario, assessment=scenario.assessment, user=admin)

        assert list(form.fields["sr_ov_pair"].queryset) == [scenario.sr_ov_pair]

    def test_its_two_levels_are_named_levels_of_the_criteria(self, admin):
        assessment, _workshop = _study(risk_criteria=self._criteria())

        form = StrategicScenarioCreateForm(assessment=assessment, user=admin)

        assert [label for _value, label in form.fields["gravity_level"].choices] == ["Not assessed", "4 - Critical"]
        assert [label for _value, label in form.fields["likelihood_level"].choices] == ["Not assessed", "2 - Unlikely"]

    def test_it_is_added_from_the_side_panel(self, client, admin):
        assessment, _workshop = _study()
        pair = RiskSourceObjectivePairFactory(assessment=assessment)
        event = FearedEventFactory(baseline=assessment.ebios_security_baseline)

        response = client.post(
            reverse("risks:ebios-strategic-scenario-create", kwargs={"assessment_pk": assessment.pk}),
            {"name": "Production stopped through the maintenance provider", "sr_ov_pair": str(pair.pk),
             "targeted_feared_events": [str(event.pk)], "gravity_level": "", "likelihood_level": ""},
            **DRAWER,
        )

        scenario = StrategicScenario.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert (scenario.assessment, scenario.sr_ov_pair, scenario.created_by) == (assessment, pair, admin)
        assert list(scenario.targeted_feared_events.all()) == [event]
        assert (scenario.gravity_level, scenario.is_retained) == (None, True)

    def test_editing_it_has_a_section_for_the_scenario_and_one_for_its_levels(self):
        assert StrategicScenarioForm.section_keys() == ["scenario", "rating"]


class TestAStepOfAnAttackPath:
    def test_creation_does_not_ask_its_rank(self, admin):
        scenario = StrategicScenarioFactory()

        form = AttackPathStepCreateForm(scenario=scenario, user=admin)

        assert list(form.fields) == ["action_type", "difficulty", "stakeholder", "description"]
        assert form.is_multistep is False
        # "Other" is not chosen for the reader.
        assert form.fields["action_type"].required and not form.initial.get("action_type")

    def test_it_passes_through_a_stakeholder_of_its_own_study(self, admin):
        scenario = StrategicScenarioFactory()
        ours = EcosystemStakeholderFactory(assessment=scenario.assessment)
        EcosystemStakeholderFactory()

        form = AttackPathStepCreateForm(scenario=scenario, user=admin)

        assert list(form.fields["stakeholder"].queryset) == [ours]

    def test_a_new_step_comes_last(self, client, admin):
        scenario = StrategicScenarioFactory()
        url = reverse("risks:ebios-attack-path-step-create", kwargs={"scenario_pk": scenario.pk})

        first = client.post(url, {"action_type": "initial_access", "difficulty": "", "stakeholder": "",
                                  "description": "<p>Steals the credentials of a technician.</p>"}, **DRAWER)
        client.post(url, {"action_type": "lateral_movement", "difficulty": "", "stakeholder": "",
                          "description": "<p>Reaches the plant network.</p>"}, **DRAWER)

        assert first.status_code == 204, first.content.decode()[:400]
        assert [(step.order, step.action_type) for step in scenario.attack_path_steps.order_by("order")] == [
            (1, "initial_access"), (2, "lateral_movement"),
        ]
        assert scenario.attack_path_steps.first().created_by == admin

    def test_two_steps_of_one_rank_are_refused_in_words(self, client, admin):
        """The scenario is not a field of the form, so the form did not check
        the constraint that names it : the page answered with a server error."""
        scenario = StrategicScenarioFactory()
        first = AttackPathStepFactory(scenario=scenario, order=1)
        second = AttackPathStepFactory(scenario=scenario, order=2)

        form = AttackPathStepForm(instance=second, scenario=scenario, user=admin)
        response = client.post(
            reverse("risks:ebios-attack-path-step-update", kwargs={"pk": second.pk}),
            {"action_type": "disruption", "difficulty": "", "stakeholder": "", "description": "<p>x</p>", "order": "1"},
            **DRAWER,
        )

        second.refresh_from_db()
        assert "order" in form.fields
        assert response.status_code == 200
        assert "Step 1 of this attack path already exists" in response.content.decode()
        assert (first.order, second.order) == (1, 2)

    def test_a_scenario_of_another_scope_is_an_unknown_one(self, client):
        mine, theirs = ScopeFactory(), ScopeFactory()
        assessment, _workshop = _study(scopes=[theirs])
        scenario = StrategicScenarioFactory(assessment=assessment)
        client.force_login(_user_with("risks.ebios_strategic.create", "risks.ebios_strategic.read", scopes=[mine]))
        url = reverse("risks:ebios-attack-path-step-create", kwargs={"scenario_pk": scenario.pk})

        assert client.get(url).status_code == 404
        assert client.post(url, {"action_type": "disruption", "description": "x"}).status_code == 404
        assert not AttackPathStep.objects.exists()


class TestThePageOfTheWorkshop:
    def test_a_scenario_reads_its_levels_by_name_and_lists_its_attack_path(self, client, admin):
        criteria = RiskCriteriaFactory(risk_matrix={"2,4": 3})
        ScaleLevelFactory(criteria=criteria, scale_type="impact", level=4, name="Critical")
        ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=2, name="Unlikely")
        RiskLevelFactory(criteria=criteria, level=3, name="Significant")
        assessment, workshop = _study(risk_criteria=criteria)
        scenario = StrategicScenarioFactory(assessment=assessment, gravity_level=4, likelihood_level=2)
        through = EcosystemStakeholderFactory(assessment=assessment, name="The maintenance subcontractor")
        AttackPathStepFactory(scenario=scenario, order=1, stakeholder=through,
                              description="<p>Steals the <strong>credentials</strong> of a technician.</p>")
        new_step = reverse("risks:ebios-attack-path-step-create", kwargs={"scenario_pk": scenario.pk})

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert '<span class="tabular-nums">4</span> - Critical' in html
        assert '<span class="tabular-nums">2</span> - Unlikely' in html
        assert '<span class="tabular-nums">3</span> - Significant' in html
        assert "Steals the credentials of a technician." in html and "&lt;p&gt;" not in html
        assert "The maintenance subcontractor" in html and f'hx-get="{new_step}"' in html

    def test_an_empty_workshop_says_what_to_do_first(self, client, admin):
        assessment, workshop = _study()
        new_stakeholder = reverse("risks:ebios-ecosystem-create", kwargs={"assessment_pk": assessment.pk})
        new_scenario = reverse("risks:ebios-strategic-scenario-create", kwargs={"assessment_pk": assessment.pk})

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "No ecosystem stakeholder yet." in html and f'hx-get="{new_stakeholder}"' in html
        # No pair retained in workshop 2 : a scenario has nothing to be built on.
        assert "retain a pair first." in html and new_scenario not in html

    def test_once_a_pair_is_retained_the_first_scenario_is_offered(self, client, admin):
        assessment, workshop = _study()
        RiskSourceObjectivePairFactory(assessment=assessment)
        new_scenario = reverse("risks:ebios-strategic-scenario-create", kwargs={"assessment_pk": assessment.pk})

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert html.count(f'hx-get="{new_scenario}"') == 2  # the card and its empty state

    def test_a_reader_is_offered_nothing_to_change(self, client):
        step = AttackPathStepFactory()
        assessment = step.scenario.assessment
        EcosystemStakeholderFactory(assessment=assessment)
        workshop = assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W3)
        client.force_login(_user_with(
            "risks.ebios_assessment.read", "risks.ebios_ecosystem.read", "risks.ebios_strategic.read",
        ))

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert step.scenario.name in html
        for fragment in ("/create/", "/edit/", "/delete/"):
            assert fragment not in html.split('id="ecosystem-stakeholders"')[1], fragment


class TestWhatTheWorkshopStillNeeds:
    def test_a_new_study_lists_what_workshop_3_needs(self, client, admin):
        _assessment, workshop = _study()

        report = completeness_of(workshop)
        html = client.get(workshop.get_absolute_url()).content.decode()

        assert [item.key for item in report.blocking_missing] == ["w3_retained_scenario"]
        assert [item.key for item in report.advised_missing] == ["w3_ecosystem"]
        assert f'href="{workshop.get_absolute_url()}#strategic-scenarios"' in html
        assert 'id="strategic-scenarios"' in html and 'id="ecosystem-stakeholders"' in html

    def test_a_retained_scenario_is_asked_for_its_levels_and_its_attack_path(self):
        assessment, workshop = _study()
        scenario = StrategicScenarioFactory(assessment=assessment, gravity_level=None, likelihood_level=None)
        EcosystemStakeholderFactory(assessment=assessment)

        before = [item.key for item in completeness_of(workshop).advised_missing]
        AttackPathStepFactory(scenario=scenario)
        after = [item.key for item in completeness_of(workshop).advised_missing]

        assert completeness_of(workshop).blocking_missing == []
        assert before == ["w3_levels", "w3_attack_paths"] and after == ["w3_levels"]

    def test_it_is_not_validated_without_a_retained_scenario(self, client, admin):
        assessment, workshop = _study()
        scenario = StrategicScenarioFactory(assessment=assessment, is_retained=False)
        type(workshop).objects.filter(pk=workshop.pk).update(workflow_state="under_review")
        url = reverse("risks:ebios-workshop-validate", kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk})

        refused = client.post(url, follow=True)
        workshop.refresh_from_db()
        state = workshop.workflow_state
        StrategicScenario.objects.filter(pk=scenario.pk).update(is_retained=True)
        client.post(url)
        workshop.refresh_from_db()

        assert state == "under_review"
        assert "retain a strategic scenario" in refused.content.decode()
        assert workshop.workflow_state == "validated"


class TestTheMcpServer:
    def test_it_sets_what_a_stakeholder_reaches_and_what_a_scenario_leads_to(self, admin):
        """Both relations were set by the page and the REST API only."""
        assessment, _workshop = _study()
        stakeholder = EcosystemStakeholderFactory(assessment=assessment)
        scenario = StrategicScenarioFactory(assessment=assessment)
        server = SupportAssetFactory(workflow_state="active")
        event = FearedEventFactory(baseline=assessment.ebios_security_baseline)

        one = _mcp(admin, "update_ebios_ecosystem_stakeholder", {
            "id": str(stakeholder.pk), "accessible_support_asset_ids": [str(server.pk)],
        })
        other = _mcp(admin, "update_ebios_strategic_scenario", {
            "id": str(scenario.pk), "targeted_feared_event_ids": [str(event.pk)],
        })

        assert "error" not in json.dumps(one).lower() and "error" not in json.dumps(other).lower(), (one, other)
        assert list(stakeholder.accessible_support_assets.all()) == [server]
        assert list(scenario.targeted_feared_events.all()) == [event]

    def test_a_step_created_without_a_rank_comes_last(self, admin):
        """Two steps created without ``order`` took the same rank, which the database refuses."""
        scenario = StrategicScenarioFactory()

        for description in ("First move.", "Second move."):
            answer = _mcp(admin, "create_ebios_attack_path_step", {
                "scenario_id": str(scenario.pk), "description": description, "action_type": "initial_access",
            })
            assert "error" not in json.dumps(answer).lower(), answer

        assert [step.order for step in scenario.attack_path_steps.order_by("order")] == [1, 2]

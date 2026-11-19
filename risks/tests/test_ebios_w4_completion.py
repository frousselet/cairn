# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Workshop 4 of an EBIOS RM study : the operational scenarios and their attack techniques.

What every form of the usability standard does is checked for all of them in
``core/tests/test_usability_standard.py``, and what a workshop page does in
``test_ebios_w1_completion.py``. This file holds what is particular to
workshop 4 : the gravity of a scenario is the one of its strategic scenario
unless it says otherwise, a technique is a MITRE ATT&CK entry or a name of
one's own, and the version of the catalogue is recorded, not typed.
"""

import json
from html import unescape

import pytest
from django.urls import reverse

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from assets.tests.factories import SupportAssetFactory
from core.completeness import completeness_of
from risks.constants import EbiosWorkshopNumber
from risks.forms_ebios import (
    AttackTechniqueCreateForm,
    AttackTechniqueForm,
    OperationalScenarioCreateForm,
    OperationalScenarioForm,
)
from risks.models import AttackTechnique, OperationalScenario, StrategicScenario
from risks.tests.factories import (
    AttackTechniqueFactory,
    EbiosAssessmentFactory,
    MitreAttackTechniqueFactory,
    OperationalScenarioFactory,
    RiskCriteriaFactory,
    RiskLevelFactory,
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
    """A study and the page of its workshop 4."""
    assessment = EbiosAssessmentFactory(**kwargs)
    return assessment, assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W4)


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


class TestAnOperationalScenario:
    def test_creation_asks_the_strategic_scenario_the_name_the_targets_and_the_likelihood(self, admin):
        assessment, _workshop = _study()

        form = OperationalScenarioCreateForm(assessment=assessment, user=admin)

        assert list(form.fields) == ["strategic_scenario", "name", "targeted_support_assets", "likelihood_v"]
        assert form.is_multistep is False
        # Its gravity is the one of its strategic scenario : it is not a question.
        assert "gravity_level" not in form.fields and "mitre_version" not in form.fields
        assert [label for _value, label in form.fields["likelihood_v"].choices][:2] == ["Not assessed", "V1 - Minimal"]

    def test_it_details_a_strategic_scenario_retained_in_its_own_study(self, admin):
        assessment, _workshop = _study()
        retained = StrategicScenarioFactory(assessment=assessment)
        StrategicScenarioFactory(assessment=assessment, is_retained=False)
        StrategicScenarioFactory()
        server, laptop = SupportAssetFactory(workflow_state="active"), SupportAssetFactory(workflow_state="active")
        assessment.ebios_security_baseline.support_assets.add(server)

        form = OperationalScenarioCreateForm(assessment=assessment, user=admin)

        assert list(form.fields["strategic_scenario"].queryset) == [retained]
        assert list(form.fields["targeted_support_assets"].queryset) == [server] and laptop.pk

    def test_it_is_added_from_the_side_panel_with_the_gravity_of_its_strategic_scenario(self, client, admin):
        criteria = RiskCriteriaFactory(risk_matrix={"3,4": 4})
        assessment, _workshop = _study(risk_criteria=criteria)
        parent = StrategicScenarioFactory(assessment=assessment, gravity_level=4)

        response = client.post(
            reverse("risks:ebios-operational-scenario-create", kwargs={"assessment_pk": assessment.pk}),
            {"strategic_scenario": str(parent.pk), "name": "Ransomware through the maintenance access",
             "likelihood_v": "3"},
            **DRAWER,
        )

        scenario = OperationalScenario.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert (scenario.assessment, scenario.created_by) == (assessment, admin)
        assert (scenario.gravity_inherited, scenario.gravity_level, scenario.risk_level) == (True, 4, 4)

    def test_a_gravity_of_its_own_is_a_level_and_a_reason(self, client, admin):
        """Rule RE-10 was written and not applied : the form took a bare
        number, and no reason."""
        criteria = RiskCriteriaFactory()
        ScaleLevelFactory(criteria=criteria, scale_type="impact", level=2, name="Limited")
        assessment, _workshop = _study(risk_criteria=criteria)
        scenario = OperationalScenarioFactory(
            assessment=assessment, strategic_scenario=StrategicScenarioFactory(assessment=assessment, gravity_level=4),
        )
        url = reverse("risks:ebios-operational-scenario-update", kwargs={"pk": scenario.pk})
        answers = {"_section": "rating", "likelihood_v": "2", "likelihood_justification": ""}

        refused = client.post(url, {**answers, "gravity_level": "", "gravity_override_justification": ""}, **DRAWER)
        accepted = client.post(url, {
            **answers, "gravity_level": "2",
            "gravity_override_justification": "<p>This path reaches the test bench only.</p>",
        }, **DRAWER)

        scenario.refresh_from_db()
        said = unescape(refused.content.decode())
        assert refused.status_code == 200
        assert "Choose the gravity of the scenario" in said and "Say why the scenario has a gravity of its own." in said
        assert accepted.status_code == 204, accepted.content.decode()[:400]
        assert (scenario.gravity_inherited, scenario.gravity_level) == (False, 2)

    def test_editing_it_has_a_section_for_the_scenario_and_one_for_its_levels(self, admin):
        scenario = OperationalScenarioFactory()

        form = OperationalScenarioForm(instance=scenario, assessment=scenario.assessment, user=admin, section="rating")

        assert OperationalScenarioForm.section_keys() == ["scenario", "rating"]
        assert list(form.fields) == [
            "likelihood_v", "likelihood_justification", "gravity_inherited", "gravity_level",
            "gravity_override_justification",
        ]


class TestAnAttackTechnique:
    def test_creation_asks_the_technique_its_description_its_target_and_its_difficulty(self, admin):
        scenario = OperationalScenarioFactory()

        form = AttackTechniqueCreateForm(scenario=scenario, user=admin)

        assert list(form.fields) == [
            "mitre_technique", "custom_name", "description", "targeted_support_asset", "difficulty",
        ]
        assert form.is_multistep is False

    def test_the_catalogue_is_listed_under_its_tactics(self, admin):
        # Identifiers of their own : where the migrations are replayed, the
        # catalogue is already there.
        access = MitreAttackTechniqueFactory(mitre_id="T9901", name="A way in", tactic="initial_access")
        damage = MitreAttackTechniqueFactory(mitre_id="T9902", name="A way to harm", tactic="impact")
        MitreAttackTechniqueFactory(mitre_id="T9903", name="Retired", tactic="impact", is_active=False)

        choices = AttackTechniqueCreateForm(scenario=OperationalScenarioFactory(), user=admin).fields["mitre_technique"].choices
        groups = dict(choices[1:])

        assert choices[0] == ("", "None")
        assert (access.pk, "T9901 A way in") in groups["Initial access"]
        assert (damage.pk, "T9902 A way to harm") in groups["Impact"]
        assert "T9903 Retired" not in [label for options in groups.values() for _pk, label in options]

    def test_it_is_a_mitre_technique_or_a_name_of_ones_own(self, client, admin):
        scenario = OperationalScenarioFactory()
        url = reverse("risks:ebios-attack-technique-create", kwargs={"scenario_pk": scenario.pk})
        answers = {"description": "<p>An operator is paid to plug in a key.</p>", "targeted_support_asset": "",
                   "difficulty": ""}

        refused = client.post(url, {**answers, "mitre_technique": "", "custom_name": ""}, **DRAWER)
        accepted = client.post(url, {**answers, "mitre_technique": "", "custom_name": "Bribes an operator"}, **DRAWER)

        technique = AttackTechnique.objects.get()
        assert refused.status_code == 200
        assert "Choose a MITRE technique or fill in a custom name." in refused.content.decode()
        assert accepted.status_code == 204, accepted.content.decode()[:400]
        assert (technique.custom_name, technique.order, technique.created_by) == ("Bribes an operator", 1, admin)

    def test_the_version_of_the_catalogue_is_recorded_not_typed(self, client, admin):
        """Rule RE-13 : the scenario keeps the version of the catalogue its
        techniques come from. It was a text field a reader had to fill in."""
        scenario = OperationalScenarioFactory(mitre_version="")
        phishing = MitreAttackTechniqueFactory(mitre_id="T9911", version="15.1")
        later = MitreAttackTechniqueFactory(mitre_id="T9912", version="16.0")
        url = reverse("risks:ebios-attack-technique-create", kwargs={"scenario_pk": scenario.pk})

        client.post(url, {"mitre_technique": str(phishing.pk), "custom_name": "", "description": "<p>x</p>"}, **DRAWER)
        client.post(url, {"mitre_technique": str(later.pk), "custom_name": "", "description": "<p>y</p>"}, **DRAWER)

        scenario.refresh_from_db()
        # The first technique dates the scenario; a later one does not move it.
        assert scenario.mitre_version == "15.1"
        assert [technique.order for technique in scenario.attack_techniques.order_by("order")] == [1, 2]

    def test_its_target_is_a_support_asset_of_the_scenario(self, admin):
        scenario = OperationalScenarioFactory()
        aimed, other = SupportAssetFactory(workflow_state="active"), SupportAssetFactory(workflow_state="active")
        scenario.targeted_support_assets.add(aimed)

        form = AttackTechniqueCreateForm(scenario=scenario, user=admin)

        assert list(form.fields["targeted_support_asset"].queryset) == [aimed] and other.pk

    def test_two_techniques_of_one_rank_are_refused_in_words(self, client, admin):
        scenario = OperationalScenarioFactory()
        AttackTechniqueFactory(scenario=scenario, order=1)
        second = AttackTechniqueFactory(scenario=scenario, order=2)

        form = AttackTechniqueForm(instance=second, scenario=scenario, user=admin)
        response = client.post(
            reverse("risks:ebios-attack-technique-update", kwargs={"pk": second.pk}),
            {"mitre_technique": str(second.mitre_technique_id or ""), "custom_name": second.custom_name or "A name",
             "description": "<p>x</p>", "targeted_support_asset": "", "difficulty": "", "detection_difficulty": "",
             "order": "1"},
            **DRAWER,
        )

        second.refresh_from_db()
        assert "order" in form.fields and "detection_difficulty" in form.fields
        assert response.status_code == 200
        assert "Technique 1 of this scenario already exists" in response.content.decode()
        assert second.order == 2


class TestThePageOfTheWorkshop:
    def test_a_scenario_reads_its_levels_by_name_and_lists_its_techniques(self, client, admin):
        criteria = RiskCriteriaFactory(risk_matrix={"3,4": 4})
        ScaleLevelFactory(criteria=criteria, scale_type="impact", level=4, name="Critical")
        RiskLevelFactory(criteria=criteria, level=4, name="Intolerable")
        assessment, workshop = _study(risk_criteria=criteria)
        scenario = OperationalScenarioFactory(
            assessment=assessment, likelihood_v=3,
            strategic_scenario=StrategicScenarioFactory(assessment=assessment, gravity_level=4),
        )
        AttackTechniqueFactory(
            scenario=scenario, order=1, description="<p>A <strong>booby-trapped</strong> work order is opened.</p>",
        )
        new_technique = reverse("risks:ebios-attack-technique-create", kwargs={"scenario_pk": scenario.pk})
        consolidate = reverse("risks:ebios-operational-scenario-consolidate", kwargs={"pk": scenario.pk})

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert "V3 - Strong" in html
        assert '<span class="tabular-nums">4</span> - Critical' in html and "(inherited)" in html
        assert '<span class="tabular-nums">4</span> - Intolerable' in html
        assert "A booby-trapped work order is opened." in html and "&lt;p&gt;" not in html
        assert f'hx-get="{new_technique}"' in html
        # The way to the register carries its words.
        assert f'action="{consolidate}"' in html and "Add to the risk register" in html

    def test_a_scenario_added_to_the_register_links_to_its_risk(self, client, admin):
        assessment, workshop = _study()
        scenario = OperationalScenarioFactory(assessment=assessment)

        client.post(reverse("risks:ebios-operational-scenario-consolidate", kwargs={"pk": scenario.pk}))
        html = client.get(workshop.get_absolute_url()).content.decode()

        scenario.refresh_from_db()
        assert scenario.consolidated_risk is not None
        assert scenario.consolidated_risk.get_absolute_url() in html
        assert reverse("risks:ebios-operational-scenario-consolidate", kwargs={"pk": scenario.pk}) not in html

    def test_an_empty_workshop_says_what_to_do_first(self, client, admin):
        assessment, workshop = _study()
        new_scenario = reverse("risks:ebios-operational-scenario-create", kwargs={"assessment_pk": assessment.pk})

        before = client.get(workshop.get_absolute_url()).content.decode()
        StrategicScenarioFactory(assessment=assessment)
        after = client.get(workshop.get_absolute_url()).content.decode()

        # No strategic scenario retained in workshop 3 : nothing to detail.
        assert "retain one first." in before and new_scenario not in before
        assert after.count(f'hx-get="{new_scenario}"') == 2  # the card and its empty state

    def test_a_reader_is_offered_nothing_to_change(self, client):
        technique = AttackTechniqueFactory()
        assessment = technique.scenario.assessment
        workshop = assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W4)
        client.force_login(_user_with("risks.ebios_assessment.read", "risks.ebios_operational.read"))

        html = client.get(workshop.get_absolute_url()).content.decode()

        assert technique.scenario.name in html
        for fragment in ("/create/", "/edit/", "/delete/", "/consolidate/"):
            assert fragment not in html.split('id="operational-scenarios"')[1], fragment


class TestWhatTheWorkshopStillNeeds:
    def test_each_retained_strategic_scenario_asks_for_its_operational_scenario(self, client, admin):
        assessment, workshop = _study()
        detailed, bare = StrategicScenarioFactory(assessment=assessment), StrategicScenarioFactory(assessment=assessment)
        StrategicScenarioFactory(assessment=assessment, is_retained=False)
        OperationalScenarioFactory(assessment=assessment, strategic_scenario=detailed, likelihood_v=None)

        report = completeness_of(workshop)
        html = client.get(workshop.get_absolute_url()).content.decode()

        assert bare.pk and [item.key for item in report.blocking_missing] == ["w4_scenarios"]
        assert [item.key for item in report.advised_missing] == ["w4_likelihood", "w4_techniques"]
        assert f'href="{workshop.get_absolute_url()}#operational-scenarios"' in html
        assert 'id="operational-scenarios"' in html

    def test_it_is_not_validated_while_a_retained_strategic_scenario_is_not_detailed(self, client, admin):
        assessment, workshop = _study()
        parent = StrategicScenarioFactory(assessment=assessment)
        type(workshop).objects.filter(pk=workshop.pk).update(workflow_state="under_review")
        url = reverse("risks:ebios-workshop-validate", kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk})

        refused = client.post(url, follow=True)
        workshop.refresh_from_db()
        state = workshop.workflow_state
        OperationalScenarioFactory(assessment=assessment, strategic_scenario=parent)
        client.post(url)
        workshop.refresh_from_db()

        assert state == "under_review"
        assert "add an operational scenario for each retained strategic scenario" in refused.content.decode()
        assert workshop.workflow_state == "validated"
        assert StrategicScenario.objects.filter(pk=parent.pk, operational_scenarios__isnull=False).exists()


class TestTheMcpServer:
    def test_it_sets_what_a_scenario_aims_at(self, admin):
        scenario = OperationalScenarioFactory()
        server = SupportAssetFactory(workflow_state="active")

        answer = _mcp(admin, "update_ebios_operational_scenario", {
            "id": str(scenario.pk), "targeted_support_asset_ids": [str(server.pk)],
        })

        assert "error" not in json.dumps(answer).lower(), answer
        assert list(scenario.targeted_support_assets.all()) == [server]

    def test_a_technique_created_without_a_rank_comes_last_and_dates_the_scenario(self, admin):
        scenario = OperationalScenarioFactory(mitre_version="")
        phishing = MitreAttackTechniqueFactory(mitre_id="T9921", version="15.1")

        for arguments in (
            {"mitre_technique_id": str(phishing.pk), "description": "A booby-trapped document."},
            {"custom_name": "Bribes an operator", "description": "An operator is paid."},
        ):
            answer = _mcp(admin, "create_ebios_attack_technique", {"scenario_id": str(scenario.pk), **arguments})
            assert "error" not in json.dumps(answer).lower(), answer

        scenario.refresh_from_db()
        assert [technique.order for technique in scenario.attack_techniques.order_by("order")] == [1, 2]
        assert scenario.mitre_version == "15.1"

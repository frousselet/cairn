# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The rows of an EBIOS RM workshop show their lifecycle bar.

A row (a feared event, a risk source, a strategic scenario, a measure of the
security improvement plan...) runs a lifecycle, and nothing in the interface
made it move : the rows are added and edited in the side panel of their
workshop page, which held neither a bar nor a step field. The page of a row
being edited (its edit address, opened as a page) now shows the lifecycle bar
above the form, and the side panel says the step it stands at with a link to
that page.

Nine of the eleven row types asked their moves for a permission that does not
exist (``risks.fearedevent.update``, derived from the model name) : only a
superuser could have moved them, bar or not. Each now names the permission
feature its views ask for.
"""

import pytest
from django.urls import reverse

from accounts.models import Permission
from accounts.tests.factories import GroupFactory, UserFactory
from core.models import LifecycleEvent
from risks.tests import factories as f

pytestmark = pytest.mark.django_db

#: Each row type : its factory, the route of its edit page, the permission
#: feature its views ask for.
ROWS = [
    (f.FearedEventFactory, "risks:ebios-feared-event-update", "risks.ebios_baseline"),
    (f.BaselineGapFactory, "risks:ebios-baseline-gap-update", "risks.ebios_baseline"),
    (f.RiskSourceFactory, "risks:ebios-risk-source-update", "risks.ebios_risk_source"),
    (f.TargetedObjectiveFactory, "risks:ebios-targeted-objective-update", "risks.ebios_risk_source"),
    (f.RiskSourceObjectivePairFactory, "risks:ebios-sr-ov-pair-update", "risks.ebios_risk_source"),
    (f.EcosystemStakeholderFactory, "risks:ebios-ecosystem-update", "risks.ebios_ecosystem"),
    (f.StrategicScenarioFactory, "risks:ebios-strategic-scenario-update", "risks.ebios_strategic"),
    (f.AttackPathStepFactory, "risks:ebios-attack-path-step-update", "risks.ebios_strategic"),
    (f.OperationalScenarioFactory, "risks:ebios-operational-scenario-update", "risks.ebios_operational"),
    (f.AttackTechniqueFactory, "risks:ebios-attack-technique-update", "risks.ebios_operational"),
    (f.PACSMeasureFactory, "risks:ebios-pacs-measure-update", "risks.ebios_summary"),
]
IDS = [route.split(":")[1].removeprefix("ebios-").removesuffix("-update") for _f, route, _n in ROWS]


def _user_with(*codenames):
    """A user of an unrestricted group holding exactly these permissions."""
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    group.users.add(user)
    return user


def _transition_url(obj):
    return reverse(
        "workflow:transition",
        kwargs={"app_label": obj._meta.app_label, "model": obj._meta.model_name, "pk": obj.pk},
    )


class TestWhoMovesARow:
    @pytest.mark.parametrize("factory, route, feature", ROWS, ids=IDS)
    def test_a_row_asks_its_moves_of_the_feature_its_views_ask_for(self, factory, route, feature):
        row = factory()

        assert row.workflow_perm_namespace == feature
        for transition in row.get_lifecycle().transitions:
            action = transition.permission_action or "update"
            assert Permission.objects.filter(codename=f"{feature}.{action}").exists(), (feature, action)

    def test_who_may_change_a_feared_event_submits_it(self, client):
        event = f.FearedEventFactory()
        client.force_login(_user_with("risks.ebios_baseline.read", "risks.ebios_baseline.update"))

        client.post(_transition_url(event), {"target_status": "pending"})

        event.refresh_from_db()
        assert event.workflow_state == "pending"
        journal = LifecycleEvent.objects.filter(object_id=str(event.pk)).first()
        assert (journal.from_step, journal.to_step) == ("draft", "pending")

    def test_validating_a_row_asks_for_approve(self, client):
        source = f.RiskSourceFactory(workflow_state="pending")
        client.force_login(_user_with("risks.ebios_risk_source.read", "risks.ebios_risk_source.update"))

        client.post(_transition_url(source), {"target_status": "validated"})
        source.refresh_from_db()
        assert source.workflow_state == "pending"

        client.force_login(_user_with(
            "risks.ebios_risk_source.read", "risks.ebios_risk_source.update", "risks.ebios_risk_source.approve",
        ))
        client.post(_transition_url(source), {"target_status": "validated"})
        source.refresh_from_db()
        assert source.workflow_state == "validated"

    def test_a_reader_of_the_feature_reads_the_history_of_a_row(self, client):
        scenario = f.StrategicScenarioFactory()
        client.force_login(_user_with("risks.ebios_strategic.read"))

        response = client.get(reverse("history:partial", kwargs={
            "app_label": "risks", "model": "strategicscenario", "pk": scenario.pk,
        }))

        assert response.status_code == 200


class TestTheBarOfARow:
    @pytest.mark.parametrize("factory, route, feature", ROWS, ids=IDS)
    def test_the_page_of_a_row_shows_its_lifecycle_bar(self, client, factory, route, feature):
        row = factory()
        client.force_login(UserFactory(is_superuser=True))

        html = client.get(reverse(route, kwargs={"pk": row.pk})).content.decode()

        assert "data-lc-bar" in html
        # The bar sits outside the row's form : a form inside a form is lost.
        assert html.index("data-lc-bar") < html.index('class="card page-form"')
        assert f'action="{_transition_url(row)}"' in html

    @pytest.mark.parametrize("factory, route, feature", ROWS, ids=IDS)
    def test_the_side_panel_says_the_step_and_leads_to_the_bar(self, client, factory, route, feature):
        row = factory()
        url = reverse(route, kwargs={"pk": row.pk})
        client.force_login(UserFactory(is_superuser=True))

        html = client.get(url, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="drawer-form-content").content.decode()

        assert "data-lc-bar" not in html and "stepper__pill-form" not in html
        assert f'<a href="{url}" hx-boost="false">Change the step</a>' in html
        assert str(row.lifecycle_label) in html

    def test_the_bar_offers_an_editor_the_next_step_only(self, client):
        event = f.FearedEventFactory()
        url = reverse("risks:ebios-feared-event-update", kwargs={"pk": event.pk})
        client.force_login(_user_with("risks.ebios_baseline.read", "risks.ebios_baseline.update"))

        html = client.get(url).content.decode()

        assert 'name="target_status" value="pending"' in html
        assert 'name="target_status" value="validated"' not in html

    def test_a_row_being_created_has_no_bar_nor_step(self, client):
        assessment = f.EbiosAssessmentFactory()
        client.force_login(UserFactory(is_superuser=True))
        url = reverse("risks:ebios-risk-source-create", kwargs={"assessment_pk": assessment.pk})

        page = client.get(url).content.decode()
        panel = client.get(url, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="drawer-form-content").content.decode()

        assert "data-lc-bar" not in page
        assert "Change the step" not in panel

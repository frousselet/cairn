# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The *Controls* reverse cards (README §8) on the requirement, risk,
treatment plan, PACS measure (EBIOS RM workshop 5), support asset, objective
and document detail pages, and the finding page's link back to its run
(RG-CTL-16)."""

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Group
from accounts.tests.factories import UserFactory
from assets.tests.factories import SupportAssetFactory
from compliance.constants import FindingSource, FindingType
from compliance.forms import FindingRegisterForm
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from context.tests.factories import ObjectiveFactory, ScopeFactory
from controls.constants import CONTROL_RETIRED, ControlEffectiveness, RunResult
from controls.integrations import linked_controls, linked_controls_for_measures
from controls.models import ControlTest
from controls.tests.factories import ControlFactory, active_test, implemented_control, validated_run
from documents.tests.factories import PolicyFactory
from risks.constants import EbiosWorkshopNumber
from risks.tests.factories import (
    EbiosAssessmentFactory,
    PACSMeasureFactory,
    RiskFactory,
    RiskTreatmentPlanFactory,
)

pytestmark = pytest.mark.django_db


def _get(user, url):
    client = Client()
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    return response


def _reader():
    """A Lecteur : reads every register, controls included (README §4)."""
    user = UserFactory()
    Group.objects.get(name="Lecteur").users.add(user)
    return user


# --- The shared helper -------------------------------------------------------


class TestLinkedControls:
    def test_none_without_the_read_permission(self):
        requirement = RequirementFactory()
        implemented_control().requirements.add(requirement)
        assert linked_controls(requirement, UserFactory()) is None

    def test_any_step_with_retired_last(self):
        requirement = RequirementFactory()
        retired = implemented_control(name="A retired control")
        retired.transition_to(CONTROL_RETIRED, retired.owner, comment="Replaced.")
        proposed = ControlFactory(name="B proposed control")
        live = implemented_control(name="C live control")
        for control in (retired, proposed, live):
            control.requirements.add(requirement)
        controls = linked_controls(requirement, UserFactory(is_superuser=True))
        assert controls[-1].pk == retired.pk
        assert controls[-1].is_retired and not any(c.is_retired for c in controls[:-1])
        assert {c.pk for c in controls} == {retired.pk, proposed.pk, live.pk}

    def test_scope_filtered(self):
        mine, other = ScopeFactory(), ScopeFactory()
        requirement = RequirementFactory()
        visible = implemented_control()
        visible.scopes.set([mine])
        hidden = implemented_control()
        hidden.scopes.set([other])
        for control in (visible, hidden):
            control.requirements.add(requirement)
        reader = _reader()
        from unittest.mock import patch

        with patch.object(type(reader), "get_allowed_scope_ids", return_value={mine.pk}):
            controls = linked_controls(requirement, reader)
        assert [c.pk for c in controls] == [visible.pk]

    def test_stale_effectiveness_is_flagged(self):
        risk = RiskFactory()
        test = active_test()
        validated_run(test=test, result=RunResult.PASS)
        ControlTest.objects.filter(pk=test.pk).update(next_due_date=timezone.localdate() - timedelta(days=2))
        test.control.risks.add(risk)
        (control,) = linked_controls(risk, UserFactory(is_superuser=True))
        assert control.effectiveness == ControlEffectiveness.EFFECTIVE
        assert control.effectiveness_stale is True

    def test_measures_carry_the_references_they_are_linked_through(self):
        m1, m2 = PACSMeasureFactory(), PACSMeasureFactory()
        control = implemented_control()
        control.pacs_measures.add(m1, m2)
        (row,) = linked_controls_for_measures([m1, m2], UserFactory(is_superuser=True))
        assert row.linked_via == sorted([m1.reference, m2.reference])


# --- The detail pages ----------------------------------------------------------


class TestReverseCards:
    def _assert_card(self, body, control):
        assert 'id="linked-controls"' in body
        assert control.reference in body
        assert reverse("controls:control-detail", args=[control.pk]) in body

    def test_requirement(self):
        framework = FrameworkFactory()
        requirement = RequirementFactory(framework=framework)
        control = implemented_control(name="Requirement control")
        control.requirements.add(requirement)
        body = _get(UserFactory(is_superuser=True), reverse("compliance:requirement-detail", args=[requirement.pk])).content.decode()
        self._assert_card(body, control)

    def test_risk_shows_effectiveness(self):
        risk = RiskFactory()
        run = validated_run(result=RunResult.FAIL)
        control = run.test.control
        control.risks.add(risk)
        body = _get(UserFactory(is_superuser=True), reverse("risks:risk-detail", args=[risk.pk])).content.decode()
        self._assert_card(body, control)
        assert str(ControlEffectiveness.NOT_EFFECTIVE.label) in body

    def test_treatment_plan(self):
        plan = RiskTreatmentPlanFactory()
        control = implemented_control()
        control.treatment_plans.add(plan)
        body = _get(UserFactory(is_superuser=True), reverse("risks:treatment-plan-detail", args=[plan.pk])).content.decode()
        self._assert_card(body, control)

    def test_support_asset(self):
        asset = SupportAssetFactory()
        control = implemented_control()
        control.support_assets.add(asset)
        body = _get(UserFactory(is_superuser=True), reverse("assets:support-asset-detail", args=[asset.pk])).content.decode()
        self._assert_card(body, control)

    def test_objective(self):
        objective = ObjectiveFactory()
        control = implemented_control()
        control.objectives.add(objective)
        body = _get(UserFactory(is_superuser=True), reverse("context:objective-detail", args=[objective.pk])).content.decode()
        self._assert_card(body, control)

    def test_policy(self):
        policy = PolicyFactory()
        control = implemented_control()
        control.policies.add(policy)
        body = _get(UserFactory(is_superuser=True), reverse("documents:policy-detail", args=[policy.pk])).content.decode()
        self._assert_card(body, control)

    def test_pacs_measures_on_workshop_5(self):
        assessment = EbiosAssessmentFactory()
        measure = PACSMeasureFactory(summary=assessment.ebios_summary)
        control = implemented_control()
        control.pacs_measures.add(measure)
        workshop = assessment.ebios_workshops.get(workshop_number=EbiosWorkshopNumber.W5)
        url = reverse("risks:ebios-workshop-detail", kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk})
        body = _get(UserFactory(is_superuser=True), url).content.decode()
        self._assert_card(body, control)
        assert measure.reference in body

    def test_empty_state(self):
        objective = ObjectiveFactory()
        body = _get(UserFactory(is_superuser=True), reverse("context:objective-detail", args=[objective.pk])).content.decode()
        assert 'id="linked-controls"' in body
        assert "No control linked." in body

    def test_retired_control_is_flagged_and_shows_no_effectiveness(self):
        requirement = RequirementFactory()
        run = validated_run(result=RunResult.PASS)
        control = run.test.control
        control.transition_to(CONTROL_RETIRED, control.owner, comment="Replaced.")
        control.requirements.add(requirement)
        body = _get(UserFactory(is_superuser=True), reverse("compliance:requirement-detail", args=[requirement.pk])).content.decode()
        self._assert_card(body, control)
        control.refresh_from_db()
        assert str(control.lifecycle_label) in body

    def test_hidden_without_the_read_permission(self):
        """A reader of objectives who may not read controls sees no card."""
        objective = ObjectiveFactory()
        implemented_control().objectives.add(objective)
        user = UserFactory()
        from accounts.models import Permission

        group = Group.objects.create(name="Objectives only")
        group.permissions.set(Permission.objects.filter(codename="context.objective.read"))
        group.users.add(user)
        body = _get(user, reverse("context:objective-detail", args=[objective.pk])).content.decode()
        assert 'id="linked-controls"' not in body


# --- The finding page ----------------------------------------------------------


class TestFindingFromRun:
    def _finding(self):
        run = validated_run(result=RunResult.FAIL, observations="Two logins without a second factor.")
        return run, run.raise_finding(UserFactory(), FindingType.MINOR_NON_CONFORMITY)

    def test_page_links_back_to_the_run(self):
        run, finding = self._finding()
        body = _get(UserFactory(is_superuser=True), reverse("compliance:finding-detail", args=[finding.pk])).content.decode()
        assert reverse("controls:controltestrun-detail", args=[run.pk]) in body
        assert run.reference in body
        assert str(FindingSource.CONTROL_TEST.label) in body

    def test_register_filter_accepts_the_source(self):
        _run, finding = self._finding()
        client = Client()
        client.force_login(UserFactory(is_superuser=True))
        response = client.get(reverse("compliance:finding-list"), {"source": FindingSource.CONTROL_TEST})
        assert response.status_code == 200
        assert finding.reference in response.content.decode()

    def test_form_never_offers_the_source_by_hand_and_keeps_it_once_raised(self):
        values = [c[0] for c in FindingRegisterForm().fields["source"].choices]
        assert FindingSource.CONTROL_TEST not in values
        _run, finding = self._finding()
        values = [c[0] for c in FindingRegisterForm(instance=finding).fields["source"].choices]
        assert values == [FindingSource.CONTROL_TEST]

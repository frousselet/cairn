"""Tests for the risk-process specific workflows (issue #105, phase 6e)."""

import pytest

from accounts.tests.factories import UserFactory
from core.lifecycle import IllegalTransitionError, resolve_lifecycle
from core.lifecycle import (
    LifecycleProtectedError,
    deletable_states,
    linkable_states,
    reportable_states,
)
from risks.constants import (
    AcceptanceStatus,
    RiskStatus,
    TreatmentPlanStatus,
    VulnerabilityStatus,
)
from risks.models import Risk, RiskAcceptance, RiskTreatmentPlan, Vulnerability
from risks.tests.factories import RiskFactory

pytestmark = pytest.mark.django_db


class TestRiskWorkflow:
    def test_resolution_and_shape(self):
        lifecycle = resolve_lifecycle(Risk)
        assert lifecycle.name == "risk"
        assert lifecycle.initial_step.code == "identified"
        assert {s.code for s in lifecycle.steps} == {s.value for s in RiskStatus}

    def test_governance_flags(self):
        # An identified risk is a working entry: not in the register yet.
        assert reportable_states(Risk) == {
            s.value for s in RiskStatus
        } - {"identified"}
        assert linkable_states(Risk) == {
            s.value for s in RiskStatus
        } - {"identified", "closed"}
        assert deletable_states(Risk) == {"identified"}

    def test_process_path(self):
        user = UserFactory()
        risk = RiskFactory()
        for target in (
            RiskStatus.ANALYZED, RiskStatus.EVALUATED,
            RiskStatus.TREATMENT_PLANNED, RiskStatus.TREATMENT_IN_PROGRESS,
            RiskStatus.TREATED, RiskStatus.MONITORING,
        ):
            risk.transition_to(target, user)
        # The monitoring loop can re-enter analysis.
        risk.transition_to(RiskStatus.ANALYZED, user)
        risk.refresh_from_db()
        assert risk.status == "analyzed"

    def test_closed_is_terminal(self):
        user = UserFactory()
        risk = RiskFactory(status=RiskStatus.MONITORING)
        risk.transition_to(RiskStatus.CLOSED, user)
        with pytest.raises(IllegalTransitionError):
            risk.transition_to(RiskStatus.ANALYZED, user)
        with pytest.raises(LifecycleProtectedError):
            risk.delete()

    def test_register_excludes_identified(self):
        from core.lifecycle import reportable

        RiskFactory()  # identified
        live = RiskFactory(status=RiskStatus.EVALUATED)
        assert set(reportable(Risk.objects.all())) == {live}


class TestTreatmentPlanWorkflow:
    def _plan(self, **kwargs):
        return RiskTreatmentPlan.objects.create(
            risk=RiskFactory(), name="Mitigate", treatment_type="mitigate", **kwargs
        )

    def test_resolution_and_flags(self):
        lifecycle = resolve_lifecycle(RiskTreatmentPlan)
        assert lifecycle.name == "risk_treatment_plan"
        assert reportable_states(RiskTreatmentPlan) == {
            "planned", "in_progress", "overdue", "completed",
        }
        assert deletable_states(RiskTreatmentPlan) == {"planned"}

    def test_overdue_auto_flip_syncs_workflow_state(self):
        from datetime import timedelta

        from django.utils import timezone

        plan = self._plan(target_date=timezone.localdate() - timedelta(days=1))
        plan.refresh_from_db()
        assert plan.status == "overdue"
        assert plan.workflow_state == "overdue"

    def test_overdue_back_to_in_progress(self):
        user = UserFactory()
        plan = self._plan(status=TreatmentPlanStatus.OVERDUE)
        plan.transition_to(TreatmentPlanStatus.IN_PROGRESS, user)
        plan.refresh_from_db()
        assert plan.status == "in_progress"

    def test_completed_is_terminal(self):
        user = UserFactory()
        plan = self._plan(status=TreatmentPlanStatus.IN_PROGRESS)
        plan.transition_to(TreatmentPlanStatus.COMPLETED, user)
        with pytest.raises(IllegalTransitionError):
            plan.transition_to(TreatmentPlanStatus.IN_PROGRESS, user)


class TestAcceptanceWorkflow:
    def _acceptance(self, **kwargs):
        return RiskAcceptance.objects.create(
            risk=RiskFactory(), justification="Residual risk acceptable", **kwargs
        )

    def test_resolution_and_flags(self):
        lifecycle = resolve_lifecycle(RiskAcceptance)
        assert lifecycle.name == "risk_acceptance"
        # Every acceptance state is audit-relevant and stays reportable.
        assert reportable_states(RiskAcceptance) == {
            s.value for s in AcceptanceStatus
        }
        assert deletable_states(RiskAcceptance) == {"active"}

    def test_renewal_cycle(self):
        user = UserFactory()
        acceptance = self._acceptance()
        acceptance.transition_to(AcceptanceStatus.EXPIRED, user)
        acceptance.transition_to(AcceptanceStatus.RENEWED, user)
        acceptance.refresh_from_db()
        assert acceptance.status == "renewed"

    def test_revoked_is_terminal(self):
        user = UserFactory()
        acceptance = self._acceptance()
        acceptance.transition_to(AcceptanceStatus.REVOKED, user)
        with pytest.raises(IllegalTransitionError):
            acceptance.transition_to(AcceptanceStatus.RENEWED, user)
        with pytest.raises(LifecycleProtectedError):
            acceptance.delete()


class TestVulnerabilityWorkflow:
    def _vulnerability(self, **kwargs):
        return Vulnerability.objects.create(
            name="Unpatched server", description="CVE pending", **kwargs
        )

    def test_resolution_and_flags(self):
        lifecycle = resolve_lifecycle(Vulnerability)
        assert lifecycle.name == "vulnerability"
        assert reportable_states(Vulnerability) == {
            s.value for s in VulnerabilityStatus
        }
        assert deletable_states(Vulnerability) == {"identified"}

    def test_false_positive_direct_close(self):
        user = UserFactory()
        vulnerability = self._vulnerability()
        vulnerability.transition_to(VulnerabilityStatus.CLOSED, user)
        vulnerability.refresh_from_db()
        assert vulnerability.status == "closed"

    def test_mitigation_path(self):
        user = UserFactory()
        vulnerability = self._vulnerability()
        vulnerability.transition_to(VulnerabilityStatus.CONFIRMED, user)
        vulnerability.transition_to(VulnerabilityStatus.MITIGATED, user)
        vulnerability.transition_to(VulnerabilityStatus.CLOSED, user)
        with pytest.raises(IllegalTransitionError):
            vulnerability.transition_to(VulnerabilityStatus.CONFIRMED, user)

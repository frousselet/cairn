"""Risk-driven applicability (Framework.applicability_managed_by_risks).

When a framework manages applicability by risks, a requirement is applicable iff
at least one of its linked risks is in a reportable (active) lifecycle state. For
the risk workflow the only non-reportable state is the initial ``identified``
one, so an analyzed/evaluated/... risk counts while a freshly identified one does
not.
"""

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from compliance.applicability import (
    APPLICABLE_AUTO_JUSTIFICATION,
    NOT_APPLICABLE_AUTO_JUSTIFICATION,
)
from compliance.constants import ComplianceStatus
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from risks.constants import RiskStatus
from risks.tests.factories import RiskFactory

pytestmark = pytest.mark.django_db


def managed_framework(**kwargs):
    return FrameworkFactory(applicability_managed_by_risks=True, **kwargs)


def reportable_risk(**kwargs):
    """A risk in an active (reportable) state, so it drives applicability."""
    return RiskFactory(status=RiskStatus.ANALYZED, **kwargs)


def identified_risk(**kwargs):
    """A freshly identified risk: linked but not yet reportable."""
    return RiskFactory(status=RiskStatus.IDENTIFIED, **kwargs)


class TestOptionOff:
    """Default behaviour is unchanged when the option is off."""

    def test_manual_applicability_is_preserved(self):
        fw = FrameworkFactory()  # not managed
        req = RequirementFactory(framework=fw, is_applicable=True)
        # Linking a risk must not auto-manage applicability.
        reportable_risk().linked_requirements.add(req)
        req.refresh_from_db()
        assert req.is_applicable is True

    def test_manual_not_applicable_is_preserved(self):
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, is_applicable=False)
        req.refresh_from_db()
        assert req.is_applicable is False


class TestManagedCreation:
    def test_requirement_without_risk_is_not_applicable(self):
        fw = managed_framework()
        req = RequirementFactory(framework=fw, is_applicable=True)
        req.refresh_from_db()
        assert req.is_applicable is False
        assert req.applicability_justification == str(NOT_APPLICABLE_AUTO_JUSTIFICATION)


class TestLinking:
    def test_link_reportable_risk_makes_applicable(self):
        req = RequirementFactory(framework=managed_framework())
        reportable_risk().linked_requirements.add(req)
        req.refresh_from_db()
        assert req.is_applicable is True
        assert req.applicability_justification == str(APPLICABLE_AUTO_JUSTIFICATION)

    def test_link_identified_risk_stays_not_applicable(self):
        req = RequirementFactory(framework=managed_framework())
        identified_risk().linked_requirements.add(req)
        req.refresh_from_db()
        assert req.is_applicable is False

    def test_reverse_link_from_requirement_side(self):
        req = RequirementFactory(framework=managed_framework())
        risk = reportable_risk()
        req.linked_risks.add(risk)  # reverse direction of the M2M
        req.refresh_from_db()
        assert req.is_applicable is True

    def test_unlink_last_risk_makes_not_applicable(self):
        req = RequirementFactory(framework=managed_framework())
        risk = reportable_risk()
        risk.linked_requirements.add(req)
        req.refresh_from_db()
        assert req.is_applicable is True
        risk.linked_requirements.remove(req)
        req.refresh_from_db()
        assert req.is_applicable is False

    def test_clear_makes_not_applicable(self):
        req = RequirementFactory(framework=managed_framework())
        risk = reportable_risk()
        risk.linked_requirements.add(req)
        req.refresh_from_db()
        assert req.is_applicable is True
        risk.linked_requirements.clear()
        req.refresh_from_db()
        assert req.is_applicable is False

    def test_at_least_one_reportable_risk_is_enough(self):
        req = RequirementFactory(framework=managed_framework())
        weak = identified_risk()
        strong = reportable_risk()
        req.linked_risks.add(weak, strong)
        req.refresh_from_db()
        assert req.is_applicable is True
        # Removing the only reportable one flips it back.
        req.linked_risks.remove(strong)
        req.refresh_from_db()
        assert req.is_applicable is False


class TestRiskLifecycle:
    def test_risk_becoming_reportable_makes_applicable(self):
        req = RequirementFactory(framework=managed_framework())
        risk = identified_risk()
        risk.linked_requirements.add(req)
        req.refresh_from_db()
        assert req.is_applicable is False
        # Analyse the risk: it becomes reportable -> requirement applicable.
        risk.status = RiskStatus.ANALYZED
        risk.save()
        req.refresh_from_db()
        assert req.is_applicable is True

    def test_deleting_last_risk_makes_not_applicable(self):
        req = RequirementFactory(framework=managed_framework())
        risk = reportable_risk()
        risk.linked_requirements.add(req)
        req.refresh_from_db()
        assert req.is_applicable is True
        # A reportable risk is not directly deletable (RG-LC-05); it is removed
        # by cascade / bulk delete, which bypasses Model.delete() but still fires
        # pre_delete / post_delete (m2m_changed does not fire on deletion).
        type(risk).objects.filter(pk=risk.pk).delete()
        req.refresh_from_db()
        assert req.is_applicable is False


class TestToggle:
    def test_toggling_on_recomputes_all_requirements(self):
        fw = FrameworkFactory()  # not managed yet
        with_reportable = RequirementFactory(framework=fw, is_applicable=True)
        without_risk = RequirementFactory(framework=fw, is_applicable=True)
        with_identified = RequirementFactory(framework=fw, is_applicable=True)
        reportable_risk().linked_requirements.add(with_reportable)
        identified_risk().linked_requirements.add(with_identified)
        # Nothing auto-managed while off.
        without_risk.refresh_from_db()
        assert without_risk.is_applicable is True

        fw.applicability_managed_by_risks = True
        fw.save()

        with_reportable.refresh_from_db()
        without_risk.refresh_from_db()
        with_identified.refresh_from_db()
        assert with_reportable.is_applicable is True
        assert without_risk.is_applicable is False
        assert with_identified.is_applicable is False

    def test_toggling_off_keeps_values_and_allows_manual_edit(self):
        fw = managed_framework()
        req = RequirementFactory(framework=fw)
        req.refresh_from_db()
        assert req.is_applicable is False  # no risk

        fw.applicability_managed_by_risks = False
        fw.save()
        # Manual control returns: a value set by hand now sticks.
        req.is_applicable = True
        req.save()
        req.refresh_from_db()
        assert req.is_applicable is True


class TestComplianceRecalculation:
    def test_framework_level_refreshes_when_applicability_flips(self):
        fw = managed_framework()
        req = RequirementFactory(
            framework=fw,
            compliance_status=ComplianceStatus.COMPLIANT,
            compliance_level=100,
        )
        # No risk -> not applicable -> excluded from the score.
        fw.refresh_from_db()
        assert fw.compliance_level == 0

        reportable_risk().linked_requirements.add(req)
        fw.refresh_from_db()
        # Now applicable and compliant -> the recalculation chain lifts the level.
        assert fw.compliance_level == 100


class TestApiCannotOverride:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_patch_is_applicable_is_ignored_for_managed_framework(self):
        fw = managed_framework()
        req = RequirementFactory(framework=fw)  # not applicable (no risk)
        response = self.client.patch(
            f"/api/v1/compliance/requirements/{req.pk}/",
            {"is_applicable": True, "applicability_justification": "forced"},
            format="json",
        )
        assert response.status_code in (200, 202)
        req.refresh_from_db()
        # The client value is ignored; the rule (no risk) wins.
        assert req.is_applicable is False

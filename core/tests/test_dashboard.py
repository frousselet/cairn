"""Tests for the GeneralDashboardView context computation and scope filtering."""

import json
from datetime import date, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import UserFactory
from assets.tests.factories import (
    DependencyFactory,
    EssentialAssetFactory,
    SupplierDependencyFactory,
    SupplierFactory,
    SupportAssetFactory,
)
from compliance.tests.factories import (
    ComplianceActionPlanFactory,
    ComplianceAssessmentFactory,
    FrameworkFactory,
    RequirementFactory,
)
from context.constants import (
    IndicatorFormat,
    IndicatorStatus,
    IndicatorType,
    CollectionMethod,
    MeasurementFrequency,
)
from context.models import Activity, Indicator, Issue, Objective, Role, Scope, Site, Stakeholder, SwotAnalysis
from context.models.indicator import IndicatorMeasurement
from context.tests.factories import (
    IssueFactory,
    ObjectiveFactory,
    ScopeFactory,
    SwotAnalysisFactory,
)
from risks.tests.factories import RiskAssessmentFactory, RiskFactory

pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────


def _superuser_client():
    user = UserFactory(is_superuser=True, is_staff=True)
    client = Client()
    client.force_login(user)
    return client, user


def _regular_client():
    user = UserFactory()
    client = Client()
    client.force_login(user)
    return client, user


def _make_indicator(**kwargs):
    defaults = {
        "name": "Dashboard Indicator",
        "indicator_type": IndicatorType.ORGANIZATIONAL,
        "collection_method": CollectionMethod.MANUAL,
        "format": IndicatorFormat.NUMBER,
        "review_frequency": MeasurementFrequency.MONTHLY,
        "first_review_date": timezone.now().date() + timedelta(days=30),
        "status": IndicatorStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Indicator.objects.create(**defaults)


# ── Dashboard with populated data ────────────────────────────


class TestDashboardWithPopulatedData:
    """Test that the dashboard correctly counts and displays data from all modules."""

    def test_scope_count(self):
        ScopeFactory()
        ScopeFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["scope_count"] == 2

    def test_active_scopes_returned(self):
        ScopeFactory(is_approved=True)
        ScopeFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert len(resp.context["active_scopes"]) == 1

    def test_issue_count(self):
        scope = ScopeFactory()
        IssueFactory(scopes=[scope])
        IssueFactory(scopes=[scope])
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["issue_count"] == 2

    def test_stakeholder_count(self):
        Stakeholder.objects.create(
            name="Test Stakeholder",
            category="customers",
            influence_level="high",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["stakeholder_count"] == 1

    def test_objective_count(self):
        ObjectiveFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["objective_count"] == 1

    def test_active_objectives_returned(self):
        ObjectiveFactory(status="active")
        ObjectiveFactory(status="draft")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert len(resp.context["active_objectives"]) == 1

    def test_role_count(self):
        Role.objects.create(name="CISO", type="governance")
        Role.objects.create(name="DPO", type="governance")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["role_count"] == 2

    def test_site_count(self):
        Site.objects.create(name="HQ", description="Headquarters")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["site_count"] == 1

    def test_mandatory_roles_no_user_alert(self):
        Role.objects.create(name="DPO", type="governance", is_mandatory=True)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["mandatory_roles_no_user"] == 1

    def test_mandatory_roles_with_user_no_alert(self):
        role = Role.objects.create(name="DPO", type="governance", is_mandatory=True)
        role.assigned_users.add(UserFactory())
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["mandatory_roles_no_user"] == 0

    def test_swot_count(self):
        SwotAnalysisFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["swot_count"] == 1

    def test_activity_count(self):
        user = UserFactory()
        Activity.objects.create(
            name="Activity 1", type="core_business",
            criticality="high", owner=user,
        )
        client, admin = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["activity_count"] == 1

    def test_critical_activities_no_owner_count(self):
        """Critical activities with no owner should be counted for the alert."""
        user = UserFactory()
        # Critical with owner - should not count
        Activity.objects.create(
            name="A1", type="core_business",
            criticality="critical", owner=user,
        )
        # Critical without owner - the model requires owner (PROTECT), so this
        # test checks the dashboard query filter. We need at least one critical
        # activity WITH owner to verify the count is correct.
        client, admin = _superuser_client()
        resp = client.get(reverse("home"))
        # Since Activity.owner is required (PROTECT), we test the query logic
        # indirectly: a critical activity with an owner should NOT trigger.
        assert resp.context["critical_activities_no_owner"] == 0


class TestDashboardAssets:
    def test_essential_asset_count(self):
        EssentialAssetFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["essential_count"] == 1

    def test_support_asset_count(self):
        SupportAssetFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["support_count"] == 1

    def test_dependency_count(self):
        DependencyFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["dependency_count"] == 1

    def test_eol_count(self):
        SupportAssetFactory(
            end_of_life_date=date.today() - timedelta(days=30),
            status="active",
        )
        # Not past EOL
        SupportAssetFactory(
            end_of_life_date=date.today() + timedelta(days=30),
            status="active",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["eol_count"] == 1

    def test_personal_data_count(self):
        EssentialAssetFactory(personal_data=True)
        EssentialAssetFactory(personal_data=False)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["personal_data_count"] == 1

    def test_supplier_count(self):
        SupplierFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["supplier_count"] == 1

    def test_expired_contract_count(self):
        SupplierFactory(
            contract_end_date=date.today() - timedelta(days=10),
            status="active",
        )
        SupplierFactory(
            contract_end_date=date.today() + timedelta(days=10),
            status="active",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["expired_contract_count"] == 1

    def test_supplier_dep_count(self):
        SupplierDependencyFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["supplier_dep_count"] == 1

    def test_supplier_spof_count(self):
        SupplierDependencyFactory(is_single_point_of_failure=True)
        SupplierDependencyFactory(is_single_point_of_failure=False)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["supplier_spof_count"] == 1


class TestDashboardRisks:
    def test_risk_assessment_count(self):
        RiskAssessmentFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["risk_assessment_count"] == 1

    def test_risk_count(self):
        RiskFactory()
        RiskFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["risk_count"] == 2

    def test_critical_risk_count(self):
        RiskFactory(priority="critical")
        RiskFactory(priority="high")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["critical_risk_count"] == 1


class TestDashboardCompliance:
    def test_framework_count(self):
        FrameworkFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["framework_count"] == 1

    def test_assessment_count(self):
        ComplianceAssessmentFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["assessment_count"] == 1

    def test_action_plan_count(self):
        ComplianceActionPlanFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["action_plan_count"] == 1

    def test_overdue_plan_count(self):
        ComplianceActionPlanFactory(
            target_date=date.today() - timedelta(days=10),
            status="in_progress",
        )
        # Not overdue
        ComplianceActionPlanFactory(
            target_date=date.today() + timedelta(days=30),
            status="in_progress",
        )
        # Closed, past target - should not count
        ComplianceActionPlanFactory(
            target_date=date.today() - timedelta(days=10),
            status="closed",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["overdue_plan_count"] == 1

    def test_requirement_count(self):
        fw = FrameworkFactory()
        RequirementFactory(framework=fw)
        RequirementFactory(framework=fw)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["requirement_count"] == 2

    def test_tracked_requirement_count_follows_rate_basis(self):
        # Validated active framework: its applicable requirements count.
        tracked = FrameworkFactory(status="active", is_approved=True)
        RequirementFactory(framework=tracked)
        RequirementFactory(framework=tracked, is_applicable=False)
        # Draft framework: excluded from the average, so from the caption too.
        draft = FrameworkFactory()
        RequirementFactory(framework=draft)
        RequirementFactory(framework=draft)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["tracked_requirement_count"] == 1
        # The inventory tile keeps the full count.
        assert resp.context["requirement_count"] == 4

    def test_framework_bar_includes_not_applicable_segment(self):
        # A framework with applicable + non-applicable requirements (no
        # assessments): the applicable segments rescale to the total and the rest
        # becomes the not-applicable slice, so the bar sums to 100%.
        fw = FrameworkFactory(status="active", is_approved=True)
        RequirementFactory.create_batch(3, framework=fw)      # applicable, not assessed
        RequirementFactory(framework=fw, is_applicable=False)  # not applicable
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        bar = next(f for f in resp.context["active_frameworks"] if f.pk == fw.pk)
        assert bar.seg_unassessed == 75   # 3 of 4 applicable, not assessed
        assert bar.seg_na == 25           # 1 of 4 not applicable
        assert bar.seg_conform == 0 and bar.seg_nonconform == 0
        assert bar.seg_conform + bar.seg_nonconform + bar.seg_unassessed + bar.seg_na == 100
        # Headline compliance is still of applicable requirements (0 here).
        assert bar.computed_compliance == 0

    def test_non_compliant_count(self):
        fw = FrameworkFactory()
        RequirementFactory(
            framework=fw,
            compliance_status="major_non_conformity",
        )
        RequirementFactory(
            framework=fw,
            compliance_status="minor_non_conformity",
        )
        RequirementFactory(
            framework=fw,
            compliance_status="compliant",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["non_compliant_count"] == 2


# ── Today's actions ──────────────────────────────────────────


def _action_labels(resp):
    return [
        str(item["label"]).lower()
        for group in resp.context["today_action_groups"]
        for item in group["items"]
    ]


class TestDashboardTodayActions:
    def test_no_actions_when_no_issues(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["today_action_groups"] == []
        assert resp.context["today_action_count"] == 0

    def test_mandatory_role_action(self):
        Role.objects.create(name="DPO", type="governance", is_mandatory=True)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        labels = _action_labels(resp)
        assert len(labels) >= 1
        assert any("mandatory" in label for label in labels)

    def test_eol_action(self):
        SupportAssetFactory(
            end_of_life_date=date.today() - timedelta(days=5),
            status="active",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert any("end of life" in label for label in _action_labels(resp))

    def test_non_compliant_action(self):
        fw = FrameworkFactory()
        RequirementFactory(framework=fw, compliance_status="major_non_conformity")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert any("compliance" in label for label in _action_labels(resp))

    def test_overdue_plan_action(self):
        ComplianceActionPlanFactory(
            target_date=date.today() - timedelta(days=5),
            status="in_progress",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert any("overdue" in label for label in _action_labels(resp))

    def test_critical_risk_action(self):
        RiskFactory(priority="critical")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert any("critical" in label for label in _action_labels(resp))
        priority_group = resp.context["today_action_groups"][0]
        assert priority_group["key"] == "priority"
        assert priority_group["items"][0]["url"]

    def test_expired_contract_action(self):
        SupplierFactory(
            contract_end_date=date.today() - timedelta(days=5),
            status="active",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert any("expired" in label for label in _action_labels(resp))

    def test_action_count_sums_counts(self):
        RiskFactory(priority="critical")
        RiskFactory(priority="critical")
        SupplierFactory(
            contract_end_date=date.today() - timedelta(days=5),
            status="active",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["today_action_count"] == 3


# ── _filter_scoped helper ────────────────────────────────────


class TestFilterScoped:
    def test_superuser_sees_all_scoped_objects(self):
        """Superusers are not filtered by scope."""
        scope1 = ScopeFactory()
        scope2 = ScopeFactory()
        IssueFactory(scopes=[scope1])
        IssueFactory(scopes=[scope2])
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["issue_count"] == 2

    def test_regular_user_sees_all_when_no_scope_restriction(self):
        """Regular users without scope restrictions see all data."""
        IssueFactory()
        client, user = _regular_client()
        resp = client.get(reverse("home"))
        # Non-superuser with no group scope restrictions should still see data
        assert resp.status_code == 200

    def test_scope_count_matches_filter(self):
        """Superuser sees all scopes."""
        ScopeFactory(is_approved=True)
        ScopeFactory()
        ScopeFactory(workflow_state="archived")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["scope_count"] == 3


# ── Dashboard indicator slots ────────────────────────────────


class TestDashboardIndicatorSlots:
    """The shared indicator-slot builder (powers the per-indicator widget and the
    legacy pinned strip). Tested directly via ``get_dashboard_indicator_slots``."""

    def _slots(self, user):
        from context.views import get_dashboard_indicator_slots

        return get_dashboard_indicator_slots(user)

    def test_empty_slots_when_no_pinned_indicators(self):
        _client, user = _superuser_client()
        slots = self._slots(user)
        assert len(slots) == 10
        assert all(s is None for s in slots)

    def test_pinned_indicator_shown_in_slots(self):
        ind = _make_indicator(name="Coverage", current_value="85")
        _client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators"])
        filled = [s for s in self._slots(user) if s is not None]
        assert len(filled) == 1
        assert filled[0]["indicator"].pk == ind.pk

    def test_pinned_indicator_with_measurements_has_trend(self):
        ind = _make_indicator(name="Trend Test", current_value="100")
        IndicatorMeasurement.objects.create(indicator=ind, value="80")
        IndicatorMeasurement.objects.create(indicator=ind, value="100")
        _client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators"])
        filled = [s for s in self._slots(user) if s is not None]
        assert len(filled) == 1
        assert filled[0]["trend"] is not None

    def test_pinned_boolean_indicator_trend(self):
        ind = _make_indicator(
            name="Boolean Test",
            format=IndicatorFormat.BOOLEAN,
            current_value="true",
        )
        IndicatorMeasurement.objects.create(indicator=ind, value="false")
        IndicatorMeasurement.objects.create(indicator=ind, value="true")
        _client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators"])
        filled = [s for s in self._slots(user) if s is not None]
        assert len(filled) == 1
        assert filled[0]["trend"] == "changed"

    def test_pinned_boolean_stable_trend(self):
        ind = _make_indicator(
            name="Bool Stable",
            format=IndicatorFormat.BOOLEAN,
            current_value="true",
        )
        IndicatorMeasurement.objects.create(indicator=ind, value="true")
        IndicatorMeasurement.objects.create(indicator=ind, value="true")
        _client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators"])
        filled = [s for s in self._slots(user) if s is not None]
        assert filled[0]["trend"] == "stable"

    def test_pinned_indicator_with_chart_enabled(self):
        ind = _make_indicator(name="Chart Test", current_value="50")
        for i in range(5):
            IndicatorMeasurement.objects.create(indicator=ind, value=str(10 * (i + 1)))
        _client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.dashboard_indicator_charts = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators", "dashboard_indicator_charts"])
        filled = [s for s in self._slots(user) if s is not None]
        assert len(filled) == 1
        assert filled[0]["show_chart"] is True
        assert len(filled[0]["sparkline_data"]) >= 2

    def test_slots_padded_to_ten(self):
        ind1 = _make_indicator(name="Ind 1")
        ind2 = _make_indicator(name="Ind 2")
        _client, user = _superuser_client()
        user.dashboard_indicators = [str(ind1.pk), str(ind2.pk)]
        user.save(update_fields=["dashboard_indicators"])
        slots = self._slots(user)
        assert len(slots) == 10
        filled = [s for s in slots if s is not None]
        assert len(filled) == 2

    def test_available_indicators_in_context(self):
        _make_indicator(name="Active One", status=IndicatorStatus.ACTIVE)
        _make_indicator(name="Inactive One", status=IndicatorStatus.INACTIVE)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        available = resp.context["available_indicators"]
        names = [ind.name for ind in available]
        assert "Active One" in names
        assert "Inactive One" not in names


# ── Overall compliance calculation ───────────────────────────


class TestDashboardOverallCompliance:
    def test_zero_when_no_active_frameworks(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["overall_compliance"] == 0

    def test_frameworks_with_no_requirements(self):
        """A framework with no requirements should show 0% compliance."""
        FrameworkFactory(status="active", is_approved=True)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        active_fws = resp.context["active_frameworks"]
        assert len(active_fws) == 1
        assert active_fws[0].computed_compliance == 0


# ── Risk matrices ────────────────────────────────────────────


class TestDashboardRiskMatrices:
    def test_default_matrix_without_criteria(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["matrix_current"] is not None
        assert "rows" in resp.context["matrix_current"]

    def test_default_matrix_has_5_rows(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert len(resp.context["matrix_current"]["rows"]) == 5

    def test_residual_matrix_present(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["matrix_residual"] is not None
        assert "rows" in resp.context["matrix_residual"]

    def test_matrix_with_risks(self):
        RiskFactory(
            current_likelihood=3,
            current_impact=4,
            residual_likelihood=2,
            residual_impact=2,
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["matrix_current"] is not None
        assert resp.context["matrix_residual"] is not None

    def test_matrices_are_two_widgets_without_configure(self):
        # The matrices are split into two separate widgets (current + residual),
        # each rendering its own heatmap, with no in-widget Configure button.
        client, user = _superuser_client()
        content = client.get(reverse("home")).content.decode()
        assert 'data-widget-id="risk_matrix_current"' in content
        assert 'data-widget-id="risk_matrix_residual"' in content
        # Each heatmap is wrapped so it scales to fit its tile (no overflow).
        assert "data-fit-scale" in content
        # The old combined widget and its Configure scales button are gone.
        assert 'data-widget-id="risk_matrices"' not in content
        assert "Configure scales" not in content


class TestOngoingAuditsWidget:
    """The conditional ongoing-audits widget (visible only while an audit runs)."""

    @staticmethod
    def _section(content, wid):
        idx = content.index('data-widget-id="%s"' % wid)
        return content[content.rfind("<section", 0, idx):idx]

    def test_shows_audit_whose_window_covers_today(self):
        from compliance.constants import AssessmentStatus
        from compliance.tests.factories import ComplianceAssessmentFactory

        today = date.today()
        audit = ComplianceAssessmentFactory(
            name="ISO 27001 surveillance",
            status=AssessmentStatus.IN_PROGRESS,
            assessment_start_date=today - timedelta(days=2),
            assessment_end_date=today + timedelta(days=3),
        )
        audit.scopes.add(ScopeFactory(name="HQ Datacenter"))
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        ongoing = resp.context["ongoing_audits"]
        assert len(ongoing) == 1
        assert ongoing[0]["audit"].name == "ISO 27001 surveillance"
        assert ongoing[0]["days_left"] == 3
        assert ongoing[0]["time_progress"] == 40  # 2 of 5 days elapsed
        content = resp.content.decode()
        # Rendered and NOT flagged empty (so it shows in view mode).
        assert 'data-widget-id="ongoing_audits"' in content
        assert "dash-widget--empty" not in self._section(content, "ongoing_audits")
        # The concerned scope is shown.
        assert "HQ Datacenter" in content

    def test_hidden_when_no_ongoing_audit(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["ongoing_audits"] == []
        content = resp.content.decode()
        # Still in the DOM, but flagged empty -> hidden in view mode.
        assert "dash-widget--empty" in self._section(content, "ongoing_audits")

    def test_excludes_draft_cancelled_and_out_of_window(self):
        from compliance.constants import AssessmentStatus
        from compliance.tests.factories import ComplianceAssessmentFactory

        today = date.today()
        common = dict(
            assessment_start_date=today - timedelta(days=1),
            assessment_end_date=today + timedelta(days=1),
        )
        # Draft "audit project" and cancelled audit, both in the window: excluded.
        ComplianceAssessmentFactory(status=AssessmentStatus.DRAFT, **common)
        ComplianceAssessmentFactory(status=AssessmentStatus.CANCELLED, **common)
        # In progress but the window is entirely in the past / future: excluded.
        ComplianceAssessmentFactory(
            status=AssessmentStatus.IN_PROGRESS,
            assessment_start_date=today - timedelta(days=10),
            assessment_end_date=today - timedelta(days=5),
        )
        ComplianceAssessmentFactory(
            status=AssessmentStatus.IN_PROGRESS,
            assessment_start_date=today + timedelta(days=5),
            assessment_end_date=today + timedelta(days=10),
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["ongoing_audits"] == []

    def test_audit_cards_surface_in_summary_widget_too(self):
        from compliance.constants import AssessmentStatus
        from compliance.tests.factories import ComplianceAssessmentFactory

        today = date.today()
        ComplianceAssessmentFactory(
            name="ISO surveillance",
            status=AssessmentStatus.IN_PROGRESS,
            assessment_start_date=today - timedelta(days=1),
            assessment_end_date=today + timedelta(days=2),
        )
        client, user = _superuser_client()
        content = client.get(reverse("home")).content.decode()
        # The cards appear inside the Summary widget (its section) as well as the
        # standalone Ongoing audits widget (one card markup per widget).
        assert "ask-cairn__audits" in content
        assert 'data-widget-id="ongoing_audits"' in content
        assert content.count("ongoing-audits__item") >= 2

    def test_ongoing_audit_feeds_ask_cairn_summary(self):
        from compliance.constants import AssessmentStatus
        from compliance.tests.factories import ComplianceAssessmentFactory

        today = date.today()
        ComplianceAssessmentFactory(
            status=AssessmentStatus.IN_PROGRESS,
            assessment_start_date=today - timedelta(days=1),
            assessment_end_date=today + timedelta(days=2),
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        # No urgent item, but the ongoing audit alone feeds the Ask Cairn
        # snapshot, so the summary is generated (never an all-clear).
        data = resp.context["ask_cairn_data"]
        assert data.get("ongoing_audits") == 1
        assert resp.context["ask_cairn_audit_count"] == 1
        content = resp.content.decode()
        assert "all clear" not in content
        # AI off in tests -> deterministic fallback names the audit, not "0 points".
        assert "audit under way" in content

    def test_brief_flags_whole_scope_coverage(self):
        from compliance.constants import AssessmentStatus
        from compliance.tests.factories import ComplianceAssessmentFactory
        from core.views import ongoing_audits_brief

        today = date.today()
        root = ScopeFactory(name="Company")
        child = ScopeFactory(name="IT", parent_scope=root)
        full = ComplianceAssessmentFactory(
            status=AssessmentStatus.IN_PROGRESS,
            assessment_start_date=today,
            assessment_end_date=today + timedelta(days=1),
        )
        full.scopes.add(root)  # every root selected -> whole perimeter
        partial = ComplianceAssessmentFactory(
            status=AssessmentStatus.IN_PROGRESS,
            assessment_start_date=today,
            assessment_end_date=today + timedelta(days=1),
        )
        partial.scopes.add(child)  # a sub-scope only -> partial
        _, user = _superuser_client()
        brief = {b["name"]: b for b in ongoing_audits_brief(user, today)}
        assert brief[full.name]["covers_entire_scope"] is True
        assert brief[partial.name]["covers_entire_scope"] is False


class TestDashboardRiskTreatmentFlow:
    """Sankey flow from current risk level to residual risk level."""

    def test_no_flow_without_risks(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["risk_treatment_flow"] is None

    def test_flow_with_risk(self):
        RiskFactory(
            current_likelihood=4,
            current_impact=5,
            residual_likelihood=2,
            residual_impact=2,
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        flow = resp.context["risk_treatment_flow"]
        assert flow is not None
        assert flow["total"] == 1
        assert len(flow["links"]) == 1
        # One current-level node and one residual-level node.
        assert len(flow["nodes"]) == 2
        link = flow["links"][0]
        assert link["value"] == 1
        assert link["source"].startswith("c")
        assert link["target"].startswith("r")

    def test_flow_aggregates_identical_transitions(self):
        for _i in range(3):
            RiskFactory(
                current_likelihood=4,
                current_impact=5,
                residual_likelihood=2,
                residual_impact=2,
            )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        flow = resp.context["risk_treatment_flow"]
        assert flow["total"] == 3
        assert len(flow["links"]) == 1
        assert flow["links"][0]["value"] == 3

    def test_flow_skips_risks_without_both_levels(self):
        # Current evaluated but no residual evaluation -> excluded.
        RiskFactory(
            current_likelihood=3,
            current_impact=3,
            residual_likelihood=None,
            residual_impact=None,
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["risk_treatment_flow"] is None


# ── Company identity in the header ──────────────────────────


class TestDashboardCompanyIdentity:
    """The company name replaces the dashboard title (the logo is not shown)."""

    def test_company_name_as_title(self):
        from accounts.models import CompanySettings

        CompanySettings.objects.create(name="Voltara Energy")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["company"].name == "Voltara Energy"
        content = resp.content.decode()
        assert "Voltara Energy" in content
        # The company name is the sole title now: no eyebrow div above it.
        assert '<div class="page-header__eyebrow">' not in content

    def test_fallback_title_without_company(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["company"] is None
        assert "Dashboard" in resp.content.decode()
        assert b'class="page-header__logo"' not in resp.content

    def test_get_does_not_create_singleton(self):
        from accounts.models import CompanySettings

        client, user = _superuser_client()
        client.get(reverse("home"))
        assert not CompanySettings.objects.exists()

    def test_company_logo_not_in_title(self):
        from accounts.models import CompanySettings

        CompanySettings.objects.create(
            name="Voltara Energy",
            logo="data:image/png;base64,abc",
            logo_128="data:image/png;base64,abc128",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        # The dashboard title shows the company name only - no logo beside it.
        assert b'class="page-header__logo"' not in resp.content
        assert b"data:image/png;base64,abc128" not in resp.content
        assert "Voltara Energy" in resp.content.decode()

    def test_company_logo_replaces_sidebar_brand_when_enabled(self):
        from accounts.models import CompanySettings

        CompanySettings.objects.create(
            name="Voltara Energy",
            logo="data:image/png;base64,brandfull",
            logo_64="data:image/png;base64,brand64",
            use_logo_as_app_brand=True,
        )
        client, user = _superuser_client()
        content = client.get(reverse("home")).content.decode()
        # The sidebar brand uses the company logo (64px variant) and name...
        assert "data:image/png;base64,brand64" in content
        # ...but the About dialog always keeps the Cairn mark.
        assert ">Cairn</h5>" in content

    def test_sidebar_keeps_cairn_when_toggle_disabled(self):
        from accounts.models import CompanySettings

        CompanySettings.objects.create(
            name="Voltara Energy",
            logo="data:image/png;base64,brandfull",
            logo_64="data:image/png;base64,brand64",
            use_logo_as_app_brand=False,
        )
        client, user = _superuser_client()
        content = client.get(reverse("home")).content.decode()
        # The 64px brand variant is only used by the sidebar brand image,
        # which stays the Cairn mark while the toggle is off.
        assert "data:image/png;base64,brand64" not in content

    def test_company_field_in_global_context(self):
        from accounts.models import CompanySettings

        CompanySettings.objects.create(name="Voltara Energy", use_logo_as_app_brand=True)
        client, user = _superuser_client()
        # The company singleton is exposed globally (sidebar brand) via the
        # context processor, not only by the dashboard view.
        resp = client.get(reverse("calendar"))
        assert resp.context["company"].use_logo_as_app_brand is True

    def test_custom_app_name_replaces_cairn_brand(self):
        from accounts.models import CompanySettings

        CompanySettings.objects.create(name="Voltara Energy", app_name="Voltara GRC")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["APP_NAME"] == "Voltara GRC"
        # The sidebar brand text uses the custom application name.
        assert "Voltara GRC" in resp.content.decode()

    def test_app_name_defaults_to_cairn(self):
        client, user = _regular_client()
        resp = client.get(reverse("home"))
        assert resp.context["APP_NAME"] == "Cairn"

    def test_custom_accent_color_injects_override(self):
        from accounts.models import CompanySettings

        CompanySettings.objects.create(name="Voltara Energy", accent_color="#2E7D32")
        client, user = _superuser_client()
        content = client.get(reverse("home")).content.decode()
        assert 'id="brand-accent-override"' in content
        assert "#2E7D32" in content

    def test_no_accent_override_without_custom_color(self):
        from accounts.models import CompanySettings

        CompanySettings.objects.create(name="Voltara Energy")
        client, user = _superuser_client()
        content = client.get(reverse("home")).content.decode()
        assert 'id="brand-accent-override"' not in content

    def test_dark_mode_keeps_a_dark_accent_legible(self):
        from accounts.models import CompanySettings

        CompanySettings.objects.create(name="Voltara Energy", accent_color="#000000")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        # Black on white is fine in light mode, but must be lightened for the
        # dark charcoal canvas so the accent stays visible.
        assert resp.context["ACCENT_LIGHT"] == "#000000"
        assert resp.context["ACCENT_DARK"] != "#000000"


# ── Collapsible section state (persisted per user) ──────────────


class TestSectionCollapseToggle:
    """The dashboard-section-toggle endpoint persists collapse state per user."""

    def test_collapse_then_expand_persists(self):
        client, user = _regular_client()
        url = reverse("dashboard-section-toggle")

        resp = client.post(
            url,
            data={"section": "today_actions", "collapsed": True},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "collapsed": True}
        user.refresh_from_db()
        assert "today_actions" in user.collapsed_sections

        resp = client.post(
            url,
            data={"section": "today_actions", "collapsed": False},
            content_type="application/json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert "today_actions" not in user.collapsed_sections

    def test_collapse_is_idempotent(self):
        client, user = _regular_client()
        url = reverse("dashboard-section-toggle")
        for _ in range(2):
            client.post(
                url,
                data={"section": "today_actions", "collapsed": True},
                content_type="application/json",
            )
        user.refresh_from_db()
        assert user.collapsed_sections.count("today_actions") == 1

    def test_unknown_section_rejected(self):
        client, user = _regular_client()
        resp = client.post(
            reverse("dashboard-section-toggle"),
            data={"section": "evil", "collapsed": True},
            content_type="application/json",
        )
        assert resp.status_code == 400
        user.refresh_from_db()
        assert user.collapsed_sections == []

    def test_requires_login(self):
        resp = Client().post(
            reverse("dashboard-section-toggle"),
            data={"section": "today_actions", "collapsed": True},
            content_type="application/json",
        )
        assert resp.status_code in (302, 403)

    def test_collapsed_state_reflected_in_dashboard_context(self):
        client, user = _regular_client()
        user.collapsed_sections = ["today_actions"]
        user.save(update_fields=["collapsed_sections"])
        resp = client.get(reverse("home"))
        assert resp.context["today_actions_collapsed"] is True

    def test_default_state_is_expanded(self):
        client, user = _regular_client()
        resp = client.get(reverse("home"))
        assert resp.context["today_actions_collapsed"] is False


# ── Configurable widget grid ─────────────────────────────────


class TestDashboardWidgetRegistry:
    """The widget registry resolves and sanitises per-user layouts safely."""

    def test_default_layout_covers_every_singleton_once(self):
        from core.dashboard import DASHBOARD_WIDGETS, default_layout

        layout = default_layout()
        ids = [e["id"] for e in layout]
        singletons = [w.id for w in DASHBOARD_WIDGETS if not w.multiple]
        # Only singletons are placed by default; "multiple" widgets start empty.
        assert sorted(ids) == sorted(singletons)
        assert "indicator" not in ids
        assert len(ids) == len(set(ids))
        # Every default entry carries an instance key (== id for singletons) and a
        # params dict (empty for plain widgets, populated for configurable ones).
        assert all(e["key"] == e["id"] and isinstance(e["params"], dict) for e in layout)

    def test_resolve_drops_unknown_and_appends_missing(self):
        from core.dashboard import DASHBOARD_WIDGETS, resolve_layout

        resolved = resolve_layout([
            {"id": "priority_risks", "size": "2x2", "visible": False},
            {"id": "does_not_exist", "size": "2x2"},
            {"id": "priority_risks", "size": "1x2"},  # duplicate singleton -> ignored
        ])
        ids = [e["id"] for e in resolved]
        singletons = [w.id for w in DASHBOARD_WIDGETS if not w.multiple]
        # Unknown id dropped; every singleton present exactly once; no multiple ones.
        assert "does_not_exist" not in ids
        assert sorted(ids) == sorted(singletons)
        assert ids.count("priority_risks") == 1
        # The first (kept) entry preserved its size/visibility and gained key/params.
        first = next(e for e in resolved if e["id"] == "priority_risks")
        assert first == {
            "key": "priority_risks", "id": "priority_risks", "size": "2x2",
            "visible": False, "zone": "rail_top", "params": {},
        }

    def test_resolve_keeps_multiple_instances_with_params(self):
        from core.dashboard import resolve_layout

        resolved = resolve_layout([
            {"key": "indicator-a", "id": "indicator", "size": "1x1",
             "params": {"indicator": "abc", "show_chart": True}},
            {"key": "indicator-b", "id": "indicator", "size": "1x1",
             "params": {"indicator": "def", "show_chart": False}},
            # Missing key -> a unique one is generated, not dropped.
            {"id": "indicator", "size": "1x1", "params": {"indicator": "ghi"}},
        ])
        instances = [e for e in resolved if e["id"] == "indicator"]
        assert len(instances) == 3
        keys = [e["key"] for e in instances]
        assert keys[0] == "indicator-a" and keys[1] == "indicator-b"
        assert len(set(keys)) == 3  # all unique, including the generated one
        assert instances[0]["params"] == {"indicator": "abc", "show_chart": True}
        # show_chart coerced to bool / defaulted.
        assert instances[2]["params"] == {"indicator": "ghi", "show_chart": False}

    def test_resolve_sanitizes_indicator_params(self):
        from core.dashboard import resolve_layout

        resolved = resolve_layout([
            {"key": "x", "id": "indicator", "size": "1x1", "params": "not-a-dict"},
        ])
        assert resolved[0]["params"] == {"indicator": "", "show_chart": False}

    def test_resolve_sanitizes_sort_params(self):
        from core.dashboard import resolve_layout

        resolved = {e["id"]: e for e in resolve_layout([
            # Valid sort + order kept (order coerced to strings).
            {"id": "compliance_by_framework", "size": "3x2",
             "params": {"sort": "value_desc", "order": [1, "b", 3]}},
            # Unknown sort falls back to "default"; non-list order -> [].
            {"id": "active_objectives", "size": "2x2",
             "params": {"sort": "bogus", "order": "nope"}},
        ])}
        assert resolved["compliance_by_framework"]["params"] == {
            "sort": "value_desc", "order": ["1", "b", "3"],
        }
        assert resolved["active_objectives"]["params"] == {"sort": "default", "order": []}

    def test_progress_widgets_are_sort_configurable(self):
        from core.dashboard import WIDGETS_BY_ID

        for wid in ("compliance_by_framework", "active_objectives"):
            w = WIDGETS_BY_ID[wid]
            assert w.configurable is True
            assert w.config == "sort"
            assert not w.multiple
        assert WIDGETS_BY_ID["indicator"].config == "indicator"
        # A plain widget is not configurable.
        assert WIDGETS_BY_ID["risk_matrix_current"].configurable is False

    def test_overall_compliance_is_target_configurable(self):
        from core.dashboard import WIDGETS_BY_ID

        w = WIDGETS_BY_ID["overall_compliance"]
        assert w.config == "target"
        assert w.configurable is True
        # Default params show the target at 80.
        assert w.default_params() == {"show_target": True, "target": 80}

    def test_resolve_sanitizes_target_params(self):
        from core.dashboard import resolve_layout

        resolved = {e["id"]: e for e in resolve_layout([
            # Out-of-range value clamped, show_target coerced to bool.
            {"id": "overall_compliance", "size": "4x1",
             "params": {"show_target": False, "target": 150}},
        ])}
        assert resolved["overall_compliance"]["params"] == {"show_target": False, "target": 100}

    def test_resolve_clamps_invalid_size_to_default(self):
        from core.dashboard import WIDGETS_BY_ID, resolve_layout

        # "9x9" is out of range and not an allowed size for risk_matrix_current.
        resolved = {e["id"]: e for e in resolve_layout([
            {"id": "risk_matrix_current", "size": "9x9", "visible": True},
            {"id": "active_objectives", "size": "garbage", "visible": True},
        ])}
        assert resolved["risk_matrix_current"]["size"] == WIDGETS_BY_ID["risk_matrix_current"].default_size
        assert resolved["active_objectives"]["size"] == WIDGETS_BY_ID["active_objectives"].default_size

    def test_resolve_migrates_legacy_letter_size(self):
        from core.dashboard import WIDGETS_BY_ID, resolve_layout

        # Legacy single-letter sizes keep their width: M -> width 2, L -> width 3,
        # preferring the token whose height matches the widget default.
        resolved = {e["id"]: e for e in resolve_layout([
            {"id": "active_objectives", "size": "M", "visible": True},  # 2x2 default
            {"id": "compliance_by_framework", "size": "L", "visible": True},  # 3x2 default
            # No allowed width-1 token for risk_matrix_current -> falls back to default.
            {"id": "risk_matrix_current", "size": "S", "visible": True},
        ])}
        assert resolved["active_objectives"]["size"] == "2x2"
        assert resolved["compliance_by_framework"]["size"] == "3x2"
        assert resolved["risk_matrix_current"]["size"] == WIDGETS_BY_ID["risk_matrix_current"].default_size

    def test_resolve_carries_and_clamps_zone(self):
        from core.dashboard import resolve_layout

        resolved = {e["id"]: e for e in resolve_layout([
            # Move a normally-main widget to a valid rail sub-zone (kept).
            {"id": "active_objectives", "size": "1x2", "visible": True, "zone": "rail_bottom"},
            # Legacy single "rail" zone migrates to the top sub-zone.
            {"id": "compliance_by_framework", "size": "2x2", "visible": True, "zone": "rail"},
            # Bogus zone falls back to the widget default (main).
            {"id": "overall_compliance", "size": "4x1", "visible": True, "zone": "nope"},
        ])}
        assert resolved["active_objectives"]["zone"] == "rail_bottom"
        assert resolved["compliance_by_framework"]["zone"] == "rail_top"
        assert resolved["overall_compliance"]["zone"] == "main"
        # Untouched widgets keep their default zone (rail widgets default to the top).
        assert resolved["priority_risks"]["zone"] == "rail_top"


class TestWidgetSizeGeometry:
    """The x*y size tokens parse into grid spans and labels correctly."""

    def test_parse_size_valid_and_invalid(self):
        from core.dashboard import parse_size

        assert parse_size("2x1") == (2, 1)
        assert parse_size("4x3") == (4, 3)
        assert parse_size("4X2") == (4, 2)  # case-insensitive
        # Out of range / malformed -> None.
        assert parse_size("5x1") is None
        assert parse_size("2x9") is None
        assert parse_size("0x1") is None
        assert parse_size("2") is None
        assert parse_size("axb") is None
        assert parse_size("") is None
        assert parse_size(None) is None

    def test_size_label(self):
        from core.dashboard import size_label

        assert size_label("2x1") == "2 × 1"
        assert size_label("4x3") == "4 × 3"

    def test_cols_rows_mapping(self):
        from core.dashboard import WIDGETS_BY_ID

        w = WIDGETS_BY_ID["risk_matrix_current"]
        # Width unit -> 3 grid columns; height unit -> grid rows.
        assert w.cols("4x2") == 12
        assert w.rows("4x2") == 2
        assert w.cols("3x2") == 9
        assert w.width("3x2") == 3
        assert w.height("3x3") == 3
        # An unparseable size falls back to the widget default's dims.
        assert w.cols("bogus") == w.cols(w.default_size)
        assert w.rows("bogus") == w.rows(w.default_size)

    def test_catalogue_sizes_are_valid_tokens(self):
        from core.dashboard import DASHBOARD_WIDGETS, parse_size

        for widget in DASHBOARD_WIDGETS:
            assert widget.sizes, f"{widget.id} declares no sizes"
            for size in widget.sizes:
                assert parse_size(size) is not None, f"{widget.id}: bad size {size!r}"
            # The default must be one of the allowed sizes.
            assert widget.default_size in widget.sizes, (
                f"{widget.id}: default {widget.default_size!r} not in {widget.sizes}"
            )


class TestDashboardLayoutEndpoint:
    """The per-user layout save endpoint persists a sanitised layout."""

    def test_save_persists_sanitised_layout(self):
        client, user = _regular_client()
        resp = client.post(
            reverse("dashboard-layout-save"),
            data=json.dumps({"layout": [
                {"id": "priority_risks", "size": "2x2", "visible": True},
                {"id": "overall_compliance", "size": "3x1", "visible": False},
                {"id": "bogus", "size": "2x2"},
            ]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        user.refresh_from_db()
        ids = [e["id"] for e in user.dashboard_layout]
        assert "bogus" not in ids
        assert user.dashboard_layout[0] == {
            "key": "priority_risks", "id": "priority_risks", "size": "2x2",
            "visible": True, "zone": "rail_top", "params": {},
        }

    def test_save_persists_indicator_instances(self):
        client, user = _regular_client()
        resp = client.post(
            reverse("dashboard-layout-save"),
            data=json.dumps({"layout": [
                {"key": "indicator-1", "id": "indicator", "size": "1x1",
                 "params": {"indicator": "11111111-1111-1111-1111-111111111111", "show_chart": True}},
                {"key": "indicator-2", "id": "indicator", "size": "1x1",
                 "params": {"indicator": "22222222-2222-2222-2222-222222222222", "show_chart": False}},
            ]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        instances = [e for e in user.dashboard_layout if e["id"] == "indicator"]
        assert len(instances) == 2
        assert {e["key"] for e in instances} == {"indicator-1", "indicator-2"}
        assert instances[0]["params"]["show_chart"] is True

    def test_invalid_body_returns_400(self):
        client, user = _regular_client()
        resp = client.post(
            reverse("dashboard-layout-save"),
            data="not json",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_requires_login(self):
        resp = Client().post(reverse("dashboard-layout-save"), data="{}", content_type="application/json")
        assert resp.status_code in (302, 403)


class TestDashboardLayoutApi:
    """The DRF dashboard-layout endpoint reads and replaces the layout."""

    def test_get_returns_layout_and_catalogue(self):
        from core.dashboard import DASHBOARD_WIDGETS

        client, user = _regular_client()
        resp = client.get("/api/v1/dashboard-layout/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        # The default layout places singletons only; the catalogue lists every type.
        singletons = [w for w in DASHBOARD_WIDGETS if not w.multiple]
        assert len(data["layout"]) == len(singletons)
        assert len(data["widgets"]) == len(DASHBOARD_WIDGETS)
        # The catalogue flags which widgets can be placed multiple times.
        indicator = next(w for w in data["widgets"] if w["id"] == "indicator")
        assert indicator["multiple"] is True

    def test_put_replaces_layout(self):
        client, user = _regular_client()
        resp = client.put(
            "/api/v1/dashboard-layout/",
            data=json.dumps({"layout": [
                {"key": "indicator-x", "id": "indicator", "size": "1x1",
                 "params": {"indicator": "11111111-1111-1111-1111-111111111111"}},
            ]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.dashboard_layout[0]["id"] == "indicator"
        assert user.dashboard_layout[0]["key"] == "indicator-x"


class TestDashboardGridRendering:
    """The dashboard renders as two widget zones with the edit chrome."""

    def test_zones_and_edit_controls_present(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        content = resp.content.decode()
        assert 'id="dashboardZones"' in content
        assert 'id="dashboardMain"' in content
        assert 'id="dashboardRailTop"' in content
        assert 'id="dashboardRailBottom"' in content
        assert 'class="dash-widget' in content
        assert 'id="dashEditToggle"' in content
        assert 'id="widgetGallery"' in content

    def test_rail_widgets_render_in_rail_zone(self):
        # priority_risks defaults to the top rail sub-zone, so its widget shell
        # must appear after that container opens and before the gallery (which
        # lists every widget id and would otherwise create a false positive).
        client, user = _superuser_client()
        content = client.get(reverse("home")).content.decode()
        main_at = content.index('id="dashboardMain"')
        rail_at = content.index('id="dashboardRailTop"')
        gallery_at = content.index('id="widgetGallery"')
        widget_at = content.index('data-widget-id="priority_risks"')
        assert rail_at < widget_at < gallery_at
        assert not (main_at < widget_at < rail_at)
        assert 'data-zone="rail_top"' in content

    def test_no_template_comment_leak(self):
        # Django {# #} comments are single-line only; a multi-line one leaks its
        # continuation as visible text. Guard against that regression across the
        # dashboard partials (markers are taken from each widget's comments).
        client, user = _superuser_client()
        content = client.get(reverse("home")).content.decode()
        # Generic guard: no raw Django comment delimiters survive into the HTML
        # (a multi-line {# #} leaks both markers and its text verbatim).
        assert "{#" not in content and "#}" not in content
        for marker in (
            "Generic widget wrapper",
            "Expects `placed`",
            "size_options}",
            "Fills the tile in the main grid",
            "the card is content-height",
        ):
            assert marker not in content

    def test_hidden_widget_marked_not_visible(self):
        client, user = _regular_client()
        user.dashboard_layout = [{"id": "risk_matrix_current", "size": "4x2", "visible": False}]
        user.save(update_fields=["dashboard_layout"])
        resp = client.get(reverse("home"))
        content = resp.content.decode()
        # The hidden widget is in the DOM but flagged so CSS keeps it off-grid.
        assert 'data-widget-id="risk_matrix_current"' in content
        assert 'data-visible="false"' in content

    def test_main_widget_renders_2d_grid_spans_and_size_classes(self):
        # A 3x2 main widget must carry both grid spans (3 width units -> 9 cols,
        # 2 height units -> 2 rows) and the width/height classes.
        client, user = _regular_client()
        user.dashboard_layout = [
            {"id": "compliance_by_framework", "size": "3x2", "visible": True, "zone": "main"},
        ]
        user.save(update_fields=["dashboard_layout"])
        content = client.get(reverse("home")).content.decode()
        anchor = content.index('data-widget-id="compliance_by_framework"')
        section = content[anchor - 200:anchor + 600]
        assert 'grid-column: span 9' in section
        assert 'grid-row: span 2' in section
        assert 'dash-widget--w3' in section
        assert 'dash-widget--h2' in section

    def test_rail_widget_has_no_inline_grid(self):
        # Rail widgets stack at content height: no inline grid spans are emitted.
        client, user = _regular_client()
        user.dashboard_layout = [
            {"id": "priority_risks", "size": "1x2", "visible": True, "zone": "rail_top"},
        ]
        user.save(update_fields=["dashboard_layout"])
        content = client.get(reverse("home")).content.decode()
        anchor = content.index('data-widget-id="priority_risks"')
        section = content[anchor - 200:anchor + 300]
        assert 'grid-column' not in section
        assert 'grid-row' not in section

    def test_overall_compliance_renders_target_config(self):
        # The overall-compliance widget exposes the target gear, renders the
        # marker at the configured value, and the target dialog is on the page.
        client, user = _regular_client()
        user.dashboard_layout = [
            {"id": "overall_compliance", "size": "4x1", "visible": True, "zone": "main",
             "params": {"show_target": True, "target": 90}},
        ]
        user.save(update_fields=["dashboard_layout"])
        content = client.get(reverse("home")).content.decode()
        anchor = content.index('data-widget-id="overall_compliance"')
        section = content[anchor - 100:anchor + 1800]
        assert 'data-config="target"' in section
        assert 'dash-widget__config' in section
        assert 'id="targetConfigModal"' in content
        # The marker is rendered at the configured target, with no display:none.
        assert 'style="left:90%"' in content

    def test_overall_compliance_target_hidden(self):
        client, user = _regular_client()
        user.dashboard_layout = [
            {"id": "overall_compliance", "size": "4x1", "visible": True, "zone": "main",
             "params": {"show_target": False, "target": 80}},
        ]
        user.save(update_fields=["dashboard_layout"])
        content = client.get(reverse("home")).content.decode()
        # The marker carries an inline display:none when the target is hidden.
        assert 'overall-compliance__target" style="left:80%;display:none"' in content

    def test_progress_widget_renders_sort_config(self):
        # The progress-bar widgets expose the sort gear, declare the sort config
        # kind, render a data-progress-rows container, and the sort dialog is
        # present on the page.
        client, user = _regular_client()
        user.dashboard_layout = [
            {"id": "active_objectives", "size": "2x2", "visible": True, "zone": "main"},
        ]
        user.save(update_fields=["dashboard_layout"])
        content = client.get(reverse("home")).content.decode()
        anchor = content.index('data-widget-id="active_objectives"')
        section = content[anchor - 100:anchor + 1600]
        assert 'data-config="sort"' in section
        assert 'dash-widget__config' in section
        assert 'data-progress-rows' in content
        assert 'id="sortConfigModal"' in content


class TestIndicatorWidget:
    """The per-indicator widget: instance params, config gear, render, partial."""

    def test_configured_indicator_widget_renders_card(self):
        ind = _make_indicator(name="Coverage", current_value="85")
        client, user = _regular_client()
        user.dashboard_layout = [{
            "key": "i1", "id": "indicator", "size": "1x1", "visible": True,
            "zone": "main", "params": {"indicator": str(ind.pk), "show_chart": False},
        }]
        user.save(update_fields=["dashboard_layout"])
        content = client.get(reverse("home")).content.decode()
        anchor = content.index('data-widget-id="indicator"')
        section = content[anchor - 100:anchor + 1600]
        # Carries its instance key, is flagged multiple, exposes the config gear,
        # and renders the indicator's KPI card (not the empty placeholder).
        assert 'data-key="i1"' in section
        assert 'data-multiple="true"' in section
        assert 'dash-widget__config' in section
        assert f'data-indicator-id="{ind.pk}"' in content
        # The section's opening tag (first 200 chars) is not flagged empty.
        assert 'dash-widget--empty' not in section[:200]

    def test_unconfigured_indicator_widget_is_empty_placeholder(self):
        client, user = _regular_client()
        user.dashboard_layout = [{
            "key": "i1", "id": "indicator", "size": "1x1", "visible": True,
            "zone": "main", "params": {"indicator": "", "show_chart": False},
        }]
        user.save(update_fields=["dashboard_layout"])
        content = client.get(reverse("home")).content.decode()
        anchor = content.index('data-widget-id="indicator"')
        section = content[anchor - 100:anchor + 600]
        # No indicator chosen -> empty (hidden in view mode) with a configure prompt.
        assert 'dash-widget--empty' in section
        assert "Choose an indicator" in content

    def test_indicator_widget_template_node_present(self):
        # The hidden clone source the editor duplicates to add a new instance.
        client, user = _regular_client()
        content = client.get(reverse("home")).content.decode()
        assert 'id="indicatorWidgetTemplate"' in content
        assert 'id="indicatorConfigModal"' in content

    def test_gallery_indicator_tile_is_multiple(self):
        client, user = _regular_client()
        content = client.get(reverse("home")).content.decode()
        # The indicator gallery tile is always available and marked multiple.
        gallery_at = content.index('id="widgetGalleryList"')
        tail = content[gallery_at:gallery_at + 4000]
        assert 'data-widget-id="indicator"' in tail
        assert 'data-multiple="true"' in tail

    def test_partial_endpoint_renders_card_for_indicator(self):
        ind = _make_indicator(name="Latency", current_value="42")
        client, user = _regular_client()
        url = reverse("dashboard-indicator-widget")
        resp = client.get(url, {"indicator": str(ind.pk), "chart": "0"})
        assert resp.status_code == 200
        content = resp.content.decode()
        assert f'data-indicator-id="{ind.pk}"' in content
        assert "Latency" in content

    def test_partial_endpoint_placeholder_without_indicator(self):
        client, user = _regular_client()
        url = reverse("dashboard-indicator-widget")
        resp = client.get(url)
        assert resp.status_code == 200
        assert "Choose an indicator" in resp.content.decode()

    def test_partial_endpoint_handles_bad_indicator_id(self):
        # A malformed indicator id must not 500; it renders the placeholder.
        client, user = _regular_client()
        url = reverse("dashboard-indicator-widget")
        resp = client.get(url, {"indicator": "not-a-uuid"})
        assert resp.status_code == 200
        assert "Choose an indicator" in resp.content.decode()


class TestAskCairnWidget:
    """The Ask Cairn widget: a metrics snapshot synthesised by the LLM (with a
    deterministic count fallback when the assistant is off / loading)."""

    def test_in_registry_defaults_to_rail(self):
        from core.dashboard import WIDGETS_BY_ID, default_layout

        w = WIDGETS_BY_ID["ask_cairn"]
        assert not w.multiple and not w.configurable
        # Titled "Summary" ("Résumé" in French); the Ask Cairn brand lives in the
        # AI attribution line, not the title.
        assert str(w.title) == "Summary"
        # Defaults to the top rail sub-zone (and is placeable in either).
        assert w.default_zone == "rail_top"
        entry = next((e for e in default_layout() if e["id"] == "ask_cairn"), None)
        assert entry is not None and entry["zone"] == "rail_top"

    def test_builds_metrics_snapshot_references_and_fallback(self):
        RiskFactory(priority="critical")
        # A non-urgent ("to plan") item: tracked, but must NOT feed the summary.
        Role.objects.create(name="DPO", type="governance", is_mandatory=True)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        data = resp.context["ask_cairn_data"]
        assert data["critical_risks_to_treat"] == 1
        assert "overall_compliance_pct" in data
        # Only urgent (high-tone) items feed the summary; the mandatory role is
        # tracked elsewhere but excluded from the snapshot and the references.
        assert "mandatory_roles_without_owner" not in data
        assert resp.context["mandatory_roles_no_user"] == 1
        assert resp.context["ask_cairn_point_count"] == 1
        # The references behind the snapshot, each linking out - all urgent.
        refs = resp.context["ask_cairn_references"]
        assert refs and refs[0]["url"] and all(r["tone"] == "high" for r in refs)
        content = resp.content.decode()
        assert 'data-widget-id="ask_cairn"' in content
        # The snapshot is embedded for the async briefing fetch.
        assert "data-facts=" in content
        # AI disabled in tests -> deterministic count fallback + the references.
        assert "point needs your attention today" in content
        assert "ask-cairn__refs" in content and refs[0]["label"] in content

    def test_all_clear_when_nothing_urgent(self):
        # A non-urgent ("to plan") item exists, but the summary reacts only to
        # urgent ones, so it still reads all-clear.
        Role.objects.create(name="DPO", type="governance", is_mandatory=True)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["mandatory_roles_no_user"] == 1  # tracked elsewhere
        # No *urgent* items -> empty snapshot, all-clear message.
        assert resp.context["ask_cairn_data"] == {}
        assert resp.context["ask_cairn_point_count"] == 0
        content = resp.content.decode()
        assert 'data-widget-id="ask_cairn"' in content  # always rendered
        assert "all clear" in content

    def test_summary_shows_skeleton_not_count_while_loading(self, settings):
        # With the assistant on, a modern skeleton placeholder is shown while the
        # briefing loads - the deterministic count never flashes (it is kept
        # hidden for the failure path only).
        settings.AI_ASSISTANT_ENABLED = True
        RiskFactory(priority="critical")
        client, user = _superuser_client()
        content = client.get(reverse("home")).content.decode()
        assert "ask-cairn__skeleton" in content
        assert "data-ai-count" in content

    def test_emoji_forced_to_paragraph_start(self):
        from core.views import _move_emojis_to_paragraph_start

        out = _move_emojis_to_paragraph_start(
            "<p>Two risks \U0001F4CA and one plan \U0001F6A8.</p><p>Audit ok.</p>"
        )
        # The first emoji is moved to the very start; any extra one is dropped.
        assert out.startswith("<p>\U0001F4CA ")
        assert "\U0001F6A8" not in out
        assert out.count("\U0001F4CA") == 1
        assert "<p>Audit ok.</p>" in out

    def test_briefing_endpoint_disabled_returns_not_ok(self):
        client, user = _regular_client()
        resp = client.post(
            reverse("dashboard-ask-cairn-briefing"),
            data=json.dumps({"data": {"critical_risks_to_treat": 2}}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is False

    def test_briefing_endpoint_generates_when_enabled(self, settings):
        from unittest.mock import MagicMock, patch

        settings.AI_ASSISTANT_ENABLED = True
        settings.AI_ASSISTANT_PROVIDER = "mistral"
        settings.AI_ASSISTANT_MODEL = "mistral-small-latest"
        fake = MagicMock()
        fake.chat_text.return_value = "Two critical risks need treatment today."
        client, user = _regular_client()
        with patch("assistant.providers.get_client", return_value=fake):
            resp = client.post(
                reverse("dashboard-ask-cairn-briefing"),
                data=json.dumps({"data": {"critical_risks_to_treat": 2, "bogus": 9}}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["text"] == "Two critical risks need treatment today."
        # Honest attribution: the provider only (no model name), with a timestamp.
        assert "powered by Mistral" in body["disclaimer"]
        assert "mistral-small-latest" not in body["disclaimer"]
        # The model only received allow-listed metric keys.
        sent = fake.chat_text.call_args[0][0][1]["content"]
        assert "critical_risks_to_treat" in sent and "bogus" not in sent

    def test_briefing_endpoint_includes_audits_and_sanitizes_bold(self, settings):
        from unittest.mock import MagicMock, patch

        from compliance.constants import AssessmentStatus
        from compliance.tests.factories import ComplianceAssessmentFactory

        settings.AI_ASSISTANT_ENABLED = True
        settings.AI_ASSISTANT_PROVIDER = "mistral"
        settings.AI_ASSISTANT_MODEL = "mistral-small-latest"
        today = date.today()
        auditor = UserFactory(first_name="Sofia", last_name="Lindqvist")
        audit = ComplianceAssessmentFactory(
            name="ISO surveillance",
            assessor=auditor,
            status=AssessmentStatus.IN_PROGRESS,
            assessment_start_date=today - timedelta(days=1),
            assessment_end_date=today + timedelta(days=2),
        )
        audit.scopes.add(ScopeFactory(name="HQ Datacenter"))
        fake = MagicMock()
        fake.chat_text.return_value = (
            "<p><b>Audits :</b> led by Sofia Lindqvist, covers HQ Datacenter.</p>"
            "<p>2 risks.</p><script>x</script>"
        )
        client, user = _superuser_client()  # superuser -> the audit query is unscoped
        with patch("assistant.providers.get_client", return_value=fake):
            resp = client.post(
                reverse("dashboard-ask-cairn-briefing"),
                data=json.dumps({"data": {"overall_compliance_pct": 50}}),
                content_type="application/json",
            )
        body = resp.json()
        assert body["ok"] is True
        # The audit brief is built server-side (name + scopes) and sent to the model.
        sent = fake.chat_text.call_args[0][0][1]["content"]
        assert "ongoing_audits" in sent
        assert "ISO surveillance" in sent and "HQ Datacenter" in sent
        # <p>/<b> are preserved; any other HTML the model emits is escaped.
        assert "<p><b>Audits :</b>" in body["text"] and "HQ Datacenter" in body["text"]
        assert "<p>2 risks.</p>" in body["text"]
        # The named auditor is rendered as a photo + name chip.
        assert 'class="ask-cairn__chip"' in body["text"]
        assert "Sofia Lindqvist" in body["text"]
        assert "<script>" not in body["text"] and "&lt;script&gt;" in body["text"]

"""Smoke tests for the EBIOS RM REST endpoints (workshops W0 and W1).

These tests verify the URL routing, basic authentication and the standard
JSON envelope. Deeper assertions (filters, workflow transitions, validate
actions) belong to dedicated test classes added when those features ship
in later lots.
"""

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from assets.tests.factories import SupportAssetFactory
from risks.tests.factories import (
    AttackPathStepFactory,
    BaselineGapFactory,
    EbiosAssessmentFactory,
    EcosystemStakeholderFactory,
    FearedEventFactory,
    RiskSourceFactory,
    RiskSourceObjectivePairFactory,
    SecurityBaselineFactory,
    StrategicScenarioFactory,
    StudyFrameworkFactory,
    TargetedObjectiveFactory,
)

pytestmark = pytest.mark.django_db


def _data(response):
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


class TestEbiosApiSmoke:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_study_frameworks_endpoint(self):
        StudyFrameworkFactory()
        response = self.client.get("/api/v1/risks/ebios/study-frameworks/")
        assert response.status_code == 200

    def test_workshops_endpoint(self):
        EbiosAssessmentFactory()  # signal creates 6 workshops
        response = self.client.get("/api/v1/risks/ebios/workshops/")
        assert response.status_code == 200
        # An ebios_rm assessment creates exactly 6 workshop progress rows
        # (W0..W5), so the list should not be empty.
        data = _data(response)
        items = data.get("results") if isinstance(data, dict) else data
        assert isinstance(items, list)
        assert len(items) >= 6

    def test_baselines_endpoint(self):
        SecurityBaselineFactory()
        response = self.client.get("/api/v1/risks/ebios/baselines/")
        assert response.status_code == 200

    def test_feared_events_endpoint(self):
        FearedEventFactory()
        response = self.client.get("/api/v1/risks/ebios/feared-events/")
        assert response.status_code == 200

    def test_baseline_gaps_endpoint(self):
        BaselineGapFactory()
        response = self.client.get("/api/v1/risks/ebios/baseline-gaps/")
        assert response.status_code == 200

    def test_workshops_filter_by_assessment(self):
        a = EbiosAssessmentFactory()
        b = EbiosAssessmentFactory()
        response = self.client.get(
            f"/api/v1/risks/ebios/workshops/?assessment={a.pk}"
        )
        assert response.status_code == 200
        data = _data(response)
        items = data.get("results") if isinstance(data, dict) else data
        # All returned workshops must belong to assessment `a` only.
        assert all(item["assessment"] == str(a.pk) for item in items)

    def test_unauthenticated_request_is_rejected(self):
        anon = APIClient()
        response = anon.get("/api/v1/risks/ebios/study-frameworks/")
        assert response.status_code in (401, 403)

    def test_risk_sources_endpoint(self):
        RiskSourceFactory()
        response = self.client.get("/api/v1/risks/ebios/risk-sources/")
        assert response.status_code == 200

    def test_risk_sources_serialize_threat_level(self):
        rs = RiskSourceFactory(motivation_level=4, resources_level=4)
        response = self.client.get(f"/api/v1/risks/ebios/risk-sources/{rs.pk}/")
        assert response.status_code == 200
        data = _data(response)
        assert data["threat_level"] == 4

    def test_risk_sources_filter_by_threat_level_min(self):
        # Two SRs: one V1 (mot=1, res=1) and one V4 (mot=4, res=4)
        RiskSourceFactory(motivation_level=1, resources_level=1)
        rs_high = RiskSourceFactory(motivation_level=4, resources_level=4)
        response = self.client.get(
            "/api/v1/risks/ebios/risk-sources/?threat_level_min=3"
        )
        assert response.status_code == 200
        data = _data(response)
        items = data.get("results") if isinstance(data, dict) else data
        ids = {item["id"] for item in items}
        assert str(rs_high.pk) in ids
        assert len(ids) == 1

    def test_targeted_objectives_endpoint(self):
        TargetedObjectiveFactory()
        response = self.client.get("/api/v1/risks/ebios/targeted-objectives/")
        assert response.status_code == 200

    def test_sr_ov_pairs_endpoint(self):
        RiskSourceObjectivePairFactory()
        response = self.client.get("/api/v1/risks/ebios/sr-ov-pairs/")
        assert response.status_code == 200

    def test_sr_ov_pairs_serialize_priority_score(self):
        # motivation 4 + resources 4 -> V4 (=4), relevance low (=1), max = 4
        pair = RiskSourceObjectivePairFactory()
        response = self.client.get(f"/api/v1/risks/ebios/sr-ov-pairs/{pair.pk}/")
        assert response.status_code == 200
        data = _data(response)
        assert data["priority_score"] is not None

    def test_ecosystem_stakeholders_endpoint(self):
        EcosystemStakeholderFactory()
        response = self.client.get("/api/v1/risks/ebios/ecosystem-stakeholders/")
        assert response.status_code == 200

    def test_ecosystem_stakeholders_serialize_threat_zone(self):
        s = EcosystemStakeholderFactory(
            dependency=4, penetration=4, maturity=1, trust=1,
        )
        response = self.client.get(
            f"/api/v1/risks/ebios/ecosystem-stakeholders/{s.pk}/"
        )
        assert response.status_code == 200
        data = _data(response)
        assert data["threat_zone"] == "danger"
        assert float(data["threat_level"]) == 16.0

    def test_ecosystem_graph_endpoint(self):
        assessment = EbiosAssessmentFactory()
        asset = SupportAssetFactory()
        stakeholder = EcosystemStakeholderFactory(
            assessment=assessment, dependency=3, penetration=3, maturity=2, trust=2,
        )
        stakeholder.accessible_support_assets.add(asset)
        response = self.client.get(
            f"/api/v1/risks/ebios/ecosystem-stakeholders/graph/?assessment={assessment.pk}"
        )
        assert response.status_code == 200
        body = _data(response)
        nodes = body["nodes"]
        edges = body["edges"]
        zones = body["zones"]
        assert any(node["id"] == str(stakeholder.pk) for node in nodes)
        assert any(edge["source"] == str(stakeholder.pk) and edge["target"] == str(asset.pk)
                   for edge in edges)
        assert "control" in zones and "monitoring" in zones and "danger" in zones

    def test_strategic_scenarios_endpoint(self):
        StrategicScenarioFactory()
        response = self.client.get("/api/v1/risks/ebios/strategic-scenarios/")
        assert response.status_code == 200

    def test_attack_path_steps_endpoint(self):
        AttackPathStepFactory()
        response = self.client.get("/api/v1/risks/ebios/attack-path-steps/")
        assert response.status_code == 200

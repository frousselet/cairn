"""Tests for the site operational lifecycle (standardised core.lifecycle engine).

Covers the registered schema, the governance flags, the model transitions, the
detail-page graph stepper, the lifecycle-aware DRF transition endpoint and the
MCP transition / allowed-transitions tools.
"""

import json

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.lifecycles import SITE_LIFECYCLE_NAME
from context.models import Site
from context.tests.factories import SiteFactory

pytestmark = pytest.mark.django_db


def _data(response):
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


# --- Schema -----------------------------------------------------------------


def test_site_lifecycle_schema():
    from core.lifecycle import get_lifecycle

    lc = get_lifecycle(SITE_LIFECYCLE_NAME)
    assert lc.layout == "graph"
    assert [s.code for s in lc.steps] == [
        "draft", "commissioning", "operational", "review", "decommissioned", "archived",
    ]
    assert lc.initial_step.code == "draft"
    # Operational and review are authoritative (count in reports + linkable);
    # only the draft entry is deletable.
    assert set(lc.reportable_step_codes) == {"operational", "review"}
    assert set(lc.linkable_step_codes) == {"operational", "review"}
    assert set(lc.deletable_step_codes) == {"draft"}


def test_site_lifecycle_transitions():
    from core.lifecycle import get_lifecycle

    lc = get_lifecycle(SITE_LIFECYCLE_NAME)
    assert {t.target for t in lc.transitions_from("draft")} == {"commissioning", "archived"}
    assert {t.target for t in lc.transitions_from("commissioning")} == {"operational", "archived"}
    assert {t.target for t in lc.transitions_from("operational")} == {
        "review", "decommissioned", "archived",
    }
    assert {t.target for t in lc.transitions_from("review")} == {"operational", "archived"}
    assert {t.target for t in lc.transitions_from("decommissioned")} == {"archived"}
    assert {t.target for t in lc.transitions_from("archived")} == {"draft"}


# --- Model governance -------------------------------------------------------


def test_new_site_starts_in_draft():
    site = SiteFactory()
    assert site.workflow_state == "draft"
    assert site.get_lifecycle().name == SITE_LIFECYCLE_NAME
    assert site.counts_in_reports is False
    assert site.is_linkable is False
    assert site.is_deletable is True


def test_operational_site_is_authoritative():
    site = SiteFactory(workflow_state="operational")
    assert site.counts_in_reports is True
    assert site.is_linkable is True
    assert site.is_deletable is False
    assert str(site.lifecycle_label) == "Operational"
    assert site.lifecycle_tone == "success"


def test_review_step_loops_back_to_operational():
    user = UserFactory()
    site = SiteFactory(workflow_state="operational")
    site.transition_to("review", user)
    assert site.workflow_state == "review"
    assert site.counts_in_reports is True
    site.transition_to("operational", user)
    assert site.workflow_state == "operational"


def test_operational_site_can_be_decommissioned():
    user = UserFactory()
    site = SiteFactory(workflow_state="operational")
    site.transition_to("decommissioned", user)
    assert site.workflow_state == "decommissioned"
    # A decommissioned site is no longer authoritative.
    assert site.counts_in_reports is False
    assert site.is_linkable is False


def test_site_transition_records_event():
    from core.models import LifecycleEvent

    user = UserFactory()
    site = SiteFactory()
    site.transition_to("commissioning", user)
    site.refresh_from_db()
    assert site.workflow_state == "commissioning"
    event = LifecycleEvent.for_instance(site).first()
    assert event.from_step == "draft"
    assert event.to_step == "commissioning"


def test_reportable_helper_uses_site_lifecycle():
    from core.lifecycle import reportable

    SiteFactory()  # draft
    SiteFactory(workflow_state="operational")
    SiteFactory(workflow_state="review")
    SiteFactory(workflow_state="commissioning")
    assert reportable(Site.objects.all()).count() == 2


# --- Detail-page stepper ----------------------------------------------------


def test_site_detail_renders_graph_stepper(client, django_user_model):
    from django.urls import reverse

    user = django_user_model.objects.create_superuser(email="lc@site.co", password="x")
    client.force_login(user)
    parent = SiteFactory(workflow_state="operational")
    site = SiteFactory(workflow_state="operational")
    SiteFactory(parent_site=site)  # a sub-site
    resp = client.get(reverse("assets:site-detail", kwargs={"pk": site.pk}))
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx["lc_enabled"] is True
    assert ctx["lc_layout"] == "graph"
    # Operational is the current step; review/decommission are reachable.
    state_by_value = {s["value"]: s["state"] for s in ctx["lc_steps"]}
    assert state_by_value["operational"] == "current"
    actionable = {s["value"] for s in ctx["lc_steps"] if s["actionable"]}
    assert {"review", "decommissioned"} <= actionable
    assert [e["value"] for e in ctx["lc_exits"]] == ["archived"]
    # Graph payload carries every step and the periodic review back-edge.
    node_ids = {n["id"] for n in json.loads(ctx["lc_graph_nodes"])}
    assert node_ids == {
        "draft", "commissioning", "operational", "review", "decommissioned", "archived",
    }
    edge_kinds = {(e["source"], e["target"], e["kind"]) for e in json.loads(ctx["lc_graph_edges"])}
    assert ("draft", "commissioning", "forward") in edge_kinds
    assert ("*", "archived", "exit") in edge_kinds
    assert ("archived", "draft", "restore") in edge_kinds
    loops = {(s, t) for s, t, kind in edge_kinds if kind == "loop"}
    assert loops == {("review", "operational")}
    # Rail context : sub-sites and dependency relations resolve.
    assert len(ctx["children"]) == 1
    assert len(ctx["asset_dependencies"]) == 0
    assert len(ctx["supplier_dependencies"]) == 0


# --- DRF transition endpoint (lifecycle-aware mixin) ------------------------


class TestSiteTransitionAPI:
    def setup_method(self):
        self.client = APIClient()
        self.superuser = UserFactory(is_superuser=True)

    def _url(self, site):
        return f"/api/v1/context/sites/{site.pk}/transition/"

    def test_get_lists_site_lifecycle_targets(self):
        self.client.force_authenticate(self.superuser)
        site = SiteFactory()
        response = self.client.get(self._url(site))
        assert response.status_code == 200
        payload = _data(response)
        assert payload["workflow"] == SITE_LIFECYCLE_NAME
        assert payload["workflow_state"] == "draft"
        targets = {t["target"] for t in payload["allowed_transitions"]}
        assert targets == {"commissioning", "archived"}

    def test_post_advances_site(self):
        self.client.force_authenticate(self.superuser)
        site = SiteFactory()
        response = self.client.post(
            self._url(site), {"target_state": "commissioning"}, format="json",
        )
        assert response.status_code == 200
        site.refresh_from_db()
        assert site.workflow_state == "commissioning"

    def test_post_illegal_transition_is_400(self):
        self.client.force_authenticate(self.superuser)
        site = SiteFactory()  # draft
        response = self.client.post(
            self._url(site), {"target_state": "operational"}, format="json",
        )
        assert response.status_code == 400
        site.refresh_from_db()
        assert site.workflow_state == "draft"


# --- MCP --------------------------------------------------------------------


class TestSiteMCPTransitions:
    def setup_method(self):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        self.srv = McpServer()
        register_all_tools(self.srv)
        self.superuser = UserFactory(is_superuser=True)

    def _call(self, user, name, arguments=None):
        result = self.srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }), user)
        return json.loads(result["result"]["content"][0]["text"])

    def test_transition_site_advances_step(self):
        site = SiteFactory()
        result = self._call(
            self.superuser, "transition_site",
            {"id": str(site.pk), "target_state": "commissioning"},
        )
        assert result["previous_state"] == "draft"
        assert result["workflow_state"] == "commissioning"
        site.refresh_from_db()
        assert site.workflow_state == "commissioning"

    def test_site_allowed_transitions_lists_lifecycle_targets(self):
        site = SiteFactory()
        result = self._call(
            self.superuser, "site_allowed_transitions", {"id": str(site.pk)},
        )
        assert result["workflow"] == SITE_LIFECYCLE_NAME
        targets = {t["target"] for t in result["allowed_transitions"]}
        assert targets == {"commissioning", "archived"}

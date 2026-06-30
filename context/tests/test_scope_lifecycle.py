"""Tests for the scope perimeter lifecycle (standardised core.lifecycle engine).

Covers the registered schema, the governance flags, the detail-page stepper
context, the generic transition endpoint, the engine-aware state badge and the
MCP transition / allowed-transitions tools.
"""

import json

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from context.lifecycles import SCOPE_LIFECYCLE_NAME
from context.models import Scope
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


# --- Schema -----------------------------------------------------------------


def test_scope_lifecycle_schema():
    from core.lifecycle import get_lifecycle

    lc = get_lifecycle(SCOPE_LIFECYCLE_NAME)
    assert lc.layout == "graph"
    assert [s.code for s in lc.steps] == [
        "draft", "definition", "validation", "in_force", "review", "archived",
    ]
    assert lc.initial_step.code == "draft"
    # The in-force and review steps are authoritative (count in reports +
    # linkable); only the draft entry is deletable.
    assert set(lc.reportable_step_codes) == {"in_force", "review"}
    assert set(lc.linkable_step_codes) == {"in_force", "review"}
    assert set(lc.deletable_step_codes) == {"draft"}


def test_scope_lifecycle_transitions():
    from core.lifecycle import get_lifecycle

    lc = get_lifecycle(SCOPE_LIFECYCLE_NAME)
    # A forward progression plus the in-force <-> review periodic loop, with
    # from-any archive; restore returns to the draft entry.
    assert {t.target for t in lc.transitions_from("draft")} == {"definition", "archived"}
    assert {t.target for t in lc.transitions_from("definition")} == {"validation", "archived"}
    assert {t.target for t in lc.transitions_from("validation")} == {"in_force", "archived"}
    assert {t.target for t in lc.transitions_from("in_force")} == {"review", "archived"}
    assert {t.target for t in lc.transitions_from("review")} == {"in_force", "archived"}
    assert {t.target for t in lc.transitions_from("archived")} == {"draft"}


# --- Model governance -------------------------------------------------------


def test_new_scope_starts_in_draft():
    scope = ScopeFactory()
    assert scope.workflow_state == "draft"
    assert scope.get_lifecycle().name == SCOPE_LIFECYCLE_NAME
    assert scope.counts_in_reports is False
    assert scope.is_linkable is False
    assert scope.is_deletable is True


def test_in_force_scope_is_authoritative():
    scope = ScopeFactory(workflow_state="in_force")
    assert scope.counts_in_reports is True
    assert scope.is_linkable is True
    assert scope.is_deletable is False
    assert str(scope.lifecycle_label) == "In force"
    assert scope.lifecycle_tone == "success"


def test_review_step_loops_back_to_in_force():
    user = UserFactory()
    scope = ScopeFactory(workflow_state="in_force")
    scope.transition_to("review", user)
    assert scope.workflow_state == "review"
    # A scope under review stays authoritative.
    assert scope.counts_in_reports is True
    assert scope.is_linkable is True
    # Completing the review returns to In force for the next cycle.
    scope.transition_to("in_force", user)
    assert scope.workflow_state == "in_force"


def test_scope_transition_records_event():
    from core.models import LifecycleEvent

    user = UserFactory()
    scope = ScopeFactory()
    scope.transition_to("definition", user)
    scope.refresh_from_db()
    assert scope.workflow_state == "definition"
    event = LifecycleEvent.for_instance(scope).first()
    assert event.from_step == "draft"
    assert event.to_step == "definition"


def test_in_force_scope_blocks_deletion():
    from core.lifecycle import LifecycleProtectedError

    scope = ScopeFactory(workflow_state="in_force")
    with pytest.raises(LifecycleProtectedError):
        scope.delete()
    assert Scope.objects.filter(pk=scope.pk).exists()


def test_reportable_helper_uses_scope_lifecycle():
    from core.lifecycle import linkable, reportable

    ScopeFactory()  # draft
    ScopeFactory(workflow_state="in_force")
    assert reportable(Scope.objects.all()).count() == 1
    assert linkable(Scope.objects.all()).count() == 1


def test_history_helpers_resolve_scope_lifecycle():
    """The unified history helpers read the scope lifecycle (engine-aware).

    The perimeter flow has no rework edge, so a backward move is never recorded;
    the helper still resolves the main-flow order and step labels off the
    lifecycle (not the legacy default workflow).
    """
    from core.history import _is_backward_transition, _state_label

    assert str(_state_label(Scope, "in_force")) == "In force"
    assert _is_backward_transition(Scope, "validation", "definition") is True
    assert _is_backward_transition(Scope, "definition", "validation") is False


# --- Detail-page stepper ----------------------------------------------------


def _superuser_client(client, django_user_model):
    user = django_user_model.objects.create_superuser(email="lc@scope.co", password="x")
    client.force_login(user)
    return client


def test_scope_detail_renders_graph_stepper(client, django_user_model):
    import json

    _superuser_client(client, django_user_model)
    scope = ScopeFactory()
    resp = client.get(reverse("context:scope-detail", kwargs={"pk": scope.pk}))
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx["lc_enabled"] is True
    # Routed through the schema-driven graph renderer (same as suppliers).
    assert ctx["lc_layout"] == "graph"
    # The four operational stages are numbered 1..4; the bookends stay unnumbered.
    number_by_value = {s["value"]: s.get("number") for s in ctx["lc_steps"]}
    assert number_by_value["definition"] == 1
    assert number_by_value["validation"] == 2
    assert number_by_value["in_force"] == 3
    assert number_by_value["review"] == 4
    assert number_by_value["draft"] is None
    # Draft is current; the next step (definition) is an available transition.
    state_by_value = {s["value"]: s["state"] for s in ctx["lc_steps"]}
    assert state_by_value["draft"] == "current"
    actionable = {s["value"] for s in ctx["lc_steps"] if s["actionable"]}
    assert "definition" in actionable
    # Archived is the detached exit.
    assert [e["value"] for e in ctx["lc_exits"]] == ["archived"]
    # The graph payload carries every step and the from-any / restore edges.
    node_ids = {n["id"] for n in json.loads(ctx["lc_graph_nodes"])}
    assert node_ids == {"draft", "definition", "validation", "in_force", "review", "archived"}
    edge_kinds = {(e["source"], e["target"], e["kind"]) for e in json.loads(ctx["lc_graph_edges"])}
    assert ("draft", "definition", "forward") in edge_kinds
    assert ("in_force", "review", "forward") in edge_kinds
    assert ("*", "archived", "exit") in edge_kinds
    assert ("archived", "draft", "restore") in edge_kinds
    # The periodic review loops back to In force (the only loop back-edge).
    loops = {(s, t) for s, t, kind in edge_kinds if kind == "loop"}
    assert loops == {("review", "in_force")}
    # The rich graph component (not the plain pill stepper) is the markup rendered.
    html = resp.content.decode()
    assert "data-lc-svg" in html
    assert 'class="stepper stepper--wrap"' not in html
    # Strategic KPI tiles feed the rail (relations resolve; empty perimeter).
    assert ctx["kpi_compliance_rate"] is None  # no scoped frameworks
    assert ctx["kpi_objectives"] == 0
    assert ctx["kpi_essential_assets"] == 0


def test_scope_map_plots_descendant_scope_sites(client, django_user_model):
    """The hero map payload covers the scope's own sites plus its sub-scopes'."""
    from context.tests.factories import SiteFactory

    _superuser_client(client, django_user_model)
    root = ScopeFactory()
    child = ScopeFactory(parent_scope=root)
    grandchild = ScopeFactory(parent_scope=child)

    own = SiteFactory(name="Own", address="1 rue A, Lyon")
    sub = SiteFactory(name="Sub", address="2 rue B, Paris")
    deep = SiteFactory(name="Deep", address="3 rue C, Lille")
    no_addr = SiteFactory(name="NoAddr", address="")
    root.included_sites.add(own)
    child.included_sites.add(sub, no_addr)
    grandchild.included_sites.add(deep)

    resp = client.get(reverse("context:scope-detail", kwargs={"pk": root.pk}))
    assert resp.status_code == 200
    ctx = resp.context
    # The "Included sites" badges stay the scope's own direct sites only.
    assert list(ctx["included_sites"]) == [own]
    # The map footprint aggregates own + descendant sites that have an address.
    map_names = {s["name"] for s in json.loads(ctx["scope_sites_json"])}
    assert map_names == {"Own", "Sub", "Deep"}
    assert ctx["has_site_map"] is True


def test_scope_get_descendants_breadth_first():
    root = ScopeFactory()
    child_a = ScopeFactory(parent_scope=root)
    child_b = ScopeFactory(parent_scope=root)
    grandchild = ScopeFactory(parent_scope=child_a)
    descendants = set(root.get_descendants())
    assert descendants == {child_a, child_b, grandchild}
    # A leaf scope has no descendants.
    assert grandchild.get_descendants() == []


def test_scope_with_stale_step_renders_gracefully(client, django_user_model):
    _superuser_client(client, django_user_model)
    scope = ScopeFactory()
    Scope.objects.filter(pk=scope.pk).update(workflow_state="ghost")
    resp = client.get(reverse("context:scope-detail", kwargs={"pk": scope.pk}))
    assert resp.status_code == 200
    states = {s["value"]: s["state"] for s in resp.context["lc_steps"]}
    assert "current" not in states.values()


# --- Transition endpoint ----------------------------------------------------


def test_transition_endpoint_advances_scope(client, django_user_model):
    _superuser_client(client, django_user_model)
    scope = ScopeFactory()
    url = reverse(
        "workflow:transition",
        kwargs={"app_label": "context", "model": "scope", "pk": scope.pk},
    )
    resp = client.post(url, {"target_status": "definition"})
    assert resp.status_code == 302
    scope.refresh_from_db()
    assert scope.workflow_state == "definition"


def test_transition_endpoint_can_archive_from_any_step(client, django_user_model):
    _superuser_client(client, django_user_model)
    scope = ScopeFactory()  # draft
    url = reverse(
        "workflow:transition",
        kwargs={"app_label": "context", "model": "scope", "pk": scope.pk},
    )
    resp = client.post(url, {"target_status": "archived"})
    assert resp.status_code == 302
    scope.refresh_from_db()
    assert scope.workflow_state == "archived"


# --- Badge ------------------------------------------------------------------


def test_scope_badge_renders_step_label_and_tone():
    from helpers.templatetags.workflow_tags import workflow_badge

    scope = ScopeFactory(workflow_state="in_force")
    ctx = workflow_badge(scope)
    assert str(ctx["label"]) == "In force"
    assert ctx["badge_class"] == "success"


# --- MCP --------------------------------------------------------------------


class TestScopeMCPTransitions:
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

    def test_transition_scope_advances_step(self):
        scope = ScopeFactory()
        result = self._call(
            self.superuser, "transition_scope",
            {"id": str(scope.pk), "target_state": "definition"},
        )
        assert result["previous_state"] == "draft"
        assert result["workflow_state"] == "definition"
        scope.refresh_from_db()
        assert scope.workflow_state == "definition"

    def test_scope_allowed_transitions_lists_lifecycle_targets(self):
        scope = ScopeFactory()
        result = self._call(
            self.superuser, "scope_allowed_transitions", {"id": str(scope.pk)},
        )
        assert result["workflow"] == SCOPE_LIFECYCLE_NAME
        targets = {t["target"] for t in result["allowed_transitions"]}
        assert targets == {"definition", "archived"}

    def test_transition_scope_rejects_illegal_step(self):
        scope = ScopeFactory()  # draft
        result = self._call(
            self.superuser, "transition_scope",
            {"id": str(scope.pk), "target_state": "in_force"},
        )
        assert "error" in result
        scope.refresh_from_db()
        assert scope.workflow_state == "draft"

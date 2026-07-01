import json

import pytest
from django.urls import reverse

from assets.tests.factories import SupplierFactory


@pytest.mark.django_db
def test_supplier_detail_emits_schema_driven_graph(client, django_user_model):
    user = django_user_model.objects.create_superuser(
        email="a@b.co", password="x"
    )
    client.force_login(user)
    supplier = SupplierFactory()
    resp = client.get(reverse("assets:supplier-detail", kwargs={"pk": supplier.pk}))
    assert resp.status_code == 200
    ctx = resp.context

    assert ctx["lc_layout"] == "graph"
    node_ids = {n["id"] for n in json.loads(ctx["lc_graph_nodes"])}
    # every schema step is present (draft + 6 stages + archived)
    for code in [
        "draft", "integration", "risk_questionnaire", "evaluation",
        "compliant", "non_compliant", "compensatory_measures", "archived",
    ]:
        assert code in node_ids

    # The terminal branch pair is numbered 4a / 4b, the spine 1..3, and the
    # remediation step 5; the entry / exit bookends stay unnumbered.
    number_by_id = {s["value"]: s.get("number") for s in ctx["lc_steps"]}
    assert number_by_id["integration"] == 1
    assert number_by_id["risk_questionnaire"] == 2
    assert number_by_id["evaluation"] == 3
    assert number_by_id["compliant"] == "4a"
    assert number_by_id["non_compliant"] == "4b"
    assert number_by_id["compensatory_measures"] == 5
    assert number_by_id["draft"] is None

    edges = json.loads(ctx["lc_graph_edges"])
    kinds = {(e["source"], e["target"], e["kind"]) for e in edges}
    # The entry path + the binary branch divergence + the remediation feed are forward.
    assert ("draft", "integration", "forward") in kinds
    assert ("integration", "risk_questionnaire", "forward") in kinds
    assert ("risk_questionnaire", "evaluation", "forward") in kinds
    assert ("evaluation", "compliant", "forward") in kinds
    assert ("evaluation", "non_compliant", "forward") in kinds
    assert ("non_compliant", "compensatory_measures", "forward") in kinds
    # Compliant loops to the questionnaire (2); compensatory measures loop to
    # the evaluation (3) for re-assessment.
    assert ("compliant", "risk_questionnaire", "loop") in kinds
    assert ("compensatory_measures", "evaluation", "loop") in kinds
    # from-any archive exit + restore are represented.
    assert ("*", "archived", "exit") in kinds
    assert ("archived", "draft", "restore") in kinds


@pytest.mark.django_db
def test_supplier_lifecycle_graph_uses_dagre_renderer(client, django_user_model):
    """The lifecycle graph is rendered with the dagre (layered) renderer.

    The whole diagram is derived from the emitted node / edge JSON and laid out
    by dagre, so arrows are routed and never overlap whatever the flow's shape.
    Guards against regressing to a hand-rolled flow layout.
    """
    user = django_user_model.objects.create_superuser(email="c@d.co", password="x")
    client.force_login(user)
    supplier = SupplierFactory()
    resp = client.get(reverse("assets:supplier-detail", kwargs={"pk": supplier.pk}))
    html = resp.content.decode()

    # The dagre container + the data-driven node / edge payload it lays out.
    assert "lc-dagre" in html
    assert "data-lc-nodes" in html
    assert "data-lc-edges" in html
    # The layered-layout library is loaded (vendored, no CDN).
    assert "dagre" in html


@pytest.mark.django_db
def test_supplier_with_stale_legacy_step_renders_gracefully(client, django_user_model):
    """A supplier left on a dropped legacy step code must not crash the page.

    Migration 0039 remaps legacy codes (onboarding / risk_scoring / ...) onto the
    new branching lifecycle, but a row that slipped through (or arrives via the
    API) with a code that is not a step of the current lifecycle must still
    render at HTTP 200 with a graceful all-future graph - never an UnknownStepError.
    """
    user = django_user_model.objects.create_superuser(email="e@f.co", password="x")
    client.force_login(user)
    supplier = SupplierFactory()
    # Write a code that no longer exists as a step of the supplier lifecycle.
    type(supplier).objects.filter(pk=supplier.pk).update(workflow_state="onboarding")
    resp = client.get(reverse("assets:supplier-detail", kwargs={"pk": supplier.pk}))
    assert resp.status_code == 200
    # Stale code is not on the spine, so no step is "current" : all future.
    states = {s["value"]: s["state"] for s in resp.context["lc_steps"]}
    assert "current" not in states.values()

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Scope tenancy must hold on every surface, including for child rows.

A model that inherits its scopes from a parent (`scope_parent_lookup`) used
to be filtered only on list and detail surfaces. The generic workflow
transition endpoint, the generic history endpoint and the MCP list layer all
guarded on the presence of a `scopes` M2M, which a child row does not have,
and fell through to returning everything. These tests pin the three.
"""
import pytest
from django.urls import reverse

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from context.tests.factories import ScopeFactory
from core.scoping import object_in_scopes, resolve_scope_lookup


def _user_limited_to(scope, *codenames):
    """A non-superuser whose only group restricts them to `scope`.

    Allowed scopes come from group membership : a group with an empty
    `allowed_scopes` means unrestricted, so the group must name the scope.
    `codenames` are granted so a test reaches the scope guard instead of
    stopping at the permission check before it.
    """
    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.allowed_scopes.set([scope])
    for codename in codenames:
        group.permissions.add(PermissionFactory(codename=codename))
    group.users.add(user)
    return user


@pytest.fixture
def two_perimeters(db):
    """A requirement in each of two disjoint scopes, and a user seeing only one."""
    mine, theirs = ScopeFactory(), ScopeFactory()
    fw_mine = FrameworkFactory()
    fw_mine.scopes.set([mine])
    fw_theirs = FrameworkFactory()
    fw_theirs.scopes.set([theirs])
    return {
        "mine": mine,
        "theirs": theirs,
        "req_mine": RequirementFactory(framework=fw_mine),
        "req_theirs": RequirementFactory(framework=fw_theirs),
    }


def test_child_model_declares_its_path_to_scope():
    from compliance.models import Requirement

    assert resolve_scope_lookup(Requirement) == "framework__scopes"


@pytest.mark.django_db
def test_object_in_scopes_follows_the_parent(two_perimeters):
    mine = [two_perimeters["mine"].id]

    assert object_in_scopes(two_perimeters["req_mine"], mine)
    assert not object_in_scopes(two_perimeters["req_theirs"], mine)


@pytest.mark.django_db
def test_a_row_with_no_scope_at_all_stays_visible(two_perimeters):
    """Scoping restricts what has been filed under a perimeter.

    It does not hide records nobody has filed yet, which is the behaviour the
    previous guard had and which this must not silently change.
    """
    orphan = RequirementFactory(framework=FrameworkFactory())
    orphan.framework.scopes.clear()

    assert object_in_scopes(orphan, [two_perimeters["mine"].id])


@pytest.mark.django_db
def test_mcp_list_does_not_leak_child_rows_across_scopes(two_perimeters):
    from mcp.tools import _filter_by_scopes
    from compliance.models import Requirement

    user = _user_limited_to(two_perimeters["mine"])

    visible = _filter_by_scopes(Requirement.objects.all(), user)

    assert two_perimeters["req_mine"] in visible
    assert two_perimeters["req_theirs"] not in visible


@pytest.mark.django_db
def test_history_endpoint_refuses_an_out_of_scope_child(client, two_perimeters):
    # The read permission is granted on purpose : without it the view returns
    # 403 before it ever reaches the scope guard, and the test proves nothing.
    user = _user_limited_to(two_perimeters["mine"], "compliance.requirement.read")
    client.force_login(user)

    url = reverse(
        "history:partial",
        kwargs={
            "app_label": "compliance",
            "model": "requirement",
            "pk": two_perimeters["req_theirs"].pk,
        },
    )

    assert client.get(url).status_code == 404

    ours = reverse(
        "history:partial",
        kwargs={
            "app_label": "compliance",
            "model": "requirement",
            "pk": two_perimeters["req_mine"].pk,
        },
    )
    assert client.get(ours).status_code == 200


@pytest.mark.django_db
def test_workflow_transition_refuses_an_out_of_scope_child(client, two_perimeters):
    user = _user_limited_to(two_perimeters["mine"])
    client.force_login(user)

    url = reverse(
        "workflow:transition",
        kwargs={
            "app_label": "compliance",
            "model": "requirement",
            "pk": two_perimeters["req_theirs"].pk,
        },
    )
    before = two_perimeters["req_theirs"].workflow_state

    response = client.post(url, {"target_status": "pending"})

    two_perimeters["req_theirs"].refresh_from_db()
    assert response.status_code == 404
    assert two_perimeters["req_theirs"].workflow_state == before


@pytest.mark.django_db
class TestAlternateScopeParents:
    """A finding raised by an incident or a control test is filed under that
    parent's scopes (``scope_parent_alternates``), not visible to everyone."""

    def test_finding_follows_its_incident_or_control_scopes(self):
        from compliance.constants import FindingSource, FindingType
        from compliance.models import Finding
        from context.tests.factories import ScopeFactory
        from controls.tests.factories import validated_run
        from core.scoping import filter_queryset_by_scopes, object_in_scopes
        from incidents.tests.factories import IncidentFactory

        mine, other = ScopeFactory(), ScopeFactory()
        incident = IncidentFactory()
        incident.scopes.add(other)
        run = validated_run(result="fail")
        run.test.control.scopes.add(mine)
        from_incident = Finding.objects.create(
            source=FindingSource.INCIDENT, incident=incident,
            finding_type=FindingType.OBSERVATION, description="From the incident.",
        )
        from_run = Finding.objects.create(
            source=FindingSource.CONTROL_TEST, control_test_run=run,
            finding_type=FindingType.OBSERVATION, description="From the test.",
        )
        orphan = Finding.objects.create(
            source=FindingSource.MONITORING, finding_type=FindingType.OBSERVATION, description="Unfiled.",
        )
        visible = set(filter_queryset_by_scopes(Finding.objects.all(), [mine.pk]).values_list("pk", flat=True))
        assert visible == {from_run.pk, orphan.pk}
        assert object_in_scopes(from_run, [mine.pk])
        assert not object_in_scopes(from_incident, [mine.pk])
        assert object_in_scopes(orphan, [mine.pk])


# ── Every way a record is reached checks the scopes ─────────────────────────
#
# A permission says what a user may do, their scopes on which records. Views
# used to check the first and fetch by identifier : a user restricted to one
# scope, holding the delete permission, could delete the records of another
# by their address, and the whole EBIOS RM API listed every assessment's rows.
# The structural tests below make forgetting the scope a failure, whichever
# surface is added next; the behavioural ones pin each family that was open.


def _routes():
    from django.urls import get_resolver

    def walk(patterns):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern.url_patterns)
            else:
                yield pattern.callback

    return list(walk(get_resolver().url_patterns))


def _member_of_one_scope(scope):
    """A user restricted to `scope` who holds every permission.

    With every permission granted, a refusal can only come from the scopes :
    the tests below never stop at a permission check before reaching them.
    """
    from accounts.models import Permission

    user = UserFactory(is_superuser=False)
    group = GroupFactory()
    group.allowed_scopes.set([scope])
    group.permissions.set(Permission.objects.all())
    group.users.add(user)
    return user


# A single-record view that does not go through PermissionRequiredMixin, and
# why its record needs no scope check.
SINGLE_RECORD_VIEWS_WITHOUT_THE_GUARD = {
    "core.lifecycle_admin_views.LifecycleDefinitionUpdateView": "an instance-wide lifecycle definition, no scope",
    "documents.views.AcknowledgeView": "the addressee acknowledges their own notice (checked by the model)",
}


def test_every_single_record_view_checks_the_scopes():
    """A detail, update or delete view fetches through the scope guard.

    The guard is `PermissionRequiredMixin.get_object` : the mixin must come
    before the generic view in the method resolution order, and no class in
    between may replace `get_object` without it.
    """
    from django.views.generic.detail import SingleObjectMixin

    from accounts.views import PermissionRequiredMixin

    unguarded = []
    for callback in _routes():
        cls = getattr(callback, "view_class", None)
        if cls is None or not issubclass(cls, SingleObjectMixin):
            continue
        name = f"{cls.__module__}.{cls.__name__}"
        if name in SINGLE_RECORD_VIEWS_WITHOUT_THE_GUARD:
            continue
        mro = cls.__mro__
        guarded = PermissionRequiredMixin in mro and mro.index(PermissionRequiredMixin) < mro.index(SingleObjectMixin)
        if guarded:
            # The first get_object found must be the guard itself.
            owner = next(c for c in mro if "get_object" in vars(c))
            guarded = owner is PermissionRequiredMixin
        if not guarded:
            unguarded.append(name)
    assert sorted(set(unguarded)) == []


# A model that hangs under a scoped record and is left without a path to the
# scopes on purpose, and why.
UNSCOPED_ON_PURPOSE = {
    "trust_center.DocumentRequest": "the Trust Center is one publication for the whole instance",
    "trust_center.TrustCenterCertification": "the Trust Center is one publication for the whole instance",
    "trust_center.TrustCenterDocument": "the Trust Center is one publication for the whole instance",
    "trust_center.TrustCenterSubprocessor": "the Trust Center is one publication for the whole instance",
}


def test_every_child_of_a_scoped_record_declares_its_path():
    """A model with a parent filed under scopes says how it reaches them.

    Without `scope_parent_lookup` the generic endpoints (transition, history),
    the MCP server and the list mixins find no path and filter nothing : the
    rows of every scope are served to everyone holding the permission.
    """
    from django.apps import apps
    from django.db import models

    ours = {
        "accounts", "assets", "assistant", "compliance", "context", "controls", "core",
        "documents", "incidents", "reports", "risks", "trust_center",
    }
    undeclared = []
    for model in apps.get_models():
        label = model._meta.label
        if model._meta.app_label not in ours or model.__name__.startswith("Historical"):
            continue
        if resolve_scope_lookup(model) or label in UNSCOPED_ON_PURPOSE:
            continue
        for field in model._meta.get_fields():
            if not isinstance(field, (models.ForeignKey, models.OneToOneField)):
                continue
            parent = field.related_model
            if parent is model or parent._meta.app_label not in ours:
                continue
            if resolve_scope_lookup(parent) and parent._meta.label not in UNSCOPED_ON_PURPOSE:
                undeclared.append(f"{label} (through {field.name})")
                break
    assert sorted(undeclared) == []


# An API class serving a scoped model that restricts it by its own rule.
API_CLASSES_SCOPED_ANOTHER_WAY = {
    "documents.api.views.PolicyAcknowledgementViewSet": "a notice is readable by its addressee or within the scopes (RG-DOC-22)",
}


def test_every_api_class_serving_a_scoped_model_filters_on_the_scopes():
    from accounts.api.mixins import ScopeFilterAPIMixin

    unguarded = []
    for callback in _routes():
        cls = getattr(callback, "cls", None)
        if cls is None:
            continue
        queryset = getattr(cls, "queryset", None)
        model = queryset.model if queryset is not None else getattr(
            getattr(getattr(cls, "serializer_class", None), "Meta", None), "model", None,
        )
        if model is None or not resolve_scope_lookup(model):
            continue
        name = f"{cls.__module__}.{cls.__name__}"
        if ScopeFilterAPIMixin in cls.__mro__ or name in API_CLASSES_SCOPED_ANOTHER_WAY:
            continue
        unguarded.append(name)
    assert sorted(set(unguarded)) == []


# Modules allowed to call Django's own get_object_or_404, and why.
UNSCOPED_FETCH_ALLOWED = {
    "accounts/views.py": "users, groups and tokens : administration, no scope",
    "accounts/views_passkey.py": "a passkey is fetched for its own user",
    "assistant/views.py": "assistant feedback : instance-wide triage",
    "controls/views.py": "one helper, over a queryset restricted to the scopes",
    "core/history_views.py": "generic endpoint, checks object_in_scopes after the fetch",
    "core/lifecycle_admin_views.py": "lifecycle definitions : administration, no scope",
    "core/scoping.py": "the scoped helper itself",
    "core/workflow_views.py": "generic endpoint, checks object_in_scopes after the fetch",
    "documents/views.py": "one helper, over a queryset restricted to the scopes",
    "incidents/views.py": "one helper, over a queryset restricted to the scopes",
    "trust_center/admin_views.py": "the Trust Center is one publication for the whole instance",
    "trust_center/views.py": "public pages, fetched by their own publication rules",
}


def test_views_fetch_records_through_the_scoped_helper():
    """No view module fetches a record with the unscoped `get_object_or_404`.

    `core.scoping.get_scoped_object_or_404` is the way : it is the same call
    with the user in front, and it refuses a record of another scope.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    offenders = []
    for path in sorted(root.glob("*/**/*.py")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith((".venv/", "node_modules/")) or "/tests/" in rel or "/migrations/" in rel:
            continue
        if rel in UNSCOPED_FETCH_ALLOWED:
            continue
        source = path.read_text(encoding="utf-8")
        if "get_object_or_404" not in source:
            continue
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "get_object_or_404":
                offenders.append(f"{rel}:{node.lineno}")
    assert offenders == []


@pytest.fixture
def two_scopes(db):
    mine, theirs = ScopeFactory(), ScopeFactory()
    return {"mine": mine, "theirs": theirs, "user": _member_of_one_scope(mine)}


@pytest.mark.django_db
class TestRecordsOfAnotherScope:
    """What a user restricted to one scope may do to the records of another : nothing."""

    def test_a_delete_view_refuses_them(self, client, two_scopes):
        from context.models import Issue
        from context.tests.factories import IssueFactory

        theirs = IssueFactory()
        theirs.scopes.set([two_scopes["theirs"]])
        mine = IssueFactory()
        mine.scopes.set([two_scopes["mine"]])
        client.force_login(two_scopes["user"])

        url = reverse("context:issue-delete", kwargs={"pk": theirs.pk})
        assert client.get(url).status_code == 404
        assert client.post(url).status_code == 404
        assert Issue.objects.filter(pk=theirs.pk).exists()

        # The same act on a record of the user's own scope still works.
        assert client.post(reverse("context:issue-delete", kwargs={"pk": mine.pk})).status_code == 302
        assert not Issue.objects.filter(pk=mine.pk).exists()

    def test_a_scope_they_are_not_given_can_be_neither_edited_nor_deleted(self, client, two_scopes):
        client.force_login(two_scopes["user"])
        theirs = two_scopes["theirs"]

        assert client.get(reverse("context:scope-update", kwargs={"pk": theirs.pk})).status_code == 404
        assert client.post(
            reverse("context:scope-update", kwargs={"pk": theirs.pk}),
            {"name": "Taken over", "description": "x"},
        ).status_code == 404
        assert client.post(reverse("context:scope-delete", kwargs={"pk": theirs.pk})).status_code == 404
        theirs.refresh_from_db()
        assert theirs.name != "Taken over"
        assert client.get(reverse("context:scope-update", kwargs={"pk": two_scopes["mine"].pk})).status_code == 200

    def test_a_row_cannot_be_added_under_them(self, client, two_scopes):
        from context.models import SwotItem
        from context.tests.factories import SwotAnalysisFactory

        analysis = SwotAnalysisFactory()
        analysis.scopes.set([two_scopes["theirs"]])
        client.force_login(two_scopes["user"])

        url = reverse("context:swot-item-create", kwargs={"analysis_pk": analysis.pk})
        assert client.get(url).status_code == 404
        assert client.post(url, {"quadrant": "strength", "description": "x", "impact_level": "medium"}).status_code == 404
        assert not SwotItem.objects.filter(swot_analysis=analysis).exists()

    def test_a_visitor_not_signed_in_is_sent_to_the_login(self, client, two_scopes):
        """Fetching the parent before the login check must not turn into a 404."""
        from context.tests.factories import SwotAnalysisFactory

        analysis = SwotAnalysisFactory()
        response = client.get(reverse("context:swot-item-create", kwargs={"analysis_pk": analysis.pk}))

        assert response.status_code == 302
        assert response["Location"].startswith("/accounts/login/")

    def test_the_generic_transition_follows_the_parent_of_a_risk(self, client, two_scopes):
        """A risk is filed under the scopes of its assessment."""
        from risks.tests.factories import RiskAssessmentFactory, RiskFactory

        assessment = RiskAssessmentFactory()
        assessment.scopes.set([two_scopes["theirs"]])
        risk = RiskFactory(assessment=assessment)
        before = risk.workflow_state
        client.force_login(two_scopes["user"])

        url = reverse("workflow:transition", kwargs={"app_label": "risks", "model": "risk", "pk": risk.pk})
        target = next(iter(t.target for t in risk.available_transitions()), "archived")

        assert client.post(url, {"target_status": target}).status_code == 404
        risk.refresh_from_db()
        assert risk.workflow_state == before

    def test_the_mcp_server_does_not_list_the_risks_of_another_scope(self, two_scopes):
        from mcp.tools import _filter_by_scopes
        from risks.models import Risk
        from risks.tests.factories import RiskAssessmentFactory, RiskFactory

        ours, theirs = RiskAssessmentFactory(), RiskAssessmentFactory()
        ours.scopes.set([two_scopes["mine"]])
        theirs.scopes.set([two_scopes["theirs"]])
        risk_ours, risk_theirs = RiskFactory(assessment=ours), RiskFactory(assessment=theirs)

        visible = _filter_by_scopes(Risk.objects.all(), two_scopes["user"])

        assert risk_ours in visible
        assert risk_theirs not in visible


@pytest.mark.django_db
class TestApiRecordsOfAnotherScope:
    def _api(self, user):
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user)
        return api

    def test_a_list_holds_the_rows_of_the_user_scopes_only(self, two_scopes):
        from context.tests.factories import SiteFactory
        from risks.tests.factories import EbiosAssessmentFactory, RiskSourceFactory

        site_ours, site_theirs = SiteFactory(), SiteFactory()
        site_ours.scopes.set([two_scopes["mine"]])
        site_theirs.scopes.set([two_scopes["theirs"]])
        ours, theirs = EbiosAssessmentFactory(), EbiosAssessmentFactory()
        ours.scopes.set([two_scopes["mine"]])
        theirs.scopes.set([two_scopes["theirs"]])
        source_ours, source_theirs = RiskSourceFactory(assessment=ours), RiskSourceFactory(assessment=theirs)
        api = self._api(two_scopes["user"])

        sites = {row["id"] for row in api.get("/api/v1/context/sites/").json()["data"]}
        sources = {row["id"] for row in api.get("/api/v1/risks/ebios/risk-sources/").json()["data"]}

        assert sites == {str(site_ours.pk)}
        assert sources == {str(source_ours.pk)}
        assert api.get(f"/api/v1/context/sites/{site_theirs.pk}/").status_code == 404
        assert api.get(f"/api/v1/risks/ebios/risk-sources/{source_theirs.pk}/").status_code == 404
        assert api.delete(f"/api/v1/risks/ebios/risk-sources/{source_theirs.pk}/").status_code == 404

    def test_a_nested_resource_is_closed_with_its_parent(self, two_scopes):
        """The parent named by the URL is fetched within the scopes first."""
        from compliance.models import AssessmentResult
        from compliance.tests.factories import ComplianceAssessmentFactory

        theirs = ComplianceAssessmentFactory()
        theirs.scopes.set([two_scopes["theirs"]])
        ours = ComplianceAssessmentFactory()
        ours.scopes.set([two_scopes["mine"]])
        requirement = RequirementFactory(framework=FrameworkFactory())
        api = self._api(two_scopes["user"])
        url = f"/api/v1/compliance/assessments/{theirs.pk}/results/"

        assert api.get(url).status_code == 404
        created = api.post(url, {"requirement": str(requirement.pk)}, format="json")
        assert created.status_code == 404
        assert not AssessmentResult.objects.filter(assessment=theirs).exists()
        assert api.get(f"/api/v1/compliance/assessments/{ours.pk}/results/").status_code == 200

    def test_a_statement_of_applicability_is_not_made_from_their_frameworks(self, two_scopes):
        from reports.models import Report

        framework = FrameworkFactory()
        framework.scopes.set([two_scopes["theirs"]])
        api = self._api(two_scopes["user"])

        response = api.post(
            "/api/v1/reports/reports/generate-soa/", {"framework_ids": [str(framework.pk)]}, format="json",
        )

        assert response.status_code == 400
        assert not Report.objects.exists()


@pytest.mark.django_db
class TestNarrowScopeIds:
    """A report covers what its author may reach."""

    def test_a_restricted_user_who_asks_for_nothing_gets_their_own_scopes(self, two_scopes):
        from core.scoping import narrow_scope_ids

        assert narrow_scope_ids(two_scopes["user"]) == [two_scopes["mine"].id]

    def test_the_scopes_asked_for_are_narrowed_to_theirs(self, two_scopes):
        from core.scoping import narrow_scope_ids

        asked = [two_scopes["mine"].id, two_scopes["theirs"].id]

        assert narrow_scope_ids(two_scopes["user"], asked) == [two_scopes["mine"].id]
        # Nothing of what was asked is theirs : an empty selection, not "no limit".
        assert narrow_scope_ids(two_scopes["user"], [two_scopes["theirs"].id]) == []

    def test_a_user_no_group_restricts_gets_what_was_asked(self, two_scopes):
        from core.scoping import narrow_scope_ids

        free = UserFactory(is_superuser=True)

        assert narrow_scope_ids(free) is None
        assert narrow_scope_ids(free, [two_scopes["theirs"].id]) == [two_scopes["theirs"].id]

    def test_a_management_review_holds_the_data_of_the_author_scopes(self, two_scopes):
        from context.tests.factories import IssueFactory
        from reports.management_review import gather_management_review_data

        ours, theirs = IssueFactory(name="Ours to see"), IssueFactory(name="Theirs to keep")
        ours.scopes.set([two_scopes["mine"]])
        theirs.scopes.set([two_scopes["theirs"]])

        data = gather_management_review_data(two_scopes["user"])
        text = repr(data)

        assert "Theirs to keep" not in text

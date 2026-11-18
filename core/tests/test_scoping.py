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
        """Through the tool itself : the helper was right while the tool did not call it."""
        from risks.tests.factories import RiskAssessmentFactory, RiskFactory

        ours, theirs = RiskAssessmentFactory(), RiskAssessmentFactory()
        ours.scopes.set([two_scopes["mine"]])
        theirs.scopes.set([two_scopes["theirs"]])
        risk_ours, risk_theirs = RiskFactory(assessment=ours), RiskFactory(assessment=theirs)

        listed = _mcp_call(two_scopes["user"], "list_risks", {})

        assert [row["id"] for row in listed["items"]] == [str(risk_ours.pk)]
        assert "error" in _mcp_call(two_scopes["user"], "get_risk", {"id": str(risk_theirs.pk)})
        assert _mcp_call(two_scopes["user"], "get_risk", {"id": str(risk_ours.pk)})["id"] == str(risk_ours.pk)


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


# ── Relations : what a user may point a record at ───────────────────────────

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def two_assets(two_scopes):
    """A support and an essential asset in each scope."""
    from assets.tests.factories import EssentialAssetFactory, SupportAssetFactory

    made = {}
    for key in ("mine", "theirs"):
        support = SupportAssetFactory(name=f"SUPPORT-{key.upper()}")
        support.scopes.set([two_scopes[key]])
        essential = EssentialAssetFactory(name=f"ESSENTIAL-{key.upper()}")
        essential.scopes.set([two_scopes[key]])
        made[key] = {"support": support, "essential": essential}
    return {**two_scopes, "assets": made}


@pytest.mark.django_db
class TestSelectable:
    """`selectable` : what the registers show the user, plus what the record holds."""

    def test_a_restricted_user_selects_within_their_scopes(self, two_assets):
        from assets.models import SupportAsset
        from core.scoping import selectable

        names = set(selectable(two_assets["user"], SupportAsset.objects.all()).values_list("name", flat=True))

        assert names == {"SUPPORT-MINE"}

    def test_what_the_record_already_holds_stays(self, two_assets):
        from assets.models import SupportAsset
        from core.scoping import selectable

        theirs = two_assets["assets"]["theirs"]["support"]

        names = set(
            selectable(two_assets["user"], SupportAsset.objects.all(), keep=[theirs.pk]).values_list("name", flat=True)
        )

        assert names == {"SUPPORT-MINE", "SUPPORT-THEIRS"}

    def test_a_user_nothing_restricts_selects_everything(self, two_assets):
        from assets.models import SupportAsset
        from core.scoping import selectable

        everywhere = UserFactory()
        GroupFactory().users.add(everywhere)  # a group that names no scope restricts nothing
        for user in (UserFactory(is_superuser=True), everywhere):
            assert selectable(user, SupportAsset.objects.all()).count() == 2

    def test_a_user_in_no_group_selects_nothing(self, two_assets):
        """No group, no scope : the safe side."""
        from assets.models import SupportAsset
        from core.scoping import selectable

        assert selectable(UserFactory(), SupportAsset.objects.all()).count() == 0

    def test_a_visitor_selects_nothing(self, two_assets):
        from django.contrib.auth.models import AnonymousUser

        from assets.models import SupportAsset
        from core.scoping import selectable

        assert selectable(AnonymousUser(), SupportAsset.objects.all()).count() == 0

    def test_a_model_with_no_path_to_the_scopes_is_left_alone(self, two_assets):
        from accounts.models import User
        from core.scoping import selectable

        queryset = User.objects.all()

        assert selectable(two_assets["user"], queryset) is queryset


@pytest.mark.django_db
class TestFormsOfferWhatTheUserMaySelect:
    def test_a_select_does_not_name_the_records_of_another_scope(self, client, two_assets):
        client.force_login(two_assets["user"])

        html = client.get(reverse("assets:dependency-create"), **DRAWER).content.decode()

        assert "SUPPORT-MINE" in html and "ESSENTIAL-MINE" in html
        assert "SUPPORT-THEIRS" not in html and "ESSENTIAL-THEIRS" not in html

    def test_a_record_of_another_scope_cannot_be_chosen(self, client, two_assets):
        from assets.models import AssetDependency

        client.force_login(two_assets["user"])
        mine, theirs = two_assets["assets"]["mine"], two_assets["assets"]["theirs"]

        response = client.post(
            reverse("assets:dependency-create"),
            {"essential_asset": str(theirs["essential"].pk), "support_asset": str(mine["support"].pk),
             "dependency_type": "runs_on", "criticality": "high", "redundancy_level": "none"},
            **DRAWER,
        )

        assert response.status_code == 200  # the form comes back with its error
        assert not AssetDependency.objects.exists()
        # The refusal is the one of an unknown value : it names nothing.
        assert "ESSENTIAL-THEIRS" not in response.content.decode()

    def test_a_link_someone_else_made_survives_the_edit_of_the_record(self, client, two_assets):
        """An activity attached by someone with a wider reach is neither refused nor dropped."""
        from context.models import Activity

        def activity(name, scope):
            made = Activity.objects.create(name=name, type="core_business", owner=two_assets["user"])
            made.scopes.set([scope])
            return made

        client.force_login(two_assets["user"])
        asset = two_assets["assets"]["mine"]["essential"]
        ours = activity("ACTIVITY-MINE", two_assets["mine"])
        theirs = activity("ACTIVITY-THEIRS", two_assets["theirs"])
        other = activity("ACTIVITY-OTHER", two_assets["theirs"])
        asset.related_activities.set([theirs])
        edit = reverse("assets:essential-asset-update", kwargs={"pk": asset.pk})

        html = client.get(f"{edit}?section=relations", **DRAWER).content.decode()
        # Shown : the record holds it. What it does not hold stays out of the list.
        assert "ACTIVITY-THEIRS" in html and "ACTIVITY-MINE" in html
        assert "ACTIVITY-OTHER" not in html

        response = client.post(
            edit, {"_section": "relations", "related_activities": [str(theirs.pk), str(ours.pk)]}, **DRAWER,
        )
        assert response.status_code == 204, response.content.decode()[:300]
        assert set(asset.related_activities.all()) == {ours, theirs}

        refused = client.post(edit, {"_section": "relations", "related_activities": [str(other.pk)]}, **DRAWER)
        assert refused.status_code == 200
        assert set(asset.related_activities.all()) == {ours, theirs}

    def test_a_tree_of_choices_is_trimmed_too(self, client, two_scopes):
        """The parent site select writes its own choices : they follow the queryset."""
        from context.tests.factories import SiteFactory

        ours, theirs = SiteFactory(name="SITE-MINE"), SiteFactory(name="SITE-THEIRS")
        ours.scopes.set([two_scopes["mine"]])
        theirs.scopes.set([two_scopes["theirs"]])
        client.force_login(two_scopes["user"])

        html = client.get(reverse("assets:site-create"), **DRAWER).content.decode()

        assert "SITE-MINE" in html
        assert "SITE-THEIRS" not in html

    def test_the_scopes_tree_holds_the_scopes_of_the_user(self, client, two_assets):
        client.force_login(two_assets["user"])
        two_assets["mine"].name, two_assets["theirs"].name = "SCOPE-MINE", "SCOPE-THEIRS"
        two_assets["mine"].save()
        two_assets["theirs"].save()
        from context.tests.factories import ScopeFactory

        second = ScopeFactory(name="SCOPE-MINE-TOO")
        group = two_assets["user"].custom_groups.first()
        group.allowed_scopes.add(second)

        html = client.get(reverse("assets:supplier-create"), **DRAWER).content.decode()

        assert "SCOPE-MINE" in html and "SCOPE-MINE-TOO" in html
        assert "SCOPE-THEIRS" not in html

    def test_a_restricted_user_files_what_they_create(self, two_assets):
        """With several scopes to choose from, one must be chosen."""
        from assets.forms import SupplierCreateForm
        from context.tests.factories import ScopeFactory

        user = two_assets["user"]
        user.custom_groups.first().allowed_scopes.add(ScopeFactory())

        form = SupplierCreateForm(
            {"name": "Northwind", "criticality": "high", "owner": str(user.pk), "status": "active"}, user=user,
        )

        assert not form.is_valid()
        assert list(form.errors) == ["scopes"]

    def test_a_scope_set_by_someone_else_is_kept_by_an_edit(self, client, two_assets):
        """Saving the identity of a record filed under two scopes used to drop the one out of reach."""
        client.force_login(two_assets["user"])
        asset = two_assets["assets"]["mine"]["support"]
        asset.scopes.add(two_assets["theirs"])
        edit = reverse("assets:support-asset-update", kwargs={"pk": asset.pk})
        from assets.forms import SupportAssetUpdateForm

        form = SupportAssetUpdateForm(instance=asset, user=two_assets["user"], section="identity")
        answers = {name: form[name].value() for name in form.fields}
        data = {
            "_section": "identity", "name": answers["name"], "category": answers["category"],
            "description": answers["description"] or "",
            "scopes": [str(getattr(item, "pk", item)) for item in answers["scopes"]],
        }

        response = client.post(edit, data, **DRAWER)

        assert response.status_code == 204, response.content.decode()[:300]
        assert set(asset.scopes.all()) == {two_assets["mine"], two_assets["theirs"]}


def _project_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[2]


def _relations_to_scoped_models(form_class):
    """The fields of `form_class` that choose among the records of a scoped model."""
    found = []
    for name, field in getattr(form_class, "base_fields", {}).items():
        queryset = getattr(field, "queryset", None)
        if queryset is not None and resolve_scope_lookup(queryset.model) is not None:
            found.append(name)
    return found


def _forms_with_relations_to_scoped_models():
    """`{class name: class}` for every form of the project that has such a field."""
    import importlib
    import pkgutil

    from django import forms
    from django.apps import apps

    root = _project_root()
    found = {}
    for config in apps.get_app_configs():
        if root not in __import__("pathlib").Path(config.path).resolve().parents:
            continue
        package = importlib.import_module(config.name)
        for info in pkgutil.iter_modules(package.__path__):
            if "form" not in info.name:
                continue
            module = importlib.import_module(f"{config.name}.{info.name}")
            for name, value in vars(module).items():
                if (
                    isinstance(value, type) and issubclass(value, forms.BaseForm)
                    and value.__module__ == module.__name__ and _relations_to_scoped_models(value)
                ):
                    found[name] = value
    return found


# A form view whose form chooses among scoped records without going through
# PermissionRequiredMixin.get_form, and why that is safe.
FORM_VIEWS_RESTRICTED_ANOTHER_WAY = {}


def test_every_form_view_offers_what_the_user_may_select():
    """A generic form view restricts its relation fields : `PermissionRequiredMixin.get_form`.

    The mixin must come before Django's own `FormMixin`, and a view that
    writes its `get_form` must still call the one above it.
    """
    import ast
    import inspect
    import textwrap

    from django.views.generic.edit import FormMixin

    from accounts.views import PermissionRequiredMixin

    unguarded = []
    for callback in _routes():
        view = getattr(callback, "view_class", None)
        if view is None or not issubclass(view, FormMixin):
            continue
        name = f"{view.__module__}.{view.__name__}"
        if name in FORM_VIEWS_RESTRICTED_ANOTHER_WAY:
            continue
        form_class = getattr(view, "form_class", None)
        if form_class is not None and not _relations_to_scoped_models(form_class):
            continue
        mro = view.__mro__
        if PermissionRequiredMixin not in mro or mro.index(PermissionRequiredMixin) > mro.index(FormMixin):
            unguarded.append(f"{name} : PermissionRequiredMixin must come before the form view")
            continue
        for klass in mro[: mro.index(PermissionRequiredMixin)]:
            own = klass.__dict__.get("get_form")
            if own is None:
                continue
            calls = [
                node for node in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(own))))
                if isinstance(node, ast.Attribute) and node.attr == "get_form"
                and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "super"
            ]
            if not calls:
                unguarded.append(f"{name} : {klass.__name__}.get_form does not call super().get_form()")
    assert sorted(set(unguarded)) == []


def test_a_form_built_by_hand_is_restricted_too():
    """A view that builds a form itself restricts it, or hands it the user.

    `restrict_form_relations(Form(...), request.user)`, or `Form(..., user=...)`
    for a form built on `ScopedFormMixin`, which restricts itself.
    """
    import ast

    from core.modal_forms import ScopedFormMixin

    forms = _forms_with_relations_to_scoped_models()
    root = _project_root()
    offenders = []
    for path in sorted(root.glob("*/**/*.py")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith((".venv/", "node_modules/", "scripts/")) or "/tests/" in rel or "/migrations/" in rel:
            continue
        source = path.read_text(encoding="utf-8")
        if not any(name in source for name in forms):
            continue
        tree = ast.parse(source)
        wrapped = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "restrict_form_relations":
                wrapped.update(id(arg) for arg in node.args)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", getattr(node.func, "attr", None))
            if name not in forms or id(node) in wrapped:
                continue
            hands_the_user = any(keyword.arg == "user" for keyword in node.keywords)
            if hands_the_user and issubclass(forms[name], ScopedFormMixin):
                continue
            offenders.append(f"{rel}:{node.lineno} {name}")
    assert offenders == []


def test_no_formset_chooses_among_scoped_records():
    """The formsets of the project hold no relation to a scoped model.

    One that gains such a field is restricted with
    `core.scoping.restrict_formset_relations(formset, user)` where it is
    built, and leaves this test with its reason.
    """
    import importlib
    import pkgutil

    from django.apps import apps
    from django.forms import BaseFormSet

    root = _project_root()
    exposed = []
    for config in apps.get_app_configs():
        if root not in __import__("pathlib").Path(config.path).resolve().parents:
            continue
        package = importlib.import_module(config.name)
        for info in pkgutil.iter_modules(package.__path__):
            if "form" not in info.name:
                continue
            module = importlib.import_module(f"{config.name}.{info.name}")
            for name, value in vars(module).items():
                if isinstance(value, type) and issubclass(value, BaseFormSet) and getattr(value, "form", None):
                    if _relations_to_scoped_models(value.form):
                        exposed.append(f"{module.__name__}.{name}")
    assert exposed == []


# ── The API : a relation written stays within reach ─────────────────────────


def _api(user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user)
    return client


def _data(response):
    payload = response.json()
    return payload.get("data", payload) if isinstance(payload, dict) else payload


@pytest.mark.django_db
class TestApiRelationsStayWithinReach:
    def test_a_record_of_another_scope_cannot_be_linked(self, two_assets):
        """It used to answer 201, with the name of the hidden record in the answer."""
        from assets.models import AssetDependency

        mine, theirs = two_assets["assets"]["mine"], two_assets["assets"]["theirs"]

        response = _api(two_assets["user"]).post("/api/v1/assets/dependencies/", {
            "essential_asset": str(theirs["essential"].pk), "support_asset": str(mine["support"].pk),
            "dependency_type": "runs_on", "criticality": "high",
        }, format="json")

        assert response.status_code == 400
        assert "ESSENTIAL-THEIRS" not in response.content.decode()
        assert not AssetDependency.objects.exists()

    def test_the_refusal_is_the_one_of_an_unknown_record(self, two_assets):
        """Nothing tells a record of another scope from one that does not exist."""
        import uuid

        mine, theirs = two_assets["assets"]["mine"], two_assets["assets"]["theirs"]
        api = _api(two_assets["user"])

        def refusal(essential):
            answer = api.post("/api/v1/assets/dependencies/", {
                "essential_asset": essential, "support_asset": str(mine["support"].pk),
                "dependency_type": "runs_on", "criticality": "high",
            }, format="json")
            return answer.status_code, str(answer.json()).replace(essential, "<id>")

        assert refusal(str(theirs["essential"].pk)) == refusal(str(uuid.uuid4()))

    def test_a_record_within_reach_is_linked(self, two_assets):
        mine = two_assets["assets"]["mine"]

        response = _api(two_assets["user"]).post("/api/v1/assets/dependencies/", {
            "essential_asset": str(mine["essential"].pk), "support_asset": str(mine["support"].pk),
            "dependency_type": "runs_on", "criticality": "high",
        }, format="json")

        assert response.status_code == 201, response.content.decode()[:300]

    def test_a_record_cannot_be_filed_under_a_scope_not_given(self, two_assets):
        from assets.models import EssentialAsset

        user = two_assets["user"]

        response = _api(user).post("/api/v1/assets/essential-assets/", {
            "name": "Planted", "type": "information", "category": "legal_data", "owner": str(user.pk),
            "scopes": [str(two_assets["theirs"].pk)],
        }, format="json")

        assert response.status_code == 400
        assert not EssentialAsset.objects.filter(name="Planted").exists()

    def test_a_restricted_caller_files_what_they_create(self, two_assets):
        """Under one of their scopes : a record filed under nothing is one they no longer find."""
        from assets.models import EssentialAsset

        user = two_assets["user"]
        api = _api(user)
        body = {"name": "Mine", "type": "information", "category": "legal_data", "owner": str(user.pk)}

        assert api.post("/api/v1/assets/essential-assets/", {**body, "scopes": []}, format="json").status_code == 400
        assert api.post("/api/v1/assets/essential-assets/", body, format="json").status_code == 400
        filed = api.post(
            "/api/v1/assets/essential-assets/", {**body, "scopes": [str(two_assets["mine"].pk)]}, format="json",
        )

        assert filed.status_code == 201, filed.content.decode()[:300]
        assert list(EssentialAsset.objects.get(name="Mine").scopes.all()) == [two_assets["mine"]]

    def test_a_record_read_can_be_sent_back_as_it_is(self, two_assets):
        """A scope set by someone with a wider reach does not make the update fail, nor leave."""
        asset = two_assets["assets"]["mine"]["essential"]
        asset.scopes.add(two_assets["theirs"])
        api = _api(two_assets["user"])
        url = f"/api/v1/assets/essential-assets/{asset.pk}/"

        read = _data(api.get(url))
        body = {key: read[key] for key in ("name", "type", "category", "owner", "scopes")}
        sent = api.put(url, {**body, "name": "Renamed"}, format="json")

        assert sent.status_code == 200, sent.content.decode()[:300]
        asset.refresh_from_db()
        assert asset.name == "Renamed"
        assert set(asset.scopes.all()) == {two_assets["mine"], two_assets["theirs"]}

    def test_an_update_cannot_add_a_scope_not_given(self, two_assets):
        asset = two_assets["assets"]["mine"]["essential"]

        response = _api(two_assets["user"]).patch(
            f"/api/v1/assets/essential-assets/{asset.pk}/",
            {"scopes": [str(two_assets["mine"].pk), str(two_assets["theirs"].pk)]}, format="json",
        )

        assert response.status_code == 400
        assert list(asset.scopes.all()) == [two_assets["mine"]]

    def test_a_caller_nothing_restricts_links_as_before(self, two_assets):
        mine, theirs = two_assets["assets"]["mine"], two_assets["assets"]["theirs"]

        response = _api(UserFactory(is_superuser=True)).post("/api/v1/assets/dependencies/", {
            "essential_asset": str(theirs["essential"].pk), "support_asset": str(mine["support"].pk),
            "dependency_type": "runs_on", "criticality": "high",
        }, format="json")

        assert response.status_code == 201, response.content.decode()[:300]


# An API class that writes a relation to a scoped model without the mixin, and why.
API_CLASSES_WRITING_RELATIONS_UNRESTRICTED = {
    "accounts.api.views.GroupViewSet": "administration of the groups : who manages them decides the scopes they give",
}


def test_every_api_class_writing_a_relation_restricts_it():
    """A serializer that writes a relation to a scoped model is built by a class
    carrying `ReachableRelationsAPIMixin` (`ScopeFilterAPIMixin` includes it)."""
    from rest_framework import serializers

    from accounts.api.mixins import ReachableRelationsAPIMixin

    def writes_a_scoped_relation(serializer_class):
        try:
            fields = serializer_class().fields
        except Exception:  # noqa: BLE001 - a serializer that needs its view to be built
            return False
        for field in fields.values():
            if field.read_only:
                continue
            relation = getattr(field, "child_relation", field)
            queryset = getattr(relation, "queryset", None) if isinstance(relation, serializers.RelatedField) else None
            if queryset is not None and resolve_scope_lookup(queryset.all().model) is not None:
                return True
        return False

    unguarded = []
    for callback in _routes():
        cls = getattr(callback, "cls", None)
        if cls is None or ReachableRelationsAPIMixin in cls.__mro__:
            continue
        name = f"{cls.__module__}.{cls.__name__}"
        if name in API_CLASSES_WRITING_RELATIONS_UNRESTRICTED:
            continue
        candidates = {getattr(cls, "serializer_class", None)}
        for value in vars(cls).values():
            if isinstance(value, dict):
                candidates.update(v for v in value.values() if isinstance(v, type))
        candidates = {c for c in candidates if isinstance(c, type) and issubclass(c, serializers.BaseSerializer)}
        if any(writes_a_scoped_relation(candidate) for candidate in candidates):
            unguarded.append(name)
    assert sorted(set(unguarded)) == []


# ── MCP : a tool reaches what its caller may reach ──────────────────────────


def _mcp_call(user, tool, arguments):
    """The answer of an MCP tool, as a dictionary (``{"error": ...}`` when it refuses)."""
    import json

    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    server = McpServer()
    register_all_tools(server)
    result = server.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }), user)
    if "error" in result:
        return {"error": result["error"].get("message", "")}
    return json.loads(result["result"]["content"][0]["text"])


@pytest.mark.django_db
class TestMcpStaysWithinReach:
    def test_a_row_under_a_record_of_another_scope_is_neither_read_changed_nor_deleted(self, two_perimeters):
        """A requirement hangs under its framework : the tools used to serve it whatever the scope."""
        from compliance.models import Requirement

        user = _member_of_one_scope(two_perimeters["mine"])
        theirs = two_perimeters["req_theirs"]
        name = theirs.name

        listed = _mcp_call(user, "list_requirements", {})
        assert [row["id"] for row in listed["items"]] == [str(two_perimeters["req_mine"].pk)]
        for tool, arguments in (
            ("get_requirement", {"id": str(theirs.pk)}),
            ("update_requirement", {"id": str(theirs.pk), "name": "Tampered"}),
            ("delete_requirement", {"id": str(theirs.pk)}),
        ):
            assert _mcp_call(user, tool, arguments) == {"error": "Requirement not found."}, tool
        assert Requirement.objects.get(pk=theirs.pk).name == name

    def test_the_refusal_does_not_tell_a_hidden_record_from_a_missing_one(self, two_perimeters):
        import uuid

        user = _member_of_one_scope(two_perimeters["mine"])

        hidden = _mcp_call(user, "get_requirement", {"id": str(two_perimeters["req_theirs"].pk)})
        missing = _mcp_call(user, "get_requirement", {"id": str(uuid.uuid4())})

        assert hidden == missing

    def test_a_record_cannot_be_linked_to_one_of_another_scope(self, two_assets):
        from assets.models import AssetDependency

        mine, theirs = two_assets["assets"]["mine"], two_assets["assets"]["theirs"]
        body = {"support_asset_id": str(mine["support"].pk), "dependency_type": "runs_on", "criticality": "high"}

        refused = _mcp_call(two_assets["user"], "create_asset_dependency", {
            **body, "essential_asset_id": str(theirs["essential"].pk),
        })

        assert "not found" in refused["error"]
        assert not AssetDependency.objects.exists()
        linked = _mcp_call(two_assets["user"], "create_asset_dependency", {
            **body, "essential_asset_id": str(mine["essential"].pk),
        })
        assert "error" not in linked, linked

    def test_a_record_is_filed_under_the_scopes_of_the_caller(self, two_assets):
        from assets.models import EssentialAsset

        user = two_assets["user"]
        body = {"name": "Planted", "type": "information", "category": "legal_data", "owner_id": str(user.pk)}

        elsewhere = _mcp_call(user, "create_essential_asset", {**body, "scope_ids": [str(two_assets["theirs"].pk)]})
        nowhere = _mcp_call(user, "create_essential_asset", body)

        assert "not found" in elsewhere["error"]
        assert "at least one of your scopes" in nowhere["error"]
        assert not EssentialAsset.objects.filter(name="Planted").exists()
        filed = _mcp_call(user, "create_essential_asset", {**body, "scope_ids": [str(two_assets["mine"].pk)]})
        assert "error" not in filed, filed
        assert list(EssentialAsset.objects.get(name="Planted").scopes.all()) == [two_assets["mine"]]

    def test_an_update_keeps_what_the_record_held_and_adds_within_reach_only(self, two_assets):
        asset = two_assets["assets"]["mine"]["essential"]
        asset.scopes.add(two_assets["theirs"])
        user = two_assets["user"]
        both = [str(two_assets["mine"].pk), str(two_assets["theirs"].pk)]

        # Sent back as it was read : the scope someone else set stays valid.
        kept = _mcp_call(user, "update_essential_asset", {"id": str(asset.pk), "scope_ids": both, "name": "Renamed"})
        assert "error" not in kept, kept

        other = two_assets["assets"]["mine"]["support"]
        added = _mcp_call(user, "update_support_asset", {"id": str(other.pk), "scope_ids": both})
        assert "not found" in added["error"]
        assert list(other.scopes.all()) == [two_assets["mine"]]

    def test_a_tool_written_by_hand_checks_the_scopes_it_is_given(self, two_scopes):
        """The management review tool set its scopes from the identifiers as given."""
        from reports.models import ManagementReview

        user = two_scopes["user"]
        body = {
            "title": "Planted", "frequency": "annual", "period_start": "2026-01-01", "period_end": "2026-12-31",
            "planned_date": "2027-01-15", "facilitator_id": str(user.pk),
        }

        refused = _mcp_call(user, "create_management_review", {**body, "scope_ids": [str(two_scopes["theirs"].pk)]})

        assert "not found" in refused["error"]
        assert not ManagementReview.objects.filter(title="Planted").exists()

    def test_a_caller_nothing_restricts_works_as_before(self, two_assets):
        mine, theirs = two_assets["assets"]["mine"], two_assets["assets"]["theirs"]

        linked = _mcp_call(UserFactory(is_superuser=True), "create_asset_dependency", {
            "essential_asset_id": str(theirs["essential"].pk), "support_asset_id": str(mine["support"].pk),
            "dependency_type": "runs_on", "criticality": "high",
        })

        assert "error" not in linked, linked


# What a tool may query on its own, and why.
MCP_QUERIES_OUTSIDE_THE_HELPERS = {
    "_reach": "the helper itself",
    "_register_documents_tools": "a base queryset, narrowed to the caller's own notices by its tool",
    "_register_controls_tools": "a base queryset, handed to the scope filter by its tool",
}


def test_mcp_tools_read_through_the_scoped_helpers():
    """No tool queries ``Model.objects`` on its own : it reads through ``_reach`` and ``_fetch``.

    Sixty families of tools were once registered with the scope filter switched
    off, and forty fetches by identifier had none. ``Model.objects.create`` is
    a write, checked by ``_refuse_relations_out_of_reach``; a queryset handed
    straight to ``_filter_by_scopes`` is scoped where it is written.
    """
    import ast

    path = _project_root() / "mcp" / "tools.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    offenders = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and node.attr == "objects"):
            continue
        parent = parents.get(node)
        if isinstance(parent, ast.Attribute) and parent.attr == "create":
            continue
        scoped_on_the_spot, functions = False, []
        cursor = node
        while cursor is not None:
            cursor = parents.get(cursor)
            if isinstance(cursor, ast.Call) and getattr(cursor.func, "id", "") == "_filter_by_scopes":
                scoped_on_the_spot = True
            if isinstance(cursor, ast.FunctionDef):
                functions.append(cursor.name)
        if scoped_on_the_spot or any(name in MCP_QUERIES_OUTSIDE_THE_HELPERS for name in functions[:1] + functions[-1:]):
            continue
        offenders.append(f"mcp/tools.py:{node.lineno} in {functions[0] if functions else 'module'}")
    assert offenders == []


def test_every_mcp_write_checks_the_relations_it_is_given():
    """A ``full_clean()`` in a tool is preceded by the check of the relations."""
    import ast

    path = _project_root() / "mcp" / "tools.py"
    source = path.read_text(encoding="utf-8")
    lines = source.split("\n")
    unguarded = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "full_clean":
            before = "\n".join(lines[max(0, node.lineno - 12): node.lineno - 1])
            if "_refuse_relations_out_of_reach(" not in before:
                unguarded.append(f"mcp/tools.py:{node.lineno}")
    assert unguarded == []


def test_an_api_action_restricts_the_serializer_it_builds():
    """A serializer built by hand with request data goes through ``restrict_serializer_relations``
    when it writes a relation to a scoped model (``get_serializer`` does it for the others)."""
    import ast
    import importlib

    from rest_framework import serializers

    root = _project_root()
    offenders = []
    for path in sorted(root.glob("*/api/*.py")):
        rel = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        module = importlib.import_module(rel[:-3].replace("/", "."))
        wrapped = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "restrict_serializer_relations":
                wrapped.update(id(arg) for arg in node.args)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            if not any(keyword.arg == "data" for keyword in node.keywords) or id(node) in wrapped:
                continue
            cls = getattr(module, node.func.id, None)
            if not (isinstance(cls, type) and issubclass(cls, serializers.BaseSerializer)):
                continue
            for field in cls().fields.values():
                relation = getattr(field, "child_relation", field)
                queryset = getattr(relation, "queryset", None) if isinstance(relation, serializers.RelatedField) else None
                if not field.read_only and queryset is not None and resolve_scope_lookup(queryset.all().model):
                    offenders.append(f"{rel}:{node.lineno} {node.func.id}")
                    break
    assert offenders == []

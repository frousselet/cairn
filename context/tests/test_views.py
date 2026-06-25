"""
Comprehensive view tests for the context app.

Covers CRUD views for: Scope, Issue, Stakeholder, Objective, Role, Activity,
Tag, Indicator, and related helpers (approve, table-body, dashboard toggles).

SWOT views are tested separately in test_swot_views.py and are NOT duplicated here.
"""

import json

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from context.constants import (
    ActivityStatus,
    ActivityType,
    CollectionMethod,
    Criticality,
    ImpactLevel,
    IndicatorFormat,
    IndicatorStatus,
    IndicatorType,
    InfluenceLevel,
    IssueCategory,
    IssueStatus,
    IssueType,
    MeasurementFrequency,
    ObjectiveCategory,
    ObjectiveStatus,
    ObjectiveType,
    PredefinedIndicatorSource,
    RoleStatus,
    RoleType,
    StakeholderCategory,
    StakeholderStatus,
    Trend,
)
from context.models import (
    Activity,
    Indicator,
    IndicatorMeasurement,
    Issue,
    Objective,
    Role,
    Scope,
    Stakeholder,
    Tag,
)

from .factories import IssueFactory, ObjectiveFactory, ScopeFactory

pytestmark = pytest.mark.django_db


# ── Helpers ────────────────────────────────────────────────


def _superuser_client():
    """Return (client, user) with a logged-in superuser."""
    user = UserFactory(is_superuser=True, is_staff=True)
    client = Client()
    client.force_login(user)
    return client, user


def _make_stakeholder(**kwargs):
    """Create a Stakeholder directly (no factory available)."""
    defaults = {
        "name": "Test Stakeholder",
        "type": IssueType.INTERNAL,
        "category": StakeholderCategory.CUSTOMERS,
        "influence_level": InfluenceLevel.MEDIUM,
        "interest_level": InfluenceLevel.HIGH,
        "status": StakeholderStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Stakeholder.objects.create(**defaults)


def _make_role(**kwargs):
    """Create a Role directly."""
    defaults = {
        "name": "Test Role",
        "type": RoleType.GOVERNANCE,
        "status": RoleStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Role.objects.create(**defaults)


def _make_activity(owner, **kwargs):
    """Create an Activity directly."""
    defaults = {
        "name": "Test Activity",
        "type": ActivityType.CORE_BUSINESS,
        "criticality": Criticality.MEDIUM,
        "owner": owner,
        "status": ActivityStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Activity.objects.create(**defaults)


def _make_tag(**kwargs):
    """Create a Tag directly."""
    defaults = {"name": "test-tag", "color": "#ff5733"}
    defaults.update(kwargs)
    return Tag.objects.create(**defaults)


def _make_indicator(indicator_type=IndicatorType.ORGANIZATIONAL, **kwargs):
    """Create an Indicator directly."""
    defaults = {
        "name": "Test Indicator",
        "indicator_type": indicator_type,
        "collection_method": CollectionMethod.MANUAL,
        "format": IndicatorFormat.NUMBER,
        "review_frequency": MeasurementFrequency.MONTHLY,
        "first_review_date": "2099-01-01",
        "status": IndicatorStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Indicator.objects.create(**defaults)


# ══════════════════════════════════════════════════════════
# Scope Views
# ══════════════════════════════════════════════════════════


class TestScopeListView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:scope-list"))
        assert resp.status_code == 302

    def test_list_returns_200(self):
        client, _ = _superuser_client()
        ScopeFactory()
        resp = client.get(reverse("context:scope-list"))
        assert resp.status_code == 200

    def test_list_with_status_filter(self):
        client, _ = _superuser_client()
        ScopeFactory(workflow_state="validated")
        ScopeFactory()
        resp = client.get(reverse("context:scope-list") + "?status=active")
        assert resp.status_code == 200

    def test_list_with_search(self):
        client, _ = _superuser_client()
        ScopeFactory(name="Unique Alpha Scope")
        resp = client.get(reverse("context:scope-list") + "?q=Alpha")
        assert resp.status_code == 200

    def test_list_tree_structure(self):
        """Scopes with parent_scope should be rendered as a tree."""
        client, _ = _superuser_client()
        parent = ScopeFactory(name="Parent Scope")
        ScopeFactory(name="Child Scope", parent_scope=parent)
        resp = client.get(reverse("context:scope-list"))
        assert resp.status_code == 200
        assert b"Parent Scope" in resp.content
        assert b"Child Scope" in resp.content


class TestListSummaryRail:
    """The sticky side rail's summary reflects the whole visible list,
    independent of the active ``?status=`` facet."""

    def test_summary_totals_and_states(self):
        client, _ = _superuser_client()
        # The initial state is forced on create, so set the states directly.
        ScopeFactory()
        validated = [ScopeFactory().pk, ScopeFactory().pk]
        Scope.objects.filter(pk__in=validated).update(workflow_state="validated")
        resp = client.get(reverse("context:scope-list"))
        summary = resp.context["list_summary"]
        assert summary["total"] == 3
        counts = {item["value"]: item["count"] for item in summary["items"]}
        assert counts.get("validated") == 2
        assert counts.get("draft") == 1

    def test_summary_ignores_active_status_facet(self):
        """Counts cover every state even when the list is filtered to one."""
        client, _ = _superuser_client()
        keep = ScopeFactory()
        ScopeFactory()
        Scope.objects.filter(pk=keep.pk).update(workflow_state="validated")
        resp = client.get(reverse("context:scope-list") + "?status=validated")
        assert resp.context["list_summary"]["total"] == 2

    def test_summary_uses_domain_status_field(self):
        """Issues facet a domain ``status`` field, not ``workflow_state``."""
        client, _ = _superuser_client()
        IssueFactory()
        resp = client.get(reverse("context:issue-list"))
        summary = resp.context["list_summary"]
        assert summary["total"] == 1
        assert sum(item["count"] for item in summary["items"]) == 1


class TestPredefinedFilters:
    """Combinable predefined facets: multiple values for one facet are
    OR-combined (``field__in``), via the same widget on the full page and
    its HTMX table-body view."""

    def _issue(self, name, status):
        from context.models import Issue

        issue = IssueFactory(name=name)
        Issue.objects.filter(pk=issue.pk).update(status=status)
        return issue

    def test_combinable_status_or(self):
        client, _ = _superuser_client()
        self._issue("AlphaIssue", "active")
        self._issue("BetaIssue", "monitored")
        self._issue("GammaIssue", "closed")
        resp = client.get(
            reverse("context:issue-table-body"), {"status": ["active", "monitored"]}
        )
        body = resp.content
        assert b"AlphaIssue" in body
        assert b"BetaIssue" in body
        assert b"GammaIssue" not in body

    def test_filter_context_marks_checked(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:issue-list"), {"status": "active"})
        groups = {g["param"]: g for g in resp.context["list_filters"]}
        status_opts = {o["value"]: o["checked"] for o in groups["status"]["options"]}
        assert status_opts.get("active") is True
        assert status_opts.get("closed") is False
        assert resp.context["list_filters_active"] is True

    def _named(self, name):
        return IssueFactory(name=name)

    def test_text_filter_contains(self):
        client, _ = _superuser_client()
        self._named("Alpha")
        self._named("Alphabet")
        self._named("Beta")
        resp = client.get(
            reverse("context:issue-table-body"), {"name_op": "contains", "name_q": "lph"}
        )
        assert b"Alpha" in resp.content and b"Alphabet" in resp.content
        assert b"Beta" not in resp.content

    def test_text_filter_starts_with(self):
        client, _ = _superuser_client()
        self._named("Alpha")
        self._named("Gamma Alpha")
        resp = client.get(
            reverse("context:issue-table-body"), {"name_op": "starts", "name_q": "Alpha"}
        )
        assert b"Alpha</a>" in resp.content or b">Alpha<" in resp.content
        assert b"Gamma Alpha" not in resp.content

    def test_text_filter_is_not(self):
        client, _ = _superuser_client()
        self._named("Alpha")
        self._named("Beta")
        resp = client.get(
            reverse("context:issue-table-body"), {"name_op": "isnot", "name_q": "Alpha"}
        )
        assert b"Beta" in resp.content
        # "Alpha" excluded (the exact match is filtered out)
        assert resp.content.count(b"Alpha") == 0


class TestColumnPreferences:
    """Per-user column visibility/order and the KPI rail context."""

    def test_default_columns(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:issue-list"))
        cols = resp.context["list_columns"]
        by_key = {c["key"]: c for c in cols}
        assert cols[0]["key"] == "reference"
        assert by_key["reference"]["always"] is True
        assert by_key["tags"]["visible"] is True

    def test_saved_preference_reorders_and_hides(self):
        client, user = _superuser_client()
        user.column_preferences = {
            "context.issue": {"order": ["name", "reference", "status"], "hidden": ["tags"]}
        }
        user.save(update_fields=["column_preferences"])
        resp = client.get(reverse("context:issue-list"))
        cols = resp.context["list_columns"]
        assert [c["key"] for c in cols][:3] == ["name", "reference", "status"]
        assert next(c for c in cols if c["key"] == "tags")["visible"] is False
        # A column added after the saved order still appears (visible) at the end.
        assert "actions" in [c["key"] for c in cols]

    def test_kpis_present(self):
        client, _ = _superuser_client()
        IssueFactory()
        resp = client.get(reverse("context:issue-list"))
        assert resp.context["list_kpis"]
        assert resp.context["list_kpis"][0]["value"] == 1

    def test_save_columns_endpoint(self):
        client, user = _superuser_client()
        resp = client.post(
            reverse("helpers:save-columns"),
            data=json.dumps(
                {"view": "context.issue", "order": ["name", "reference"], "hidden": ["tags"]}
            ),
            content_type="application/json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.column_preferences["context.issue"]["hidden"] == ["tags"]
        assert user.column_preferences["context.issue"]["order"] == ["name", "reference"]


class TestAdvancedFilters:
    """The generic "filter on any field" engine (AdvancedFilterMixin)."""

    @staticmethod
    def _rule(f, o, v):
        return json.dumps({"f": f, "o": o, "v": v})

    def test_text_rule_contains(self):
        client, _ = _superuser_client()
        IssueFactory(name="AlphaWidget")
        IssueFactory(name="BetaWidget")
        resp = client.get(
            reverse("context:issue-table-body"), {"rule": self._rule("name", "contains", "Alpha")}
        )
        assert b"AlphaWidget" in resp.content
        assert b"BetaWidget" not in resp.content

    def test_choice_rule_is(self):
        client, _ = _superuser_client()
        crit = IssueFactory(name="CritWidget")
        IssueFactory(name="LowWidget")
        from context.models import Issue

        Issue.objects.filter(pk=crit.pk).update(impact_level="critical")
        resp = client.get(
            reverse("context:issue-table-body"),
            {"rule": self._rule("impact_level", "is", "critical")},
        )
        assert b"CritWidget" in resp.content
        assert b"LowWidget" not in resp.content

    def test_relation_rule_scopes_in(self):
        client, _ = _superuser_client()
        scope = ScopeFactory(name="ScopeX")
        a = IssueFactory(name="ScopedWidget")
        a.scopes.add(scope)
        IssueFactory(name="UnscopedWidget")
        resp = client.get(
            reverse("context:issue-table-body"),
            {"rule": self._rule("scopes", "in", [str(scope.pk)])},
        )
        assert b"ScopedWidget" in resp.content
        assert b"UnscopedWidget" not in resp.content

    def test_unknown_field_is_ignored(self):
        client, _ = _superuser_client()
        IssueFactory(name="SafeWidget")
        resp = client.get(
            reverse("context:issue-table-body"), {"rule": self._rule("password", "is", "x")}
        )
        assert resp.status_code == 200
        assert b"SafeWidget" in resp.content

    def test_registry_exposed_and_filtered(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:issue-list"))
        fields = json.loads(resp.context["filter_fields_json"])
        keys = {f["key"] for f in fields}
        assert {"name", "impact_level", "scopes"} <= keys
        assert "password" not in keys and "id" not in keys and "created_by" not in keys
        impact = next(f for f in fields if f["key"] == "impact_level")
        assert impact["type"] == "choice"
        assert any(o["value"] == "critical" for o in impact["options"])


class TestTableBodyPagination:
    """The HTMX table-body paginates and its response carries the pager OOB,
    so filtering/search/paging stay consistent."""

    def test_first_page_is_capped_and_has_pager(self):
        client, _ = _superuser_client()
        for _i in range(60):
            IssueFactory()
        body = client.get(reverse("context:issue-table-body")).content.decode()
        assert body.count('class="ref"') == 50
        assert 'id="list-pagination"' in body and 'hx-swap-oob="true"' in body
        assert 'data-page="2"' in body

    def test_second_page(self):
        client, _ = _superuser_client()
        for _i in range(60):
            IssueFactory()
        body = client.get(reverse("context:issue-table-body"), {"page": 2}).content.decode()
        assert body.count('class="ref"') == 10

    def test_search_narrows_and_repaginates(self):
        client, _ = _superuser_client()
        IssueFactory(name="ZebraUnique")
        for _i in range(3):
            IssueFactory(name="Common")
        body = client.get(reverse("context:issue-table-body"), {"q": "ZebraUnique"}).content.decode()
        assert body.count('class="ref"') == 1

    def test_quoted_search_is_exact(self):
        client, _ = _superuser_client()
        IssueFactory(name="Alpha")
        IssueFactory(name="Alpha extended")
        url = reverse("context:issue-table-body")
        # Substring: both match.
        assert client.get(url, {"q": "Alpha"}).content.decode().count('class="ref"') == 2
        # Quoted: only the exact title matches.
        assert client.get(url, {"q": '"Alpha"'}).content.decode().count('class="ref"') == 1


class TestSavedFilters:
    """Saved filters: list context (own + shared) and the CRUD API."""

    def test_context_lists_own_and_shared(self):
        from accounts.models import SavedFilter

        client, user = _superuser_client()
        other = UserFactory()
        SavedFilter.objects.create(owner=user, view_key="context.issue", name="Mine", query="status=active")
        SavedFilter.objects.create(owner=other, view_key="context.issue", name="SharedOne", is_shared=True)
        SavedFilter.objects.create(owner=other, view_key="context.issue", name="PrivateOne")
        resp = client.get(reverse("context:issue-list"))
        names = {sf["name"] for sf in resp.context["saved_filters"]}
        assert {"Mine", "SharedOne"} <= names
        assert "PrivateOne" not in names
        assert resp.context["saved_filter_view_key"] == "context.issue"

    def test_api_create_and_list(self):
        from accounts.models import SavedFilter

        client, user = _superuser_client()
        resp = client.post(
            "/api/v1/saved-filters/",
            data=json.dumps({"view_key": "context.issue", "name": "F1", "query": "status=active"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert SavedFilter.objects.filter(owner=user, name="F1").exists()
        resp = client.get("/api/v1/saved-filters/?view_key=context.issue")
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert any(i["name"] == "F1" for i in items)

    def test_api_cannot_modify_others(self):
        from accounts.models import SavedFilter

        client, _ = _superuser_client()
        other = UserFactory()
        sf = SavedFilter.objects.create(owner=other, view_key="context.issue", name="Foreign", is_shared=True)
        resp = client.delete(f"/api/v1/saved-filters/{sf.id}/")
        assert resp.status_code in (403, 404)
        assert SavedFilter.objects.filter(pk=sf.id).exists()


class TestScopeDetailView:
    def test_requires_login(self):
        scope = ScopeFactory()
        client = Client()
        resp = client.get(reverse("context:scope-detail", args=[scope.pk]))
        assert resp.status_code == 302

    def test_detail_returns_200(self):
        client, _ = _superuser_client()
        scope = ScopeFactory()
        resp = client.get(reverse("context:scope-detail", args=[scope.pk]))
        assert resp.status_code == 200

    def test_detail_shows_ancestors(self):
        client, _ = _superuser_client()
        parent = ScopeFactory(name="Parent")
        child = ScopeFactory(name="Child", parent_scope=parent)
        resp = client.get(reverse("context:scope-detail", args=[child.pk]))
        assert resp.status_code == 200

    def test_detail_has_history(self):
        client, _ = _superuser_client()
        scope = ScopeFactory()
        resp = client.get(reverse("context:scope-detail", args=[scope.pk]))
        assert resp.status_code == 200
        assert resp.context["history_available"] is True
        assert "history_url" in resp.context


class TestScopeCreateView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:scope-create"))
        assert resp.status_code == 302

    def test_get_form(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:scope-create"))
        assert resp.status_code == 200

    def test_create_scope(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:scope-create"),
            {
                "name": "New Scope",
                "description": "A brand new scope",
            },
        )
        assert resp.status_code == 302
        assert Scope.objects.filter(name="New Scope").exists()

    def test_create_sets_created_by(self):
        client, user = _superuser_client()
        client.post(
            reverse("context:scope-create"),
            {
                "name": "Owned Scope",
                "description": "Check created_by",
            },
        )
        scope = Scope.objects.get(name="Owned Scope")
        assert scope.created_by == user


class TestScopeUpdateView:
    def test_get_form(self):
        client, _ = _superuser_client()
        scope = ScopeFactory()
        resp = client.get(reverse("context:scope-update", args=[scope.pk]))
        assert resp.status_code == 200

    def test_update_scope(self):
        client, _ = _superuser_client()
        scope = ScopeFactory(name="Old Name")
        resp = client.post(
            reverse("context:scope-update", args=[scope.pk]),
            {
                "name": "Updated Name",
                "description": scope.description,
                
            },
        )
        assert resp.status_code == 302
        scope.refresh_from_db()
        assert scope.name == "Updated Name"


class TestScopeDeleteView:
    def test_requires_login(self):
        scope = ScopeFactory()
        client = Client()
        resp = client.post(reverse("context:scope-delete", args=[scope.pk]))
        assert resp.status_code == 302
        assert Scope.objects.filter(pk=scope.pk).exists()

    def test_get_confirmation_page(self):
        client, _ = _superuser_client()
        scope = ScopeFactory()
        resp = client.get(reverse("context:scope-delete", args=[scope.pk]))
        assert resp.status_code == 200

    def test_delete_scope(self):
        client, _ = _superuser_client()
        scope = ScopeFactory()
        resp = client.post(reverse("context:scope-delete", args=[scope.pk]))
        assert resp.status_code == 302
        assert not Scope.objects.filter(pk=scope.pk).exists()


class TestScopeApproveView:
    def test_requires_login(self):
        scope = ScopeFactory()
        client = Client()
        resp = client.post(reverse("context:scope-approve", args=[scope.pk]))
        assert resp.status_code == 302

    def test_approve_scope(self):
        client, user = _superuser_client()
        scope = ScopeFactory()
        resp = client.post(reverse("context:scope-approve", args=[scope.pk]))
        assert resp.status_code == 302
        scope.refresh_from_db()
        assert scope.is_approved is True
        assert scope.approved_by == user


class TestScopeTableBodyView:
    def test_returns_200(self):
        client, _ = _superuser_client()
        ScopeFactory()
        resp = client.get(reverse("context:scope-table-body"))
        assert resp.status_code == 200

    def test_with_status_filter(self):
        client, _ = _superuser_client()
        ScopeFactory(workflow_state="validated")
        resp = client.get(reverse("context:scope-table-body") + "?status=active")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════
# Issue Views
# ══════════════════════════════════════════════════════════


class TestIssueListView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:issue-list"))
        assert resp.status_code == 302

    def test_list_returns_200(self):
        client, _ = _superuser_client()
        IssueFactory()
        resp = client.get(reverse("context:issue-list"))
        assert resp.status_code == 200

    def test_list_with_type_filter(self):
        client, _ = _superuser_client()
        IssueFactory(type=IssueType.INTERNAL)
        resp = client.get(reverse("context:issue-list") + "?type=internal")
        assert resp.status_code == 200

    def test_list_with_status_filter(self):
        client, _ = _superuser_client()
        IssueFactory()
        resp = client.get(reverse("context:issue-list") + "?status=identified")
        assert resp.status_code == 200

    def test_list_with_impact_filter(self):
        client, _ = _superuser_client()
        IssueFactory(impact_level=ImpactLevel.HIGH)
        resp = client.get(reverse("context:issue-list") + "?impact=high")
        assert resp.status_code == 200

    def test_list_with_search(self):
        client, _ = _superuser_client()
        IssueFactory(name="Unique Issue XYZ")
        resp = client.get(reverse("context:issue-list") + "?q=XYZ")
        assert resp.status_code == 200

    def test_list_sorting(self):
        client, _ = _superuser_client()
        IssueFactory()
        resp = client.get(reverse("context:issue-list") + "?sort=name&order=desc")
        assert resp.status_code == 200


class TestIssueDetailView:
    def test_requires_login(self):
        issue = IssueFactory()
        client = Client()
        resp = client.get(reverse("context:issue-detail", args=[issue.pk]))
        assert resp.status_code == 302

    def test_detail_returns_200(self):
        client, _ = _superuser_client()
        issue = IssueFactory()
        resp = client.get(reverse("context:issue-detail", args=[issue.pk]))
        assert resp.status_code == 200

    def test_detail_has_history(self):
        client, _ = _superuser_client()
        issue = IssueFactory()
        resp = client.get(reverse("context:issue-detail", args=[issue.pk]))
        assert resp.context["history_available"] is True
        assert "history_url" in resp.context


class TestIssueCreateView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:issue-create"))
        assert resp.status_code == 302

    def test_get_form(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:issue-create"))
        assert resp.status_code == 200

    def test_create_issue(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:issue-create"),
            {
                "name": "New Issue",
                "type": IssueType.INTERNAL,
                "category": IssueCategory.STRATEGIC,
                "impact_level": ImpactLevel.MEDIUM,
                "status": IssueStatus.IDENTIFIED,
            },
        )
        assert resp.status_code == 302
        assert Issue.objects.filter(name="New Issue").exists()

    def test_create_sets_created_by(self):
        client, user = _superuser_client()
        client.post(
            reverse("context:issue-create"),
            {
                "name": "Owned Issue",
                "type": IssueType.EXTERNAL,
                "category": IssueCategory.POLITICAL,
                "impact_level": ImpactLevel.LOW,
                "status": IssueStatus.IDENTIFIED,
            },
        )
        issue = Issue.objects.get(name="Owned Issue")
        assert issue.created_by == user


class TestIssueUpdateView:
    def test_get_form(self):
        client, _ = _superuser_client()
        issue = IssueFactory()
        resp = client.get(reverse("context:issue-update", args=[issue.pk]))
        assert resp.status_code == 200

    def test_update_issue(self):
        client, _ = _superuser_client()
        issue = IssueFactory(name="Old Issue")
        resp = client.post(
            reverse("context:issue-update", args=[issue.pk]),
            {
                "name": "Updated Issue",
                "type": issue.type,
                "category": issue.category,
                "impact_level": issue.impact_level,
                "status": IssueStatus.IDENTIFIED,
            },
        )
        assert resp.status_code == 302
        issue.refresh_from_db()
        assert issue.name == "Updated Issue"


class TestIssueDeleteView:
    def test_get_confirmation_page(self):
        client, _ = _superuser_client()
        issue = IssueFactory()
        resp = client.get(reverse("context:issue-delete", args=[issue.pk]))
        assert resp.status_code == 200

    def test_delete_issue(self):
        client, _ = _superuser_client()
        issue = IssueFactory()
        resp = client.post(reverse("context:issue-delete", args=[issue.pk]))
        assert resp.status_code == 302
        assert not Issue.objects.filter(pk=issue.pk).exists()


class TestIssueApproveView:
    def test_approve_issue(self):
        client, user = _superuser_client()
        issue = IssueFactory()
        resp = client.post(reverse("context:issue-approve", args=[issue.pk]))
        assert resp.status_code == 302
        issue.refresh_from_db()
        assert issue.is_approved is True
        assert issue.approved_by == user


class TestIssueTableBodyView:
    def test_returns_200(self):
        client, _ = _superuser_client()
        IssueFactory()
        resp = client.get(reverse("context:issue-table-body"))
        assert resp.status_code == 200

    def test_with_type_filter(self):
        client, _ = _superuser_client()
        IssueFactory(type=IssueType.EXTERNAL, category=IssueCategory.POLITICAL)
        resp = client.get(reverse("context:issue-table-body") + "?type=external")
        assert resp.status_code == 200

    def test_with_status_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:issue-table-body") + "?status=identified")
        assert resp.status_code == 200

    def test_with_impact_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:issue-table-body") + "?impact=high")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════
# Stakeholder Views
# ══════════════════════════════════════════════════════════


class TestStakeholderListView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:stakeholder-list"))
        assert resp.status_code == 302

    def test_list_returns_200(self):
        client, _ = _superuser_client()
        _make_stakeholder()
        resp = client.get(reverse("context:stakeholder-list"))
        assert resp.status_code == 200

    def test_list_with_type_filter(self):
        client, _ = _superuser_client()
        _make_stakeholder(type=IssueType.EXTERNAL)
        resp = client.get(reverse("context:stakeholder-list") + "?type=external")
        assert resp.status_code == 200

    def test_list_with_status_filter(self):
        client, _ = _superuser_client()
        _make_stakeholder()
        resp = client.get(reverse("context:stakeholder-list") + "?status=active")
        assert resp.status_code == 200


class TestStakeholderDetailView:
    def test_requires_login(self):
        sh = _make_stakeholder()
        client = Client()
        resp = client.get(reverse("context:stakeholder-detail", args=[sh.pk]))
        assert resp.status_code == 302

    def test_detail_returns_200(self):
        client, _ = _superuser_client()
        sh = _make_stakeholder()
        resp = client.get(reverse("context:stakeholder-detail", args=[sh.pk]))
        assert resp.status_code == 200

    def test_detail_has_history(self):
        client, _ = _superuser_client()
        sh = _make_stakeholder()
        resp = client.get(reverse("context:stakeholder-detail", args=[sh.pk]))
        assert resp.context["history_available"] is True
        assert "history_url" in resp.context


class TestStakeholderCreateView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:stakeholder-create"))
        assert resp.status_code == 302

    def test_get_form(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:stakeholder-create"))
        assert resp.status_code == 200

    def test_create_stakeholder(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:stakeholder-create"),
            {
                "name": "New Stakeholder",
                "type": IssueType.INTERNAL,
                "category": StakeholderCategory.EMPLOYEES,
                "influence_level": InfluenceLevel.HIGH,
                "interest_level": InfluenceLevel.MEDIUM,
                "status": StakeholderStatus.ACTIVE,
            },
        )
        assert resp.status_code == 302
        assert Stakeholder.objects.filter(name="New Stakeholder").exists()

    def test_create_sets_created_by(self):
        client, user = _superuser_client()
        client.post(
            reverse("context:stakeholder-create"),
            {
                "name": "Owned Stakeholder",
                "type": IssueType.EXTERNAL,
                "category": StakeholderCategory.REGULATORS,
                "influence_level": InfluenceLevel.LOW,
                "interest_level": InfluenceLevel.LOW,
                "status": StakeholderStatus.ACTIVE,
            },
        )
        sh = Stakeholder.objects.get(name="Owned Stakeholder")
        assert sh.created_by == user


class TestStakeholderUpdateView:
    def test_get_form(self):
        client, _ = _superuser_client()
        sh = _make_stakeholder()
        resp = client.get(reverse("context:stakeholder-update", args=[sh.pk]))
        assert resp.status_code == 200

    def test_update_stakeholder(self):
        client, _ = _superuser_client()
        sh = _make_stakeholder(name="Old Name")
        resp = client.post(
            reverse("context:stakeholder-update", args=[sh.pk]),
            {
                "name": "Updated Stakeholder",
                "type": sh.type,
                "category": sh.category,
                "influence_level": sh.influence_level,
                "interest_level": sh.interest_level,
                "status": sh.status,
            },
        )
        assert resp.status_code == 302
        sh.refresh_from_db()
        assert sh.name == "Updated Stakeholder"


class TestStakeholderDeleteView:
    def test_get_confirmation_page(self):
        client, _ = _superuser_client()
        sh = _make_stakeholder()
        resp = client.get(reverse("context:stakeholder-delete", args=[sh.pk]))
        assert resp.status_code == 200

    def test_delete_stakeholder(self):
        client, _ = _superuser_client()
        sh = _make_stakeholder()
        resp = client.post(reverse("context:stakeholder-delete", args=[sh.pk]))
        assert resp.status_code == 302
        assert not Stakeholder.objects.filter(pk=sh.pk).exists()


class TestStakeholderApproveView:
    def test_approve_stakeholder(self):
        client, user = _superuser_client()
        sh = _make_stakeholder()
        resp = client.post(reverse("context:stakeholder-approve", args=[sh.pk]))
        assert resp.status_code == 302
        sh.refresh_from_db()
        assert sh.is_approved is True


class TestStakeholderTableBodyView:
    def test_returns_200(self):
        client, _ = _superuser_client()
        _make_stakeholder()
        resp = client.get(reverse("context:stakeholder-table-body"))
        assert resp.status_code == 200

    def test_with_type_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:stakeholder-table-body") + "?type=internal")
        assert resp.status_code == 200

    def test_with_status_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:stakeholder-table-body") + "?status=active")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════
# Objective Views
# ══════════════════════════════════════════════════════════


class TestObjectiveListView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:objective-list"))
        assert resp.status_code == 302

    def test_list_returns_200(self):
        client, _ = _superuser_client()
        ObjectiveFactory()
        resp = client.get(reverse("context:objective-list"))
        assert resp.status_code == 200

    def test_list_with_status_filter(self):
        client, _ = _superuser_client()
        ObjectiveFactory(status=ObjectiveStatus.ACTIVE)
        resp = client.get(reverse("context:objective-list") + "?status=active")
        assert resp.status_code == 200

    def test_list_with_category_filter(self):
        client, _ = _superuser_client()
        ObjectiveFactory(category=ObjectiveCategory.CONFIDENTIALITY)
        resp = client.get(reverse("context:objective-list") + "?category=confidentiality")
        assert resp.status_code == 200

    def test_list_sorting(self):
        client, _ = _superuser_client()
        ObjectiveFactory()
        resp = client.get(reverse("context:objective-list") + "?sort=name&order=asc")
        assert resp.status_code == 200


class TestObjectiveDetailView:
    def test_requires_login(self):
        obj = ObjectiveFactory()
        client = Client()
        resp = client.get(reverse("context:objective-detail", args=[obj.pk]))
        assert resp.status_code == 302

    def test_detail_returns_200(self):
        client, _ = _superuser_client()
        obj = ObjectiveFactory()
        resp = client.get(reverse("context:objective-detail", args=[obj.pk]))
        assert resp.status_code == 200

    def test_detail_has_history(self):
        client, _ = _superuser_client()
        obj = ObjectiveFactory()
        resp = client.get(reverse("context:objective-detail", args=[obj.pk]))
        assert resp.context["history_available"] is True
        assert "history_url" in resp.context


class TestObjectiveCreateView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:objective-create"))
        assert resp.status_code == 302

    def test_get_form(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:objective-create"))
        assert resp.status_code == 200

    def test_create_objective(self):
        client, user = _superuser_client()
        resp = client.post(
            reverse("context:objective-create"),
            {
                "name": "New Objective",
                "category": ObjectiveCategory.INTEGRITY,
                "type": ObjectiveType.SECURITY,
                "owner": user.pk,
                "status": ObjectiveStatus.DRAFT,
            },
        )
        assert resp.status_code == 302
        assert Objective.objects.filter(name="New Objective").exists()

    def test_create_sets_created_by(self):
        client, user = _superuser_client()
        client.post(
            reverse("context:objective-create"),
            {
                "name": "Owned Objective",
                "category": ObjectiveCategory.COMPLIANCE,
                "type": ObjectiveType.COMPLIANCE,
                "owner": user.pk,
                "status": ObjectiveStatus.DRAFT,
            },
        )
        obj = Objective.objects.get(name="Owned Objective")
        assert obj.created_by == user


class TestObjectiveUpdateView:
    def test_get_form(self):
        client, _ = _superuser_client()
        obj = ObjectiveFactory()
        resp = client.get(reverse("context:objective-update", args=[obj.pk]))
        assert resp.status_code == 200

    def test_update_objective(self):
        client, _ = _superuser_client()
        obj = ObjectiveFactory(name="Old Objective")
        resp = client.post(
            reverse("context:objective-update", args=[obj.pk]),
            {
                "name": "Updated Objective",
                "category": obj.category,
                "type": obj.type,
                "owner": obj.owner.pk,
                "status": obj.status,
            },
        )
        assert resp.status_code == 302
        obj.refresh_from_db()
        assert obj.name == "Updated Objective"


class TestObjectiveDeleteView:
    def test_get_confirmation_page(self):
        client, _ = _superuser_client()
        obj = ObjectiveFactory()
        resp = client.get(reverse("context:objective-delete", args=[obj.pk]))
        assert resp.status_code == 200

    def test_delete_objective(self):
        client, _ = _superuser_client()
        obj = ObjectiveFactory()
        resp = client.post(reverse("context:objective-delete", args=[obj.pk]))
        assert resp.status_code == 302
        assert not Objective.objects.filter(pk=obj.pk).exists()


class TestObjectiveApproveView:
    def test_approve_objective(self):
        client, user = _superuser_client()
        obj = ObjectiveFactory()
        resp = client.post(reverse("context:objective-approve", args=[obj.pk]))
        assert resp.status_code == 302
        obj.refresh_from_db()
        assert obj.is_approved is True
        assert obj.approved_by == user


class TestObjectiveTableBodyView:
    def test_returns_200(self):
        client, _ = _superuser_client()
        ObjectiveFactory()
        resp = client.get(reverse("context:objective-table-body"))
        assert resp.status_code == 200

    def test_with_status_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:objective-table-body") + "?status=active")
        assert resp.status_code == 200

    def test_with_category_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:objective-table-body") + "?category=confidentiality")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════
# Role Views
# ══════════════════════════════════════════════════════════


class TestRoleListView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:role-list"))
        assert resp.status_code == 302

    def test_list_returns_200(self):
        client, _ = _superuser_client()
        _make_role()
        resp = client.get(reverse("context:role-list"))
        assert resp.status_code == 200

    def test_list_with_type_filter(self):
        client, _ = _superuser_client()
        _make_role(type=RoleType.OPERATIONAL)
        resp = client.get(reverse("context:role-list") + "?type=operational")
        assert resp.status_code == 200

    def test_list_with_status_filter(self):
        client, _ = _superuser_client()
        _make_role()
        resp = client.get(reverse("context:role-list") + "?status=active")
        assert resp.status_code == 200


class TestRoleDetailView:
    def test_requires_login(self):
        role = _make_role()
        client = Client()
        resp = client.get(reverse("context:role-detail", args=[role.pk]))
        assert resp.status_code == 302

    def test_detail_returns_200(self):
        client, _ = _superuser_client()
        role = _make_role()
        resp = client.get(reverse("context:role-detail", args=[role.pk]))
        assert resp.status_code == 200

    def test_detail_has_history(self):
        client, _ = _superuser_client()
        role = _make_role()
        resp = client.get(reverse("context:role-detail", args=[role.pk]))
        assert resp.context["history_available"] is True
        assert "history_url" in resp.context


class TestRoleCreateView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:role-create"))
        assert resp.status_code == 302

    def test_get_form(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:role-create"))
        assert resp.status_code == 200

    def test_create_role(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:role-create"),
            {
                "name": "New Role",
                "type": RoleType.SUPPORT,
                "status": RoleStatus.ACTIVE,
            },
        )
        assert resp.status_code == 302
        assert Role.objects.filter(name="New Role").exists()

    def test_create_sets_created_by(self):
        client, user = _superuser_client()
        client.post(
            reverse("context:role-create"),
            {
                "name": "Owned Role",
                "type": RoleType.CONTROL,
                "status": RoleStatus.ACTIVE,
            },
        )
        role = Role.objects.get(name="Owned Role")
        assert role.created_by == user


class TestRoleUpdateView:
    def test_get_form(self):
        client, _ = _superuser_client()
        role = _make_role()
        resp = client.get(reverse("context:role-update", args=[role.pk]))
        assert resp.status_code == 200

    def test_update_role(self):
        client, _ = _superuser_client()
        role = _make_role(name="Old Role")
        resp = client.post(
            reverse("context:role-update", args=[role.pk]),
            {
                "name": "Updated Role",
                "type": role.type,
                "status": role.status,
            },
        )
        assert resp.status_code == 302
        role.refresh_from_db()
        assert role.name == "Updated Role"


class TestRoleDeleteView:
    def test_get_confirmation_page(self):
        client, _ = _superuser_client()
        role = _make_role()
        resp = client.get(reverse("context:role-delete", args=[role.pk]))
        assert resp.status_code == 200

    def test_delete_role(self):
        client, _ = _superuser_client()
        role = _make_role()
        resp = client.post(reverse("context:role-delete", args=[role.pk]))
        assert resp.status_code == 302
        assert not Role.objects.filter(pk=role.pk).exists()


class TestRoleApproveView:
    def test_approve_role(self):
        client, user = _superuser_client()
        role = _make_role()
        resp = client.post(reverse("context:role-approve", args=[role.pk]))
        assert resp.status_code == 302
        role.refresh_from_db()
        assert role.is_approved is True


class TestRoleTableBodyView:
    def test_returns_200(self):
        client, _ = _superuser_client()
        _make_role()
        resp = client.get(reverse("context:role-table-body"))
        assert resp.status_code == 200

    def test_with_type_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:role-table-body") + "?type=governance")
        assert resp.status_code == 200

    def test_with_status_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:role-table-body") + "?status=active")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════
# Activity Views
# ══════════════════════════════════════════════════════════


class TestActivityListView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:activity-list"))
        assert resp.status_code == 302

    def test_list_returns_200(self):
        client, user = _superuser_client()
        _make_activity(owner=user)
        resp = client.get(reverse("context:activity-list"))
        assert resp.status_code == 200

    def test_list_with_criticality_filter(self):
        client, user = _superuser_client()
        _make_activity(owner=user, criticality=Criticality.HIGH)
        resp = client.get(reverse("context:activity-list") + "?criticality=high")
        assert resp.status_code == 200

    def test_list_with_status_filter(self):
        client, user = _superuser_client()
        _make_activity(owner=user)
        resp = client.get(reverse("context:activity-list") + "?status=active")
        assert resp.status_code == 200


class TestActivityDetailView:
    def test_requires_login(self):
        user = UserFactory(is_superuser=True)
        activity = _make_activity(owner=user)
        client = Client()
        resp = client.get(reverse("context:activity-detail", args=[activity.pk]))
        assert resp.status_code == 302

    def test_detail_returns_200(self):
        client, user = _superuser_client()
        activity = _make_activity(owner=user)
        resp = client.get(reverse("context:activity-detail", args=[activity.pk]))
        assert resp.status_code == 200

    def test_detail_has_history(self):
        client, user = _superuser_client()
        activity = _make_activity(owner=user)
        resp = client.get(reverse("context:activity-detail", args=[activity.pk]))
        assert resp.context["history_available"] is True
        assert "history_url" in resp.context


class TestActivityCreateView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:activity-create"))
        assert resp.status_code == 302

    def test_get_form(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:activity-create"))
        assert resp.status_code == 200

    def test_create_activity(self):
        client, user = _superuser_client()
        resp = client.post(
            reverse("context:activity-create"),
            {
                "name": "New Activity",
                "type": ActivityType.SUPPORT,
                "criticality": Criticality.LOW,
                "owner": user.pk,
                "status": ActivityStatus.ACTIVE,
            },
        )
        assert resp.status_code == 302
        assert Activity.objects.filter(name="New Activity").exists()

    def test_create_sets_created_by(self):
        client, user = _superuser_client()
        client.post(
            reverse("context:activity-create"),
            {
                "name": "Owned Activity",
                "type": ActivityType.MANAGEMENT,
                "criticality": Criticality.CRITICAL,
                "owner": user.pk,
                "status": ActivityStatus.PLANNED,
            },
        )
        activity = Activity.objects.get(name="Owned Activity")
        assert activity.created_by == user


class TestActivityUpdateView:
    def test_get_form(self):
        client, user = _superuser_client()
        activity = _make_activity(owner=user)
        resp = client.get(reverse("context:activity-update", args=[activity.pk]))
        assert resp.status_code == 200

    def test_update_activity(self):
        client, user = _superuser_client()
        activity = _make_activity(owner=user, name="Old Activity")
        resp = client.post(
            reverse("context:activity-update", args=[activity.pk]),
            {
                "name": "Updated Activity",
                "type": activity.type,
                "criticality": activity.criticality,
                "owner": user.pk,
                "status": activity.status,
            },
        )
        assert resp.status_code == 302
        activity.refresh_from_db()
        assert activity.name == "Updated Activity"


class TestActivityDeleteView:
    def test_get_confirmation_page(self):
        client, user = _superuser_client()
        activity = _make_activity(owner=user)
        resp = client.get(reverse("context:activity-delete", args=[activity.pk]))
        assert resp.status_code == 200

    def test_delete_activity(self):
        client, user = _superuser_client()
        activity = _make_activity(owner=user)
        resp = client.post(reverse("context:activity-delete", args=[activity.pk]))
        assert resp.status_code == 302
        assert not Activity.objects.filter(pk=activity.pk).exists()


class TestActivityApproveView:
    def test_approve_activity(self):
        client, user = _superuser_client()
        activity = _make_activity(owner=user)
        resp = client.post(reverse("context:activity-approve", args=[activity.pk]))
        assert resp.status_code == 302
        activity.refresh_from_db()
        assert activity.is_approved is True


class TestActivityTableBodyView:
    def test_returns_200(self):
        client, user = _superuser_client()
        _make_activity(owner=user)
        resp = client.get(reverse("context:activity-table-body"))
        assert resp.status_code == 200

    def test_with_criticality_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:activity-table-body") + "?criticality=high")
        assert resp.status_code == 200

    def test_with_status_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:activity-table-body") + "?status=active")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════
# Tag Views
# ══════════════════════════════════════════════════════════


class TestTagListView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:tag-list"))
        assert resp.status_code == 302

    def test_list_returns_200(self):
        client, _ = _superuser_client()
        _make_tag()
        resp = client.get(reverse("context:tag-list"))
        assert resp.status_code == 200

    def test_list_shows_usage_counts(self):
        client, _ = _superuser_client()
        tag = _make_tag(name="used-tag")
        scope = ScopeFactory()
        scope.tags.add(tag)
        resp = client.get(reverse("context:tag-list"))
        assert resp.status_code == 200


class TestTagUpdateView:
    def test_get_form(self):
        client, _ = _superuser_client()
        tag = _make_tag()
        resp = client.get(reverse("context:tag-update", args=[tag.pk]))
        assert resp.status_code == 200

    def test_update_tag(self):
        client, _ = _superuser_client()
        tag = _make_tag(name="old-tag")
        resp = client.post(
            reverse("context:tag-update", args=[tag.pk]),
            {"name": "updated-tag", "color": "#000000"},
        )
        assert resp.status_code == 302
        tag.refresh_from_db()
        assert tag.name == "updated-tag"
        assert tag.color == "#000000"


class TestTagDeleteView:
    def test_get_confirmation_page(self):
        client, _ = _superuser_client()
        tag = _make_tag()
        resp = client.get(reverse("context:tag-delete", args=[tag.pk]))
        assert resp.status_code == 200

    def test_delete_tag(self):
        client, _ = _superuser_client()
        tag = _make_tag()
        resp = client.post(reverse("context:tag-delete", args=[tag.pk]))
        assert resp.status_code == 302
        assert not Tag.objects.filter(pk=tag.pk).exists()


class TestTagCreateInline:
    def test_requires_login(self):
        client = Client()
        resp = client.post(
            reverse("context:tag-create-inline"),
            json.dumps({"name": "test"}),
            content_type="application/json",
        )
        assert resp.status_code == 302

    def test_create_tag(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:tag-create-inline"),
            json.dumps({"name": "ajax-tag"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "ajax-tag"
        assert Tag.objects.filter(name="ajax-tag").exists()

    def test_get_or_create_existing_tag(self):
        """Submitting a name that already exists returns the existing tag."""
        client, _ = _superuser_client()
        existing = _make_tag(name="existing-tag")
        resp = client.post(
            reverse("context:tag-create-inline"),
            json.dumps({"name": "existing-tag"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(existing.pk)

    def test_empty_name_returns_400(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:tag-create-inline"),
            json.dumps({"name": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_invalid_json_returns_400(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:tag-create-inline"),
            "not json",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_name_returns_400(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:tag-create-inline"),
            json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_only_post_allowed(self):
        """GET requests should not be allowed."""
        client, _ = _superuser_client()
        resp = client.get(reverse("context:tag-create-inline"))
        assert resp.status_code == 405


# ══════════════════════════════════════════════════════════
# Indicator Views
# ══════════════════════════════════════════════════════════


class TestIndicatorListView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:indicator-organizational-list"))
        assert resp.status_code == 302

    def test_organizational_list_returns_200(self):
        client, _ = _superuser_client()
        _make_indicator(indicator_type=IndicatorType.ORGANIZATIONAL)
        resp = client.get(reverse("context:indicator-organizational-list"))
        assert resp.status_code == 200

    def test_technical_list_returns_200(self):
        client, _ = _superuser_client()
        _make_indicator(indicator_type=IndicatorType.TECHNICAL)
        resp = client.get(reverse("context:indicator-technical-list"))
        assert resp.status_code == 200

    def test_list_with_status_filter(self):
        client, _ = _superuser_client()
        _make_indicator()
        resp = client.get(
            reverse("context:indicator-organizational-list") + "?status=active"
        )
        assert resp.status_code == 200

    def test_list_context_has_indicator_type(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:indicator-organizational-list"))
        assert resp.context["indicator_type"] == IndicatorType.ORGANIZATIONAL

    def test_technical_list_context_has_indicator_type(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:indicator-technical-list"))
        assert resp.context["indicator_type"] == IndicatorType.TECHNICAL


class TestIndicatorDetailView:
    def test_requires_login(self):
        ind = _make_indicator()
        client = Client()
        resp = client.get(reverse("context:indicator-detail", args=[ind.pk]))
        assert resp.status_code == 302

    def test_detail_returns_200(self):
        client, _ = _superuser_client()
        ind = _make_indicator()
        resp = client.get(reverse("context:indicator-detail", args=[ind.pk]))
        assert resp.status_code == 200

    def test_detail_has_measurement_form(self):
        client, _ = _superuser_client()
        ind = _make_indicator()
        resp = client.get(reverse("context:indicator-detail", args=[ind.pk]))
        assert "measurement_form" in resp.context

    def test_detail_has_history(self):
        client, _ = _superuser_client()
        ind = _make_indicator()
        resp = client.get(reverse("context:indicator-detail", args=[ind.pk]))
        assert resp.context["history_available"] is True
        assert "history_url" in resp.context

    def test_detail_shows_measurements(self):
        client, user = _superuser_client()
        ind = _make_indicator()
        ind.record_measurement(value="42", recorded_by=user, notes="first")
        resp = client.get(reverse("context:indicator-detail", args=[ind.pk]))
        assert "measurements" in resp.context


class TestIndicatorCreateView:
    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("context:indicator-organizational-create"))
        assert resp.status_code == 302

    def test_get_form_organizational(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:indicator-organizational-create"))
        assert resp.status_code == 200

    def test_get_form_technical(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:indicator-technical-create"))
        assert resp.status_code == 200

    def test_create_organizational_indicator(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:indicator-organizational-create"),
            {
                "name": "New Org Indicator",
                "collection_method": CollectionMethod.MANUAL,
                "format": IndicatorFormat.NUMBER,
                "review_frequency": MeasurementFrequency.MONTHLY,
                "first_review_date": "2099-01-01",
                "status": IndicatorStatus.ACTIVE,
            },
        )
        assert resp.status_code == 302
        ind = Indicator.objects.get(name="New Org Indicator")
        assert ind.indicator_type == IndicatorType.ORGANIZATIONAL

    def test_create_technical_indicator(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:indicator-technical-create"),
            {
                "name": "New Tech Indicator",
                "collection_method": CollectionMethod.MANUAL,
                "format": IndicatorFormat.BOOLEAN,
                "review_frequency": MeasurementFrequency.WEEKLY,
                "first_review_date": "2099-06-01",
                "status": IndicatorStatus.DRAFT,
            },
        )
        assert resp.status_code == 302
        ind = Indicator.objects.get(name="New Tech Indicator")
        assert ind.indicator_type == IndicatorType.TECHNICAL

    def test_create_sets_created_by(self):
        client, user = _superuser_client()
        client.post(
            reverse("context:indicator-organizational-create"),
            {
                "name": "Owned Indicator",
                "collection_method": CollectionMethod.MANUAL,
                "format": IndicatorFormat.NUMBER,
                "review_frequency": MeasurementFrequency.QUARTERLY,
                "first_review_date": "2099-01-01",
                "status": IndicatorStatus.ACTIVE,
            },
        )
        ind = Indicator.objects.get(name="Owned Indicator")
        assert ind.created_by == user

    def test_create_context_has_indicator_type(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:indicator-organizational-create"))
        assert resp.context["indicator_type"] == IndicatorType.ORGANIZATIONAL


class TestPredefinedIndicatorCreateView:
    def test_get_form(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:indicator-predefined-create"))
        assert resp.status_code == 200

    def test_create_predefined_indicator(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:indicator-predefined-create"),
            {
                "name": "Approved Scopes Rate",
                "internal_source": PredefinedIndicatorSource.APPROVED_SCOPES_RATE,
                "review_frequency": MeasurementFrequency.MONTHLY,
                "first_review_date": "2099-01-01",
                "status": IndicatorStatus.ACTIVE,
            },
        )
        assert resp.status_code == 302
        ind = Indicator.objects.get(name="Approved Scopes Rate")
        assert ind.is_internal is True
        assert ind.indicator_type == IndicatorType.ORGANIZATIONAL
        assert ind.collection_method == CollectionMethod.INTERNAL

    def test_predefined_records_initial_measurement(self):
        client, _ = _superuser_client()
        client.post(
            reverse("context:indicator-predefined-create"),
            {
                "name": "Mandatory Roles",
                "internal_source": PredefinedIndicatorSource.MANDATORY_ROLES_COVERAGE,
                "review_frequency": MeasurementFrequency.MONTHLY,
                "first_review_date": "2099-01-01",
                "status": IndicatorStatus.ACTIVE,
            },
        )
        ind = Indicator.objects.get(name="Mandatory Roles")
        assert IndicatorMeasurement.objects.filter(indicator=ind).exists()


class TestIndicatorUpdateView:
    def test_get_form(self):
        client, _ = _superuser_client()
        ind = _make_indicator()
        resp = client.get(reverse("context:indicator-update", args=[ind.pk]))
        assert resp.status_code == 200

    def test_update_indicator(self):
        client, _ = _superuser_client()
        ind = _make_indicator(name="Old Indicator")
        resp = client.post(
            reverse("context:indicator-update", args=[ind.pk]),
            {
                "name": "Updated Indicator",
                "collection_method": ind.collection_method,
                "format": ind.format,
                "review_frequency": ind.review_frequency,
                "first_review_date": str(ind.first_review_date),
                "status": ind.status,
            },
        )
        assert resp.status_code == 302
        ind.refresh_from_db()
        assert ind.name == "Updated Indicator"

    def test_update_predefined_indicator_uses_predefined_form(self):
        client, _ = _superuser_client()
        ind = _make_indicator(
            is_internal=True,
            internal_source=PredefinedIndicatorSource.APPROVED_SCOPES_RATE,
            collection_method=CollectionMethod.INTERNAL,
        )
        resp = client.get(reverse("context:indicator-update", args=[ind.pk]))
        assert resp.status_code == 200

    def test_update_context_has_indicator_type(self):
        client, _ = _superuser_client()
        ind = _make_indicator(indicator_type=IndicatorType.TECHNICAL)
        resp = client.get(reverse("context:indicator-update", args=[ind.pk]))
        assert resp.context["indicator_type"] == IndicatorType.TECHNICAL


class TestIndicatorDeleteView:
    def test_get_confirmation_page(self):
        client, _ = _superuser_client()
        ind = _make_indicator()
        resp = client.get(reverse("context:indicator-delete", args=[ind.pk]))
        assert resp.status_code == 200

    def test_delete_organizational_indicator(self):
        client, _ = _superuser_client()
        ind = _make_indicator(indicator_type=IndicatorType.ORGANIZATIONAL)
        resp = client.post(reverse("context:indicator-delete", args=[ind.pk]))
        assert resp.status_code == 302
        assert not Indicator.objects.filter(pk=ind.pk).exists()

    def test_delete_technical_indicator_redirects_correctly(self):
        client, _ = _superuser_client()
        ind = _make_indicator(indicator_type=IndicatorType.TECHNICAL)
        resp = client.post(reverse("context:indicator-delete", args=[ind.pk]))
        assert resp.status_code == 302
        assert not Indicator.objects.filter(pk=ind.pk).exists()


class TestIndicatorApproveView:
    def test_approve_indicator(self):
        client, user = _superuser_client()
        ind = _make_indicator()
        resp = client.post(reverse("context:indicator-approve", args=[ind.pk]))
        assert resp.status_code == 302
        ind.refresh_from_db()
        assert ind.is_approved is True


class TestIndicatorTableBodyView:
    def test_returns_200(self):
        client, _ = _superuser_client()
        _make_indicator()
        resp = client.get(reverse("context:indicator-table-body"))
        assert resp.status_code == 200

    def test_with_indicator_type_filter(self):
        client, _ = _superuser_client()
        _make_indicator(indicator_type=IndicatorType.ORGANIZATIONAL)
        resp = client.get(
            reverse("context:indicator-table-body") + "?indicator_type=organizational"
        )
        assert resp.status_code == 200

    def test_with_status_filter(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:indicator-table-body") + "?status=active")
        assert resp.status_code == 200


class TestIndicatorRecordMeasurementView:
    def test_requires_login(self):
        ind = _make_indicator()
        client = Client()
        resp = client.post(
            reverse("context:indicator-record", args=[ind.pk]),
            {"value": "42", "notes": "test"},
        )
        assert resp.status_code == 302

    def test_record_measurement(self):
        client, _ = _superuser_client()
        ind = _make_indicator()
        resp = client.post(
            reverse("context:indicator-record", args=[ind.pk]),
            {"value": "42", "notes": "recorded"},
        )
        assert resp.status_code == 302
        ind.refresh_from_db()
        assert ind.current_value == "42"
        assert IndicatorMeasurement.objects.filter(indicator=ind).exists()

    def test_record_invalid_measurement(self):
        """Missing value should show error and redirect."""
        client, _ = _superuser_client()
        ind = _make_indicator()
        resp = client.post(
            reverse("context:indicator-record", args=[ind.pk]),
            {"value": "", "notes": ""},
        )
        assert resp.status_code == 302  # redirects back with error message


class TestIndicatorRefreshView:
    def test_requires_login(self):
        ind = _make_indicator(
            is_internal=True,
            internal_source=PredefinedIndicatorSource.APPROVED_SCOPES_RATE,
            collection_method=CollectionMethod.INTERNAL,
        )
        client = Client()
        resp = client.post(reverse("context:indicator-refresh", args=[ind.pk]))
        assert resp.status_code == 302

    def test_refresh_predefined_indicator(self):
        client, _ = _superuser_client()
        ind = _make_indicator(
            is_internal=True,
            internal_source=PredefinedIndicatorSource.APPROVED_SCOPES_RATE,
            collection_method=CollectionMethod.INTERNAL,
        )
        resp = client.post(reverse("context:indicator-refresh", args=[ind.pk]))
        assert resp.status_code == 302
        assert IndicatorMeasurement.objects.filter(indicator=ind).exists()

    def test_refresh_non_predefined_shows_error(self):
        """Non-predefined indicators should show an error."""
        client, _ = _superuser_client()
        ind = _make_indicator(is_internal=False)
        resp = client.post(reverse("context:indicator-refresh", args=[ind.pk]))
        assert resp.status_code == 302


# ══════════════════════════════════════════════════════════
# Dashboard Indicator Toggle Views
# ══════════════════════════════════════════════════════════


class TestDashboardIndicatorToggle:
    def test_requires_login(self):
        client = Client()
        resp = client.post(
            reverse("context:dashboard-indicator-toggle"),
            json.dumps({"indicator_id": "test"}),
            content_type="application/json",
        )
        assert resp.status_code == 302

    def test_pin_indicator(self):
        client, user = _superuser_client()
        ind = _make_indicator()
        resp = client.post(
            reverse("context:dashboard-indicator-toggle"),
            json.dumps({"indicator_id": str(ind.pk)}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "added"
        user.refresh_from_db()
        assert str(ind.pk) in user.dashboard_indicators

    def test_unpin_indicator(self):
        client, user = _superuser_client()
        ind = _make_indicator()
        user.dashboard_indicators = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators"])
        resp = client.post(
            reverse("context:dashboard-indicator-toggle"),
            json.dumps({"indicator_id": str(ind.pk)}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "removed"

    def test_invalid_json_returns_400(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:dashboard-indicator-toggle"),
            "bad json",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_indicator_id_returns_400(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:dashboard-indicator-toggle"),
            json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_nonexistent_indicator_returns_404(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:dashboard-indicator-toggle"),
            json.dumps({"indicator_id": "00000000-0000-0000-0000-000000000000"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_max_pinned_indicators(self):
        client, user = _superuser_client()
        # Pin 10 indicators (the max)
        pinned = []
        for i in range(10):
            ind = _make_indicator(name=f"Indicator {i}")
            pinned.append(str(ind.pk))
        user.dashboard_indicators = pinned
        user.save(update_fields=["dashboard_indicators"])
        # Try to pin an 11th
        extra = _make_indicator(name="Extra Indicator")
        resp = client.post(
            reverse("context:dashboard-indicator-toggle"),
            json.dumps({"indicator_id": str(extra.pk)}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestDashboardIndicatorChartToggle:
    def test_requires_login(self):
        client = Client()
        resp = client.post(
            reverse("context:dashboard-indicator-chart-toggle"),
            json.dumps({"indicator_id": "test"}),
            content_type="application/json",
        )
        assert resp.status_code == 302

    def test_show_chart(self):
        client, user = _superuser_client()
        ind = _make_indicator()
        resp = client.post(
            reverse("context:dashboard-indicator-chart-toggle"),
            json.dumps({"indicator_id": str(ind.pk)}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "shown"
        user.refresh_from_db()
        assert str(ind.pk) in user.dashboard_indicator_charts

    def test_hide_chart(self):
        client, user = _superuser_client()
        ind = _make_indicator()
        user.dashboard_indicator_charts = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicator_charts"])
        resp = client.post(
            reverse("context:dashboard-indicator-chart-toggle"),
            json.dumps({"indicator_id": str(ind.pk)}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "hidden"

    def test_invalid_json_returns_400(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:dashboard-indicator-chart-toggle"),
            "nope",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_indicator_id_returns_400(self):
        client, _ = _superuser_client()
        resp = client.post(
            reverse("context:dashboard-indicator-chart-toggle"),
            json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════
# ApproveView edge cases
# ══════════════════════════════════════════════════════════


class TestApproveViewEdgeCases:
    def test_approve_only_accepts_post(self):
        """GET requests to approve should return 405."""
        client, _ = _superuser_client()
        scope = ScopeFactory()
        resp = client.get(reverse("context:scope-approve", args=[scope.pk]))
        assert resp.status_code == 405

    def test_approve_with_referer_redirects_back(self):
        """Approve should redirect back to the HTTP_REFERER if present."""
        client, user = _superuser_client()
        scope = ScopeFactory()
        detail_url = reverse("context:scope-detail", args=[scope.pk])
        resp = client.post(
            reverse("context:scope-approve", args=[scope.pk]),
            HTTP_REFERER=detail_url,
        )
        assert resp.status_code == 302
        assert resp.url == detail_url


# ══════════════════════════════════════════════════════════
# Context dashboard redirect
# ══════════════════════════════════════════════════════════


class TestContextDashboardRedirect:
    def test_root_redirects_to_scope_list(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("context:dashboard"))
        assert resp.status_code == 302
        assert "scopes" in resp.url

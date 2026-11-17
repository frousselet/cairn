# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A list page costs the same number of queries whatever its number of rows.

These lists used to read their tags, their scope ancestors and their filter
options one row (or one option) at a time : a page of fifty rows issued
hundreds of queries. The tests compare the cost of a short and a longer list,
so they fail on any per-row query, not on a hand-tuned ceiling.
"""

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.tests.factories import UserFactory
from context.constants import RoleType
from context.models import Role, Tag
from context.tests.factories import IssueFactory, ScopeFactory

pytestmark = pytest.mark.django_db


def _queries(client, url):
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200
    return len(ctx.captured_queries)


@pytest.fixture
def admin_client():
    client = Client()
    client.force_login(UserFactory(is_superuser=True))
    return client


def _nested_scope():
    """A scope three levels deep, so its ancestors have to be resolved."""
    root = ScopeFactory()
    middle = ScopeFactory(parent_scope=root)
    return ScopeFactory(parent_scope=middle)


def _issue(tags):
    issue = IssueFactory()
    issue.scopes.add(_nested_scope())
    issue.tags.set(tags)
    return issue


def test_issue_list_cost_does_not_grow_with_its_rows(admin_client):
    tags = [Tag.objects.create(name=f"tag-{i}") for i in range(3)]
    url = reverse("context:issue-list")
    for _ in range(2):
        _issue(tags)
    short = _queries(admin_client, url)
    for _ in range(8):
        _issue(tags)
    longer = _queries(admin_client, url)
    assert longer == short


def test_site_list_cost_does_not_grow_with_its_rows(admin_client):
    """The site list is not a sortable list : it prefetches its tags itself."""
    from context.tests.factories import SiteFactory

    tags = [Tag.objects.create(name=f"site-tag-{i}") for i in range(2)]
    url = reverse("assets:site-list")
    for _ in range(2):
        SiteFactory().tags.set(tags)
    short = _queries(admin_client, url)
    for _ in range(8):
        SiteFactory().tags.set(tags)
    longer = _queries(admin_client, url)
    assert longer == short


def test_role_list_cost_does_not_grow_with_its_rows(admin_client):
    users = [UserFactory() for _ in range(3)]
    url = reverse("context:role-list")

    def role():
        instance = Role.objects.create(name="Role", type=RoleType.choices[0][0])
        instance.assigned_users.set(users)
        return instance

    for _ in range(2):
        role()
    short = _queries(admin_client, url)
    for _ in range(8):
        role()
    longer = _queries(admin_client, url)
    assert longer == short


def test_tag_list_cost_does_not_grow_with_its_tags(admin_client):
    """Usage was counted relation by relation for each tag."""
    url = reverse("context:tag-list")
    issue = IssueFactory()
    for i in range(2):
        issue.tags.add(Tag.objects.create(name=f"probe-{i}"))
    short = _queries(admin_client, url)
    for i in range(2, 12):
        issue.tags.add(Tag.objects.create(name=f"probe-{i}"))
    longer = _queries(admin_client, url)
    assert longer == short


def test_tag_list_still_counts_usage(admin_client):
    tag = Tag.objects.create(name="counted")
    IssueFactory().tags.add(tag)
    IssueFactory().tags.add(tag)
    response = admin_client.get(reverse("context:tag-list"))
    listed = next(t for t in response.context["tags"] if t.pk == tag.pk)
    assert listed.usage_total == 2
    assert [count for _name, count in listed.usage] == [2]


def test_dashboard_reads_indicator_measurements_from_the_prefetch():
    """The dashboard prefetches the measurements of its indicators; ordering
    and slicing them in the database threw that away, one query per indicator."""
    from datetime import timedelta

    from django.utils import timezone

    from context.models import Indicator, IndicatorMeasurement
    from context.views import build_indicator_slot

    created = Indicator.objects.create(
        review_frequency="monthly", first_review_date="2025-01-01", name="Probe",
        indicator_type="technical", collection_method="manual", format="number",
    )
    now = timezone.now()
    for days, value in ((3, "10"), (2, "20"), (1, "30")):
        IndicatorMeasurement.objects.create(
            indicator=created, value=value, recorded_at=now - timedelta(days=days),
        )
    indicator = Indicator.objects.prefetch_related("measurements").get(pk=created.pk)
    with CaptureQueriesContext(connection) as ctx:
        slot = build_indicator_slot(indicator, True)
    assert not [q for q in ctx.captured_queries if "indicatormeasurement" in q["sql"]]
    # Same answer as the database ordering gave : the latest measurement first.
    assert str(slot["current_measurement"].value) == "30"
    assert str(slot["previous_measurement"].value) == "20"


def test_filter_options_are_read_once_and_not_per_option(admin_client):
    """The advanced filter lists the records of each relation. It was built
    twice per request and labelled each option with a query of its own."""
    from accounts.tests.factories import PermissionFactory

    url = reverse("accounts:user-list")
    short = _queries(admin_client, url)
    for i in range(25):
        PermissionFactory(codename=f"probe.feature{i}.read")
    longer = _queries(admin_client, url)
    assert longer == short


def test_scope_ancestors_are_resolved_without_walking_the_tree():
    """The scope cell names the ancestors of each scope from one shared read."""
    from django.template import Context, Template
    from django.test import RequestFactory

    leaves = [_nested_scope() for _ in range(5)]
    request = RequestFactory().get("/")
    template = Template(
        "{% load scope_tags %}{% for s in scopes %}{% scope_popover s %}{% endfor %}"
    )
    context = Context({"request": request, "scopes": [[leaf] for leaf in leaves]})
    with CaptureQueriesContext(connection) as ctx:
        html = template.render(context)
    assert len(ctx.captured_queries) == 1
    # Each leaf is printed with its two ancestors.
    assert leaves[0].parent_scope.parent_scope.name in html

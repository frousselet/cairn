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

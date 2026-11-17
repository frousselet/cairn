# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The action log reads one page of the audit trail, never all of it.

It first loaded every row of every history table and sorted them in memory on
each visit. ``MergedHistory`` asks the database for the page only; these tests
pin that the cost of a visit does not follow the size of the history, and that
the page shows what the full sort showed.
"""

from itertools import chain
from operator import attrgetter

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.action_log import MergedHistory, entry_kind
from accounts.tests.factories import UserFactory
from accounts.views import ActionLogListView, _get_model_labels
from context.models import Scope
from context.tests.factories import IssueFactory, ScopeFactory
from core.history import EntryKind, classify_record

pytestmark = pytest.mark.django_db


def _history_models():
    labels = _get_model_labels()
    return [m for m in ActionLogListView()._get_historical_models() if labels.get(m, (None, None))[0]]


def _client():
    client = Client()
    client.force_login(UserFactory(is_superuser=True))
    return client


def _edit(scope, times):
    for index in range(times):
        scope.description = f"revision {index}"
        scope.save()


class TestMergedHistory:
    def test_it_lists_every_table_newest_first(self):
        scope = ScopeFactory(name="Head office")
        IssueFactory()
        _edit(scope, 3)
        merged = MergedHistory(_history_models())
        expected = sorted(
            chain(*[model.objects.all() for model in _history_models()]),
            key=attrgetter("history_date"), reverse=True,
        )
        assert merged.count() == len(expected) >= 5
        page = merged[0:len(expected)]
        assert [row.history_date for row in page] == [row.history_date for row in expected]
        assert {(type(row), row.history_id) for row in page} == {(type(row), row.history_id) for row in expected}

    def test_pages_do_not_overlap_and_miss_nothing(self):
        """Rows saved at the same instant must not swap places between two
        slices : the order has a tie-break."""
        scope = ScopeFactory()
        _edit(scope, 12)
        IssueFactory.create_batch(4)
        merged = MergedHistory(_history_models())
        total = merged.count()
        seen = []
        for start in range(0, total, 5):
            seen.extend((type(row).__name__, row.history_id) for row in merged[start:start + 5])
        assert len(seen) == total
        assert len(set(seen)) == total

    def test_a_page_costs_the_same_whatever_the_size_of_the_history(self):
        scope = ScopeFactory()
        _edit(scope, 30)
        merged = MergedHistory(_history_models())
        with CaptureQueriesContext(connection) as small:
            merged[0:20]
        _edit(scope, 200)
        merged = MergedHistory(_history_models())
        with CaptureQueriesContext(connection) as large:
            rows = merged[0:20]
        assert len(rows) == 20
        assert len(large) == len(small) <= 3

    def test_only_a_slice_can_be_read(self):
        with pytest.raises(TypeError):
            MergedHistory(_history_models())[0]

    def test_no_table_is_an_empty_log(self):
        merged = MergedHistory([])
        assert merged.count() == 0 and merged[0:10] == []


class TestEntryKind:
    def test_it_agrees_with_the_history_classifier(self):
        """Creation, update, lifecycle transition and deletion : the same
        answer as ``classify_record``, without its query per row."""
        user = UserFactory(is_superuser=True)
        scope = ScopeFactory(name="Plant")
        scope.description = "changed"
        scope.save()
        scope.transition_to("definition", user)
        doomed = ScopeFactory(name="Closed site")
        doomed.delete()
        rows = MergedHistory(_history_models())[0:50]
        kinds = {entry_kind(row) for row in rows if isinstance(row, Scope.history.model)}
        assert kinds == {EntryKind.CREATE, EntryKind.UPDATE, EntryKind.TRANSITION, EntryKind.DELETE}
        for row in rows:
            assert entry_kind(row) == classify_record(row), (type(row).__name__, row.history_type)

    def test_classifying_a_page_runs_no_query(self):
        scope = ScopeFactory()
        _edit(scope, 10)
        rows = MergedHistory(_history_models())[0:20]
        with CaptureQueriesContext(connection) as queries:
            for row in rows:
                entry_kind(row)
        assert len(queries) == 0


class TestActionLogPage:
    def test_the_page_does_not_read_the_whole_history(self):
        """The number of queries of a visit is bounded by the page, not by
        the number of rows behind it."""
        scope = ScopeFactory()
        _edit(scope, 60)
        client = _client()
        url = reverse("accounts:action-log-list")
        with CaptureQueriesContext(connection) as before:
            assert client.get(url).status_code == 200
        _edit(scope, 300)
        with CaptureQueriesContext(connection) as after:
            response = client.get(url)
        assert len(after) <= len(before)
        assert len(response.context["entries"]) == 50
        assert response.context["list_kpis"][0]["value"] >= 361

    def test_the_last_page_is_reachable(self):
        scope = ScopeFactory()
        _edit(scope, 70)
        response = _client().get(reverse("accounts:action-log-list") + "?page=2")
        assert response.status_code == 200
        assert 1 <= len(response.context["entries"]) <= 50

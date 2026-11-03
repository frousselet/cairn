# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The advanced filter's relation options honour the reader's scopes.

The options are rendered into every list page; they used to list up to 200
rows of each related model unscoped, printing the names of records outside
the reader's perimeter (e.g. the risk assessments of another scope).
"""
import pytest
from django.test import RequestFactory

from accounts.tests.factories import GroupFactory, UserFactory
from context.tests.factories import ScopeFactory
from risks.tests.factories import RiskAssessmentFactory
from risks.views import RiskListView

pytestmark = pytest.mark.django_db


def _options(user):
    view = RiskListView()
    view.request = RequestFactory().get("/")
    view.request.user = user
    field = next(f for f in view.get_filter_fields() if f["key"] == "assessment")
    return {o["label"] for o in field["options"]}


def test_relation_options_are_scoped():
    mine, other = ScopeFactory(), ScopeFactory()
    visible = RiskAssessmentFactory(name="Visible assessment")
    visible.scopes.add(mine)
    hidden = RiskAssessmentFactory(name="Hidden assessment")
    hidden.scopes.add(other)
    user = UserFactory()
    group = GroupFactory()
    group.users.add(user)
    group.allowed_scopes.add(mine)

    labels = _options(user)
    assert any("Visible assessment" in label for label in labels)
    assert not any("Hidden assessment" in label for label in labels)
    assert any("Hidden assessment" in label for label in _options(UserFactory(is_superuser=True)))


def test_lifecycle_lookup_accepts_a_model_label():
    """reportable_states("documents.Policy") used to answer the default
    lifecycle's {"validated"}, a code the Policy lifecycle does not have."""
    from core.lifecycle import reportable_states
    from documents.models import Policy

    assert reportable_states("documents.Policy") == reportable_states(Policy) == {"active"}

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Choosing an assessment on the risk form reloads its likelihood / impact scales.

The behaviour is declared on the form (data-scale-source / data-scale-target)
and wired once in base.html, so it works in the modal and on the page alike;
the endpoint only answers for an assessment the user may see.
"""
import json

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import GroupFactory, UserFactory
from context.tests.factories import ScopeFactory
from risks.forms import RiskCreateForm
from risks.tests.factories import RiskAssessmentFactory, RiskCriteriaFactory, ScaleLevelFactory

pytestmark = pytest.mark.django_db


def test_the_form_declares_the_dependent_scales():
    form = RiskCreateForm()
    assert form.fields["assessment"].widget.attrs["data-scale-source"] == reverse("risks:api-scale-choices")
    assert form.fields["initial_likelihood"].widget.attrs["data-scale-target"] == "likelihood"
    assert form.fields["current_impact"].widget.attrs["data-scale-target"] == "impact"


def _assessment_with_scale(label):
    criteria = RiskCriteriaFactory()
    ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=1, name=label)
    assessment = RiskAssessmentFactory(risk_criteria=criteria)
    return assessment


def _labels(client, assessment):
    resp = client.get(reverse("risks:api-scale-choices"), {"assessment": assessment.pk})
    return [c["label"] for c in json.loads(resp.content)["likelihood"]]


def test_scales_come_from_a_visible_assessment_only():
    mine_scope, other_scope = ScopeFactory(), ScopeFactory()
    mine = _assessment_with_scale("Mine")
    mine.scopes.add(mine_scope)
    other = _assessment_with_scale("Secret")
    other.scopes.add(other_scope)

    user = UserFactory()
    group = GroupFactory()
    group.users.add(user)
    group.allowed_scopes.add(mine_scope)
    client = Client()
    client.force_login(user)

    assert "1 - Mine" in _labels(client, mine)
    assert "1 - Secret" not in _labels(client, other)

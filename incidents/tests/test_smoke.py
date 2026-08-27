# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Smoke tests for the incidents module foundation.

The lifecycle binding test is the important one : omitting the
``incidents.lifecycles`` import from ``IncidentsConfig.ready()`` fails
SILENTLY, because ``lifecycle_name_for`` falls back to the default 4-state
lifecycle with no error anywhere. Every governance gate in the module would
disappear and every test but this one would still pass.
"""
import pytest

from core.lifecycle import get_lifecycle, lifecycle_name_for
from incidents.models import (
    Incident,
    IncidentEvidence,
    IncidentNotification,
    PersonalDataBreach,
    PostIncidentReview,
    SecurityEvent,
)

EXPECTED = [
    (Incident, "incident"),
    (SecurityEvent, "security_event"),
    (IncidentEvidence, "incident_evidence"),
    (IncidentNotification, "incident_notification"),
    (PostIncidentReview, "post_incident_review"),
    (PersonalDataBreach, "personal_data_breach"),
]


@pytest.mark.parametrize("model,name", EXPECTED)
def test_model_resolves_its_own_lifecycle(model, name):
    assert lifecycle_name_for(model) == name


@pytest.mark.parametrize("model,name", EXPECTED)
def test_every_archive_and_restore_edge_is_gated(model, name):
    """The auto-wired bookends carry no permission_action.

    `user_can_perform` allows any transition whose `permission_action` is
    empty, so a generated pair would give anyone reaching the endpoint an
    archive -> restore -> delete path out of the deletable draft step.
    """
    lifecycle = get_lifecycle(name)
    bookends = [
        t for t in lifecycle.transitions
        if t.target == "archived" or (t.source == "archived" and t.target == "draft")
    ]

    assert len(bookends) == 2, f"{name} should declare exactly two bookend edges"
    for transition in bookends:
        assert transition.permission_action, (
            f"{name}: {transition.code} carries no permission_action"
        )


@pytest.mark.parametrize("model,name", EXPECTED)
def test_every_lifecycle_starts_in_draft(model, name):
    assert get_lifecycle(name).initial_step.code == "draft"


@pytest.mark.django_db
@pytest.mark.parametrize("model", [m for m, _ in EXPECTED])
def test_the_table_exists_and_is_queryable(model):
    assert model.objects.count() == 0

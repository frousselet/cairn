# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The full-page fallback of a child form keeps its parent incident crumb."""
import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from incidents.tests.factories import IncidentResponseActionFactory

pytestmark = pytest.mark.django_db


def test_child_edit_page_shows_the_parent_crumb_and_cancels_to_it():
    action = IncidentResponseActionFactory()
    client = Client()
    client.force_login(UserFactory(is_superuser=True))
    html = client.get(reverse("incidents:response-action-update", args=[action.pk])).content.decode()
    detail = reverse("incidents:incident-detail", args=[action.incident.pk])
    assert f'<a href="{detail}" class="page-header__crumb">{action.incident.reference}</a>' in html
    assert f'href="{detail}" class="btn btn-secondary me-auto"' in html
    assert "page-header--accent-incidents" in html

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A drawer delete confirmation renders as a page on a direct visit.

Opening a drawer-only ``/delete/`` URL directly (a bookmark, a shared link)
used to return the bare modal fragment, unstyled and outside the page.
"""
import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from incidents.models import Incident
from incidents.tests.factories import IncidentFactory

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def client():
    c = Client()
    c.force_login(UserFactory(is_superuser=True))
    return c


def test_direct_visit_renders_the_page_shell(client):
    incident = IncidentFactory()
    html = client.get(reverse("incidents:incident-delete", args=[incident.pk])).content.decode()
    assert "<html" in html and 'class="card page-form page-form--danger" hx-boost="false"' in html
    assert "modal-header" not in html.split('class="card page-form', 1)[1].split("</form>", 1)[0]


def test_drawer_request_renders_the_modal(client):
    incident = IncidentFactory()
    html = client.get(reverse("incidents:incident-delete", args=[incident.pk]), **DRAWER).content.decode()
    assert "<html" not in html
    assert 'class="modal-header"' in html and 'hx-post=' in html


def test_page_post_deletes_and_redirects(client):
    incident = IncidentFactory(workflow_state="draft")
    resp = client.post(reverse("incidents:incident-delete", args=[incident.pk]))
    assert resp.status_code == 302
    assert not Incident.objects.filter(pk=incident.pk).exists()

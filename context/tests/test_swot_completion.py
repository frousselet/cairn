# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A SWOT analysis is created on one screen, then worked on its page.

What every entity of the usability standard does is checked for all of them
in ``core/tests/test_usability_standard.py``. This file holds what is
particular to the analysis : it is the work of a team, so nobody answers for
it by creating it, and what it still needs is its four boxes, which are
filled on the page itself.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.forms import SwotAnalysisCreateForm
from context.models import SwotAnalysis
from context.tests.factories import ScopeFactory, SwotAnalysisFactory, SwotItemFactory
from core.completeness import completeness_of

pytestmark = pytest.mark.django_db

DRAWER = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _mcp(user, tool, arguments):
    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    server = McpServer()
    register_all_tools(server)
    answer = server.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }), user)
    return json.loads(answer["result"]["content"][0]["text"])


class TestCreationIsShort:
    def test_it_asks_what_it_looks_at_and_when(self, admin):
        ScopeFactory()
        ScopeFactory()

        form = SwotAnalysisCreateForm(user=admin)

        assert list(form.fields) == ["scopes", "name", "description", "analysis_date"]
        assert form.is_multistep is False

    def test_an_analysis_is_created_and_lands_on_its_page(self, client, admin):
        response = client.post(
            reverse("context:swot-create"),
            {"name": "Security of the customer portal, 2027", "analysis_date": "2027-02-01", "description": ""},
            **DRAWER,
        )

        analysis = SwotAnalysis.objects.get()
        assert response.status_code == 204, response.content.decode()[:400]
        assert response.headers["HX-Redirect"] == analysis.get_absolute_url()


class TestWhatItStillNeeds:
    def test_a_bare_analysis_asks_for_its_four_boxes_and_its_next_time(self, client, admin):
        analysis = SwotAnalysisFactory()
        edit = reverse("context:swot-update", kwargs={"pk": analysis.pk})

        report = completeness_of(analysis)
        html = client.get(analysis.get_absolute_url()).content.decode()

        assert [item.key for item in report.advised_missing] == ["boxes", "review"]
        assert report.blocking_missing == [] and report.can_advance
        # The boxes are filled on the page : the line leads to them.
        assert f'href="{analysis.get_absolute_url()}#swot-items"' in html and 'id="swot-items"' in html
        assert f'href="{edit}?section=identity"' in html

    def test_three_boxes_are_not_four(self):
        analysis = SwotAnalysisFactory()
        for quadrant in ("strength", "weakness", "opportunity"):
            SwotItemFactory(swot_analysis=analysis, quadrant=quadrant)

        assert "boxes" in [item.key for item in completeness_of(analysis).advised_missing]

        SwotItemFactory(swot_analysis=analysis, quadrant="threat")

        assert "boxes" not in [item.key for item in completeness_of(analysis).advised_missing]


class TestThePage:
    def test_the_empty_register_explains_and_offers_the_first_analysis(self, client, admin):
        html = client.get(reverse("context:swot-list")).content.decode()

        assert "No SWOT analysis yet." in html and "a four-box picture of where you stand" in html
        create = reverse("context:swot-create")
        assert f'href="{create}"' in html and f'hx-get="{create}"' in html


class TestTheApiAndTheMcpServer:
    def test_they_report_the_completeness_of_one_analysis(self, admin):
        analysis = SwotAnalysisFactory()
        api = APIClient()
        api.force_authenticate(admin)

        one = api.get(f"/api/v1/context/swot-analyses/{analysis.pk}/").json()
        one = one.get("data", one)
        read = _mcp(admin, "get_swot_analysis", {"id": str(analysis.pk)})

        assert [item["key"] for item in one["completeness"]["missing"]] == ["boxes", "review"]
        assert [item["key"] for item in read["completeness"]["missing"]] == ["boxes", "review"]

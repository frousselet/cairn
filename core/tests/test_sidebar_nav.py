# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Tests for the sidebar navigation fold state.

The menu is one accordion : every group ships folded and the group holding the
current page is opened client-side, so the open group is always derived from the
URL. Nothing is stored per user, and these tests guard the markup that makes
that true - a group shipping with ``show`` puts the whole product tree back on
screen at once.
"""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

# The collapsible groups of the sidebar, one per nested list in the menu. The
# administration groups are left out: they depend on the viewer's permissions.
NAV_GROUPS = [
    "navGouv", "navIndicateurs", "navStrategie",
    "navActifs", "navSuppliers", "navDocuments", "navDeps",
    "navRiskAssess", "navRiskReg", "navRiskCatalogs",
]


def _sidebar_html():
    client = Client()
    client.force_login(UserFactory())
    html = client.get(reverse("home")).content.decode()
    return html.split('<aside class="sidebar"', 1)[1].split("</aside>", 1)[0]


class TestSidebarFolding:
    def test_every_group_ships_folded(self):
        sidebar = _sidebar_html()
        for group in NAV_GROUPS:
            assert f'class="collapse" id="{group}" data-bs-parent=".sidebar-body"' in sidebar
            assert (
                f'data-bs-target="#{group}" aria-controls="{group}" aria-expanded="false"'
                in sidebar
            ), group

    def test_no_group_is_rendered_open(self):
        """A ``collapse show`` in the menu would defeat the whole point."""
        assert 'class="collapse show"' not in _sidebar_html()

    def test_section_headers_stay_plain_labels(self):
        """Section headers organise the menu; they are not fold controls."""
        sidebar = _sidebar_html()
        for label in ("Governance", "Assets", "Risk management", "Compliance", "Incidents"):
            assert f'<div class="sidebar-section">{label}</div>' in sidebar

    def test_flat_entries_stay_visible(self):
        """An entry with no sub-list is never hidden behind a fold."""
        sidebar = _sidebar_html()
        for url_name in ("context:role-list", "assets:site-list", "compliance:framework-list"):
            assert f'href="{reverse(url_name)}" class="sidebar-link"' in sidebar

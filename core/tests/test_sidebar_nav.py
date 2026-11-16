# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Tests for the navigation : the sidebar, its fold state and its breadcrumbs.

The navigation is declared once (``core.navigation.MENU``). The sidebar is
rendered from it, two levels deep : a section folds and unfolds its pages.
Every section ships folded and the one holding the current page is opened
client-side, so the open section is always derived from the URL : nothing is
stored per user, and a section shipping with ``show`` would put the whole
product tree back on screen at once.
"""

import re

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from core.navigation import MENU, NAV_TREE, nav_views, required_permissions, visible_menu

pytestmark = pytest.mark.django_db


def _sidebar_html(user=None):
    client = Client()
    client.force_login(user or UserFactory(is_superuser=True))
    html = client.get(reverse("home")).content.decode()
    return html.split('<aside class="sidebar"', 1)[1].split("</aside>", 1)[0]


def _user_with(*codenames):
    user = UserFactory()
    group = GroupFactory()
    for codename in codenames:
        module, feature, action = codename.split(".")
        group.permissions.add(PermissionFactory(
            codename=codename, module=module, feature=feature, action=action,
        ))
    group.users.add(user)
    return user


class TestSidebarStructure:
    def test_the_menu_has_two_levels_only(self):
        """A section opens on its pages : no group inside a section."""
        sidebar = _sidebar_html()
        sections = re.findall(r'<div class="collapse" id="nav-([a-z]+)" data-bs-parent="\.sidebar-body">(.*?)</div>', sidebar, re.S)
        assert [key for key, _body in sections] == [section.key for section in MENU]
        for _key, body in sections:
            assert "sidebar-collapse-btn" not in body
            assert 'class="sidebar-link sidebar-sub"' in body

    def test_every_section_ships_folded(self):
        sidebar = _sidebar_html()
        for section in MENU:
            assert (
                f'data-bs-target="#nav-{section.key}" aria-controls="nav-{section.key}" aria-expanded="false"'
                in sidebar
            ), section.key
        assert 'class="collapse show"' not in sidebar

    def test_no_section_heading_is_left_above_the_sections(self):
        """The headings were the third level : a section is its own heading now."""
        assert 'class="sidebar-section"' not in _sidebar_html()

    def test_the_everyday_links_stay_outside_the_sections(self):
        sidebar = _sidebar_html()
        for url_name in ("home", "calendar", "kanban"):
            assert f'href="{reverse(url_name)}" class="sidebar-link"' in sidebar

    def test_no_two_entries_share_a_label(self):
        """"Documents" once named both the contracts and the policies. (A
        section may be named after its main register : Incidents > Incidents.)"""
        labels = [item.label for section in MENU for item in section.items if item.in_menu]
        assert len(labels) == len(set(labels)), sorted(label for label in labels if labels.count(label) > 1)
        sections = [section.label for section in MENU]
        assert len(sections) == len(set(sections))

    def test_reference_data_is_kept_out_of_the_working_sections(self):
        reference = {item.label for section in MENU if section.key == "reference" for item in section.items}
        assert {"Supplier types", "Risk criteria", "Threats", "Requirement mappings"} <= reference
        working = {
            item.label
            for section in MENU if section.key not in ("reference", "administration")
            for item in section.items
        }
        assert not working & reference


class TestSidebarEntries:
    def test_an_entry_with_several_views_is_one_line(self):
        sidebar = _sidebar_html()
        organizational = reverse("context:indicator-organizational-list")
        technical = reverse("context:indicator-technical-list")
        assert f'href="{organizational}" class="sidebar-link sidebar-sub" data-nav-paths="{organizational} {technical}"' in sidebar
        assert f'href="{technical}" class="sidebar-link' not in sidebar

    def test_an_entry_is_shown_to_those_the_page_lets_in(self):
        """The permission is read from the view : an entry that would only
        lead to a refusal is not offered."""
        assert required_permissions("risks:risk-list") == ("risks.risk.read",)
        outsider = UserFactory()
        reader = _user_with("risks.risk.read")
        assert reverse("risks:risk-list") not in _sidebar_html(outsider)
        sidebar = _sidebar_html(reader)
        assert reverse("risks:risk-list") in sidebar
        assert reverse("risks:assessment-list") not in sidebar

    def test_a_section_with_nothing_to_show_is_left_out(self):
        sections = {section["key"] for section in visible_menu(_user_with("risks.risk.read"))}
        assert sections == {"risks"}

    def test_administration_needs_a_system_permission(self):
        assert "nav-administration" not in _sidebar_html(_user_with("risks.risk.read"))
        assert "nav-administration" in _sidebar_html(_user_with("system.users.read"))

    def test_every_entry_resolves(self):
        for section in MENU:
            for item in section.items:
                # Aliases are detail pages : they need a record to be reversed.
                for name in [item.url_name, *[view.url_name for view in item.views]]:
                    if name:
                        assert reverse(name)


class TestBreadcrumbs:
    def test_a_page_reads_section_then_entry(self):
        assert NAV_TREE["context:scope-list"] == ("Governance", None, "Scopes")
        assert NAV_TREE["incidents:incident-detail"] == ("Incidents", None, "Incidents")

    def test_a_view_reads_section_entry_view(self):
        assert NAV_TREE["context:indicator-technical-list"] == ("Governance", "Indicators", "Technical")

    def test_an_entry_outside_the_sidebar_still_has_its_breadcrumb(self):
        assert NAV_TREE["documents:acknowledge-list"] == ("Compliance", None, "To acknowledge")
        assert reverse("documents:acknowledge-list") not in "".join(
            item["paths"] for section in visible_menu(UserFactory(is_superuser=True)) for item in section["items"]
        )


class TestViewSwitcher:
    def test_a_list_of_several_views_shows_the_switcher(self):
        client = Client()
        client.force_login(UserFactory(is_superuser=True))
        html = client.get(reverse("context:indicator-technical-list")).content.decode()
        assert 'class="page-switcher"' in html
        technical = reverse("context:indicator-technical-list")
        assert f'href="{technical}" class="page-switcher__link is-current" aria-current="page"' in html
        assert f'href="{reverse("context:indicator-organizational-list")}" class="page-switcher__link"' in html

    def test_a_plain_list_has_no_switcher(self):
        client = Client()
        client.force_login(UserFactory(is_superuser=True))
        assert 'class="page-switcher"' not in client.get(reverse("context:scope-list")).content.decode()

    def test_the_switcher_only_offers_the_views_the_user_may_open(self):
        superuser = UserFactory(is_superuser=True)
        assert len(nav_views("assets:dependency-list", superuser)) == 5
        # One view left is not a choice : no switcher.
        assert nav_views("assets:dependency-list", UserFactory()) == []

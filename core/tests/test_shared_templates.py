# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Presentation of the shared includes rendered on every module's pages."""

from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from compliance.constants import ActionPlanStatus
from compliance.tests.factories import ComplianceActionPlanFactory
from core.kanban import build_kanban_cards, serialize_card


def test_tags_badge_renders_safe_pills():
    tags = [
        SimpleNamespace(name="Critical", color="#dc2626"),
        SimpleNamespace(name="Hostile", color="red;background:url(x)"),
    ]
    html = render_to_string("includes/tags_badge.html", {"tags": tags})
    assert html.count('class="tag-pill"') == 2
    assert "--tag-bg:#dc2626" in html
    # A colour that is not a hex value never reaches the style attribute.
    assert "url(x)" not in html


def test_tags_badge_renders_nothing_without_tags():
    assert render_to_string("includes/tags_badge.html", {"tags": []}).strip() == ""


def test_history_timeline_uses_framework_badges():
    entry = SimpleNamespace(
        kind="create", entity_label="", version=3, history_date=None, user=None,
        snapshot=[], approved=False, is_refusal=False, changes=[],
    )
    html = render_to_string("includes/history_timeline.html", {"history_records": [entry]})
    assert 'class="badge-dot success"' in html
    assert "text-bg-" not in html
    assert "v3" in html


@pytest.mark.django_db
class TestKanbanCardBadge:
    def test_card_badge_is_a_badge_dot_with_framework_variant(self):
        user = UserFactory(is_superuser=True)
        ComplianceActionPlanFactory(name="Board plan", status=ActionPlanStatus.TO_IMPLEMENT)
        client = Client()
        client.force_login(user)
        content = client.get(reverse("kanban")).content.decode()
        assert "Board plan" in content
        # "to_implement" is the Bootstrap "primary" tone, the framework's accent.
        assert '<span class="badge-dot accent">' in content

    def test_primary_tone_maps_to_accent_without_changing_the_api(self):
        user = UserFactory(is_superuser=True)
        ComplianceActionPlanFactory(name="Board plan", status=ActionPlanStatus.TO_IMPLEMENT)
        card = next(c for c in build_kanban_cards(user) if c["title"] == "Board plan")
        assert card["status_tone"] == "primary"
        assert card["badge_variant"] == "accent"
        assert "badge_variant" not in serialize_card(card)


@pytest.mark.django_db
def test_changelog_popup_badges_come_from_the_view(settings):
    settings.APP_VERSION = "0.36.1"
    user = UserFactory(last_seen_version="0.36.0")
    client = Client()
    client.force_login(user)
    response = client.get(reverse("home"))
    entries = response.context["changelog_entries"]
    assert entries, "the 0.36.1 section should be offered"
    sections = entries[0][1]
    assert {s["category"]: s["variant"] for s in sections}.get("Fixed") == "warning"
    content = response.content.decode()
    assert 'id="changelogModal"' in content
    assert '<span class="badge-dot warning mb-1">' in content
    assert "bg-warning" not in content

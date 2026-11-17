# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The help banners rewritten in plain words (migration 0011).

A banner is content an administrator may have rewritten : the migration
replaces a row only while it still holds the text a previous migration
shipped, and its reverse puts that text back under the same condition.
"""

import importlib

import pytest
from django.apps import apps

from helpers.models import HelpContent

pytestmark = pytest.mark.django_db

migration = importlib.import_module("helpers.migrations.0011_plain_words_scope_and_asset_help")


def _ship(key, language):
    title, body, _new_title, _new_body = migration.REWRITES[(key, language)]
    row, _ = HelpContent.objects.update_or_create(
        key=key, language=language, defaults={"title": title, "body": body},
    )
    return row


def test_a_shipped_banner_is_rewritten():
    row = _ship("context.scope_list", "en")

    migration.plain_words(apps, None)

    row.refresh_from_db()
    assert row.body.startswith("A scope says what your security work covers")
    # The rule it used to state was removed with the scope hierarchy.
    assert "Only one scope can be active" not in row.body


def test_a_banner_an_administrator_rewrote_is_left_alone():
    row = _ship("assets.essential_asset_list", "fr")
    row.body = "Notre propre texte."
    row.save()

    migration.plain_words(apps, None)

    row.refresh_from_db()
    assert row.body == "Notre propre texte."


def test_the_reverse_puts_the_shipped_text_back():
    row = _ship("context.scope_detail", "fr")
    shipped = row.body

    migration.plain_words(apps, None)
    migration.previous_words(apps, None)

    row.refresh_from_db()
    assert row.body == shipped


def test_every_rewrite_exists_in_both_languages_and_explains_without_jargon():
    keys = {key for key, _language in migration.REWRITES}

    for key in keys:
        assert (key, "en") in migration.REWRITES and (key, "fr") in migration.REWRITES
    for (_key, _language), (_title, _body, new_title, new_body) in migration.REWRITES.items():
        assert new_title and len(new_body.split()) >= 25
        # No section sign, no acronym thrown at the reader unexplained.
        assert "§" not in new_body
        assert "CIA" not in new_body and "DIC" not in new_body
        assert chr(0x2014) not in new_body  # no em dash, as everywhere

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Every string of the interface has its French, whole and well formed.

``docs/technical/internationalization.md`` calls an untranslated string a
defect. These tests are what makes it one : they read the code the way
``makemessages`` does and compare it with the French catalogue, which is
maintained by hand. They caught, when they were written, ten strings shipped
in English and ten plural sentences whose translation was filed as a singular
one, which gettext never finds : a French reader got the English.
"""

import os
import re

import pytest

from core.tests import po_catalog

_PLACEHOLDER = re.compile(r"%\(\w+\)[sd]|%[sd]|\{\w*\}")


@pytest.fixture(scope="module")
def french():
    return po_catalog.read()


@pytest.fixture(scope="module")
def asked():
    """Every message the code asks a translation for."""
    entries = po_catalog.extract()
    if entries is None:
        # The check cannot be skipped where it matters : CI installs gettext.
        if os.environ.get("CI"):
            pytest.fail("xgettext is not installed : the translation checks cannot run.")
        pytest.skip("xgettext (gettext tools) is not installed")
    return entries


def _placeholders(text):
    return sorted(_PLACEHOLDER.findall(text))


class TestTheCatalogueIsComplete:
    def test_the_extraction_reads_the_code(self, asked):
        """A guard against a silent extraction that would make the next tests pass on nothing."""
        keys = {entry.key for entry in asked}

        assert len(asked) > 4000
        assert ("", "Save") in keys
        # A template string, a lazy alias, a context and a plural are all read.
        assert ("", "Help on this page") in keys
        assert ("", "IP address") in keys
        assert ("incident", "Incident response team (CSIRT)") in keys
        assert any(entry.plural for entry in asked)

    def test_every_string_has_its_french(self, asked, french):
        have = {entry.key for entry in french}

        missing = sorted(
            (f"[{entry.context}] " if entry.context else "") + entry.msgid
            for entry in asked if entry.key not in have
        )

        assert not missing, (
            f"{len(missing)} string(s) have no French in locale/fr/LC_MESSAGES/django.po :\n  "
            + "\n  ".join(missing[:40])
        )

    def test_every_label_of_the_menu_has_its_french(self, french):
        """The menu is declared as plain strings, translated when shown : the extraction cannot see them."""
        from core.navigation import MENU

        have = {entry.key for entry in french}
        labels = set()
        for section in MENU:
            labels.add(section.label)
            for item in section.items:
                labels.add(item.label)
                labels.update(view.label for view in item.views)

        assert not sorted(label for label in labels if ("", label) not in have)

    def test_every_column_heading_has_its_french(self, french):
        """``{% sortable_th "field" "Label" %}`` translates its label when shown, like the menu."""
        have = {entry.key for entry in french}
        heading = re.compile(r"""{%\s*sortable_th\s+["'][^"']*["']\s+["']([^"']+)["']""")
        labels = set()
        for path in po_catalog.source_files():
            if path.suffix == ".html":
                labels.update(heading.findall(path.read_text(encoding="utf-8")))

        assert len(labels) > 50
        assert not sorted(label for label in labels if ("", label) not in have)

    def test_a_plural_sentence_is_filed_as_a_plural(self, asked, french):
        """A plural looked up in a singular entry is never found : the English is shown."""
        have = {entry.key: entry for entry in french}

        wrong = sorted(
            entry.msgid for entry in asked
            if entry.plural and entry.key in have and have[entry.key].plural != entry.plural
        )

        assert not wrong, (
            "These sentences are used with a count, their French entry needs "
            "msgid_plural and msgstr[0] / msgstr[1] :\n  " + "\n  ".join(wrong)
        )

    def test_a_singular_sentence_is_not_filed_as_a_plural(self, asked, french):
        have = {entry.key: entry for entry in french}

        wrong = sorted(
            entry.msgid for entry in asked
            if not entry.plural and entry.key in have and have[entry.key].plural
        )

        assert not wrong, "Filed as plurals, used without a count :\n  " + "\n  ".join(wrong)


class TestTheCatalogueIsWellFormed:
    def test_no_translation_is_left_empty(self, french):
        empty = [entry.msgid for entry in french if not entry.texts or not all(entry.texts)]

        assert not empty, "Empty translations :\n  " + "\n  ".join(empty[:40])

    def test_no_entry_is_filed_twice(self, french):
        seen, twice = set(), []
        for entry in french:
            if entry.key in seen:
                twice.append(entry.msgid)
            seen.add(entry.key)

        assert not twice, "Filed twice (compilemessages refuses them) :\n  " + "\n  ".join(twice)

    def test_a_translation_carries_the_variables_of_its_sentence(self, french):
        """A variable the sentence does not provide raises when the page renders."""
        wrong = []
        for entry in french:
            offered = set(_placeholders(entry.msgid)) | set(_placeholders(entry.plural or ""))
            for form, text in entry.translations.items():
                unknown = set(_placeholders(text)) - offered
                # The singular form may leave the count out ("tous les mois").
                source = entry.msgid if form in ("msgstr", "msgstr[0]") else (entry.plural or entry.msgid)
                dropped = set() if form == "msgstr[0]" else set(_placeholders(source)) - set(_placeholders(text))
                if unknown or dropped:
                    wrong.append(f"{entry.msgid[:70]!r} {form} : unknown {sorted(unknown)}, dropped {sorted(dropped)}")

        assert not wrong, "\n  ".join(wrong)

    def test_no_em_dash(self, french):
        dash = chr(0x2014)

        assert not [entry.msgid for entry in french if dash in entry.msgid or any(dash in text for text in entry.texts)]

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The help of a page : plain words, and never lost (rule W4 of the usability standard).

A help is titled with the name of the page (*Essential assets*, the word of
the menu). Its text says what the thing is in one sentence, gives an example,
and says what to do first or what to watch. It is shown open until the reader
hides it, and a hidden help leaves a button that brings it back.

The texts are shipped by ``helpers/migrations/0013_help_titles_name_the_thing.py``
(written in plain words by ``0012_plain_words_everywhere.py``, whose titles were
sentences). Each rewrites a row only while it still holds the text the
previous migration shipped : a help an administrator rewrote is theirs. The
helps of the EBIOS RM workshop pages, which had none, come with
``0014_ebios_workshop_helps.py``.
"""

import importlib
import json
import re
from pathlib import Path

import pytest
from django.apps import apps
from django.template import Context, Template
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import translation

from accounts.tests.factories import UserFactory
from core import glossary, usability
from helpers.models import HelpContent
from helpers.templatetags.help_tags import help_for

pytestmark = pytest.mark.django_db

REPO = Path(__file__).resolve().parents[2]
migration = importlib.import_module("helpers.migrations.0013_help_titles_name_the_thing")
#: The migration that wrote the texts in plain words, and removed the helps no page shows.
plain_words = importlib.import_module("helpers.migrations.0012_plain_words_everywhere")
#: The migration that gave the EBIOS RM workshop pages their help.
workshops = importlib.import_module("helpers.migrations.0014_ebios_workshop_helps")
#: The migration that gave the page of a document version its help.
versions = importlib.import_module("helpers.migrations.0015_document_version_help")
#: Every help shipped : key -> ((English title, English text), (French title, French text)).
HELP = {**migration.HELP, **workshops.HELP, **versions.HELP}

_TAG = re.compile(r"""\{%\s*help_modal\s+["']([a-z_.0-9]+)["']\s*%\}""")


@pytest.fixture(autouse=True)
def _in_english():
    """Whatever language an earlier test left active, these read English."""
    with translation.override("en"):
        yield

# French spellings the glossary retires, that a help must not bring back. The
# actors of the EBIOS RM ecosystem keep *partie prenante*, the word of that
# method (docs/brand/glossary.md).
_RETIRED_IN_FRENCH = re.compile(
    r"parties? prenantes?(?! de l'écosystème)|\bworkflows?\b|\bCIA\b|\bprestataires?\b|\btags?\b|dépositaires?"
    r"|éléments? de preuve|(analyses?|évaluations?) (de|des) risques|Open ?GRC"
    r"|\bactifs? (supports?|essentiels?|primordia)|d'actifs|\bvos actifs\b|\bles actifs\b",
    re.I,
)


def _keys_used_by_the_pages():
    used = set()
    for path in REPO.rglob("*.html"):
        if ".venv" in path.parts or "node_modules" in path.parts:
            continue
        used |= set(_TAG.findall(path.read_text(encoding="utf-8")))
    used.discard("key")  # the example of the component's own comment
    return used


def _texts():
    """(key, language, title, body) for every help shipped."""
    for key, texts in HELP.items():
        for language, (title, body) in zip(("en", "fr"), texts):
            yield key, language, title, body


# ── The texts ───────────────────────────────────────────────────────────────


class TestEveryPageHasItsHelp:
    def test_every_help_a_page_asks_for_is_written(self):
        assert _keys_used_by_the_pages() - set(HELP) == set()

    def test_no_help_is_written_for_a_page_that_does_not_exist(self):
        assert set(HELP) - _keys_used_by_the_pages() == set()

    def test_the_main_registers_carry_one(self):
        """The registers a newcomer opens first, and those that had none."""
        for key in (
            "context.scope_list", "assets.essential_asset_list", "assets.support_asset_list",
            "assets.supplier_list", "compliance.framework_list", "risks.assessment_list", "risks.risk_list",
            "controls.control_list", "documents.policy_list", "incidents.incident_list",
            "incidents.event_list", "compliance.finding_list", "assets.contract_list",
            "assets.certificate_list", "reports.management_review_list", "reports.report_list",
        ):
            assert key in HELP, key


class TestAHelpIsWrittenForANewcomer:
    def test_both_languages_and_not_the_same_text(self):
        for key, (english, french) in HELP.items():
            assert english[0] and english[1] and french[0] and french[1], key
            assert english != french, key

    def test_the_title_names_the_page(self):
        """Asked by the maintainer : *Essential assets*, the word of the menu,
        where a sentence stood ("An essential asset is what the business cannot
        do without")."""
        for key, language, title, _body in _texts():
            where = f"{key} ({language}) : {title}"
            # Words, not marks : the dash of "Workshop 1 - Security baseline" is none.
            assert 1 <= len(re.findall(r"[\w'’]+", title)) <= 5, where
            assert title[-1] not in ".?!:", where
            assert not re.search(r"(?i)\b(is|are|says|est|sont|dit)\b", title), where
            if language == "en":
                assert not usability.describes_instead_of_naming(title), where

    def test_a_register_and_its_record_are_named_alike(self):
        """*Risks* over the register, *Risk* over one of them."""
        for key, (english, _french) in HELP.items():
            if not key.endswith("_detail"):
                continue
            register = HELP.get(key.removesuffix("_detail") + "_list")
            if register is not None:
                assert english[0].split()[-1][:4].lower() == register[0][0].split()[-1][:4].lower(), key

    def test_the_text_opens_on_what_the_thing_is_and_stays_short(self):
        for key, language, _title, body in _texts():
            where = f"{key} ({language})"
            assert 20 <= len(body.split()) <= 80, f"{where} : {len(body.split())} words"
            assert body.rstrip()[-1] in ".?", where
            # The sentence that was the title, then the rest.
            assert 3 <= len(re.split(r"(?<=[.?!])\s", body)[0].split()) <= 18, where
            assert not re.search(r"(?i)\bthis page presents\b|\bcette page présente\b", body), where

    def test_no_jargon_mark(self):
        dash = chr(0x2014)
        for key, language, title, body in _texts():
            text = f"{title} {body}"
            assert "§" not in text, f"{key} ({language})"
            assert dash not in text, f"{key} ({language})"

    def test_an_acronym_comes_with_its_words(self):
        """ISMS, SPOF, RTO : spelled out in the very text, or not used. A proper
        name (ISO 27001, NIS2) and an everyday word (PDF) stand as they are."""
        wrong = []
        for key, language, title, body in _texts():
            with translation.override(language):
                missing = glossary.unexplained_acronyms(f"{title}. {body}")
            if missing:
                wrong.append(f"{key} ({language}) : {missing}")

        assert not wrong, "\n".join(wrong)

    def test_the_french_uses_the_words_of_the_glossary(self):
        wrong = [
            f"{key} : {match.group(0)}"
            for key, language, title, body in _texts() if language == "fr"
            for match in [_RETIRED_IN_FRENCH.search(f"{title} {body}")] if match
        ]

        assert not wrong, "\n".join(wrong)

    def test_french_punctuation_is_spaced(self):
        for key, language, title, body in _texts():
            if language != "fr":
                continue
            text = f"{title} {body}"
            assert not re.search(r"\S[;:?!]", re.sub(r"\d:\d", "", text)), f"{key} : a space goes before ; : ? !"

    def test_a_list_help_gives_an_example(self):
        """After saying what the thing is, the help of a register starts from
        something a newcomer can picture."""
        for key, (english, _french) in HELP.items():
            if not key.endswith("_list") or key.startswith("accounts."):
                continue
            example = re.split(r"(?<=[.?!])\s", english[1])[1]
            assert re.search(r"[,;:]", example) or " or " in example, (
                f"{key} : the sentence after the first is an example (a list of things)"
            )


# ── The migration ───────────────────────────────────────────────────────────


def _ship(key, language, title="Old title", body="Old body."):
    """A row as a previous migration left it."""
    row, _ = HelpContent.objects.update_or_create(key=key, language=language, defaults={"title": title, "body": body})
    return row


class TestTheMigration:
    @pytest.fixture
    def shipped(self, monkeypatch):
        """Make ``Old title / Old body.`` the text the previous migrations shipped."""
        marks = dict(migration.SHIPPED)
        fingerprint = migration.fingerprint("Old title", "Old body.")
        for key in ("risks.risk_list", "assets.dashboard", "context.scope_list"):
            for language in ("en", "fr"):
                marks[(key, language)] = fingerprint
        monkeypatch.setattr(migration, "SHIPPED", marks)

    def test_a_shipped_help_is_rewritten(self, shipped):
        row = _ship("risks.risk_list", "fr")

        migration.name_the_thing(apps, None)

        row.refresh_from_db()
        assert row.title == "Risques"
        assert row.body.startswith("Un risque est ce qui pourrait mal tourner, et ce que cela vous coûterait.")
        assert "rançongiciel" in row.body

    def test_a_help_an_administrator_rewrote_is_left_alone(self, shipped):
        row = _ship("risks.risk_list", "en", body="Our own words.")

        migration.name_the_thing(apps, None)

        row.refresh_from_db()
        assert (row.title, row.body) == ("Old title", "Our own words.")

    def test_a_missing_help_is_created_in_both_languages(self):
        HelpContent.objects.filter(key="incidents.incident_list").delete()

        migration.name_the_thing(apps, None)

        rows = {row.language: row for row in HelpContent.objects.filter(key="incidents.incident_list")}
        assert set(rows) == {"en", "fr"}
        assert rows["en"].title == "Incidents"
        assert rows["en"].body.startswith("A security incident is")

    def test_it_can_run_twice(self, shipped):
        _ship("context.scope_list", "en")

        migration.name_the_thing(apps, None)
        first = {(row.key, row.language): (row.title, row.body) for row in HelpContent.objects.all()}
        migration.name_the_thing(apps, None)

        assert {(row.key, row.language): (row.title, row.body) for row in HelpContent.objects.all()} == first

    def test_it_recognises_the_text_the_previous_migration_shipped(self):
        """The chain holds : what 0012 wrote is what 0013 replaces, key by key."""
        assert set(migration.HELP) == set(plain_words.HELP)
        for key, texts in plain_words.HELP.items():
            for language, (title, body) in zip(("en", "fr"), texts):
                assert migration.SHIPPED[(key, language)] == migration.fingerprint(title, body), (key, language)

    def test_the_sentence_that_was_the_title_opens_the_text(self):
        for key, texts in plain_words.HELP.items():
            for (old_title, old_body), (_title, body) in zip(texts, migration.HELP[key]):
                assert body.startswith(old_title) and body.endswith(old_body), key


class TestTheHelpsNoPageShows:
    """Removed by the migration that wrote the texts in plain words (0012)."""

    def test_a_help_no_page_shows_is_removed_unless_it_was_rewritten(self, monkeypatch):
        marks = dict(plain_words.SHIPPED)
        for language in ("en", "fr"):
            marks[("assets.dashboard", language)] = plain_words.fingerprint("Old title", "Old body.")
        monkeypatch.setattr(plain_words, "SHIPPED", marks)
        _ship("assets.dashboard", "en")
        kept = _ship("assets.dashboard", "fr", body="Notre texte.")

        plain_words.plain_words(apps, None)

        assert not HelpContent.objects.filter(key="assets.dashboard", language="en").exists()
        assert HelpContent.objects.filter(pk=kept.pk).exists()

    def test_they_are_not_shown_by_any_page(self):
        assert set(plain_words.ORPHANS).isdisjoint(_keys_used_by_the_pages())


# ── The component ───────────────────────────────────────────────────────────


def _render(user, key="context.scope_list"):
    request = RequestFactory().get("/")
    request.user = user
    return Template('{% load help_tags %}{% help_modal "' + key + '" %}').render(Context({"request": request}))


class TestTheHelpOfAPage:
    @pytest.fixture(autouse=True)
    def _a_help(self):
        HelpContent.objects.update_or_create(
            key="context.scope_list", language="en",
            defaults={"title": "A scope says what your security work covers", "body": "First paragraph.\n\nSecond <b>one</b>."},
        )

    def test_it_is_open_until_hidden(self):
        html = _render(UserFactory())

        assert 'class="help-banner" id="help-context-scope_list" role="note"' in html
        assert "A scope says what your security work covers" in html
        # The banner is shown, the button that brings it back is not.
        assert re.search(r'<div class="help-banner"[^>]*(?<!hidden)>', html)
        assert re.search(r'<button type="button" class="page-help__open"[^>]* hidden>', html)

    def test_a_hidden_help_leaves_a_button_that_brings_it_back(self):
        user = UserFactory()
        user.dismissed_helpers = ["context.scope_list"]
        user.save(update_fields=["dismissed_helpers"])

        html = _render(user)

        assert re.search(r'<div class="help-banner"[^>]* hidden>', html)
        opener = re.search(r'<button type="button" class="page-help__open"([^>]*)>', html).group(1)
        assert "hidden" not in opener
        assert 'data-on-click="showPageHelp"' in opener
        assert "Help on this page" in html

    def test_it_is_a_note_with_a_name_not_an_alert(self):
        html = _render(UserFactory())

        assert 'role="alert"' not in html
        assert 'aria-labelledby="help-context-scope_list-title"' in html
        assert 'id="help-context-scope_list-title"' in html
        assert 'aria-label="Hide this help"' in html

    def test_it_carries_no_inline_style_nor_script(self):
        """The policy refuses an inline handler, and a fixed visual choice is a class."""
        html = _render(UserFactory())

        assert "style=" not in html
        assert "<script" not in html
        assert "onclick" not in html

    def test_the_body_keeps_its_paragraphs_and_is_shown_as_text(self):
        html = _render(UserFactory())

        assert "<p>First paragraph.</p>" in html
        assert "&lt;b&gt;one&lt;/b&gt;" in html and "<b>one</b>" not in html

    def test_it_links_to_the_glossary(self):
        assert f'href="{reverse("glossary")}"' in _render(UserFactory())

    def test_nothing_is_rendered_for_a_page_without_a_text(self):
        assert _render(UserFactory(), key="no.such_page").strip() == ""

    def test_the_text_follows_the_language_then_falls_back_to_english(self):
        HelpContent.objects.update_or_create(
            key="context.scope_list", language="fr", defaults={"title": "Un périmètre", "body": "Texte."},
        )

        assert help_for("context.scope_list", "fr").title == "Un périmètre"
        assert help_for("context.scope_list", "fr-ca").title == "Un périmètre"
        assert help_for("context.scope_list", "de").language == "en"
        assert help_for("no.such_page", "fr") is None

    def test_it_is_read_in_one_query(self, django_assert_num_queries):
        with django_assert_num_queries(1):
            help_for("context.scope_list", "fr")

    def test_the_two_actions_are_registered(self):
        script = (REPO / "static" / "js" / "cairn" / "actions.js").read_text(encoding="utf-8")

        assert "actions.hidePageHelp" in script and "actions.showPageHelp" in script


# ── Hiding, and bringing back ───────────────────────────────────────────────


def _post(client, payload):
    return client.post(reverse("helpers:dismiss"), data=json.dumps(payload), content_type="application/json")


class TestHidingAndBringingBack:
    @pytest.fixture
    def reader(self):
        user = UserFactory()
        client = Client()
        client.force_login(user)
        return client, user

    def test_a_help_is_hidden_then_brought_back(self, reader):
        client, user = reader

        assert _post(client, {"key": "risks.risk_list"}).json() == {"status": "ok", "dismissed": True}
        user.refresh_from_db()
        assert user.dismissed_helpers == ["risks.risk_list"]

        assert _post(client, {"key": "risks.risk_list", "dismissed": False}).json() == {"status": "ok", "dismissed": False}
        user.refresh_from_db()
        assert user.dismissed_helpers == []

    def test_the_other_choices_are_kept(self, reader):
        client, user = reader
        user.dismissed_helpers = ["getting_started", "context.scope_list"]
        user.save(update_fields=["dismissed_helpers"])

        _post(client, {"key": "context.scope_list", "dismissed": False})

        user.refresh_from_db()
        assert user.dismissed_helpers == ["getting_started"]

    def test_bringing_back_what_is_shown_changes_nothing(self, reader):
        client, user = reader

        assert _post(client, {"key": "risks.risk_list", "dismissed": False}).status_code == 200
        user.refresh_from_db()
        assert user.dismissed_helpers in ([], None)

    @pytest.mark.parametrize("payload", [
        ["risks.risk_list"],
        "risks.risk_list",
        {"key": 12},
        {"key": ""},
        {"key": "x" * 101},
        {"key": "risks.risk_list", "dismissed": "no"},
        {"key": {"nested": True}},
    ])
    def test_a_malformed_request_is_refused_not_stored(self, reader, payload):
        client, user = reader

        assert _post(client, payload).status_code == 400
        user.refresh_from_db()
        assert not user.dismissed_helpers

    def test_the_list_cannot_be_grown_without_end(self, reader):
        from helpers.views import MAX_DISMISSED_HELPERS

        client, user = reader
        user.dismissed_helpers = [f"made.up_{index}" for index in range(MAX_DISMISSED_HELPERS)]
        user.save(update_fields=["dismissed_helpers"])

        assert _post(client, {"key": "one.more"}).status_code == 400
        # What is already hidden can still be brought back.
        assert _post(client, {"key": "made.up_0", "dismissed": False}).status_code == 200
        user.refresh_from_db()
        assert len(user.dismissed_helpers) == MAX_DISMISSED_HELPERS - 1

    def test_one_reader_does_not_change_the_help_of_another(self, reader):
        client, _user = reader
        other = UserFactory()

        _post(client, {"key": "risks.risk_list"})

        other.refresh_from_db()
        assert not other.dismissed_helpers


class TestTheWorkshopHelps:
    """The six EBIOS RM workshop pages had no help (``0014_ebios_workshop_helps``)."""

    def test_each_workshop_page_has_one_titled_with_the_name_of_the_page(self):
        from risks.constants import EbiosWorkshopNumber

        for number in EbiosWorkshopNumber:
            (title, _text), (french_title, _french) = workshops.HELP[f"risks.ebios_workshop_{number.value}"]
            assert title == str(number.label)
            with translation.override("fr"):
                assert french_title == str(number.label)

    def test_the_migration_creates_the_missing_rows_and_leaves_the_others(self):
        HelpContent.objects.filter(key__startswith="risks.ebios_workshop_").delete()
        ours = _ship("risks.ebios_workshop_1", "fr", title="Notre atelier", body="Nos mots.")

        workshops.write_the_helps(apps, None)
        workshops.write_the_helps(apps, None)

        assert HelpContent.objects.filter(key__startswith="risks.ebios_workshop_").count() == 12
        ours.refresh_from_db()
        assert (ours.title, ours.body) == ("Notre atelier", "Nos mots.")
        assert HelpContent.objects.get(key="risks.ebios_workshop_1", language="en").title == "Workshop 1 - Security baseline"

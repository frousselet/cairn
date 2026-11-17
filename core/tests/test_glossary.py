# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""One thing, one name, everywhere (rules W1 and W2 of the usability standard).

``docs/brand/glossary.md`` says which word the product uses for each notion,
``core/glossary.py`` is that vocabulary as the application shows it, and
these tests are what keeps the two true :

- the French catalogue does not use a spelling the glossary retires
  (*actif* for an asset, *partie prenante* for a stakeholder of the context,
  *workflow*, *CIA*...);
- an acronym is never a label on its own, and an acronym that spreads through
  the interface is explained in the glossary;
- the glossary names each thing with the very word the screens use, and
  answers the other names people know it by, on the page, in the search
  palette, over REST and over MCP.
"""

import json
import re
from collections import Counter

import pytest
from django.apps import apps
from django.test import Client
from django.urls import NoReverseMatch, reverse
from django.utils import translation

from accounts.tests.factories import UserFactory
from core import glossary
from core.tests import po_catalog
from core.usability import EVERYDAY_ACRONYMS, is_bare_acronym, is_unexplained_acronym

pytestmark = pytest.mark.django_db


# ── W1 : the spellings the glossary retires ────────────────────────────────
#
# (what the English says, the French it must not be given, the word to use,
#  an English pattern that makes the rule not apply, messages left alone)

_EBIOS_STAKEHOLDERS = frozenset({
    # "Partie prenante" is the word of the EBIOS RM method for the actors of
    # the ecosystem (workshop 3) : a different thing from the interested
    # parties of ISO 27001 clause 4.2, which the context module holds.
    "EBIOS RM ecosystem stakeholders (workshop 3)",
    "Involved stakeholder",
    "Organisation dependency on the stakeholder (1..4).",
    "Stakeholder penetration into the ecosystem (1..4).",
    "Stakeholder cyber maturity (1..4).",
    "Trust placed in the stakeholder (1..4).",
    "Frozen copy of the ecosystem thresholds used at first scoring so later edits to the criteria do not silently move stakeholders between zones.",
    "EBIOS RM ecosystem stakeholder",
    "EBIOS RM ecosystem stakeholders",
    "Edit ecosystem stakeholder",
    "Add ecosystem stakeholder",
    "Ecosystem stakeholder",
    "Ecosystem stakeholders",
    "No ecosystem stakeholder yet. Map the suppliers, partners and other actors involved in your digital ecosystem.",
})

_OTHER_CONTROLS = frozenset({
    # "Contrôle" in its other meanings : a zone of the ANSSI map, an attack
    # tactic, the buttons of a zoom, access control.
    "Control zone",
    "Command and control",
    "ANSSI zone derived from threat_level: control, monitoring or danger.",
    "Zoom controls",
    "Permissions are the building blocks of access control. They are seeded automatically from the application's feature registry.",
    "The document title, e.g. Access control policy.",
})

RETIRED = [
    (r"\bassets?\b", r"\bactifs?\b", "bien", None, frozenset()),
    (r"\b(suppliers?|vendors?)\b", r"\bprestataires?\b|\btiers\b", "fournisseur", None, frozenset()),
    (r".", r"\bCIA\b", "DIC, or « besoins de sécurité »", None, frozenset()),
    (r"\bassessments?\b", r"\baudits?\b", "évaluation", r"\baudit", frozenset()),
    (r"\brisk assessments?\b", r"(évaluations?|analyses?) (des?|du|de) risques?", "appréciation des risques", None, frozenset()),
    (r"\bfindings?\b", r"\bécarts?\b|non-conformités? relevées?", "constat", r"\bgap\b|nonconformit", frozenset()),
    (r"\bstakeholders?\b", r"parties? prenantes?", "partie intéressée", None, _EBIOS_STAKEHOLDERS),
    (r"\bcustodians?\b", r"\bdépositaires?\b", "gestionnaire", None, frozenset()),
    (r"\btags?\b", r"\btags?\b", "étiquette", None, frozenset()),
    (r"\bevidence\b", r"éléments? de preuve|pièces? (probantes?|présentées?)", "preuve", None, frozenset()),
    (r".", r"\bworkflows?\b", "cycle de vie", None, frozenset()),
    (r"\blifecycle (state|stage|step)|\b(current|target) state\b", r"\bétats?\b", "étape", None, frozenset()),
    (r"\blikelihood\b", r"probabilit", "vraisemblance", None, frozenset()),
    (r"\bcontrols?\b", r"\bcontrôles?\b", "mesure", None, _OTHER_CONTROLS),
    (r"\bowners?\b", r"\bresponsables?\b", "propriétaire", None, frozenset()),
    (r"\bISMS changes?\b|\bchanges? to the ISMS\b", r"modifications? du SMSI|changements? SMSI", "changement du SMSI", None, frozenset()),
    (r".", r"\bOpen\s?GRC\b", "Cairn", None, frozenset()),
    # A part of a standard is a "chapitre"; "article" is kept for a law (GDPR, art. 33).
    (r"\bclause \d|§\s?\d", r"\bclause \d|§\s?\d", "chapitre", None, frozenset()),
]


@pytest.fixture(scope="module")
def french():
    return po_catalog.read()


@pytest.fixture(autouse=True)
def _in_english():
    """A request made as a French reader leaves French active : each test starts in English."""
    with translation.override("en"):
        yield


class TestOneThingOneName:
    def test_the_french_catalogue_uses_the_words_of_the_glossary(self, french):
        wrong = []
        for source, retired, use, unless, left_alone in RETIRED:
            for entry in french:
                # The glossary lists the names it does not use, so people find them.
                if entry.context == "glossary : other names":
                    continue
                if entry.msgid in left_alone or not re.search(source, entry.msgid, re.I):
                    continue
                if unless and re.search(unless, entry.msgid, re.I):
                    continue
                if any(re.search(retired, text, re.I) for text in entry.texts):
                    wrong.append(f"{entry.msgid[:80]!r} -> {entry.text[:80]!r} : say « {use} »")

        assert not wrong, (
            "These translations use a spelling docs/brand/glossary.md retires :\n  " + "\n  ".join(wrong)
        )

    def test_the_risk_module_speaks_of_appreciation(self, french):
        """One English word, two French ones : the *assessment* of the risk module is
        an *appréciation des risques*, the one of the compliance module an
        *évaluation*. A message the risk screens show must not borrow the other."""
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in po_catalog.source_files()
            if path.relative_to(po_catalog.REPO).parts[0] == "risks"
        )
        # A message given its own context is its own message : leave those out.
        sources = re.sub(r"pgettext(?:_lazy)?\(\s*[\"'][^\"']+[\"'],\s*[\"'][^\"']*[\"']\s*\)", "", sources)
        sources = re.sub(r"{%\s*trans\s+[\"'][^\"']*[\"']\s+context\s+[^%]*%}", "", sources)

        wrong = sorted(
            f"{entry.msgid[:70]!r} -> {entry.text[:70]!r}"
            for entry in french
            if re.search(r"\bassessments?\b", entry.msgid, re.I)
            and any(re.search(r"\bévaluations?\b", text, re.I) for text in entry.texts)
            and (f'"{entry.msgid}"' in sources or f"'{entry.msgid}'" in sources)
        )

        assert not wrong, (
            "Shown by the risk module with the word of the compliance one. Give the risk module "
            "its own message (« Risk assessment », or a context) :\n  " + "\n  ".join(wrong)
        )

    def test_every_exception_still_exists(self, french):
        """An exception that names no message any more is removed, not kept."""
        known = {entry.msgid for entry in french}

        for _source, _retired, _use, _unless, left_alone in RETIRED:
            assert left_alone <= known, sorted(left_alone - known)

    def test_the_menu_names_things_as_their_records_do(self):
        from core.navigation import MENU

        with translation.override("fr"):
            labels = {translation.gettext(section.label) for section in MENU}
            labels |= {translation.gettext(item.label) for section in MENU for item in section.items}

        assert "Biens et fournisseurs" in labels
        assert "Parties intéressées" in labels
        assert "Étiquettes" in labels
        # The register of the documents module is named after its records.
        assert "Documents" in labels and "Politiques" not in labels

    def test_the_glossary_names_things_as_the_screens_do(self):
        """A term takes the message the interface uses, so it cannot drift from it."""
        with translation.override("fr"):
            names = {row["key"]: row["name"] for row in glossary.terms()}

        assert names["essential_asset"] == "Bien essentiel"
        assert names["support_asset"] == "Bien support"
        assert names["stakeholder"] == "Partie intéressée"
        assert names["risk_assessment"] == "Appréciation des risques"
        assert names["compliance_assessment"] == "Évaluation de conformité"
        assert names["control"] == "Mesure"
        assert names["finding"] == "Constat"
        assert names["custodian"] == "Gestionnaire"
        assert names["likelihood"] == "Vraisemblance"
        assert names["lifecycle_step"] == "Étape"
        assert names["evidence"] == "Preuve"
        assert names["tag"] == "Étiquette"


# ── W2 : an acronym is not a label ──────────────────────────────────────────


class TestAnAcronymIsNotALabel:
    def test_the_rule(self):
        assert is_unexplained_acronym("RTO")
        assert is_unexplained_acronym("SPOF")
        assert is_unexplained_acronym("TLP")
        assert not is_unexplained_acronym("Recovery time objective (RTO)")
        # Everyday words, and the mark a protocol prescribes.
        assert not is_unexplained_acronym("PDF")
        assert not is_unexplained_acronym("SHA-256")
        assert not is_unexplained_acronym("TLP:AMBER+STRICT")
        assert is_bare_acronym("PDF")

    def test_no_message_is_an_acronym_alone(self, french):
        alone = sorted(
            entry.msgid for entry in french
            if entry.context != "glossary : acronym"
            and (is_unexplained_acronym(entry.msgid) or any(is_unexplained_acronym(text) for text in entry.texts))
        )

        assert not alone, f"Labels made of an acronym alone, spell them out first : {alone}"

    def test_no_field_and_no_choice_is_labelled_with_an_acronym_alone(self):
        alone = []
        for model in apps.get_models():
            for field in model._meta.get_fields():
                label = getattr(field, "verbose_name", None)
                if label and is_unexplained_acronym(label):
                    alone.append(f"{model._meta.label}.{field.name} : {label}")
                for _value, text in getattr(field, "flatchoices", None) or ():
                    if is_unexplained_acronym(text):
                        alone.append(f"{model._meta.label}.{field.name} choice : {text}")

        assert not alone, "Spell these out first :\n  " + "\n  ".join(sorted(set(alone)))

    @pytest.mark.parametrize("language", ["en", "fr"])
    def test_an_acronym_that_spreads_is_explained(self, french, language):
        """Met in three strings or more, an acronym is in the glossary, or is an everyday word."""
        token = re.compile(r"\b[A-Z][A-Z0-9]{1,7}\b")
        seen = Counter()
        for entry in french:
            texts = entry.texts if language == "fr" else [entry.msgid, entry.plural or ""]
            found = set()
            for text in texts:
                found |= set(token.findall(re.sub(r"%\(\w+\)[sd]", " ", text)))
            seen.update(found)
        with translation.override(language):
            known = glossary.known_acronyms()
        # Not acronyms : the letters of a date format, the levels of a
        # maturity scale, a unit of size.
        not_acronyms = {"MM", "AAAA", "JJ", "YYYY", "DD", "HH", "V1", "V2", "V3", "V4", "KB", "MB", "GB"}

        unexplained = sorted(
            f"{word} ({count})" for word, count in seen.items()
            if count >= 3 and word not in known and word not in EVERYDAY_ACRONYMS and word not in not_acronyms
        )

        assert not unexplained, (
            f"Used in three strings or more ({language}) and explained nowhere : {unexplained}. "
            "Add them to core/glossary.py, or to core.usability.EVERYDAY_ACRONYMS."
        )


# ── The registry ────────────────────────────────────────────────────────────


class TestTheRegistry:
    def test_keys_are_unique(self):
        keys = [term.key for term in glossary.TERMS]
        letters = [acronym.key for acronym in glossary.ACRONYMS]

        assert len(keys) == len(set(keys))
        assert len(letters) == len(set(letters))

    def test_every_register_named_exists(self):
        for term in glossary.TERMS:
            if term.url_name:
                try:
                    reverse(term.url_name)
                except NoReverseMatch:
                    pytest.fail(f"{term.key} : '{term.url_name}' is not a page")

    @pytest.mark.parametrize("language", ["en", "fr"])
    def test_a_definition_is_a_sentence_a_newcomer_can_read(self, language):
        with translation.override(language):
            rows = glossary.terms() + glossary.acronyms()
            known = glossary.known_acronyms()

        for row in rows:
            definition = row["definition"]
            name = row.get("name") or row["letters"]
            assert definition.endswith("."), f"{name} : {definition!r}"
            assert len(definition.split()) <= 40, f"{name} : a definition is short"
            assert chr(0x2014) not in definition
            # A definition does not lean on an acronym the glossary does not explain.
            for word in re.findall(r"\b[A-Z][A-Z0-9]{2,7}\b", definition):
                assert word in known or word in EVERYDAY_ACRONYMS or word in {"RED", "CLEAR"}, f"{name} : {word}"

    def test_the_french_is_not_the_english(self):
        """Every definition and every list of other names has its own French."""
        with translation.override("en"):
            english = {row["key"]: row for row in glossary.terms()}
        with translation.override("fr"):
            french = {row["key"]: row for row in glossary.terms()}

        for key, row in english.items():
            assert french[key]["definition"] != row["definition"], key
            if row["also"]:
                assert french[key]["also"] != row["also"], key

    def test_acronyms_take_the_letters_of_each_language(self):
        with translation.override("en"):
            english = {row["key"]: row["letters"] for row in glossary.acronyms()}
        with translation.override("fr"):
            french = {row["key"]: row["letters"] for row in glossary.acronyms()}

        assert (english["isms"], french["isms"]) == ("ISMS", "SMSI")
        assert (english["cia"], french["cia"]) == ("CIA", "DIC")
        assert (english["gdpr"], french["gdpr"]) == ("GDPR", "RGPD")
        assert (english["mtd"], french["mtd"]) == ("MTD", "DMT")

    def test_terms_are_sorted_in_the_language_read(self):
        with translation.override("fr"):
            names = [row["name"] for row in glossary.terms()]

        assert names == sorted(names, key=glossary.fold)
        # "Étape" and "Étiquette" sort under E, not after Z.
        assert names.index("Étape") < names.index("Fournisseur")

    def test_search_answers_the_names_people_know(self):
        with translation.override("fr"):
            assert [row["key"] for row in glossary.terms("actif", deep=False)] == ["essential_asset", "support_asset"]
            assert "compliance_assessment" in [row["key"] for row in glossary.terms("audit", deep=False)]
            assert [row["key"] for row in glossary.terms("partie prenante", deep=False)] == ["stakeholder"]
            # Without accents, in any case.
            assert [row["key"] for row in glossary.terms("PERIMETRE", deep=False)] == ["scope"]
            assert [row["key"] for row in glossary.acronyms("smsi", deep=False)] == ["isms"]
            assert [row["key"] for row in glossary.acronyms("défaillance", deep=False)] == ["spof"]
        with translation.override("en"):
            assert [row["key"] for row in glossary.terms("vendor", deep=False)] == ["supplier"]

    def test_a_deep_search_reads_the_definitions_too(self):
        with translation.override("en"):
            assert glossary.terms("ransomware", deep=False) == []
            assert [row["key"] for row in glossary.terms("ransomware")] == ["threat"]

    def test_known_acronyms_answer_for_their_parts(self):
        with translation.override("en"):
            known = glossary.known_acronyms()

        assert {"EBIOS", "RM", "SR", "OV", "ISO", "MITRE", "ATT", "CK", "ISMS"} <= known


# ── The page ────────────────────────────────────────────────────────────────


def _reader(**kwargs):
    user = UserFactory(**kwargs)
    client = Client()
    client.force_login(user)
    return client, user


class TestThePage:
    def test_it_asks_to_sign_in(self):
        response = Client().get(reverse("glossary"))

        assert response.status_code == 302
        assert "/login" in response["Location"]

    def test_it_lists_the_words_and_the_acronyms(self):
        client, _user = _reader()

        response = client.get(reverse("glossary"))
        body = response.content.decode()

        assert response.status_code == 200
        assert 'id="term-essential_asset"' in body
        assert 'id="acronym-isms"' in body
        assert "information security management system" in body
        assert "Also called" in body
        # A list of terms is a description list.
        assert '<dl class="def-list">' in body

    def test_it_reads_in_french(self):
        client, user = _reader()
        user.language = "fr"
        user.save(update_fields=["language"])

        body = client.get(reverse("glossary")).content.decode()

        assert "Bien essentiel" in body
        assert "valeur métier" in body
        assert "SMSI" in body

    def test_a_search_keeps_what_answers(self):
        client, _user = _reader()

        body = client.get(reverse("glossary"), {"q": "vendor"}).content.decode()

        assert 'id="term-supplier"' in body
        assert 'id="term-scope"' not in body
        assert 'value="vendor"' in body

    def test_nothing_found_says_so_and_offers_everything(self):
        client, _user = _reader()

        body = client.get(reverse("glossary"), {"q": "zzzz"}).content.decode()

        assert "Nothing found" in body
        assert "No word of the glossary matches" in body
        assert "def-list" not in body

    def test_what_is_typed_is_shown_as_text(self):
        client, _user = _reader()

        body = client.get(reverse("glossary"), {"q": '"><script>alert(1)</script>'}).content.decode()

        assert "<script>alert(1)</script>" not in body
        assert "&lt;script&gt;" in body

    def test_a_long_search_is_cut(self):
        client, _user = _reader()

        response = client.get(reverse("glossary"), {"q": "a" * 5000})

        assert response.status_code == 200
        assert "a" * 129 not in response.content.decode()

    def test_a_term_links_to_its_register_for_who_may_open_it(self):
        admin_client, _admin = _reader(is_superuser=True)
        reader_client, _reader_user = _reader()
        scopes = reverse("context:scope-list")

        assert f'href="{scopes}"' in admin_client.get(reverse("glossary")).content.decode()
        # Someone with no permission reads the words, and is offered no register.
        reader_body = reader_client.get(reverse("glossary")).content.decode()
        assert "Open the register" not in reader_body
        assert 'id="term-scope"' in reader_body


# ── The search palette ──────────────────────────────────────────────────────


class TestTheSearchPalette:
    def _groups(self, client, query):
        data = json.loads(client.get(reverse("global-search"), {"q": query}).content)
        return {group["label"]: group["items"] for group in data["results"]}

    def test_a_word_people_know_is_answered_with_the_word_used(self):
        client, user = _reader()
        user.language = "fr"
        user.save(update_fields=["language"])

        groups = self._groups(client, "actif")

        titles = [item["title"] for item in groups["Glossaire"]]
        assert titles == ["Bien essentiel", "Bien support"]
        assert groups["Glossaire"][0]["url"] == reverse("glossary") + "#term-essential_asset"

    def test_an_acronym_is_answered_spelled_out(self):
        client, _user = _reader()

        groups = self._groups(client, "spof")

        assert groups["Glossary"][0]["title"] == "SPOF : single point of failure"
        assert groups["Glossary"][0]["url"].endswith("#acronym-spof")

    def test_a_word_of_a_definition_alone_is_not_an_answer(self):
        client, _user = _reader()

        assert "Glossary" not in self._groups(client, "ransomware")

    def test_the_glossary_is_a_place_to_go(self):
        client, _user = _reader()

        data = json.loads(client.get(reverse("global-search")).content)
        navigation = next(group for group in data["results"] if group["label"] == "Navigation")

        assert {"title": "Glossary", "url": reverse("glossary"), "icon": "bi-book"} in navigation["items"]


# ── REST and MCP ────────────────────────────────────────────────────────────


class TestTheRestEndpoint:
    def test_it_asks_to_sign_in(self):
        response = Client().get(reverse("api-glossary"))

        assert response.status_code in (401, 403)

    def test_it_returns_the_vocabulary(self):
        client, _user = _reader()

        payload = client.get(reverse("api-glossary")).json()

        assert payload["status"] == "success"
        assert payload["count"] == len(glossary.TERMS) + len(glossary.ACRONYMS)
        supplier = next(row for row in payload["data"]["terms"] if row["key"] == "supplier")
        assert supplier["name"] == "Supplier"
        assert supplier["also_called"] == ["third party", "vendor", "provider"]
        assert supplier["url"] == reverse("assets:supplier-list")
        isms = next(row for row in payload["data"]["acronyms"] if row["key"] == "isms")
        assert isms == {
            "key": "isms", "acronym": "ISMS", "meaning": "information security management system",
            "definition": isms["definition"],
        }

    def test_a_query_keeps_what_answers(self):
        client, _user = _reader()

        payload = client.get(reverse("api-glossary"), {"q": "audit"}).json()

        assert "compliance_assessment" in [row["key"] for row in payload["data"]["terms"]]
        assert "scope" not in [row["key"] for row in payload["data"]["terms"]]

    def test_it_speaks_the_language_asked(self):
        client, _user = _reader()

        payload = client.get(reverse("api-glossary"), HTTP_ACCEPT_LANGUAGE="fr").json()

        names = {row["key"]: row["name"] for row in payload["data"]["terms"]}
        assert names["stakeholder"] == "Partie intéressée"


class TestTheMcpTool:
    def _tool(self):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        server = McpServer()
        register_all_tools(server)
        return server.get_tool("get_glossary")

    def test_it_is_registered_and_described(self):
        tool = self._tool()

        assert tool is not None
        assert set(tool["inputSchema"]["properties"]) == {"query", "language"}

    def test_it_answers_in_the_language_of_the_user(self):
        user = UserFactory(language="fr")

        result = self._tool()["handler"](user, {"query": "audit"})

        assert result["language"] == "fr"
        assert "Évaluation de conformité" in [row["name"] for row in result["terms"]]

    def test_another_language_can_be_asked(self):
        user = UserFactory(language="fr")

        result = self._tool()["handler"](user, {"language": "en", "query": "isms"})

        assert result["language"] == "en"
        # The acronym itself, and the entries whose definition leans on it.
        assert "ISMS" in [row["acronym"] for row in result["acronyms"]]
        assert "SMSI" not in [row["acronym"] for row in result["acronyms"]]

    def test_an_unknown_language_is_refused(self):
        result = self._tool()["handler"](UserFactory(), {"language": "de"})

        assert result["isError"] is True

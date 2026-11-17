# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The measurable part of the usability standard, as code.

``docs/sdk/usability-standard.md`` says what a screen owes to someone who
has never used the product. What can be measured of it is measured here, so
a form is held to the standard by a test (``core/tests/
test_usability_standard.py``) and not by the memory of whoever reviews it :

- a creation form asks for six fields at most, on one screen;
- a helper says something its label does not, or is absent;
- a label is made of words, an acronym comes after them in brackets
  (everyday ones aside : ``EVERYDAY_ACRONYMS``).

A form that follows the standard is added to the list of that test. The
functions take a form *instance* in the language to check.
"""

from __future__ import annotations

import re
import unicodedata

#: A creation form asks for what makes the record exist : six fields at most.
MAX_CREATION_FIELDS = 6

#: A helper that adds fewer words than this to its label says nothing new.
MIN_NEW_WORDS = 3

#: Acronyms that are everyday words of office and IT life, or the name of a
#: format or a protocol only an administrator meets : more familiar than
#: their expansion, they may stand alone and need no entry in the glossary.
#: Every other acronym is spelled out where it is a label, and explained in
#: ``core/glossary.py``.
EVERYDAY_ACRONYMS = frozenset({
    "AI", "IA", "API", "CSS", "CSV", "DOC", "DOCX", "HR", "HTML", "ID", "IP", "JPEG", "JPG", "JSON", "PDF",
    "PKCE", "PNG", "RH", "SHA", "UI", "URL", "UTF", "XLS", "XLSX",
})

# A mark of the Traffic Light Protocol is written as the protocol writes it.
_PROTOCOL_MARK = re.compile(r"^TLP:[A-Z+]+$")

# Words that carry no information of their own, in the two languages shipped.
_FILLER = frozenset("""
    the and for this that with from are was its his her any all not but you your one can may will when which
    les des une que qui pour par sur dans avec est son ses cet cette aux ces ont leur leurs pas plus tout tous
    name nom
""".split())


def _words(text):
    text = unicodedata.normalize("NFKD", str(text).lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return [word for word in re.findall(r"[a-z]+", text) if len(word) > 2 and word not in _FILLER]


def help_restates_label(label, help_text):
    """Whether ``help_text`` only says its ``label`` again.

    "Name : Name of the scope." tells nothing the label did not. A helper is
    kept when it brings at least ``MIN_NEW_WORDS`` words of its own : an
    example, a consequence, how to answer.
    """
    said = set(_words(label))
    new = [word for word in _words(help_text) if word not in said]
    return len(set(new)) < MIN_NEW_WORDS


def is_bare_acronym(label):
    """Whether ``label`` is an acronym with no word around it ("RTO")."""
    text = str(label).strip()
    letters = re.sub(r"[^A-Za-zÀ-ÿ]", "", text)
    return bool(letters) and len(letters) <= 6 and letters.isupper() and " " not in text


def is_unexplained_acronym(label):
    """Whether ``label`` is an acronym alone that a newcomer cannot be expected to know.

    "RTO" and "SPOF" are; "PDF" and "URL" are everyday words, and "TLP:RED"
    is the mark the protocol itself prescribes.
    """
    text = str(label).strip()
    if not is_bare_acronym(text) or _PROTOCOL_MARK.match(text):
        return False
    letters = re.sub(r"[^A-Za-zÀ-ÿ]", "", text).upper()
    return text.upper() not in EVERYDAY_ACRONYMS and letters not in EVERYDAY_ACRONYMS


def form_findings(form, *, creation=False):
    """What ``form`` owes to the standard, as a list of sentences (empty : nothing).

    ``creation=True`` adds the rules of a creation form (few fields, one
    screen). Hidden fields ask nothing and are left out.
    """
    name = type(form).__name__
    findings = []
    visible = {key: field for key, field in form.fields.items() if not field.widget.is_hidden}
    if creation:
        if len(visible) > MAX_CREATION_FIELDS:
            findings.append(
                f"{name} asks for {len(visible)} fields at creation (at most {MAX_CREATION_FIELDS}) : "
                "keep what makes the record exist, the rest is filled in on its page."
            )
        if getattr(form, "is_multistep", False):
            findings.append(f"{name} walks through steps at creation : a creation fits one screen.")
    for key, field in visible.items():
        label = field.label if field.label is not None else key
        if is_unexplained_acronym(label):
            findings.append(f'{name}.{key} : the label "{label}" is an acronym alone, spell it out first.')
        help_text = str(field.help_text or "").strip()
        if help_text and help_restates_label(label, help_text):
            findings.append(
                f'{name}.{key} : the helper "{help_text}" says the label "{label}" again : '
                "give an example, a consequence or how to answer, or leave it out."
            )
    return findings

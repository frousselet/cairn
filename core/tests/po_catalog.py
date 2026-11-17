# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Read a gettext catalogue, for the tests that hold the words.

The French catalogue (``locale/fr/LC_MESSAGES/django.po``) is maintained by
hand. Tests read the source file rather than the compiled one, so a stale
``.mo`` on a developer's machine cannot hide a defect. This is the small
part of the format the project uses : contexts, plurals, wrapped strings.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FRENCH = REPO / "locale" / "fr" / "LC_MESSAGES" / "django.po"

_KEY = re.compile(r'^(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(".*")$')

#: Folders that hold no string of the interface.
SKIPPED_PARTS = frozenset({".venv", "node_modules", "migrations", "tests", "locale", "docs", "scripts", "staticfiles"})

#: The names a translation function goes by in the code base.
_KEYWORDS = (
    "_", "_l", "_lazy", "gettext", "gettext_lazy", "gettext_noop",
    "ngettext:1,2", "ngettext_lazy:1,2",
    "pgettext:1c,2", "pgettext_lazy:1c,2",
    "npgettext:1c,2,3", "npgettext_lazy:1c,2,3",
)


@dataclass
class Entry:
    """One message : its context, its text, and its translations."""

    context: str = ""
    msgid: str = ""
    plural: str | None = None
    translations: dict = field(default_factory=dict)

    @property
    def key(self):
        return (self.context, self.msgid)

    @property
    def texts(self):
        """Every translated form (one, or one per plural form)."""
        return list(self.translations.values())

    @property
    def text(self):
        """The translation, or its first plural form."""
        return self.translations.get("msgstr", self.translations.get("msgstr[0]", ""))


def read(path=FRENCH):
    """The entries of a ``.po`` / ``.pot`` file, header left out."""
    entries, current, last = [], None, None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            if current is not None:
                entries.append(current)
            current, last = None, None
            continue
        if line.startswith("#"):
            continue
        match = _KEY.match(line)
        if match:
            if current is None:
                current = Entry()
            last, value = match.group(1), ast.literal_eval(match.group(2))
            if last == "msgctxt":
                current.context = value
            elif last == "msgid":
                current.msgid = value
            elif last == "msgid_plural":
                current.plural = value
            else:
                current.translations[last] = value
        elif line.startswith('"') and current is not None and last:
            value = ast.literal_eval(line)
            if last == "msgctxt":
                current.context += value
            elif last == "msgid":
                current.msgid += value
            elif last == "msgid_plural":
                current.plural += value
            else:
                current.translations[last] += value
    if current is not None:
        entries.append(current)
    return [entry for entry in entries if entry.msgid]


def source_files():
    """The Python files and templates that may carry a string of the interface."""
    for path in sorted(REPO.rglob("*")):
        if path.suffix not in (".py", ".html", ".txt") or not path.is_file():
            continue
        if SKIPPED_PARTS & set(path.relative_to(REPO).parts):
            continue
        yield path


def extract():
    """Every message the code asks a translation for, as ``Entry`` rows.

    Templates go through Django's own ``templatize`` and the lot through
    ``xgettext``, which is what ``makemessages`` does : the test reads what
    the tool chain reads. ``None`` when ``xgettext`` is not installed.
    """
    if shutil.which("xgettext") is None:
        return None
    from django.utils.translation import templatize

    with tempfile.TemporaryDirectory(prefix="cairn-i18n-") as tmp:
        sources = []
        for index, path in enumerate(source_files()):
            if path.suffix == ".py":
                sources.append(str(path))
                continue
            converted = Path(tmp) / f"{index}.py"
            converted.write_text(templatize(path.read_text(encoding="utf-8"), origin=str(path)), encoding="utf-8")
            sources.append(str(converted))
        listing = Path(tmp) / "sources.txt"
        listing.write_text("\n".join(sources), encoding="utf-8")
        template = Path(tmp) / "messages.pot"
        subprocess.run(
            ["xgettext", "--language=Python", "--from-code=UTF-8", "--no-location", "--no-wrap",
             f"--files-from={listing}", f"--output={template}", *(f"--keyword={name}" for name in _KEYWORDS)],
            check=True, capture_output=True,
        )
        return read(template) if template.exists() else []

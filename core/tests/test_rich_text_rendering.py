# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A stored text is shown through ``|rich``, or as a plain excerpt.

Every ``textarea.form-control`` of the interface is a rich-text editor
(``templates/base.html``), so a text field may hold markup : printed as it
is, or through ``|linebreaks``, the reader sees its tags (``<p>Text</p>``).
That defect was fixed page by page through lot 3 of the usability programme;
this guard keeps it fixed.

A template prints the value of a text field (any ``TextField`` of the
project's models, matched by its name) in one of three ways :

- ``|rich`` : formatted, sanitized at render time, a plain text keeping its
  line breaks (``core/templatetags/ui.py``);
- ``|striptags`` : a plain excerpt, for a table cell or a tooltip
  (``|safe_html`` on the public Trust Center page sanitizes like ``|rich``);
- inside an HTML attribute, where the value is escaped text anyway.

Anything else fails, unless it is listed below with the reason.
"""

import re
from pathlib import Path

from django.apps import apps
from django.db import models

ROOT = Path(__file__).resolve().parents[2]

#: The filters that show a stored text correctly. ``safe_html`` is the
#: sanitizer of the public Trust Center page (``clean_html``, as ``|rich``).
_SAFE_FILTERS = ("rich", "striptags", "safe_html")

#: Expressions that match a text field's name and are something else, each
#: with its reason : (template, the expression as written).
EXCEPTIONS = {
    ("templates/includes/form_steps.html", "{{ step.intro }}"):
        "the introduction of a form step (core.modal_forms.Step), written in the code",
    ("templates/includes/page_form.html", "{{ step.intro }}"):
        "the introduction of a form step (core.modal_forms.Step), written in the code",
    ("templates/dashboard/widget_gallery.html", "{{ tile.widget.description }}"):
        "the description of a dashboard widget, written in the code",
    ("assets/templates/assets/supplier_detail.html", "{{ sp.purpose }}"):
        "SupplierSubprocessor.purpose is a CharField",
    ("trust_center/templates/trust_center/public_landing.html", '{{ sub.purpose|default:"-" }}'):
        "TrustCenterSubprocessor.purpose is a CharField",
    ("incidents/templates/incidents/_timeline_entries.html", "{{ entry.summary }}"):
        "IncidentTimelineEntry.summary is a CharField",
    ("incidents/templates/incidents/_timeline_entries.html", "{{ entry.superseded_entry.summary|truncatechars:70 }}"):
        "IncidentTimelineEntry.summary is a CharField",
    ("assistant/templates/assistant/_answer.html", "{{ outcome.summary }}"):
        "the summary of an assistant answer, computed for the response and never stored",
    ("templates/includes/help_modal.html", "{{ help_content.body|linebreaks }}"):
        "the help of a page is plain text by design, shown as text with its paragraphs "
        "(helpers/tests/test_help_content.py)",
    ("reports/templates/reports/soa_pdf.html", '{{ row.justification|default:"-"|safe }}'):
        "sanitized by the generator (clean_html, or escape) in reports/generators.py",
}


def _text_field_names():
    names = set()
    for model in apps.get_models():
        if model.__name__.startswith("Historical"):
            continue
        for field in model._meta.concrete_fields:
            if isinstance(field, models.TextField) and not isinstance(field, models.JSONField):
                names.add(field.name)
    # An image held as a data URI is shown through an <img>, never as text.
    return {name for name in names if not name.startswith(("logo", "avatar"))}


def _in_attribute(line, start):
    """Whether position ``start`` of ``line`` sits inside an attribute value."""
    before = line[:start]
    for quote in ('"', "'"):
        opened = before.rfind("=" + quote)
        if opened != -1 and before.count(quote, opened + 2) == 0:
            return True
    return False


def _templates():
    for path in sorted(ROOT.glob("**/templates/**/*.html")):
        if ".venv" in path.parts or "node_modules" in path.parts:
            continue
        yield path


def test_every_stored_text_is_shown_formatted_or_as_an_excerpt():
    names = _text_field_names()
    pattern = re.compile(
        r"\{\{\s*([a-z_][\w.]*)\.(%s)\s*(\|[^}]*)?\}\}" % "|".join(sorted(names, key=len, reverse=True))
    )
    raw, used = [], set()
    for path in _templates():
        relative = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in pattern.finditer(line):
                variable, filters = match.group(1), match.group(3) or ""
                if variable.split(".")[0].endswith("form"):
                    continue  # a form field : it renders its widget
                if any(name in filters for name in _SAFE_FILTERS) or _in_attribute(line, match.start()):
                    continue
                key = (relative, match.group(0))
                if key in EXCEPTIONS:
                    used.add(key)
                    continue
                raw.append(f"{relative}:{number} {match.group(0)}")
    assert raw == [], "Show a stored text through |rich, or |striptags for an excerpt :\n" + "\n".join(raw)
    assert set(EXCEPTIONS) <= used, f"Exceptions that no longer match anything : {sorted(set(EXCEPTIONS) - used)}"


def test_a_stored_text_is_never_marked_safe_by_hand():
    """``|safe`` on a stored text skips the sanitizer; ``|rich`` is the way."""
    names = _text_field_names()
    pattern = re.compile(r"\{\{\s*[a-z_][\w.]*\.(%s)\b[^}]*\|safe\b[^}]*\}\}" % "|".join(names))
    marked = []
    for path in _templates():
        relative = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in pattern.finditer(line):
                if (relative, match.group(0)) not in EXCEPTIONS:
                    marked.append(f"{relative}:{number} {match.group(0)}")
    assert marked == []

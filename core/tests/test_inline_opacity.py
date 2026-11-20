# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""A text is quieted by its colour token, never by an opacity.

An opacity fades the text and its contrast with it : a grey that passes
WCAG 2.2 AA at full strength fails at 45 %. The text tokens (``--text-muted``,
``--text-secondary``) are what quiet a text (CLAUDE.md, accessibility). A
template sets no ``opacity`` in a ``style`` attribute and uses no Bootstrap
``opacity-*`` utility; a stylesheet is where a state that fades a whole block
(a dragged tile, a disabled control) is declared.

What is not a text is listed below with the reason.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_STYLE_ATTRIBUTE = re.compile(r"""style\s*=\s*(["'])(?:(?!\1).)*\bopacity\s*:""", re.IGNORECASE)
_UTILITY = re.compile(r"""class\s*=\s*(["'])(?:(?!\1).)*\bopacity-\d+\b""")

#: (template, line content) -> why the opacity fades no text.
EXCEPTIONS = {
    ("templates/includes/dashboard_indicators.html", '<div style="opacity:.35">'):
        "the skeleton bars of an empty indicator tile : decorative blocks, no text",
}


def test_no_template_quiets_a_text_with_an_opacity():
    found, used = [], set()
    for path in sorted(ROOT.glob("**/templates/**/*.html")):
        if ".venv" in path.parts or "node_modules" in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not (_STYLE_ATTRIBUTE.search(line) or _UTILITY.search(line)):
                continue
            key = (relative, line.strip())
            if key in EXCEPTIONS:
                used.add(key)
                continue
            found.append(f"{relative}:{number} {line.strip()}")
    assert found == [], "Quiet a text with a text token, not an opacity :\n" + "\n".join(found)
    assert set(EXCEPTIONS) <= used, f"Exceptions that no longer match anything : {sorted(set(EXCEPTIONS) - used)}"

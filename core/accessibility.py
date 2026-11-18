# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""What Cairn states about its own accessibility.

One statement, shown by the About dialog and returned by
``GET /api/v1/accessibility/`` and the ``get_accessibility_statement`` MCP
tool : the level the product is built to meet, what is checked on every
change, and what is not claimed.

A statement read by an auditor is one the project can back. No automated
check proves a page accessible (``docs/technical/testing.md``) : the checks
listed here catch what a machine can measure, and nobody has yet evaluated
the product against every success criterion. Until someone has, its
conformance is ``not_assessed``, in the words of the W3C statement generator
(fully conformant, partially conformant, non conformant, not assessed), and
the statement claims nothing more.

When an evaluation exists, change ``CONFORMANCE`` and ``LIMITS``, and say in
this docstring who made it, when and on which version : a status without its
evidence is the claim this module exists to prevent.

``core/tests/test_accessibility.py`` holds the statement to the checks : the
level it names is the one ``scripts/a11y_audit.py`` fails on, and every check
it lists is a file of the repository.
"""

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

#: The standard the product is built to meet, its version and its level.
STANDARD = "WCAG"
VERSION = "2.2"
LEVEL = "AA"

#: The words a conformance status is given in (W3C statement generator).
CONFORMANCE_STATUSES = ("fully_conformant", "partially_conformant", "non_conformant", "not_assessed")

#: No evaluation by a person covers every criterion : nothing is claimed.
CONFORMANCE = "not_assessed"

#: Where a barrier is reported : the issue forms of the project.
REPORT_URL = "https://github.com/frousselet/cairn/issues/new/choose"

TARGET = _("Cairn is built to meet the Web Content Accessibility Guidelines (WCAG) %(version)s at level %(level)s.")

LIMITS = _("Its conformance has not been assessed : automated checks see only part of the criteria, and nobody has evaluated Cairn against all of them yet. Full conformance is not claimed.")


@dataclass(frozen=True)
class Check:
    """One automated check the statement rests on."""

    key: str
    #: What it checks, in words.
    label: str
    #: The file of the repository that runs it.
    source: str


#: Run on every change by the continuous integration (``tests.yml``).
CHECKS = (
    Check(
        "contrast",
        _("The contrast of every text colour, in the light and the dark theme."),
        "core/tests/test_contrast.py",
    ),
    Check(
        "markup",
        _("The markup of every page : a name for each control and each image, a label for each field, links the keyboard reaches."),
        "core/tests/markup_audit.py",
    ),
    Check(
        "rendered",
        _("A reference set of pages opened in a browser and audited with axe-core, in both themes."),
        "scripts/a11y_audit.py",
    ),
)


def statement():
    """The statement, in the active language, as plain values.

    The About dialog renders it and the REST API and the MCP tool return it :
    the three cannot say different things.
    """
    return {
        "standard": STANDARD,
        "version": VERSION,
        "level": LEVEL,
        "conformance": CONFORMANCE,
        "target": str(TARGET) % {"version": VERSION, "level": LEVEL},
        "checks": [{"key": check.key, "label": str(check.label), "source": check.source} for check in CHECKS],
        "limits": str(LIMITS),
        "report_url": REPORT_URL,
    }

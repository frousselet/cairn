# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Text contrast (WCAG 2.2 AA, 1.4.3 : 4.5:1), checked on the design tokens.

The palette is read from ``static/css/cairn/00-tokens.css`` itself, so the
test follows the tokens : change a text colour or a surface and the ratios
are recomputed. Three things are guarded :

- every text token reads on every surface, in the light and the dark theme;
- a status ink reads on its own soft background (a badge);
- no rule draws text with a *fill* token (``--accent``, ``--success``...),
  which only clears 3:1 : text uses the ink tokens (``--accent-text``...).

The colours an administrator types (company accent, Trust Center accent) are
not in the palette : ``core.colors`` derives a readable tone from any of them.
"""

import re
import subprocess

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from accounts.models import CompanySettings
from accounts.tests.factories import UserFactory
from core import colors

TOKENS = settings.BASE_DIR / "static" / "css" / "cairn" / "00-tokens.css"

TEXT_TOKENS = (
    "text-primary", "text-secondary", "text-muted", "text-xs", "text-sidebar-sub",
    "accent-text", "success-text", "warning-text", "danger-text", "info-text",
)
SURFACES = ("surface", "surface-raised", "surface-muted", "surface-subtle", "bg-page")
STATUSES = ("accent", "success", "warning", "danger", "info")
FILL_TOKENS = "accent|success|warning|danger|info"


def _declarations(block):
    return dict(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", block))


def _tokens(theme):
    """``{token: value}`` for a theme : the root palette, overridden by the dark block."""
    css = re.sub(r"/\*.*?\*/", "", TOKENS.read_text(), flags=re.S)
    values = _declarations(re.search(r":root\s*\{(.*?)\n\}", css, re.S).group(1))
    if theme == "dark":
        values.update(_declarations(re.search(r'\[data-bs-theme="dark"\]\s*\{(.*?)\n\}', css, re.S).group(1)))
    return values


def _resolve(tokens, name, over=None):
    """The ``#RRGGBB`` a token renders as; a translucent one is laid over ``over``."""
    value = tokens[name].strip()
    for _ in range(10):
        reference = re.fullmatch(r"var\(--([\w-]+)\)", value)
        if not reference:
            break
        value = tokens[reference.group(1)].strip()
    if value.startswith("#"):
        digits = value.lstrip("#")
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        return "#" + digits.upper()
    translucent = re.fullmatch(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", value)
    assert translucent and over, f"--{name} : cannot resolve {value!r}"
    red, green, blue = (int(translucent.group(i)) for i in (1, 2, 3))
    return colors.mix("#{:02X}{:02X}{:02X}".format(red, green, blue), over, float(translucent.group(4)))


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_text_token_reads_on_every_surface(theme):
    tokens = _tokens(theme)
    failures = []
    for text in TEXT_TOKENS:
        for surface in SURFACES:
            ratio = colors.contrast_ratio(_resolve(tokens, text), _resolve(tokens, surface))
            if ratio < colors.TEXT_CONTRAST:
                failures.append(f"--{text} on --{surface} : {ratio:.2f}:1")
    assert not failures, f"{theme} theme, text under 4.5:1 :\n  " + "\n  ".join(failures)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_a_status_ink_reads_on_its_own_soft_background(theme):
    """A badge : the status ink on the status' soft fill."""
    tokens = _tokens(theme)
    failures = []
    for status in STATUSES:
        for surface in ("surface", "surface-raised"):
            soft = _resolve(tokens, f"{status}-soft", over=_resolve(tokens, surface))
            ratio = colors.contrast_ratio(_resolve(tokens, f"{status}-text"), soft)
            if ratio < colors.TEXT_CONTRAST:
                failures.append(f"--{status}-text on --{status}-soft over --{surface} : {ratio:.2f}:1")
    assert not failures, f"{theme} theme, badges under 4.5:1 :\n  " + "\n  ".join(failures)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_focus_ring_stands_out_on_every_surface(theme):
    """WCAG 1.4.11 : a focus indicator needs 3:1 against what it is drawn on."""
    tokens = _tokens(theme)
    share = float(re.search(r"var\(--text-primary\) (\d+)%", tokens["focus-ring"]).group(1)) / 100
    for surface in SURFACES:
        background = _resolve(tokens, surface)
        ring = colors.mix(_resolve(tokens, "text-primary"), background, share)
        assert colors.contrast_ratio(ring, background) >= 3, f"{theme} : focus ring on --{surface}"


def test_text_is_never_drawn_with_a_fill_token():
    """``color: var(--success)`` is a 3:1 colour used as text. The ink token
    (``--success-text``) is the one that clears 4.5:1 in both themes."""
    files = subprocess.run(  # noqa: S603, S607 - fixed command, repository files
        ["git", "ls-files", "*.css", "*.html", "*.js", "*.py"],
        cwd=settings.BASE_DIR, capture_output=True, text=True, check=True,
    ).stdout.split()
    pattern = re.compile(
        rf"(?<![-\w])color\s*:\s*var\(--(?:{FILL_TOKENS})\)|--btn-fg(?:-hover)?\s*:\s*var\(--(?:{FILL_TOKENS})\)"
    )
    offenders = []
    for name in files:
        if name.startswith(("static/vendor/", "docs/")) or "/tests/" in name:
            continue
        if not (settings.BASE_DIR / name).is_file():
            continue  # deleted in the working tree, not committed yet
        for number, line in enumerate((settings.BASE_DIR / name).read_text(errors="replace").splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{name}:{number}")
    assert not offenders, "text drawn with a fill token (use the -text ink) :\n  " + "\n  ".join(offenders)


# ── Colours typed by an administrator ─────────────────────────────────────

ANY_COLOUR = ["#1E3A8A", "#0E9F6E", "#FFD400", "#FF0000", "#3B82F6", "#808080", "#000000", "#FFFFFF", "#F5E6FF"]


@pytest.mark.parametrize("colour", ANY_COLOUR)
def test_any_accent_gets_a_readable_ink_in_both_themes(colour):
    light, dark = colors.ink_on_light(colour), colors.ink_on_dark(colour)
    for surface in colors.LIGHT_SURFACES:
        assert colors.contrast_ratio(light, surface) >= colors.TEXT_CONTRAST, (colour, light, surface)
    for surface in colors.DARK_SURFACES:
        assert colors.contrast_ratio(dark, surface) >= colors.TEXT_CONTRAST, (colour, dark, surface)


@pytest.mark.parametrize("colour", ANY_COLOUR)
def test_any_accent_gets_a_readable_label_and_banner(colour):
    assert colors.contrast_ratio(colour, colors.label_on(colour)) >= colors.TEXT_CONTRAST
    assert colors.contrast_ratio(colors.fill_under_white(colour), "#FFFFFF") >= colors.TEXT_CONTRAST


def test_a_colour_that_already_reads_is_left_alone():
    assert colors.ink_on_light("#1E3A8A") == "#1E3A8A"
    assert colors.fill_under_white("#1E3A8A") == "#1E3A8A"
    assert colors.label_on("#1E3A8A") == "#FFFFFF"
    assert colors.label_on("#FFD400") == "#18181B"


def test_the_ink_keeps_the_hue():
    """A green stays a green : only the lightness moves."""
    import colorsys

    hue = lambda value: colorsys.rgb_to_hls(*colors.parse_hex(value))[0]  # noqa: E731
    assert abs(hue(colors.ink_on_light("#0E9F6E")) - hue("#0E9F6E")) < 0.01
    assert abs(hue(colors.ink_on_dark("#0E9F6E")) - hue("#0E9F6E")) < 0.01


def test_the_short_hex_form_is_understood():
    """The Trust Center accent accepts ``#RGB`` as well as ``#RRGGBB``."""
    assert colors.ink_on_light("#FD0") == colors.ink_on_light("#FFDD00")
    assert colors.contrast_ratio(colors.ink_on_light("#FD0"), "#FFFFFF") >= colors.TEXT_CONTRAST


def test_a_malformed_colour_is_passed_through():
    for helper in (colors.ink_on_light, colors.ink_on_dark, colors.fill_under_white):
        assert helper("not-a-colour") == "not-a-colour"
    assert colors.label_on("not-a-colour") == "#FFFFFF"


@pytest.mark.django_db
def test_a_pale_company_accent_is_given_a_readable_text_tone():
    """A yellow accent : the fill stays yellow, links and labels drawn in it
    take the deepened ink, and what sits on the fill turns dark."""
    CompanySettings.objects.create(name="Voltara Energy", accent_color="#FFD400")
    client = Client()
    client.force_login(UserFactory(is_superuser=True))
    response = client.get(reverse("home"))
    light = response.context["ACCENT_LIGHT_TEXT"]
    assert colors.contrast_ratio(light, "#FFFFFF") >= colors.TEXT_CONTRAST
    assert colors.contrast_ratio(response.context["ACCENT_DARK_TEXT"], "#1C1F23") >= colors.TEXT_CONTRAST
    assert response.context["ACCENT_LIGHT_FG"] == "#18181B"
    html = response.content.decode()
    assert f"--accent-text: {light};" in html
    assert "--accent-contrast: #18181B;" in html

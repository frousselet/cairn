# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Colour arithmetic for the colours an administrator chooses.

The palette shipped in ``static/css/cairn/00-tokens.css`` is checked once, by
hand and by ``core/tests/test_contrast.py``. A colour typed in the company
settings or the Trust Center settings is not : whatever it is, the interface
must stay readable (WCAG 2.2, 1.4.3 : 4.5:1 for text). These helpers derive,
from any ``#RRGGBB``, the tone that carries text on a given surface and the
label colour that sits on the colour itself.
"""

import colorsys

# Contrast a text colour must reach on its background (WCAG 2.2 AA, 1.4.3).
TEXT_CONTRAST = 4.5

# The surfaces accent-coloured text sits on, per theme, darkest (light theme)
# or lightest (dark theme) first : the page, the cards, the subtle fills and
# the tinted table rows. An ink readable on these is readable everywhere.
LIGHT_SURFACES = ("#F5F5F5", "#FAFAFA", "#FFFFFF")
DARK_SURFACES = ("#322C21", "#2A2D32", "#1C1F23", "#16181B")

DARK_LABEL = "#18181B"
LIGHT_LABEL = "#FFFFFF"


def parse_hex(value):
    """``#RRGGBB`` as ``(r, g, b)`` floats in 0..1, or ``None`` if malformed."""
    digits = (value or "").strip().lstrip("#")
    if len(digits) == 3:  # the short form, #1AF
        digits = "".join(character * 2 for character in digits)
    if len(digits) != 6:
        return None
    try:
        return tuple(int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return None


def to_hex(red, green, blue):
    return "#{:02X}{:02X}{:02X}".format(round(red * 255), round(green * 255), round(blue * 255))


def relative_luminance(value):
    """WCAG relative luminance of ``#RRGGBB`` (0 black, 1 white)."""
    rgb = parse_hex(value)
    if rgb is None:
        raise ValueError(f"not a #RRGGBB colour : {value!r}")

    def linear(channel):
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first, second):
    """WCAG contrast ratio between two ``#RRGGBB`` colours (1 to 21)."""
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def mix(colour, base, share):
    """``share`` (0..1) of ``colour`` over ``base`` : what ``color-mix`` renders."""
    top, bottom = parse_hex(colour), parse_hex(base)
    return to_hex(*(share * t + (1 - share) * b for t, b in zip(top, bottom, strict=True)))


def label_on(colour):
    """The label colour (near-black or white) that reads best on ``colour``."""
    if parse_hex(colour) is None:
        return LIGHT_LABEL
    dark, light = contrast_ratio(colour, DARK_LABEL), contrast_ratio(colour, LIGHT_LABEL)
    if light >= dark:
        return LIGHT_LABEL
    # A narrow band of mid tones leaves the near-black label a hair under
    # 4.5:1 : plain black clears it.
    return DARK_LABEL if dark >= TEXT_CONTRAST else "#000000"


def ink(colour, surfaces, minimum=TEXT_CONTRAST):
    """``colour`` moved in lightness, hue and saturation kept, until it reads
    as text on every one of ``surfaces``.

    Darkened on light surfaces, lightened on dark ones, and only as far as
    needed : a colour that already reads is returned unchanged. A malformed
    value is returned as is (the caller falls back to the default palette).
    """
    rgb = parse_hex(colour)
    if rgb is None:
        return colour
    on_light = relative_luminance(surfaces[0]) > 0.5
    hue, lightness, saturation = colorsys.rgb_to_hls(*rgb)
    step = -0.01 if on_light else 0.01
    candidate = to_hex(*rgb)
    while not all(contrast_ratio(candidate, surface) >= minimum for surface in surfaces):
        lightness += step
        if not 0 <= lightness <= 1:
            # Black or white : the end of the scale always reads.
            return "#000000" if on_light else "#FFFFFF"
        candidate = to_hex(*colorsys.hls_to_rgb(hue, lightness, saturation))
    return candidate


def ink_on_light(colour):
    """The text tone of ``colour`` on the light theme, its own soft fill included."""
    if parse_hex(colour) is None:
        return colour
    return ink(colour, (mix(colour, "#FFFFFF", 0.12), *LIGHT_SURFACES))


def ink_on_dark(colour):
    """The text tone of ``colour`` on the dark theme, its own soft fill included."""
    if parse_hex(colour) is None:
        return colour
    return ink(colour, (mix(colour, DARK_SURFACES[0], 0.18), *DARK_SURFACES))


def fill_under_white(colour):
    """``colour`` darkened, hue kept, until a white label reads on it.

    For a banner whose text is white whatever the colour chosen : a pale or
    mid-tone accent is deepened rather than the label flipped to black, so a
    theme written for white text keeps working.
    """
    if parse_hex(colour) is None:
        return colour
    return ink(colour, (LIGHT_LABEL,))


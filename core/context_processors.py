import colorsys

from django.conf import settings


def app_version(request):
    return {"APP_VERSION": settings.APP_VERSION}


def _parse_hex(hex_color):
    """Parse ``#RRGGBB`` to ``(hue, lightness, saturation)`` or ``None``."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return None
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return None
    return colorsys.rgb_to_hls(r, g, b)


def _hls_to_hex(hue, light, sat):
    r, g, b = colorsys.hls_to_rgb(hue, light, sat)
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def _contrast_fg(hex_color):
    """Return a legible foreground (#18181B dark or #FFFFFF) for text sitting on
    ``hex_color``, based on its perceived luminance."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return "#FFFFFF"
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return "#FFFFFF"
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#18181B" if luminance > 0.6 else "#FFFFFF"


def _accent_for_light(hex_color):
    """Darken a pale accent so it stays legible on the light canvas."""
    parsed = _parse_hex(hex_color)
    if parsed is None:
        return hex_color
    hue, light, sat = parsed
    return _hls_to_hex(hue, min(light, 0.62), sat)


def _accent_for_dark(hex_color):
    """Lighten a dark accent so it stays legible on the dark charcoal canvas.
    Low-saturation colours (black / grey) carry no hue cue, so they need a much
    higher lightness floor than vivid colours to read as an accent."""
    parsed = _parse_hex(hex_color)
    if parsed is None:
        return hex_color
    hue, light, sat = parsed
    floor = 0.62 + (1 - sat) * 0.34  # ~0.96 (near-white) for greys, 0.62 for vivid hues
    return _hls_to_hex(hue, min(max(light, floor), 0.97), sat)


def assistant_enabled(request):
    return {"AI_ASSISTANT_ENABLED": settings.AI_ASSISTANT_ENABLED}


def company(request):
    """Expose the company settings singleton and the resolved application name to
    every template (sidebar brand, tab titles). Uses .first() so a GET never
    creates the singleton row; APP_NAME falls back to "Cairn" and
    ASSISTANT_NAME (the AI assistant brand) to "Ask Cairn"."""
    from django.db import DatabaseError

    from accounts.models import CompanySettings

    try:
        settings_obj = CompanySettings.objects.first()
    except DatabaseError:
        # Fresh database (tables not migrated yet): the onboarding screen renders
        # before any table exists, so fall back to defaults instead of crashing.
        settings_obj = None
    app_name = (settings_obj.app_name if settings_obj and settings_obj.app_name else "Cairn")
    assistant_name = (
        settings_obj.assistant_name
        if settings_obj and settings_obj.assistant_name
        else "Ask Cairn"
    )
    ctx = {"company": settings_obj, "APP_NAME": app_name, "ASSISTANT_NAME": assistant_name}
    accent = settings_obj.accent_color if settings_obj else ""
    if accent:
        # Adjust lightness per theme so any chosen colour stays legible: darken
        # pale colours for the light canvas, lighten dark ones for the dark
        # charcoal canvas (greys are pushed lighter than vivid hues).
        ctx["ACCENT_LIGHT"] = _accent_for_light(accent)
        ctx["ACCENT_DARK"] = _accent_for_dark(accent)
        # Foreground (text / checkmarks / switch knobs) that sits on the accent.
        ctx["ACCENT_LIGHT_FG"] = _contrast_fg(ctx["ACCENT_LIGHT"])
        ctx["ACCENT_DARK_FG"] = _contrast_fg(ctx["ACCENT_DARK"])
    return ctx

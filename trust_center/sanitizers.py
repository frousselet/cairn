"""Allowlist-based SVG sanitization for the public Trust Center.

Logos (framework / supplier / company) are stored as raw SVG markup in
``TextField``s and rendered into authenticated pages today. On the *public*,
unauthenticated Trust Center, raw SVG is an XSS sink (``<script>``, ``on*``
handlers, ``<foreignObject>``, external references). :func:`clean_svg`
reconstructs the markup from a strict allowlist of elements and attributes,
dropping everything else and suppressing the content of dangerous elements.

No third-party dependency is used (no bleach / nh3 / lxml): the stdlib HTML
parser is sufficient for the small, presentation-only SVGs we render, and the
allowlist is deny-by-default, so an unknown element or attribute is removed
rather than passed through.
"""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

# Presentation-only elements. Anything not listed is dropped. Scripting,
# foreignObject, animation and external-image elements are intentionally absent.
ALLOWED_TAGS = frozenset(
    {
        "svg",
        "g",
        "path",
        "circle",
        "ellipse",
        "rect",
        "line",
        "polyline",
        "polygon",
        "defs",
        "lineargradient",
        "radialgradient",
        "stop",
        "title",
        "desc",
        "clippath",
        "mask",
        "use",
        "symbol",
        "text",
        "tspan",
    }
)

# Elements whose entire content must be discarded, not just the tag.
SUPPRESSED_TAGS = frozenset(
    {
        "script",
        "style",
        "foreignobject",
        "animate",
        "animatetransform",
        "animatemotion",
        "set",
        "image",
        "iframe",
        "a",
    }
)

# Safe geometry / presentation attributes shared across elements.
ALLOWED_ATTRS = frozenset(
    {
        "viewbox",
        "xmlns",
        "width",
        "height",
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "cx",
        "cy",
        "r",
        "rx",
        "ry",
        "d",
        "points",
        "transform",
        "fill",
        "fill-rule",
        "fill-opacity",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-miterlimit",
        "stroke-dasharray",
        "stroke-opacity",
        "opacity",
        "offset",
        "stop-color",
        "stop-opacity",
        "gradientunits",
        "gradienttransform",
        "spreadmethod",
        "clip-path",
        "clip-rule",
        "id",
        "class",
        "preserveaspectratio",
        "text-anchor",
        "font-family",
        "font-size",
        "font-weight",
        "letter-spacing",
        "dominant-baseline",
        "dx",
        "dy",
    }
)

# Local-reference attributes: only allowed when the value points inside the
# document (``#id``), never to an external URL.
LOCAL_REF_ATTRS = frozenset({"href", "xlink:href"})

# html.parser lowercases names, but several SVG names are case-sensitive. These
# maps restore the canonical camelCase so the output is correct in any context
# (inline HTML auto-adjusts, but a standalone / API consumer would not).
TAG_CASE = {
    "lineargradient": "linearGradient",
    "radialgradient": "radialGradient",
    "clippath": "clipPath",
}
ATTR_CASE = {
    "viewbox": "viewBox",
    "preserveaspectratio": "preserveAspectRatio",
    "gradientunits": "gradientUnits",
    "gradienttransform": "gradientTransform",
    "spreadmethod": "spreadMethod",
    "clippathunits": "clipPathUnits",
    "maskunits": "maskUnits",
    "maskcontentunits": "maskContentUnits",
}

_DANGEROUS_STYLE = re.compile(r"(url\s*\(|expression\s*\(|javascript:|@import)", re.IGNORECASE)


def _safe_style(value: str) -> str | None:
    """Return the style value if it carries no active content, else ``None``."""
    if _DANGEROUS_STYLE.search(value or ""):
        return None
    return value


class _SVGSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._suppress_depth = 0
        self._seen_svg = False

    # -- helpers -----------------------------------------------------------
    def _clean_attrs(self, attrs) -> str:
        out = []
        for name, value in attrs:
            name = (name or "").lower()
            value = value or ""
            if name.startswith("on"):
                continue
            if name == "style":
                safe = _safe_style(value)
                if safe is None:
                    continue
                out.append(f'style="{escape(safe, quote=True)}"')
                continue
            if name in LOCAL_REF_ATTRS:
                if value.startswith("#"):
                    out.append(f'{name}="{escape(value, quote=True)}"')
                continue
            if name in ALLOWED_ATTRS:
                out.append(f'{ATTR_CASE.get(name, name)}="{escape(value, quote=True)}"')
        return (" " + " ".join(out)) if out else ""

    def _emit_start(self, tag, attrs, self_closing):
        out = f"<{TAG_CASE.get(tag, tag)}{self._clean_attrs(attrs)}"
        out += "/>" if self_closing else ">"
        self.parts.append(out)

    # -- parser hooks ------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self._suppress_depth:
            if tag in SUPPRESSED_TAGS:
                self._suppress_depth += 1
            return
        if tag in SUPPRESSED_TAGS:
            self._suppress_depth = 1
            return
        if tag == "svg":
            self._seen_svg = True
        if tag in ALLOWED_TAGS:
            self._emit_start(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self._suppress_depth:
            return
        if tag in SUPPRESSED_TAGS:
            return
        if tag == "svg":
            self._seen_svg = True
        if tag in ALLOWED_TAGS:
            self._emit_start(tag, attrs, self_closing=True)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._suppress_depth:
            if tag in SUPPRESSED_TAGS:
                self._suppress_depth -= 1
            return
        if tag in ALLOWED_TAGS:
            self.parts.append(f"</{TAG_CASE.get(tag, tag)}>")

    def handle_data(self, data):
        if self._suppress_depth:
            return
        self.parts.append(escape(data))

    # Comments, declarations and processing instructions are dropped.
    def handle_comment(self, data):
        return

    def handle_decl(self, decl):
        return

    def handle_pi(self, data):
        return

    def result(self) -> str:
        return "".join(self.parts) if self._seen_svg else ""


def clean_svg(markup: str) -> str:
    """Return a sanitized copy of ``markup`` safe to embed in a public page.

    Returns an empty string when the input is empty or contains no ``<svg>``
    root, so non-SVG content (including a stray ``<script>``) never renders.
    """
    if not markup or "<svg" not in markup.lower():
        return ""
    parser = _SVGSanitizer()
    try:
        parser.feed(markup)
        parser.close()
    except Exception:
        return ""
    return parser.result()


# --- Rich-text (Jodit) sanitization -----------------------------------------
# Admin-authored fields (intro, descriptions) are edited with the Jodit WYSIWYG
# and rendered on the public page. A Contributeur can edit settings/descriptions
# but not publish, so this is a potential stored-XSS path: only a small set of
# formatting tags is allowed, all attributes are dropped (except safe <a href>),
# and the content of active elements is discarded.

ALLOWED_HTML_TAGS = frozenset(
    {
        "p", "br", "strong", "b", "em", "i", "u", "s", "strike", "del", "ins",
        "ul", "ol", "li", "a", "h2", "h3", "h4", "h5", "h6", "blockquote",
        "code", "pre", "span", "hr",
    }
)

SUPPRESSED_HTML_TAGS = frozenset(
    {
        "script", "style", "iframe", "object", "embed", "form", "input",
        "textarea", "button", "select", "option", "svg", "link", "meta",
        "head", "title", "noscript", "template", "base",
    }
)

_SELF_CLOSING_HTML = frozenset({"br", "hr"})
_SAFE_HREF = re.compile(r"^(https?:|mailto:|/|#)", re.IGNORECASE)


class _HTMLSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._suppress_depth = 0

    def _attrs_for(self, tag, attrs) -> str:
        # Only <a href> with a safe scheme survives; everything else (style,
        # class, on*, ...) is dropped.
        if tag != "a":
            return ""
        for name, value in attrs:
            if (name or "").lower() == "href" and value and _SAFE_HREF.match(value.strip()):
                href = escape(value.strip(), quote=True)
                return f' href="{href}" rel="noopener noreferrer nofollow" target="_blank"'
        return ""

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self._suppress_depth:
            if tag in SUPPRESSED_HTML_TAGS:
                self._suppress_depth += 1
            return
        if tag in SUPPRESSED_HTML_TAGS:
            self._suppress_depth = 1
            return
        if tag in ALLOWED_HTML_TAGS:
            close = "/" if tag in _SELF_CLOSING_HTML else ""
            self.parts.append(f"<{tag}{self._attrs_for(tag, attrs)}{close}>")

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self._suppress_depth:
            return
        if tag in ALLOWED_HTML_TAGS:
            self.parts.append(f"<{tag}{self._attrs_for(tag, attrs)}/>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._suppress_depth:
            if tag in SUPPRESSED_HTML_TAGS:
                self._suppress_depth -= 1
            return
        if tag in ALLOWED_HTML_TAGS and tag not in _SELF_CLOSING_HTML:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self._suppress_depth:
            return
        self.parts.append(escape(data))

    def handle_comment(self, data):
        return

    def handle_decl(self, decl):
        return

    def handle_pi(self, data):
        return

    def result(self) -> str:
        return "".join(self.parts)


def clean_html(markup: str) -> str:
    """Sanitize admin-authored rich text for safe rendering on a public page."""
    if not markup:
        return ""
    parser = _HTMLSanitizer()
    try:
        parser.feed(markup)
        parser.close()
    except Exception:
        return ""
    return parser.result()


# --- Custom CSS sanitization ------------------------------------------------
# Operator-supplied CSS injected into the public page. CSS cannot run JS on its
# own, but it must not break out of the <style> element or pull active content,
# so the breakout token and a few dangerous constructs are stripped.

_CSS_DANGEROUS = re.compile(
    r"(</\s*style|<\s*script|@import|expression\s*\(|javascript:|behaviou?r\s*:|-moz-binding)",
    re.IGNORECASE,
)


def clean_css(css: str) -> str:
    """Strip active-content / breakout constructs from custom CSS.

    Applied to a fixed point so a split-token payload (e.g. ``<scr<script>ipt>``)
    cannot reconstruct a stripped token after a single pass. Custom CSS is served
    from a dedicated ``text/css`` endpoint (not inlined in a ``<style>``), so this
    is defence in depth rather than the sole boundary.
    """
    if not css:
        return ""
    previous = None
    out = css
    while previous != out:
        previous = out
        out = _CSS_DANGEROUS.sub("", out)
    return out


# --- Logo rendering ---------------------------------------------------------
# Logos (company / framework / supplier) are stored either as a data-URI image
# (the common case: an uploaded raster resized to a data URI) or, occasionally,
# as raw inline SVG markup. These helpers render either form safely.

_DATA_OR_URL = re.compile(r"^(data:image/|https?://|/)", re.IGNORECASE)


def logo_href(raw: str) -> str:
    """Return a usable image URL/data-URI for an <img src>/favicon, else ''."""
    raw = (raw or "").strip()
    if raw and _DATA_OR_URL.match(raw):
        return raw
    return ""


def logo_html(raw: str) -> str:
    """Return safe HTML for a logo: an <img> for a data-URI/URL, sanitized inline
    SVG for raw SVG markup, or '' for anything else."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if "<svg" in raw.lower():
        return clean_svg(raw)
    if _DATA_OR_URL.match(raw):
        return f'<img src="{escape(raw, quote=True)}" alt="" loading="lazy">'
    return ""

# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Accessibility checks that can be read from the markup alone.

A rendered page is parsed with the standard library and searched for the
defects a screen reader or a keyboard trips on, whatever the theme :

- an image with no ``alt`` attribute (WCAG 1.1.1);
- a link or a button with no accessible name (2.4.4, 4.1.2);
- a link that acts (``hx-get``, ``onclick``...) but has no ``href``, so the
  keyboard never reaches it (2.1.1);
- a form control with no label (1.3.1, 3.3.2);
- a positive ``tabindex``, which overrides the reading order (2.4.3);
- an ``aria-label`` on an element with no role (a ``div``, a ``span``, an
  ``i``...), a name that screen readers do not announce (4.1.2) : the element
  takes the role of what it is (``img`` for an icon or a dot that means
  something, ``group`` for a set of links, ``region`` for a panel);
- an inline event handler (``onclick=``...), which the Content Security Policy
  refuses : the control is there and does nothing.

What depends on the cascade (contrast, target size, focus rings) is left to the
browser audit, ``scripts/a11y_audit.py``. Markup built by a script at run time
is not seen here either : ``<script>`` content is skipped.
"""

from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
# Controls that label themselves (their value is their name) or carry no name.
SELF_NAMED_INPUTS = {"hidden", "submit", "button", "reset", "image"}
ACTING_ATTRIBUTES = ("hx-get", "hx-post", "hx-delete", "hx-put", "hx-patch", "onclick", "data-bs-toggle")
# Elements with no role of their own : a name given to them is never announced
# (ARIA 1.2, the roles that prohibit naming : generic, paragraph, emphasis...).
UNNAMEABLE = {"div", "span", "p", "i", "b", "em", "strong", "small", "code", "u", "s", "mark"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children, self.text = [], []

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def snippet(self):
        attrs = " ".join(f'{key}="{value}"' if value is not None else key for key, value in self.attrs.items())
        return f"<{self.tag} {attrs}>"[:160]


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.current.children.append(Node(tag, dict(attrs), self.current))

    def handle_endtag(self, tag):
        node = self.current
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.current = node.parent

    def handle_data(self, data):
        if self.current.tag not in ("script", "style", "template"):
            self.current.text.append(data)


def parse(html):
    builder = _Builder()
    builder.feed(html)
    builder.close()
    return builder.root


def _hidden_from_readers(node):
    return node.attrs.get("aria-hidden") == "true"


def accessible_text(node):
    """The text a screen reader reads inside ``node`` : its own text, the
    ``alt`` of its images and the ``aria-label`` of its parts, with everything
    under ``aria-hidden="true"`` left out."""
    if _hidden_from_readers(node):
        return ""
    parts = list(node.text)
    for child in node.children:
        if _hidden_from_readers(child):
            continue
        if child.tag == "img":
            parts.append(child.attrs.get("alt") or "")
        elif child.attrs.get("aria-label"):
            parts.append(child.attrs["aria-label"])
        else:
            parts.append(accessible_text(child))
    return " ".join(part.strip() for part in parts if part and part.strip())


def _named(node):
    attrs = node.attrs
    return bool(
        (attrs.get("aria-label") or "").strip()
        or attrs.get("aria-labelledby")
        or (attrs.get("title") or "").strip()
        or accessible_text(node)
    )


def problems(html):
    """The accessibility defects of a rendered page, one line each."""
    root = parse(html)
    nodes = list(root.walk())
    labelled_ids = {node.attrs["for"] for node in nodes if node.tag == "label" and node.attrs.get("for")}
    found = []
    for node in nodes:
        attrs = node.attrs
        if any(_hidden_from_readers(ancestor) for ancestor in node.ancestors()) or _hidden_from_readers(node):
            continue
        if any(ancestor.tag in ("script", "style", "template") for ancestor in node.ancestors()):
            continue
        if node.tag == "img" and "alt" not in attrs:
            found.append(f"image without alt : {node.snippet()}")
        elif node.tag == "button" or (node.tag == "a" and "href" in attrs) or attrs.get("role") == "button":
            if not _named(node):
                found.append(f"control without a name : {node.snippet()}")
        elif node.tag == "a" and any(key in attrs for key in ACTING_ATTRIBUTES):
            if attrs.get("role") != "button" or "tabindex" not in attrs:
                found.append(f"link without href, out of the keyboard's reach : {node.snippet()}")
        elif node.tag in ("select", "textarea") or (
            node.tag == "input" and (attrs.get("type") or "text").lower() not in SELF_NAMED_INPUTS
        ):
            labelled = (
                (attrs.get("aria-label") or "").strip()
                or attrs.get("aria-labelledby")
                or (attrs.get("title") or "").strip()
                or attrs.get("id") in labelled_ids
                or any(ancestor.tag == "label" for ancestor in node.ancestors())
            )
            if not labelled:
                found.append(f"form control without a label : {node.snippet()}")
        for name in attrs:
            # onclick, onchange... : script in the markup. The Content Security
            # Policy refuses it, so the control would do nothing in a browser.
            if name.startswith("on") and name[2:].isalpha() and node.tag not in ("script", "style"):
                found.append(f"inline event handler ({name}) : {node.snippet()}")
        if node.tag in UNNAMEABLE and (attrs.get("aria-label") or "").strip() and not attrs.get("role"):
            found.append(f"aria-label on an element with no role : {node.snippet()}")
        tabindex = attrs.get("tabindex")
        if tabindex and tabindex.lstrip("-").isdigit() and int(tabindex) > 0:
            found.append(f"positive tabindex : {node.snippet()}")
    return found

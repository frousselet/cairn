# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The page header pinned at the top of the window, on every screen width.

The header sticks once the page scrolls (``.page-header.is-compact``). On a
phone its title and its actions wrap onto several lines : it was three times
as tall as on a laptop, a card reached through an anchor (the *Jump to a
section* menu, a term of the glossary) stopped under it, its lower
lines let the scrolling content show through, and the menu button covered the
start of its title. What a browser lays out cannot be asserted here : these
tests hold the rules that fixed it, measured in a browser at the time
(iPhone 13 : a card landed 87 px under a 167 px header; it now lands clear of
a 121 px one).
"""

import re

from django.conf import settings

CSS = settings.BASE_DIR / "static" / "css" / "cairn"


def _media(css, query):
    """The rules of every ``@media (query)`` block of ``css``, end to end."""
    rules = []
    for match in re.finditer(re.escape(f"@media ({query}) {{"), css):
        depth, i = 0, match.end() - 1
        for j in range(i, len(css)):
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            if depth == 0:
                rules.append(css[i + 1:j])
                break
    assert rules, query
    return "\n".join(rules)


class TestAnAnchoredCardClearsTheHeader:
    def test_the_header_height_is_measured(self):
        """A fixed offset (3.75rem) is right for a laptop's one-line bar only."""
        base = (settings.BASE_DIR / "templates" / "base.html").read_text()
        script = base.split("function initPageHeader()", 1)[1].split("initPageHeader();", 1)[0]
        assert "new ResizeObserver(" in script
        assert "setProperty('--page-header-height', header.offsetHeight + 'px')" in script
        # A boosted navigation renders a new bar : the old one is let go.
        assert "window._pageHeaderSize.disconnect()" in script

    def test_what_an_anchor_reaches_stops_below_the_measured_height(self):
        framework = (CSS / "10-framework.css").read_text()
        rule = "scroll-margin-top: calc(var(--page-header-height, var(--page-header-offset)) + 1.25rem);"
        assert f".detail-main .section-card {{ {rule} }}" in framework
        entry = framework.split(".def-list__entry {", 1)[1].split("}", 1)[0]
        assert rule in entry
        assert not re.search(r"scroll-margin-top:\s*[\d.]+rem", framework)


class TestThePinnedHeaderOnASmallScreen:
    def test_a_phone_lays_the_header_out_in_one_column(self):
        """Wrapped, each row took the width of its content : a title held on
        one line widened the bar past the screen."""
        phone = _media((CSS / "09-components.css").read_text(), "max-width: 575.98px")
        assert ".page-header { flex-direction: column; flex-wrap: nowrap; align-items: stretch; }" in phone
        assert ".page-header.is-compact { padding-top: .25rem; align-items: stretch; }" in phone
        assert ".page-header.is-compact .page-header__modified { display: none; }" in phone

    def test_below_992px_the_pinned_title_holds_one_line_clear_of_the_menu_button(self):
        pinned = _media((CSS / "09-components.css").read_text(), "max-width: 991.98px")
        assert ".page-header.is-compact .page-header__main { padding-left: 2.25rem; }" in pinned
        title = pinned.split(".page-header__title:not(:has(.page-header__logo)) {", 1)[1].split("}", 1)[0]
        for declaration in ("white-space: nowrap;", "overflow: hidden;", "text-overflow: ellipsis;"):
            assert declaration in title

    def test_below_992px_the_tint_covers_the_whole_pinned_header(self):
        """The fade drawn for a one-line bar left the lower lines of a wrapped
        bar over the content, which showed through them."""
        pinned = _media((CSS / "09-components.css").read_text(), "max-width: 991.98px")
        tint = pinned.split(".page-header.is-compact::before {", 1)[1].split("}", 1)[0]
        assert "mask-image: linear-gradient(to bottom, #000 calc(100% - 1.25rem), transparent);" in tint

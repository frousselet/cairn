#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Render ``docs/`` into a GitHub wiki tree, and validate its links.

GitHub wikis are a git repository with one hard constraint : **directories have
no effect on a page's URL**. A page is addressed by its filename alone, so two
files called ``README.md`` in different folders would be the same wiki page.
This script therefore flattens the tree into globally unique page names and
rewrites every internal link to match.

    python scripts/build_wiki.py --check           validate links, write nothing
    python scripts/build_wiki.py --out build/wiki  render the wiki tree

``--check`` is what CI runs on every push : a link to a file that does not
exist, or to a directory (which the wiki cannot address), fails the build long
before release day.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

REPO_URL = "https://github.com/frousselet/cairn"
RAW_WIKI_URL = "https://raw.githubusercontent.com/wiki/frousselet/cairn"

# Not documentation : historical test-campaign artefacts, kept in the repository
# but never published.
EXCLUDED = {"qa"}

# Segments whose natural casing is not simply capitalised.
ACRONYMS = {
    "sdk": "SDK", "api": "API", "mcp": "MCP", "ui": "UI", "rest": "REST",
    "qa": "QA", "swot": "SWOT", "ebios": "EBIOS", "rm": "RM", "iso27005": "ISO27005",
    "m0": "M0", "m1": "M1", "m2": "M2", "m3": "M3", "m4": "M4", "m5": "M5", "m6": "M6",
}

# Sections listed in the sidebar by their module index only. The specifications
# run to about a hundred entity pages; listing every one of them would bury the
# rest of the navigation, and each module page already links its own entities.
INDEX_ONLY = {"specs"}

# Sidebar order and headings. Anything not listed falls to the end.
SECTIONS = [
    ("user-guide", "User guide"),
    ("technical", "Technical"),
    ("sdk", "SDK"),
    ("reference", "Reference"),
    ("specs", "Specifications"),
    ("brand", "Brand"),
]

LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# Fenced blocks and inline code spans are masked before links are matched : a
# documented example such as `[Objective](objective.md)` is prose about a link,
# not a link, and must be neither validated nor rewritten.
CODE = re.compile(r"(```.*?```|~~~.*?~~~|`[^`\n]*`)", re.DOTALL)


def page_name(relative: Path) -> str:
    """The wiki page name for a documentation file, e.g. ``Technical-Security``.

    ``docs/README.md`` is the wiki ``Home``; a section's ``README.md`` takes the
    section's own name.
    """
    parts = list(relative.parts)
    if parts[-1].lower() in ("readme.md", "index.md"):
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][: -len(".md")]
    if not parts:
        return "Home"
    words = []
    for part in parts:
        for word in part.split("-"):
            words.append(ACRONYMS.get(word.lower(), word.capitalize()))
    return "-".join(words)


def discover() -> dict[Path, str]:
    """Map every published documentation file to its wiki page name."""
    pages: dict[Path, str] = {}
    taken: dict[str, Path] = {}
    for path in sorted(DOCS.rglob("*.md")):
        relative = path.relative_to(DOCS)
        if relative.parts[0] in EXCLUDED:
            continue
        name = page_name(relative)
        if name in taken:
            raise SystemExit(
                f"Page name collision: {relative} and {taken[name]} both render "
                f"as '{name}'. Rename one of them."
            )
        taken[name] = relative
        pages[path] = name
    return pages


def rewrite(source: Path, text: str, pages: dict[Path, str], problems: list[str]) -> str:
    """Rewrite every relative link in one page for the flattened wiki."""

    def replace(match: re.Match) -> str:
        bang, label, target = match.group(1), match.group(2), match.group(3)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)

        path_part, _, anchor = target.partition("#")
        if not path_part:
            return match.group(0)

        resolved = (source.parent / path_part).resolve()

        if not resolved.exists():
            problems.append(f"{source.relative_to(REPO)} -> {target} (does not exist)")
            return match.group(0)

        if resolved.is_dir():
            problems.append(
                f"{source.relative_to(REPO)} -> {target} (points at a directory; "
                "the wiki has no directories to link to, so link to a file)"
            )
            return match.group(0)

        # An image, or any asset, is served from the wiki's own repository by an
        # absolute raw URL : a relative one would resolve differently depending
        # on the page it is read from.
        if bang or resolved.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
            try:
                relative = resolved.relative_to(DOCS)
            except ValueError:
                return f"{bang}[{label}]({REPO_URL}/blob/main/{resolved.relative_to(REPO)})"
            return f"{bang}[{label}]({RAW_WIKI_URL}/{relative.as_posix()})"

        # A documentation page becomes its flattened wiki name.
        if resolved in pages:
            suffix = f"#{anchor}" if anchor else ""
            return f"[{label}]({pages[resolved]}{suffix})"

        # Anything else lives in the repository, not in the wiki.
        try:
            in_repo = resolved.relative_to(REPO)
        except ValueError:
            problems.append(f"{source.relative_to(REPO)} -> {target} (outside the repository)")
            return match.group(0)
        return f"[{label}]({REPO_URL}/blob/main/{in_repo.as_posix()})"

    return "".join(
        segment if index % 2 else LINK.sub(replace, segment)
        for index, segment in enumerate(CODE.split(text))
    )


def sidebar(pages: dict[Path, str]) -> str:
    """The wiki navigation, grouped by section and ordered deliberately."""
    grouped: dict[str, list[tuple[str, str]]] = {}
    for path, name in pages.items():
        relative = path.relative_to(DOCS)
        section = relative.parts[0] if len(relative.parts) > 1 else ""
        if not section:
            continue
        if section in INDEX_ONLY and path.name != "README.md":
            continue
        title = heading(path) or name
        grouped.setdefault(section, []).append((title, name))

    lines = ["## [Cairn](Home)", ""]
    for key, label in SECTIONS:
        entries = grouped.pop(key, [])
        if not entries:
            continue
        root = pages.get(DOCS / key / "README.md")
        lines.append(f"### {f'[{label}]({root})' if root else label}")
        for title, name in sorted(entries, key=lambda e: e[1]):
            if name == root:
                continue
            lines.append(f"- [{title}]({name})")
        lines.append("")
    for key, entries in sorted(grouped.items()):
        lines.append(f"### {key}")
        lines += [f"- [{t}]({n})" for t, n in sorted(entries, key=lambda e: e[1])]
        lines.append("")
    return "\n".join(lines) + "\n"


def heading(path: Path) -> str:
    """The page's first H1, used as its human-readable title in the sidebar."""
    for line in path.read_text().splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def footer(version: str) -> str:
    return (
        f"---\n\n"
        f"Built from [`docs/`]({REPO_URL}/tree/main/docs) at **{version}**. "
        f"Edits made here are overwritten by the next release : "
        f"[open a pull request]({REPO_URL}/pulls) against the source instead.\n"
    )


def build(out: Path, pages: dict[Path, str], version: str, problems: list[str]) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for path, name in pages.items():
        text = rewrite(path, path.read_text(), pages, problems)
        (out / f"{name}.md").write_text(text)

    # Assets keep their path under the wiki root, matching the raw URLs above.
    for assets in ("screenshots", "brand"):
        source = DOCS / assets
        if not source.is_dir():
            continue
        for asset in source.rglob("*"):
            if asset.is_file() and asset.suffix.lower() != ".md":
                target = out / asset.relative_to(DOCS)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset, target)

    (out / "_Sidebar.md").write_text(sidebar(pages))
    (out / "_Footer.md").write_text(footer(version))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="Directory to render the wiki into.")
    parser.add_argument("--check", action="store_true",
                        help="Validate links and page names; write nothing.")
    parser.add_argument("--version", default="dev",
                        help="Version stamped into the wiki footer.")
    args = parser.parse_args()

    pages = discover()
    problems: list[str] = []

    if args.check or not args.out:
        for path in pages:
            rewrite(path, path.read_text(), pages, problems)
    else:
        build(args.out, pages, args.version, problems)

    if problems:
        print(f"{len(problems)} broken documentation link(s):", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    if args.out and not args.check:
        print(f"Rendered {len(pages)} pages into {args.out}")
    else:
        print(f"{len(pages)} pages, every link resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

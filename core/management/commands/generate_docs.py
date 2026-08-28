# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Generate the code-derived reference pages under ``docs/reference/generated/``.

Every page in that directory is rendered from a registry that already exists in
the code : the permission registry, the lifecycle registry, the dashboard widget
registry, the MCP tool registry, the URL resolver, the Django model registry,
``.env.example`` and the management-command registry. Nothing there is written
by hand.

``python manage.py generate_docs`` rewrites the pages; ``--check`` writes
nothing and exits non-zero as soon as one page is stale. CI runs the second
form, which is what keeps the reference documentation in step with the code : a
new permission, lifecycle step, widget, MCP tool or endpoint fails the build
until the docs are regenerated.
"""

from __future__ import annotations

import ast
import difflib
import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import get_commands, load_command_class
from django.core.management.base import BaseCommand, CommandError
from django.urls import URLPattern, URLResolver, get_resolver

# Apps whose contents are part of Cairn (as opposed to Django's own or a
# third-party dependency). Used to keep the generated inventories on-topic.
PROJECT_APPS = (
    "accounts", "assets", "assistant", "compliance", "context", "core",
    "helpers", "incidents", "mcp", "reports", "risks", "trust_center",
)

OUTPUT_SUBDIR = Path("docs") / "reference" / "generated"


def banner(source: str) -> str:
    """The do-not-edit header carried by every generated page."""
    return (
        "<!-- GENERATED FILE - DO NOT EDIT BY HAND.\n"
        f"     Rendered from {source} by `python manage.py generate_docs`.\n"
        "     Change the code, then re-run the command. CI fails on a stale page. -->\n"
    )


def cell(value) -> str:
    """Render a value as a single Markdown table cell (never breaks the row)."""
    text = "" if value is None else str(value)
    text = text.replace("|", "\\|").replace("\n", " ").strip()
    return re.sub(r"\s+", " ", text)


def code(value) -> str:
    """A table cell holding an identifier, or an em-free dash when empty."""
    text = cell(value)
    return f"`{text}`" if text else "-"


def yesno(flag: bool) -> str:
    return "yes" if flag else "-"


def normalize(text: str) -> str:
    """Tidy a rendered page : a blank line after every heading, no triple blanks.

    Applied centrally so each generator can concatenate fragments without
    worrying about the seams.
    """
    lines = text.splitlines()
    out: list[str] = []
    for index, line in enumerate(lines):
        out.append(line)
        if line.startswith("#") and index + 1 < len(lines) and lines[index + 1].strip():
            out.append("")
    text = "\n".join(out)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.rstrip("\n") + "\n"


def table(headers, rows) -> str:
    """Render a Markdown table; returns an empty string when there is no row."""
    rows = list(rows)
    if not rows:
        return ""
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out) + "\n"


# ── Permissions ─────────────────────────────────────────────

def render_permissions() -> dict:
    from accounts.constants import (
        ACTION_LABELS, MODULE_LABELS, PERMISSION_REGISTRY, SYSTEM_GROUPS,
        get_all_permissions,
    )

    codenames = [c for c, *_ in get_all_permissions()]
    out = [banner("`accounts/constants.py` (`PERMISSION_REGISTRY`, `SYSTEM_GROUPS`)"),
           "\n# Permissions\n",
           "Cairn does not use Django's per-model `add`/`change`/`delete` permissions. "
           "It declares its own flat codenames shaped `module.feature.action`, and every "
           "web view, REST endpoint and MCP tool is gated on one of them.\n",
           f"\nThere are **{len(codenames)} permissions** across "
           f"**{len(PERMISSION_REGISTRY)} modules**. They are created by a data "
           "migration from the registry below, so adding an entry there and migrating "
           "is the whole of adding a permission.\n",
           "\n## Actions\n",
           table(["Action", "Label", "Meaning"], [
               ["`create`", cell(ACTION_LABELS.get("create")), "Create a new record"],
               ["`read`", cell(ACTION_LABELS.get("read")), "List and view records"],
               ["`update`", cell(ACTION_LABELS.get("update")), "Edit an existing record"],
               ["`delete`", cell(ACTION_LABELS.get("delete")), "Delete a record (only from a deletable lifecycle step)"],
               ["`access`", cell(ACTION_LABELS.get("access")), "Reach a surface that is not a record (a page, a console)"],
               ["`approve`", cell(ACTION_LABELS.get("approve")), "Perform a lifecycle transition that carries `permission_action=\"approve\"`"],
           ])]

    for module, features in PERMISSION_REGISTRY.items():
        label = cell(MODULE_LABELS.get(module, module))
        out.append(f"\n## {label} (`{module}`)\n")
        out.append(table(
            ["Feature", "Label", "Codenames"],
            [[f"`{feature}`", cell(info.get("label", feature)),
              ", ".join(f"`{module}.{feature}.{a}`" for a in info["actions"])]
             for feature, info in features.items()],
        ))

    out.append("\n## System groups\n")
    out.append("Six groups ship with the platform and are kept in sync by the same "
               "data migration. A group's permission set is a filter over the codenames "
               "above, so a newly declared permission lands in the right groups "
               "automatically.\n\n")
    out.append(table(
        ["Group", "Permissions", "Description"],
        [[cell(name), str(sum(1 for c in codenames if info["filter"](c))),
          cell(info.get("description", ""))]
         for name, info in SYSTEM_GROUPS.items()],
    ))
    return {"permissions.md": "".join(out)}


# ── Lifecycles ──────────────────────────────────────────────

def _models_by_lifecycle() -> dict:
    from core.lifecycle import DEFAULT_LIFECYCLE_NAME
    mapping: dict[str, list[str]] = {}
    for model in apps.get_models():
        if model._meta.app_label not in PROJECT_APPS:
            continue
        if not hasattr(model, "workflow_state"):
            continue
        if model.__name__.startswith("Historical"):
            continue
        name = getattr(model, "LIFECYCLE_NAME", None) or DEFAULT_LIFECYCLE_NAME
        mapping.setdefault(name, []).append(
            f"{model._meta.app_label}.{model.__name__}")
    for names in mapping.values():
        names.sort()
    return mapping


def render_lifecycles() -> dict:
    from core.lifecycle import ANY, LIFECYCLE_REGISTRY

    users = _models_by_lifecycle()
    out = [banner("`core/lifecycle.py` and each app's `lifecycles.py`"),
           "\n# Lifecycles\n",
           "Every domain record runs a registered lifecycle. A lifecycle is an ordered "
           "set of **steps** plus the **transitions** between them; the step carries the "
           "governance metadata the rest of the platform reads instead of hardcoding a "
           "status value.\n",
           "\n| Flag | Read by |\n| --- | --- |\n"
           "| `counts_in_reports` | `reportable()` : dashboards, KPIs, reports |\n"
           "| `linkable` | `linkable()` : the object pickers of other forms |\n"
           "| `deletable` | `deletable_states()` : whether deletion is offered at all |\n",
           "\nThe engine is specified in [governance/lifecycle.md](../../specs/governance/lifecycle.md); "
           "the governance contract is in [governance/workflow.md](../../specs/governance/workflow.md).\n",
           f"\n**{len(LIFECYCLE_REGISTRY)} lifecycles** are declared in code. An "
           "administrator can override any of them from `/config/lifecycles/`; this page "
           "documents the shipped defaults.\n",
           "\n## Summary\n",
           table(["Lifecycle", "Steps", "Transitions", "Layout", "Models"],
                 [[f"[`{name}`](#{name.replace('_', '-')})", str(len(lc.steps)),
                   str(len(lc.transitions)), cell(lc.layout),
                   ", ".join(f"`{m}`" for m in users.get(name, [])) or "-"]
                  for name, lc in sorted(LIFECYCLE_REGISTRY.items())])]

    for name, lc in sorted(LIFECYCLE_REGISTRY.items()):
        out.append(f"\n## {name}\n")
        bound = users.get(name, [])
        if bound:
            out.append("\nRun by " + ", ".join(f"`{m}`" for m in bound) + ".\n")
        out.append("\n### Steps\n")
        out.append(table(
            ["Code", "Label", "Kind", "In reports", "Linkable", "Deletable"],
            [[f"`{s.code}`", cell(s.label), cell(s.kind.value),
              yesno(s.counts_in_reports), yesno(s.linkable), yesno(s.deletable)]
             for s in lc.steps]))
        out.append("\n### Transitions\n")
        out.append(table(
            ["From", "To", "Label", "Comment required", "Permission", "Restricted to roles"],
            [["any" if t.source == ANY else f"`{t.source}`", f"`{t.target}`",
              cell(t.label), yesno(t.requires_comment),
              code(t.permission_action),
              ", ".join(f"`{r}`" for r in t.allowed_roles) or "-"]
             for t in lc.transitions]))
    return {"lifecycles.md": "".join(out)}


# ── Dashboard widgets ───────────────────────────────────────

def render_widgets() -> dict:
    from core.dashboard import (
        DASHBOARD_WIDGETS, MAX_HEIGHT, MAX_WIDTH, PROGRESS_ROW_COUNTS, ZONES,
    )

    out = [banner("`core/dashboard.py` (`DASHBOARD_WIDGETS`)"),
           "\n# Dashboard widgets\n",
           "The home dashboard is a grid of widgets, each declared once in "
           "`core/dashboard.py`. A user's personal arrangement lives in "
           "`User.dashboard_layout` and is merged with this registry at render time, so "
           "a newly shipped widget appears without a data migration.\n",
           f"\nSizes are `WxH` tokens : width in quarter-columns (1..{MAX_WIDTH}) and "
           f"height in row units (1..{MAX_HEIGHT}, plus the half-step `0.5`). Zones are "
           + ", ".join(f"`{z}`" for z in ZONES) + ".\n",
           "\nTo add one, follow [sdk/dashboard-widget.md](../../sdk/dashboard-widget.md).\n",
           f"\n**{len(DASHBOARD_WIDGETS)} widgets** ship with the platform.\n",
           "\n## Catalogue\n",
           table(["Id", "Title", "Category", "Sizes", "Default", "Zone", "Reusable", "Config", "Description"],
                 [[f"`{w.id}`", cell(w.title), cell(w.category),
                   " ".join(f"`{s}`" for s in w.sizes), f"`{w.default_size}`",
                   f"`{w.default_zone}`", yesno(w.multiple), code(w.config),
                   cell(w.description)]
                  for w in DASHBOARD_WIDGETS]),
           "\n## Templates\n",
           table(["Id", "Template", "Icon", "Default order", "On by default", "Bare"],
                 [[f"`{w.id}`", f"`{w.template}`", f"`bi-{w.icon}`",
                   str(w.default_order), yesno(w.default_visible), yesno(w.bare)]
                  for w in DASHBOARD_WIDGETS]),
           "\n## Rows shown by a progress-bar widget\n",
           "A list widget fits its row count to the tile height, so a taller tile shows "
           "more rows rather than scrolling.\n\n",
           table(["Tile height", "Rows"],
                 [[f"`{h}`", str(n)] for h, n in sorted(PROGRESS_ROW_COUNTS.items())])]
    return {"dashboard-widgets.md": "".join(out)}


# ── MCP tools ───────────────────────────────────────────────

def _tool_permission(handler) -> str:
    return getattr(handler, "required_perm", "") or ""


MCP_MODULE_TITLES = {
    "assets": "Assets",
    "compliance": "Compliance",
    "context": "Governance and context",
    "general": "General",
    "incidents": "Incidents",
    "reports": "Reports and management review",
    "risks": "Risks",
    "system": "System and administration",
    "trust_center": "Trust Center",
}


def _mcp_page_name(module: str) -> str:
    return f"mcp-tools-{module.replace('_', '-')}.md"


def render_mcp_tools() -> dict:
    """The MCP reference : one index page plus one detail page per module.

    Cairn registers several hundred tools (every entity gets the same CRUD,
    lifecycle and history surface), so a single page carrying each tool's
    parameter table would be unreadable. The index stays the one place that
    lists everything; the parameter tables live next to their module.
    """
    from mcp.server import McpServer
    from mcp.tools import register_all_tools

    server = McpServer()
    register_all_tools(server)
    tools = list(server.iter_tools())

    groups: dict[str, list] = {}
    for tool in tools:
        perm = _tool_permission(tool["handler"])
        module = perm.split(".")[0] if perm else "general"
        groups.setdefault(module, []).append(tool)
    for group in groups.values():
        group.sort(key=lambda t: t["name"])

    pages = {}
    index = [
        banner("the MCP tool registry (`mcp/tools.py`)"),
        "\n# MCP tools\n",
        "Cairn's MCP server exposes the whole platform to AI assistants and scripts "
        "over JSON-RPC 2.0. Every tool runs as the calling user : the permission "
        "column below is enforced by the `@require_perm` decorator, and scope-based "
        "tenancy filters the rows on top of it.\n",
        "\nTransport, authentication and client setup are in "
        "[../mcp-server.md](../mcp-server.md).\n",
        f"\n**{len(tools)} tools** are registered, across "
        f"**{len(groups)} modules**. Most entities carry the same surface : "
        "`list_*`, `get_*`, `create_*`, `batch_create_*`, `update_*`, `delete_*`, "
        "plus `*_transition`, `*_allowed_transitions` and `*_history` when the "
        "entity runs a lifecycle.\n",
        "\n## Modules\n",
        table(["Module", "Tools", "Parameter reference"],
              [[cell(MCP_MODULE_TITLES.get(m, m)), str(len(g)),
                f"[{_mcp_page_name(m)}]({_mcp_page_name(m)})"]
               for m, g in sorted(groups.items())]),
    ]

    for module, group in sorted(groups.items()):
        title = MCP_MODULE_TITLES.get(module, module)
        index.append(f"\n## {title}\n")
        index.append(table(
            ["Tool", "Permission", "Description"],
            [[f"`{t['name']}`", code(_tool_permission(t["handler"])),
              cell(t["description"])] for t in group]))

        detail = [
            banner("the MCP tool registry (`mcp/tools.py`)"),
            f"\n# MCP tool parameters : {title}\n",
            f"Input schemas for the {len(group)} `{module}` tools. The index of every "
            "module is in [mcp-tools.md](mcp-tools.md); a live server answers the same "
            "thing authoritatively through the `tools/list` JSON-RPC method.\n",
        ]
        for tool in group:
            schema = tool.get("inputSchema") or {}
            props = schema.get("properties") or {}
            required = set(schema.get("required") or [])
            detail.append(f"\n## `{tool['name']}`\n")
            detail.append("\n" + cell(tool["description"]) + "\n")
            perm = _tool_permission(tool["handler"])
            if perm:
                detail.append(f"\nRequires `{perm}`.\n")
            if not props:
                detail.append("\nNo parameters.\n")
                continue
            detail.append("\n" + table(
                ["Parameter", "Type", "Required", "Description"],
                [[f"`{key}`", code(spec.get("type", "")), yesno(key in required),
                  cell(spec.get("description", ""))]
                 for key, spec in props.items()]))
        pages[_mcp_page_name(module)] = "".join(detail)

    pages["mcp-tools.md"] = "".join(index)
    return pages


# ── REST endpoints ──────────────────────────────────────────

def _walk_urls(resolver, prefix=""):
    for entry in resolver.url_patterns:
        pattern = prefix + str(entry.pattern)
        if isinstance(entry, URLResolver):
            yield from _walk_urls(entry, pattern)
        elif isinstance(entry, URLPattern):
            yield pattern, entry


def _methods(entry) -> str:
    """The HTTP verbs a route answers, read off the view it points at."""
    callback = entry.callback
    actions = getattr(callback, "actions", None)
    if actions:
        return ", ".join(sorted(m.upper() for m in actions))
    view = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
    if view is None:
        return "-"
    verbs = [m for m in ("get", "post", "put", "patch", "delete", "head", "options")
             if hasattr(view, m)]
    return ", ".join(v.upper() for v in verbs) or "-"


def _view_name(entry) -> str:
    callback = entry.callback
    view = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
    target = view or callback
    return f"{target.__module__}.{target.__qualname__}"


def render_endpoints() -> dict:
    """The `/api/v1/` route table, read off Django's URL resolver.

    DRF publishes a `.<format>` twin of every route (the format-suffix
    convention); they answer exactly like their canonical sibling, so listing
    both would double the table without saying anything new.
    """
    routes = []
    for pattern, entry in _walk_urls(get_resolver()):
        if not pattern.startswith("api/v1/"):
            continue
        if "format" in pattern and ("drf_format_suffix" in pattern or "\\." in pattern):
            continue
        path = "/" + pattern.replace("$", "").replace("^", "")
        path = re.sub(r"\(\?P<(\w+)>[^)]*\)", r"<\1>", path)
        module = path.split("/")[3] if len(path.split("/")) > 4 else "root"
        routes.append((module, path, _methods(entry), _view_name(entry), entry.name or ""))
    routes.sort(key=lambda r: (r[0], r[1]))

    groups: dict[str, list] = {}
    for module, *rest in routes:
        groups.setdefault(module, []).append(rest)

    out = [banner("the URL resolver (`core/urls.py` and each app's `api/urls.py`)"),
           "\n# REST endpoints\n",
           "The complete route table under `/api/v1/`. Authentication, pagination, "
           "filtering and the error contract are documented in "
           "[../rest-api.md](../rest-api.md); the field-level contract of each "
           "resource is in its [specification](../../specs/README.md).\n",
           f"\n**{len(routes)} routes** are published across "
           f"**{len(groups)} groups**. Every route also answers at a `.<format>` "
           "suffix (`.json`, `.api`), which is omitted here.\n",
           "\n## Groups\n",
           table(["Group", "Routes"],
                 [[f"[`{m}`](#{m})", str(len(g))] for m, g in sorted(groups.items())])]

    for module, rows in sorted(groups.items()):
        out.append(f"\n## {module}\n")
        out.append(table(["Path", "Methods", "View", "URL name"],
                         [[f"`{p}`", cell(m), f"`{v}`", code(n)] for p, m, v, n in rows]))
    return {"rest-endpoints.md": "".join(out)}


# ── Models ──────────────────────────────────────────────────

def render_models() -> dict:
    from core.lifecycle import DEFAULT_LIFECYCLE_NAME

    rows = []
    for model in apps.get_models():
        meta = model._meta
        if meta.app_label not in PROJECT_APPS or model.__name__.startswith("Historical"):
            continue
        has_lifecycle = hasattr(model, "workflow_state")
        lifecycle = (getattr(model, "LIFECYCLE_NAME", None) or DEFAULT_LIFECYCLE_NAME) \
            if has_lifecycle else ""
        rows.append([
            cell(meta.app_label),
            f"`{model.__name__}`",
            f"`{meta.db_table}`",
            code(getattr(model, "REFERENCE_PREFIX", "")),
            code(lifecycle),
            yesno(any(f.name == "scopes" and f.many_to_many for f in meta.get_fields())),
            yesno(hasattr(model, "history")),
            str(len([f for f in meta.get_fields() if getattr(f, "concrete", False)])),
        ])
    rows.sort(key=lambda r: (r[0], r[1]))

    return {"models.md": "".join([
        banner("the Django model registry"),
        "\n# Models\n",
        "Every persisted model in the project, with the platform-wide behaviours it "
        "inherits. `BaseModel` gives a UUID primary key, timestamps, `created_by`, a "
        "lifecycle and versioning; `ScopedModel` adds the `scopes` many-to-many that "
        "drives tenancy; `ReferenceGeneratorMixin` issues the sequential business "
        "reference from a four-character prefix.\n",
        "\nThe field-by-field contract of each entity lives in its "
        "[specification](../../specs/README.md); this page is the inventory.\n",
        f"\n**{len(rows)} models** are registered.\n",
        "\n## Inventory\n",
        table(["App", "Model", "Table", "Prefix", "Lifecycle", "Scoped", "History", "Fields"], rows),
    ])}


# ── Settings ────────────────────────────────────────────────

# Modules that read the environment. ``.env.example`` documents the common
# subset; the settings modules are the exhaustive truth, so the page is built
# from the code and annotated with the template's comments.
ENV_SOURCES = (
    "core/settings.py",
    "assets/services/spof_scheduler.py",
)

def _env_reads(source: Path):
    """Yield ``(name, default)`` for every environment read in a Python module.

    Parsed rather than pattern-matched : several of these calls span lines
    (``SECRET_KEY``, ``EMAIL_BACKEND``), and a regex either misses those or
    swallows the commas inside a default like ``"localhost,127.0.0.1"``.
    """
    tree = ast.parse(source.read_text())
    for node in ast.walk(tree):
        name = default = None
        # os.environ.get("NAME") / os.environ.get("NAME", default)
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and ast.unparse(node.func.value) == "os.environ"
                and node.args
                and isinstance(node.args[0], ast.Constant)):
            name = node.args[0].value
            if len(node.args) > 1:
                fallback = node.args[1]
                # A literal default is shown as its value; a computed one (the
                # email backend switches on DEBUG) as the expression itself.
                default = (str(fallback.value) if isinstance(fallback, ast.Constant)
                           else ast.unparse(fallback))
        # os.environ["NAME"]
        elif (isinstance(node, ast.Subscript)
                and ast.unparse(node.value) == "os.environ"
                and isinstance(node.slice, ast.Constant)):
            name = node.slice.value
        if isinstance(name, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            yield name, (default or "")


def _env_template_notes() -> dict:
    """Map each variable documented in ``.env.example`` to its comment block."""
    notes, block = {}, []
    for raw in (Path(settings.BASE_DIR) / ".env.example").read_text().splitlines():
        line = raw.strip()
        if not line:
            block = []
            continue
        body = line.lstrip("#").strip()
        name = body.split("=", 1)[0].strip() if "=" in body else ""
        if name and re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            notes.setdefault(name, " ".join(block))
            block = []
        elif line.startswith("#"):
            block.append(body)
    return notes


def render_settings() -> dict:
    """Every environment variable the code actually reads.

    Scanning the settings modules rather than ``.env.example`` is deliberate :
    the template documents the common subset, so a variable added to the code
    and forgotten in the template would otherwise be invisible here. The
    template still supplies the prose, and the page marks what it omits.
    """
    notes = _env_template_notes()
    found: dict[str, str] = {}
    for relative in ENV_SOURCES:
        for name, default in _env_reads(Path(settings.BASE_DIR) / relative):
            # Runtime plumbing, not deployment configuration.
            if name in ("RUN_MAIN", "DJANGO_SETTINGS_MODULE"):
                continue
            found.setdefault(name, default)

    rows = []
    for name in sorted(found):
        default = found[name]
        rows.append([
            f"`{name}`",
            code(default) if default else "-",
            "yes" if name in notes else "-",
            cell(notes.get(name, "")),
        ])

    undocumented = [n for n in sorted(found) if n not in notes]
    template_only = [n for n in sorted(notes) if n not in found]

    out = [
        banner("the settings modules (" + ", ".join(f"`{s}`" for s in ENV_SOURCES) + ") and `.env.example`"),
        "\n# Environment variables\n",
        "Cairn is configured entirely through the environment. This page lists every "
        "variable the code reads, taken from the settings modules themselves rather "
        "than from the template, so a variable that exists in the code but not in "
        "`.env.example` still shows up here.\n",
        "\nThe **In template** column says whether `.env.example` mentions it. Copy "
        "that file to `.env` to get started; anything absent from it falls back to "
        "the default below. Setting them up is covered in "
        "[../../technical/configuration.md](../../technical/configuration.md).\n",
        f"\n**{len(found)} variables** are read by the code.\n",
        "\n## Variables\n",
        table(["Variable", "Default", "In template", "Notes"], rows),
    ]
    if undocumented:
        out.append("\n## Read by the code, absent from `.env.example`\n")
        out.append("These work but are undocumented in the template; they are listed "
                   "here so no deployment knob stays invisible.\n\n")
        out.append(", ".join(f"`{n}`" for n in undocumented) + "\n")
    if template_only:
        out.append("\n## In `.env.example`, not read by the settings modules\n")
        out.append("Consumed elsewhere than the settings (the container entrypoint, "
                   "`docker-compose.yml`) rather than unused.\n\n")
        out.append(", ".join(f"`{n}`" for n in template_only) + "\n")
    return {"settings.md": "".join(out)}


# ── Management commands ─────────────────────────────────────

def render_commands() -> dict:
    rows = []
    for name, app in sorted(get_commands().items()):
        if app not in PROJECT_APPS:
            continue
        try:
            help_text = (load_command_class(app, name).help or "").strip()
        except Exception:  # a command that cannot be imported is still worth listing
            help_text = ""
        rows.append([f"`{name}`", cell(app), cell(help_text.split("\n")[0])])

    return {"management-commands.md": "".join([
        banner("the Django management-command registry"),
        "\n# Management commands\n",
        "Commands Cairn adds on top of Django's own. Run them with "
        "`python manage.py <command>` (inside the container : "
        "`docker compose exec web python manage.py <command>`).\n",
        "\nThe ones meant to run on a schedule are covered in "
        "[../../technical/operations.md](../../technical/operations.md).\n",
        "\n## Commands\n",
        table(["Command", "App", "Purpose"], rows),
    ])}


# ── Command ─────────────────────────────────────────────────

# Every generator returns ``{filename: markdown}``; one of them (the MCP
# reference) emits several pages, so the mapping is the contract rather than a
# single string.
GENERATORS = (
    render_permissions,
    render_lifecycles,
    render_widgets,
    render_mcp_tools,
    render_endpoints,
    render_models,
    render_settings,
    render_commands,
)


class Command(BaseCommand):
    help = "Generate the code-derived reference pages under docs/reference/generated/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check", action="store_true",
            help="Write nothing; exit non-zero if any generated page is out of date.",
        )

    def handle(self, *args, **options):
        target = Path(settings.BASE_DIR) / OUTPUT_SUBDIR
        target.mkdir(parents=True, exist_ok=True)

        pages = {}
        for generator in GENERATORS:
            for filename, content in generator().items():
                pages[filename] = normalize(content)

        stale = []
        for filename, content in sorted(pages.items()):
            path = target / filename
            current = path.read_text() if path.exists() else None
            if current == content:
                self.stdout.write(f"  ok       {OUTPUT_SUBDIR / filename}")
                continue
            if options["check"]:
                stale.append(filename)
                self.stdout.write(self.style.ERROR(f"  stale    {OUTPUT_SUBDIR / filename}"))
                diff = difflib.unified_diff(
                    (current or "").splitlines(True), content.splitlines(True),
                    fromfile="on disk", tofile="generated", n=1)
                self.stdout.write("".join(list(diff)[:40]))
                continue
            path.write_text(content)
            self.stdout.write(self.style.SUCCESS(f"  written  {OUTPUT_SUBDIR / filename}"))

        # A page left behind by a generator that no longer produces it would go
        # on being published for ever; treat it exactly like a stale one.
        for orphan in sorted(p.name for p in target.glob("*.md") if p.name not in pages):
            if options["check"]:
                stale.append(orphan)
                self.stdout.write(self.style.ERROR(f"  orphan   {OUTPUT_SUBDIR / orphan}"))
            else:
                (target / orphan).unlink()
                self.stdout.write(self.style.WARNING(f"  removed  {OUTPUT_SUBDIR / orphan}"))

        if stale:
            raise CommandError(
                f"{len(stale)} reference page(s) out of date: " + ", ".join(stale)
                + "\nRun `python manage.py generate_docs` and commit the result."
            )

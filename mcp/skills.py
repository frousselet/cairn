# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The skills the MCP server serves (the ``io.modelcontextprotocol/skills`` extension).

A skill is a directory whose ``SKILL.md`` tells an agent how to carry out a
piece of work with the tools (the Agent Skills format : YAML frontmatter with
``name`` and ``description``, then instructions). Each file is a resource,
read with ``resources/read`` under ``skill://cairn/<name>/<file>``.

Two sources make the catalogue :

- **the skills Cairn ships** (``mcp/skill_library/<name>/``), written against
  the tools of this version and updated with it;
- **the skills of the organization** (:class:`mcp.models.McpSkill`), written in
  the interface : the organization's own procedures. Only a validated skill is
  served. One that bears the name of a shipped skill replaces it, under the
  same URI, for the whole instance; archiving it brings the shipped one back.

What a skill says reaches the model's context : it is instructions, so it is
served only once someone holding the approval permission validated it, and the
host verifies each file against the digest of the listing (any change of
content asks the user to approve the new version).

A skill is served to anyone the endpoint admits (``system.mcp.access``) : it
names tools and procedures, never a record, and every tool it names still
answers with the permissions and scopes of the person calling it. The answers
are marked ``cacheScope: private`` all the same, since an organization's
procedures are its own.
"""

import hashlib
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

SKILLS_EXTENSION = "io.modelcontextprotocol/skills"
URI_PREFIX = "skill://cairn/"
LIBRARY = Path(__file__).resolve().parent / "skill_library"
TTL_MS = 300_000

#: The Agent Skills naming rule : 1-64 lowercase letters, digits and single
#: hyphens, neither first nor last.
NAME_PATTERN = re.compile(r"^(?=.{1,64}$)[a-z0-9]+(?:-[a-z0-9]+)*$")
DESCRIPTION_MAX = 1024
# The limits the extension fixes per skill.
MAX_FILES = 512
MAX_BYTES = 16 * 1024 * 1024

MIME_TYPES = {".md": "text/markdown", ".txt": "text/plain", ".json": "application/json",
              ".yaml": "application/yaml", ".yml": "application/yaml", ".csv": "text/csv"}


@dataclass(frozen=True)
class SkillFile:
    path: str  # relative to the skill root, "/"-separated
    content: bytes

    @property
    def digest(self):
        return "sha256:" + hashlib.sha256(self.content).hexdigest()

    @property
    def mime_type(self):
        return MIME_TYPES.get(posixpath.splitext(self.path)[1].lower(), "text/plain")


@dataclass(frozen=True)
class Skill:
    name: str
    frontmatter: dict
    files: tuple  # of SkillFile, SKILL.md first
    origin: str  # "cairn" or "organization"

    @property
    def root(self):
        return f"{URI_PREFIX}{self.name}"

    @property
    def uri(self):
        return f"{self.root}/SKILL.md"

    def file_uri(self, file):
        return f"{self.root}/{file.path}"

    def entry(self):
        """The ``Skill`` entry of ``skills/list`` and ``skills/get``."""
        return {
            "uri": self.uri,
            "frontmatter": dict(self.frontmatter),
            "resources": [
                {"uri": self.file_uri(f), "digest": f.digest, "size": len(f.content)} for f in self.files
            ],
            "_meta": {"io.modelcontextprotocol.skills/origin": self.origin},
        }


# ── The SKILL.md format ───────────────────────────────────


def name_problem(name):
    """Why ``name`` is not a valid skill name, or ``None``."""
    if not isinstance(name, str) or not NAME_PATTERN.match(name):
        return "1 to 64 lowercase letters, digits and hyphens, no hyphen first, last or twice in a row"
    return None


def parse_skill_md(text):
    """``(frontmatter, body)`` of a ``SKILL.md``; ``ValueError`` when malformed."""
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must begin with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("the frontmatter of SKILL.md is not closed")
    frontmatter = yaml.safe_load(text[4:end]) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("the frontmatter of SKILL.md must be a mapping")
    return frontmatter, text[end + 5:]


def render_skill_md(name, description, body):
    """The ``SKILL.md`` of an organization skill : its frontmatter, then its body."""
    head = yaml.safe_dump(
        {"name": name, "description": description},
        allow_unicode=True, sort_keys=False, default_flow_style=False, width=10_000,
    )
    body = (body or "").replace("\r\n", "\n").strip("\n")
    return f"---\n{head}---\n\n{body}\n"


# ── The catalogue ─────────────────────────────────────────


def _shipped():
    skills = {}
    if not LIBRARY.is_dir():
        return skills
    for directory in sorted(p for p in LIBRARY.iterdir() if p.is_dir()):
        skill_md = directory / "SKILL.md"
        if not skill_md.is_file():
            continue
        frontmatter, _body = parse_skill_md(skill_md.read_text(encoding="utf-8"))
        files = [SkillFile("SKILL.md", skill_md.read_bytes())]
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path != skill_md:
                files.append(SkillFile(path.relative_to(directory).as_posix(), path.read_bytes()))
        skills[directory.name] = Skill(directory.name, frontmatter, tuple(files), "cairn")
    return skills


def shipped():
    """The skills Cairn ships, by name."""
    return _shipped()


def shipped_names():
    """The names of the skills Cairn ships."""
    return tuple(_shipped())


def _organization():
    from core.lifecycle import reportable
    from mcp.models import McpSkill

    skills = {}
    for skill in reportable(McpSkill.objects.all()).order_by("name"):
        text = skill.skill_md()
        frontmatter, _body = parse_skill_md(text)
        skills[skill.name] = Skill(
            skill.name, frontmatter, (SkillFile("SKILL.md", text.encode("utf-8")),), "organization",
        )
    return skills


def catalogue():
    """Every skill served, by name : the organization's over the shipped ones."""
    skills = _shipped()
    skills.update(_organization())
    return dict(sorted(skills.items()))


# ── Resolving a URI ───────────────────────────────────────


def _split(uri):
    """``(skill name, file path or "")`` of a ``skill://cairn/...`` URI, or ``None``."""
    if not isinstance(uri, str) or not uri.startswith(URI_PREFIX):
        return None
    rest = uri[len(URI_PREFIX):]
    name, _, path = rest.partition("/")
    if not name or path.startswith("/") or path.endswith("/"):
        return None
    normalised = posixpath.normpath(path) if path else ""
    if normalised in (".",) or normalised.startswith("..") or (path and normalised != path):
        return None
    return name, path


def skill_at(uri):
    """The skill whose ``SKILL.md`` is at ``uri``, or ``None``."""
    parts = _split(uri)
    if parts is None or parts[1] != "SKILL.md":
        return None
    return catalogue().get(parts[0])


def file_at(uri):
    """``(skill, file)`` served at ``uri``, or ``None``."""
    parts = _split(uri)
    if parts is None or not parts[1]:
        return None
    skill = catalogue().get(parts[0])
    if skill is None:
        return None
    for file in skill.files:
        if file.path == parts[1]:
            return skill, file
    return None


def directory_at(uri):
    """``(skill, children)`` of the directory at ``uri`` : ``Resource`` objects, or ``None``."""
    parts = _split(uri)
    if parts is None:
        return None
    name, prefix = parts
    skill = catalogue().get(name)
    if skill is None:
        return None
    paths = [f.path for f in skill.files]
    if prefix and (prefix in paths or not any(p.startswith(prefix + "/") for p in paths)):
        return None  # a file, or nothing
    base = f"{prefix}/" if prefix else ""
    children, seen = [], set()
    for file in skill.files:
        if not file.path.startswith(base):
            continue
        head, _, tail = file.path[len(base):].partition("/")
        if head in seen:
            continue
        seen.add(head)
        if tail:
            children.append({"uri": f"{skill.root}/{base}{head}", "name": head, "mimeType": "inode/directory"})
        else:
            children.append({
                "uri": skill.file_uri(file), "name": head, "mimeType": file.mime_type, "size": len(file.content),
            })
    return skill, children


def resource(skill, file):
    """The ``Resource`` metadata of a file of a skill."""
    item = {
        "uri": skill.file_uri(file),
        "name": file.path if file.path != "SKILL.md" else skill.name,
        "mimeType": file.mime_type,
        "size": len(file.content),
    }
    if file.path == "SKILL.md":
        item["description"] = str(skill.frontmatter.get("description", ""))
    return item

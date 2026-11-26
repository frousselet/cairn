# McpSkill

`mcp.models.McpSkill`

An **agent skill** : a procedure of the organization, written for the AI
assistants connected to Cairn over MCP. The MCP server publishes it through the
`io.modelcontextprotocol/skills` extension as `skill://cairn/<name>/SKILL.md`,
in the Agent Skills format (YAML frontmatter `name` and `description`, then the
instructions), once it is validated. A skill bearing the name of one Cairn
ships replaces it for the whole instance.

File: `mcp/models/skill.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`SKIL`**),
`tags`, `version`, `created_by`, `django-simple-history` audit trail, and the
core **`default` 4-state lifecycle**. `workflow_perm_namespace` is
`system.mcp_skill`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `SKIL-N`, unique | Business reference |
| `name` | string | required, unique, max 64, `^[a-z0-9]+(-[a-z0-9]+)*$` | The skill name of the Agent Skills format, and the last segment of its URI. The web form lowercases and hyphenates what is typed |
| `description` | text | required, max 1024 | What the skill does and when an agent should use it : all an agent reads before it chooses the skill |
| `body` | text | optional, blank default | The instructions, in Markdown, served as they are written |

### Meta

Ordering `name`. Verbose names *Agent skill* / *Agent skills* (*Compétence
d'agent* / *Compétences d'agent*).

## Lifecycle

The `default` lifecycle : Draft, Pending validation, Validated, Archived.
Submit and Send back ask for `system.mcp_skill.update`, Validate and Archive for
`system.mcp_skill.approve`. Only a draft can be deleted.

## Business rules

| Rule | Statement |
| --- | --- |
| RG-MCP-SKL-01 | A skill is served over MCP while it is on a reportable step (*Validated*) and only then. |
| RG-MCP-SKL-02 | A served skill bearing the name of a skill Cairn ships replaces it, under the same URI; archiving it brings the shipped one back. |
| RG-MCP-SKL-03 | The served `SKILL.md` is generated from the record : its frontmatter holds exactly `name` and `description`, as the listing does, and its digest changes with any of the three fields, which makes the host ask the user to approve the new version. |
| RG-MCP-SKL-04 | The instructions are Markdown : never rendered as HTML, neither in the interface nor for the agent. |

## Scope tenancy

None : a procedure of the organization belongs to no scope. The register, the
REST API and the MCP tools are gated by the `system.mcp_skill.*` permissions
alone, and a served skill names tools, never records : every tool it names
answers with the permissions and scopes of the person calling it.

## Endpoints

### REST

`/api/v1/mcp/skills/` : list, create, read, update, delete, `transition`,
`history`. The detail carries `uri`, `replaces_shipped_skill`, `skill_md` (the
file served) and `completeness`.

### MCP

`list_mcp_skills`, `get_mcp_skill`, `create_mcp_skill`, `batch_create_mcp_skills`,
`update_mcp_skill`, `delete_mcp_skill`, `transition_mcp_skill`,
`mcp_skill_allowed_transitions`, `get_mcp_skill_history`. The skills themselves
are read with `skills/list`, `skills/get`, `resources/read` and
`resources/directory/read` ([reference/mcp-server.md](../../reference/mcp-server.md)).

## Permissions

`system.mcp_skill.create`, `read`, `update`, `delete`, `approve`. Super
Administrateur and Administrateur hold all five, RSSI / DPO all but `delete`,
Auditeur `read`; Contributeur and Lecteur none, as for every `system.` feature.

## Creation and completeness

Created with its name and its description, on one screen; the instructions are
written on its page. `COMPLETENESS` : *write the instructions* (`body`,
section `instructions`, blocking before Pending validation and Validated).

## UI

*Administration > Agent skills* : the register (name, description, status),
the skills Cairn ships with whether one is replaced, and the page of a skill
(identity, the `SKILL.md` served, shown as text).

## Translations

Every label has its French; the notion is *Compétence d'agent* in the glossary,
never *compétence* alone, which names what a risk source can do (EBIOS RM).

## References

- Skills extension : `io.modelcontextprotocol/skills` (SEP-2640), base revision `2026-07-28`
- Agent Skills specification : the `SKILL.md` format and its naming rules

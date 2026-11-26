# MCP server

The Model Context Protocol server of Cairn : the endpoint, its tools, the
confirmations it asks the user for, the tasks it answers long calls with, and
the skills it publishes. The transport and authentication contract is
[reference/mcp-server.md](../../reference/mcp-server.md); the tools are
listed in the [generated reference](../../reference/generated/mcp-tools.md).

| Entity | Covers |
| --- | --- |
| [McpSkill](mcp-skill.md) | An agent skill written by the organization, served over MCP once validated |

## Business rules

| Rule | Statement |
| --- | --- |
| RG-MCP-01 | Every tool runs as the person who authorized the connection, with their permissions and their scopes. |
| RG-MCP-02 | A question put to the user (elicitation) never replaces a check : the tool enforces the permission, the scopes and the lifecycle when it runs. |
| RG-MCP-03 | A task is read, updated and cancelled by the person it ran as, and by no one else. |
| RG-MCP-04 | The server publishes the skills Cairn ships (`mcp/skill_library/`) and the validated agent skills of the organization; one of the organization replaces a shipped skill of the same name. |
| RG-MCP-05 | An agent skill is served only once it reaches a reportable step of its lifecycle (*Validated*), validated by a holder of `system.mcp_skill.approve`. |

## API

- MCP endpoint : `POST /api/v1/mcp`
- REST : `/api/v1/mcp/skills/` (see [McpSkill](mcp-skill.md))

## Permissions

| Codename | Grants |
| --- | --- |
| `system.mcp.access` | Connecting to the MCP endpoint |
| `system.mcp_skill.read` / `create` / `update` / `delete` / `approve` | The agent skills register; `approve` validates a skill, which makes it served |

## UI

*Administration > Agent skills* (`/mcp/skills/`) : the register of the agent
skills, the skills Cairn ships and which of them a skill of the organization
replaces.

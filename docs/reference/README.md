# Reference

The exhaustive, mechanical listings : every endpoint, every MCP tool, every
permission, every lifecycle step, every environment variable. Look things up
here; understand them in the [specifications](../specs/README.md) or the
[technical documentation](../technical/README.md).

## Hand-written

| Page | Contents |
| --- | --- |
| [REST API](rest-api.md) | Base paths, authentication, conventions, the error contract, module-specific rules |
| [MCP server](mcp-server.md) | Transport, OAuth 2.0, the protocol, the CRUD pattern |

## Generated pages

Everything below is rendered from the code by
`python manage.py generate_docs`, and CI fails when one is stale. **Do not edit
them** : each carries a do-not-edit banner naming its source, and an edit is
reverted by the next run. Change the code and regenerate.

| Page | Rendered from |
| --- | --- |
| [REST endpoints](generated/rest-endpoints.md) | Django's URL resolver |
| [MCP tools](generated/mcp-tools.md) | The MCP tool registry |
| [Permissions](generated/permissions.md) | `PERMISSION_REGISTRY` and `SYSTEM_GROUPS` |
| [Lifecycles](generated/lifecycles.md) | The lifecycle registry |
| [Dashboard widgets](generated/dashboard-widgets.md) | `DASHBOARD_WIDGETS` |
| [Models](generated/models.md) | The Django model registry |
| [Environment variables](generated/settings.md) | The settings modules, cross-checked against `.env.example` |
| [Management commands](generated/management-commands.md) | The management-command registry |

Per-module MCP parameter tables live alongside the index :
[context](generated/mcp-tools-context.md),
[assets](generated/mcp-tools-assets.md),
[compliance](generated/mcp-tools-compliance.md),
[risks](generated/mcp-tools-risks.md),
[incidents](generated/mcp-tools-incidents.md),
[reports](generated/mcp-tools-reports.md),
[trust center](generated/mcp-tools-trust-center.md),
[system](generated/mcp-tools-system.md),
[general](generated/mcp-tools-general.md).

## Why these are generated

A reference is the part of documentation most likely to drift and least likely
to be noticed drifting, because nobody reads it end to end : they look up one
row and trust it. Deriving these pages from the registries the application
itself reads means they cannot describe a permission that does not exist or miss
an endpoint that does.

The mechanism is described in
[technical/documentation.md](../technical/documentation.md).

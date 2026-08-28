# MCP server

Cairn ships a built-in Model Context Protocol server so AI assistants and
scripts can read and manage GRC data directly. It speaks JSON-RPC 2.0 over
Streamable HTTP, protocol version `2025-03-26`, authenticates with OAuth 2.0,
and enforces the same RBAC permissions and scope-based tenancy as the web
interface.

This page is the transport and authentication contract. **The tool catalogue is
[generated from the registry](generated/mcp-tools.md)** and is never maintained
by hand.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/mcp` | The JSON-RPC 2.0 MCP endpoint |
| `GET /api/v1/mcp/.well-known/oauth-protected-resource` | Protected-resource metadata (RFC 9728), for client discovery |
| `GET /.well-known/oauth-authorization-server` | Authorization-server metadata (RFC 8414) |
| `GET /authorize` | Authorization endpoint (authorization code + PKCE) |
| `POST /api/v1/oauth/register/` | Dynamic client registration |
| `POST /api/v1/oauth/token/` | Token endpoint (authorization code and refresh grants) |
| `GET`, `POST /api/v1/oauth/applications/` | Manage your registered applications |

The two `.well-known` documents sit where the specifications require them : the
authorization-server metadata at the host root, the protected-resource metadata
next to the MCP endpoint. A compliant client needs no configuration beyond the
base URL.

## Authentication

The authorization server advertises:

| Capability | Value |
| --- | --- |
| Response types | `code` |
| Grant types | `authorization_code`, `client_credentials` |
| PKCE | `S256` |
| Client authentication | `none` (public clients, with PKCE), `client_secret_post` |
| Scopes | `claudeai` |

A client that supports dynamic registration needs nothing set up in advance : it
registers itself, runs the authorization-code flow with PKCE, and the user
approves it from the consent screen. Applications approved this way are listed
and revocable under the account's OAuth applications.

Tokens carry the granting user's identity. Every tool call runs **as that user**,
which is what makes the permission and scope checks meaningful : an assistant
connected with your token can do exactly what you can do, and nothing else.

## Protocol

| Method | Behaviour |
| --- | --- |
| `initialize` | Returns the protocol version, capabilities and server info |
| `ping` | Returns `{}` |
| `tools/list` | Returns every registered tool with its name, description and JSON Schema |
| `tools/call` | Runs a tool as the authenticated user |

Batch requests are supported : send an array, receive an array of the responses
that have an id. Notifications (a request with no `id`) return nothing.

A tool result comes back as MCP content, with the payload as JSON text. A tool
that refuses returns `isError: true` and a JSON body carrying the reason, rather
than a JSON-RPC error : a permission refusal is a result the model should read
and act on, not a transport failure.

An unexpected server-side failure is logged with its stack trace and returned as
a bare `Internal error`. That is deliberate : a tool call never leaks internals
to a connected assistant.

## The CRUD pattern

Most entities expose the same generated surface, which is why the server
registers several hundred tools rather than a curated handful.

| Operation | Tool name | Notes |
| --- | --- | --- |
| List | `list_{entity}s` | Paginated, with search, filters and `limit` / `offset` |
| Get | `get_{entity}` | By UUID |
| Create | `create_{entity}` | |
| Batch create / upsert | `batch_create_{entity}s` | Up to 500 objects, non-atomic with partial success. Pass `match_on` (a list of field names) to update matching records instead of duplicating, which makes a re-run idempotent |
| Update | `update_{entity}` | Partial |
| Delete | `delete_{entity}` | Only from a lifecycle step marked deletable |
| Transition | `{entity}_transition` | Moves the lifecycle state, enforcing permissions, mandatory comments and side effects |
| Allowed transitions | `{entity}_allowed_transitions` | What this caller may do from the current state |
| History | `get_{entity}_history` | Field diffs, approvals and lifecycle events, paginated |

Ask for `{entity}_allowed_transitions` before attempting a transition. It is the
difference between a model that respects a governance gate and one that
discovers it by failing.

## Tool catalogue

| Reference | Contents |
| --- | --- |
| [Index](generated/mcp-tools.md) | Every tool, grouped by module, with its permission and description |
| [Governance and context](generated/mcp-tools-context.md) | Scopes, issues, stakeholders, objectives, SWOT, roles, activities, indicators |
| [Assets](generated/mcp-tools-assets.md) | Essential and support assets, dependencies, suppliers, contracts, certificates |
| [Compliance](generated/mcp-tools-compliance.md) | Frameworks, requirements, assessments, findings, action plans, mappings |
| [Risks](generated/mcp-tools-risks.md) | Risk assessments, risks, threats, vulnerabilities, EBIOS RM, treatment, acceptance |
| [Incidents](generated/mcp-tools-incidents.md) | Events, incidents, evidence, custody, notifications, filings, breaches, reviews |
| [Reports](generated/mcp-tools-reports.md) | Report generation and the management review |
| [Trust Center](generated/mcp-tools-trust-center.md) | Certifications, subprocessors, measures, documents, requests |
| [System](generated/mcp-tools-system.md) | Users, groups, permissions, company settings |
| [General](generated/mcp-tools-general.md) | Saved filters, help, the assistant |

A live server answers the same question authoritatively through `tools/list`.

## Adding a tool

See [sdk/mcp-tool.md](../sdk/mcp-tool.md).

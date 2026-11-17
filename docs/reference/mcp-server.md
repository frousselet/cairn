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
| `POST /api/v1/oauth/token/` | Token endpoint (authorization code and client credentials grants) |
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
connected with your token can do exactly what you can do, and nothing else. A
token obtained through the consent screen acts as the person who approved it;
a token obtained with client credentials acts as the owner of the application.
A public client is shared by everyone who authorizes it, so a token is never
attributed from the application alone.

What bounds the flow :

| Rule | Detail |
| --- | --- |
| Redirect addresses | Registered at registration, between 1 and 10. `https`, `http` on the loopback interface only (`localhost`, `127.0.0.1`, `[::1]`), or a private scheme of an installed application. No fragment, no embedded credentials, no scheme a browser interprets itself (`javascript:`, `data:`...). A code is only ever sent to an exact registered address : an application that registered none has no authorization-code flow. |
| Consent | Offered to accounts holding `system.mcp.access` only. The screen shows the application's name **and the address that will receive the access** : the name is chosen by the application. |
| Authorization code | Single use, ten minutes, bound to the client, the redirect address and the PKCE challenge. |
| Access token | Valid `OAUTH_ACCESS_TOKEN_LIFETIME_DAYS` days (90 by default), then refused. `expires_in` is in the token response. There is no refresh token : a script asks for a new token with its credentials, an interactive client sends its user through the consent screen again. Revocable at any time under the account's OAuth applications. |
| Rate limits | Registration : 30 per hour and per address. Token endpoint : 300 per hour and per address. |

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
| [Documents](generated/mcp-tools-documents.md) | Policies and procedures, versions in force, review cycle, acknowledgement campaigns, personal acknowledgements |
| [Reports](generated/mcp-tools-reports.md) | Report generation and the management review |
| [Trust Center](generated/mcp-tools-trust-center.md) | Certifications, subprocessors, measures, documents, requests |
| [System](generated/mcp-tools-system.md) | Users, groups, permissions, company settings |
| [General](generated/mcp-tools-general.md) | Saved filters, help, the assistant |

A live server answers the same question authoritatively through `tools/list`.

## Adding a tool

See [sdk/mcp-tool.md](../sdk/mcp-tool.md).

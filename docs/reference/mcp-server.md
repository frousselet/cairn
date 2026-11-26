# MCP server

Cairn ships a built-in Model Context Protocol server so AI assistants and
scripts can read and manage GRC data directly. It speaks JSON-RPC 2.0 over
Streamable HTTP, protocol revision `2026-07-28` (and `2025-03-26` for the
clients that predate it), authenticates with OAuth 2.0,
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
| Grant types | `authorization_code`, `client_credentials`, and `urn:ietf:params:oauth:grant-type:jwt-bearer` once `MCP_EMA_ISSUER` is set (see [Enterprise Managed Auth](#enterprise-managed-auth)) |
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

The endpoint serves two revisions of the protocol. A request that names the
revision in `params._meta["io.modelcontextprotocol/protocolVersion"]` is served
under the stateless `2026-07-28` rules; a request that does not is served under
the `2025-03-26` rules, through the `initialize` handshake, exactly as before.

### Revision 2026-07-28 (stateless)

Every request carries, in `params._meta`, the protocol version and the client's
capabilities for this request (`io.modelcontextprotocol/clientCapabilities`,
required, `{}` for none). There is no handshake and no session : the server keeps
nothing between two requests, and ignores `Mcp-Session-Id`.

| Method | Behaviour |
| --- | --- |
| `server/discover` | The supported versions, the capabilities (`tools`, `resources`, the `io.modelcontextprotocol/tasks`, `skills`, `files` and `ui` extensions, and `enterprise-managed-authorization` once an issuer is trusted), the server info and instructions for the model |
| `tools/list` | Every registered tool with its name, description and JSON Schema, cacheable (`ttlMs`, `cacheScope`) |
| `tools/call` | Runs a tool as the authenticated user; may first ask the user (see [Confirmations](#confirmations-elicitation)) or answer with a task (see [Tasks](#tasks)) |
| `tasks/get`, `tasks/update`, `tasks/cancel` | The methods of the tasks extension |
| `skills/list`, `skills/get` | The skills the server publishes (see [Skills](#skills)) |
| `resources/list`, `resources/read`, `resources/directory/read` | The files of the skills, under `skill://cairn/`, and the MCP Apps, under `ui://cairn/` |

Every result carries `resultType` (`complete`, `input_required` or `task`).

| Refusal | JSON-RPC code | HTTP status |
| --- | --- | --- |
| A version the server does not serve (the supported ones are in `error.data.supported`) | `-32022` | 400 |
| `_meta` without the client capabilities | `-32602` | 400 |
| `MCP-Protocol-Version` header missing or different from `_meta`; `Mcp-Method` or `Mcp-Name` sent and different from the body | `-32020` | 400 |
| A task method without the tasks extension in the request's capabilities | `-32021` | 400 |
| An unknown method (`ping` and `initialize` included) | `-32601` | 404 |

### Revision 2025-03-26

| Method | Behaviour |
| --- | --- |
| `initialize` | Returns the protocol version, capabilities and server info |
| `ping` | Returns `{}` |
| `tools/list` | Returns every registered tool with its name, description and JSON Schema |
| `tools/call` | Runs a tool as the authenticated user |

The `Mcp-Session-Id` the client sends is echoed back. `GET` opens the
revision's event stream, which carries no notification, and `DELETE` ends the
session and revokes the access token.

### Both revisions

Batch requests are supported : send an array, receive an array of the responses
that have an id. Notifications (a request with no `id`) are accepted with a
`202` and no body.

A request whose `Origin` header names another site than the instance is refused
with a `403` : a page open in the browser of someone holding a token cannot
reach the endpoint (DNS rebinding). Programs send no `Origin`; a browser-based
client is admitted by listing its origin in `CSRF_TRUSTED_ORIGINS`.

A tool result comes back as MCP content, with the payload as JSON text. A tool
that refuses returns `isError: true` and a JSON body carrying the reason, rather
than a JSON-RPC error : a permission refusal is a result the model should read
and act on, not a transport failure.

An unexpected server-side failure is logged with its stack trace and returned as
a bare `Internal error`. That is deliberate : a tool call never leaks internals
to a connected assistant.

## Confirmations (elicitation)

When the client declares form-mode elicitation for the request
(`clientCapabilities.elicitation`, `{}` or with `form`), some tools ask the user
before they act, as the web interface does :

| Tool | What is asked | Key |
| --- | --- | --- |
| Every `delete_*` tool | A confirmation : the deletion cannot be undone | `confirm_deletion` |
| A `transition_*` tool (`transition_management_review` included) whose transition requires a comment, called without one | The comment, kept in the record's history | `transition_comment` |
| A `transition_*` tool whose target step carries a `confirm` trigger | A confirmation, with the trigger's message | `confirm_transition` |

The call answers `resultType: "input_required"` with the form in `inputRequests`
(`elicitation/create`, form mode) and a `requestState`. The client shows the
form and retries the same call with the answer in `inputResponses` and the
`requestState` echoed. The tool runs on `accept` with the box ticked (or the
comment written); on `decline`, `cancel` or an unticked box it changes nothing
and says so (`isError: true`).

What holds the confirmation :

| Rule | Detail |
| --- | --- |
| Bound to its call | `requestState` is signed with the instance's `SECRET_KEY` and names the person, the tool, a digest of the arguments and the question, for ten minutes. An answer brought with another call's state, a forged state or none is not used : the question is asked again |
| Asked of who may act | The question is only put to a person holding the tool's permission (for a transition : who may perform it), about a record within their scopes. Anyone else gets the tool's own refusal, and the form never names a record they could not read |
| Never a substitute | The tool enforces the permission, the scopes and the lifecycle rules when it runs. A client without elicitation is served as before : the call runs (a transition that requires a comment is refused without one) |

## Tasks

When the client declares the `io.modelcontextprotocol/tasks` extension for the
request (`clientCapabilities.extensions`), the long tools answer at once with a
task instead of making the client wait : the `generate_*` report tools and the
`batch_create_*` tools. The call answers `resultType: "task"` with a `taskId`,
and the client polls `tasks/get` until the task is terminal.

| Status | Meaning |
| --- | --- |
| `working` | The tool is running (`pollIntervalMs` : 2000) |
| `completed` | `result` holds the tool's result, a refusal included (`isError: true`) |
| `failed` | `error` holds a JSON-RPC error : `Internal error` for a failure of the server (logged, never described), or the worker stopped before the end |

| Rule | Detail |
| --- | --- |
| The person | A task is read, updated and cancelled by the person it ran as, and by no one else : an unknown, foreign, malformed or expired identifier answers `-32602` (*Task not found*). The identifier is a random UUID. The tool runs as that person, with their permissions and scopes when it runs, in their language |
| Durable | The task is recorded (`mcp.McpTask`) before the answer is sent, then run on a thread of the worker that took the call. The thread signs a heartbeat every 15 seconds : a task left without one for two minutes (the worker restarted or stopped) answers `failed` |
| Cancellation | Cooperative, as the extension allows : `tasks/cancel` is acknowledged and recorded, but a Cairn tool is not interrupted half way through, so the task reports its real outcome |
| Retention | `ttlMs` : two hours from creation, after which the task is deleted |
| Refused at once | A call the person has no permission for gets the tool's refusal immediately, with no task |

`tasks/update` is acknowledged : no Cairn task waits for an input.

## Skills

The server publishes skills (the `io.modelcontextprotocol/skills` extension,
with `directoryRead`) : procedures in the Agent Skills format, each a
`SKILL.md` (YAML frontmatter `name` and `description`, then instructions) read
as a resource under `skill://cairn/<name>/`.

| Source | What |
| --- | --- |
| Shipped with Cairn (`mcp/skill_library/`) | `working-with-cairn` (how to work with the tools : lifecycles, permissions, scopes, batches), `iso27005-risk-analysis`, `compliance-assessment` |
| Written by the organization | The validated [agent skills](../specs/mcp/mcp-skill.md) of *Administration > Agent skills*. One bearing the name of a shipped skill replaces it, under the same URI, while it is validated |

| Rule | Detail |
| --- | --- |
| A complete manifest | Each entry of `skills/list` and `skills/get` lists every file with its `sha256:` digest and its size, so the host verifies what it reads; any change of a skill changes its digests and the host asks the user to approve the new version |
| Validated before served | An agent skill is served only once validated, by a holder of `system.mcp_skill.approve` : its text becomes instructions in the model's context |
| Names only | A skill names tools and procedures, never a record. It is served to anyone the endpoint admits; every tool it names answers with that person's permissions and scopes. Answers carry `cacheScope: private` all the same |
| Errors | An unknown skill, file or directory answers `-32602` |

## Files

The server takes files (the `io.modelcontextprotocol/files` extension, draft) for
the tools that attach one : `add_control_test_run_evidence`,
`attach_contract_file` and `attach_certificate_file`. A file argument is a
`FileInput` (`id`, `name`, `mimeType`, `size`, optional `digest`) marked
`x-mcp-file` in the tool's schema with the types it accepts and its maximum size.

| Way | How |
| --- | --- |
| Inline | Base64 in `data`, up to 1 MiB in total per request (`maxInlineBytes`), from any client |
| Out of band | The first call answers `resultType: "upload_required"` with one target per file : `PUT` to `/api/v1/mcp/uploads/<id>` on this instance, with the client's own bearer token (`credentials: "include"`) and the declared `Content-Type`. Once every file is sent, the client retries the same call with the `requestState` it was given |

| Rule | Detail |
| --- | --- |
| Checked on the bytes | The size declared, the `digest` when sent, and the type the tool accepts (a contract or certificate file must start with the PDF signature) are checked on what arrived, never taken from the metadata |
| One target, one person, one write | A target accepts one write, of exactly the declared size, from the person it was issued to (anyone else : `404`), for one hour |
| One retry | The `requestState` is signed and binds the person, the tool, the arguments and the uploads; the uploads are consumed atomically by the first retry, so a tool never runs twice for one call (`-32602` on a second retry, or on any other call) |
| Nothing kept | Staged bytes live under `MEDIA_ROOT/mcp_uploads/` until the retry reads them or their hour is over, then are deleted |
| A client that cannot upload | A file without `data` from a client that did not declare `upload` is refused with `-32021` |

## MCP Apps

For a client that declares the `io.modelcontextprotocol/ui` extension with the
`text/html;profile=mcp-app` type, two tools name an interface in
`_meta.ui.resourceUri`, and add their data as `structuredContent` beside the
text the model reads :

| Tool | App | Shows |
| --- | --- | --- |
| `get_risk_heatmap` | `ui://cairn/risk-heatmap` | The risks within your scopes on the likelihood x impact grid, for one assessment or all, at the initial, current or residual stage |
| `get_framework_compliance_summary` | `ui://cairn/compliance-summary` | The overall compliance of a framework, by section and by status |

The app is a page the host runs in a sandboxed frame of its own origin. It is
rendered in the reader's language, loads nothing from anywhere (no CSP domain
declared, so the host's restrictive default applies), draws the data with text
nodes only, follows the host's theme, and calls no tool.

## Enterprise Managed Auth

The identity provider of the organization can sign people in to the MCP
server without a consent page (the
`io.modelcontextprotocol/enterprise-managed-authorization` extension,
draft-ietf-oauth-identity-assertion-authz-grant). It signs an Identity
Assertion JWT Authorization Grant (ID-JAG) for a person; the client posts it to
the token endpoint :

```
grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
&assertion=<ID-JAG>
&client_id=<pre-registered client>
&client_secret=<its secret>
&resource=https://<instance>/api/v1/mcp
```

Off until `MCP_EMA_ISSUER` names the one issuer trusted (see
[configuration](../technical/configuration.md#enterprise-managed-auth)); the
metadata then lists the grant and the `urn:ietf:params:oauth:grant-profile:id-jag`
profile. The assertion is refused (`invalid_grant`) unless, in this order :

| Check | Rule |
| --- | --- |
| Issuer | `iss` is `MCP_EMA_ISSUER`, exactly, before any key is fetched |
| Keys | From the issuer's `/.well-known/openid-configuration` (whose `issuer` must match) and its `jwks_uri` over https, never from the assertion |
| Signature | ES256 or RS256; `none` and HS256 are refused |
| Type | `typ` is `oauth-id-jag+jwt` |
| Audience | `aud` is the issuer of this authorization server, alone |
| Client | `client_id` is the client that authenticated with its secret (no dynamic registration : the client is registered beforehand) |
| Resource | `resource`, when present (claim or parameter), is this MCP endpoint (otherwise `invalid_target`) |
| Time | `exp`, `iat` and `nbf` hold, with 60 seconds of leeway |
| Replay | `jti` was never exchanged (remembered until the assertion expires) |
| Person | The active account whose email is the assertion's `email`, holding `system.mcp.access` (otherwise `access_denied`) |

The token acts as that person for `MCP_EMA_ACCESS_TOKEN_LIFETIME_HOURS` (8 by
default), with no refresh token : removing someone from the identity provider
ends their access when their token ends.

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
| Delete | `delete_{entity}` | Only from a lifecycle step marked deletable. Asks the user to confirm when the client supports elicitation |
| Transition | `transition_{entity}` | Moves the lifecycle state, enforcing permissions, mandatory comments and side effects. Asks the user for a required comment or a confirmation when the client supports elicitation |
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

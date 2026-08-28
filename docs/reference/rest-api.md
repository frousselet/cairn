# REST API

Cairn exposes a full REST API under `/api/v1/`, built with Django REST Framework. Every domain resource supports CRUD, filtering, search, ordering, pagination and batch creation. All endpoints enforce the same RBAC permissions and scope-based tenancy as the web UI.

## Base paths

| Module | Base path |
| ------ | --------- |
| Accounts & auth | `/api/v1/` |
| Context | `/api/v1/context/` |
| Assets | `/api/v1/assets/` |
| Compliance | `/api/v1/compliance/` |
| Risks | `/api/v1/risks/` |
| Incidents | `/api/v1/incidents/` |
| Reports | `/api/v1/reports/` |
| Assistant | `/api/v1/assistant/` |
| MCP & OAuth | `/api/v1/mcp`, `/api/v1/oauth/` |

The complete route table is [generated from the URL resolver](generated/rest-endpoints.md). The detailed per-entity contracts (fields, validation, business rules) are documented in each module's specification: see [docs/specs/](../specs/README.md). To add an endpoint, see [sdk/rest-endpoint.md](../sdk/rest-endpoint.md).

## Authentication

Three authentication methods are accepted:

| Method | Use case |
| ------ | -------- |
| Session | Browser-based access (web UI, same-origin AJAX) |
| JWT | API clients - obtain a token pair via `POST /api/v1/auth/login/`, refresh via `POST /api/v1/auth/refresh/` (token rotation enabled) |
| OAuth 2.0 bearer token | MCP and external integrations - see [mcp-server.md](mcp-server.md) |

Auth endpoints:

```
POST /api/v1/auth/login/     # email + password, returns JWT access/refresh pair
POST /api/v1/auth/refresh/   # rotate the refresh token
POST /api/v1/auth/logout/    # invalidate the session/token
GET  /api/v1/auth/me/        # current user profile (+ can_override_import_dates / can_create_users flags)
```

User provisioning:

```
POST /api/v1/users/invite/   # provision a user without a password (system.users.create)
```

Body: `{"email": "...", "last_name": "...", "first_name": "...", "groups": ["Contributeur"]}`. The account is created with an unusable password; the response returns `activation_url`, a single-use link the invitee opens to set their first credential. No password is ever accepted here.

## Conventions

- **Pagination**: page-number pagination, 25 items per page by default.
- **Filtering**: field filters via query parameters (django-filter), full-text search via `?search=`, ordering via `?ordering=field` / `?ordering=-field`.
- **Identifiers**: all domain objects use UUID primary keys.
- **Lifecycle**: state transitions go through dedicated transition endpoints/actions, never by patching a status field. Deletion is only allowed from a deletable lifecycle state.
- **Batch creation / upsert**: list resources accept batch creation (up to 500 objects, non-atomic with partial success reporting). Via the MCP layer, `batch_create_*` also accepts `match_on` for idempotent upsert (update on match instead of duplicating).
- **Audit**: every write is recorded in the object's history (django-simple-history) and increments its version.

## Incidents

The thirteen entities of module 6 are registered flat under `/api/v1/incidents/`. Nothing is nested under a parent path : a child is filtered by its parent (`?incident=<uuid>`) rather than addressed through it, so every row keeps one stable URL.

| Resource | Route |
| -------- | ----- |
| Incidents | `/api/v1/incidents/incidents/` |
| Security events | `/api/v1/incidents/security-events/` |
| Response plans | `/api/v1/incidents/response-plans/` |
| Response actions | `/api/v1/incidents/response-actions/` |
| Timeline entries | `/api/v1/incidents/timeline-entries/` |
| Evidence | `/api/v1/incidents/evidence/` |
| Custody events | `/api/v1/incidents/custody-events/` |
| Post-incident reviews | `/api/v1/incidents/post-incident-reviews/` |
| Reporting authorities | `/api/v1/incidents/reporting-authorities/` |
| Obligation templates | `/api/v1/incidents/obligation-templates/` |
| Notification obligations | `/api/v1/incidents/notifications/` |
| Notification filings | `/api/v1/incidents/notification-filings/` |
| Personal data breaches | `/api/v1/incidents/personal-data-breaches/` |

### Append-only entities

Three registers are ledgers, and the router publishes no verb that could rewrite one. `PUT`, `PATCH` and `DELETE` are not merely refused, they generate no route at all and answer `405`:

| Ledger | Verbs published | Correcting a mistake |
| ------ | --------------- | -------------------- |
| `timeline-entries/` | `GET`, `POST` | Append a further entry of type `correction` naming the entry it supersedes |
| `custody-events/` | `GET`, `POST` | Append a further handling act whose notes state what the earlier one got wrong |
| `notification-filings/` | `GET`, `POST`, `PATCH` | File again, superseding the earlier filing |

The one `PATCH` is the narrow completion of a filing : it accepts `outcome`, `acknowledged_at` and `external_reference` and nothing else, and any other key is rejected with a `400` rather than ignored. It runs through the model's own completion path, so a filing that has already been completed answers `409` instead of being overwritten.

`GET /api/v1/incidents/<ledger>/<uuid>/history/` is the tamper-detection surface on these three : a row whose trail shows more writes than the design allows was altered outside the supported paths.

### Conventions specific to the module

- **Permissions.** Six features gate the whole module : `incidents.incident`, `.event`, `.response_plan`, `.evidence`, `.notification` and `.review`. Child entities are gated by their parent's feature, so a timeline entry is `incidents.incident.*` and a custody event `incidents.evidence.*`. Appending to a ledger is an `update` on the parent, never a `create` : recording a handling act maintains the evidence item, and recording a filing discharges an obligation that already exists.
- **Tenancy.** Only the four scoped parents carry `scopes`. Every child and grandchild inherits the incident's perimeter through a declared scope path, enforced on this API, the generic workflow and history endpoints and the MCP layer alike. `reporting-authorities/` and `obligation-templates/` are shared catalogues and are deliberately not scope filtered.
- **Lifecycle.** Nine resources expose `POST .../<uuid>/transition/`; the four ledger and status-column entities (response actions, timeline entries, custody events, filings) run no lifecycle and publish no transition route. `workflow_state` is read-only everywhere : the transition endpoint is where the gates, the phase stamps and the immutable lifecycle event live. A governance refusal comes back as `403` (transition not permitted), `400` (a gate refused the move) or `409` (a write-once or append-only field was targeted), never as a `500`.
- **Derived clocks.** A notification obligation's `anchor_at`, `due_at`, `late_by` and overdue verdict are computed, never writable. `GET /api/v1/incidents/notifications/overdue/` answers "what is late" in one call, honouring every other filter, the search and the ordering; `?overdue=true` on the list route is the same definition, and the two cannot disagree.
- **Files.** Evidence artefacts and proof-of-filing documents appear in no payload. They are streamed by `GET .../evidence/<uuid>/download/`, `GET .../notifications/<uuid>/proof/` and `GET .../notification-filings/<uuid>/proof/`, each resolved through the scoped queryset and permission-checked, so an artefact carrying a TLP caveat is never one guessable media URL away. An item registered by reference, or one whose artefact is gone, is a `404`.
- **Bespoke actions.** `POST .../security-events/<uuid>/promote/` (`target`: `incident` or `vulnerability`, plus a mandatory `comment`) creates the target, declares it and moves the event on in one transaction, checking the create permission of the receiving register on top of the event's own transition permission. `POST .../evidence/<uuid>/verify-integrity/` re-measures the artefact, appends a custody row and returns one of three outcomes : `match`, `mismatch` or `not_verifiable`.

## Assistant (Ask Cairn)

`POST /api/v1/assistant/ask/` answers a simple natural-language question using the optional AI assistant (pluggable LLM provider; see [docs/specs/assistant/](../specs/assistant/README.md)).

Request body: `{"q": "Quelles décisions ont été prises lors de la dernière revue de direction ?", "language": "fr"}` (`language` optional, defaults to the request language).

Response `200`: `{"summary": "...", "language": "fr", "degraded": false, "refused_tools": [], "results": [{"tool": "list_management_review_decisions", "label": "Decisions", "error": null, "records": [{"title": "DECS-1 ...", "subtitle": "pending", "url": "/reports/decisions/<uuid>/", "icon": "bi-check2-square"}]}]}`. Records are real database objects the caller is allowed to read; the summary sentence is AI-generated and must be verified against them.

Errors: `400` on invalid `q`; `503` with a stable code (`assistant_disabled`, `assistant_unreachable`, `model_missing`, `model_error`) when the assistant is disabled or its configured LLM provider is unavailable.

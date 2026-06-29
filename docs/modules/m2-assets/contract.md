# Contract

`assets.models.contract.Contract`

A contract is an autonomous, potentially multi-party document inside the **Documents** area of the Assets module. It is the first document type implemented; further types (standards, policies, procedures) will follow as sibling entities under the same area. A contract links one or more **parties** (supplier parties and client parties), carries a single attached **PDF**, and can host **amendments** (avenants) as child contracts. A future capability will extract the PDF content automatically via Ask Cairn.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `CTRT-N`, unique | Business reference |
| `scopes` | relation | M2M -> Scope | ISMS scopes concerned by the contract. At least one scope is required by the form (RG-CTR-01). |
| `label` | string | optional, max 255 | Short title of the contract |
| `status` | enum | required, default `draft` | `draft`, `drafting`, `signing`, `active`, `under_review`, `expired`, `archived` (mirrors the lifecycle step) |
| `start_date` | date | optional | Effective date |
| `end_date` | date | optional | Termination date; drives `is_expired` |
| `amount` | decimal | optional, 14,2 | Contract value |
| `currency` | string | optional, max 3 | ISO 4217 currency code |
| `parent` | relation | FK -> Contract, optional | The contract this one amends (avenant). `null` for a top-level contract |
| `supersedes` | relation | FK -> Contract, optional, `SET_NULL` | The contract or amendment this one cancels and replaces ("annule et remplace"). Reverse: `superseded_by` |
| `suppliers` | relation | M2M -> Supplier | Supplier parties |
| `clients` | relation | M2M -> Stakeholder | Client parties (customer stakeholders) |
| `file_content` | binary | optional, not exposed via API | Inline PDF bytes (stored in the database) |
| `file_name` | string | optional, max 255 | Original PDF file name |
| `content_type` | string | optional, max 100 | MIME type (`application/pdf`) |
| `notes` | text | optional, HTML | Free-text notes |
| `tags` | relation | M2M -> Tag | |
| `is_approved` | boolean | default `false` | Validated by an approver (independent of the workflow state) |
| `approved_by` / `approved_at` | relation / datetime | optional | |
| `version` | int | auto-incremented | Bumped on each major change |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | |

## Enumerations

### `status`

- `draft`: the generic engine entry (record created); distinct from the `drafting` contract stage
- `drafting`: "projet de contrat" - the contract is being drafted / negotiated
- `signing`: under signature
- `active`: in force
- `under_review`: in force, undergoing a periodic contract review
- `expired`: past its end date, kept for audit history (no new links)
- `archived`: ended / filed (the lifecycle exit)

## Lifecycle

Contract runs the standardised lifecycle engine (`core.lifecycle`, `LIFECYCLE_NAME = "contract"`, see `assets/lifecycles.py`), like Suppliers and Scopes, and is rendered with the **directed-graph stepper** (`LifecycleStepperMixin` + `includes/lifecycle_stepper.html`, `layout="graph"`; the state badge is `{% workflow_badge %}`, which reads the current step). The step codes are exactly the `ContractStatus` values, so the legacy `status` field stays coherent with `workflow_state` (`sync_legacy_status` in `Contract.save()`).

| Step | kind | counts_in_reports | linkable | deletable |
|---|---|:--:|:--:|:--:|
| draft | Draft (generic entry) | | | yes |
| drafting | Intermediate | yes | | |
| signing | Intermediate | yes | | |
| active | Intermediate | yes | yes | |
| under_review | Intermediate | yes | yes | |
| expired | Intermediate | yes | | |
| archived | Archived (exit) | yes | | |

Transitions: `draft -> drafting` (Start drafting), `drafting -> signing` (Send for signature), `signing -> active` (Bring into force), the recurring review cycle `active -> under_review` (Start review) / `under_review -> active` (Reviewed), `active -> expired` (Expire), and `any -> archived` (Archive, requires a comment). There is deliberately **no** `expired -> active`: an expired contract is not renewed in place but replaced by a new one via `supersedes` ("annule et remplace"). The review back-edge makes the lifecycle cyclic, which is why it uses the `graph` layout. `archived` is the exit but still counts in reports for traceability. Approval (`is_approved`) is an independent axis. As with every lifecycle entity today, web transitions are gated on authentication + scope (role/form gating is a later platform-wide phase); the MCP `transition_contract` tool is permission-gated.

## Computed properties

- `is_amendment`: `true` when `parent` is set.
- `is_superseded`: `true` when at least one other contract cancels and replaces this one (`superseded_by` is non-empty).
- `is_expired`: `true` when `status=active` and `end_date` is in the past.
- `has_document`: `true` when a PDF is attached.
- `supplier_names` / `client_names`: party display names (read-only, for API / assistant output).
- `get_file_bytes()`: returns the attached PDF bytes, or `None`.

## Business rules

| ID | Rule |
|---|---|
| RG-CTR-01 | A contract must be attached to at least one scope (enforced at the form layer). |
| RG-CTR-02 | The attached document must be a PDF: extension `.pdf` + magic bytes `%PDF-` + size <= 25 MB. The file is stored inline in the database (`file_content`). |
| RG-CTR-03 | Parties are the union of `suppliers` (supplier parties) and `clients` (customer stakeholders). Any number of parties is allowed. |
| RG-CTR-04 | An amendment (avenant) is a child contract pointing to its parent via `parent`. A contract can only amend a top-level contract, never itself. |
| RG-CTR-05 | The contract list is a hierarchy (like the scope tree): each top-level contract is followed by its amendments, indented under it. |
| RG-CTR-08 | A contract or amendment can cancel and replace ("annule et remplace") another via `supersedes`. The superseded contract is kept for traceability and flagged in the UI (struck-through, "Replaced" badge); deleting the replacement nulls the link (`SET_NULL`), it does not cascade. |
| RG-CTR-06 | Deletion is only allowed in the `draft` state (lifecycle governance). |
| RG-CTR-07 | The PDF is served only through the permission-checked, scope-filtered download view, never directly via `MEDIA_URL`. |

## Endpoints

### REST

- `GET /api/v1/assets/contracts/`: list with filters `status`, `supplier`, `client`, `parent`, `is_amendment`
- `POST /api/v1/assets/contracts/`
- `GET /api/v1/assets/contracts/<uuid>/`
- `PUT/PATCH /api/v1/assets/contracts/<uuid>/`
- `DELETE /api/v1/assets/contracts/<uuid>/`
- `POST /api/v1/assets/contracts/<uuid>/approve/`

The serializer exposes `document_url` (the protected download path) but never the raw `file_content`. The PDF cannot be uploaded via the JSON API; use the web form.

### Web

- `/assets/contracts/` (list), `/assets/contracts/create/`, `/assets/contracts/<uuid>/` (detail), `/assets/contracts/<uuid>/edit/`, `/assets/contracts/<uuid>/delete/`
- `/assets/contracts/<uuid>/document/`: permission-checked, scope-filtered PDF download

### MCP

- `list_contracts` / `get_contract` / `create_contract` / `update_contract` / `delete_contract` / `approve_contract` / `batch_create_contracts`
- `transition_contract` / `contract_allowed_transitions`
- Parties and scopes are set via `scope_ids`, `supplier_ids`, `client_ids`. The PDF cannot be uploaded through MCP (binary payloads are out of scope for the JSON transport).

## Permissions

| Codename | Description |
|---|---|
| `assets.contract.read` | Read contracts (and download the PDF) |
| `assets.contract.create` | Create a contract |
| `assets.contract.update` | Modify a contract |
| `assets.contract.delete` | Delete a contract |
| `assets.contract.approve` | Approve a contract |

## Future work

Automatic content extraction via Ask Cairn (`extract_document_text()` is a clean seam, not yet implemented) will index the PDF text and structured terms for search and assistant answers.

## References

- ISO/IEC 27001:2022 Annex A §5.19 to §5.23 (supplier relationships), §5.20 (addressing security within supplier agreements)
- [Supplier](supplier.md): supplier parties of a contract
- [Stakeholder](../m1-context/stakeholder.md): customer stakeholders act as client parties

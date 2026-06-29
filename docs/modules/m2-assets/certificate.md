# Certificate

`assets.models.certificate.Certificate`

A certificate is a company certification record inside the **Documents** area of the Assets module, sibling to [Contract](contract.md). It stores and historises the organisation's own certificates (ISO/IEC 27001, HDS, SOC 2, ...). Each certificate is attached to the **framework** (référentiel) it attests compliance to (a [Framework](../m3-compliance/framework.md) of the Compliance module), carries the certification body, the certificate number and the validity dates, names the **certified perimeter** (free text + covered [Sites](site.md)), and stores a single attached **PDF**. Renewals are tracked with `supersedes` ("annule et remplace"), so the full certification history is kept over time.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `CERT-N`, unique | Business reference |
| `scopes` | relation | M2M -> Scope | ISMS scopes concerned by the certificate. At least one scope is required by the form (RG-CERT-01). |
| `label` | string | optional, max 255 | Short title of the certificate |
| `framework` | relation | FK -> Framework, `PROTECT` | The framework (référentiel) the certificate attests compliance to. Required at the form / API / MCP layers (RG-CERT-02). Reverse: `Framework.certificates` |
| `status` | enum | required, default `draft` | `draft`, `valid`, `under_renewal`, `suspended`, `expired`, `archived` (mirrors the lifecycle step) |
| `certificate_number` | string | optional, max 120 | Official certificate number from the certification body |
| `issuer` | string | optional, max 255 | Certification body that audited and issued the certificate (e.g. AFNOR, BSI) - distinct from the framework's `issuing_body` |
| `issue_date` | date | optional | Date the certificate was issued |
| `expiry_date` | date | optional | Expiry date; drives `is_expired` |
| `scope_statement` | text | optional | Perimeter covered by the certificate (free text) |
| `sites` | relation | M2M -> Site | Sites covered by the certified perimeter. Reverse: `Site.certificates` |
| `supersedes` | relation | FK -> Certificate, optional, `SET_NULL` | The previous certificate this one renews and replaces. Reverse: `superseded_by` |
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

- `draft`: the generic engine entry - the certificate is being prepared / applied for
- `valid`: the certificate is in force
- `under_renewal`: in force, undergoing a recertification / surveillance audit
- `suspended`: **terminal** - suspended by the certification body (no reinstatement; replaced by a new certificate)
- `expired`: **terminal** - lapsed or not renewed in time, kept for audit history (no new links; replaced by a new certificate)
- `archived`: filed (the lifecycle exit)

## Lifecycle

Certificate runs the standardised lifecycle engine (`core.lifecycle`, `LIFECYCLE_NAME = "certificate"`, see `assets/lifecycles.py`), like Contract / Suppliers / Scopes, and is rendered with the **directed-graph stepper** (`LifecycleStepperMixin` + `includes/lifecycle_stepper.html`, `layout="graph"`; the state badge is `{% workflow_badge %}`, which reads the current step). The step codes are exactly the `CertificateStatus` values, so the legacy `status` field stays coherent with `workflow_state` (`sync_legacy_status` in `Certificate.save()`).

| Step | kind | terminal | counts_in_reports | linkable | deletable |
|---|---|:--:|:--:|:--:|:--:|
| draft | Draft (generic entry) | | | | yes |
| valid | Intermediate | | yes | yes | |
| under_renewal | Intermediate | | yes | yes | |
| suspended | Intermediate | yes | yes | | |
| expired | Intermediate | yes | yes | | |
| archived | Archived (exit) | | yes | | |

Transitions: `draft -> valid` (Issue certificate), the recurring recertification cycle `valid -> under_renewal` (Start renewal) / `under_renewal -> valid` (Renewed) - the only non-terminal branch - then `valid -> suspended` (Suspend), `valid -> expired` / `under_renewal -> expired` (Expire), and `any -> archived` (Archive). **Suspended and Expired are terminal**: there is no reinstatement and no renewal in place - re-certifying means issuing a new certificate that supersedes this one via `supersedes` ("annule et remplace"), so the renewal history is kept; the only move out of a terminal state is Archive (terminality is structural - those steps have no outgoing transition other than the from-any Archive). The recertification back-edge makes the lifecycle cyclic, which is why it uses the `graph` layout. `archived` is the exit but still counts in reports for traceability. Approval (`is_approved`) is an independent axis. As with every lifecycle entity today, web transitions are gated on authentication + scope (role/form gating is a later platform-wide phase); the MCP `transition_certificate` tool is permission-gated.

## Computed properties

- `framework_label`: the framework's abbreviation (`short_name`) or full `name`, or `""` when no framework is set.
- `is_superseded`: `true` when at least one other certificate renews and replaces this one (`superseded_by` is non-empty).
- `is_expired`: `true` when `expiry_date` is in the past and the status is `valid` or `under_renewal` (the live states).
- `has_document`: `true` when a PDF is attached.
- `site_names`: covered-site display names (read-only, for API / assistant output).
- `get_file_bytes()`: returns the attached PDF bytes, or `None`.

## Business rules

| ID | Rule |
|---|---|
| RG-CERT-01 | A certificate must be attached to at least one scope (enforced at the form layer). |
| RG-CERT-02 | A certificate must name the framework (référentiel) it attests compliance to. The framework is a `compliance.Framework`; requiredness is enforced at the form / API / MCP layers, and `PROTECT` prevents deleting a framework that still has certificates. |
| RG-CERT-03 | The attached document must be a PDF: extension `.pdf` + magic bytes `%PDF-` + size <= 25 MB. The file is stored inline in the database (`file_content`). |
| RG-CERT-04 | The certified perimeter is described by `scope_statement` (free text) and the covered `sites`. |
| RG-CERT-05 | A certificate can renew and replace ("annule et remplace") a previous one via `supersedes`. The superseded certificate is kept for traceability and flagged in the UI (struck-through, "Replaced" badge); deleting the replacement nulls the link (`SET_NULL`), it does not cascade. |
| RG-CERT-06 | The expiry date cannot be earlier than the issue date (form validation). |
| RG-CERT-07 | Deletion is only allowed in the `draft` state (lifecycle governance). |
| RG-CERT-08 | The PDF is served only through the permission-checked, scope-filtered download view, never directly via `MEDIA_URL`. |

## Endpoints

### REST

- `GET /api/v1/assets/certificates/`: list with filters `status`, `framework`, `scope`, `site`, `supersedes`, `expiry_before`, `expiry_after`
- `POST /api/v1/assets/certificates/`
- `GET /api/v1/assets/certificates/<uuid>/`
- `PUT/PATCH /api/v1/assets/certificates/<uuid>/`
- `DELETE /api/v1/assets/certificates/<uuid>/`
- `POST /api/v1/assets/certificates/<uuid>/approve/`

The serializer exposes `framework_label` and `document_url` (the protected download path) but never the raw `file_content`. The PDF cannot be uploaded via the JSON API; use the web form.

### Web

- `/assets/certificates/` (list), `/assets/certificates/create/`, `/assets/certificates/<uuid>/` (detail), `/assets/certificates/<uuid>/edit/`, `/assets/certificates/<uuid>/delete/`
- `/assets/certificates/<uuid>/document/`: permission-checked, scope-filtered PDF download

### MCP

- `list_certificates` / `get_certificate` / `create_certificate` / `update_certificate` / `delete_certificate` / `approve_certificate` / `batch_create_certificates`
- `transition_certificate` / `certificate_allowed_transitions`
- The framework, scopes and covered sites are set via `framework_id`, `scope_ids`, `site_ids`. The PDF cannot be uploaded through MCP (binary payloads are out of scope for the JSON transport).

## Permissions

| Codename | Description |
|---|---|
| `assets.certificate.read` | Read certificates (and download the PDF) |
| `assets.certificate.create` | Create a certificate |
| `assets.certificate.update` | Modify a certificate |
| `assets.certificate.delete` | Delete a certificate |
| `assets.certificate.approve` | Approve a certificate |

## References

- [Framework](../m3-compliance/framework.md): the référentiel a certificate attests compliance to
- [Site](site.md): sites covered by the certified perimeter
- [Contract](contract.md): the sibling document type under the Documents area
- ISO/IEC 27001:2022 (the canonical example of a certifiable référentiel)

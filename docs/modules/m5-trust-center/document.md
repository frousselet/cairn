# TrustCenterDocument

`trust_center.models.document.TrustCenterDocument`

A document published on the public Trust Center : a policy, a certificate, an audit report or any other shareable artifact. Its source is **exactly one** of a generated internal `reports.Report` or an inline uploaded file (stored as bytes, mirroring the Report storage so the same streaming download view serves both). The `access` level decides whether the document downloads directly (public) or behind a request-and-approval flow (gated).

File: `trust_center/models/document.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`TCDO`**, e.g. `TCDO-1`), `django-simple-history` audit trail (excluding `file_content`), and the `trust_center_publication` lifecycle workflow.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier. Also the public download handle (the one identifier the public document serializer exposes). |
| `reference` | string | auto `TCDO-N`, unique | Business reference |
| `title` | string | required, max 255 | Public-facing document title |
| `description` | text | optional, blank default | Public-facing description |
| `access` | enum | required, default `public` | `public` (direct download) or `gated` (request + approval) |
| `requires_nda` | boolean | required, default `True` | Whether an NDA acceptance is required. **Only meaningful for gated documents.** |
| `report` | relation | FK -> `reports.Report`, `PROTECT`, nullable, blank | Source report. `related_name="trust_center_documents"`. Mutually exclusive with the inline file (enforced in `clean()`). |
| `file_content` | binary | nullable, blank, `editable=False` | Inline file bytes (UI-only upload path). Mutually exclusive with `report`. Never serialized; excluded from history. |
| `file_name` | string | optional, max 255, blank default | Inline file name |
| `content_type` | string | optional, max 100, blank default | Inline MIME type (used as the download `Content-Type`) |
| `display_order` | int | `PositiveIntegerField`, default `0` | Render order within the Documents section |
| `workflow_state` | string | indexed | Lifecycle state (`trust_center_publication`) |
| `created_by` | relation | FK -> User | Creator |
| `created_at` / `updated_at` | datetime | auto | Timestamps |
| `tags` | relation | M2M -> Tag | Free tagging (from `BaseModel`) |

`Meta.ordering = ["display_order", "title"]`. `HistoricalRecords(excluded_fields=["file_content"])`.

## Enumerations

### `access` (`DocumentAccess`)

| Value | Description |
|---|---|
| `public` | Anyone can download directly via the streaming view, subject to the dual gate and the global switch. |
| `gated` | Not directly downloadable. Requires a [document request](document-request.md), curator approval, and a signed time-limited link. |

## Validation (`clean()`)

The source must be **exactly one** of report or inline content:

- both set -> `ValidationError` ("Provide either a source report or an uploaded file, not both.")
- neither set -> `ValidationError` ("Provide a source report or upload a file.")

This one-of invariant (RG-TC-18) is enforced at the model level so it holds regardless of the entry point.

## Computed properties and helpers

- `is_gated` : `access == gated`.
- `effective_file_name` : the report's file name when report-backed, else `file_name`.
- `get_file_bytes()` : returns the bytes from the linked report's `file_content` when report-backed, else the inline `file_content`, else `None`.
- `workflow_perm_namespace` : `"trust_center.document"`.

## Lifecycle

Runs the shared `trust_center_publication` workflow (see [README.md §2.3](README.md#23-the-trust_center_publication-workflow)). Publish / unpublish / archive-from-published require `approve`; archiving a draft / unpublished entry is `update`.

## Publish gate (dual gate)

`DocumentQuerySet.published()` returns an entry only when **both**:

1. its `workflow_state` is `published`, AND
2. either it has no report (inline-file document) OR its `report.status` is `completed`.

So a document backed by a report that is not yet completed (or was reverted) drops out of the public list automatically (RG-TC-08 / RG-TC-21). The global `is_published` switch is enforced separately at the view layer.

## Download

- **Public documents** : `GET /trust/documents/<uuid>/download/` streams the bytes with `Content-Disposition: attachment`. The view re-checks the global switch (404 if off), filters on `published()` AND `access = public`, and 404s a missing / gated / empty document. Files are **never** exposed under `/media/` (RG-TC-20).
- **Gated documents** : not served by the public download view. They require the [document request](document-request.md) flow and a signed, expiring link (TTL via `TRUST_CENTER_DOWNLOAD_TTL`), served by `TrustCenterGatedDownloadView` at `/trust/documents/download/<token>/`.

## Business rules

| ID | Rule |
|---|---|
| RG-TC-18 | Source is exactly one of `report` or inline `file_content` (+ `file_name` + `content_type`); enforced in `clean()`. |
| RG-TC-19 | `access` is `public` (direct) or `gated` (request + approval). |
| RG-TC-20 | Bytes are streamed through a view, never exposed under `/media/`. `file_content` is excluded from history and never serialized. |
| RG-TC-21 | A report-backed document is public only when its report is `completed`. `requires_nda` only applies to gated documents. |
| RG-TC-02 | The `report` FK is `PROTECT` : a report still referenced by a document cannot be hard-deleted. |

## Endpoints

### REST (management, authenticated, `/api/v1/trust-center/`)

- `GET /documents/` : list (search on `title`, `description`; ordering on `display_order`, `title`, `created_at`; `?workflow_state=` filter).
- `POST /documents/` : create. **A source `report` is required via the API** : the inline-upload path is UI-only, so `DocumentSerializer.validate()` rejects an API create without `report` (the model's one-of invariant still holds).
- `GET /documents/{id}/`
- `PUT/PATCH /documents/{id}/`
- `DELETE /documents/{id}/`
- `POST /documents/{id}/transition/`

The management serializer exposes `title`, `description`, `access`, `requires_nda`, `report`, `file_name`, `display_order` (+ the read-only base fields). It never exposes `file_content`.

### REST (public, `/trust/api/`)

- `GET /trust/api/documents/` : published documents via `PublicDocumentSerializer` (fields: `id`, `title`, `description`, `access`, `requires_nda`). The `id` is the download handle; bytes are fetched via the download endpoint, not this list. Also included in the aggregate `GET /trust/api/`.
- `GET /trust/documents/<uuid>/download/` : public document byte stream (see Download above).

### MCP

- `list_trust_center_document` / `get_trust_center_document` / `create_trust_center_document` / `update_trust_center_document` / `delete_trust_center_document`
- `transition_trust_center_document` / `trust_center_document_allowed_transitions`

## Permissions

| Codename | Description |
|---|---|
| `trust_center.document.read` | List / read documents |
| `trust_center.document.create` | Create a document |
| `trust_center.document.update` | Modify a document (and archive a draft / unpublished one) |
| `trust_center.document.delete` | Hard-delete a document |
| `trust_center.document.approve` | Publish / unpublish / archive a published document |

Gated-document requests have their own feature, `document_request` (see [document-request.md](document-request.md)).

## References

- `reports.Report` (`reports.models.report.Report`) : the optional source object; its `status` gates publication and its bytes feed the download.
- [DocumentRequest](document-request.md) : the request / approval / signed-link flow for gated documents.
- [README.md](README.md) : §2.7 (document rules), §6.3 (no raw file exposure).

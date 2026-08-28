<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : Trust Center

Input schemas for the 42 `trust_center` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `approve_trust_center_document_request`

Approve a gated-document request: issues a time-limited signed download link and emails it to the requester.

Requires `trust_center.document_request.approve`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `batch_create_trust_center_certifications`

Create or upsert multiple trust center certifications in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `trust_center.certification.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of trust center certification objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_trust_center_documents`

Create or upsert multiple trust center documents in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `trust_center.document.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of trust center document objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_trust_center_measures`

Create or upsert multiple trust center measures in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `trust_center.measure.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of trust center measure objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_trust_center_subprocessors`

Create or upsert multiple trust center subprocessors in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `trust_center.subprocessor.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of trust center subprocessor objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `create_trust_center_certification`

Create a new trust center certification

Requires `trust_center.certification.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `framework` | `string` | yes | UUID of the source compliance framework. |
| `public_label` | `string` | yes | public_label |
| `public_description` | `string` | - | public_description |
| `show_percentage` | `boolean` | - | Show this certification's compliance percentage. |
| `display_order` | `integer` | - | Ascending sort order. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_trust_center_document`

Create a new trust center document

Requires `trust_center.document.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `title` | `string` | yes | title |
| `description` | `string` | - | description |
| `access` | `string` | - | Access level: 'public' (direct download) or 'gated' (request + approval). |
| `requires_nda` | `boolean` | - | Whether a gated document requires NDA acceptance. |
| `report` | `string` | - | UUID of the source generated report (required when creating via the API/MCP). |
| `display_order` | `integer` | - | Ascending sort order. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_trust_center_measure`

Create a new trust center measure

Requires `trust_center.measure.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `title` | `string` | yes | title |
| `description` | `string` | - | description |
| `icon` | `string` | - | Bootstrap Icons name, e.g. bi-shield-check. |
| `category` | `string` | - | One of: organizational, technical, physical. |
| `display_order` | `integer` | - | Ascending sort order. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_trust_center_subprocessor`

Create a new trust center subprocessor

Requires `trust_center.subprocessor.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `supplier` | `string` | yes | UUID of the source supplier. |
| `public_name` | `string` | yes | public_name |
| `purpose` | `string` | - | purpose |
| `public_country` | `string` | - | public_country |
| `public_website` | `string` | - | public_website |
| `display_order` | `integer` | - | Ascending sort order. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `delete_trust_center_certification`

Delete a trust center certification

Requires `trust_center.certification.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_trust_center_document`

Delete a trust center document

Requires `trust_center.document.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_trust_center_measure`

Delete a trust center measure

Requires `trust_center.measure.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_trust_center_subprocessor`

Delete a trust center subprocessor

Requires `trust_center.subprocessor.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_trust_center_certification`

Get a trust center certification by ID

Requires `trust_center.certification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_trust_center_certification_history`

Return the change history of a trust center certification: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `trust_center.certification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the trust center certification |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_trust_center_document`

Get a trust center document by ID

Requires `trust_center.document.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_trust_center_document_history`

Return the change history of a trust center document: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `trust_center.document.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the trust center document |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_trust_center_document_request`

Get a Trust Center document request by ID.

Requires `trust_center.document_request.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_trust_center_measure`

Get a trust center measure by ID

Requires `trust_center.measure.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_trust_center_measure_history`

Return the change history of a trust center measure: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `trust_center.measure.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the trust center measure |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_trust_center_settings`

Get the public Trust Center settings (publication switch, headline, intro, security contact, theme).

Requires `trust_center.settings.read`.

No parameters.

## `get_trust_center_subprocessor`

Get a trust center subprocessor by ID

Requires `trust_center.subprocessor.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_trust_center_subprocessor_history`

Return the change history of a trust center subprocessor: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `trust_center.subprocessor.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the trust center subprocessor |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `list_trust_center_certifications`

List trust center certifications with optional search and filters

Requires `trust_center.certification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `list_trust_center_document_requests`

List Trust Center gated-document access requests (optionally filter by workflow_state).

Requires `trust_center.document_request.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `workflow_state` | `string` | - | Filter by state: pending, approved, rejected. |

## `list_trust_center_documents`

List trust center documents with optional search and filters

Requires `trust_center.document.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `list_trust_center_measures`

List trust center measures with optional search and filters

Requires `trust_center.measure.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `list_trust_center_subprocessors`

List trust center subprocessors with optional search and filters

Requires `trust_center.subprocessor.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `reject_trust_center_document_request`

Reject a pending gated-document request, or revoke access for an approved one. A comment is required.

Requires `trust_center.document_request.approve`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the request |
| `comment` | `string` | yes | Reason (required) |

## `transition_trust_center_certification`

Change the lifecycle state of a trust center certification (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `trust_center.certification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the trust center certification |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_trust_center_document`

Change the lifecycle state of a trust center document (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `trust_center.document.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the trust center document |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_trust_center_measure`

Change the lifecycle state of a trust center measure (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `trust_center.measure.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the trust center measure |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_trust_center_subprocessor`

Change the lifecycle state of a trust center subprocessor (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `trust_center.subprocessor.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the trust center subprocessor |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `trust_center_certification_allowed_transitions`

List the lifecycle transitions the caller may perform on a trust center certification from its current state.

Requires `trust_center.certification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `trust_center_document_allowed_transitions`

List the lifecycle transitions the caller may perform on a trust center document from its current state.

Requires `trust_center.document.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `trust_center_measure_allowed_transitions`

List the lifecycle transitions the caller may perform on a trust center measure from its current state.

Requires `trust_center.measure.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `trust_center_subprocessor_allowed_transitions`

List the lifecycle transitions the caller may perform on a trust center subprocessor from its current state.

Requires `trust_center.subprocessor.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `update_trust_center_certification`

Update an existing trust center certification

Requires `trust_center.certification.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `framework` | `string` | - | UUID of the source compliance framework. |
| `public_label` | `string` | - | public_label |
| `public_description` | `string` | - | public_description |
| `show_percentage` | `boolean` | - | Show this certification's compliance percentage. |
| `display_order` | `integer` | - | Ascending sort order. |

## `update_trust_center_document`

Update an existing trust center document

Requires `trust_center.document.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `title` | `string` | - | title |
| `description` | `string` | - | description |
| `access` | `string` | - | Access level: 'public' (direct download) or 'gated' (request + approval). |
| `requires_nda` | `boolean` | - | Whether a gated document requires NDA acceptance. |
| `report` | `string` | - | UUID of the source generated report (required when creating via the API/MCP). |
| `display_order` | `integer` | - | Ascending sort order. |

## `update_trust_center_measure`

Update an existing trust center measure

Requires `trust_center.measure.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `title` | `string` | - | title |
| `description` | `string` | - | description |
| `icon` | `string` | - | Bootstrap Icons name, e.g. bi-shield-check. |
| `category` | `string` | - | One of: organizational, technical, physical. |
| `display_order` | `integer` | - | Ascending sort order. |

## `update_trust_center_settings`

Update the public Trust Center settings. Set is_published=true to expose the public page and API; false takes the whole Trust Center offline (404).

Requires `trust_center.settings.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `is_published` | `boolean` | - | Master switch: expose the public Trust Center page and API. |
| `headline` | `string` | - | Public hero headline. |
| `intro` | `string` | - | Public introduction paragraph. |
| `contact_email` | `string` | - | Public security contact email. |
| `show_compliance_percentages` | `boolean` | - | Show numeric compliance percentages on certifications. |
| `theme_accent` | `string` | - | Accent colour as a hex value, e.g. #1E3A8A. |
| `custom_domain` | `string` | - | Informational custom domain (routing is configured via the TRUST_CENTER_HOST env var). |

## `update_trust_center_subprocessor`

Update an existing trust center subprocessor

Requires `trust_center.subprocessor.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `supplier` | `string` | - | UUID of the source supplier. |
| `public_name` | `string` | - | public_name |
| `purpose` | `string` | - | purpose |
| `public_country` | `string` | - | public_country |
| `public_website` | `string` | - | public_website |
| `display_order` | `integer` | - | Ascending sort order. |

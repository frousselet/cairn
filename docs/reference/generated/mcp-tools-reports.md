<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : Reports and management review

Input schemas for the 18 `reports` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `create_isms_change`

Record an ISMS change decided during a management review.

Requires `reports.management_review.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `review_id` | `string` | yes |  |
| `change_type` | `string` | - | scope\|policy\|control\|organization\|resource\|process\|other |
| `title` | `string` | yes |  |
| `description` | `string` | yes |  |
| `impact_analysis` | `string` | - |  |
| `affected_policies` | `string` | - |  |
| `owner_id` | `string` | yes |  |
| `status` | `string` | - |  |
| `target_date` | `string` | - |  |

## `create_management_review`

Create a management review (ISO 27001:2022 clause 9.3).

Requires `reports.management_review.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `title` | `string` | yes |  |
| `description` | `string` | - |  |
| `frequency` | `string` | yes | quarterly\|semiannual\|annual\|exceptional |
| `period_start` | `string` | yes | YYYY-MM-DD |
| `period_end` | `string` | yes | YYYY-MM-DD |
| `planned_date` | `string` | yes | YYYY-MM-DD |
| `location` | `string` | - |  |
| `facilitator_id` | `string` | yes |  |
| `scope_ids` | `array` | - |  |

## `create_management_review_decision`

Record a decision from a management review (ISO 27001:2022 clause 9.3.3).

Requires `reports.management_review.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `review_id` | `string` | yes |  |
| `category` | `string` | - | improvement\|isms_change\|resource_allocation\|risk_acceptance\|objective_adjustment\|policy_update\|other |
| `input_clause` | `string` | - | 9.3.2 clause letter: a\|b\|c\|d1\|d2\|d3\|d4\|e\|f\|g |
| `title` | `string` | yes |  |
| `description` | `string` | yes |  |
| `rationale` | `string` | - |  |
| `owner_id` | `string` | - |  |
| `due_date` | `string` | - |  |
| `priority` | `string` | - |  |
| `status` | `string` | - |  |

## `delete_report`

Delete a generated report

Requires `reports.report.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `download_report`

Retrieve the binary content of a previously generated report. Returns the file as a base64-encoded string along with its content type, size and original filename. Use list_reports first to discover available report IDs.

Requires `reports.report.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `export_management_review`

Export a management review as DOCX (meeting minutes) or PPTX (presentation). Returns base64-encoded content.

Requires `reports.management_review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes |  |
| `format` | `string` | - | docx\|pptx |

## `generate_audit_report`

Generate an audit report PDF for a completed or closed compliance assessment

Requires `reports.report.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | UUID of the compliance assessment (must be completed or closed) |

## `generate_management_review_docx`

Generate a management review meeting minutes document (Word) covering ISO 27001 clause 9.3 inputs: action plans, issues, stakeholders, security performance, risks, and improvement opportunities

Requires `reports.report.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `scope_ids` | `array` | - | Optional list of scope UUIDs to filter data. Omit to include all data. |
| `period_start` | `string` | - | Start of the review period (YYYY-MM-DD). Omit to include all past data. |
| `period_end` | `string` | - | End of the review period (YYYY-MM-DD). Defaults to today. |

## `generate_management_review_pptx`

Generate a management review presentation (PowerPoint) covering ISO 27001 clause 9.3 inputs: action plans, issues, stakeholders, security performance, risks, and improvement opportunities

Requires `reports.report.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `scope_ids` | `array` | - | Optional list of scope UUIDs to filter data. Omit to include all data. |
| `period_start` | `string` | - | Start of the review period (YYYY-MM-DD). Omit to include all past data. |
| `period_end` | `string` | - | End of the review period (YYYY-MM-DD). Defaults to today. |

## `generate_soa_report`

Generate a Statement of Applicability (SoA) PDF report for one or more frameworks

Requires `reports.report.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `framework_ids` | `array` | yes | List of framework UUIDs to include in the SoA |

## `get_management_review`

Get a management review by ID.

Requires `reports.management_review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes |  |

## `list_isms_changes`

List ISMS changes decided during management reviews (ISO 27001:2022 clause 9.3.3).

Requires `reports.management_review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `review_id` | `string` | - |  |
| `limit` | `integer` | - |  |
| `offset` | `integer` | - |  |

## `list_management_review_decisions`

List decisions (ISO 27001:2022 clause 9.3.3 outputs). Filter by review or status.

Requires `reports.management_review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `review_id` | `string` | - |  |
| `status` | `string` | - |  |
| `limit` | `integer` | - |  |
| `offset` | `integer` | - |  |

## `list_management_reviews`

List management reviews (ISO 27001:2022 clause 9.3). Filter by status or scope.

Requires `reports.management_review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | `string` | - | planned\|in_preparation\|held\|closed\|cancelled |
| `scope_id` | `string` | - |  |
| `limit` | `integer` | - |  |
| `offset` | `integer` | - |  |

## `list_reports`

List generated reports, optionally filtered by report_type

Requires `reports.report.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `report_type` | `string` | - | Filter by report type (e.g. 'soa') |
| `limit` | `integer` | - | Max results (default 50) |
| `offset` | `integer` | - | Offset for pagination |

## `promote_decision_to_action_plan`

Create a ComplianceActionPlan from a management review decision.

Requires `reports.management_review.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `decision_id` | `string` | yes |  |

## `set_participant_signature`

Attach a graphical signature (data URI) to a participant for DOCX embedding.

Requires `reports.management_review.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `participant_id` | `string` | yes |  |
| `signature_data_uri` | `string` | yes | Data URI, e.g. data:image/png;base64,iVBORw0KGgo... |

## `transition_management_review`

Transition a management review to a new status (planned -> in_preparation -> held -> closed, or cancelled).

Requires `reports.management_review.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes |  |
| `target_status` | `string` | yes |  |
| `comment` | `string` | - |  |

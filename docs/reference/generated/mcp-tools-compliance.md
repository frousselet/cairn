<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : Compliance

Input schemas for the 64 `compliance` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `action_plan_allowed_transitions`

Get allowed status transitions for an action plan, including permission checks and refusal/cancellation flags. Call this before action_plan_transition to know what is possible.

Requires `compliance.action_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `action_plan_id` | `string` | yes | UUID of the action plan |

## `action_plan_kanban`

Get action plans grouped by status for kanban board, including workflow transition rules

Requires `compliance.action_plan.read`.

No parameters.

## `action_plan_transition`

Transition an action plan to a new Kanban status. Forward flow: new → to_define → to_validate → to_implement → implementation_to_validate → validated → closed. Refusals (require comment): to_validate → to_define, implementation_to_validate → to_implement. Cancellation: any non-terminal status → cancelled.

Requires `compliance.action_plan.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `action_plan_id` | `string` | yes | UUID of the action plan |
| `target_status` | `string` | yes | Target status to transition to |
| `comment` | `string` | - | Comment explaining the transition. Mandatory for refusals (backward transitions). Recommended for cancellations. |

## `action_plan_transitions`

List transition history for an action plan

Requires `compliance.action_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `action_plan_id` | `string` | yes | UUID of the action plan |

## `batch_create_action_plans`

Create or upsert multiple action plans in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `compliance.action_plan.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of action plan objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_frameworks`

Create or upsert multiple frameworks in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `compliance.framework.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of framework objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_requirement_mappings`

Create or upsert multiple requirement mappings in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `compliance.mapping.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of requirement mapping objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_requirements`

Create or upsert multiple requirements in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `compliance.requirement.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of requirement objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_sections`

Create or upsert multiple sections in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `compliance.section.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of section objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `create_action_plan`

Create a new action plan

Requires `compliance.action_plan.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `gap_description` | `string` | yes | Gap description (HTML rich text) |
| `remediation_plan` | `string` | yes | Remediation plan (HTML rich text) |
| `priority` | `string` | yes | Priority level. |
| `start_date` | `string` | - | Start date (ISO 8601). |
| `target_date` | `string` | yes | Target completion date (ISO 8601, e.g. 2025-12-31) |
| `completion_date` | `string` | - | Actual completion date (ISO 8601). Auto-set when transitioning to CLOSED. |
| `cost_estimate` | `number` | - | Estimated cost of the action plan. |
| `progress_percentage` | `integer` | - | Progress percentage (0-100) |
| `owner_id` | `string` | yes | UUID of the action plan owner (user) |
| `originating_review_id` | `string` | - | UUID of the management review that spawned this plan (optional). |
| `scope_ids` | `array` | - | Scopes this plan applies to. |
| `assignee_ids` | `array` | - | UUIDs of assignees (users) for this plan. |
| `requirement_ids` | `array` | - | Compliance requirements this plan addresses. |
| `finding_ids` | `array` | - | Audit findings this plan addresses. |
| `risk_ids` | `array` | - | Risks this plan helps mitigate. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_action_plan_comment`

Create a comment or reply on an action plan

Requires `compliance.action_plan.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `action_plan_id` | `string` | yes | UUID of the action plan |
| `content` | `string` | yes | Comment text |
| `parent_id` | `string` | - | UUID of parent comment (for replies, optional) |

## `create_assessment_result`

Create a new assessment result

Requires `compliance.assessment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | - | assessment_id |
| `requirement_id` | `string` | - | requirement_id |
| `compliance_status` | `string` | - | Compliance status. Same 11-value enum as Requirement.compliance_status: the 5 conformance-oriented values (not_assessed, non_compliant, partially_compliant, compliant, not_applicable) plus the 6 audit-oriented values (evaluated, major_non_conformity, minor_non_conformity, observation, improvement_opportunity, strength). See docs/specs/m3-compliance/requirement.md for the audit -> conformance mapping used by RC-01 / RC-02 averages. |
| `compliance_level` | `string` | - | compliance_level |
| `finding` | `string` | - | Finding (HTML rich text) |
| `auditor_recommendations` | `string` | - | Auditor recommendations (HTML rich text) |
| `evidence` | `string` | - | Evidence (HTML rich text) |
| `assessed_by_id` | `string` | - | UUID of the assessor (user) |
| `assessed_at` | `string` | - | Assessment date-time in ISO 8601 format (e.g. 2025-01-15T10:30:00Z) |

## `create_compliance_assessment`

Create a new compliance assessment

Requires `compliance.assessment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `limitations` | `string` | - | limitations |
| `assessment_start_date` | `string` | - | assessment_start_date |
| `assessment_end_date` | `string` | - | assessment_end_date |
| `status` | `string` | - | status |
| `assessor_id` | `string` | - | assessor_id |
| `framework_ids` | `array` | - | List of framework UUIDs to link to this assessment |
| `scope_ids` | `array` | - | List of scope UUIDs this assessment covers (RG-01). |

## `create_finding`

Create a new audit finding

Requires `compliance.finding.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | - | assessment_id |
| `source` | `string` | - | What surfaced the nonconformity. 'audit' additionally requires assessment_id and assessor_id. |
| `finding_type` | `string` | - | Type of finding. Allowed values: major_nc (Major non-conformity, ref NCMAJ-x), minor_nc (Minor non-conformity, ref NCMIN-x), observation (Observation, ref OBS-x), improvement (Improvement opportunity, ref OA-x), strength (Strength, ref STR-x) |
| `description` | `string` | - | Finding description (HTML rich text) |
| `recommendation` | `string` | - | Recommendation (HTML rich text) |
| `evidence` | `string` | - | Evidence presented (HTML rich text) |
| `assessor_id` | `string` | - | UUID of the user who raised the nonconformity. Required when source is 'audit', optional otherwise. |
| `effectiveness_reviewed_at` | `string` | - | effectiveness_reviewed_at |
| `effectiveness_reviewed_by_id` | `string` | - | effectiveness_reviewed_by_id |
| `effectiveness_verdict` | `string` | - | ISO 27001 clause 10.2 d) : whether the corrective action worked. Requires effectiveness_reviewed_at. |
| `requirement_ids` | `array` | - | List of requirement UUIDs to link to this finding |

## `create_framework`

Create a new framework

Requires `compliance.framework.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `short_name` | `string` | - | short_name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Framework type. |
| `category` | `string` | - | Framework category. |
| `framework_version` | `string` | - | Version of the framework (e.g. '2022'). |
| `publication_date` | `string` | - | Publication date (ISO 8601). |
| `effective_date` | `string` | - | Effective date (ISO 8601). |
| `expiry_date` | `string` | - | Expiry date (ISO 8601). |
| `issuing_body` | `string` | - | Standards body or regulator that issued the framework. |
| `jurisdiction` | `string` | - | Jurisdiction the framework applies to. |
| `url` | `string` | - | Official link to the framework. |
| `is_mandatory` | `boolean` | - | Whether the framework is mandatory (drives RC-05 non-compliance alert). |
| `is_applicable` | `boolean` | - | Whether the framework applies to the organisation (drives Statement of Applicability inclusion). |
| `applicability_justification` | `string` | - | Applicability justification (HTML rich text) |
| `applicability_managed_by_risks` | `boolean` | - | When true, each requirement's applicability is derived automatically from its linked risks: applicable when at least one active (reportable) risk is linked, not applicable otherwise. The requirement fields is_applicable / applicability_justification then become read-only (writes are ignored). |
| `status` | `string` | - | Framework status. |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `owner_id` | `string` | - | UUID of the framework owner (user) |
| `logo` | `string` | - | logo |
| `scope_ids` | `array` | - | Scopes this framework applies to (RG-01). |
| `related_stakeholder_ids` | `array` | - | Stakeholders interested in this framework. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_requirement`

Create a new requirement

Requires `compliance.requirement.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `requirement_number` | `string` | - | requirement_number |
| `name` | `string` | yes | name |
| `description` | `string` | yes | Description (HTML rich text) |
| `guidance` | `string` | - | Implementation recommendations (HTML rich text) |
| `type` | `string` | yes | Requirement type. |
| `category` | `string` | - | Requirement category. |
| `compliance_status` | `string` | - | Compliance status. |
| `compliance_level` | `string` | - | compliance_level |
| `priority` | `string` | - | Priority level. |
| `is_applicable` | `boolean` | - | Whether this requirement is applicable. Ignored when the framework has applicability_managed_by_risks enabled: applicability is then derived from linked risks. |
| `applicability_justification` | `string` | - | Applicability justification (HTML rich text) |
| `compliance_evidence` | `string` | - | Compliance evidence (HTML rich text) |
| `compliance_finding` | `string` | - | Finding (HTML rich text) |
| `target_date` | `string` | - | Target date for implementation (ISO 8601). |
| `status` | `string` | - | Requirement lifecycle status. |
| `framework_id` | `string` | yes | framework_id |
| `section_id` | `string` | - | section_id |
| `owner_id` | `string` | - | UUID of the requirement owner (user) |
| `linked_asset_ids` | `array` | - | Essential assets this requirement protects. |
| `linked_stakeholder_expectation_ids` | `array` | - | Stakeholder expectations satisfied by this requirement. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_requirement_mapping`

Create a new requirement mapping

Requires `compliance.mapping.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `source_requirement_id` | `string` | yes | source_requirement_id |
| `target_requirement_id` | `string` | yes | target_requirement_id |
| `mapping_type` | `string` | yes | Type of mapping between requirements. |
| `coverage_level` | `string` | - | Coverage level of the mapping. |
| `description` | `string` | - | Description (HTML rich text) |
| `justification` | `string` | - | Justification (HTML rich text) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_section`

Create a new section

Requires `compliance.section.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `reference` | `string` | - | Section reference / number within the framework (e.g. 'A.5', '6.1.2'). Auto-generated as SEC-N if omitted; unique per framework when non-empty. |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `order` | `string` | - | order |
| `framework_id` | `string` | yes | framework_id |
| `parent_section_id` | `string` | - | parent_section_id |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `delete_action_plan`

Delete a action plan

Requires `compliance.action_plan.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_assessment_result`

Delete an assessment result

Requires `compliance.assessment.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_compliance_assessment`

Delete a compliance assessment

Requires `compliance.assessment.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_finding`

Delete a finding

Requires `compliance.finding.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_framework`

Delete a framework

Requires `compliance.framework.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_requirement`

Delete a requirement

Requires `compliance.requirement.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_requirement_mapping`

Delete a requirement mapping

Requires `compliance.mapping.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_section`

Delete a section

Requires `compliance.section.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `framework_allowed_transitions`

List the lifecycle transitions the caller may perform on a framework from its current state.

Requires `compliance.framework.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_action_plan`

Get a action plan by ID

Requires `compliance.action_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_action_plan_history`

Return the change history of a action plan: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `compliance.action_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the action plan |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_assessment_result`

Get an assessment result by ID

Requires `compliance.assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_compliance_assessment`

Get a compliance assessment by ID

Requires `compliance.assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_finding`

Get a finding by ID

Requires `compliance.finding.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_framework`

Get a framework by ID

Requires `compliance.framework.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_framework_compliance_summary`

Get compliance summary for a framework, including section-level compliance and status distribution

Requires `compliance.framework.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_framework_history`

Return the change history of a framework: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `compliance.framework.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the framework |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_requirement`

Get a requirement by ID

Requires `compliance.requirement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_requirement_history`

Return the change history of a requirement: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `compliance.requirement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the requirement |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_requirement_mapping`

Get a requirement mapping by ID

Requires `compliance.mapping.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_requirement_mapping_history`

Return the change history of a requirement mapping: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `compliance.mapping.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the requirement mapping |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_section`

Get a section by ID

Requires `compliance.section.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_section_history`

Return the change history of a section: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `compliance.section.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the section |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `list_action_plan_comments`

List comments on an action plan with threaded replies

Requires `compliance.action_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `action_plan_id` | `string` | yes | UUID of the action plan |

## `list_action_plans`

List action plans with optional search and filters

Requires `compliance.action_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `status` | `string` | - | Filter by status |
| `priority` | `string` | - | Filter by priority |

## `list_assessment_results`

List assessment results with optional search and filters

Requires `compliance.assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `requirement_id` | `string` | - | Filter by requirement_id |
| `compliance_status` | `string` | - | Filter by compliance_status |

## `list_compliance_assessments`

List compliance assessments with optional search and filters

Requires `compliance.assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `status` | `string` | - | Filter by status |

## `list_findings`

List findings with optional search and filters

Requires `compliance.finding.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `finding_type` | `string` | - | Filter by finding_type |
| `source` | `string` | - | Filter by source |
| `effectiveness_verdict` | `string` | - | Filter by effectiveness_verdict |

## `list_frameworks`

List frameworks with optional search and filters

Requires `compliance.framework.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `category` | `string` | - | Filter by category |
| `status` | `string` | - | Filter by status |
| `is_mandatory` | `string` | - | Filter by is_mandatory |
| `is_applicable` | `string` | - | Filter by is_applicable |
| `applicability_managed_by_risks` | `string` | - | Filter by applicability_managed_by_risks |

## `list_requirement_mappings`

List requirement mappings with optional search and filters

Requires `compliance.mapping.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `source_requirement_id` | `string` | - | Filter by source_requirement_id |
| `target_requirement_id` | `string` | - | Filter by target_requirement_id |
| `mapping_type` | `string` | - | Filter by mapping_type |

## `list_requirement_risks`

List all risks linked to a compliance requirement. Returns risk id, reference, name, current_risk_level, priority and status for each linked risk.

Requires `compliance.requirement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `requirement_id` | `string` | yes | UUID of the requirement |

## `list_requirements`

List requirements with optional search and filters

Requires `compliance.requirement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `framework_id` | `string` | - | Filter by framework_id |
| `section_id` | `string` | - | Filter by section_id |
| `requirement_number` | `string` | - | Filter by requirement_number |
| `compliance_status` | `string` | - | Filter by compliance_status |
| `type` | `string` | - | Filter by type |
| `category` | `string` | - | Filter by category |
| `priority` | `string` | - | Filter by priority |
| `is_applicable` | `string` | - | Filter by is_applicable |
| `status` | `string` | - | Filter by status |

## `list_sections`

List sections with optional search and filters

Requires `compliance.section.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `framework_id` | `string` | - | Filter by framework_id |
| `parent_section_id` | `string` | - | Filter by parent_section_id |

## `requirement_allowed_transitions`

List the lifecycle transitions the caller may perform on a requirement from its current state.

Requires `compliance.requirement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `semantic_search_requirements`

Find framework requirements / controls by MEANING using embeddings (language-agnostic). Use for conceptual / topic questions when an exact reference is not given. Read-only; requires the semantic index to be built (AI_ASSISTANT_SEMANTIC_ENABLED).

Requires `compliance.requirement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | `string` | yes | Topic or concept to search for |
| `limit` | `integer` | - | Max results (default 5, max 20) |

## `transition_action_plan`

Change the lifecycle state of a action plan (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `compliance.action_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the action plan |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_framework`

Change the lifecycle state of a framework (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `compliance.framework.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the framework |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_requirement`

Change the lifecycle state of a requirement (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `compliance.requirement.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the requirement |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `update_action_plan`

Update an existing action plan

Requires `compliance.action_plan.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `gap_description` | `string` | - | Gap description (HTML rich text) |
| `remediation_plan` | `string` | - | Remediation plan (HTML rich text) |
| `priority` | `string` | - | Priority level. |
| `start_date` | `string` | - | Start date (ISO 8601). |
| `target_date` | `string` | - | Target completion date (ISO 8601, e.g. 2025-12-31) |
| `completion_date` | `string` | - | Actual completion date (ISO 8601). Auto-set when transitioning to CLOSED. |
| `cost_estimate` | `number` | - | Estimated cost of the action plan. |
| `progress_percentage` | `integer` | - | Progress percentage (0-100) |
| `owner_id` | `string` | - | UUID of the action plan owner (user) |
| `originating_review_id` | `string` | - | UUID of the management review that spawned this plan (optional). |
| `scope_ids` | `array` | - | Scopes this plan applies to. |
| `assignee_ids` | `array` | - | UUIDs of assignees (users) for this plan. |
| `requirement_ids` | `array` | - | Compliance requirements this plan addresses. |
| `finding_ids` | `array` | - | Audit findings this plan addresses. |
| `risk_ids` | `array` | - | Risks this plan helps mitigate. |

## `update_assessment_result`

Update an existing assessment result

Requires `compliance.assessment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the result to update |
| `assessment_id` | `string` | - | assessment_id |
| `requirement_id` | `string` | - | requirement_id |
| `compliance_status` | `string` | - | Compliance status. Same 11-value enum as Requirement.compliance_status: the 5 conformance-oriented values (not_assessed, non_compliant, partially_compliant, compliant, not_applicable) plus the 6 audit-oriented values (evaluated, major_non_conformity, minor_non_conformity, observation, improvement_opportunity, strength). See docs/specs/m3-compliance/requirement.md for the audit -> conformance mapping used by RC-01 / RC-02 averages. |
| `compliance_level` | `string` | - | compliance_level |
| `finding` | `string` | - | Finding (HTML rich text) |
| `auditor_recommendations` | `string` | - | Auditor recommendations (HTML rich text) |
| `evidence` | `string` | - | Evidence (HTML rich text) |
| `assessed_by_id` | `string` | - | UUID of the assessor (user) |
| `assessed_at` | `string` | - | Assessment date-time in ISO 8601 format (e.g. 2025-01-15T10:30:00Z) |

## `update_compliance_assessment`

Update an existing compliance assessment

Requires `compliance.assessment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the assessment to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `limitations` | `string` | - | limitations |
| `assessment_start_date` | `string` | - | assessment_start_date |
| `assessment_end_date` | `string` | - | assessment_end_date |
| `status` | `string` | - | status |
| `assessor_id` | `string` | - | assessor_id |
| `framework_ids` | `array` | - | List of framework UUIDs to link (replaces existing links) |
| `scope_ids` | `array` | - | List of scope UUIDs (replaces existing scopes). |

## `update_finding`

Update an existing audit finding

Requires `compliance.finding.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the finding to update |
| `assessment_id` | `string` | - | assessment_id |
| `source` | `string` | - | What surfaced the nonconformity. 'audit' additionally requires assessment_id and assessor_id. |
| `finding_type` | `string` | - | Type of finding. Allowed values: major_nc (Major non-conformity, ref NCMAJ-x), minor_nc (Minor non-conformity, ref NCMIN-x), observation (Observation, ref OBS-x), improvement (Improvement opportunity, ref OA-x), strength (Strength, ref STR-x) |
| `description` | `string` | - | Finding description (HTML rich text) |
| `recommendation` | `string` | - | Recommendation (HTML rich text) |
| `evidence` | `string` | - | Evidence presented (HTML rich text) |
| `assessor_id` | `string` | - | UUID of the user who raised the nonconformity. Required when source is 'audit', optional otherwise. |
| `effectiveness_reviewed_at` | `string` | - | effectiveness_reviewed_at |
| `effectiveness_reviewed_by_id` | `string` | - | effectiveness_reviewed_by_id |
| `effectiveness_verdict` | `string` | - | ISO 27001 clause 10.2 d) : whether the corrective action worked. Requires effectiveness_reviewed_at. |
| `requirement_ids` | `array` | - | List of requirement UUIDs to link (replaces existing links) |

## `update_framework`

Update an existing framework

Requires `compliance.framework.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `short_name` | `string` | - | short_name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Framework type. |
| `category` | `string` | - | Framework category. |
| `framework_version` | `string` | - | Version of the framework (e.g. '2022'). |
| `publication_date` | `string` | - | Publication date (ISO 8601). |
| `effective_date` | `string` | - | Effective date (ISO 8601). |
| `expiry_date` | `string` | - | Expiry date (ISO 8601). |
| `issuing_body` | `string` | - | Standards body or regulator that issued the framework. |
| `jurisdiction` | `string` | - | Jurisdiction the framework applies to. |
| `url` | `string` | - | Official link to the framework. |
| `is_mandatory` | `boolean` | - | Whether the framework is mandatory (drives RC-05 non-compliance alert). |
| `is_applicable` | `boolean` | - | Whether the framework applies to the organisation (drives Statement of Applicability inclusion). |
| `applicability_justification` | `string` | - | Applicability justification (HTML rich text) |
| `applicability_managed_by_risks` | `boolean` | - | When true, each requirement's applicability is derived automatically from its linked risks: applicable when at least one active (reportable) risk is linked, not applicable otherwise. The requirement fields is_applicable / applicability_justification then become read-only (writes are ignored). |
| `status` | `string` | - | Framework status. |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `owner_id` | `string` | - | UUID of the framework owner (user) |
| `logo` | `string` | - | logo |
| `scope_ids` | `array` | - | Scopes this framework applies to (RG-01). |
| `related_stakeholder_ids` | `array` | - | Stakeholders interested in this framework. |

## `update_requirement`

Update an existing requirement

Requires `compliance.requirement.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `requirement_number` | `string` | - | requirement_number |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `guidance` | `string` | - | Implementation recommendations (HTML rich text) |
| `type` | `string` | - | Requirement type. |
| `category` | `string` | - | Requirement category. |
| `compliance_status` | `string` | - | Compliance status. |
| `compliance_level` | `string` | - | compliance_level |
| `priority` | `string` | - | Priority level. |
| `is_applicable` | `boolean` | - | Whether this requirement is applicable. Ignored when the framework has applicability_managed_by_risks enabled: applicability is then derived from linked risks. |
| `applicability_justification` | `string` | - | Applicability justification (HTML rich text) |
| `compliance_evidence` | `string` | - | Compliance evidence (HTML rich text) |
| `compliance_finding` | `string` | - | Finding (HTML rich text) |
| `target_date` | `string` | - | Target date for implementation (ISO 8601). |
| `status` | `string` | - | Requirement lifecycle status. |
| `framework_id` | `string` | - | framework_id |
| `section_id` | `string` | - | section_id |
| `owner_id` | `string` | - | UUID of the requirement owner (user) |
| `linked_asset_ids` | `array` | - | Essential assets this requirement protects. |
| `linked_stakeholder_expectation_ids` | `array` | - | Stakeholder expectations satisfied by this requirement. |

## `update_requirement_mapping`

Update an existing requirement mapping

Requires `compliance.mapping.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `source_requirement_id` | `string` | - | source_requirement_id |
| `target_requirement_id` | `string` | - | target_requirement_id |
| `mapping_type` | `string` | - | Type of mapping between requirements. |
| `coverage_level` | `string` | - | Coverage level of the mapping. |
| `description` | `string` | - | Description (HTML rich text) |
| `justification` | `string` | - | Justification (HTML rich text) |

## `update_section`

Update an existing section

Requires `compliance.section.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `reference` | `string` | - | Section reference / number within the framework (e.g. 'A.5', '6.1.2'). Auto-generated as SEC-N if omitted; unique per framework when non-empty. |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `order` | `string` | - | order |
| `framework_id` | `string` | - | framework_id |
| `parent_section_id` | `string` | - | parent_section_id |

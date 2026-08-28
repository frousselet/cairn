<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : Governance and context

Input schemas for the 126 `context` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `activity_allowed_transitions`

List the lifecycle transitions the caller may perform on a activity from its current state.

Requires `context.activity.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `batch_create_activitys`

Create or upsert multiple activitys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.activity.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of activity objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_expectations`

Create or upsert multiple expectations in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.expectation.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of expectation objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_indicator_measurements`

Create or upsert multiple indicator measurements in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.indicator.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of indicator measurement objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_indicators`

Create or upsert multiple indicators in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.indicator.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of indicator objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_issues`

Create or upsert multiple issues in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.issue.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of issue objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_objectives`

Create or upsert multiple objectives in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.objective.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of objective objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_responsibilitys`

Create or upsert multiple responsibilitys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.role.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of responsibility objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_roles`

Create or upsert multiple roles in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.role.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of role objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_scopes`

Create or upsert multiple scopes in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.scope.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of scope objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_sites`

Create or upsert multiple sites in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.site.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of site objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_stakeholders`

Create or upsert multiple stakeholders in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.stakeholder.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of stakeholder objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_swot_analysiss`

Create or upsert multiple swot analysiss in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.swot.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of swot analysis objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_swot_items`

Create or upsert multiple swot items in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.swot.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of swot item objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_swot_strategys`

Create or upsert multiple swot strategys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `context.swot.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of swot strategy objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `create_activity`

Create a new activity

Requires `context.activity.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | yes | Activity type. |
| `criticality` | `string` | yes | Criticality level. |
| `owner_id` | `string` | yes | UUID of the activity owner (user) |
| `status` | `string` | - | Activity status. |
| `parent_activity_id` | `string` | - | Parent activity UUID (must share at least one scope). |
| `scope_ids` | `array` | - | List of scope UUIDs this activity belongs to (RG-01). |
| `related_stakeholder_ids` | `array` | - | Stakeholders involved in this activity. |
| `related_objective_ids` | `array` | - | Objectives this activity contributes to. |
| `linked_essential_asset_ids` | `array` | - | Essential assets supporting this activity (uses the reverse manager of EssentialAsset.related_activities). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_expectation`

Create a new expectation

Requires `context.expectation.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `description` | `string` | yes | Description (HTML rich text) |
| `type` | `string` | yes | Expectation type. |
| `priority` | `string` | yes | Priority level. |
| `stakeholder_id` | `string` | yes | stakeholder_id |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_indicator`

Create a new indicator

Requires `context.indicator.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `indicator_type` | `string` | yes | Indicator type. |
| `collection_method` | `string` | - | Data collection method. |
| `format` | `string` | yes | Indicator format. |
| `unit` | `string` | - | unit |
| `expected_level` | `string` | - | expected_level |
| `critical_threshold_operator` | `string` | - | Critical threshold operator. |
| `critical_threshold_value` | `string` | - | critical_threshold_value |
| `critical_threshold_min` | `string` | - | critical_threshold_min |
| `critical_threshold_max` | `string` | - | critical_threshold_max |
| `review_frequency` | `string` | yes | Review frequency. |
| `first_review_date` | `string` | yes | First review date (ISO 8601, e.g. 2026-06-30). Required. |
| `status` | `string` | - | Indicator status. |
| `is_internal` | `boolean` | - | Whether this is an internal predefined indicator. |
| `internal_source` | `string` | - | Predefined indicator source (only for internal indicators). |
| `internal_source_parameter` | `string` | - | internal_source_parameter |
| `owner_id` | `string` | - | UUID of the user accountable for measuring and reviewing this indicator. |
| `scope_ids` | `array` | - | Scopes this indicator belongs to. |
| `linked_objective_ids` | `array` | - | Objectives this indicator measures progress against (ISO 27001 §6.2 / §9.1). |
| `linked_requirement_ids` | `array` | - | Compliance requirements this indicator measures the satisfaction of. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_indicator_measurement`

Create a new indicator measurement

Requires `context.indicator.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `indicator_id` | `string` | yes | UUID of the indicator this measurement belongs to (required). |
| `value` | `string` | yes | Measured value (number or boolean as string). |
| `recorded_at` | `string` | - | Measurement timestamp (ISO 8601). Defaults to the current time if omitted; backdate historical measurements by passing an earlier datetime. |
| `recorded_by_id` | `string` | - | UUID of the user recording the measurement. |
| `notes` | `string` | - | Free-form notes. |

## `create_issue`

Create a new issue

Requires `context.issue.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | yes | Issue type. |
| `category` | `string` | yes | Issue category. |
| `impact_level` | `string` | yes | Impact level. |
| `trend` | `string` | - | Issue trend over time. |
| `source` | `string` | - | Where the issue was identified (PESTEL workshop, audit, etc.). |
| `review_date` | `string` | - | Next review date (YYYY-MM-DD). |
| `status` | `string` | - | Issue status. |
| `scope_ids` | `array` | - | List of scope UUIDs this issue belongs to (RG-01). |
| `related_stakeholder_ids` | `array` | - | List of stakeholder UUIDs related to this issue. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_objective`

Create a new objective

Requires `context.objective.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | yes | Objective category. |
| `type` | `string` | yes | Objective type. |
| `target_value` | `string` | - | Target value (free-form, e.g. '95%' or '< 30 days') |
| `current_value` | `string` | - | Current value (free-form, same format as target_value) |
| `unit` | `string` | - | Unit of measure (e.g. '%', 'days') |
| `measurement_method` | `string` | - | How the objective is measured. |
| `measurement_frequency` | `string` | - | How often the objective is measured. |
| `status` | `string` | - | Objective status. To set 'achieved' you must also pass progress_percentage=100. |
| `progress_percentage` | `integer` | - | Progress percentage (0-100). Required to be 100 when status=achieved. |
| `target_date` | `string` | - | Target date (ISO 8601, e.g. 2025-12-31) |
| `owner_id` | `string` | yes | UUID of the objective owner (user) |
| `parent_objective_id` | `string` | - | Parent objective UUID (for objective hierarchies). |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `scope_ids` | `array` | - | List of scope UUIDs this objective belongs to (RG-01). |
| `related_issue_ids` | `array` | - | List of issue UUIDs addressed by this objective. |
| `related_stakeholder_ids` | `array` | - | List of stakeholder UUIDs related to this objective. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_responsibility`

Create a new responsibility

Requires `context.role.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `role_id` | `string` | yes | role_id |
| `description` | `string` | yes | Description (HTML rich text) |
| `raci_type` | `string` | yes | RACI responsibility type. |
| `related_activity_id` | `string` | - | related_activity_id |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_role`

Create a new role

Requires `context.role.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | yes | Role type. |
| `is_mandatory` | `boolean` | - | Whether this role is mandatory (enables the 'mandatory role without assigned user' compliance alert). |
| `source_standard` | `string` | - | Standard or regulation that requires this role (e.g. 'ISO 27001:2022 §5.3'). |
| `status` | `string` | - | Role status. |
| `scope_ids` | `array` | - | List of scope UUIDs this role belongs to (RG-01). |
| `assigned_user_ids` | `array` | - | UUIDs of users assigned to this role. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_scope`

Create a new scope

Requires `context.scope.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `icon` | `string` | - | Bootstrap Icons class (e.g. bi-building, bi-globe). |
| `boundaries` | `string` | - | Boundaries and exclusions (HTML rich text) |
| `justification_exclusions` | `string` | - | Justification for exclusions (HTML rich text) |
| `geographic_scope` | `string` | - | Geographic scope (HTML rich text) |
| `organizational_scope` | `string` | - | Organizational scope (HTML rich text) |
| `technical_scope` | `string` | - | Technical scope (HTML rich text) |
| `effective_date` | `string` | - | Effective date (ISO 8601, e.g. 2025-01-15) |
| `review_date` | `string` | - | Review date (ISO 8601, e.g. 2025-06-15) |
| `parent_scope_id` | `string` | - | UUID of the parent scope (for nested perimeters). |
| `manager_ids` | `array` | - | List of user UUIDs to assign as scope managers. |
| `included_site_ids` | `array` | - | Sites explicitly included in this scope. |
| `excluded_site_ids` | `array` | - | Sites explicitly excluded from this scope. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_site`

Create a new site

Requires `context.site.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Site type. |
| `address` | `string` | - | address |
| `parent_site_id` | `string` | - | UUID of the parent site (for site hierarchies). Cycles are rejected. |
| `scope_ids` | `array` | - | Scopes this site belongs to. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_stakeholder`

Create a new stakeholder

Requires `context.stakeholder.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | yes | Stakeholder type. |
| `category` | `string` | yes | Stakeholder category. |
| `contact_name` | `string` | - | contact_name |
| `contact_email` | `string` | - | contact_email |
| `contact_phone` | `string` | - | contact_phone |
| `influence_level` | `string` | yes | Influence level. |
| `interest_level` | `string` | yes | Interest level. |
| `review_date` | `string` | - | review_date |
| `status` | `string` | - | Stakeholder status. |
| `scope_ids` | `string` | - | scope_ids |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_stakeholder_feedback`

Record formal feedback from an interested party (ISO 27001:2022 clause 9.3.2.e).

Requires `context.stakeholder_feedback.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `stakeholder_id` | `string` | yes |  |
| `channel` | `string` | - | survey\|meeting\|complaint\|email\|audit\|incident\|other |
| `received_date` | `string` | yes |  |
| `subject` | `string` | yes |  |
| `content` | `string` | yes |  |
| `sentiment` | `string` | - |  |
| `severity` | `string` | - |  |
| `status` | `string` | - |  |
| `response` | `string` | - |  |
| `scope_ids` | `array` | - |  |

## `create_swot_analysis`

Create a new swot analysis

Requires `context.swot.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `analysis_date` | `string` | yes | Analysis date in ISO 8601 format (e.g. 2025-06-15) |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `scope_ids` | `array` | - | List of scope UUIDs this SWOT belongs to (RG-01). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_swot_item`

Create a new swot item

Requires `context.swot.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `quadrant` | `string` | yes | SWOT quadrant. |
| `description` | `string` | yes | Description (HTML rich text) |
| `impact_level` | `string` | - | Impact level. |
| `order` | `string` | - | order |
| `swot_analysis_id` | `string` | yes | UUID of the parent SWOT analysis |
| `related_issue_ids` | `array` | - | Issues this item connects to. |
| `related_objective_ids` | `array` | - | Objectives this item informs. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_swot_strategy`

Create a new swot strategy

Requires `context.swot.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `quadrant` | `string` | yes | Strategy quadrant. |
| `description` | `string` | yes | Description (HTML rich text) |
| `order` | `string` | - | order |
| `swot_analysis_id` | `string` | yes | UUID of the parent SWOT analysis |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_tag`

Create a tag

Requires `context.scope.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes |  |
| `color` | `string` | - |  |

## `delete_activity`

Delete a activity

Requires `context.activity.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_expectation`

Delete a expectation

Requires `context.expectation.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_indicator`

Delete a indicator

Requires `context.indicator.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_indicator_measurement`

Delete a indicator measurement

Requires `context.indicator.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_issue`

Delete a issue

Requires `context.issue.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_objective`

Delete a objective

Requires `context.objective.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_responsibility`

Delete a responsibility

Requires `context.role.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_role`

Delete a role

Requires `context.role.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_scope`

Delete a scope

Requires `context.scope.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_site`

Delete a site

Requires `context.site.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_stakeholder`

Delete a stakeholder

Requires `context.stakeholder.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_swot_analysis`

Delete a swot analysis

Requires `context.swot.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_swot_item`

Delete a swot item

Requires `context.swot.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_swot_strategy`

Delete a swot strategy

Requires `context.swot.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_tag`

Delete a tag

Requires `context.scope.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `expectation_allowed_transitions`

List the lifecycle transitions the caller may perform on a expectation from its current state.

Requires `context.expectation.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_activity`

Get a activity by ID

Requires `context.activity.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_activity_history`

Return the change history of a activity: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.activity.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the activity |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_expectation`

Get a expectation by ID

Requires `context.expectation.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_expectation_history`

Return the change history of a expectation: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.expectation.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the expectation |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_indicator`

Get a indicator by ID

Requires `context.indicator.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_indicator_history`

Return the change history of a indicator: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.indicator.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the indicator |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_indicator_measurement`

Get a indicator measurement by ID

Requires `context.indicator.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_issue`

Get a issue by ID

Requires `context.issue.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_issue_history`

Return the change history of a issue: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.issue.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the issue |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_objective`

Get a objective by ID

Requires `context.objective.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_objective_history`

Return the change history of a objective: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.objective.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the objective |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_responsibility`

Get a responsibility by ID

Requires `context.role.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_responsibility_history`

Return the change history of a responsibility: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.role.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the responsibility |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_role`

Get a role by ID

Requires `context.role.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_role_history`

Return the change history of a role: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.role.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the role |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_scope`

Get a scope by ID

Requires `context.scope.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_scope_history`

Return the change history of a scope: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.scope.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the scope |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_site`

Get a site by ID

Requires `context.site.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_site_history`

Return the change history of a site: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.site.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the site |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_stakeholder`

Get a stakeholder by ID

Requires `context.stakeholder.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_stakeholder_history`

Return the change history of a stakeholder: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.stakeholder.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the stakeholder |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_swot_analysis`

Get a swot analysis by ID

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_swot_analysis_history`

Return the change history of a swot analysis: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the swot analysis |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_swot_item`

Get a swot item by ID

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_swot_item_history`

Return the change history of a swot item: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the swot item |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_swot_strategy`

Get a swot strategy by ID

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_swot_strategy_history`

Return the change history of a swot strategy: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the swot strategy |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `indicator_allowed_transitions`

List the lifecycle transitions the caller may perform on a indicator from its current state.

Requires `context.indicator.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `issue_allowed_transitions`

List the lifecycle transitions the caller may perform on a issue from its current state.

Requires `context.issue.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `list_activitys`

List activitys with optional search and filters

Requires `context.activity.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `criticality` | `string` | - | Filter by criticality |
| `status` | `string` | - | Filter by status |

## `list_expectations`

List expectations with optional search and filters

Requires `context.expectation.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `stakeholder_id` | `string` | - | Filter by stakeholder_id |
| `type` | `string` | - | Filter by type |

## `list_indicator_measurements`

List indicator measurements with optional search and filters

Requires `context.indicator.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `indicator_id` | `string` | - | Filter by indicator_id |

## `list_indicators`

List indicators with optional search and filters

Requires `context.indicator.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `indicator_type` | `string` | - | Filter by indicator_type |
| `status` | `string` | - | Filter by status |
| `format` | `string` | - | Filter by format |
| `collection_method` | `string` | - | Filter by collection_method |

## `list_issues`

List issues with optional search and filters

Requires `context.issue.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `category` | `string` | - | Filter by category |
| `impact_level` | `string` | - | Filter by impact_level |
| `status` | `string` | - | Filter by status |

## `list_objectives`

List objectives with optional search and filters

Requires `context.objective.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `category` | `string` | - | Filter by category |
| `type` | `string` | - | Filter by type |
| `status` | `string` | - | Filter by status |

## `list_responsibilitys`

List responsibilitys with optional search and filters

Requires `context.role.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `role_id` | `string` | - | Filter by role_id |
| `raci_type` | `string` | - | Filter by raci_type |

## `list_roles`

List roles with optional search and filters

Requires `context.role.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `status` | `string` | - | Filter by status |

## `list_scopes`

List scopes with optional search and filters

Requires `context.scope.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `parent_scope_id` | `string` | - | Filter by parent_scope_id |

## `list_sites`

List sites with optional search and filters

Requires `context.site.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `parent_site_id` | `string` | - | Filter by parent_site_id |

## `list_stakeholder_feedback`

List formal stakeholder feedback (ISO 27001:2022 clause 9.3.2.e).

Requires `context.stakeholder_feedback.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `stakeholder_id` | `string` | - |  |
| `status` | `string` | - |  |
| `limit` | `integer` | - |  |
| `offset` | `integer` | - |  |

## `list_stakeholders`

List stakeholders with optional search and filters

Requires `context.stakeholder.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `category` | `string` | - | Filter by category |
| `status` | `string` | - | Filter by status |

## `list_swot_analysiss`

List swot analysiss with optional search and filters

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `workflow_state` | `string` | - | Filter by workflow_state |

## `list_swot_items`

List swot items with optional search and filters

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `swot_analysis_id` | `string` | - | Filter by swot_analysis_id |
| `quadrant` | `string` | - | Filter by quadrant |

## `list_swot_strategys`

List swot strategys with optional search and filters

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `swot_analysis_id` | `string` | - | Filter by swot_analysis_id |
| `quadrant` | `string` | - | Filter by quadrant |

## `list_tags`

List all tags

Requires `context.scope.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - |  |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `objective_allowed_transitions`

List the lifecycle transitions the caller may perform on a objective from its current state.

Requires `context.objective.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `role_allowed_transitions`

List the lifecycle transitions the caller may perform on a role from its current state.

Requires `context.role.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `scope_allowed_transitions`

List the lifecycle transitions the caller may perform on a scope from its current state.

Requires `context.scope.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `site_allowed_transitions`

List the lifecycle transitions the caller may perform on a site from its current state.

Requires `context.site.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `stakeholder_allowed_transitions`

List the lifecycle transitions the caller may perform on a stakeholder from its current state.

Requires `context.stakeholder.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `swot_analysis_allowed_transitions`

List the lifecycle transitions the caller may perform on a swot analysis from its current state.

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `swot_item_allowed_transitions`

List the lifecycle transitions the caller may perform on a swot item from its current state.

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `swot_strategy_allowed_transitions`

List the lifecycle transitions the caller may perform on a swot strategy from its current state.

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `transition_activity`

Change the lifecycle state of a activity (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.activity.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the activity |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_expectation`

Change the lifecycle state of a expectation (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.expectation.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the expectation |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_indicator`

Change the lifecycle state of a indicator (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.indicator.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the indicator |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_issue`

Change the lifecycle state of a issue (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.issue.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the issue |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_objective`

Change the lifecycle state of a objective (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.objective.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the objective |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_role`

Change the lifecycle state of a role (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.role.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the role |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_scope`

Change the lifecycle state of a scope (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.scope.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the scope |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_site`

Change the lifecycle state of a site (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.site.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the site |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_stakeholder`

Change the lifecycle state of a stakeholder (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.stakeholder.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the stakeholder |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_swot_analysis`

Change the lifecycle state of a swot analysis (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the swot analysis |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_swot_item`

Change the lifecycle state of a swot item (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the swot item |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_swot_strategy`

Change the lifecycle state of a swot strategy (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `context.swot.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the swot strategy |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `update_activity`

Update an existing activity

Requires `context.activity.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Activity type. |
| `criticality` | `string` | - | Criticality level. |
| `owner_id` | `string` | - | UUID of the activity owner (user) |
| `status` | `string` | - | Activity status. |
| `parent_activity_id` | `string` | - | Parent activity UUID (must share at least one scope). |
| `scope_ids` | `array` | - | List of scope UUIDs this activity belongs to (RG-01). |
| `related_stakeholder_ids` | `array` | - | Stakeholders involved in this activity. |
| `related_objective_ids` | `array` | - | Objectives this activity contributes to. |
| `linked_essential_asset_ids` | `array` | - | Essential assets supporting this activity (uses the reverse manager of EssentialAsset.related_activities). |

## `update_expectation`

Update an existing expectation

Requires `context.expectation.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Expectation type. |
| `priority` | `string` | - | Priority level. |
| `stakeholder_id` | `string` | - | stakeholder_id |

## `update_indicator`

Update an existing indicator

Requires `context.indicator.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `indicator_type` | `string` | - | Indicator type. |
| `collection_method` | `string` | - | Data collection method. |
| `format` | `string` | - | Indicator format. |
| `unit` | `string` | - | unit |
| `expected_level` | `string` | - | expected_level |
| `critical_threshold_operator` | `string` | - | Critical threshold operator. |
| `critical_threshold_value` | `string` | - | critical_threshold_value |
| `critical_threshold_min` | `string` | - | critical_threshold_min |
| `critical_threshold_max` | `string` | - | critical_threshold_max |
| `review_frequency` | `string` | - | Review frequency. |
| `first_review_date` | `string` | - | First review date (ISO 8601, e.g. 2026-06-30). Required. |
| `status` | `string` | - | Indicator status. |
| `is_internal` | `boolean` | - | Whether this is an internal predefined indicator. |
| `internal_source` | `string` | - | Predefined indicator source (only for internal indicators). |
| `internal_source_parameter` | `string` | - | internal_source_parameter |
| `owner_id` | `string` | - | UUID of the user accountable for measuring and reviewing this indicator. |
| `scope_ids` | `array` | - | Scopes this indicator belongs to. |
| `linked_objective_ids` | `array` | - | Objectives this indicator measures progress against (ISO 27001 §6.2 / §9.1). |
| `linked_requirement_ids` | `array` | - | Compliance requirements this indicator measures the satisfaction of. |

## `update_indicator_measurement`

Update an existing indicator measurement

Requires `context.indicator.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `indicator_id` | `string` | - | UUID of the indicator this measurement belongs to (required). |
| `value` | `string` | - | Measured value (number or boolean as string). |
| `recorded_at` | `string` | - | Measurement timestamp (ISO 8601). Defaults to the current time if omitted; backdate historical measurements by passing an earlier datetime. |
| `recorded_by_id` | `string` | - | UUID of the user recording the measurement. |
| `notes` | `string` | - | Free-form notes. |

## `update_issue`

Update an existing issue

Requires `context.issue.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Issue type. |
| `category` | `string` | - | Issue category. |
| `impact_level` | `string` | - | Impact level. |
| `trend` | `string` | - | Issue trend over time. |
| `source` | `string` | - | Where the issue was identified (PESTEL workshop, audit, etc.). |
| `review_date` | `string` | - | Next review date (YYYY-MM-DD). |
| `status` | `string` | - | Issue status. |
| `scope_ids` | `array` | - | List of scope UUIDs this issue belongs to (RG-01). |
| `related_stakeholder_ids` | `array` | - | List of stakeholder UUIDs related to this issue. |

## `update_objective`

Update an existing objective

Requires `context.objective.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | - | Objective category. |
| `type` | `string` | - | Objective type. |
| `target_value` | `string` | - | Target value (free-form, e.g. '95%' or '< 30 days') |
| `current_value` | `string` | - | Current value (free-form, same format as target_value) |
| `unit` | `string` | - | Unit of measure (e.g. '%', 'days') |
| `measurement_method` | `string` | - | How the objective is measured. |
| `measurement_frequency` | `string` | - | How often the objective is measured. |
| `status` | `string` | - | Objective status. To set 'achieved' you must also pass progress_percentage=100. |
| `progress_percentage` | `integer` | - | Progress percentage (0-100). Required to be 100 when status=achieved. |
| `target_date` | `string` | - | Target date (ISO 8601, e.g. 2025-12-31) |
| `owner_id` | `string` | - | UUID of the objective owner (user) |
| `parent_objective_id` | `string` | - | Parent objective UUID (for objective hierarchies). |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `scope_ids` | `array` | - | List of scope UUIDs this objective belongs to (RG-01). |
| `related_issue_ids` | `array` | - | List of issue UUIDs addressed by this objective. |
| `related_stakeholder_ids` | `array` | - | List of stakeholder UUIDs related to this objective. |

## `update_responsibility`

Update an existing responsibility

Requires `context.role.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `role_id` | `string` | - | role_id |
| `description` | `string` | - | Description (HTML rich text) |
| `raci_type` | `string` | - | RACI responsibility type. |
| `related_activity_id` | `string` | - | related_activity_id |

## `update_role`

Update an existing role

Requires `context.role.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Role type. |
| `is_mandatory` | `boolean` | - | Whether this role is mandatory (enables the 'mandatory role without assigned user' compliance alert). |
| `source_standard` | `string` | - | Standard or regulation that requires this role (e.g. 'ISO 27001:2022 §5.3'). |
| `status` | `string` | - | Role status. |
| `scope_ids` | `array` | - | List of scope UUIDs this role belongs to (RG-01). |
| `assigned_user_ids` | `array` | - | UUIDs of users assigned to this role. |

## `update_scope`

Update an existing scope

Requires `context.scope.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `icon` | `string` | - | Bootstrap Icons class (e.g. bi-building, bi-globe). |
| `boundaries` | `string` | - | Boundaries and exclusions (HTML rich text) |
| `justification_exclusions` | `string` | - | Justification for exclusions (HTML rich text) |
| `geographic_scope` | `string` | - | Geographic scope (HTML rich text) |
| `organizational_scope` | `string` | - | Organizational scope (HTML rich text) |
| `technical_scope` | `string` | - | Technical scope (HTML rich text) |
| `effective_date` | `string` | - | Effective date (ISO 8601, e.g. 2025-01-15) |
| `review_date` | `string` | - | Review date (ISO 8601, e.g. 2025-06-15) |
| `parent_scope_id` | `string` | - | UUID of the parent scope (for nested perimeters). |
| `manager_ids` | `array` | - | List of user UUIDs to assign as scope managers. |
| `included_site_ids` | `array` | - | Sites explicitly included in this scope. |
| `excluded_site_ids` | `array` | - | Sites explicitly excluded from this scope. |

## `update_site`

Update an existing site

Requires `context.site.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Site type. |
| `address` | `string` | - | address |
| `parent_site_id` | `string` | - | UUID of the parent site (for site hierarchies). Cycles are rejected. |
| `scope_ids` | `array` | - | Scopes this site belongs to. |

## `update_stakeholder`

Update an existing stakeholder

Requires `context.stakeholder.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Stakeholder type. |
| `category` | `string` | - | Stakeholder category. |
| `contact_name` | `string` | - | contact_name |
| `contact_email` | `string` | - | contact_email |
| `contact_phone` | `string` | - | contact_phone |
| `influence_level` | `string` | - | Influence level. |
| `interest_level` | `string` | - | Interest level. |
| `review_date` | `string` | - | review_date |
| `status` | `string` | - | Stakeholder status. |
| `scope_ids` | `string` | - | scope_ids |

## `update_swot_analysis`

Update an existing swot analysis

Requires `context.swot.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `analysis_date` | `string` | - | Analysis date in ISO 8601 format (e.g. 2025-06-15) |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `scope_ids` | `array` | - | List of scope UUIDs this SWOT belongs to (RG-01). |

## `update_swot_item`

Update an existing swot item

Requires `context.swot.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `quadrant` | `string` | - | SWOT quadrant. |
| `description` | `string` | - | Description (HTML rich text) |
| `impact_level` | `string` | - | Impact level. |
| `order` | `string` | - | order |
| `swot_analysis_id` | `string` | - | UUID of the parent SWOT analysis |
| `related_issue_ids` | `array` | - | Issues this item connects to. |
| `related_objective_ids` | `array` | - | Objectives this item informs. |

## `update_swot_strategy`

Update an existing swot strategy

Requires `context.swot.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `quadrant` | `string` | - | Strategy quadrant. |
| `description` | `string` | - | Description (HTML rich text) |
| `order` | `string` | - | order |
| `swot_analysis_id` | `string` | - | UUID of the parent SWOT analysis |

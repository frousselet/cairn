<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : Assets

Input schemas for the 136 `assets` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `asset_dependency_allowed_transitions`

List the lifecycle transitions the caller may perform on a asset dependency from its current state.

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `asset_group_allowed_transitions`

List the lifecycle transitions the caller may perform on a asset group from its current state.

Requires `assets.group.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `batch_create_asset_dependencys`

Create or upsert multiple asset dependencys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.dependency.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of asset dependency objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_asset_groups`

Create or upsert multiple asset groups in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.group.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of asset group objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_asset_valuations`

Create or upsert multiple asset valuations in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.essential_asset.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of asset valuation objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_certificates`

Create or upsert multiple certificates in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.certificate.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of certificate objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_contracts`

Create or upsert multiple contracts in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.contract.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of contract objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_essential_assets`

Create or upsert multiple essential assets in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.essential_asset.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of essential asset objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_site_asset_dependencys`

Create or upsert multiple site asset dependencys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.dependency.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of site asset dependency objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_site_supplier_dependencys`

Create or upsert multiple site supplier dependencys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.supplier_dependency.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of site supplier dependency objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_supplier_contacts`

Create or upsert multiple supplier contacts in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of supplier contact objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_supplier_dependencys`

Create or upsert multiple supplier dependencys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.supplier_dependency.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of supplier dependency objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_supplier_requirement_reviews`

Create or upsert multiple supplier requirement reviews in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of supplier requirement review objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_supplier_requirements`

Create or upsert multiple supplier requirements in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of supplier requirement objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_supplier_subprocessors`

Create or upsert multiple supplier subprocessors in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of supplier subprocessor objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_supplier_type_requirements`

Create or upsert multiple supplier type requirements in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.config.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of supplier type requirement objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_supplier_types`

Create or upsert multiple supplier types in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.config.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of supplier type objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_suppliers`

Create or upsert multiple suppliers in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of supplier objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_support_assets`

Create or upsert multiple support assets in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `assets.support_asset.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of support asset objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `certificate_allowed_transitions`

List the lifecycle transitions the caller may perform on a certificate from its current state.

Requires `assets.certificate.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `contract_allowed_transitions`

List the lifecycle transitions the caller may perform on a contract from its current state.

Requires `assets.contract.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `create_asset_dependency`

Create a new asset dependency

Requires `assets.dependency.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `essential_asset_id` | `string` | yes | essential_asset_id |
| `support_asset_id` | `string` | yes | support_asset_id |
| `dependency_type` | `string` | yes | Type of dependency between essential and support asset. |
| `criticality` | `string` | yes | Criticality level. |
| `redundancy_level` | `string` | - | Redundancy level for this dependency. |
| `description` | `string` | - | Description (HTML rich text) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_asset_group`

Create a new asset group

Requires `assets.group.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | yes | Asset group type (matches SupportAsset.type). |
| `status` | `string` | - | Asset group status. |
| `owner_id` | `string` | - | UUID of the group owner (user) |
| `scope_ids` | `array` | - | Scopes this asset group belongs to (RG-01). |
| `member_ids` | `array` | - | UUIDs of support assets to include in this group. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_asset_valuation`

Create a new asset valuation

Requires `assets.essential_asset.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `essential_asset_id` | `string` | yes | essential_asset_id |
| `evaluation_date` | `string` | - | Evaluation date (ISO 8601, e.g. 2025-01-15) |
| `confidentiality_level` | `integer` | - | Confidentiality level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical). |
| `integrity_level` | `integer` | - | Integrity level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical). |
| `availability_level` | `integer` | - | Availability level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical). |
| `evaluated_by_id` | `string` | - | UUID of the evaluator (user) |
| `justification` | `string` | - | Justification (HTML rich text) |
| `context` | `string` | - | Context (HTML rich text) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_certificate`

Create a new certificate

Requires `assets.certificate.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `label` | `string` | - | label |
| `status` | `string` | - | Certificate lifecycle status. |
| `certificate_number` | `string` | - | Official certificate number from the certification body. |
| `issuer` | `string` | - | Certification body that issued the certificate (e.g. AFNOR, BSI). |
| `issue_date` | `string` | - | Issue date (YYYY-MM-DD). |
| `expiry_date` | `string` | - | Expiry date (YYYY-MM-DD). |
| `scope_statement` | `string` | - | Perimeter covered by the certificate (free text). |
| `notes` | `string` | - | Notes (HTML rich text) |
| `framework_id` | `string` | yes | UUID of the framework (référentiel) this certificate attests compliance to (use list_frameworks). Required. |
| `supersedes_id` | `string` | - | UUID of the previous certificate this one renews and replaces. |
| `scope_ids` | `array` | yes | Scopes this certificate belongs to (RG-01). At least one is required. |
| `site_ids` | `array` | - | UUIDs of sites covered by the certified perimeter (use list_sites). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_contract`

Create a new contract

Requires `assets.contract.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `label` | `string` | - | label |
| `status` | `string` | - | Contract status. |
| `start_date` | `string` | - | Start date (YYYY-MM-DD). |
| `end_date` | `string` | - | End date (YYYY-MM-DD). |
| `amount` | `number` | - | Contract value. |
| `currency` | `string` | - | ISO 4217 currency code (e.g. EUR). |
| `notes` | `string` | - | Notes (HTML rich text) |
| `parent_id` | `string` | - | UUID of the contract this one amends (avenant); omit for a top-level contract. |
| `supersedes_id` | `string` | - | UUID of the contract or amendment this one cancels and replaces. |
| `scope_ids` | `array` | yes | Scopes this contract belongs to (RG-01). At least one is required. |
| `supplier_ids` | `array` | - | UUIDs of supplier parties (use list_suppliers). |
| `client_ids` | `array` | - | UUIDs of client parties: customer stakeholders (use list_stakeholders). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_essential_asset`

Create a new essential asset

Requires `assets.essential_asset.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | yes | Essential asset type. |
| `category` | `string` | yes | Essential asset category. |
| `status` | `string` | - | Essential asset status. |
| `confidentiality_level` | `['integer', 'string']` | - | Confidentiality level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2. |
| `integrity_level` | `['integer', 'string']` | - | Integrity level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2. |
| `availability_level` | `['integer', 'string']` | - | Availability level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2. |
| `confidentiality_justification` | `string` | - | Why this confidentiality level was chosen. |
| `integrity_justification` | `string` | - | Why this integrity level was chosen. |
| `availability_justification` | `string` | - | Why this availability level was chosen. |
| `max_tolerable_downtime` | `string` | - | Max tolerable downtime (MTD), free form e.g. '4 hours'. |
| `recovery_time_objective` | `string` | - | Recovery Time Objective (RTO), free form. |
| `recovery_point_objective` | `string` | - | Recovery Point Objective (RPO), free form. |
| `data_classification` | `string` | - | Data classification label. |
| `personal_data` | `boolean` | - | Whether this asset contains personal data. |
| `personal_data_categories` | `array` | - | GDPR categories of personal data (free-form list). |
| `regulatory_constraints` | `string` | - | Applicable regulatory constraints. |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `owner_id` | `string` | yes | UUID of the asset owner (user) |
| `custodian_id` | `string` | - | UUID of the asset custodian (user) |
| `scope_ids` | `array` | - | Scopes this asset belongs to (RG-01). |
| `related_activity_ids` | `array` | - | Business activities this asset supports. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_site_asset_dependency`

Create a new site asset dependency

Requires `assets.dependency.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `support_asset_id` | `string` | yes | support_asset_id |
| `site_id` | `string` | yes | site_id |
| `dependency_type` | `string` | yes | Type of site-asset dependency. |
| `criticality` | `string` | yes | Criticality level. |
| `description` | `string` | - | Description (HTML rich text) |
| `redundancy_level` | `string` | - | Redundancy level. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_site_supplier_dependency`

Create a new site supplier dependency

Requires `assets.supplier_dependency.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `site_id` | `string` | yes | site_id |
| `supplier_id` | `string` | yes | supplier_id |
| `dependency_type` | `string` | yes | Type of site-supplier dependency. |
| `criticality` | `string` | yes | Criticality level. |
| `description` | `string` | - | Description (HTML rich text) |
| `redundancy_level` | `string` | - | Redundancy level. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_supplier`

Create a new supplier. Optionally provide 'image_url' (a public URL pointing to an image file) to set the supplier logo. The image will be downloaded, resized to 128x128, and 64x64, 32x32, 16x16 variants will be generated automatically. Prefer 'image_url' over 'update_supplier_logo' when the logo is available as a URL.

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `integer` | - | ID of a SupplierType. Use list_supplier_types to get valid IDs. |
| `criticality` | `string` | - | Supplier criticality. |
| `parent_company_id` | `string` | - | UUID of the parent company (another supplier) this supplier is a subsidiary of. Use list_suppliers to get valid IDs. |
| `status` | `string` | - | Supplier status. |
| `contact_name` | `string` | - | contact_name |
| `contact_email` | `string` | - | contact_email |
| `contact_phone` | `string` | - | contact_phone |
| `website` | `string` | - | website |
| `address` | `string` | - | address |
| `country` | `string` | - | country |
| `latitude` | `number` | - | Latitude of the supplier address (WGS84). |
| `longitude` | `number` | - | Longitude of the supplier address (WGS84). |
| `contract_reference` | `string` | - | contract_reference |
| `contract_start_date` | `string` | - | contract_start_date |
| `contract_end_date` | `string` | - | contract_end_date |
| `next_review_date` | `string` | - | Date of the next scheduled supplier review (ISO 8601, YYYY-MM-DD). |
| `notes` | `string` | - | Notes (HTML rich text) |
| `owner_id` | `string` | - | UUID of the supplier owner (user) |
| `scope_ids` | `array` | - | Scopes this supplier belongs to (RG-01). |
| `image_url` | `string` | - | Public URL of an image to use as the supplier logo (PNG, JPG, WebP, etc.). The image is downloaded, resized to 128x128, and size variants are generated. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import. Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import. Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_supplier_contact`

Create a new supplier contact

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `supplier_id` | `string` | yes | supplier_id |
| `name` | `string` | yes | name |
| `profession` | `string` | - | profession |
| `service` | `string` | - | service |
| `email` | `string` | - | email |
| `phone` | `string` | - | phone |
| `role` | `string` | - | role |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_supplier_dependency`

Create a new supplier dependency

Requires `assets.supplier_dependency.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `support_asset_id` | `string` | yes | support_asset_id |
| `supplier_id` | `string` | yes | supplier_id |
| `dependency_type` | `string` | yes | Type of supplier dependency. |
| `criticality` | `string` | yes | Criticality level. |
| `description` | `string` | - | Description (HTML rich text) |
| `redundancy_level` | `string` | - | Redundancy level (operator-set). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_supplier_requirement`

Create a new supplier requirement

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `supplier_id` | `string` | yes | supplier_id |
| `source_type_requirement_id` | `string` | - | source_type_requirement_id |
| `requirement_id` | `string` | - | requirement_id |
| `title` | `string` | yes | title |
| `description` | `string` | - | Description (HTML rich text) |
| `compliance_status` | `string` | - | Compliance status of the supplier requirement. |
| `evidence` | `string` | - | Evidence (HTML rich text) |
| `due_date` | `string` | - | due_date |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_supplier_requirement_review`

Create a new supplier requirement review

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `supplier_requirement_id` | `string` | - | supplier_requirement_id |
| `review_date` | `string` | - | review_date |
| `reviewer_id` | `string` | - | reviewer_id |
| `result` | `string` | - | result |
| `comment` | `string` | - | Comment (HTML rich text) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_supplier_subprocessor`

Create a new supplier subprocessor

Requires `assets.supplier.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `supplier_id` | `string` | yes | UUID of the supplier (délégataire) engaging the sub-processor. Use list_suppliers to get valid IDs. |
| `subprocessor_id` | `string` | yes | UUID of the supplier engaged as a sub-processor (must differ from supplier_id). |
| `purpose` | `string` | - | purpose |
| `criticality` | `string` | - | Criticality of the sub-processing engagement. |
| `status` | `string` | - | Status of the sub-processing engagement. |
| `start_date` | `string` | - | start_date |
| `end_date` | `string` | - | end_date |
| `description` | `string` | - | Description (HTML rich text) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_supplier_type`

Create a new supplier type

Requires `assets.config.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_supplier_type_requirement`

Create a new supplier type requirement

Requires `assets.config.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `supplier_type_id` | `string` | - | supplier_type_id |
| `title` | `string` | - | title |
| `description` | `string` | - | Description (HTML rich text) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_support_asset`

Create a new support asset

Requires `assets.support_asset.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | yes | Support asset type. Physical locations live in `context.Site`, not here: the legacy `site` type was removed (migration assets.0029 converted existing rows to Site). |
| `category` | `string` | yes | Support asset category. Must match the type. Hardware: server, workstation, laptop, mobile_device, network_equipment, storage, peripheral, iot_device, removable_media, other_hardware. Software: operating_system, database, application, middleware, security_tool, development_tool, saas_application, other_software. Network: lan, wan, wifi, vpn, internet_link, firewall_zone, dmz, other_network. Person: internal_staff, contractor, external_provider, administrator, developer, other_person. Service: cloud_service, hosting_service, managed_service, telecom_service, outsourced_service, other_service. Paper: archive, printed_document, form, other_paper. |
| `status` | `string` | - | Support asset status. |
| `location` | `string` | - | Physical or logical location of the asset. |
| `manufacturer` | `string` | - | Manufacturer / vendor. |
| `model_name` | `string` | - | Model or version designation. |
| `serial_number` | `string` | - | Serial number. |
| `software_version` | `string` | - | Software version. |
| `operating_system` | `string` | - | Operating system. |
| `hostname` | `string` | - | hostname |
| `ip_address` | `string` | - | ip_address |
| `acquisition_date` | `string` | - | Acquisition date (ISO 8601). |
| `end_of_life_date` | `string` | - | End-of-life date (ISO 8601). |
| `warranty_expiry_date` | `string` | - | Warranty expiry (ISO 8601). |
| `contract_reference` | `string` | - | Procurement / support contract reference. |
| `exposure_level` | `string` | - | Exposure level (network reachability). |
| `environment` | `string` | - | Environment hosting this asset. |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `owner_id` | `string` | yes | UUID of the asset owner (user) |
| `custodian_id` | `string` | - | UUID of the asset custodian (user) |
| `supplier_id` | `string` | - | UUID of the supplier that provides / hosts / maintains this asset. |
| `parent_asset_id` | `string` | - | UUID of the parent support asset (must share at least one scope). |
| `scope_ids` | `array` | - | Scopes this asset belongs to (RG-01). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `delete_asset_dependency`

Delete a asset dependency

Requires `assets.dependency.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_asset_group`

Delete a asset group

Requires `assets.group.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_asset_valuation`

Delete a asset valuation

Requires `assets.essential_asset.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_certificate`

Delete a certificate

Requires `assets.certificate.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_contract`

Delete a contract

Requires `assets.contract.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_essential_asset`

Delete a essential asset

Requires `assets.essential_asset.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_site_asset_dependency`

Delete a site asset dependency

Requires `assets.dependency.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_site_supplier_dependency`

Delete a site supplier dependency

Requires `assets.supplier_dependency.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_supplier`

Delete a supplier

Requires `assets.supplier.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_supplier_contact`

Delete a supplier contact

Requires `assets.supplier.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_supplier_dependency`

Delete a supplier dependency

Requires `assets.supplier_dependency.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_supplier_requirement`

Delete a supplier requirement

Requires `assets.supplier.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_supplier_requirement_review`

Delete a supplier requirement review

Requires `assets.supplier.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_supplier_subprocessor`

Delete a supplier subprocessor

Requires `assets.supplier.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_supplier_type`

Delete a supplier type

Requires `assets.config.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_supplier_type_requirement`

Delete a supplier type requirement

Requires `assets.config.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_support_asset`

Delete a support asset

Requires `assets.support_asset.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `essential_asset_allowed_transitions`

List the lifecycle transitions the caller may perform on a essential asset from its current state.

Requires `assets.essential_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_asset_dependency`

Get a asset dependency by ID

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_asset_dependency_history`

Return the change history of a asset dependency: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the asset dependency |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_asset_group`

Get a asset group by ID

Requires `assets.group.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_asset_group_history`

Return the change history of a asset group: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.group.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the asset group |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_asset_valuation`

Get a asset valuation by ID

Requires `assets.essential_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_asset_valuation_history`

Return the change history of a asset valuation: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.essential_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the asset valuation |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_certificate`

Get a certificate by ID

Requires `assets.certificate.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_certificate_history`

Return the change history of a certificate: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.certificate.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the certificate |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_contract`

Get a contract by ID

Requires `assets.contract.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_contract_history`

Return the change history of a contract: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.contract.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the contract |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_essential_asset`

Get a essential asset by ID

Requires `assets.essential_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_essential_asset_history`

Return the change history of a essential asset: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.essential_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the essential asset |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_site_asset_dependency`

Get a site asset dependency by ID

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_site_asset_dependency_history`

Return the change history of a site asset dependency: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the site asset dependency |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_site_supplier_dependency`

Get a site supplier dependency by ID

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_site_supplier_dependency_history`

Return the change history of a site supplier dependency: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the site supplier dependency |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_supplier`

Get a supplier by ID

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_supplier_contact`

Get a supplier contact by ID

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_supplier_contact_history`

Return the change history of a supplier contact: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the supplier contact |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_supplier_dependency`

Get a supplier dependency by ID

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_supplier_dependency_history`

Return the change history of a supplier dependency: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the supplier dependency |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_supplier_history`

Return the change history of a supplier: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the supplier |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_supplier_requirement`

Get a supplier requirement by ID

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_supplier_requirement_review`

Get a supplier requirement review by ID

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_supplier_subprocessor`

Get a supplier subprocessor by ID

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_supplier_subprocessor_history`

Return the change history of a supplier subprocessor: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the supplier subprocessor |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_supplier_type`

Get a supplier type by ID

Requires `assets.config.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_supplier_type_requirement`

Get a supplier type requirement by ID

Requires `assets.config.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_support_asset`

Get a support asset by ID

Requires `assets.support_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_support_asset_history`

Return the change history of a support asset: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `assets.support_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the support asset |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `list_asset_dependencys`

List asset dependencys with optional search and filters

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `essential_asset_id` | `string` | - | Filter by essential_asset_id |
| `support_asset_id` | `string` | - | Filter by support_asset_id |
| `dependency_type` | `string` | - | Filter by dependency_type |
| `criticality` | `string` | - | Filter by criticality |

## `list_asset_groups`

List asset groups with optional search and filters

Requires `assets.group.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `status` | `string` | - | Filter by status |

## `list_asset_valuations`

List asset valuations with optional search and filters

Requires `assets.essential_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `essential_asset_id` | `string` | - | Filter by essential_asset_id |

## `list_certificates`

List certificates with optional search and filters

Requires `assets.certificate.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `status` | `string` | - | Filter by status |

## `list_contracts`

List contracts with optional search and filters

Requires `assets.contract.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `status` | `string` | - | Filter by status |

## `list_essential_assets`

List essential assets with optional search and filters

Requires `assets.essential_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `category` | `string` | - | Filter by category |
| `status` | `string` | - | Filter by status |

## `list_site_asset_dependencys`

List site asset dependencys with optional search and filters

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `support_asset_id` | `string` | - | Filter by support_asset_id |
| `site_id` | `string` | - | Filter by site_id |
| `dependency_type` | `string` | - | Filter by dependency_type |
| `criticality` | `string` | - | Filter by criticality |

## `list_site_supplier_dependencys`

List site supplier dependencys with optional search and filters

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `site_id` | `string` | - | Filter by site_id |
| `supplier_id` | `string` | - | Filter by supplier_id |
| `dependency_type` | `string` | - | Filter by dependency_type |
| `criticality` | `string` | - | Filter by criticality |

## `list_supplier_contacts`

List supplier contacts with optional search and filters

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `supplier_id` | `string` | - | Filter by supplier_id |
| `role` | `string` | - | Filter by role |

## `list_supplier_dependencys`

List supplier dependencys with optional search and filters

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `support_asset_id` | `string` | - | Filter by support_asset_id |
| `supplier_id` | `string` | - | Filter by supplier_id |
| `dependency_type` | `string` | - | Filter by dependency_type |
| `criticality` | `string` | - | Filter by criticality |

## `list_supplier_requirement_reviews`

List supplier requirement reviews with optional search and filters

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `supplier_requirement_id` | `string` | - | Filter by supplier_requirement_id |
| `result` | `string` | - | Filter by result |

## `list_supplier_requirements`

List supplier requirements with optional search and filters

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `supplier_id` | `string` | - | Filter by supplier_id |
| `compliance_status` | `string` | - | Filter by compliance_status |

## `list_supplier_subprocessors`

List supplier subprocessors with optional search and filters

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `supplier_id` | `string` | - | Filter by supplier_id |
| `subprocessor_id` | `string` | - | Filter by subprocessor_id |
| `criticality` | `string` | - | Filter by criticality |
| `status` | `string` | - | Filter by status |

## `list_supplier_type_requirements`

List supplier type requirements with optional search and filters

Requires `assets.config.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `supplier_type_id` | `string` | - | Filter by supplier_type_id |

## `list_supplier_types`

List supplier types with optional search and filters

Requires `assets.config.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `list_suppliers`

List suppliers with optional search and filters

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `criticality` | `string` | - | Filter by criticality |
| `status` | `string` | - | Filter by status |
| `expired` | `boolean` | - | If true, only suppliers whose contract has expired (active suppliers with a contract end date in the past). |

## `list_support_assets`

List support assets with optional search and filters

Requires `assets.support_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `category` | `string` | - | Filter by category |
| `status` | `string` | - | Filter by status |
| `environment` | `string` | - | Filter by environment |
| `exposure_level` | `string` | - | Filter by exposure_level |

## `site_asset_dependency_allowed_transitions`

List the lifecycle transitions the caller may perform on a site asset dependency from its current state.

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `site_supplier_dependency_allowed_transitions`

List the lifecycle transitions the caller may perform on a site supplier dependency from its current state.

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `supplier_allowed_transitions`

List the lifecycle transitions the caller may perform on a supplier from its current state.

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `supplier_dependency_allowed_transitions`

List the lifecycle transitions the caller may perform on a supplier dependency from its current state.

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `support_asset_allowed_transitions`

List the lifecycle transitions the caller may perform on a support asset from its current state.

Requires `assets.support_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `transition_asset_dependency`

Change the lifecycle state of a asset dependency (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the asset dependency |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_asset_group`

Change the lifecycle state of a asset group (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.group.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the asset group |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_certificate`

Change the lifecycle state of a certificate (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.certificate.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the certificate |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_contract`

Change the lifecycle state of a contract (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.contract.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the contract |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_essential_asset`

Change the lifecycle state of a essential asset (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.essential_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the essential asset |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_site_asset_dependency`

Change the lifecycle state of a site asset dependency (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the site asset dependency |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_site_supplier_dependency`

Change the lifecycle state of a site supplier dependency (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the site supplier dependency |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_supplier`

Change the lifecycle state of a supplier (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.supplier.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the supplier |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_supplier_dependency`

Change the lifecycle state of a supplier dependency (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.supplier_dependency.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the supplier dependency |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_support_asset`

Change the lifecycle state of a support asset (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `assets.support_asset.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the support asset |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `update_asset_dependency`

Update an existing asset dependency

Requires `assets.dependency.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `essential_asset_id` | `string` | - | essential_asset_id |
| `support_asset_id` | `string` | - | support_asset_id |
| `dependency_type` | `string` | - | Type of dependency between essential and support asset. |
| `criticality` | `string` | - | Criticality level. |
| `redundancy_level` | `string` | - | Redundancy level for this dependency. |
| `description` | `string` | - | Description (HTML rich text) |

## `update_asset_group`

Update an existing asset group

Requires `assets.group.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Asset group type (matches SupportAsset.type). |
| `status` | `string` | - | Asset group status. |
| `owner_id` | `string` | - | UUID of the group owner (user) |
| `scope_ids` | `array` | - | Scopes this asset group belongs to (RG-01). |
| `member_ids` | `array` | - | UUIDs of support assets to include in this group. |

## `update_asset_valuation`

Update an existing asset valuation

Requires `assets.essential_asset.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `essential_asset_id` | `string` | - | essential_asset_id |
| `evaluation_date` | `string` | - | Evaluation date (ISO 8601, e.g. 2025-01-15) |
| `confidentiality_level` | `integer` | - | Confidentiality level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical). |
| `integrity_level` | `integer` | - | Integrity level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical). |
| `availability_level` | `integer` | - | Availability level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical). |
| `evaluated_by_id` | `string` | - | UUID of the evaluator (user) |
| `justification` | `string` | - | Justification (HTML rich text) |
| `context` | `string` | - | Context (HTML rich text) |

## `update_certificate`

Update an existing certificate

Requires `assets.certificate.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `label` | `string` | - | label |
| `status` | `string` | - | Certificate lifecycle status. |
| `certificate_number` | `string` | - | Official certificate number from the certification body. |
| `issuer` | `string` | - | Certification body that issued the certificate (e.g. AFNOR, BSI). |
| `issue_date` | `string` | - | Issue date (YYYY-MM-DD). |
| `expiry_date` | `string` | - | Expiry date (YYYY-MM-DD). |
| `scope_statement` | `string` | - | Perimeter covered by the certificate (free text). |
| `notes` | `string` | - | Notes (HTML rich text) |
| `framework_id` | `string` | - | UUID of the framework (référentiel) this certificate attests compliance to (use list_frameworks). Required. |
| `supersedes_id` | `string` | - | UUID of the previous certificate this one renews and replaces. |
| `scope_ids` | `array` | - | Scopes this certificate belongs to (RG-01). At least one is required. |
| `site_ids` | `array` | - | UUIDs of sites covered by the certified perimeter (use list_sites). |

## `update_contract`

Update an existing contract

Requires `assets.contract.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `label` | `string` | - | label |
| `status` | `string` | - | Contract status. |
| `start_date` | `string` | - | Start date (YYYY-MM-DD). |
| `end_date` | `string` | - | End date (YYYY-MM-DD). |
| `amount` | `number` | - | Contract value. |
| `currency` | `string` | - | ISO 4217 currency code (e.g. EUR). |
| `notes` | `string` | - | Notes (HTML rich text) |
| `parent_id` | `string` | - | UUID of the contract this one amends (avenant); omit for a top-level contract. |
| `supersedes_id` | `string` | - | UUID of the contract or amendment this one cancels and replaces. |
| `scope_ids` | `array` | - | Scopes this contract belongs to (RG-01). At least one is required. |
| `supplier_ids` | `array` | - | UUIDs of supplier parties (use list_suppliers). |
| `client_ids` | `array` | - | UUIDs of client parties: customer stakeholders (use list_stakeholders). |

## `update_essential_asset`

Update an existing essential asset

Requires `assets.essential_asset.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Essential asset type. |
| `category` | `string` | - | Essential asset category. |
| `status` | `string` | - | Essential asset status. |
| `confidentiality_level` | `['integer', 'string']` | - | Confidentiality level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2. |
| `integrity_level` | `['integer', 'string']` | - | Integrity level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2. |
| `availability_level` | `['integer', 'string']` | - | Availability level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2. |
| `confidentiality_justification` | `string` | - | Why this confidentiality level was chosen. |
| `integrity_justification` | `string` | - | Why this integrity level was chosen. |
| `availability_justification` | `string` | - | Why this availability level was chosen. |
| `max_tolerable_downtime` | `string` | - | Max tolerable downtime (MTD), free form e.g. '4 hours'. |
| `recovery_time_objective` | `string` | - | Recovery Time Objective (RTO), free form. |
| `recovery_point_objective` | `string` | - | Recovery Point Objective (RPO), free form. |
| `data_classification` | `string` | - | Data classification label. |
| `personal_data` | `boolean` | - | Whether this asset contains personal data. |
| `personal_data_categories` | `array` | - | GDPR categories of personal data (free-form list). |
| `regulatory_constraints` | `string` | - | Applicable regulatory constraints. |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `owner_id` | `string` | - | UUID of the asset owner (user) |
| `custodian_id` | `string` | - | UUID of the asset custodian (user) |
| `scope_ids` | `array` | - | Scopes this asset belongs to (RG-01). |
| `related_activity_ids` | `array` | - | Business activities this asset supports. |

## `update_site_asset_dependency`

Update an existing site asset dependency

Requires `assets.dependency.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `support_asset_id` | `string` | - | support_asset_id |
| `site_id` | `string` | - | site_id |
| `dependency_type` | `string` | - | Type of site-asset dependency. |
| `criticality` | `string` | - | Criticality level. |
| `description` | `string` | - | Description (HTML rich text) |
| `redundancy_level` | `string` | - | Redundancy level. |

## `update_site_supplier_dependency`

Update an existing site supplier dependency

Requires `assets.supplier_dependency.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `site_id` | `string` | - | site_id |
| `supplier_id` | `string` | - | supplier_id |
| `dependency_type` | `string` | - | Type of site-supplier dependency. |
| `criticality` | `string` | - | Criticality level. |
| `description` | `string` | - | Description (HTML rich text) |
| `redundancy_level` | `string` | - | Redundancy level. |

## `update_supplier`

Update an existing supplier. Optionally provide 'image_url' (a public URL pointing to an image file) to set or replace the supplier logo. The image will be downloaded, resized to 128x128, and 64x64, 32x32, 16x16 variants will be generated automatically. Prefer 'image_url' over 'update_supplier_logo' when the logo is available as a URL.

Requires `assets.supplier.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `integer` | - | ID of a SupplierType. Use list_supplier_types to get valid IDs. |
| `criticality` | `string` | - | Supplier criticality. |
| `parent_company_id` | `string` | - | UUID of the parent company (another supplier) this supplier is a subsidiary of. Use list_suppliers to get valid IDs. |
| `status` | `string` | - | Supplier status. |
| `contact_name` | `string` | - | contact_name |
| `contact_email` | `string` | - | contact_email |
| `contact_phone` | `string` | - | contact_phone |
| `website` | `string` | - | website |
| `address` | `string` | - | address |
| `country` | `string` | - | country |
| `latitude` | `number` | - | Latitude of the supplier address (WGS84). |
| `longitude` | `number` | - | Longitude of the supplier address (WGS84). |
| `contract_reference` | `string` | - | contract_reference |
| `contract_start_date` | `string` | - | contract_start_date |
| `contract_end_date` | `string` | - | contract_end_date |
| `next_review_date` | `string` | - | Date of the next scheduled supplier review (ISO 8601, YYYY-MM-DD). |
| `notes` | `string` | - | Notes (HTML rich text) |
| `owner_id` | `string` | - | UUID of the supplier owner (user) |
| `scope_ids` | `array` | - | Scopes this supplier belongs to (RG-01). |
| `image_url` | `string` | - | Public URL of an image to use as the supplier logo (PNG, JPG, WebP, etc.). The image is downloaded, resized to 128x128, and size variants are generated. |

## `update_supplier_contact`

Update an existing supplier contact

Requires `assets.supplier.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `supplier_id` | `string` | - | supplier_id |
| `name` | `string` | - | name |
| `profession` | `string` | - | profession |
| `service` | `string` | - | service |
| `email` | `string` | - | email |
| `phone` | `string` | - | phone |
| `role` | `string` | - | role |

## `update_supplier_dependency`

Update an existing supplier dependency

Requires `assets.supplier_dependency.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `support_asset_id` | `string` | - | support_asset_id |
| `supplier_id` | `string` | - | supplier_id |
| `dependency_type` | `string` | - | Type of supplier dependency. |
| `criticality` | `string` | - | Criticality level. |
| `description` | `string` | - | Description (HTML rich text) |
| `redundancy_level` | `string` | - | Redundancy level (operator-set). |

## `update_supplier_logo`

Update a supplier's logo. Provide EITHER a base64 data URI via 'logo' OR a public image URL via 'image_url'. The image is resized to 128x128 and 64x64, 32x32, 16x16 variants are generated automatically.

Requires `assets.supplier.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the supplier |
| `logo` | `string` | - | Base64 data URI of the logo image (e.g. 'data:image/png;base64,...') |
| `image_url` | `string` | - | Public URL of an image to download as the logo |

## `update_supplier_requirement`

Update an existing supplier requirement

Requires `assets.supplier.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `supplier_id` | `string` | - | supplier_id |
| `source_type_requirement_id` | `string` | - | source_type_requirement_id |
| `requirement_id` | `string` | - | requirement_id |
| `title` | `string` | - | title |
| `description` | `string` | - | Description (HTML rich text) |
| `compliance_status` | `string` | - | Compliance status of the supplier requirement. |
| `evidence` | `string` | - | Evidence (HTML rich text) |
| `due_date` | `string` | - | due_date |

## `update_supplier_requirement_review`

Update an existing supplier requirement review

Requires `assets.supplier.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `supplier_requirement_id` | `string` | - | supplier_requirement_id |
| `review_date` | `string` | - | review_date |
| `reviewer_id` | `string` | - | reviewer_id |
| `result` | `string` | - | result |
| `comment` | `string` | - | Comment (HTML rich text) |

## `update_supplier_subprocessor`

Update an existing supplier subprocessor

Requires `assets.supplier.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `supplier_id` | `string` | - | UUID of the supplier (délégataire) engaging the sub-processor. Use list_suppliers to get valid IDs. |
| `subprocessor_id` | `string` | - | UUID of the supplier engaged as a sub-processor (must differ from supplier_id). |
| `purpose` | `string` | - | purpose |
| `criticality` | `string` | - | Criticality of the sub-processing engagement. |
| `status` | `string` | - | Status of the sub-processing engagement. |
| `start_date` | `string` | - | start_date |
| `end_date` | `string` | - | end_date |
| `description` | `string` | - | Description (HTML rich text) |

## `update_supplier_type`

Update an existing supplier type

Requires `assets.config.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |

## `update_supplier_type_requirement`

Update an existing supplier type requirement

Requires `assets.config.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `supplier_type_id` | `string` | - | supplier_type_id |
| `title` | `string` | - | title |
| `description` | `string` | - | Description (HTML rich text) |

## `update_support_asset`

Update an existing support asset

Requires `assets.support_asset.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Support asset type. Physical locations live in `context.Site`, not here: the legacy `site` type was removed (migration assets.0029 converted existing rows to Site). |
| `category` | `string` | - | Support asset category. Must match the type. Hardware: server, workstation, laptop, mobile_device, network_equipment, storage, peripheral, iot_device, removable_media, other_hardware. Software: operating_system, database, application, middleware, security_tool, development_tool, saas_application, other_software. Network: lan, wan, wifi, vpn, internet_link, firewall_zone, dmz, other_network. Person: internal_staff, contractor, external_provider, administrator, developer, other_person. Service: cloud_service, hosting_service, managed_service, telecom_service, outsourced_service, other_service. Paper: archive, printed_document, form, other_paper. |
| `status` | `string` | - | Support asset status. |
| `location` | `string` | - | Physical or logical location of the asset. |
| `manufacturer` | `string` | - | Manufacturer / vendor. |
| `model_name` | `string` | - | Model or version designation. |
| `serial_number` | `string` | - | Serial number. |
| `software_version` | `string` | - | Software version. |
| `operating_system` | `string` | - | Operating system. |
| `hostname` | `string` | - | hostname |
| `ip_address` | `string` | - | ip_address |
| `acquisition_date` | `string` | - | Acquisition date (ISO 8601). |
| `end_of_life_date` | `string` | - | End-of-life date (ISO 8601). |
| `warranty_expiry_date` | `string` | - | Warranty expiry (ISO 8601). |
| `contract_reference` | `string` | - | Procurement / support contract reference. |
| `exposure_level` | `string` | - | Exposure level (network reachability). |
| `environment` | `string` | - | Environment hosting this asset. |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `owner_id` | `string` | - | UUID of the asset owner (user) |
| `custodian_id` | `string` | - | UUID of the asset custodian (user) |
| `supplier_id` | `string` | - | UUID of the supplier that provides / hosts / maintains this asset. |
| `parent_asset_id` | `string` | - | UUID of the parent support asset (must share at least one scope). |
| `scope_ids` | `array` | - | Scopes this asset belongs to (RG-01). |

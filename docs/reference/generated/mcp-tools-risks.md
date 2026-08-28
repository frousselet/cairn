<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : Risks

Input schemas for the 222 `risks` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `batch_create_ebios_attack_path_steps`

Create or upsert multiple ebios attack path steps in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_strategic.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios attack path step objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_attack_techniques`

Create or upsert multiple ebios attack techniques in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_operational.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios attack technique objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_baseline_gaps`

Create or upsert multiple ebios baseline gaps in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_baseline.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios baseline gap objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_ecosystem_stakeholders`

Create or upsert multiple ebios ecosystem stakeholders in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_ecosystem.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios ecosystem stakeholder objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_feared_events`

Create or upsert multiple ebios feared events in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_baseline.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios feared event objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_operational_scenarios`

Create or upsert multiple ebios operational scenarios in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_operational.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios operational scenario objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_pacs_measures`

Create or upsert multiple ebios pacs measures in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_summary.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios pacs measure objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_risk_sources`

Create or upsert multiple ebios risk sources in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_risk_source.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios risk source objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_security_baselines`

Create or upsert multiple ebios security baselines in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_baseline.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios security baseline objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_sr_ov_pairs`

Create or upsert multiple ebios sr ov pairs in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_risk_source.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios sr ov pair objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_strategic_scenarios`

Create or upsert multiple ebios strategic scenarios in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_strategic.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios strategic scenario objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_study_frameworks`

Create or upsert multiple ebios study frameworks in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_assessment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios study framework objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_summarys`

Create or upsert multiple ebios summarys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_summary.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios summary objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_targeted_objectives`

Create or upsert multiple ebios targeted objectives in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_risk_source.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios targeted objective objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_ebios_workshops`

Create or upsert multiple ebios workshops in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.ebios_assessment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of ebios workshop objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_iso27005_risks`

Create or upsert multiple iso27005 risks in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.iso27005.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of iso27005 risk objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_risk_acceptances`

Create or upsert multiple risk acceptances in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.acceptance.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of risk acceptance objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_risk_assessments`

Create or upsert multiple risk assessments in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.assessment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of risk assessment objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_risk_criterias`

Create or upsert multiple risk criterias in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.criteria.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of risk criteria objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_risk_levels`

Create or upsert multiple risk levels in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.criteria.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of risk level objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_risk_treatment_plans`

Create or upsert multiple risk treatment plans in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.treatment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of risk treatment plan objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_risks`

Create or upsert multiple risks in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.risk.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of risk objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_scale_levels`

Create or upsert multiple scale levels in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.criteria.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of scale level objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_threats`

Create or upsert multiple threats in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.threat.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of threat objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_treatment_actions`

Create or upsert multiple treatment actions in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.treatment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of treatment action objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_vulnerabilitys`

Create or upsert multiple vulnerabilitys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `risks.vulnerability.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of vulnerability objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `capture_ebios_risk_mappings`

Snapshot the assessment's risk register into the EbiosSummary before / after JSON slots so the cartography can render the treatment effect. Pass capture_before / capture_after to scope the update; both default to true.

Requires `risks.ebios_summary.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the EbiosSummary to update. |
| `capture_before` | `string` | - | Update risk_mapping_before (default true). |
| `capture_after` | `string` | - | Update risk_mapping_after (default true). |

## `consolidate_ebios_operational_scenario_to_risk`

Materialise an EBIOS operational scenario into a Risk in the unified register. Idempotent: returns the existing Risk if the scenario has already been consolidated.

Requires `risks.risk.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `consolidate_iso27005_risk`

Materialise an ISO 27005 analysis (threat × vulnerability) into a Risk in the unified register. Idempotent: returns the existing Risk if the analysis has already been consolidated. The source link is preserved via source_entity_id / source_entity_type on the resulting Risk.

Requires `risks.risk.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `create_ebios_attack_path_step`

Create a new ebios attack path step

Requires `risks.ebios_strategic.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `scenario_id` | `string` | yes | scenario_id |
| `order` | `integer` | - | Position of the step in the attack path (unique per scenario). |
| `stakeholder_id` | `string` | - | stakeholder_id |
| `description` | `string` | yes | Description (HTML rich text) |
| `action_type` | `string` | - | Action type: initial_access, reconnaissance, lateral_movement, privilege_escalation, data_exfiltration, disruption, manipulation, persistence, other. |
| `difficulty` | `string` | - | Difficulty: trivial, easy, moderate, difficult, very_difficult. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_attack_technique`

Create a new ebios attack technique

Requires `risks.ebios_operational.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `scenario_id` | `string` | yes | scenario_id |
| `order` | `integer` | - | Position of the technique in the operational sequence (unique per scenario). |
| `mitre_technique_id` | `string` | - | mitre_technique_id |
| `custom_name` | `string` | - | custom_name |
| `description` | `string` | yes | Description (HTML rich text) |
| `targeted_support_asset_id` | `string` | - | targeted_support_asset_id |
| `difficulty` | `string` | - | Difficulty: trivial, easy, moderate, difficult, very_difficult. |
| `detection_difficulty` | `string` | - | Detection difficulty: trivial, easy, moderate, difficult, very_difficult. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_baseline_gap`

Create a new ebios baseline gap

Requires `risks.ebios_baseline.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `baseline_id` | `string` | yes | baseline_id |
| `reference_source` | `string` | yes | reference_source |
| `linked_requirement_id` | `string` | - | linked_requirement_id |
| `description` | `string` | yes | Description (HTML rich text) |
| `severity` | `string` | - | Severity: low, medium, high, critical. |
| `recommended_remediation` | `string` | - | Recommended remediation (HTML rich text) |
| `status` | `string` | - | Gap status: identified, accepted, in_remediation, remediated. |
| `order` | `string` | - | order |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_ecosystem_stakeholder`

Create a new ebios ecosystem stakeholder

Requires `risks.ebios_ecosystem.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | assessment_id |
| `stakeholder_id` | `string` | - | stakeholder_id |
| `supplier_id` | `string` | - | supplier_id |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | - | Ecosystem category: supplier, partner, subcontractor, customer, regulator, shared_infrastructure, client_employee, other. |
| `dependency` | `integer` | - | Organisation dependency on the stakeholder (1..4). Numerator in (D*P)/(M*T). |
| `penetration` | `integer` | - | Stakeholder penetration into the ecosystem (1..4). Numerator in (D*P)/(M*T). |
| `maturity` | `integer` | - | Stakeholder cyber maturity (1..4). Denominator in (D*P)/(M*T). |
| `trust` | `integer` | - | Trust placed in the stakeholder (1..4). Denominator in (D*P)/(M*T). |
| `is_attack_vector` | `string` | - | is_attack_vector |
| `attack_vector_justification` | `string` | - | Attack vector justification (HTML rich text) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_feared_event`

Create a new ebios feared event

Requires `risks.ebios_baseline.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `baseline_id` | `string` | yes | baseline_id |
| `essential_asset_id` | `string` | yes | essential_asset_id |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `dic_criterion` | `string` | yes | DIC criterion impaired: confidentiality, integrity, availability. |
| `gravity_level` | `integer` | - | Gravity level on the assessment impact scale (e.g. 1-4 or 1-5). |
| `gravity_justification` | `string` | - | Gravity justification (HTML rich text) |
| `business_impacts` | `object` | - | Optional business impact breakdown. Accepts a JSON object with keys such as financial, legal, reputation, operational, human, environmental. |
| `order` | `string` | - | order |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_operational_scenario`

Create a new ebios operational scenario

Requires `risks.ebios_operational.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | assessment_id |
| `strategic_scenario_id` | `string` | yes | strategic_scenario_id |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `gravity_level` | `string` | - | gravity_level |
| `gravity_inherited` | `string` | - | true when gravity_level is inherited from the parent strategic scenario; set to false and supply gravity_override_justification to override. |
| `gravity_override_justification` | `string` | - | Gravity override justification (HTML rich text) |
| `likelihood_v` | `integer` | - | ANSSI operational likelihood V1..V4 stored as integer 1..4 (M4bis Annex B). |
| `likelihood_justification` | `string` | - | Likelihood justification (HTML rich text) |
| `existing_controls` | `string` | - | Existing controls (HTML rich text) |
| `mitre_version` | `string` | - | mitre_version |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_pacs_measure`

Create a new ebios pacs measure

Requires `risks.ebios_summary.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `summary_id` | `string` | yes | summary_id |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `measure_type` | `string` | - | PACS measure type: governance, protection, defense, resilience, awareness. |
| `owner_id` | `string` | - | owner_id |
| `start_date` | `string` | - | start_date |
| `target_date` | `string` | - | target_date |
| `completion_date` | `string` | - | completion_date |
| `cost_estimate` | `string` | - | cost_estimate |
| `expected_gain` | `string` | - | Expected gain (HTML rich text) |
| `priority` | `string` | - | Priority: low, medium, high, critical. |
| `status` | `string` | - | Status: planned, in_progress, completed, cancelled, overdue. |
| `progress_percentage` | `integer` | - | Progress in percent (0 to 100). |
| `order` | `string` | - | order |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_risk_source`

Create a new ebios risk source

Requires `risks.ebios_risk_source.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | assessment_id |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | - | ANSSI risk source category: state, organized_crime, terrorist, activist, competitor, employee, service_provider, amateur, natural, other. |
| `motivation_level` | `integer` | - | 1 (low) to 4 (very strong). Drives the ANSSI threat level Grid A. |
| `motivation_description` | `string` | - | Motivation description (HTML rich text) |
| `resources_level` | `integer` | - | 1 (limited) to 4 (unlimited). Drives the ANSSI threat level Grid A. |
| `activity_level` | `integer` | - | Observed activity 1 to 4. Activity >= 3 majorates the threat level by one (capped at V4). |
| `is_retained` | `string` | - | is_retained |
| `retention_justification` | `string` | - | Retention justification (HTML rich text) |
| `is_from_catalog` | `string` | - | is_from_catalog |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_security_baseline`

Create a new ebios security baseline

Requires `risks.ebios_baseline.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | assessment_id |
| `dic_summary` | `string` | - | DIC needs summary (HTML rich text) |
| `status` | `string` | - | Baseline status: draft, in_progress, completed. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_sr_ov_pair`

Create a new ebios sr ov pair

Requires `risks.ebios_risk_source.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | assessment_id |
| `risk_source_id` | `string` | yes | risk_source_id |
| `targeted_objective_id` | `string` | yes | targeted_objective_id |
| `relevance` | `string` | - | SR/OV relevance: low, medium, high, critical. Combined with risk_source.threat_level to produce priority_score. |
| `relevance_justification` | `string` | - | Relevance justification (HTML rich text) |
| `is_retained` | `string` | - | is_retained |
| `retention_justification` | `string` | - | Retention justification (HTML rich text) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_strategic_scenario`

Create a new ebios strategic scenario

Requires `risks.ebios_strategic.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | assessment_id |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `sr_ov_pair_id` | `string` | yes | sr_ov_pair_id |
| `gravity_level` | `integer` | - | Gravity on the assessment impact scale. Combined with likelihood via the matrix to compute risk_level. |
| `gravity_justification` | `string` | - | Gravity justification (HTML rich text) |
| `likelihood_level` | `integer` | - | Likelihood on the assessment likelihood scale. Combined with gravity via the matrix to compute risk_level. |
| `likelihood_justification` | `string` | - | Likelihood justification (HTML rich text) |
| `existing_security_measures` | `string` | - | Existing security measures (HTML rich text) |
| `is_retained` | `string` | - | is_retained |
| `retention_justification` | `string` | - | retention_justification |
| `consolidated_risk_id` | `string` | - | consolidated_risk_id |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_study_framework`

Create a new ebios study framework

Requires `risks.ebios_assessment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | assessment_id |
| `mission_statement` | `string` | - | Mission statement (HTML rich text) |
| `business_perimeter` | `string` | - | Business perimeter (HTML rich text) |
| `technical_perimeter` | `string` | - | Technical perimeter (HTML rich text) |
| `temporal_perimeter` | `string` | - | temporal_perimeter |
| `financial_envelope` | `string` | - | financial_envelope |
| `assumptions` | `string` | - | assumptions |
| `constraints` | `string` | - | constraints |
| `expected_deliverables` | `string` | - | expected_deliverables |
| `status` | `string` | - | Study framework status: draft, validated. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_summary`

Create a new ebios summary

Requires `risks.ebios_summary.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | assessment_id |
| `residual_risk_strategy` | `string` | - | Residual risk strategy (HTML rich text) |
| `monitoring_plan` | `string` | - | Monitoring plan (HTML rich text) |
| `pacs_summary` | `string` | - | PACS summary (HTML rich text) |
| `next_strategic_cycle_date` | `string` | - | next_strategic_cycle_date |
| `next_operational_cycle_date` | `string` | - | next_operational_cycle_date |
| `status` | `string` | - | Summary status: draft, in_progress, under_review, validated. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_targeted_objective`

Create a new ebios targeted objective

Requires `risks.ebios_risk_source.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `risk_source_id` | `string` | yes | risk_source_id |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | - | ANSSI objective category: lucrative, strategic, terrorist, ideological, revenge, ludic, other. |
| `is_retained` | `string` | - | is_retained |
| `order` | `string` | - | order |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_ebios_workshop`

Create a new ebios workshop

Requires `risks.ebios_assessment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | assessment_id |
| `workshop_number` | `integer` | yes | Workshop number 0..5 (0=study framework, 1=baseline, 5=treatment). |
| `iteration_type` | `string` | - | Iteration type: strategic (annual) or operational (semestrial). |
| `iteration_number` | `integer` | - | Iteration number (starts at 1). |
| `status` | `string` | - | Workshop status: not_started, in_progress, under_review, validated, rejected. |
| `started_at` | `string` | - | started_at |
| `deliverables_summary` | `string` | - | deliverables_summary |
| `notes` | `string` | - | notes |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_iso27005_risk`

Create a new iso27005 risk

Requires `risks.iso27005.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | - | assessment_id |
| `threat_id` | `string` | - | threat_id |
| `vulnerability_id` | `string` | - | vulnerability_id |
| `threat_likelihood` | `integer` | - | Threat likelihood level (integer matching a scale level, e.g. 1-5). combined_likelihood is auto-computed as max(threat_likelihood, vulnerability_exposure). |
| `vulnerability_exposure` | `integer` | - | Vulnerability exposure level (integer matching a scale level, e.g. 1-5). combined_likelihood is auto-computed as max(threat_likelihood, vulnerability_exposure). |
| `impact_confidentiality` | `integer` | - | Confidentiality impact level (integer matching a scale level, e.g. 1-5). |
| `impact_integrity` | `integer` | - | Integrity impact level (integer matching a scale level, e.g. 1-5). |
| `impact_availability` | `integer` | - | Availability impact level (integer matching a scale level, e.g. 1-5). |
| `existing_controls` | `string` | - | Existing controls (HTML rich text) |
| `risk_id` | `string` | - | risk_id |
| `description` | `string` | - | Description (HTML rich text) |
| `affected_essential_asset_ids` | `array` | - | Essential assets impacted by this triplet. |
| `affected_support_asset_ids` | `array` | - | Support assets impacted by this triplet. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_risk`

Create a new risk

Requires `risks.risk.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `status` | `string` | - | Risk status. |
| `priority` | `string` | - | Risk priority. |
| `risk_source` | `string` | - | How this risk entered the register (manual, consolidated from an analysis, etc.). |
| `source_entity_id` | `string` | - | UUID of the source entity (ISO 27005 analysis, EBIOS scenario, ...) when risk_source is not 'manual'. |
| `source_entity_type` | `string` | - | Class name of the source entity (e.g. 'ISO27005Risk', 'OperationalScenario'). |
| `initial_likelihood` | `integer` | - | Initial likelihood level (matching scale levels, e.g. 1-5) |
| `initial_impact` | `integer` | - | Initial impact level (matching scale levels, e.g. 1-5) |
| `current_likelihood` | `integer` | - | Current likelihood level (matching scale levels, e.g. 1-5) |
| `current_impact` | `integer` | - | Current impact level (matching scale levels, e.g. 1-5) |
| `residual_likelihood` | `integer` | - | Residual likelihood level (matching scale levels, e.g. 1-5) |
| `residual_impact` | `integer` | - | Residual impact level (matching scale levels, e.g. 1-5) |
| `impact_confidentiality` | `boolean` | - | Whether this risk impacts confidentiality. |
| `impact_integrity` | `boolean` | - | Whether this risk impacts integrity. |
| `impact_availability` | `boolean` | - | Whether this risk impacts availability. |
| `treatment_decision` | `string` | - | Treatment decision. |
| `treatment_justification` | `string` | - | Treatment justification (HTML rich text) |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `assessment_id` | `string` | yes | assessment_id |
| `risk_owner_id` | `string` | - | UUID of the risk owner (user) |
| `affected_essential_asset_ids` | `array` | - | Essential assets affected by this risk. |
| `affected_support_asset_ids` | `array` | - | Support assets affected by this risk. |
| `linked_requirement_ids` | `array` | - | Compliance requirements linked to this risk. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_risk_acceptance`

Create a new risk acceptance

Requires `risks.acceptance.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `risk_id` | `string` | yes | risk_id |
| `justification` | `string` | yes | Justification (HTML rich text) |
| `conditions` | `string` | - | Conditions (HTML rich text) |
| `valid_until` | `string` | - | Last day the acceptance remains in force (ISO 8601). |
| `review_date` | `string` | - | Date the acceptance should be reviewed (ISO 8601). |
| `accepted_by_id` | `string` | - | UUID of the user who accepted the risk |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_risk_assessment`

Create a new risk assessment

Requires `risks.assessment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `methodology` | `string` | - | Risk assessment methodology. Default: iso27005. |
| `status` | `string` | - | Risk assessment status. |
| `assessment_date` | `string` | - | Assessment date (ISO 8601, e.g. 2025-06-15) |
| `next_review_date` | `string` | - | Next review date (ISO 8601). |
| `risk_criteria_id` | `string` | - | UUID of the risk criteria to use |
| `assessor_id` | `string` | - | UUID of the assessor (user) |
| `summary` | `string` | - | Summary (HTML rich text) |
| `scope_ids` | `array` | - | Scopes this assessment covers (RG-01). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_risk_criteria`

Create a new risk criteria

Requires `risks.criteria.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `risk_matrix` | `object` | - | Risk matrix as JSON object mapping 'likelihood,impact' to risk level. Example for a 5x5 matrix: {"1,1": 1, "1,2": 2, ..., "5,5": 5}. Can be omitted - the matrix will be auto-built from scale levels and risk levels via rebuild_risk_matrix(). |
| `acceptance_threshold` | `integer` | - | Risk level at or below which risks are automatically acceptable (default 0). |
| `is_default` | `boolean` | - | Whether this is the default risk criteria. |
| `scope_ids` | `array` | - | Scopes these criteria apply to (RG-01). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_risk_level`

Create a new risk level

Requires `risks.criteria.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `criteria_id` | `string` | yes | UUID of the parent RiskCriteria. |
| `level` | `integer` | yes | Numeric risk level (e.g. 1-5). Must be unique per criteria. |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `color` | `string` | - | Color hex code (e.g. #ff0000) |
| `requires_treatment` | `boolean` | - | Whether this risk level requires treatment. |

## `create_risk_treatment_plan`

Create a new risk treatment plan

Requires `risks.treatment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | name |
| `description` | `string` | - | Description (HTML rich text) |
| `treatment_type` | `string` | - | Treatment strategy type. |
| `status` | `string` | - | Treatment plan status. |
| `expected_residual_likelihood` | `integer` | - | Expected residual likelihood (matching scale levels, e.g. 1-5) |
| `expected_residual_impact` | `integer` | - | Expected residual impact (matching scale levels, e.g. 1-5) |
| `cost_estimate` | `string` | - | cost_estimate |
| `start_date` | `string` | - | start_date |
| `target_date` | `string` | - | target_date |
| `completion_date` | `string` | - | completion_date |
| `progress_percentage` | `string` | - | progress_percentage |
| `risk_id` | `string` | yes | risk_id |
| `owner_id` | `string` | - | UUID of the treatment plan owner (user) |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_scale_level`

Create a new scale level

Requires `risks.criteria.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `criteria_id` | `string` | - | UUID of the parent RiskCriteria. |
| `scale_type` | `string` | - | Type of scale. |
| `level` | `integer` | - | Numeric level (e.g. 1-5). Must be unique per criteria + scale_type. |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `color` | `string` | - | color |

## `create_threat`

Create a new threat

Requires `risks.threat.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Threat type. |
| `origin` | `string` | - | Threat origin. |
| `category` | `string` | - | Threat category. |
| `typical_likelihood` | `integer` | - | Typical likelihood level (integer, e.g. 1-5). |
| `is_from_catalog` | `boolean` | - | Whether this threat comes from a predefined ISO 27005 catalog. |
| `status` | `string` | - | Threat status. |
| `scope_ids` | `array` | - | Scopes this threat applies to (RG-01). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_treatment_action`

Create a new treatment action

Requires `risks.treatment.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `treatment_plan_id` | `string` | yes | treatment_plan_id |
| `description` | `string` | yes | Description (HTML rich text) |
| `owner_id` | `string` | - | UUID of the action owner (user) |
| `target_date` | `string` | - | target_date |
| `completion_date` | `string` | - | completion_date |
| `status` | `string` | - | Action status. |
| `order` | `string` | - | order |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_vulnerability`

Create a new vulnerability

Requires `risks.vulnerability.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | - | Vulnerability category. |
| `severity` | `string` | - | Vulnerability severity. |
| `status` | `string` | - | Vulnerability status. |
| `affected_asset_types` | `array` | - | Support asset types this vulnerability affects (free-form list). |
| `cve_references` | `array` | - | List of CVE identifiers (e.g. 'CVE-2024-1234'). |
| `is_from_catalog` | `boolean` | - | Whether this vulnerability comes from a predefined catalog. |
| `remediation_guidance` | `string` | - | Remediation guidance (HTML rich text) |
| `scope_ids` | `array` | - | Scopes this vulnerability applies to (RG-01). |
| `affected_asset_ids` | `array` | - | UUIDs of support assets affected by this vulnerability. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `delete_ebios_attack_path_step`

Delete a ebios attack path step

Requires `risks.ebios_strategic.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_attack_technique`

Delete a ebios attack technique

Requires `risks.ebios_operational.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_baseline_gap`

Delete a ebios baseline gap

Requires `risks.ebios_baseline.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_ecosystem_stakeholder`

Delete a ebios ecosystem stakeholder

Requires `risks.ebios_ecosystem.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_feared_event`

Delete a ebios feared event

Requires `risks.ebios_baseline.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_operational_scenario`

Delete a ebios operational scenario

Requires `risks.ebios_operational.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_pacs_measure`

Delete a ebios pacs measure

Requires `risks.ebios_summary.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_risk_source`

Delete a ebios risk source

Requires `risks.ebios_risk_source.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_security_baseline`

Delete a ebios security baseline

Requires `risks.ebios_baseline.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_sr_ov_pair`

Delete a ebios sr ov pair

Requires `risks.ebios_risk_source.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_strategic_scenario`

Delete a ebios strategic scenario

Requires `risks.ebios_strategic.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_study_framework`

Delete a ebios study framework

Requires `risks.ebios_assessment.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_summary`

Delete a ebios summary

Requires `risks.ebios_summary.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_targeted_objective`

Delete a ebios targeted objective

Requires `risks.ebios_risk_source.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_ebios_workshop`

Delete a ebios workshop

Requires `risks.ebios_assessment.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_iso27005_risk`

Delete a iso27005 risk

Requires `risks.iso27005.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_risk`

Delete a risk

Requires `risks.risk.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_risk_acceptance`

Delete a risk acceptance

Requires `risks.acceptance.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_risk_assessment`

Delete a risk assessment

Requires `risks.assessment.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_risk_criteria`

Delete a risk criteria

Requires `risks.criteria.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_risk_level`

Delete a risk level

Requires `risks.criteria.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_risk_treatment_plan`

Delete a risk treatment plan

Requires `risks.treatment.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_scale_level`

Delete a scale level

Requires `risks.criteria.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_threat`

Delete a threat

Requires `risks.threat.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_treatment_action`

Delete a treatment action

Requires `risks.treatment.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_vulnerability`

Delete a vulnerability

Requires `risks.vulnerability.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `ebios_ecosystem_stakeholder_allowed_transitions`

List the lifecycle transitions the caller may perform on a ebios ecosystem stakeholder from its current state.

Requires `risks.ebios_ecosystem.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `ebios_operational_scenario_allowed_transitions`

List the lifecycle transitions the caller may perform on a ebios operational scenario from its current state.

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `ebios_risk_source_allowed_transitions`

List the lifecycle transitions the caller may perform on a ebios risk source from its current state.

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `ebios_security_baseline_allowed_transitions`

List the lifecycle transitions the caller may perform on a ebios security baseline from its current state.

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `ebios_sr_ov_pair_allowed_transitions`

List the lifecycle transitions the caller may perform on a ebios sr ov pair from its current state.

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `ebios_strategic_scenario_allowed_transitions`

List the lifecycle transitions the caller may perform on a ebios strategic scenario from its current state.

Requires `risks.ebios_strategic.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `ebios_summary_allowed_transitions`

List the lifecycle transitions the caller may perform on a ebios summary from its current state.

Requires `risks.ebios_summary.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `generate_iso27005_report`

Generate an ISO 27005 risk assessment DOCX report for a single assessment. The report covers context, criteria, threats, vulnerabilities, analyses, consolidated risks, treatment plans and acceptances. Persisted as a Report.

Requires `risks.export.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `assessment_id` | `string` | yes | UUID of the RiskAssessment to export. |

## `generate_risk_register`

Generate an Excel (.xlsx) export of the risk register. Optional filters: scope_ids, assessment_id, status, priority. When omitted, scope filtering falls back to the user's allowed scopes. The generated file is persisted as a Report.

Requires `risks.export.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `scope_ids` | `array` | - | Restrict to risks under these scope UUIDs. |
| `assessment_id` | `string` | - | Restrict to risks under this assessment UUID. |
| `status` | `string` | - | Filter by risk status. |
| `priority` | `string` | - | Filter by risk priority. |

## `get_ebios_attack_path_step`

Get a ebios attack path step by ID

Requires `risks.ebios_strategic.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_attack_path_step_history`

Return the change history of a ebios attack path step: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_strategic.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios attack path step |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_attack_technique`

Get a ebios attack technique by ID

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_attack_technique_history`

Return the change history of a ebios attack technique: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios attack technique |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_baseline_gap`

Get a ebios baseline gap by ID

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_baseline_gap_history`

Return the change history of a ebios baseline gap: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios baseline gap |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_ecosystem_stakeholder`

Get a ebios ecosystem stakeholder by ID

Requires `risks.ebios_ecosystem.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_ecosystem_stakeholder_history`

Return the change history of a ebios ecosystem stakeholder: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_ecosystem.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios ecosystem stakeholder |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_feared_event`

Get a ebios feared event by ID

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_feared_event_history`

Return the change history of a ebios feared event: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios feared event |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_operational_scenario`

Get a ebios operational scenario by ID

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_operational_scenario_history`

Return the change history of a ebios operational scenario: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios operational scenario |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_pacs_measure`

Get a ebios pacs measure by ID

Requires `risks.ebios_summary.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_pacs_measure_history`

Return the change history of a ebios pacs measure: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_summary.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios pacs measure |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_risk_source`

Get a ebios risk source by ID

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_risk_source_history`

Return the change history of a ebios risk source: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios risk source |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_security_baseline`

Get a ebios security baseline by ID

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_security_baseline_history`

Return the change history of a ebios security baseline: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios security baseline |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_sr_ov_pair`

Get a ebios sr ov pair by ID

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_sr_ov_pair_history`

Return the change history of a ebios sr ov pair: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios sr ov pair |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_strategic_scenario`

Get a ebios strategic scenario by ID

Requires `risks.ebios_strategic.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_strategic_scenario_history`

Return the change history of a ebios strategic scenario: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_strategic.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios strategic scenario |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_study_framework`

Get a ebios study framework by ID

Requires `risks.ebios_assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_study_framework_history`

Return the change history of a ebios study framework: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios study framework |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_summary`

Get a ebios summary by ID

Requires `risks.ebios_summary.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_summary_history`

Return the change history of a ebios summary: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_summary.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios summary |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_targeted_objective`

Get a ebios targeted objective by ID

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_targeted_objective_history`

Return the change history of a ebios targeted objective: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios targeted objective |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_ebios_workshop`

Get a ebios workshop by ID

Requires `risks.ebios_assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_ebios_workshop_history`

Return the change history of a ebios workshop: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.ebios_assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios workshop |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_iso27005_risk`

Get a iso27005 risk by ID

Requires `risks.iso27005.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_iso27005_risk_history`

Return the change history of a iso27005 risk: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.iso27005.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the iso27005 risk |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_mitre_attack_technique`

Get a MITRE ATT&CK technique by ID.

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_risk`

Get a risk by ID

Requires `risks.risk.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_risk_acceptance`

Get a risk acceptance by ID

Requires `risks.acceptance.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_risk_acceptance_history`

Return the change history of a risk acceptance: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.acceptance.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the risk acceptance |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_risk_assessment`

Get a risk assessment by ID

Requires `risks.assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_risk_assessment_history`

Return the change history of a risk assessment: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the risk assessment |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_risk_criteria`

Get a risk criteria by ID

Requires `risks.criteria.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_risk_criteria_history`

Return the change history of a risk criteria: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.criteria.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the risk criteria |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_risk_history`

Return the change history of a risk: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.risk.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the risk |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_risk_level`

Get a risk level by ID

Requires `risks.criteria.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_risk_treatment_plan`

Get a risk treatment plan by ID

Requires `risks.treatment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_risk_treatment_plan_history`

Return the change history of a risk treatment plan: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.treatment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the risk treatment plan |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_scale_level`

Get a scale level by ID

Requires `risks.criteria.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_threat`

Get a threat by ID

Requires `risks.threat.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_threat_history`

Return the change history of a threat: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.threat.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the threat |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_treatment_action`

Get a treatment action by ID

Requires `risks.treatment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_vulnerability`

Get a vulnerability by ID

Requires `risks.vulnerability.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_vulnerability_history`

Return the change history of a vulnerability: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `risks.vulnerability.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the vulnerability |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `iso27005_risk_allowed_transitions`

List the lifecycle transitions the caller may perform on a iso27005 risk from its current state.

Requires `risks.iso27005.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `link_risk_requirements`

Link one or more compliance requirements to a risk. This is additive - existing links are preserved. Provide a risk_id and a list of requirement_ids to attach.

Requires `risks.risk.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `risk_id` | `string` | yes | UUID of the risk |
| `requirement_ids` | `array` | yes | List of requirement UUIDs to link to the risk |

## `link_treatment_plan_action_plans`

Link one or more compliance action plans to a risk treatment plan. This is additive - existing links are preserved. Provide a treatment_plan_id and a list of action_plan_ids to attach.

Requires `risks.treatment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `treatment_plan_id` | `string` | yes | UUID of the treatment plan |
| `action_plan_ids` | `array` | yes | List of compliance action plan UUIDs to link |

## `list_ebios_attack_path_steps`

List ebios attack path steps with optional search and filters

Requires `risks.ebios_strategic.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `scenario_id` | `string` | - | Filter by scenario_id |
| `stakeholder_id` | `string` | - | Filter by stakeholder_id |
| `action_type` | `string` | - | Filter by action_type |
| `difficulty` | `string` | - | Filter by difficulty |

## `list_ebios_attack_techniques`

List ebios attack techniques with optional search and filters

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `scenario_id` | `string` | - | Filter by scenario_id |
| `mitre_technique_id` | `string` | - | Filter by mitre_technique_id |
| `targeted_support_asset_id` | `string` | - | Filter by targeted_support_asset_id |
| `difficulty` | `string` | - | Filter by difficulty |
| `detection_difficulty` | `string` | - | Filter by detection_difficulty |

## `list_ebios_baseline_gaps`

List ebios baseline gaps with optional search and filters

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `baseline_id` | `string` | - | Filter by baseline_id |
| `linked_requirement_id` | `string` | - | Filter by linked_requirement_id |
| `severity` | `string` | - | Filter by severity |
| `status` | `string` | - | Filter by status |

## `list_ebios_ecosystem_stakeholders`

List ebios ecosystem stakeholders with optional search and filters

Requires `risks.ebios_ecosystem.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `category` | `string` | - | Filter by category |
| `threat_zone` | `string` | - | Filter by threat_zone |
| `is_attack_vector` | `string` | - | Filter by is_attack_vector |

## `list_ebios_feared_events`

List ebios feared events with optional search and filters

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `baseline_id` | `string` | - | Filter by baseline_id |
| `essential_asset_id` | `string` | - | Filter by essential_asset_id |
| `dic_criterion` | `string` | - | Filter by dic_criterion |

## `list_ebios_operational_scenarios`

List ebios operational scenarios with optional search and filters

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `strategic_scenario_id` | `string` | - | Filter by strategic_scenario_id |
| `likelihood_v` | `string` | - | Filter by likelihood_v |
| `gravity_inherited` | `string` | - | Filter by gravity_inherited |
| `risk_level` | `string` | - | Filter by risk_level |

## `list_ebios_pacs_measures`

List ebios pacs measures with optional search and filters

Requires `risks.ebios_summary.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `summary_id` | `string` | - | Filter by summary_id |
| `measure_type` | `string` | - | Filter by measure_type |
| `priority` | `string` | - | Filter by priority |
| `status` | `string` | - | Filter by status |
| `owner_id` | `string` | - | Filter by owner_id |

## `list_ebios_risk_sources`

List ebios risk sources with optional search and filters

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `category` | `string` | - | Filter by category |
| `is_retained` | `string` | - | Filter by is_retained |
| `is_from_catalog` | `string` | - | Filter by is_from_catalog |
| `threat_level` | `string` | - | Filter by threat_level |

## `list_ebios_security_baselines`

List ebios security baselines with optional search and filters

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `status` | `string` | - | Filter by status |

## `list_ebios_sr_ov_pairs`

List ebios sr ov pairs with optional search and filters

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `risk_source_id` | `string` | - | Filter by risk_source_id |
| `targeted_objective_id` | `string` | - | Filter by targeted_objective_id |
| `relevance` | `string` | - | Filter by relevance |
| `is_retained` | `string` | - | Filter by is_retained |

## `list_ebios_strategic_scenarios`

List ebios strategic scenarios with optional search and filters

Requires `risks.ebios_strategic.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `sr_ov_pair_id` | `string` | - | Filter by sr_ov_pair_id |
| `is_retained` | `string` | - | Filter by is_retained |
| `risk_level` | `string` | - | Filter by risk_level |

## `list_ebios_study_frameworks`

List ebios study frameworks with optional search and filters

Requires `risks.ebios_assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `status` | `string` | - | Filter by status |

## `list_ebios_summarys`

List ebios summarys with optional search and filters

Requires `risks.ebios_summary.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `status` | `string` | - | Filter by status |

## `list_ebios_targeted_objectives`

List ebios targeted objectives with optional search and filters

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `risk_source_id` | `string` | - | Filter by risk_source_id |
| `category` | `string` | - | Filter by category |
| `is_retained` | `string` | - | Filter by is_retained |

## `list_ebios_workshops`

List ebios workshops with optional search and filters

Requires `risks.ebios_assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `workshop_number` | `string` | - | Filter by workshop_number |
| `iteration_type` | `string` | - | Filter by iteration_type |
| `iteration_number` | `string` | - | Filter by iteration_number |
| `status` | `string` | - | Filter by status |

## `list_iso27005_risks`

List iso27005 risks with optional search and filters

Requires `risks.iso27005.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `threat_id` | `string` | - | Filter by threat_id |
| `vulnerability_id` | `string` | - | Filter by vulnerability_id |

## `list_mitre_attack_techniques`

List MITRE ATT&CK techniques (Enterprise Matrix). Filterable by tactic, mitre_id and active flag.

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `tactic` | `string` | - | Filter by tactic (e.g. initial_access). |
| `mitre_id` | `string` | - | Exact MITRE identifier (e.g. T1566.001). |
| `is_active` | `string` | - | Filter by active flag (true/false). |

## `list_risk_acceptances`

List risk acceptances with optional search and filters

Requires `risks.acceptance.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `risk_id` | `string` | - | Filter by risk_id |
| `status` | `string` | - | Filter by status |

## `list_risk_assessments`

List risk assessments with optional search and filters

Requires `risks.assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `status` | `string` | - | Filter by status |
| `methodology` | `string` | - | Filter by methodology |

## `list_risk_criterias`

List risk criterias with optional search and filters

Requires `risks.criteria.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `workflow_state` | `string` | - | Filter by workflow_state |

## `list_risk_levels`

List risk levels with optional search and filters

Requires `risks.criteria.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `criteria_id` | `string` | - | Filter by criteria_id |
| `requires_treatment` | `string` | - | Filter by requires_treatment |

## `list_risk_requirements`

List all compliance requirements linked to a risk. Returns requirement id, reference, number, name, compliance_status and framework_id for each linked requirement.

Requires `risks.risk.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `risk_id` | `string` | yes | UUID of the risk |

## `list_risk_treatment_plans`

List risk treatment plans with optional search and filters

Requires `risks.treatment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `status` | `string` | - | Filter by status |
| `risk_id` | `string` | - | Filter by risk_id |

## `list_risks`

List risks with optional search and filters

Requires `risks.risk.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `status` | `string` | - | Filter by status |
| `priority` | `string` | - | Filter by priority |
| `assessment_id` | `string` | - | Filter by assessment_id |
| `risk_source` | `string` | - | Filter by risk_source |

## `list_scale_levels`

List scale levels with optional search and filters

Requires `risks.criteria.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `criteria_id` | `string` | - | Filter by criteria_id |
| `scale_type` | `string` | - | Filter by scale_type |

## `list_threats`

List threats with optional search and filters

Requires `risks.threat.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `type` | `string` | - | Filter by type |
| `status` | `string` | - | Filter by status |
| `is_from_catalog` | `string` | - | Filter by is_from_catalog |

## `list_treatment_actions`

List treatment actions with optional search and filters

Requires `risks.treatment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `treatment_plan_id` | `string` | - | Filter by treatment_plan_id |
| `status` | `string` | - | Filter by status |

## `list_treatment_plan_action_plans`

List all compliance action plans linked to a risk treatment plan. Returns action plan id, reference, name, status, priority, progress_percentage and owner_id for each link.

Requires `risks.treatment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `treatment_plan_id` | `string` | yes | UUID of the treatment plan |

## `list_vulnerabilitys`

List vulnerabilitys with optional search and filters

Requires `risks.vulnerability.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `category` | `string` | - | Filter by category |
| `severity` | `string` | - | Filter by severity |
| `status` | `string` | - | Filter by status |
| `is_from_catalog` | `string` | - | Filter by is_from_catalog |

## `risk_acceptance_allowed_transitions`

List the lifecycle transitions the caller may perform on a risk acceptance from its current state.

Requires `risks.acceptance.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `risk_allowed_transitions`

List the lifecycle transitions the caller may perform on a risk from its current state.

Requires `risks.risk.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `risk_assessment_allowed_transitions`

List the lifecycle transitions the caller may perform on a risk assessment from its current state.

Requires `risks.assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `risk_treatment_plan_allowed_transitions`

List the lifecycle transitions the caller may perform on a risk treatment plan from its current state.

Requires `risks.treatment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `set_risk_requirements`

Replace the full set of linked requirements on a risk. All previous links are removed and replaced by the supplied list. Pass an empty requirement_ids list to clear all links.

Requires `risks.risk.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `risk_id` | `string` | yes | UUID of the risk |
| `requirement_ids` | `array` | yes | Complete list of requirement UUIDs to link. Pass an empty list to remove all links. |

## `set_treatment_plan_action_plans`

Replace the full set of compliance action plans linked to a risk treatment plan. All previous links are removed and replaced by the supplied list. Pass an empty action_plan_ids list to clear all links.

Requires `risks.treatment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `treatment_plan_id` | `string` | yes | UUID of the treatment plan |
| `action_plan_ids` | `array` | yes | Complete list of compliance action plan UUIDs to link. Pass an empty list to remove all links. |

## `threat_allowed_transitions`

List the lifecycle transitions the caller may perform on a threat from its current state.

Requires `risks.threat.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `transition_ebios_ecosystem_stakeholder`

Change the lifecycle state of a ebios ecosystem stakeholder (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.ebios_ecosystem.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios ecosystem stakeholder |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_ebios_operational_scenario`

Change the lifecycle state of a ebios operational scenario (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.ebios_operational.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios operational scenario |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_ebios_risk_source`

Change the lifecycle state of a ebios risk source (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios risk source |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_ebios_security_baseline`

Change the lifecycle state of a ebios security baseline (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.ebios_baseline.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios security baseline |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_ebios_sr_ov_pair`

Change the lifecycle state of a ebios sr ov pair (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.ebios_risk_source.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios sr ov pair |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_ebios_strategic_scenario`

Change the lifecycle state of a ebios strategic scenario (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.ebios_strategic.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios strategic scenario |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_ebios_summary`

Change the lifecycle state of a ebios summary (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.ebios_summary.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the ebios summary |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_iso27005_risk`

Change the lifecycle state of a iso27005 risk (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.iso27005.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the iso27005 risk |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_risk`

Change the lifecycle state of a risk (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.risk.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the risk |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_risk_acceptance`

Change the lifecycle state of a risk acceptance (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.acceptance.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the risk acceptance |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_risk_assessment`

Change the lifecycle state of a risk assessment (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.assessment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the risk assessment |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_risk_treatment_plan`

Change the lifecycle state of a risk treatment plan (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.treatment.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the risk treatment plan |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_threat`

Change the lifecycle state of a threat (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.threat.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the threat |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_vulnerability`

Change the lifecycle state of a vulnerability (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `risks.vulnerability.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the vulnerability |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `unlink_risk_requirements`

Remove one or more compliance requirements from a risk. Only the specified links are removed; other links are preserved. Provide a risk_id and a list of requirement_ids to detach.

Requires `risks.risk.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `risk_id` | `string` | yes | UUID of the risk |
| `requirement_ids` | `array` | yes | List of requirement UUIDs to unlink from the risk |

## `unlink_treatment_plan_action_plans`

Remove one or more compliance action plans from a risk treatment plan. Only the specified links are removed; other links are preserved.

Requires `risks.treatment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `treatment_plan_id` | `string` | yes | UUID of the treatment plan |
| `action_plan_ids` | `array` | yes | List of compliance action plan UUIDs to unlink |

## `update_ebios_attack_path_step`

Update an existing ebios attack path step

Requires `risks.ebios_strategic.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `scenario_id` | `string` | - | scenario_id |
| `order` | `integer` | - | Position of the step in the attack path (unique per scenario). |
| `stakeholder_id` | `string` | - | stakeholder_id |
| `description` | `string` | - | Description (HTML rich text) |
| `action_type` | `string` | - | Action type: initial_access, reconnaissance, lateral_movement, privilege_escalation, data_exfiltration, disruption, manipulation, persistence, other. |
| `difficulty` | `string` | - | Difficulty: trivial, easy, moderate, difficult, very_difficult. |

## `update_ebios_attack_technique`

Update an existing ebios attack technique

Requires `risks.ebios_operational.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `scenario_id` | `string` | - | scenario_id |
| `order` | `integer` | - | Position of the technique in the operational sequence (unique per scenario). |
| `mitre_technique_id` | `string` | - | mitre_technique_id |
| `custom_name` | `string` | - | custom_name |
| `description` | `string` | - | Description (HTML rich text) |
| `targeted_support_asset_id` | `string` | - | targeted_support_asset_id |
| `difficulty` | `string` | - | Difficulty: trivial, easy, moderate, difficult, very_difficult. |
| `detection_difficulty` | `string` | - | Detection difficulty: trivial, easy, moderate, difficult, very_difficult. |

## `update_ebios_baseline_gap`

Update an existing ebios baseline gap

Requires `risks.ebios_baseline.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `baseline_id` | `string` | - | baseline_id |
| `reference_source` | `string` | - | reference_source |
| `linked_requirement_id` | `string` | - | linked_requirement_id |
| `description` | `string` | - | Description (HTML rich text) |
| `severity` | `string` | - | Severity: low, medium, high, critical. |
| `recommended_remediation` | `string` | - | Recommended remediation (HTML rich text) |
| `status` | `string` | - | Gap status: identified, accepted, in_remediation, remediated. |
| `order` | `string` | - | order |

## `update_ebios_ecosystem_stakeholder`

Update an existing ebios ecosystem stakeholder

Requires `risks.ebios_ecosystem.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `stakeholder_id` | `string` | - | stakeholder_id |
| `supplier_id` | `string` | - | supplier_id |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | - | Ecosystem category: supplier, partner, subcontractor, customer, regulator, shared_infrastructure, client_employee, other. |
| `dependency` | `integer` | - | Organisation dependency on the stakeholder (1..4). Numerator in (D*P)/(M*T). |
| `penetration` | `integer` | - | Stakeholder penetration into the ecosystem (1..4). Numerator in (D*P)/(M*T). |
| `maturity` | `integer` | - | Stakeholder cyber maturity (1..4). Denominator in (D*P)/(M*T). |
| `trust` | `integer` | - | Trust placed in the stakeholder (1..4). Denominator in (D*P)/(M*T). |
| `is_attack_vector` | `string` | - | is_attack_vector |
| `attack_vector_justification` | `string` | - | Attack vector justification (HTML rich text) |

## `update_ebios_feared_event`

Update an existing ebios feared event

Requires `risks.ebios_baseline.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `baseline_id` | `string` | - | baseline_id |
| `essential_asset_id` | `string` | - | essential_asset_id |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `dic_criterion` | `string` | - | DIC criterion impaired: confidentiality, integrity, availability. |
| `gravity_level` | `integer` | - | Gravity level on the assessment impact scale (e.g. 1-4 or 1-5). |
| `gravity_justification` | `string` | - | Gravity justification (HTML rich text) |
| `business_impacts` | `object` | - | Optional business impact breakdown. Accepts a JSON object with keys such as financial, legal, reputation, operational, human, environmental. |
| `order` | `string` | - | order |

## `update_ebios_operational_scenario`

Update an existing ebios operational scenario

Requires `risks.ebios_operational.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `strategic_scenario_id` | `string` | - | strategic_scenario_id |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `gravity_level` | `string` | - | gravity_level |
| `gravity_inherited` | `string` | - | true when gravity_level is inherited from the parent strategic scenario; set to false and supply gravity_override_justification to override. |
| `gravity_override_justification` | `string` | - | Gravity override justification (HTML rich text) |
| `likelihood_v` | `integer` | - | ANSSI operational likelihood V1..V4 stored as integer 1..4 (M4bis Annex B). |
| `likelihood_justification` | `string` | - | Likelihood justification (HTML rich text) |
| `existing_controls` | `string` | - | Existing controls (HTML rich text) |
| `mitre_version` | `string` | - | mitre_version |

## `update_ebios_pacs_measure`

Update an existing ebios pacs measure

Requires `risks.ebios_summary.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `summary_id` | `string` | - | summary_id |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `measure_type` | `string` | - | PACS measure type: governance, protection, defense, resilience, awareness. |
| `owner_id` | `string` | - | owner_id |
| `start_date` | `string` | - | start_date |
| `target_date` | `string` | - | target_date |
| `completion_date` | `string` | - | completion_date |
| `cost_estimate` | `string` | - | cost_estimate |
| `expected_gain` | `string` | - | Expected gain (HTML rich text) |
| `priority` | `string` | - | Priority: low, medium, high, critical. |
| `status` | `string` | - | Status: planned, in_progress, completed, cancelled, overdue. |
| `progress_percentage` | `integer` | - | Progress in percent (0 to 100). |
| `order` | `string` | - | order |

## `update_ebios_risk_source`

Update an existing ebios risk source

Requires `risks.ebios_risk_source.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | - | ANSSI risk source category: state, organized_crime, terrorist, activist, competitor, employee, service_provider, amateur, natural, other. |
| `motivation_level` | `integer` | - | 1 (low) to 4 (very strong). Drives the ANSSI threat level Grid A. |
| `motivation_description` | `string` | - | Motivation description (HTML rich text) |
| `resources_level` | `integer` | - | 1 (limited) to 4 (unlimited). Drives the ANSSI threat level Grid A. |
| `activity_level` | `integer` | - | Observed activity 1 to 4. Activity >= 3 majorates the threat level by one (capped at V4). |
| `is_retained` | `string` | - | is_retained |
| `retention_justification` | `string` | - | Retention justification (HTML rich text) |
| `is_from_catalog` | `string` | - | is_from_catalog |

## `update_ebios_security_baseline`

Update an existing ebios security baseline

Requires `risks.ebios_baseline.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `dic_summary` | `string` | - | DIC needs summary (HTML rich text) |
| `status` | `string` | - | Baseline status: draft, in_progress, completed. |

## `update_ebios_sr_ov_pair`

Update an existing ebios sr ov pair

Requires `risks.ebios_risk_source.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `risk_source_id` | `string` | - | risk_source_id |
| `targeted_objective_id` | `string` | - | targeted_objective_id |
| `relevance` | `string` | - | SR/OV relevance: low, medium, high, critical. Combined with risk_source.threat_level to produce priority_score. |
| `relevance_justification` | `string` | - | Relevance justification (HTML rich text) |
| `is_retained` | `string` | - | is_retained |
| `retention_justification` | `string` | - | Retention justification (HTML rich text) |

## `update_ebios_strategic_scenario`

Update an existing ebios strategic scenario

Requires `risks.ebios_strategic.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `sr_ov_pair_id` | `string` | - | sr_ov_pair_id |
| `gravity_level` | `integer` | - | Gravity on the assessment impact scale. Combined with likelihood via the matrix to compute risk_level. |
| `gravity_justification` | `string` | - | Gravity justification (HTML rich text) |
| `likelihood_level` | `integer` | - | Likelihood on the assessment likelihood scale. Combined with gravity via the matrix to compute risk_level. |
| `likelihood_justification` | `string` | - | Likelihood justification (HTML rich text) |
| `existing_security_measures` | `string` | - | Existing security measures (HTML rich text) |
| `is_retained` | `string` | - | is_retained |
| `retention_justification` | `string` | - | retention_justification |
| `consolidated_risk_id` | `string` | - | consolidated_risk_id |

## `update_ebios_study_framework`

Update an existing ebios study framework

Requires `risks.ebios_assessment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `mission_statement` | `string` | - | Mission statement (HTML rich text) |
| `business_perimeter` | `string` | - | Business perimeter (HTML rich text) |
| `technical_perimeter` | `string` | - | Technical perimeter (HTML rich text) |
| `temporal_perimeter` | `string` | - | temporal_perimeter |
| `financial_envelope` | `string` | - | financial_envelope |
| `assumptions` | `string` | - | assumptions |
| `constraints` | `string` | - | constraints |
| `expected_deliverables` | `string` | - | expected_deliverables |
| `status` | `string` | - | Study framework status: draft, validated. |

## `update_ebios_summary`

Update an existing ebios summary

Requires `risks.ebios_summary.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `residual_risk_strategy` | `string` | - | Residual risk strategy (HTML rich text) |
| `monitoring_plan` | `string` | - | Monitoring plan (HTML rich text) |
| `pacs_summary` | `string` | - | PACS summary (HTML rich text) |
| `next_strategic_cycle_date` | `string` | - | next_strategic_cycle_date |
| `next_operational_cycle_date` | `string` | - | next_operational_cycle_date |
| `status` | `string` | - | Summary status: draft, in_progress, under_review, validated. |

## `update_ebios_targeted_objective`

Update an existing ebios targeted objective

Requires `risks.ebios_risk_source.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `risk_source_id` | `string` | - | risk_source_id |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | - | ANSSI objective category: lucrative, strategic, terrorist, ideological, revenge, ludic, other. |
| `is_retained` | `string` | - | is_retained |
| `order` | `string` | - | order |

## `update_ebios_workshop`

Update an existing ebios workshop

Requires `risks.ebios_assessment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `workshop_number` | `integer` | - | Workshop number 0..5 (0=study framework, 1=baseline, 5=treatment). |
| `iteration_type` | `string` | - | Iteration type: strategic (annual) or operational (semestrial). |
| `iteration_number` | `integer` | - | Iteration number (starts at 1). |
| `status` | `string` | - | Workshop status: not_started, in_progress, under_review, validated, rejected. |
| `started_at` | `string` | - | started_at |
| `deliverables_summary` | `string` | - | deliverables_summary |
| `notes` | `string` | - | notes |

## `update_iso27005_risk`

Update an existing iso27005 risk

Requires `risks.iso27005.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `assessment_id` | `string` | - | assessment_id |
| `threat_id` | `string` | - | threat_id |
| `vulnerability_id` | `string` | - | vulnerability_id |
| `threat_likelihood` | `integer` | - | Threat likelihood level (integer matching a scale level, e.g. 1-5). combined_likelihood is auto-computed as max(threat_likelihood, vulnerability_exposure). |
| `vulnerability_exposure` | `integer` | - | Vulnerability exposure level (integer matching a scale level, e.g. 1-5). combined_likelihood is auto-computed as max(threat_likelihood, vulnerability_exposure). |
| `impact_confidentiality` | `integer` | - | Confidentiality impact level (integer matching a scale level, e.g. 1-5). |
| `impact_integrity` | `integer` | - | Integrity impact level (integer matching a scale level, e.g. 1-5). |
| `impact_availability` | `integer` | - | Availability impact level (integer matching a scale level, e.g. 1-5). |
| `existing_controls` | `string` | - | Existing controls (HTML rich text) |
| `risk_id` | `string` | - | risk_id |
| `description` | `string` | - | Description (HTML rich text) |
| `affected_essential_asset_ids` | `array` | - | Essential assets impacted by this triplet. |
| `affected_support_asset_ids` | `array` | - | Support assets impacted by this triplet. |

## `update_risk`

Update an existing risk

Requires `risks.risk.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `status` | `string` | - | Risk status. |
| `priority` | `string` | - | Risk priority. |
| `risk_source` | `string` | - | How this risk entered the register (manual, consolidated from an analysis, etc.). |
| `source_entity_id` | `string` | - | UUID of the source entity (ISO 27005 analysis, EBIOS scenario, ...) when risk_source is not 'manual'. |
| `source_entity_type` | `string` | - | Class name of the source entity (e.g. 'ISO27005Risk', 'OperationalScenario'). |
| `initial_likelihood` | `integer` | - | Initial likelihood level (matching scale levels, e.g. 1-5) |
| `initial_impact` | `integer` | - | Initial impact level (matching scale levels, e.g. 1-5) |
| `current_likelihood` | `integer` | - | Current likelihood level (matching scale levels, e.g. 1-5) |
| `current_impact` | `integer` | - | Current impact level (matching scale levels, e.g. 1-5) |
| `residual_likelihood` | `integer` | - | Residual likelihood level (matching scale levels, e.g. 1-5) |
| `residual_impact` | `integer` | - | Residual impact level (matching scale levels, e.g. 1-5) |
| `impact_confidentiality` | `boolean` | - | Whether this risk impacts confidentiality. |
| `impact_integrity` | `boolean` | - | Whether this risk impacts integrity. |
| `impact_availability` | `boolean` | - | Whether this risk impacts availability. |
| `treatment_decision` | `string` | - | Treatment decision. |
| `treatment_justification` | `string` | - | Treatment justification (HTML rich text) |
| `review_date` | `string` | - | Next review date (ISO 8601). |
| `assessment_id` | `string` | - | assessment_id |
| `risk_owner_id` | `string` | - | UUID of the risk owner (user) |
| `affected_essential_asset_ids` | `array` | - | Essential assets affected by this risk. |
| `affected_support_asset_ids` | `array` | - | Support assets affected by this risk. |
| `linked_requirement_ids` | `array` | - | Compliance requirements linked to this risk. |

## `update_risk_acceptance`

Update an existing risk acceptance

Requires `risks.acceptance.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `risk_id` | `string` | - | risk_id |
| `justification` | `string` | - | Justification (HTML rich text) |
| `conditions` | `string` | - | Conditions (HTML rich text) |
| `valid_until` | `string` | - | Last day the acceptance remains in force (ISO 8601). |
| `review_date` | `string` | - | Date the acceptance should be reviewed (ISO 8601). |
| `accepted_by_id` | `string` | - | UUID of the user who accepted the risk |

## `update_risk_assessment`

Update an existing risk assessment

Requires `risks.assessment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `methodology` | `string` | - | Risk assessment methodology. Default: iso27005. |
| `status` | `string` | - | Risk assessment status. |
| `assessment_date` | `string` | - | Assessment date (ISO 8601, e.g. 2025-06-15) |
| `next_review_date` | `string` | - | Next review date (ISO 8601). |
| `risk_criteria_id` | `string` | - | UUID of the risk criteria to use |
| `assessor_id` | `string` | - | UUID of the assessor (user) |
| `summary` | `string` | - | Summary (HTML rich text) |
| `scope_ids` | `array` | - | Scopes this assessment covers (RG-01). |

## `update_risk_criteria`

Update an existing risk criteria

Requires `risks.criteria.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `risk_matrix` | `object` | - | Risk matrix as JSON object mapping 'likelihood,impact' to risk level. Example for a 5x5 matrix: {"1,1": 1, "1,2": 2, ..., "5,5": 5}. Can be omitted - the matrix will be auto-built from scale levels and risk levels via rebuild_risk_matrix(). |
| `acceptance_threshold` | `integer` | - | Risk level at or below which risks are automatically acceptable (default 0). |
| `is_default` | `boolean` | - | Whether this is the default risk criteria. |
| `scope_ids` | `array` | - | Scopes these criteria apply to (RG-01). |

## `update_risk_level`

Update an existing risk level

Requires `risks.criteria.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `criteria_id` | `string` | - | UUID of the parent RiskCriteria. |
| `level` | `integer` | - | Numeric risk level (e.g. 1-5). Must be unique per criteria. |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `color` | `string` | - | Color hex code (e.g. #ff0000) |
| `requires_treatment` | `boolean` | - | Whether this risk level requires treatment. |

## `update_risk_treatment_plan`

Update an existing risk treatment plan

Requires `risks.treatment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `treatment_type` | `string` | - | Treatment strategy type. |
| `status` | `string` | - | Treatment plan status. |
| `expected_residual_likelihood` | `integer` | - | Expected residual likelihood (matching scale levels, e.g. 1-5) |
| `expected_residual_impact` | `integer` | - | Expected residual impact (matching scale levels, e.g. 1-5) |
| `cost_estimate` | `string` | - | cost_estimate |
| `start_date` | `string` | - | start_date |
| `target_date` | `string` | - | target_date |
| `completion_date` | `string` | - | completion_date |
| `progress_percentage` | `string` | - | progress_percentage |
| `risk_id` | `string` | - | risk_id |
| `owner_id` | `string` | - | UUID of the treatment plan owner (user) |

## `update_scale_level`

Update an existing scale level

Requires `risks.criteria.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `criteria_id` | `string` | - | UUID of the parent RiskCriteria. |
| `scale_type` | `string` | - | Type of scale. |
| `level` | `integer` | - | Numeric level (e.g. 1-5). Must be unique per criteria + scale_type. |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `color` | `string` | - | color |

## `update_threat`

Update an existing threat

Requires `risks.threat.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `type` | `string` | - | Threat type. |
| `origin` | `string` | - | Threat origin. |
| `category` | `string` | - | Threat category. |
| `typical_likelihood` | `integer` | - | Typical likelihood level (integer, e.g. 1-5). |
| `is_from_catalog` | `boolean` | - | Whether this threat comes from a predefined ISO 27005 catalog. |
| `status` | `string` | - | Threat status. |
| `scope_ids` | `array` | - | Scopes this threat applies to (RG-01). |

## `update_treatment_action`

Update an existing treatment action

Requires `risks.treatment.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `treatment_plan_id` | `string` | - | treatment_plan_id |
| `description` | `string` | - | Description (HTML rich text) |
| `owner_id` | `string` | - | UUID of the action owner (user) |
| `target_date` | `string` | - | target_date |
| `completion_date` | `string` | - | completion_date |
| `status` | `string` | - | Action status. |
| `order` | `string` | - | order |

## `update_vulnerability`

Update an existing vulnerability

Requires `risks.vulnerability.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | name |
| `description` | `string` | - | Description (HTML rich text) |
| `category` | `string` | - | Vulnerability category. |
| `severity` | `string` | - | Vulnerability severity. |
| `status` | `string` | - | Vulnerability status. |
| `affected_asset_types` | `array` | - | Support asset types this vulnerability affects (free-form list). |
| `cve_references` | `array` | - | List of CVE identifiers (e.g. 'CVE-2024-1234'). |
| `is_from_catalog` | `boolean` | - | Whether this vulnerability comes from a predefined catalog. |
| `remediation_guidance` | `string` | - | Remediation guidance (HTML rich text) |
| `scope_ids` | `array` | - | Scopes this vulnerability applies to (RG-01). |
| `affected_asset_ids` | `array` | - | UUIDs of support assets affected by this vulnerability. |

## `vulnerability_allowed_transitions`

List the lifecycle transitions the caller may perform on a vulnerability from its current state.

Requires `risks.vulnerability.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

# Indicator

`context.models.indicator.Indicator`

Steering indicator (KPI) of the ISMS, manual, fed by API or predefined by Cairn. It quantifies an objective, compliance with a requirement, or the performance of a control, and serves as input to dashboards and management reviews.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `INDC-N`, unique | Business reference |
| `scopes` | relation | M2M → Scope | Linked scopes (RG-01) |
| `name` | string | required, max 255 | Indicator title |
| `description` | text | optional, HTML | Description and purpose |
| `indicator_type` | enum | required | `organizational`, `technical` |
| `collection_method` | enum | required, default `manual` | `manual`, `api`, `internal` |
| `format` | enum | required, default `number` | `number`, `boolean` |
| `unit` | string | optional, max 50, not allowed for `boolean` | Display unit (`%`, `j`, `incidents`, etc.) |
| `current_value` | string | read-only, max 255 | Last measured value (updated automatically with each `IndicatorMeasurement`) |
| `expected_level` | string | optional, max 255 | Expected target (free-text label) |
| `critical_threshold_operator` | enum | optional | `below`, `above`, `is_false`, `is_true` |
| `critical_threshold_value` | string | optional | Threshold value (for `below` / `above`) |
| `critical_threshold_min` | float | optional, numbers only | Lower bound outside the critical zone |
| `critical_threshold_max` | float | optional, numbers only | Upper bound outside the critical zone |
| `review_frequency` | enum | required | `daily`, `weekly`, `monthly`, `quarterly`, `semi_annual`, `annual` |
| `first_review_date` | date | required | First review date (must be today or later at creation) |
| `status` | enum | required, default `active` | `active`, `inactive`, `draft` |
| `is_internal` | boolean | default `false` | `true` = predefined Cairn indicator, fed internally |
| `internal_source` | enum | required if `is_internal=true` | `global_compliance_rate`, `framework_compliance_rate`, `objective_progress`, `risk_treatment_rate`, `approved_scopes_rate`, `mandatory_roles_coverage` |
| `internal_source_parameter` | string | optional | Parameter of the predefined source (for example the framework UUID for `framework_compliance_rate`) |
| `owner` | relation | FK → User, optional | Business owner responsible for the measurement and the review |
| `linked_objectives` | relation | M2M → Objective | Objectives whose progress the indicator measures (ISO 27001 §6.2 / §9.1) |
| `linked_requirements` | relation | M2M → Requirement | Requirements whose compliance the indicator measures |
| `tags` | relation | M2M → Tag | Free-form tags |
| `version` | int | auto-incremented | Bumped on each major modification |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## Énumérations

### `indicator_type`

- `organizational`: business or governance indicator (compliance rate, role coverage, etc.). Mandatory for predefined indicators (`is_internal=true`).
- `technical`: technical indicator (response time, availability, incident rate).

### `collection_method`

- `manual`: entered manually by a user through `IndicatorMeasurement`.
- `api`: fed by an external call (script, integration, agent).
- `internal`: fed automatically by Cairn from an `internal_source` (see below).

### `internal_source` (predefined sources)

| Source | Format | Unité | Description |
|---|---|---|---|
| `global_compliance_rate` | number | `%` | Aggregated compliance rate: same calculation as the "Overall compliance" card on the dashboard (average, over active and reportable frameworks, of the share of applicable requirements that are compliant according to the latest assessment result; shared service `compliance.services`) |
| `framework_compliance_rate` | number | `%` | Compliance rate of a specific framework (parameter = `Framework` UUID), same per-requirement calculation as above |
| `objective_progress` | number | `%` | Average progress of objectives (`Objective.progress_percentage`) |
| `risk_treatment_rate` | number | `%` | Share of risks whose treatment plan is `completed` |
| `approved_scopes_rate` | number | `%` | Share of `Scope` records in a reportable lifecycle state (counting in reports) |
| `mandatory_roles_coverage` | number | `%` | Share of roles with `is_mandatory=true` that have at least one assigned user |

Internal indicators are recalculated periodically by a background service; see [§ Automated monitoring](README.md#pilotage-et-calculs-automatiques) of the module.

## Sub-entity: `IndicatorMeasurement`

`context.models.indicator.IndicatorMeasurement`

A historical measurement of an indicator. Several measurements per indicator, indexed by date, feed the sparklines and the trend over time.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Unique identifier |
| `indicator` | relation | FK → Indicator, required | Measured indicator |
| `value` | string | required, max 255 | Measured value (number or boolean serialized as a string) |
| `recorded_at` | datetime | default `now`, indexed | Timestamp of the measurement. Editable, which allows importing historical series |
| `recorded_by` | relation | FK → User, optional | Author of the measurement |
| `notes` | text | optional | Free-form comment (methodology, contextual event) |

The indicator's `current_value` is updated automatically when each `IndicatorMeasurement` is created, with the value of the most recent measurement.

## Specific business rules

| ID | Rule |
|---|---|
| RS-IND-01 | A predefined indicator (`is_internal=true`) must have `indicator_type=organizational`. |
| RS-IND-02 | A predefined indicator must set `internal_source`; its `format` and `unit` are aligned with `PREDEFINED_SOURCE_FORMAT`. |
| RS-IND-03 | An indicator with `format=boolean` cannot have a `unit`. |
| RS-IND-04 | An indicator with `format=boolean` uses only `is_true` or `is_false` as `critical_threshold_operator`. |
| RS-IND-05 | An indicator with `format=number` uses only `below` or `above` as `critical_threshold_operator`. |
| RS-IND-06 | `critical_threshold_min` and `critical_threshold_max` are reserved for `format=number`. If both are set, `min < max`. |
| RS-IND-07 | At creation, `first_review_date` must be today or later. |
| RS-IND-08 | On each creation of an `IndicatorMeasurement`, `Indicator.current_value` is updated with the value of the new measurement. |

## Critical state (`is_critical`)

Property computed on read, true when:

- `format=boolean` and `current_value` violates the configured operator (`is_true` → false value, `is_false` → true value);
- `format=number` and `current_value < critical_threshold_min` or `current_value > critical_threshold_max`;
- `critical_threshold_operator=below` and `current_value < critical_threshold_value`;
- `critical_threshold_operator=above` and `current_value > critical_threshold_value`.

A critical indicator is displayed with a red border on the dashboard and appears in the weekly notifications.

## Endpoints

### REST

- `GET /api/v1/context/indicators/`: list with filters `indicator_type`, `status`, `format`, `collection_method`, `is_internal`
- `POST /api/v1/context/indicators/`
- `GET /api/v1/context/indicators/<uuid>/`
- `PUT/PATCH /api/v1/context/indicators/<uuid>/`
- `DELETE /api/v1/context/indicators/<uuid>/`
- `GET /api/v1/context/indicators/<uuid>/measurements/`: measurement history
- `POST /api/v1/context/indicators/<uuid>/measurements/`: new measurement
- `POST /api/v1/context/indicators/batch/`: batch creation

### MCP

- `list_indicators` / `get_indicator` / `create_indicator` / `update_indicator` / `delete_indicator` / `batch_create_indicators`
- `list_indicator_measurements` / `create_indicator_measurement` / `batch_create_indicator_measurements`

## Permissions

| Codename | Description |
|---|---|
| `context.indicator.read` | Read indicators and their measurements |
| `context.indicator.create` | Create an indicator and its measurements |
| `context.indicator.update` | Modify an indicator |
| `context.indicator.delete` | Delete an indicator |

## Références

- ISO/IEC 27001:2022 §6.2 (Security objectives and measurability) and §9.1 (Monitoring, measurement, analysis, evaluation)
- [Objective](objective.md), [Requirement](../m3-compliance/requirement.md): target entities of the M2M links
- [Indicator MCP tools](https://github.com/frousselet/cairn/blob/main/mcp/tools.py): implementation

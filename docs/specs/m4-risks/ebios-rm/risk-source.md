# RiskSource

`risks.models.ebios.risk_source.RiskSource`

Risk source (SR): an element (individual, group, organization, State, phenomenon) at the origin of the risk. Reference prefix: `ERSC`.

## 4.2.1 Entity: RiskSource (Risk source)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required | Parent assessment |
| `reference` | string | required, unique, prefix ERSC | Code (e.g. ERSC-1) |
| `name` | string | required, max 255 | Name of the SR |
| `description` | text | optional | Description |
| `category` | enum | required | `state`, `organized_crime`, `terrorist`, `activist`, `competitor`, `employee`, `service_provider`, `amateur`, `natural`, `other` |
| `motivation_level` | integer | required, 1 to 4 | Motivation level (1 low, 4 very high) |
| `motivation_description` | text | optional | Qualitative description |
| `resources_level` | integer | required, 1 to 4 | Resources level (1 limited, 4 unlimited) |
| `activity_level` | integer | required, 1 to 4 | Observed activity level |
| `threat_level` | integer | computed, 1 to 4 (V1-V4) | ANSSI threat level (grid A, [see README §2.8](README.md#28-anssi-scoring-grids)) |
| `is_retained` | boolean | required, default true | SR retained for the analysis |
| `retention_justification` | text | optional | Justification |
| `is_from_catalog` | boolean | required, default false | Sourced from the predefined ANSSI catalog |
| `criteria_snapshot` | json | computed | Snapshot of the scoring grid |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

> `threat_level` is computed in `save()` according to grid A ([see README §2.8](README.md#28-anssi-scoring-grids)). The result is stored for use in filtering/indexing. The grid is configurable via a JSON field on [`RiskCriteria`](../risk-criteria.md) (key `ebios_threat_grid`).

# RiskCriteria

`risks.models.risk_criteria.RiskCriteria`

Scales, matrix and acceptance thresholds used for a risk assessment. Reusable across several assessments.

## 2.2 Entity: RiskCriteria (Risk criteria)

Defines the scales, the matrix and the acceptance thresholds used for a risk assessment. Reusable across several assessments.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Attached scope |
| `name` | string | required, max 255 | Name of the criteria set (e.g. "2026 Criteria") |
| `description` | text | optional | Description |
| `likelihood_scale` | relation | O2M → ScaleLevel | Likelihood scale |
| `impact_scale` | relation | O2M → ScaleLevel | Impact scale |
| `risk_matrix` | json | required | Risk matrix (likelihood × impact → risk level) |
| `risk_levels` | relation | O2M → RiskLevel | Resulting risk levels |
| `acceptance_threshold` | integer | required | Acceptance threshold (risk level above which treatment is mandatory) |
| `is_default` | boolean | required, default false | Default criteria for new assessments |
| `workflow_state` | enum | required, default `draft` | Unified lifecycle: `draft`, `pending`, `validated`, `archived`. See [governance/workflow.md](../governance/workflow.md). |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## ScaleLevel

`risks.models.risk_criteria.ScaleLevel`

### 2.3 Sub-entity: ScaleLevel (Scale level)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `criteria_id` | relation | FK → RiskCriteria, required | Parent criteria |
| `scale_type` | enum | required | `likelihood`, `impact` |
| `level` | integer | required | Numeric value (e.g. 1, 2, 3, 4) |
| `name` | string | required, max 100 | Label (e.g. "Rare", "Likely", "Almost certain") |
| `description` | text | optional | Detailed description and examples |
| `color` | string | optional, hex format | Display color |

## RiskLevel

`risks.models.risk_criteria.RiskLevel`

### 2.4 Sub-entity: RiskLevel (Risk level)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `criteria_id` | relation | FK → RiskCriteria, required | Parent criteria |
| `level` | integer | required | Numeric value (e.g. 1, 2, 3, 4) |
| `name` | string | required, max 100 | Label (e.g. "Low", "Moderate", "High", "Critical") |
| `description` | text | optional | Description and expected actions |
| `color` | string | required, hex format | Display color |
| `requires_treatment` | boolean | required | Treatment mandatory at this level |

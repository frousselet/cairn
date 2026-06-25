# RiskTreatmentPlan

`risks.models.treatment.RiskTreatmentPlan`

Treatment plan listing the actions associated with a risk.

## 2.6 Entity: RiskTreatmentPlan (Risk treatment plan)

Represents the treatment actions associated with a risk.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `risk_id` | relation | FK → Risk, required | Treated risk |
| `reference` | string | required, unique | Reference code (e.g. PTR-001) |
| `name` | string | required, max 255 | Plan title |
| `description` | text | optional | Detailed description |
| `treatment_type` | enum | required | `mitigate`, `transfer`, `avoid` |
| `actions` | relation | O2M → TreatmentAction | Treatment actions |
| `expected_residual_likelihood` | integer | optional | Expected residual likelihood |
| `expected_residual_impact` | integer | optional | Expected residual impact |
| `cost_estimate` | decimal | optional | Overall cost estimate |
| `owner_id` | relation | FK → User, required | Plan owner |
| `start_date` | date | optional | Start date |
| `target_date` | date | required | Target completion date |
| `completion_date` | date | optional | Actual completion date |
| `progress_percentage` | integer | optional, 0-100 | Overall progress |
| `status` | enum | required | `planned`, `in_progress`, `completed`, `cancelled`, `overdue` |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## TreatmentAction

`risks.models.treatment.TreatmentAction`

### 2.7 Sub-entity: TreatmentAction (Treatment action)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `treatment_plan_id` | relation | FK → RiskTreatmentPlan, required | Parent treatment plan |
| `description` | text | required | Description of the action |
| `owner_id` | relation | FK → User, required | Action owner |
| `target_date` | date | required | Target date |
| `completion_date` | date | optional | Completion date |
| `linked_measures` | relation | M2M → Measure | Associated measures (Measures module) |
| `status` | enum | required | `planned`, `in_progress`, `completed`, `cancelled` |
| `order` | integer | required | Execution order |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

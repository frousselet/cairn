# PACSMeasure

`risks.models.ebios.pacs_measure.PACSMeasure`

PACS measure (Plan d'Amélioration Continue de la Sécurité - Continuous Security Improvement Plan). Reference prefix: `EPAC`.

## 4.5.2 Entity: PACSMeasure (PACS measure)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `summary_id` | relation | FK -> [EbiosSummary](ebios-summary.md), required | Parent summary |
| `reference` | string | required, unique, prefix EPAC | Code (e.g. EPAC-1) |
| `name` | string | required, max 255 | Measure title |
| `description` | text | required | Description |
| `measure_type` | enum | required | `governance`, `protection`, `defense`, `resilience`, `awareness` |
| `linked_treatment_plans` | M2M -> [RiskTreatmentPlan](../risk-treatment-plan.md) | optional | Treatment plans carrying the measure |
| `linked_baseline_gaps` | M2M -> [BaselineGap](baseline-gap.md) | optional | Baseline gaps addressed by the measure |
| `linked_requirements` | M2M -> Requirement | optional | Compliance requirements covered |
| `owner_id` | relation | FK -> User, required | Measure owner |
| `start_date` | date | optional | Start date |
| `target_date` | date | required | Target date |
| `completion_date` | date | optional | Actual completion date |
| `cost_estimate` | decimal | optional | Estimated cost |
| `expected_gain` | text | optional | Expected gain (risk reduction) |
| `priority` | enum | required | `low`, `medium`, `high`, `critical` |
| `status` | enum | required | `planned`, `in_progress`, `completed`, `cancelled`, `overdue` |
| `progress_percentage` | integer | optional, 0 to 100 | Progress |
| `order` | integer | required | Display order within the PACS |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

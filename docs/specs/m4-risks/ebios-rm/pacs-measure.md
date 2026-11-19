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
| `controls` | reverse M2M -> [Control](../../m8-controls/control.md) via `Control.pacs_measures` | optional | Register controls the measure creates or reinforces |
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

## Creation and edition

A measure is a row of the page of workshop 5 (see [README, 8.8](README.md)).

- **Creation** asks for five fields on one screen : the name, the measure type and the priority (two decisions, the selects open on *Choose...*), the owner (whoever adds the measure, unless they say otherwise) and the target date. The summary is known from the address. `order` is not asked : a new measure comes last.
- **Edition** has three sections : *PACS measure* (name, type, priority, description, expected gain, cost estimate), *Owner and dates* (owner, start, target and completion dates, progress, rank) and *Relations* (the treatment plans it carries out, the baseline gaps it closes, the requirements it meets).
- **The baseline gaps** are picked among those of the same study, **the requirements** among those of the frameworks the study names (applicable frameworks of workshop 0, baseline references of workshop 1; every requirement when it names none). What the measure already links to stays offered.
- `linked_treatment_plan_ids`, `linked_baseline_gap_ids` and `linked_requirement_ids` set the three relations through the MCP tools.
- The status of a measure is its lifecycle step; the web interface shows it and does not move it yet (the overdue flip is automatic, rule RE-18).


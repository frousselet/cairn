# RiskSourceObjectivePair

`risks.models.ebios.sr_ov_pair.RiskSourceObjectivePair`

Risk-source / targeted-objective pair (SR-OV): the formal association of a risk source and a targeted objective, assessed for relevance. Reference prefix: `ESOV`.

## 4.2.3 Entity: RiskSourceObjectivePair (Risk-source / targeted-objective pair (SR-OV))

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required | Parent assessment |
| `reference` | string | required, unique, prefix ESOV | Code (e.g. ESOV-1) |
| `risk_source_id` | relation | FK -> [RiskSource](risk-source.md), required | SR |
| `targeted_objective_id` | relation | FK -> [TargetedObjective](targeted-objective.md), required | OV |
| `relevance` | enum | required | `low`, `medium`, `high`, `critical` |
| `relevance_justification` | text | optional | Justification |
| `priority_score` | integer | computed, 1 to 4 | Aggregated score: f(`risk_source.threat_level`, `relevance`) |
| `is_retained` | boolean | required, default true | Retained for workshop 3 |
| `retention_justification` | text | optional | Justification |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

> Uniqueness constraint: `(assessment_id, risk_source_id, targeted_objective_id)`.

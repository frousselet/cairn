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

> Rule : the targeted objective of a pair is an objective of its risk source, in the same assessment. `RiskSourceObjectivePair.clean()` refuses a pair that says otherwise, on the form, the REST API and the MCP server.

## Creation and edition

A pair is a row of the page of workshop 2 (see [README, 8.5](README.md)).

- **A pair is named by its targeted objective.** An objective belongs to one risk source, of one study : the form asks for the objective, listed under its risk source, and the pair takes the source and the assessment of that objective. `risk_source` and `assessment` are optional in the REST API (`POST /api/v1/risks/ebios/sr-ov-pairs/`) and in `create_ebios_sr_ov_pair`, and are refused when they contradict the objective.
- **Creation** asks for two fields : the targeted objective, among those of the study that have no pair yet, and the relevance (a decision, the select opens on *Choose...*). Opened from the line of an objective (`?objective=<id>`), the form opens on that objective.
- **Edition** changes the relevance, its justification, and whether the pair is retained for workshop 3, with the reason. The objective of an existing pair is not changed.


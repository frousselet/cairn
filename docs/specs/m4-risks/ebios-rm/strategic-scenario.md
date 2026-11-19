# StrategicScenario

`risks.models.ebios.strategic_scenario.StrategicScenario`

Strategic scenario: a high-level attack path from an SR to an OV passing through the ecosystem. Reference prefix: `ESTS`.

## 4.3.2 Entity: StrategicScenario (Strategic scenario)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required | Parent assessment |
| `reference` | string | required, unique, prefix ESTS | Code (e.g. ESTS-1) |
| `name` | string | required, max 255 | Title |
| `description` | text | required | Narrative description |
| `sr_ov_pair_id` | relation | FK -> [RiskSourceObjectivePair](sr-ov-pair.md), required | Source SR-OV pair |
| `targeted_feared_events` | M2M -> [FearedEvent](feared-event.md) | required | Targeted feared events |
| `gravity_level` | integer | required | Severity (impact scale) |
| `gravity_justification` | text | optional | Justification |
| `likelihood_level` | integer | required | Strategic likelihood (likelihood scale) |
| `likelihood_justification` | text | optional | Justification |
| `risk_level` | integer | computed | Risk level via the [`RiskCriteria`](../risk-criteria.md) matrix |
| `existing_security_measures` | text | optional | Existing measures taken into account |
| `is_retained` | boolean | required, default true | Retained for workshop 4 |
| `retention_justification` | text | optional | Justification |
| `consolidated_risk_id` | relation | FK -> [Risk](../risk.md), optional | Risk consolidated into the register |
| `criteria_snapshot` | json | computed | Snapshot of the scale |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

## Creation and edition

A strategic scenario is a row of the page of workshop 3 (see [README, 8.6](README.md)).

- **Creation** asks for five fields on one screen : the name, the pair, the feared events the scenario leads to, the gravity and the likelihood. The study is known from the address and is never asked.
- **The pair** is picked among the pairs retained in workshop 2 for the same study (rule RE-08), **the feared events** among those of its security baseline. The pair a scenario is built on stays offered once set aside.
- **Gravity and likelihood** are picked by the name of their level on the impact and likelihood scales of the criteria of the assessment. No level reads *Not assessed*; the risk level is computed once both are given.
- **Edition** has two sections : *Strategic scenario* (name, pair, feared events, description, existing security measures) and *Gravity and likelihood* (the two levels, their justifications, and whether the scenario is retained for workshop 4, with the reason).
- `targeted_feared_event_ids` sets the feared events through the MCP tools.


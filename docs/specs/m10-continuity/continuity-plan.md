# ContinuityPlan

`continuity.models.plan.ContinuityPlan`

A business continuity, disaster recovery, crisis management or ICT continuity plan : what it covers, the strategy, when to activate it and the ordered [recovery steps](recovery-step.md) (ISO 22301 clause 8.4; ISO/IEC 27001:2022 A.5.29, A.5.30).

File: `continuity/models/plan.py`

`ScopedModel` : `reference` (prefix **`BCPL`**), `scopes`, `tags`, history. `LIFECYCLE_NAME = "continuity_plan"`. `workflow_perm_namespace = "continuity.plan"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `name` | string | required, max 255 | |
| `plan_type` | enum | required | `business_continuity`, `disaster_recovery`, `crisis_management`, `ict_continuity` |
| `owner` | relation | FK -> User, `SET_NULL`, optional | |
| `strategy` | text | optional | The recovery strategy (alternate site, manual workaround, failover...) |
| `activation_criteria` | text | optional | When to activate |
| `activities`, `essential_assets`, `support_assets`, `sites` | M2M | reverse `continuity_plans` | Coverage (RG-BCM-07) |
| `requirements` | M2M | `compliance.Requirement`, reverse `continuity_plans` | A.5.29, A.5.30, NIS2 21.2 c |
| `document` | relation | FK -> `documents.Policy`, `SET_NULL`, optional | The formal plan document |
| `exercise_frequency_months` | integer | 1 to 36, default 12 | |
| `approved_by`, `approved_at` | | not editable | RG-BCM-09 |
| `last_exercised_on` | date | not editable | RG-BCM-13 |
| `next_exercise_due` | date | indexed, not editable | RG-BCM-09 / RG-BCM-13 |
| `workflow_state` | string | default `draft` | |

## Computed

`recovery_minutes` (latest step target), `smallest_covered_rto_hours` (latest validated BIA), `rto_not_met` (RG-BCM-10), `is_exercise_overdue` (RG-BCM-13), `active_activation`.

## References

- [README.md](README.md) : RG-BCM-07 to RG-BCM-11

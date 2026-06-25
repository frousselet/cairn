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

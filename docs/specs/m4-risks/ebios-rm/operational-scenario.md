# OperationalScenario

`risks.models.ebios.operational_scenario.OperationalScenario`

Operational scenario: the technical breakdown of a strategic scenario describing the modus operandi against support assets. Reference prefix: `EOPS`.

## 4.4.1 Entity: OperationalScenario (Operational scenario)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required | Parent assessment |
| `strategic_scenario_id` | relation | FK -> [StrategicScenario](strategic-scenario.md), required | Parent strategic scenario |
| `reference` | string | required, unique, prefix EOPS | Code (e.g. EOPS-1) |
| `name` | string | required, max 255 | Title |
| `description` | text | required | Technical description |
| `targeted_support_assets` | M2M -> SupportAsset | required | Targeted support assets |
| `gravity_level` | integer | required | Severity (inherited from the parent by default) |
| `gravity_inherited` | boolean | required, default true | Indicates whether the severity is inherited |
| `gravity_override_justification` | text | optional | Justification if the severity is adjusted |
| `likelihood_v` | enum | required | `V1`, `V2`, `V3`, `V4` (grid B, [see README §2.8](README.md#28-anssi-scoring-grids)) |
| `likelihood_justification` | text | optional | Justification |
| `risk_level` | integer | computed | Risk level (mapped gravity x likelihood matrix) |
| `existing_controls` | text | optional | Existing technical controls |
| `existing_measures` | M2M -> Requirement | optional | Formalized measures (reuses Module 3) |
| `consolidated_risk_id` | relation | FK -> [Risk](../risk.md), optional | Risk consolidated into the register |
| `mitre_version` | string | optional | Referenced MITRE ATT&CK version (e.g. v15.1) |
| `criteria_snapshot` | json | computed | Snapshot |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

> Mapping of `likelihood_v` -> integer value used by the matrix: V1=1, V2=2, V3=3, V4=4.

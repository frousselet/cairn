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
| `mitre_version` | string | computed | Version of the MITRE ATT&CK catalogue the techniques of the scenario come from (e.g. 15.1). Recorded when the first technique with a MITRE entry is attached (rule RE-13), and kept afterwards |
| `criteria_snapshot` | json | computed | Snapshot |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

> Mapping of `likelihood_v` -> integer value used by the matrix: V1=1, V2=2, V3=3, V4=4.

## Creation and edition

An operational scenario is a row of the page of workshop 4 (see [README, 8.7](README.md)).

- **Creation** asks for four fields on one screen : the strategic scenario it details, among those retained in workshop 3 for the same study (rule RE-09), its name, the support assets it aims at, among those of the security baseline, and its operational likelihood (V1 to V4, *Not assessed* while it waits). The study is known from the address. The gravity is not asked : it is the one of the strategic scenario.
- **Edition** has two sections : *Operational scenario* (strategic scenario, name, targeted support assets, description, existing controls) and *Likelihood and gravity*. Unticking *Gravity inherited from parent* asks for a gravity, picked by the name of its level on the impact scale of the criteria, and for its justification (rule RE-10, which the form did not apply).
- `mitre_version` is not on the form : `AttackTechnique.save()` records it.
- `targeted_support_asset_ids` sets the targeted support assets through the MCP tools. `existing_measures` is written through the REST API only.


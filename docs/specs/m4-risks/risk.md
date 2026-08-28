# Risk

`risks.models.risk.Risk`

Identified risk, regardless of the originating methodology. Central entity of the risk register.

## 2.5 Entity: Risk (Risk)

Represents an identified risk, regardless of the originating methodology. It is the central entity of the risk register.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `assessment_id` | relation | FK → RiskAssessment, required | Source assessment |
| `reference` | string | required, unique | Reference code (e.g. RSK-001) |
| `name` | string | required, max 255 | Risk title |
| `description` | text | required | Narrative description of the risk scenario |
| `risk_source` | enum | required | `iso27005_analysis`, `ebios_strategic_scenario`, `ebios_operational_scenario`, `incident`, `audit`, `compliance`, `manual` |
| `source_entity_id` | UUID | optional | Identifier of the source entity (ISO27005Risk, StrategicScenario, etc.) |
| `source_entity_type` | string | optional | Type of the source entity |
| `affected_essential_assets` | relation | M2M → EssentialAsset | Impacted essential assets |
| `affected_support_assets` | relation | M2M → SupportAsset | Support assets concerned |
| `impact_confidentiality` | boolean | required, default false | Impact on confidentiality |
| `impact_integrity` | boolean | required, default false | Impact on integrity |
| `impact_availability` | boolean | required, default false | Impact on availability |
| `initial_likelihood` | integer | required | Initial (gross) likelihood: value on the scale |
| `initial_impact` | integer | required | Initial (gross) impact: value on the scale |
| `initial_risk_level` | integer | computed | Initial risk level (via the matrix) |
| `current_likelihood` | integer | optional | Current likelihood (after existing measures) |
| `current_impact` | integer | optional | Current impact |
| `current_risk_level` | integer | computed | Current risk level |
| `residual_likelihood` | integer | optional | Residual likelihood (after planned treatment) |
| `residual_impact` | integer | optional | Residual impact |
| `residual_risk_level` | integer | computed | Residual risk level |
| `treatment_decision` | enum | optional | `accept`, `mitigate`, `transfer`, `avoid`, `not_decided` |
| `treatment_justification` | text | optional | Justification for the treatment decision |
| `risk_owner_id` | relation | FK → User, required | Risk owner (decision-maker) |
| `linked_measures` | relation | M2M → Measure | Existing measures covering this risk |
| `linked_requirements` | relation | M2M → Requirement | Associated compliance requirements |
| `linked_incidents` | relation | M2M → Incident | Linked incidents |
| `priority` | enum | optional | `low`, `medium`, `high`, `critical` |
| `status` | enum | required | `identified`, `analyzed`, `evaluated`, `treatment_planned`, `treatment_in_progress`, `treated`, `accepted`, `closed`, `monitoring` |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

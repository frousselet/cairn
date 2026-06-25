# StudyFramework

`risks.models.ebios.study_framework.StudyFramework`

Formalizes the prerequisites required by ANSSI before workshop 1: participants, frameworks, assumptions, constraints. Reference prefix: `EFRA`.

## 4.0.1 Entity: StudyFramework (Study framework)

Formalizes the prerequisites required by ANSSI before workshop 1: participants, frameworks, assumptions, constraints.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required, unique | Parent assessment (1 framework per assessment) |
| `reference` | string | required, unique, prefix EFRA | Code (e.g. EFRA-1) |
| `mission_statement` | text | required | Description of the mission under study |
| `business_perimeter` | text | required | Business perimeter (activities, processes) |
| `technical_perimeter` | text | required | Technical perimeter (support assets, infrastructures) |
| `temporal_perimeter` | text | required | Time horizon (study start / end date) |
| `financial_envelope` | decimal | optional | Allocated budget envelope |
| `participants` | M2M -> User | optional | Study participants |
| `participants_external` | json | optional | List of external participants (name, role, organization) |
| `applicable_frameworks` | M2M -> Framework | optional | Applicable frameworks (ISO 27001, NIS2, GDPR, etc.) |
| `assumptions` | text | optional | Assumptions retained |
| `constraints` | text | optional | Constraints (organizational, technical, legal) |
| `expected_deliverables` | text | optional | Expected deliverables |
| `status` | enum | required | `draft`, `validated` |
| `created_by`, `created_at`, `updated_at` | - | auto | `BaseModel` standard |

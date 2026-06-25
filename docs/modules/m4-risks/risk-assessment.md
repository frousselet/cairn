# RiskAssessment

`risks.models.risk_assessment.RiskAssessment`

Risk assessment campaign conducted following one or the other methodology (ISO 27005 or EBIOS RM). Root entity that groups together all analysis elements.

## 2.1 Entity: RiskAssessment (Risk assessment)

Represents a risk assessment campaign, conducted following one or the other methodology. It is the root entity that groups together all analysis elements.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Attached scope |
| `reference` | string | required, unique | Reference code (e.g. RA-2026-001) |
| `name` | string | required, max 255 | Assessment title |
| `description` | text | optional | Description and context |
| `methodology` | enum | required | `iso27005`, `ebios_rm` |
| `assessment_date` | date | required | Date carried out |
| `assessor_id` | relation | FK → User, required | Assessment owner |
| `team_members` | relation | M2M → User | Members of the assessment team |
| `risk_criteria_id` | relation | FK → RiskCriteria, required | Applied risk criteria |
| `status` | enum | required | `draft`, `in_progress`, `completed`, `validated`, `archived` |
| `validated_by` | relation | FK → User, optional | Validator |
| `validated_at` | datetime | optional | Validation date |
| `next_review_date` | date | optional | Next review date |
| `summary` | text | optional | Summary of results |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

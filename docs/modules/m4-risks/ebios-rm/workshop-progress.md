# EbiosWorkshopProgress

`risks.models.ebios.workshop_progress.EbiosWorkshopProgress`

Per-workshop progress tracker. 6 instances created automatically per assessment (W0 to W5). Reference prefix: `EWSP`.

## 4.0.2 Entity: EbiosWorkshopProgress (Workshop progress)

Per-workshop progress tracker. 6 instances created automatically per assessment (W0 to W5).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Unique identifier |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), required | Parent assessment |
| `reference` | string | required, unique, prefix EWSP | Code (e.g. EWSP-1) |
| `workshop_number` | integer | required, 0 to 5 | Workshop number |
| `iteration_type` | enum | required | `strategic`, `operational` |
| `iteration_number` | integer | required, >= 1 | Cycle iteration number |
| `status` | enum | required | `not_started`, `in_progress`, `under_review`, `validated`, `rejected` |
| `started_at` | datetime | optional | Start date |
| `validated_by_id` | relation | FK -> User, optional | Validator |
| `validated_at` | datetime | optional | Validation date |
| `rejection_reason` | text | optional | Rejection reason (if `status = rejected`) |
| `deliverables_summary` | text | optional | Summary of the deliverables produced |
| `attachments` | M2M -> File | optional | Attachments (workshop reports) |
| `notes` | text | optional | Facilitator notes |
| `created_by`, `created_at`, `updated_at` | - | auto | Standard |

> Uniqueness constraint: `(assessment_id, workshop_number, iteration_type, iteration_number)`.

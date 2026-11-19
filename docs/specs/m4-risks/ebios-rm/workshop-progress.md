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

> Permissions: starting a workshop and submitting it for review ask for `risks.ebios_assessment.update`. Its verdict, validation or rejection, asks for `risks.ebios_assessment.validate`: the `ebios_workshop` lifecycle names that permission on both transitions, so the workshop page, the generic transition endpoint and the MCP server (a `status` written by `create_ebios_workshop` or `update_ebios_workshop` included) all ask for it.

## Completeness

A workshop is validated on its deliverables (rule RE-04). `EbiosWorkshopProgress.COMPLETENESS` (`core/completeness.py`) declares them, each requirement for one workshop (`when`) :

| Workshop | Requirement | Key | Blocking |
|---|---|---|---|
| 1 | The security baseline names at least one essential asset | `w1_essential_assets` | yes |
| 1 | The security baseline names at least one support asset | `w1_support_assets` | yes |
| 1 | Each essential asset of the baseline has a feared event | `w1_feared_events` | yes |
| 1 | Each feared event has a gravity level | `w1_gravity` | no |
| 1 | The security baseline names at least one business value (activity) | `w1_business_values` | no |
| 1 | The security baseline names at least one baseline reference | `w1_baseline_references` | no |

- The page of the workshop lists what is missing under **To complete**, each line leading to the card where it is done.
- While a blocking requirement is missing, the workshop cannot move to `validated` : the workshop page, the generic transition endpoint and the MCP server (a `status` written by `update_ebios_workshop` included) answer *Before moving to "Validated", this remains to be done : ...*.
- `GET /api/v1/risks/ebios/workshops/{id}/` and `get_ebios_workshop` return `completeness` : `{"complete", "can_advance", "missing": [{"key", "label", "blocking"}]}`.
- The requirements of workshops 0 and 2 to 5 are declared as each workshop is brought to the usability standard; until then these workshops are validated as before.


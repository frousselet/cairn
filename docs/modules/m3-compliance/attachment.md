# Attachment

`compliance.models.assessment.AssessmentResultAttachment`

Documentary attachment associated with a [compliance assessment](compliance-assessment.md) result or with an [action plan](compliance-action-plan.md).

## Sub-entity: Attachment

Used to store the documentary evidence associated with compliance assessments.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `entity_type` | string | required | Parent entity type (e.g. `AssessmentResult`, `ComplianceActionPlan`) |
| `entity_id` | UUID | required | Parent entity identifier |
| `file_name` | string | required, max 255 | File name |
| `file_path` | string | required | Storage path |
| `file_size` | integer | required | Size in bytes |
| `mime_type` | string | required | MIME type |
| `description` | text | optional | Attachment description |
| `uploaded_by` | relation | FK → User, required | User who uploaded the file |
| `created_at` | datetime | auto | Creation date |

# SwotAnalysis

`context.models.swot.SwotAnalysis`

Represents a SWOT analysis carried out for a given scope.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `name` | string | required, max 255 | Analysis title |
| `description` | text | optional | Analysis context |
| `analysis_date` | date | required | Date carried out |
| `workflow_state` | enum | required, default `draft` | Unified lifecycle: `draft`, `pending`, `validated`, `archived`. See [governance/workflow.md](../governance/workflow.md). |
| `validated_by` | relation | FK → User | Validator |
| `validated_at` | datetime | optional | Validation date |
| `items` | relation | O2M → SwotItem | SWOT items |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## SwotItem

Sub-entity: SWOT item.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `swot_analysis_id` | relation | FK → SwotAnalysis, required | Parent analysis |
| `quadrant` | enum | required | `strength`, `weakness`, `opportunity`, `threat` |
| `description` | text | required | Item description |
| `impact_level` | enum | required | `low`, `medium`, `high` |
| `related_issues` | relation | M2M → Issue | Associated issues |
| `related_objectives` | relation | M2M → Objective | Associated objectives |
| `order` | integer | required | Display order within the quadrant |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

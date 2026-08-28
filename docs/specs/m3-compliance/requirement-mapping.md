# RequirementMapping

`compliance.models.mapping.RequirementMapping`

Mapping between two [Requirements](requirement.md) from different frameworks.

## Entity: RequirementMapping (Inter-framework mapping)

Represents a mapping between two requirements from different frameworks. Allows compliance efforts to be shared and overlaps to be visualized.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `source_requirement_id` | relation | FK → Requirement, required | Source requirement |
| `target_requirement_id` | relation | FK → Requirement, required | Target requirement |
| `mapping_type` | enum | required | `equivalent`, `partial_overlap`, `includes`, `included_by`, `related` |
| `coverage_level` | enum | optional | `full`, `partial`, `minimal` |
| `description` | text | optional | Mapping description |
| `justification` | text | optional | Mapping justification |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

> Uniqueness constraint: the pair (`source_requirement_id`, `target_requirement_id`) must be unique.
> Constraint: `source_requirement_id` and `target_requirement_id` must belong to different frameworks.

**Mapping types:**

| Type | Description |
|---|---|
| `equivalent` | The two requirements are equivalent (mutual coverage) |
| `partial_overlap` | The requirements partially overlap |
| `includes` | The source requirement includes / covers the target requirement |
| `included_by` | The source requirement is included in / covered by the target requirement |
| `related` | The requirements are related without direct overlap |

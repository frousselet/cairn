# Section

`compliance.models.section.Section`

Hierarchical structure of a [Framework](framework.md) (chapters, sections, sub-sections).

## Entity: Section (Framework section / chapter)

Represents the hierarchical structure of a framework (chapters, sections, sub-sections). Allows the plan of the original framework to be reproduced faithfully.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `framework_id` | relation | FK → Framework, required | Parent framework |
| `parent_section_id` | relation | FK → Section, optional | Parent section (hierarchy) |
| `reference` | string | required | Section number (e.g. "A.5", "4.2.1") |
| `name` | string | required, max 255 | Section title |
| `description` | text | optional | Section description or text |
| `order` | integer | required | Display order within the parent |
| `compliance_level` | decimal | computed, 0-100 | Aggregated compliance level of the section (%) |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

> Constraint: the combination (`framework_id`, `reference`) must be unique.

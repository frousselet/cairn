# Objective

`context.models.objective.Objective`

Represents an information security or compliance objective.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `reference` | string | required, unique | Reference code (e.g. OBJ-001) |
| `name` | string | required, max 255 | Objective title |
| `description` | text | optional | Detailed description |
| `category` | enum | required | `confidentiality`, `integrity`, `availability`, `compliance`, `operational`, `strategic` |
| `type` | enum | required | `security`, `compliance`, `business`, `other` |
| `target_value` | string | optional | Measurable target value |
| `current_value` | string | optional | Current value |
| `unit` | string | optional | Unit of measurement |
| `measurement_method` | text | optional | Measurement method |
| `measurement_frequency` | enum | optional | `monthly`, `quarterly`, `semi_annual`, `annual` |
| `target_date` | date | optional | Target achievement date |
| `owner_id` | relation | FK → User, required | Objective owner |
| `status` | enum | required | `draft`, `active`, `achieved`, `not_achieved`, `cancelled` |
| `progress_percentage` | integer | optional, 0-100 | Progress percentage |
| `related_issues` | relation | M2M → Issue | Issues addressed |
| `related_stakeholders` | relation | M2M → Stakeholder | Stakeholders concerned |
| `parent_objective_id` | relation | FK → Objective, optional | Parent objective (hierarchy) |
| `linked_measures` | relation | M2M → Measure | Measures contributing to the objective (Measures module) |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

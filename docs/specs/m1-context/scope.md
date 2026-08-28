# Scope

`context.models.scope.Scope`

Represents the scope covered by the GRC framework.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `name` | string | required, max 255 | Scope name |
| `description` | text | required | Detailed description of the scope |
| `version` | string | required | Version of the scope document |
| `workflow_state` | enum | required, default `draft` | Standardised perimeter lifecycle: `draft` → `definition` → `validation` → `in_force` → `review` (periodic, looping back to `in_force`), with `archived` as the from-any exit (and restore to `draft`). `in_force` and `review` count in reports and are linkable; only `draft` is deletable. Runs the [standardised lifecycle engine](../governance/lifecycle.md) (`Scope.LIFECYCLE_NAME = "scope"`), not the default workflow. |
| `boundaries` | text | optional | Scope boundaries and exclusions |
| `justification_exclusions` | text | optional | Justification of exclusions |
| `geographic_scope` | text | optional | Geographic scope |
| `organizational_scope` | text | optional | Organizational scope |
| `technical_scope` | text | optional | Technical scope |
| `applicable_standards` | relation | M2M → Referential | Applicable standards |
| `effective_date` | date | optional | Effective date |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

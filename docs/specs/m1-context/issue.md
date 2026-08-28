# Issue

`context.models.issue.Issue`

Represents an internal or external issue that may influence the organization's ability to achieve the intended outcomes of its GRC framework.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `name` | string | required, max 255 | Issue title |
| `description` | text | optional | Detailed description |
| `type` | enum | required | `internal`, `external` |
| `category` | enum | required | See list below |
| `impact_level` | enum | required | `low`, `medium`, `high`, `critical` |
| `trend` | enum | optional | `improving`, `stable`, `degrading` |
| `source` | string | optional | Source of the issue identification |
| `related_stakeholders` | relation | M2M → Stakeholder | Linked stakeholders |
| `review_date` | date | optional | Next review date |
| `status` | enum | required | `identified`, `active`, `monitored`, `closed` |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

**Issue categories (`category` values):**

- *Internal issues:* `strategic`, `organizational`, `human_resources`, `technical`, `financial`, `cultural`
- *External issues:* `political`, `economic`, `social`, `technological`, `legal`, `environmental`, `competitive`, `regulatory`

> Note: Categories must be configurable by the administrator (add/edit/delete).

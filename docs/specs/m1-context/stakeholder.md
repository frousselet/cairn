# Stakeholder

`context.models.stakeholder.Stakeholder`

Represents any person or organization that can affect, be affected by, or perceive itself to be affected by a decision or activity.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `scope_id` | relation | FK → Scope, required | Linked scope |
| `name` | string | required, max 255 | Stakeholder name |
| `type` | enum | required | `internal`, `external` |
| `category` | enum | required | See list below |
| `description` | text | optional | Description |
| `contact_name` | string | optional | Primary contact name |
| `contact_email` | string | optional, email format | Contact email |
| `contact_phone` | string | optional | Contact phone |
| `influence_level` | enum | required | `low`, `medium`, `high` |
| `interest_level` | enum | required | `low`, `medium`, `high` |
| `expectations` | relation | O2M → StakeholderExpectation | Expectations and requirements |
| `related_issues` | relation | M2M → Issue | Associated issues |
| `status` | enum | required | `active`, `inactive` |
| `review_date` | date | optional | Next review date |
| `created_by` | relation | FK → User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

**Stakeholder categories (`category` values):**

`executive_management`, `employees`, `customers`, `suppliers`, `partners`, `regulators`, `shareholders`, `insurers`, `public`, `competitors`, `unions`, `auditors`, `other`

> Note: Categories must be configurable by the administrator.

## StakeholderExpectation

Sub-entity: expectation of a stakeholder.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `stakeholder_id` | relation | FK → Stakeholder, required | Parent stakeholder |
| `description` | text | required | Description of the expectation or requirement |
| `type` | enum | required | `requirement`, `expectation`, `need` |
| `priority` | enum | required | `low`, `medium`, `high`, `critical` |
| `is_applicable` | boolean | required, default true | Applicable to the scope |
| `linked_requirements` | relation | M2M → Requirement | Linked compliance requirements (Compliance module) |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

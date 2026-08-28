# IsmsChange

`reports.models.management_review.IsmsChange`

Formalised ISMS change decided during a management review (ISO 27001:2022 clause 9.3.3 requirement on "any need for changes to the ISMS").

Clause 9.3.3 requirement : "any need for changes to the ISMS". Formalisation of the changes decided during a review.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (prefix `ICHG`), unique | e.g. `ICHG-1` |
| `review` | FK → ManagementReview | required, CASCADE | Originating review |
| `change_type` | enum | required | `scope`, `policy`, `control`, `organization`, `resource`, `process`, `other` |
| `title` | string | required, max 255 | Title |
| `description` | text | required | Description of the change |
| `impact_analysis` | text | optional | Impact analysis (interested parties, risks, assets) |
| `affected_scopes` | M2M → Scope | optional | Affected scopes |
| `affected_frameworks` | M2M → Framework | optional | Affected frameworks |
| `affected_policies` | text | optional | List of policies to revise (free text, future evolution towards a `Policy` model) |
| `status` | enum | required | `proposed`, `approved`, `in_progress`, `implemented`, `rejected` |
| `owner` | FK → User | required | Person responsible for implementation |
| `target_date` | date | optional | Target date |
| `implemented_at` | date | optional | Actual implementation date |
| `created_at`, `updated_at` | datetime | auto | |

**History** : `HistoricalRecords`.

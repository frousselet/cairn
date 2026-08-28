# StakeholderFeedback

`context.models.stakeholder_feedback.StakeholderFeedback`

Formalised stakeholder feedback channel required by ISO 27001:2022 clause 9.3.2.e, distinct from permanent `StakeholderExpectation` records.

Formalisation of the feedback channel required by clause 9.3.2.e (distinct from `StakeholderExpectation` records, which are permanent requirements).

File : `context/models/stakeholder_feedback.py`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (prefix `FBCK`), unique | e.g. `FBCK-1` |
| `stakeholder` | FK → Stakeholder | required, CASCADE | Originating stakeholder |
| `channel` | enum | required | `survey`, `meeting`, `complaint`, `email`, `audit`, `incident`, `other` |
| `received_date` | date | required | Date received |
| `subject` | string | required, max 255 | Subject of the feedback |
| `content` | text | required | Detailed content (HTML rich text) |
| `sentiment` | enum | optional | `positive`, `neutral`, `negative`, `mixed` |
| `severity` | enum | optional | `low`, `medium`, `high`, `critical` |
| `status` | enum | required | `new`, `under_review`, `addressed`, `closed` |
| `response` | text | optional | Response provided |
| `linked_issues` | M2M → Issue | optional | Associated issues |
| `linked_expectations` | M2M → StakeholderExpectation | optional | Reinforced expectations |
| `scopes` | M2M → Scope | required, at least 1 | Relevant scopes |
| `created_by`, `created_at`, `updated_at` | auto | | Traceability |

**History** : `HistoricalRecords`.

**Aggregation in a review** : section 5 of the export becomes :
- a table of the `StakeholderFeedback` over the period (priority given to `negative` + `critical`)
- plus the current view of applicable expectations (unchanged).

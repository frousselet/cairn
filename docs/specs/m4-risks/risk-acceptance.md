# RiskAcceptance

`risks.models.acceptance.RiskAcceptance`

Formalizes the acceptance of a risk by its owner, in accordance with the organization's decision-making process.

## 2.8 Entity: RiskAcceptance (Risk acceptance)

Formalizes the acceptance of a risk by the risk owner, in accordance with the organization's decision-making process.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `risk_id` | relation | FK → Risk, required | Accepted risk |
| `accepted_by` | relation | FK → User, required | Accepting party (risk owner) |
| `accepted_at` | datetime | required | Acceptance date |
| `risk_level_at_acceptance` | integer | required | Risk level at the time of acceptance |
| `justification` | text | required | Justification for the acceptance |
| `conditions` | text | optional | Acceptance conditions (e.g. quarterly review) |
| `valid_until` | date | optional | Validity date of the acceptance |
| `review_date` | date | required | Mandatory review date |
| `status` | enum | required | `active`, `expired`, `revoked`, `renewed` |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

# ManagementReviewComment

`reports.models.management_review.ManagementReviewComment`

Discussion thread attached to a [ManagementReview](management-review.md), used for pre-meeting arbitration, cancellation rationale, etc.

Discussion thread attached to a review (useful for pre-meeting arbitration, cancellation rationale, etc.).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `review` | FK → ManagementReview | required, CASCADE | |
| `author` | FK → User | required, SET_NULL | |
| `content` | text | required | HTML rich text |
| `created_at` | datetime | auto | |

Same pattern as `ComplianceActionPlanComment`.

# ManagementReviewComment

`reports.models.management_review.ManagementReviewComment`

Discussion thread attached to a [ManagementReview](management-review.md), used for pre-meeting arbitration, cancellation rationale, etc.

Fil de discussion attaché à une revue (utile pour arbitrage pré-réunion, justification d'annulation, etc.).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `review` | FK → ManagementReview | requis, CASCADE | |
| `author` | FK → User | requis, SET_NULL | |
| `content` | text | requis | HTML rich text |
| `created_at` | datetime | auto | |

Pattern identique à `ComplianceActionPlanComment`.

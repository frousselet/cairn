# ManagementReviewParticipant

`reports.models.management_review.ManagementReviewParticipant`

Enriched join table between a [ManagementReview](management-review.md) and internal or external participants.

Enriched join table between `ManagementReview` and `User` (internal or external participants).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `review` | FK → ManagementReview | required, `on_delete=CASCADE` | Parent review |
| `user` | FK → User | optional | Internal participant (null for external) |
| `external_name` | string | max 255, optional | Plain-text name for an external participant |
| `external_role` | string | max 255, optional | Plain-text role for an external participant |
| `role` | enum | required | `facilitator`, `decision_maker`, `contributor`, `observer` |
| `attended` | boolean | default false | Attended the meeting |
| `signature_data` | text | optional | Signature (base64 PNG or text) for the DOCX |

> Constraint : `user` or (`external_name` + `external_role`) must be provided (`CheckConstraint`).

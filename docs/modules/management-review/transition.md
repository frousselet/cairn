# ManagementReviewTransition

`reports.models.management_review_transition.ManagementReviewTransition`

Status transition journal for a [ManagementReview](management-review.md), aligned with `ComplianceActionPlanTransition`.

Status transition journal, aligned with `ComplianceActionPlanTransition`.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `review` | FK → ManagementReview | CASCADE |
| `from_status`, `to_status` | enum | - |
| `user` | FK → User | Author |
| `comment` | text | Comment required for `cancelled` |
| `created_at` | datetime | auto |

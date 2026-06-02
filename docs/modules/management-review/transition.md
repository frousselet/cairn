# ManagementReviewTransition

`reports.models.management_review_transition.ManagementReviewTransition`

Status transition journal for a [ManagementReview](management-review.md), aligned with `ComplianceActionPlanTransition`.

Journal des transitions de statut, aligné sur `ComplianceActionPlanTransition`.

| Champ | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `review` | FK → ManagementReview | CASCADE |
| `from_status`, `to_status` | enum | - |
| `user` | FK → User | Auteur |
| `comment` | text | Commentaire obligatoire pour `cancelled` |
| `created_at` | datetime | auto |

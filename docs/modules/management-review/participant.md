# ManagementReviewParticipant

`reports.models.management_review.ManagementReviewParticipant`

Enriched join table between a [ManagementReview](management-review.md) and internal or external participants.

Table de liaison enrichie entre `ManagementReview` et `User` (participants internes ou externes).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `review` | FK → ManagementReview | requis, `on_delete=CASCADE` | Revue parente |
| `user` | FK → User | optionnel | Participant interne (null pour externes) |
| `external_name` | string | max 255, optionnel | Nom en clair pour participant externe |
| `external_role` | string | max 255, optionnel | Fonction en clair pour participant externe |
| `role` | enum | requis | `facilitator`, `decision_maker`, `contributor`, `observer` |
| `attended` | boolean | défaut false | A assisté à la réunion |
| `signature_data` | text | optionnel | Signature (base64 PNG ou texte) pour le DOCX |

> Contrainte : `user` ou (`external_name` + `external_role`) doit être renseigné (`CheckConstraint`).

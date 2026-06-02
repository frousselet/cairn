# RiskAcceptance

`risks.models.acceptance.RiskAcceptance`

Formalise l'acceptation d'un risque par son propriétaire, conformément au processus décisionnel de l'organisme.

## 2.8 Entité : RiskAcceptance (Acceptation de risque)

Formalise l'acceptation d'un risque par le propriétaire du risque, conformément au processus décisionnel de l'organisme.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `risk_id` | relation | FK → Risk, requis | Risque accepté |
| `accepted_by` | relation | FK → User, requis | Acceptant (propriétaire du risque) |
| `accepted_at` | datetime | requis | Date d'acceptation |
| `risk_level_at_acceptance` | integer | requis | Niveau de risque au moment de l'acceptation |
| `justification` | text | requis | Justification de l'acceptation |
| `conditions` | text | optionnel | Conditions d'acceptation (ex. revue trimestrielle) |
| `valid_until` | date | optionnel | Date de validité de l'acceptation |
| `review_date` | date | requis | Date de revue obligatoire |
| `status` | enum | requis | `active`, `expired`, `revoked`, `renewed` |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

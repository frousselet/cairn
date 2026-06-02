# EbiosWorkshopProgress

`risks.models.ebios.workshop_progress.EbiosWorkshopProgress`

Tracker de progression par atelier. 6 instances créées automatiquement par appréciation (W0 à W5). Préfixe de référence : `EWSP`.

## 4.0.2 Entité : EbiosWorkshopProgress (Suivi atelier)

Tracker de progression par atelier. 6 instances créées automatiquement par appréciation (W0 à W5).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), requis | Appréciation parente |
| `reference` | string | requis, unique, préfixe EWSP | Code (ex. EWSP-1) |
| `workshop_number` | integer | requis, 0 à 5 | Numéro d'atelier |
| `iteration_type` | enum | requis | `strategic`, `operational` |
| `iteration_number` | integer | requis, >= 1 | Numéro d'itération du cycle |
| `status` | enum | requis | `not_started`, `in_progress`, `under_review`, `validated`, `rejected` |
| `started_at` | datetime | optionnel | Date de démarrage |
| `validated_by_id` | relation | FK -> User, optionnel | Validateur |
| `validated_at` | datetime | optionnel | Date de validation |
| `rejection_reason` | text | optionnel | Motif de rejet (si `status = rejected`) |
| `deliverables_summary` | text | optionnel | Synthèse des livrables produits |
| `attachments` | M2M -> File | optionnel | Pièces jointes (rapports atelier) |
| `notes` | text | optionnel | Notes de l'animateur |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |

> Contrainte d'unicité : `(assessment_id, workshop_number, iteration_type, iteration_number)`.

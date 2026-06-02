# RiskTreatmentPlan

`risks.models.treatment.RiskTreatmentPlan`

Plan de traitement listant les actions associées à un risque.

## 2.6 Entité : RiskTreatmentPlan (Plan de traitement du risque)

Représente les actions de traitement associées à un risque.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `risk_id` | relation | FK → Risk, requis | Risque traité |
| `reference` | string | requis, unique | Code de référence (ex. PTR-001) |
| `name` | string | requis, max 255 | Intitulé du plan |
| `description` | text | optionnel | Description détaillée |
| `treatment_type` | enum | requis | `mitigate`, `transfer`, `avoid` |
| `actions` | relation | O2M → TreatmentAction | Actions de traitement |
| `expected_residual_likelihood` | integer | optionnel | Vraisemblance résiduelle attendue |
| `expected_residual_impact` | integer | optionnel | Impact résiduel attendu |
| `cost_estimate` | decimal | optionnel | Estimation du coût global |
| `owner_id` | relation | FK → User, requis | Responsable du plan |
| `start_date` | date | optionnel | Date de début |
| `target_date` | date | requis | Date cible d'achèvement |
| `completion_date` | date | optionnel | Date d'achèvement effective |
| `progress_percentage` | integer | optionnel, 0-100 | Avancement global |
| `status` | enum | requis | `planned`, `in_progress`, `completed`, `cancelled`, `overdue` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

## TreatmentAction

`risks.models.treatment.TreatmentAction`

### 2.7 Sous-entité : TreatmentAction (Action de traitement)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `treatment_plan_id` | relation | FK → RiskTreatmentPlan, requis | Plan de traitement parent |
| `description` | text | requis | Description de l'action |
| `owner_id` | relation | FK → User, requis | Responsable de l'action |
| `target_date` | date | requis | Date cible |
| `completion_date` | date | optionnel | Date d'achèvement |
| `linked_measures` | relation | M2M → Measure | Mesures associées (Module Mesures) |
| `status` | enum | requis | `planned`, `in_progress`, `completed`, `cancelled` |
| `order` | integer | requis | Ordre d'exécution |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

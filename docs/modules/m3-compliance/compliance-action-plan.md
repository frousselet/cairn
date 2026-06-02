# ComplianceActionPlan

`compliance.models.action_plan.ComplianceActionPlan`

Plan d'action visant à corriger les écarts de conformité constatés lors d'une [évaluation](compliance-assessment.md).

## Entité : ComplianceActionPlan (Plan d'action de conformité)

Représente un plan d'action visant à corriger les écarts de conformité constatés lors d'une évaluation.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `reference` | string | requis, unique | Code de référence (ex. PAC-001) |
| `name` | string | requis, max 255 | Intitulé du plan d'action |
| `description` | text | optionnel | Description détaillée |
| `assessment_id` | relation | FK → ComplianceAssessment, optionnel | Évaluation source |
| `requirement_id` | relation | FK → Requirement, optionnel | Exigence concernée |
| `gap_description` | text | requis | Description de l'écart à combler |
| `remediation_plan` | text | requis | Plan de remédiation |
| `priority` | enum | requis | `low`, `medium`, `high`, `critical` |
| `owner_id` | relation | FK → User, requis | Responsable de l'action |
| `start_date` | date | optionnel | Date de début prévue |
| `target_date` | date | requis | Date cible d'achèvement |
| `completion_date` | date | optionnel | Date d'achèvement effective |
| `progress_percentage` | integer | optionnel, 0-100 | Pourcentage d'avancement |
| `cost_estimate` | decimal | optionnel | Estimation du coût |
| `linked_measures` | relation | M2M → Measure | Mesures à mettre en place (Module Mesures) |
| `status` | enum | requis | `planned`, `in_progress`, `completed`, `cancelled`, `overdue` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

# PACSMeasure

`risks.models.ebios.pacs_measure.PACSMeasure`

Mesure du PACS (Plan d'Amélioration Continue de la Sécurité). Préfixe de référence : `EPAC`.

## 4.5.2 Entité : PACSMeasure (Mesure du PACS)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `summary_id` | relation | FK -> [EbiosSummary](ebios-summary.md), requis | Synthèse parente |
| `reference` | string | requis, unique, préfixe EPAC | Code (ex. EPAC-1) |
| `name` | string | requis, max 255 | Intitulé de la mesure |
| `description` | text | requis | Description |
| `measure_type` | enum | requis | `governance`, `protection`, `defense`, `resilience`, `awareness` |
| `linked_treatment_plans` | M2M -> [RiskTreatmentPlan](../risk-treatment-plan.md) | optionnel | Plans de traitement portant la mesure |
| `linked_baseline_gaps` | M2M -> [BaselineGap](baseline-gap.md) | optionnel | Écarts au socle traités par la mesure |
| `linked_requirements` | M2M -> Requirement | optionnel | Exigences de conformité couvertes |
| `owner_id` | relation | FK -> User, requis | Responsable de la mesure |
| `start_date` | date | optionnel | Date de début |
| `target_date` | date | requis | Date cible |
| `completion_date` | date | optionnel | Date de réalisation effective |
| `cost_estimate` | decimal | optionnel | Coût estimé |
| `expected_gain` | text | optionnel | Gain attendu (réduction de risque) |
| `priority` | enum | requis | `low`, `medium`, `high`, `critical` |
| `status` | enum | requis | `planned`, `in_progress`, `completed`, `cancelled`, `overdue` |
| `progress_percentage` | integer | optionnel, 0 à 100 | Avancement |
| `order` | integer | requis | Ordre d'affichage dans le PACS |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |

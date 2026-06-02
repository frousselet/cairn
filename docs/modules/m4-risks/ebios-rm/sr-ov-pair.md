# RiskSourceObjectivePair

`risks.models.ebios.sr_ov_pair.RiskSourceObjectivePair`

Couple SR/OV : association formelle d'une source de risque et d'un objectif visé, évaluée en pertinence. Préfixe de référence : `ESOV`.

## 4.2.3 Entité : RiskSourceObjectivePair (Couple SR/OV)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), requis | Appréciation parente |
| `reference` | string | requis, unique, préfixe ESOV | Code (ex. ESOV-1) |
| `risk_source_id` | relation | FK -> [RiskSource](risk-source.md), requis | SR |
| `targeted_objective_id` | relation | FK -> [TargetedObjective](targeted-objective.md), requis | OV |
| `relevance` | enum | requis | `low`, `medium`, `high`, `critical` |
| `relevance_justification` | text | optionnel | Justification |
| `priority_score` | integer | calculé, 1 à 4 | Score agrégé : f(`risk_source.threat_level`, `relevance`) |
| `is_retained` | boolean | requis, défaut true | Retenu pour l'atelier 3 |
| `retention_justification` | text | optionnel | Justification |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |

> Contrainte d'unicité : `(assessment_id, risk_source_id, targeted_objective_id)`.

# EbiosSummary

`risks.models.ebios.ebios_summary.EbiosSummary`

Synthèse de l'appréciation EBIOS RM (atelier 5). Une seule par appréciation. Préfixe de référence : `ESUM`.

## 4.5.1 Entité : EbiosSummary (Synthèse de l'appréciation)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), requis, unique | Appréciation parente |
| `reference` | string | requis, unique, préfixe ESUM | Code (ex. ESUM-1) |
| `residual_risk_strategy` | text | requis | Stratégie globale de traitement du risque résiduel |
| `monitoring_plan` | text | optionnel | Plan de suivi et d'amélioration continue |
| `pacs_summary` | text | optionnel | Synthèse narrative du PACS |
| `risk_mapping_before` | json | calculé | Snapshot cartographie des risques avant traitement |
| `risk_mapping_after` | json | calculé | Snapshot cartographie après traitement |
| `next_strategic_cycle_date` | date | optionnel | Prochaine itération stratégique prévue |
| `next_operational_cycle_date` | date | optionnel | Prochaine itération opérationnelle prévue |
| `validated_by_id` | relation | FK -> User, optionnel | Validateur direction générale |
| `validated_at` | datetime | optionnel | Date de validation |
| `status` | enum | requis | `draft`, `in_progress`, `under_review`, `validated` |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |

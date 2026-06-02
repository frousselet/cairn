# StrategicScenario

`risks.models.ebios.strategic_scenario.StrategicScenario`

Scénario stratégique : chemin d'attaque haut niveau depuis une SR vers un OV en passant par l'écosystème. Préfixe de référence : `ESTS`.

## 4.3.2 Entité : StrategicScenario (Scénario stratégique)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), requis | Appréciation parente |
| `reference` | string | requis, unique, préfixe ESTS | Code (ex. ESTS-1) |
| `name` | string | requis, max 255 | Intitulé |
| `description` | text | requis | Description narrative |
| `sr_ov_pair_id` | relation | FK -> [RiskSourceObjectivePair](sr-ov-pair.md), requis | Couple SR/OV source |
| `targeted_feared_events` | M2M -> [FearedEvent](feared-event.md) | requis | Événements redoutés visés |
| `gravity_level` | integer | requis | Gravité (échelle impact) |
| `gravity_justification` | text | optionnel | Justification |
| `likelihood_level` | integer | requis | Vraisemblance stratégique (échelle likelihood) |
| `likelihood_justification` | text | optionnel | Justification |
| `risk_level` | integer | calculé | Niveau de risque via matrice [`RiskCriteria`](../risk-criteria.md) |
| `existing_security_measures` | text | optionnel | Mesures existantes prises en compte |
| `is_retained` | boolean | requis, défaut true | Retenu pour l'atelier 4 |
| `retention_justification` | text | optionnel | Justification |
| `consolidated_risk_id` | relation | FK -> [Risk](../risk.md), optionnel | Risque consolidé dans le registre |
| `criteria_snapshot` | json | calculé | Snapshot du barème |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |

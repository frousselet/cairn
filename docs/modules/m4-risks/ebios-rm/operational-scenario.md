# OperationalScenario

`risks.models.ebios.operational_scenario.OperationalScenario`

Scénario opérationnel : déclinaison technique d'un scénario stratégique décrivant les modes opératoires sur les biens supports. Préfixe de référence : `EOPS`.

## 4.4.1 Entité : OperationalScenario (Scénario opérationnel)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), requis | Appréciation parente |
| `strategic_scenario_id` | relation | FK -> [StrategicScenario](strategic-scenario.md), requis | Scénario stratégique parent |
| `reference` | string | requis, unique, préfixe EOPS | Code (ex. EOPS-1) |
| `name` | string | requis, max 255 | Intitulé |
| `description` | text | requis | Description technique |
| `targeted_support_assets` | M2M -> SupportAsset | requis | Biens supports ciblés |
| `gravity_level` | integer | requis | Gravité (héritée du parent par défaut) |
| `gravity_inherited` | boolean | requis, défaut true | Indique si la gravité est héritée |
| `gravity_override_justification` | text | optionnel | Justification si gravité ajustée |
| `likelihood_v` | enum | requis | `V1`, `V2`, `V3`, `V4` (grille B, [voir README §2.8](README.md#28-grilles-de-scoring-anssi)) |
| `likelihood_justification` | text | optionnel | Justification |
| `risk_level` | integer | calculé | Niveau de risque (matrice gravity x likelihood mappée) |
| `existing_controls` | text | optionnel | Mesures techniques existantes |
| `existing_measures` | M2M -> Requirement | optionnel | Mesures formalisées (réutilise Module 3) |
| `consolidated_risk_id` | relation | FK -> [Risk](../risk.md), optionnel | Risque consolidé dans le registre |
| `mitre_version` | string | optionnel | Version MITRE ATT&CK référencée (ex. v15.1) |
| `criteria_snapshot` | json | calculé | Snapshot |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |

> Mapping `likelihood_v` -> valeur entière utilisée par la matrice : V1=1, V2=2, V3=3, V4=4.

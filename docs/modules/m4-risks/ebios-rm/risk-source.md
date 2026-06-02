# RiskSource

`risks.models.ebios.risk_source.RiskSource`

Source de risque (SR) : élément (personne, groupe, organisation, État, phénomène) à l'origine du risque. Préfixe de référence : `ERSC`.

## 4.2.1 Entité : RiskSource (Source de risque)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), requis | Appréciation parente |
| `reference` | string | requis, unique, préfixe ERSC | Code (ex. ERSC-1) |
| `name` | string | requis, max 255 | Nom de la SR |
| `description` | text | optionnel | Description |
| `category` | enum | requis | `state`, `organized_crime`, `terrorist`, `activist`, `competitor`, `employee`, `service_provider`, `amateur`, `natural`, `other` |
| `motivation_level` | integer | requis, 1 à 4 | Niveau de motivation (1 faible, 4 très forte) |
| `motivation_description` | text | optionnel | Description qualitative |
| `resources_level` | integer | requis, 1 à 4 | Niveau de ressources (1 limitées, 4 illimitées) |
| `activity_level` | integer | requis, 1 à 4 | Niveau d'activité observée |
| `threat_level` | integer | calculé, 1 à 4 (V1-V4) | Niveau de menace ANSSI (grille A, [voir README §2.8](README.md#28-grilles-de-scoring-anssi)) |
| `is_retained` | boolean | requis, défaut true | SR retenue pour l'analyse |
| `retention_justification` | text | optionnel | Justification |
| `is_from_catalog` | boolean | requis, défaut false | Issue du catalogue ANSSI prédéfini |
| `criteria_snapshot` | json | calculé | Snapshot de la grille de calcul |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |

> `threat_level` est calculé dans `save()` selon la grille A ([voir README §2.8](README.md#28-grilles-de-scoring-anssi)). Le résultat est stocké pour usage en filtrage/index. La grille est paramétrable via un champ JSON sur [`RiskCriteria`](../risk-criteria.md) (clé `ebios_threat_grid`).

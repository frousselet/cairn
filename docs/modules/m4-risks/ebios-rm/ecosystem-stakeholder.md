# EcosystemStakeholder

`risks.models.ebios.ecosystem_stakeholder.EcosystemStakeholder`

Partie prenante de l'écosystème pouvant constituer un vecteur d'attaque. Modèle indépendant du `context.Stakeholder` (parties intéressées ISO 9001/27001). Préfixe de référence : `EECS`.

## 4.3.1 Entité : EcosystemStakeholder (Partie prenante de l'écosystème)

Modèle indépendant du `context.Stakeholder` (parties intéressées ISO 9001/27001). Lien optionnel via FK.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto | Identifiant unique |
| `assessment_id` | relation | FK -> [RiskAssessment](../risk-assessment.md), requis | Appréciation parente |
| `reference` | string | requis, unique, préfixe EECS | Code (ex. EECS-1) |
| `stakeholder_id` | relation | FK -> Stakeholder, optionnel | Lien Module 1 (si déjà recensé) |
| `supplier_id` | relation | FK -> Supplier, optionnel | Lien Module 2 (si fournisseur) |
| `name` | string | requis, max 255 | Nom |
| `description` | text | optionnel | Description du rôle dans l'écosystème |
| `category` | enum | requis | `supplier`, `partner`, `subcontractor`, `customer`, `regulator`, `shared_infrastructure`, `client_employee`, `other` |
| `dependency` | integer | requis, 1 à 4 | Dépendance de l'organisme vis-à-vis de la PP |
| `penetration` | integer | requis, 1 à 4 | Pénétration de la PP dans l'écosystème |
| `maturity` | integer | requis, 1 à 4 | Maturité cyber de la PP |
| `trust` | integer | requis, 1 à 4 | Confiance accordée à la PP |
| `threat_level` | decimal(4,2) | calculé | `(dependency * penetration) / (maturity * trust)` |
| `threat_zone` | enum | calculé | `control`, `monitoring`, `danger` (seuils [voir README §2.6](README.md#26-cartographie-de-la-menace-numérique-de-lécosystème)) |
| `accessible_support_assets` | M2M -> SupportAsset | optionnel | Biens supports accessibles |
| `is_attack_vector` | boolean | requis, défaut false | Identifié comme vecteur d'attaque |
| `attack_vector_justification` | text | optionnel | Justification |
| `criteria_snapshot` | json | calculé | Snapshot des seuils de zonage |
| `created_by`, `created_at`, `updated_at` | - | auto | Standards |

> `threat_level` et `threat_zone` sont calculés dans `save()` selon la formule [README §2.6](README.md#26-cartographie-de-la-menace-numérique-de-lécosystème). Les seuils sont paramétrables sur [`RiskCriteria`](../risk-criteria.md) (clé JSON `ebios_ecosystem_thresholds`).

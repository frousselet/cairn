# EssentialAsset

`assets.models.essential_asset.EssentialAsset`

Processus métier ou type d'information essentiel pour l'organisme dont la compromission aurait un impact significatif.

Représente un processus métier ou un type d'information essentiel pour l'organisme dont la compromission aurait un impact significatif.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. BE-001) |
| `name` | string | requis, max 255 | Nom du bien essentiel |
| `description` | text | optionnel | Description détaillée |
| `type` | enum | requis | `business_process`, `information` |
| `category` | enum | requis | Voir liste ci-dessous |
| `owner_id` | relation | FK → User, requis | Propriétaire du bien essentiel |
| `custodian_id` | relation | FK → User, optionnel | Dépositaire / responsable opérationnel |
| `confidentiality_level` | enum | requis | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4) |
| `integrity_level` | enum | requis | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4) |
| `availability_level` | enum | requis | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4) |
| `confidentiality_justification` | text | optionnel | Justification du niveau de confidentialité |
| `integrity_justification` | text | optionnel | Justification du niveau d'intégrité |
| `availability_justification` | text | optionnel | Justification du niveau de disponibilité |
| `max_tolerable_downtime` | string | optionnel | Durée maximale d'indisponibilité tolérable (DMIT / MTD) |
| `recovery_time_objective` | string | optionnel | Objectif de temps de reprise (RTO) |
| `recovery_point_objective` | string | optionnel | Objectif de point de reprise (RPO) |
| `data_classification` | enum | optionnel | `public`, `internal`, `confidential`, `restricted`, `secret` |
| `personal_data` | boolean | requis, défaut false | Contient des données à caractère personnel |
| `personal_data_categories` | json | optionnel | Catégories de données personnelles (RGPD) |
| `regulatory_constraints` | text | optionnel | Contraintes réglementaires spécifiques |
| `related_activities` | relation | M2M → Activity | Activités métier associées (Module 1) |
| `supporting_assets` | relation | M2M → SupportAsset (via AssetDependency) | Biens supports associés |
| `status` | enum | requis | `identified`, `active`, `under_review`, `decommissioned` |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories de biens essentiels (valeurs de `category`) :**

- *Type `business_process` :* `core_process`, `support_process`, `management_process`
- *Type `information` :* `strategic_data`, `operational_data`, `personal_data`, `financial_data`, `technical_data`, `legal_data`, `research_data`, `commercial_data`

> Note : Les catégories doivent être paramétrables par l'administrateur.

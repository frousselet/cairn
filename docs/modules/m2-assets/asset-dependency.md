# AssetDependency

`assets.models.dependency.AssetDependency`

Relation de dépendance entre un bien essentiel et un bien support, vecteur d'héritage des besoins de sécurité DIC.

Représente le lien de dépendance entre un bien essentiel et un bien support. C'est via cette relation que les besoins de sécurité DIC sont hérités par les biens supports.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `essential_asset_id` | relation | FK → EssentialAsset, requis | Bien essentiel source |
| `support_asset_id` | relation | FK → SupportAsset, requis | Bien support cible |
| `dependency_type` | enum | requis | `runs_on`, `stored_in`, `transmitted_by`, `managed_by`, `hosted_at`, `protected_by`, `other` |
| `criticality` | enum | requis | `low`, `medium`, `high`, `critical` |
| `description` | text | optionnel | Description de la relation de dépendance |
| `is_single_point_of_failure` | boolean | requis, défaut false | Point unique de défaillance |
| `redundancy_level` | enum | optionnel | `none`, `partial`, `full` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte d'unicité : le couple (`essential_asset_id`, `support_asset_id`) doit être unique.

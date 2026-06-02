# SupplierDependency

`assets.models.supplier.SupplierDependency`

Relation typée entre un bien support et un fournisseur. Permet d'inventorier la chaîne d'approvisionnement à la maille de l'actif (« le serveur de paie est hébergé par OVH ») et d'alimenter la détection automatique des points uniques de défaillance (SPOF) issus d'une dépendance fournisseur.

Ne pas confondre avec [`SiteSupplierDependency`](site.md#sitesupplierdependency-rattachement-site-supplier) qui rattache un fournisseur à un site (vue géographique) plutôt qu'à un actif.

## Champs

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | Identifiant unique |
| `reference` | string | auto-généré `SDEP-N`, unique | Référence métier |
| `support_asset` | FK -> SupportAsset | requis, cascade | Bien support concerné |
| `supplier` | FK -> Supplier | requis, cascade | Fournisseur intervenant sur cet actif |
| `dependency_type` | enum | requis | `provides`, `hosts`, `manages`, `develops`, `supports`, `licenses`, `maintains`, `other` |
| `criticality` | enum | requis | `low`, `medium`, `high`, `critical` |
| `description` | text | optionnel, HTML | |
| `is_single_point_of_failure` | boolean | **lecture seule, calculé** | Mis à jour par le service `assets.services.spof_detection` (M2 §3.3 RS-07). Toute valeur fournie en écriture est ignorée. |
| `redundancy_level` | enum | optionnel | `none`, `partial`, `full`. Saisi par l'opérateur. |
| `is_approved` / `approved_by` / `approved_at` | boolean / FK -> User / datetime | optionnel | Workflow d'approbation standard |
| `version` | int | auto | |
| `created_by` | FK -> User | optionnel | |
| `created_at` / `updated_at` | datetime | auto | |

## Contrainte d'unicité

Un couple (`support_asset`, `supplier`) ne peut apparaître qu'une fois. Pour deux relations distinctes entre les mêmes actif et fournisseur (par exemple « hosts » + « supports »), créer une seule ligne dont la `description` détaille les rôles, ou élargir la convention de saisie.

## Énumération `dependency_type`

| Valeur | Sens |
|---|---|
| `provides` | Le fournisseur livre l'actif (produit, équipement) |
| `hosts` | Le fournisseur héberge l'actif (cloud, colocation) |
| `manages` | Le fournisseur opère l'actif (managed service) |
| `develops` | Le fournisseur développe / personnalise l'actif (intégrateur) |
| `supports` | Le fournisseur fournit le support technique (TMA, SLA) |
| `licenses` | Le fournisseur concède la licence (éditeur logiciel) |
| `maintains` | Le fournisseur assure la maintenance physique |
| `other` | Autre type de dépendance, détaillé dans `description` |

## Règles de gestion

| ID | Règle |
|---|---|
| RG-SDEP-01 | `is_single_point_of_failure` est calculé par le service SPOF. La valeur fournie à l'API/MCP n'est pas persistée : le serveur la réécrase au prochain passage du service. |
| RG-SDEP-02 | `redundancy_level` est saisi par l'opérateur. Le service SPOF utilise cette valeur (combinée à la criticité et au nombre de fournisseurs alternatifs) pour décider si la dépendance est SPOF. |
| RG-SDEP-03 | `unique(support_asset, supplier)` est une contrainte d'intégrité. La création d'un doublon est rejetée par la base. |
| RG-SDEP-04 | La suppression du `SupportAsset` ou du `Supplier` cascade sur la dépendance. La suppression de la dépendance laisse l'actif et le fournisseur intacts. |

## Endpoints

### REST

- `GET /api/v1/assets/supplier-dependencies/` : liste avec filtres `support_asset_id`, `supplier_id`, `dependency_type`, `criticality`
- `POST /api/v1/assets/supplier-dependencies/`
- `GET /api/v1/assets/supplier-dependencies/<uuid>/`
- `PUT/PATCH /api/v1/assets/supplier-dependencies/<uuid>/`
- `DELETE /api/v1/assets/supplier-dependencies/<uuid>/`
- `POST /api/v1/assets/supplier-dependencies/<uuid>/approve/`

### MCP

`list_supplier_dependencys`, `get_supplier_dependency`, `create_supplier_dependency`, `update_supplier_dependency`, `delete_supplier_dependency`, `approve_supplier_dependency`, `batch_create_supplier_dependencys`.

## Permissions

| Codename | Description |
|---|---|
| `assets.supplier_dependency.read` | Lire les dépendances fournisseur |
| `assets.supplier_dependency.create` | Créer |
| `assets.supplier_dependency.update` | Modifier |
| `assets.supplier_dependency.delete` | Supprimer |
| `assets.supplier_dependency.approve` | Approuver |

## Références

- [Supplier](supplier.md), [SupportAsset](support-asset.md), [AssetDependency](asset-dependency.md), [Site](site.md)
- ISO/IEC 27001:2022 §A.5.22 (Surveillance, examen et gestion des changements des services fournisseurs)
- Service `assets.services.spof_detection` : moteur de calcul de `is_single_point_of_failure`

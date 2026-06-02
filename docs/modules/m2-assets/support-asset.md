# SupportAsset

`assets.models.support_asset.SupportAsset`

Actif technique, humain ou physique qui supporte les biens essentiels et sur lequel les vulnérabilités peuvent être exploitées.

Représente un actif technique, humain ou physique qui supporte les biens essentiels et sur lequel les vulnérabilités peuvent être exploitées.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. BS-001) |
| `name` | string | requis, max 255 | Nom du bien support |
| `description` | text | optionnel | Description détaillée |
| `type` | enum | requis | `hardware`, `software`, `network`, `person`, `site`, `service`, `paper` |
| `category` | enum | requis | Voir liste ci-dessous |
| `owner_id` | relation | FK → User, requis | Propriétaire du bien support |
| `custodian_id` | relation | FK → User, optionnel | Dépositaire / responsable opérationnel |
| `location` | string | optionnel | Localisation physique |
| `manufacturer` | string | optionnel | Fabricant / éditeur |
| `model` | string | optionnel | Modèle / version |
| `serial_number` | string | optionnel | Numéro de série |
| `version` | string | optionnel | Version (logiciel, firmware) |
| `ip_address` | string | optionnel | Adresse IP (si applicable) |
| `hostname` | string | optionnel | Nom d'hôte (si applicable) |
| `operating_system` | string | optionnel | Système d'exploitation |
| `acquisition_date` | date | optionnel | Date d'acquisition |
| `end_of_life_date` | date | optionnel | Date de fin de vie / fin de support |
| `warranty_expiry_date` | date | optionnel | Date d'expiration de la garantie |
| `supplier_id` | relation | FK → Supplier, optionnel | Fournisseur associé (Module Fournisseurs) |
| `contract_reference` | string | optionnel | Référence du contrat associé |
| `inherited_confidentiality` | enum | calculé | Niveau hérité max des biens essentiels |
| `inherited_integrity` | enum | calculé | Niveau hérité max des biens essentiels |
| `inherited_availability` | enum | calculé | Niveau hérité max des biens essentiels |
| `exposure_level` | enum | optionnel | `internal`, `exposed`, `internet_facing`, `dmz` |
| `environment` | enum | optionnel | `production`, `staging`, `development`, `test`, `disaster_recovery` |
| `essential_assets` | relation | M2M → EssentialAsset (via AssetDependency) | Biens essentiels supportés |
| `parent_asset_id` | relation | FK → SupportAsset, optionnel | Bien support parent (composition) |
| `related_measures` | relation | M2M → Measure | Mesures de sécurité appliquées (Module Mesures) |
| `status` | enum | requis | `in_stock`, `deployed`, `active`, `under_maintenance`, `decommissioned`, `disposed` |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories de biens supports (valeurs de `category`) :**

- *`hardware` :* `server`, `workstation`, `laptop`, `mobile_device`, `network_equipment`, `storage`, `peripheral`, `iot_device`, `removable_media`, `other_hardware`
- *`software` :* `operating_system`, `database`, `application`, `middleware`, `security_tool`, `development_tool`, `saas_application`, `other_software`
- *`network` :* `lan`, `wan`, `wifi`, `vpn`, `internet_link`, `firewall_zone`, `dmz`, `other_network`
- *`person` :* `internal_staff`, `contractor`, `external_provider`, `administrator`, `developer`, `other_person`
- *`site` :* `datacenter`, `office`, `remote_site`, `cloud_region`, `other_site`
- *`service` :* `cloud_service`, `hosting_service`, `managed_service`, `telecom_service`, `outsourced_service`, `other_service`
- *`paper` :* `archive`, `printed_document`, `form`, `other_paper`

> Note : Les catégories doivent être paramétrables par l'administrateur.

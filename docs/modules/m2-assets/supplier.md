# Supplier

`assets.models.supplier.Supplier`

Fournisseur tiers (éditeur logiciel, hébergeur, prestataire de service managé, mainteneur, intégrateur, etc.) intervenant sur les biens supports ou les sites du SMSI. Sert de point d'ancrage à l'analyse de la chaîne d'approvisionnement (ISO 27001:2022 §A.5.19 à §A.5.23), à l'inventaire contractuel et à la revue périodique de conformité des prestataires.

## Champs

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `reference` | string | auto-généré `SUPP-N`, unique | Référence métier |
| `scopes` | relation | M2M -> Scope | Périmètres SMSI concernés par ce fournisseur. Un fournisseur transverse peut rester sans périmètre (liste vide). |
| `name` | string | requis, max 255 | Nom commercial du fournisseur |
| `description` | text | optionnel, HTML | Description et contexte d'intervention |
| `logo` | text | optionnel | Logo data-URI (base64), 128 px |
| `logo_64` / `logo_32` / `logo_16` | text | optionnel, lecture seule | Variantes du logo générées automatiquement à la mise à jour |
| `type` | relation | FK -> SupplierType, optionnel | Type de fournisseur (paramétrable, voir sous-entité ci-dessous) |
| `criticality` | enum | requis, défaut `medium` | `low`, `medium`, `high`, `critical` |
| `contact_name` | string | optionnel, max 255 | Référent commercial / technique |
| `contact_email` | email | optionnel | |
| `contact_phone` | string | optionnel, max 50 | |
| `website` | url | optionnel | |
| `address` | text | optionnel | Adresse postale |
| `country` | string | optionnel, max 100 | Pays (pour analyses de juridiction / RGPD / souveraineté) |
| `contract_reference` | string | optionnel, max 255 | Référence interne du contrat |
| `contract_start_date` | date | optionnel | |
| `contract_end_date` | date | optionnel | Déclenche l'alerte « contrat expiré » via `is_contract_expired` (M2 §9) |
| `owner` | relation | FK -> User, requis | Propriétaire interne (responsable de la relation contractuelle) |
| `status` | enum | requis, défaut `active` | `active`, `under_evaluation`, `suspended`, `archived` |
| `notes` | text | optionnel, HTML | Notes libres |
| `tags` | relation | M2M -> Tag | |
| `is_approved` | boolean | défaut `false` | Validé par un approbateur |
| `approved_by` / `approved_at` | relation / datetime | optionnel | |
| `version` | int | auto-incrémenté | Bumpé à chaque modification majeure |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | |

## Énumérations

### `criticality`

`low`, `medium`, `high`, `critical`. Conditionne la fréquence de revue, l'inclusion dans les exports de chaîne d'approvisionnement critique et la priorité des plans d'action sur les non-conformités.

### `status`

- `active` : sous contrat, opérations en cours
- `under_evaluation` : en cours de qualification (audit fournisseur, RFP, étude de risque)
- `suspended` : intervention temporairement suspendue (incident, manquement, gel)
- `archived` : contrat terminé, conservation pour traçabilité historique

## Propriétés calculées

### `is_contract_expired`

`true` si `status=active` et `contract_end_date` est dans le passé. Sert d'indicateur visuel sur les vues liste et déclenche les notifications de renouvellement.

### `requirement_compliance_summary`

Dict agrégeant le nombre d'exigences fournisseur (`SupplierRequirement`) par statut (`compliant`, `non_compliant`, `partially_compliant`, `not_assessed`). Utilisé par les tableaux de bord et l'export contrat / SoA.

## Sous-entité : `SupplierType`

`assets.models.supplier.SupplierType`

Type de fournisseur paramétrable par l'administrateur (par exemple « SaaS », « Hébergeur cloud », « Prestataire RH », « Auditeur externe »). Permet d'attacher un socle d'exigences-types réutilisables (voir `SupplierTypeRequirement`) à tous les fournisseurs du même type.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | int | PK auto-incrémenté | Identifiant numérique (pas UUID, particularité historique) |
| `reference` | string | auto-généré `SPTY-N`, unique | |
| `name` | string | requis, max 255, unique | Nom du type |
| `description` | text | optionnel | |
| `created_at` / `updated_at` | datetime | auto | |

## Sous-entité : `SupplierTypeRequirement`

`assets.models.supplier.SupplierTypeRequirement`

Exigence-modèle attachée à un `SupplierType`. À la création d'un `Supplier` de ce type, ces exigences peuvent être instanciées en `SupplierRequirement` (voir [supplier-requirement.md](supplier-requirement.md)).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | int | PK auto-incrémenté | |
| `supplier_type` | FK -> SupplierType | requis, cascade | |
| `title` | string | requis, max 500 | Intitulé de l'exigence-type (ex. « Certification ISO 27001 valide ») |
| `description` | text | optionnel | |
| `created_at` / `updated_at` | datetime | auto | |

## Règles de gestion

| ID | Règle |
|---|---|
| RG-SUP-01 | `Supplier.owner` est requis : tout fournisseur doit avoir un propriétaire interne nommé responsable de la relation. |
| RG-SUP-02 | `Supplier.type` est optionnel mais recommandé : sans type, les exigences-types ne s'appliquent pas automatiquement. |
| RG-SUP-03 | `scopes` est optionnel. Un fournisseur transverse à toute l'organisation peut rester sans périmètre. Les fournisseurs cantonnés à une filiale ou à un périmètre SMSI précis doivent être rattachés (RG-01 cross-module). |
| RG-SUP-04 | La suppression d'un `Supplier` référencé par un `SupportAsset.supplier`, par une `SupplierDependency`, ou par un `SupplierRequirement` est interdite. Désactiver via `status = archived`. |
| RG-SUP-05 | `contract_end_date` passée et `status=active` déclenche la propriété calculée `is_contract_expired`. Le statut n'est pas modifié automatiquement : c'est à l'opérateur d'archiver ou de renouveler. |
| RG-SUP-06 | `requirement_compliance_summary` est recalculé à la lecture, pas stocké. Aucune migration ni action n'est nécessaire après modification d'un `SupplierRequirement`. |

## Endpoints

### REST

- `GET /api/v1/assets/suppliers/` : liste avec filtres `type`, `criticality`, `status`, `country`
- `POST /api/v1/assets/suppliers/`
- `GET /api/v1/assets/suppliers/<uuid>/`
- `PUT/PATCH /api/v1/assets/suppliers/<uuid>/`
- `DELETE /api/v1/assets/suppliers/<uuid>/`
- `POST /api/v1/assets/suppliers/<uuid>/approve/`
- `GET /api/v1/assets/supplier-types/` (CRUD complet)
- `GET /api/v1/assets/supplier-type-requirements/` (CRUD complet)

### MCP

- `list_suppliers` / `get_supplier` / `create_supplier` / `update_supplier` / `delete_supplier` / `approve_supplier` / `batch_create_suppliers`
- `update_supplier_logo` : met à jour le logo (data URI ou URL publique) et regénère les variantes 64/32/16
- `list_supplier_types` / `create_supplier_type` / `delete_supplier_type`
- `list_supplier_type_requirements` / `create_supplier_type_requirement` / `delete_supplier_type_requirement`

## Import CSV en masse

Les fournisseurs sont le premier consommateur du socle d'import générique (`core/imports`, voir [le module Compliance](../m3-compliance/framework.md) pour le modèle d'origine). Un bouton **Import** au-dessus de la liste des fournisseurs ouvre, dans une modale, le téléversement d'un fichier CSV. Le flux est en trois temps : téléversement -> aperçu (lignes à créer, correspondances existantes, lignes en erreur) -> confirmation.

**Gestion des doublons (par ligne, dans l'aperçu)** : une ligne dont le nom correspond exactement à un fournisseur existant est signalée et propose une case **Remplacer**. Cochée, le fournisseur existant est mis à jour avec les valeurs du CSV ; décochée, l'existant est conservé tel quel et la ligne est ignorée (pas de doublon). En cas de remplacement, la **date de création d'origine est préservée** (la colonne `created_at` du CSV est ignorée pour une mise à jour). Si un nom correspond à plusieurs fournisseurs existants, la ligne passe en erreur (ambiguïté à lever). Les nouvelles lignes créent un fournisseur avec une référence `SUPP-N` auto-générée.

- **Permission** : `assets.supplier.create` (le téléchargement de l'exemple ne requiert que `assets.supplier.read`).
- **URLs** : `/imports/supplier/` (formulaire), `/imports/supplier/preview/` (aperçu/confirmation), `/imports/supplier/sample/` (exemple CSV).
- **Encodage** : `.csv` UTF-8 (BOM toléré), taille max 10 Mo.

### Colonnes

| Colonne | Obligatoire | Résolution / valeurs |
|---|---|---|
| `name` | oui | Texte |
| `owner` | non | Utilisateur par e-mail ; vide -> utilisateur courant |
| `type` | non | `SupplierType` par nom (doit exister) |
| `criticality` | non | `low` / `medium` / `high` / `critical` (défaut `medium`) |
| `status` | non | `active` / `under_evaluation` / `suspended` / `archived` (défaut `active`) |
| `description` | non | Texte |
| `contact_name` | non | Texte |
| `contact_email` | non | E-mail valide |
| `contact_phone` | non | Texte |
| `website` | non | URL valide |
| `address` | non | Texte |
| `country` | non | Texte |
| `contract_reference` | non | Texte |
| `contract_start_date` | non | Date `AAAA-MM-JJ` |
| `contract_end_date` | non | Date `AAAA-MM-JJ` |
| `notes` | non | Texte |
| `scopes` | non | Références ou noms de périmètres séparés par `;` (doivent exister) |
| `tags` | non | Noms de tags séparés par `;` (créés s'ils n'existent pas) |
| `created_at` | non | Date / date-heure de création d'origine (reprise depuis l'ancien outil) ; appliquée après création pour contourner `auto_now_add`, défaut « maintenant » |

La création en masse est aussi disponible par programmation via l'outil MCP `batch_create_suppliers` et l'endpoint de lot `/api/v1/assets/suppliers/`.

## Permissions

| Codename | Description |
|---|---|
| `assets.supplier.read` | Lire les fournisseurs |
| `assets.supplier.create` | Créer un fournisseur |
| `assets.supplier.update` | Modifier un fournisseur |
| `assets.supplier.delete` | Supprimer un fournisseur |
| `assets.supplier.approve` | Approuver un fournisseur |

`SupplierType` et `SupplierTypeRequirement` partagent les mêmes codenames sous le préfixe `assets.config.*`.

## Références

- ISO/IEC 27001:2022 Annex A §5.19 à §5.23 (Sécurité de l'information dans les relations fournisseurs)
- ISO/IEC 27036 (Information security in supplier relationships)
- [SupportAsset](support-asset.md) : `supplier` FK rattache un actif technique à son fournisseur
- [SupplierRequirement](supplier-requirement.md) : exigences imposées au fournisseur et revues de conformité
- [SupplierDependency](supplier-dependency.md) : lien actif <-> fournisseur typé
- Site dependencies : [Site](site.md) et `SiteSupplierDependency` pour les fournisseurs intervenant sur un site donné

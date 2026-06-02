# SupplierRequirement

`assets.models.supplier.SupplierRequirement`

Exigence imposée à un fournisseur (par exemple « Certification ISO 27001 valide », « Plan de reprise testé annuellement », « Notification d'incident sous 24 h »). Peut être créée à la main, dérivée d'un `SupplierTypeRequirement` (modèle attaché au type) ou rattachée à une `compliance.Requirement` du SMSI. Sa conformité est évaluée et révisée périodiquement via des `SupplierRequirementReview`.

## Champs

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | int | PK auto-incrémenté | Identifiant numérique |
| `supplier` | FK -> Supplier | requis, cascade | Fournisseur concerné |
| `source_type_requirement` | FK -> SupplierTypeRequirement | optionnel | Origine si l'exigence dérive d'un modèle de type |
| `requirement` | FK -> compliance.Requirement | optionnel | Lien vers l'exigence SMSI à laquelle elle se rattache (un même contrôle ISO peut être imposé à plusieurs fournisseurs) |
| `title` | string | requis, max 500 | Intitulé personnalisé, surtout utile quand `requirement` n'est pas renseigné |
| `description` | text | optionnel | |
| `compliance_status` | enum | requis, défaut `not_assessed` | `not_assessed`, `compliant`, `partially_compliant`, `non_compliant` |
| `evidence` | text | optionnel | Description des preuves (références de documents, captures, etc.) |
| `due_date` | date | optionnel | Échéance contractuelle |
| `verified_at` | datetime | optionnel | Date de la dernière vérification, mise à jour à chaque `SupplierRequirementReview` |
| `verified_by` | FK -> User | optionnel | Auteur de la dernière vérification |
| `created_at` / `updated_at` | datetime | auto | |

## Sous-entité : `SupplierRequirementReview`

`assets.models.supplier.SupplierRequirementReview`

Trace de revue / justification associée à une `SupplierRequirement`. Plusieurs revues par exigence permettent de reconstituer l'historique de conformité et d'attacher des preuves datées (audit, certificat à jour, rapport d'incident).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | int | PK auto-incrémenté | |
| `supplier_requirement` | FK -> SupplierRequirement | requis, cascade | |
| `review_date` | date | requis | Date de la revue |
| `reviewer` | FK -> User | optionnel | |
| `result` | enum | requis, défaut `not_assessed` | Même énumération que `compliance_status` ci-dessus |
| `comment` | text | optionnel | Justification écrite |
| `evidence_file` | text | optionnel | Document data-URI uploadé |
| `evidence_filename` | string | optionnel, max 255 | Nom de fichier original |
| `created_at` / `updated_at` | datetime | auto | |

À l'enregistrement d'une revue avec un `result` final, l'exigence parente met à jour son `compliance_status`, `verified_at` et `verified_by` à partir de la revue la plus récente.

## Énumération `compliance_status`

- `not_assessed` : exigence créée mais jamais évaluée. Pas d'alerte.
- `compliant` : conforme. Date de prochaine revue calculée d'après la `due_date` ou la fréquence définie au niveau du type.
- `partially_compliant` : exigence partiellement satisfaite (certaines parties oui, d'autres non). Alerte légère.
- `non_compliant` : non conforme. Alerte critique, contribue au compteur du tableau de bord.

## Règles de gestion

| ID | Règle |
|---|---|
| RG-SREQ-01 | Une `SupplierRequirement` doit avoir un `title` non vide même si `requirement` est rattaché : le titre sert au listing rapide sans charger l'exigence SMSI. |
| RG-SREQ-02 | `source_type_requirement` est immutable une fois posée. Pour remplacer la source, dupliquer l'exigence. |
| RG-SREQ-03 | À l'enregistrement d'une `SupplierRequirementReview`, son `result` propage au `compliance_status` de l'exigence parente, et `verified_at` / `verified_by` reflètent la revue. |
| RG-SREQ-04 | Une `SupplierRequirement` au statut `non_compliant` ou avec `due_date` passée sans review apparaît dans la file d'alertes du fournisseur et compte dans `Supplier.requirement_compliance_summary`. |

## Endpoints

### REST

- `GET /api/v1/assets/supplier-requirements/`
- `POST /api/v1/assets/supplier-requirements/`
- `GET /api/v1/assets/supplier-requirements/<id>/`
- `PUT/PATCH /api/v1/assets/supplier-requirements/<id>/`
- `DELETE /api/v1/assets/supplier-requirements/<id>/`
- `GET /api/v1/assets/supplier-requirement-reviews/` (CRUD complet)

### MCP

- `list_supplier_requirements` / `get_supplier_requirement` / `create_supplier_requirement` / `update_supplier_requirement` / `delete_supplier_requirement` / `batch_create_supplier_requirements`
- `list_supplier_requirement_reviews` / `create_supplier_requirement_review` / `delete_supplier_requirement_review`

## Permissions

Les exigences-fournisseur et leurs revues utilisent le préfixe permission `assets.supplier.*` (héritage de l'entité parente Supplier).

## Références

- [Supplier](supplier.md) : entité parente
- [Requirement](../m3-compliance/requirement.md) : référentiel d'exigences SMSI rattachables

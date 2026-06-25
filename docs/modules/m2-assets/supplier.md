# Supplier

`assets.models.supplier.Supplier`

Third-party supplier (software vendor, host, managed service provider, maintainer, integrator, etc.) operating on the support assets or sites of the ISMS. Serves as the anchor point for supply chain analysis (ISO 27001:2022 §A.5.19 to §A.5.23), the contractual inventory and the periodic compliance review of providers.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `SUPP-N`, unique | Business reference |
| `scopes` | relation | M2M -> Scope | ISMS scopes concerned by this supplier. A cross-cutting supplier can remain without a scope (empty list). |
| `name` | string | required, max 255 | Trade name of the supplier |
| `description` | text | optional, HTML | Description and context of operation |
| `logo` | text | optional | Logo data-URI (base64), 128 px |
| `logo_64` / `logo_32` / `logo_16` | text | optional, read-only | Logo variants generated automatically on update |
| `type` | relation | FK -> SupplierType, optional | Supplier type (configurable, see sub-entity below) |
| `criticality` | enum | required, default `medium` | `low`, `medium`, `high`, `critical` |
| `contact_name` | string | optional, max 255 | Commercial / technical contact |
| `contact_email` | email | optional | |
| `contact_phone` | string | optional, max 50 | |
| `website` | url | optional | |
| `address` | text | optional | Postal address |
| `country` | string | optional, max 100 | Country (for jurisdiction / GDPR / sovereignty analyses) |
| `contract_reference` | string | optional, max 255 | Internal contract reference |
| `contract_start_date` | date | optional | |
| `contract_end_date` | date | optional | Triggers the "contract expired" alert via `is_contract_expired` (M2 §9) |
| `owner` | relation | FK -> User, required | Internal owner (responsible for the contractual relationship) |
| `status` | enum | required, default `active` | `active`, `under_evaluation`, `suspended`, `archived` |
| `notes` | text | optional, HTML | Free-text notes |
| `tags` | relation | M2M -> Tag | |
| `is_approved` | boolean | default `false` | Validated by an approver |
| `approved_by` / `approved_at` | relation / datetime | optional | |
| `version` | int | auto-incremented | Bumped on each major change |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | |

## Enumerations

### `criticality`

`low`, `medium`, `high`, `critical`. Drives the review frequency, the inclusion in critical supply chain exports and the priority of action plans on non-conformities.

### `status`

- `active`: under contract, operations ongoing
- `under_evaluation`: being qualified (supplier audit, RFP, risk study)
- `suspended`: operation temporarily suspended (incident, breach, freeze)
- `archived`: contract terminated, retained for historical traceability

## Computed properties

### `is_contract_expired`

`true` if `status=active` and `contract_end_date` is in the past. Serves as a visual indicator on the list views and triggers renewal notifications.

### `requirement_compliance_summary`

Dict aggregating the number of supplier requirements (`SupplierRequirement`) by status (`compliant`, `non_compliant`, `partially_compliant`, `not_assessed`). Used by the dashboards and the contract / SoA export.

## Sub-entity: `SupplierType`

`assets.models.supplier.SupplierType`

Supplier type configurable by the administrator (for example "SaaS", "Cloud host", "HR provider", "External auditor"). Makes it possible to attach a reusable set of requirement templates (see `SupplierTypeRequirement`) to all suppliers of the same type.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | int | PK auto-incremented | Numeric identifier (not UUID, historical particularity) |
| `reference` | string | auto-generated `SPTY-N`, unique | |
| `name` | string | required, max 255, unique | Name of the type |
| `description` | text | optional | |
| `created_at` / `updated_at` | datetime | auto | |

## Sub-entity: `SupplierTypeRequirement`

`assets.models.supplier.SupplierTypeRequirement`

Requirement template attached to a `SupplierType`. When a `Supplier` of this type is created, these requirements can be instantiated as `SupplierRequirement` (see [supplier-requirement.md](supplier-requirement.md)).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | int | PK auto-incremented | |
| `supplier_type` | FK -> SupplierType | required, cascade | |
| `title` | string | required, max 500 | Title of the requirement template (e.g. "Valid ISO 27001 certification") |
| `description` | text | optional | |
| `created_at` / `updated_at` | datetime | auto | |

## Business rules

| ID | Rule |
|---|---|
| RG-SUP-01 | `Supplier.owner` is required: every supplier must have a named internal owner responsible for the relationship. |
| RG-SUP-02 | `Supplier.type` is optional but recommended: without a type, requirement templates do not apply automatically. |
| RG-SUP-03 | `scopes` is optional. A supplier that is cross-cutting across the whole organization can remain without a scope. Suppliers confined to a subsidiary or to a specific ISMS scope must be attached (RG-01 cross-module). |
| RG-SUP-04 | Deleting a `Supplier` referenced by a `SupportAsset.supplier`, by a `SupplierDependency`, or by a `SupplierRequirement` is forbidden. Disable via `status = archived`. |
| RG-SUP-05 | A past `contract_end_date` and `status=active` triggers the computed property `is_contract_expired`. The status is not changed automatically: it is up to the operator to archive or renew. |
| RG-SUP-06 | `requirement_compliance_summary` is recomputed on read, not stored. No migration or action is necessary after modifying a `SupplierRequirement`. |

## Endpoints

### REST

- `GET /api/v1/assets/suppliers/`: list with filters `type`, `criticality`, `status`, `country`
- `POST /api/v1/assets/suppliers/`
- `GET /api/v1/assets/suppliers/<uuid>/`
- `PUT/PATCH /api/v1/assets/suppliers/<uuid>/`
- `DELETE /api/v1/assets/suppliers/<uuid>/`
- `POST /api/v1/assets/suppliers/<uuid>/approve/`
- `GET /api/v1/assets/supplier-types/` (full CRUD)
- `GET /api/v1/assets/supplier-type-requirements/` (full CRUD)

### MCP

- `list_suppliers` / `get_supplier` / `create_supplier` / `update_supplier` / `delete_supplier` / `approve_supplier` / `batch_create_suppliers`
- `update_supplier_logo`: updates the logo (data URI or public URL) and regenerates the 64/32/16 variants
- `list_supplier_types` / `create_supplier_type` / `delete_supplier_type`
- `list_supplier_type_requirements` / `create_supplier_type_requirement` / `delete_supplier_type_requirement`

## Bulk CSV import

Suppliers are the first consumer of the generic import foundation (`core/imports`, see [the Compliance module](../m3-compliance/framework.md) for the original model). An **Import** button above the supplier list opens, in a modal, the upload of a CSV file. The flow has three steps: upload -> preview (rows to create, existing matches, rows in error) -> confirmation.

**Duplicate handling (per row, in the preview)**: a row whose name matches exactly an existing supplier is flagged and offers a **Replace** checkbox. When checked, the existing supplier is updated with the CSV values; when unchecked, the existing one is kept as is and the row is ignored (no duplicate). In the case of a replacement, the **original creation date is preserved** (the `created_at` column of the CSV is ignored for an update). If a name matches several existing suppliers, the row goes into error (ambiguity to be resolved). New rows create a supplier with an auto-generated `SUPP-N` reference.

- **Permission**: `assets.supplier.create` (downloading the sample only requires `assets.supplier.read`).
- **URLs**: `/imports/supplier/` (form), `/imports/supplier/preview/` (preview/confirmation), `/imports/supplier/sample/` (CSV sample).
- **Encoding**: `.csv` UTF-8 (BOM tolerated), max size 10 MB.

### Columns

| Column | Required | Resolution / values |
|---|---|---|
| `name` | yes | Text |
| `owner` | no | User by email; empty -> current user |
| `type` | no | `SupplierType` by name (must exist) |
| `criticality` | no | `low` / `medium` / `high` / `critical` (default `medium`) |
| `status` | no | `active` / `under_evaluation` / `suspended` / `archived` (default `active`) |
| `description` | no | Text |
| `contact_name` | no | Text |
| `contact_email` | no | Valid email |
| `contact_phone` | no | Text |
| `website` | no | Valid URL |
| `address` | no | Text |
| `country` | no | Text |
| `contract_reference` | no | Text |
| `contract_start_date` | no | Date `YYYY-MM-DD` |
| `contract_end_date` | no | Date `YYYY-MM-DD` |
| `notes` | no | Text |
| `scopes` | no | Scope references or names separated by `;` (must exist) |
| `tags` | no | Tag names separated by `;` (created if they do not exist) |
| `created_at` | no | Original creation date / datetime (carried over from the legacy tool); applied after creation to bypass `auto_now_add`, default "now" |

Bulk creation is also available programmatically via the MCP tool `batch_create_suppliers` and the batch endpoint `/api/v1/assets/suppliers/`.

## Permissions

| Codename | Description |
|---|---|
| `assets.supplier.read` | Read suppliers |
| `assets.supplier.create` | Create a supplier |
| `assets.supplier.update` | Modify a supplier |
| `assets.supplier.delete` | Delete a supplier |
| `assets.supplier.approve` | Approve a supplier |

`SupplierType` and `SupplierTypeRequirement` share the same codenames under the `assets.config.*` prefix.

## References

- ISO/IEC 27001:2022 Annex A §5.19 to §5.23 (Information security in supplier relationships)
- ISO/IEC 27036 (Information security in supplier relationships)
- [SupportAsset](support-asset.md): the `supplier` FK attaches a technical asset to its supplier
- [SupplierRequirement](supplier-requirement.md): requirements imposed on the supplier and compliance reviews
- [SupplierDependency](supplier-dependency.md): typed asset <-> supplier link
- Site dependencies: [Site](site.md) and `SiteSupplierDependency` for suppliers operating on a given site

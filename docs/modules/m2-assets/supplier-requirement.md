# SupplierRequirement

`assets.models.supplier.SupplierRequirement`

Requirement imposed on a supplier (for example "Valid ISO 27001 certification", "Recovery plan tested annually", "Incident notification within 24 h"). Can be created manually, derived from a `SupplierTypeRequirement` (template attached to the type) or linked to a `compliance.Requirement` of the ISMS. Its compliance is assessed and reviewed periodically via `SupplierRequirementReview` records.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | int | PK auto-incremented | Numeric identifier |
| `supplier` | FK -> Supplier | required, cascade | Supplier concerned |
| `source_type_requirement` | FK -> SupplierTypeRequirement | optional | Origin if the requirement derives from a type template |
| `requirement` | FK -> compliance.Requirement | optional | Link to the ISMS requirement it relates to (the same ISO control can be imposed on several suppliers) |
| `title` | string | required, max 500 | Custom title, especially useful when `requirement` is not set |
| `description` | text | optional | |
| `compliance_status` | enum | required, default `not_assessed` | `not_assessed`, `compliant`, `partially_compliant`, `non_compliant` |
| `evidence` | text | optional | Description of the evidence (document references, screenshots, etc.) |
| `due_date` | date | optional | Contractual deadline |
| `verified_at` | datetime | optional | Date of the last verification, updated on each `SupplierRequirementReview` |
| `verified_by` | FK -> User | optional | Author of the last verification |
| `created_at` / `updated_at` | datetime | auto | |

## Sub-entity: `SupplierRequirementReview`

`assets.models.supplier.SupplierRequirementReview`

Review / justification record associated with a `SupplierRequirement`. Several reviews per requirement make it possible to reconstruct the compliance history and to attach dated evidence (audit, up-to-date certificate, incident report).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | int | PK auto-incremented | |
| `supplier_requirement` | FK -> SupplierRequirement | required, cascade | |
| `review_date` | date | required | Date of the review |
| `reviewer` | FK -> User | optional | |
| `result` | enum | required, default `not_assessed` | Same enumeration as `compliance_status` above |
| `comment` | text | optional | Written justification |
| `evidence_file` | text | optional | Uploaded data-URI document |
| `evidence_filename` | string | optional, max 255 | Original file name |
| `created_at` / `updated_at` | datetime | auto | |

When a review with a final `result` is saved, the parent requirement updates its `compliance_status`, `verified_at` and `verified_by` from the most recent review.

## `compliance_status` enumeration

- `not_assessed`: requirement created but never assessed. No alert.
- `compliant`: compliant. Next review date computed from the `due_date` or the frequency defined at the type level.
- `partially_compliant`: requirement partially satisfied (some parts yes, others no). Mild alert.
- `non_compliant`: non-compliant. Critical alert, contributes to the dashboard counter.

## Business rules

| ID | Rule |
|---|---|
| RG-SREQ-01 | A `SupplierRequirement` must have a non-empty `title` even if `requirement` is linked: the title serves the quick listing without loading the ISMS requirement. |
| RG-SREQ-02 | `source_type_requirement` is immutable once set. To replace the source, duplicate the requirement. |
| RG-SREQ-03 | When a `SupplierRequirementReview` is saved, its `result` propagates to the `compliance_status` of the parent requirement, and `verified_at` / `verified_by` reflect the review. |
| RG-SREQ-04 | A `SupplierRequirement` with a `non_compliant` status or with a past `due_date` and no review appears in the supplier's alert queue and counts in `Supplier.requirement_compliance_summary`. |

## Endpoints

### REST

- `GET /api/v1/assets/supplier-requirements/`
- `POST /api/v1/assets/supplier-requirements/`
- `GET /api/v1/assets/supplier-requirements/<id>/`
- `PUT/PATCH /api/v1/assets/supplier-requirements/<id>/`
- `DELETE /api/v1/assets/supplier-requirements/<id>/`
- `GET /api/v1/assets/supplier-requirement-reviews/` (full CRUD)

### MCP

- `list_supplier_requirements` / `get_supplier_requirement` / `create_supplier_requirement` / `update_supplier_requirement` / `delete_supplier_requirement` / `batch_create_supplier_requirements`
- `list_supplier_requirement_reviews` / `create_supplier_requirement_review` / `delete_supplier_requirement_review`

## Permissions

Supplier requirements and their reviews use the `assets.supplier.*` permission prefix (inherited from the parent Supplier entity).

## References

- [Supplier](supplier.md): parent entity
- [Requirement](../m3-compliance/requirement.md): repository of linkable ISMS requirements

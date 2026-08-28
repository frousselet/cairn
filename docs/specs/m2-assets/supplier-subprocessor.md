# SupplierSubprocessor

`assets.models.supplier.SupplierSubprocessor`

Directed link recording that a supplier (the *délégataire*) further delegates part of the service it provides to another supplier acting as a **sub-processor** (*sous-délégataire* / sous-traitant ultérieur). Both ends are real [`Supplier`](supplier.md) records, so every sub-processor keeps its own requirements, reviews and criticality, and the chain feeds nth-party / supply-chain risk analysis (ISO 27036, GDPR Art. 28 sub-processing register).

Corporate structure (subsidiaries / *filiales*) is modelled separately, directly on the `Supplier` via the `parent_company` self-FK (reverse accessor `subsidiaries`) : see [supplier.md](supplier.md).

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `SSPR-N`, unique | Business reference |
| `supplier` | relation | FK -> Supplier, required, cascade | The délégataire that engages the sub-processor. Reverse accessor `subprocessors`. |
| `subprocessor` | relation | FK -> Supplier, required, protect | The supplier engaged as a sub-processor. Reverse accessor `engaged_by`. |
| `purpose` | string | optional, max 500 | Nature of the service delegated |
| `criticality` | enum | required, default `medium` | `low`, `medium`, `high`, `critical` |
| `status` | enum | required, default `active` | `active`, `suspended`, `terminated` |
| `start_date` | date | optional | Date the engagement started |
| `end_date` | date | optional | Date the engagement ends |
| `description` | text | optional, HTML | Additional context |
| `version` | int | default 1 | |
| `created_by` | relation | FK -> User, optional | |
| `created_at` / `updated_at` | datetime | auto | |

## Business rules

| ID | Rule |
|---|---|
| RG-SSP-01 | `supplier` and `subprocessor` must differ : a supplier cannot be its own sub-processor (DB `CheckConstraint` + form/serializer validation). |
| RG-SSP-02 | The pair (`supplier`, `subprocessor`) is unique : a given délégataire lists each sub-processor at most once. |
| RG-SSP-03 | Deleting the délégataire (`supplier`) cascades its sub-processing links. The `subprocessor` side is `PROTECT` : a supplier engaged as a sub-processor cannot be deleted while the link exists (archive it instead). |
| RG-SSP-04 | `end_date` cannot be earlier than `start_date` (form validation). |

## Endpoints

### REST

- `GET /api/v1/assets/supplier-subprocessors/` : list with filters `supplier`, `subprocessor`, `criticality`, `status`
- `POST /api/v1/assets/supplier-subprocessors/` (+ batch)
- `GET/PUT/PATCH/DELETE /api/v1/assets/supplier-subprocessors/<uuid>/`
- `GET/POST /api/v1/assets/suppliers/<uuid>/subprocessors/` : the sub-processors of a supplier (nested)
- `GET /api/v1/assets/suppliers/<uuid>/subsidiaries/` : the subsidiaries (filiales) of a supplier (nested)

### MCP

- `list_supplier_subprocessors` / `get_supplier_subprocessor` / `create_supplier_subprocessor` / `update_supplier_subprocessor` / `delete_supplier_subprocessor` / `batch_create_supplier_subprocessors` / `get_supplier_subprocessor_history`
- `parent_company_id` on `create_supplier` / `update_supplier` sets the corporate subsidiary relation.

## Permissions

Managed under the parent supplier's codenames (`assets.supplier.read` / `.update`) : editing a supplier's sub-processing chain is part of maintaining the supplier.

## UI

Rendered on the supplier detail page in two cards :

- **Corporate structure** : the `parent_company` (shown as "Subsidiary of ...") and the list of `subsidiaries` chips (only shown when either is set).
- **Sub-processors** : a table of the délégataire's sub-processors (add / edit / remove through the HTMX drawer), followed by a read-only "Engaged as a sub-processor by" chip list built from the `engaged_by` reverse relation.

## References

- ISO/IEC 27036 (Information security in supplier relationships)
- GDPR Article 28 (processor and sub-processor obligations)
- [Supplier](supplier.md) : both ends of the link, and the `parent_company` / `subsidiaries` corporate relation

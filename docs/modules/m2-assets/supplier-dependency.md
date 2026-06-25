# SupplierDependency

`assets.models.supplier.SupplierDependency`

Typed relationship between a support asset and a supplier. It is used to inventory the supply chain at the asset level ("the payroll server is hosted by OVH") and to feed the automatic detection of single points of failure (SPOF) arising from a supplier dependency.

Not to be confused with [`SiteSupplierDependency`](site.md#sitesupplierdependency-rattachement-site-supplier), which attaches a supplier to a site (geographic view) rather than to an asset.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Unique identifier |
| `reference` | string | auto-generated `SDEP-N`, unique | Business reference |
| `support_asset` | FK -> SupportAsset | required, cascade | Support asset concerned |
| `supplier` | FK -> Supplier | required, cascade | Supplier operating on this asset |
| `dependency_type` | enum | required | `provides`, `hosts`, `manages`, `develops`, `supports`, `licenses`, `maintains`, `other` |
| `criticality` | enum | required | `low`, `medium`, `high`, `critical` |
| `description` | text | optional, HTML | |
| `is_single_point_of_failure` | boolean | **read-only, calculated** | Updated by the `assets.services.spof_detection` service (M2 §3.3 RS-07). Any value provided on write is ignored. |
| `redundancy_level` | enum | optional | `none`, `partial`, `full`. Entered by the operator. |
| `is_approved` / `approved_by` / `approved_at` | boolean / FK -> User / datetime | optional | Standard approval workflow |
| `version` | int | auto | |
| `created_by` | FK -> User | optional | |
| `created_at` / `updated_at` | datetime | auto | |

## Uniqueness constraint

A pair (`support_asset`, `supplier`) may appear only once. For two distinct relationships between the same asset and supplier (for example "hosts" + "supports"), create a single row whose `description` details the roles, or extend the entry convention.

## `dependency_type` enumeration

| Value | Meaning |
|---|---|
| `provides` | The supplier delivers the asset (product, equipment) |
| `hosts` | The supplier hosts the asset (cloud, colocation) |
| `manages` | The supplier operates the asset (managed service) |
| `develops` | The supplier develops / customizes the asset (integrator) |
| `supports` | The supplier provides technical support (application maintenance, SLA) |
| `licenses` | The supplier grants the license (software vendor) |
| `maintains` | The supplier provides physical maintenance |
| `other` | Other type of dependency, detailed in `description` |

## Business rules

| ID | Rule |
|---|---|
| RG-SDEP-01 | `is_single_point_of_failure` is calculated by the SPOF service. The value provided to the API/MCP is not persisted: the server overwrites it on the next run of the service. |
| RG-SDEP-02 | `redundancy_level` is entered by the operator. The SPOF service uses this value (combined with the criticality and the number of alternative suppliers) to decide whether the dependency is a SPOF. |
| RG-SDEP-03 | `unique(support_asset, supplier)` is an integrity constraint. The creation of a duplicate is rejected by the database. |
| RG-SDEP-04 | Deleting the `SupportAsset` or the `Supplier` cascades to the dependency. Deleting the dependency leaves the asset and the supplier intact. |

## Endpoints

### REST

- `GET /api/v1/assets/supplier-dependencies/`: list with filters `support_asset_id`, `supplier_id`, `dependency_type`, `criticality`
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
| `assets.supplier_dependency.read` | Read supplier dependencies |
| `assets.supplier_dependency.create` | Create |
| `assets.supplier_dependency.update` | Update |
| `assets.supplier_dependency.delete` | Delete |
| `assets.supplier_dependency.approve` | Approve |

## References

- [Supplier](supplier.md), [SupportAsset](support-asset.md), [AssetDependency](asset-dependency.md), [Site](site.md)
- ISO/IEC 27001:2022 §A.5.22 (Monitoring, review and change management of supplier services)
- `assets.services.spof_detection` service: calculation engine for `is_single_point_of_failure`

# Site

`context.models.site.Site`

Physical location covered by the ISMS (head office, datacenter, office, factory, warehouse, remote site). Serves as a geographic container for support assets and suppliers, and enables the "assets / suppliers per site" mapping.

## Why a dedicated model rather than a `SupportAsset` of type site

Sites were initially modelable both as standalone entities and through the `site` type of `SupportAsset` (with its subcategories `datacenter` / `office` / `remote_site` / `cloud_region` / `other_site`). This dual modeling was removed (issue #30, migrations `context.0028` + `assets.0029`). Decision: a site is not a support asset, it is a container of support assets. The distinction is now:

| Model | Used to... |
|---|---|
| `Site` | describe a physical location (address, hierarchy, attached scopes) |
| `SupportAsset` | describe a technical or human asset (with owner, CIA levels, lifecycle, etc.) |
| `SiteAssetDependency` | attach a support asset to its hosting site |
| `SiteSupplierDependency` | attach a supplier to a site it serves |

The `site` type of `SupportAsset` no longer exists. Existing rows were automatically converted to `Site` at migration time; the support assets that hosted those sites must be re-attached via `SiteAssetDependency`.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `SITE-N`, unique | Business reference |
| `scopes` | relation | M2M -> Scope | Attached ISMS scopes (RG-01). A site can cover several scopes (case of multiple subsidiaries sharing the same datacenter). |
| `name` | string | required, max 255 | Name of the site (e.g. "Lyon Part-Dieu head office", "Bron datacenter") |
| `type` | enum | required, default `other` | `headquarters`, `office`, `factory`, `warehouse`, `datacenter`, `remote`, `other` |
| `address` | text | optional | Postal address, map, access directions |
| `description` | text | optional | Free-text description |
| `parent_site` | relation | FK -> Site, optional | Site hierarchy (group -> subsidiary -> site). Cycles rejected by `clean()`. |
| `workflow_state` | enum | required, default `draft` | Standardised site lifecycle (`core.lifecycle`): `draft`, `commissioning`, `operational`, `review`, `decommissioned`, `archived`. See the [Lifecycle](#lifecycle) section and [governance/workflow.md](../governance/workflow.md). |
| `tags` | relation | M2M -> Tag | Free-text labels |
| `is_approved` | boolean | default `false` | Site validated by an approver |
| `approved_by` | relation | FK -> User, optional | Approver |
| `approved_at` | datetime | optional | Approval date |
| `version` | int | auto-incremented | Bumped on each major change |
| `created_by` | relation | FK -> User | Creator |
| `created_at` | datetime | auto | Creation date |
| `updated_at` | datetime | auto | Last modification date |

## `type` enumeration

- `headquarters`: head office
- `office`: office / administrative premises
- `factory`: factory / production site
- `warehouse`: warehouse / logistics center
- `datacenter`: datacenter (owned or colocation). Now also includes the former `cloud_region` values of support assets, which are folded into this category by the `assets.0029` migration for lack of a dedicated entry.
- `remote`: remote site, organized teleworking, secondary site
- `other`: other case

The displayed labels are localized via the i18n layer (`.po`). The former French values (`siege`, `bureau`, `usine`, `entrepot`, `site_distant`, `autre`) were renamed to English by the `context.0027` migration (issue #31).

## Hierarchy

`parent_site` makes it possible to model a tree: Group -> Subsidiary -> Site -> Building. The `clean()` rule detects and rejects cycles. There is no depth constraint nor consistency constraint between the scopes of a parent and its children: a child site can belong to a scope that its parent does not have (case of multiple subsidiaries sharing a site).

## Lifecycle

The site runs the standardised lifecycle engine (`core.lifecycle`, defined in `context/lifecycles.py` as the `site` lifecycle, `layout="graph"`), rendered with the directed-graph stepper on the detail page. It models the operational life of a physical location:

| Step | Code | Authoritative? | Meaning |
|---|---|---|---|
| Draft | `draft` | no (deletable) | Initial stub, just created. |
| Commissioning | `commissioning` | no | Being brought online (built, fitted out, connected). |
| Operational | `operational` | yes (counts in reports, linkable) | In service. |
| Under review | `review` | yes (counts in reports, linkable) | Periodic re-examination of an in-service site; loops back to Operational. |
| Decommissioned | `decommissioned` | no | Taken out of service for good; kept for traceability. |
| Archived | `archived` | no | From-any exit; can be restored to Draft. |

Transitions: `draft -> commissioning -> operational`; `operational <-> review` (periodic loop); `operational -> decommissioned`; `any -> archived`; `archived -> draft` (restore). Only the `operational` and `review` steps count in reports and are linkable, mirroring the governance the legacy default workflow expressed (only the validated-equivalent state counted / linked). The web detail page (transitions via the generic stepper), the REST `.../transition/` action and the MCP `transition_site` / `site_allowed_transitions` tools all route through the lifecycle service, which records a `LifecycleEvent` for every move.

The detail page itself uses the standardised 2-column layout (hero overview with an address map, sub-sites, hosted-asset and supplier dependencies, an audit-metadata card, and a sticky KPI rail).

## Dependency relations

### `SiteAssetDependency` (Site <- SupportAsset attachment)

`assets.models.site_dependency.SiteAssetDependency`

A support asset (server, network equipment, etc.) is hosted or located at a site. The relation carries its own reference (`SADP-N`), a dependency type, a criticality and an `is_single_point_of_failure` flag computed automatically.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto-generated `SADP-N`, unique | |
| `site` | FK -> Site | required | Site that hosts the asset |
| `support_asset` | FK -> SupportAsset | required | Hosted support asset |
| `dependency_type` | enum | required | `located_at`, `hosted_at`, `deployed_at`, `other` |
| `criticality` | enum | required | `low`, `medium`, `high`, `critical` |
| `description` | text | optional | |
| `is_single_point_of_failure` | boolean | read-only | Computed by the SPOF detection service (M2 §3.3 RS-07) |
| `redundancy_level` | enum | optional | `none`, `partial`, `full` |

### `SiteSupplierDependency` (Site <- Supplier attachment)

`assets.models.site_dependency.SiteSupplierDependency`

A supplier serves / operates / maintains a site.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto-generated `SSDP-N`, unique | |
| `site` | FK -> Site | required | Served site |
| `supplier` | FK -> Supplier | required | Supplier operating on the site |
| `dependency_type` | enum | required | `provides`, `hosts`, `manages`, `develops`, `supports`, `licenses`, `maintains`, `other` |
| `criticality` | enum | required | `low`, `medium`, `high`, `critical` |
| `description` | text | optional | |
| `is_single_point_of_failure` | boolean | read-only | Computed by the SPOF detection service |
| `redundancy_level` | enum | optional | `none`, `partial`, `full` |

## Business rules

| ID | Rule |
|---|---|
| RG-SITE-01 | A site can be attached to one or more `Scope`. A site without a scope is valid (cross-cutting site). |
| RG-SITE-02 | The `parent_site` hierarchy does not tolerate cycles. Detected at `clean()`. |
| RG-SITE-03 | The lifecycle step (`workflow_state`) is unconstrained across sites: any number of sites can be `operational` at once (the single-active rule of the Context module was removed because of the multi-scope hierarchy). |
| RG-SITE-04 | `is_single_point_of_failure` on site dependencies is computed by the `assets.services.spof_detection` service. The value provided on write is ignored. |

## Endpoints

### REST

- `GET /api/v1/context/sites/`: list with filters `type`, `workflow_state`, `parent_site_id`
- `POST /api/v1/context/sites/`
- `GET /api/v1/context/sites/<uuid>/`
- `PUT/PATCH /api/v1/context/sites/<uuid>/`
- `DELETE /api/v1/context/sites/<uuid>/`
- `GET/POST /api/v1/context/sites/<uuid>/transition/`: list the caller's allowed lifecycle transitions (GET) or perform one (POST `target_state`, optional `comment`)
- `POST /api/v1/context/sites/<uuid>/approve/` (deprecated alias of the validate transition)
- The `SiteAssetDependency` and `SiteSupplierDependency` have their own routes under `/api/v1/assets/site-asset-dependencies/` and `/api/v1/assets/site-supplier-dependencies/`.

### MCP

- `list_sites` / `get_site` / `create_site` / `update_site` / `delete_site` / `approve_site` / `batch_create_sites`
- `transition_site` / `site_allowed_transitions` (lifecycle transitions, route through the lifecycle service)
- `list_site_asset_dependencys` / `create_site_asset_dependency` / ...
- `list_site_supplier_dependencys` / `create_site_supplier_dependency` / ...

## Permissions

| Codename | Description |
|---|---|
| `context.site.read` | Read sites |
| `context.site.create` | Create a site |
| `context.site.update` | Modify a site |
| `context.site.delete` | Delete a site |
| `context.site.approve` | Approve a site |

## Migration

The historical `SupportAsset[type=site]` rows were converted to `Site` by the `assets.0029` migration. The mapping applied:

| Former `SupportAsset.category` | New `Site.type` |
|---|---|
| `datacenter` | `datacenter` |
| `office` | `office` |
| `remote_site` | `remote` |
| `cloud_region` | `datacenter` |
| `other_site` | `other` |

The other fields of the support asset (owner, CIA, lifecycle dates, etc.) are not transferred to Site, which does not model them. The `AssetDependency` records that pointed to those support assets were deleted by cascade: they must be recreated as `SiteAssetDependency` on the `Site` side if the relation makes sense.

## References

- [SupportAsset](support-asset.md), [AssetDependency](asset-dependency.md), [Supplier](#m2-assets-supplier-mdtbd) (supplier, spec to come, issue [#35](https://github.com/frousselet/cairn/issues/35))
- Migrations: `context.0027` (rename FR -> EN), `context.0028` (scopes M2M), `assets.0029` (drop site type + conversion), `context.0034` (migrate onto the standardised `site` lifecycle)
- Issues: [#30](https://github.com/frousselet/cairn/issues/30) (this spec), [#31](https://github.com/frousselet/cairn/issues/31) (rename FR -> EN)

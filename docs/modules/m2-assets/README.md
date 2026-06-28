# Module 2: Asset Management

## Functional and technical specifications

**Version:** 1.0
**Date:** 27 February 2026
**Status:** Draft

---

## Entities in this module

- [EssentialAsset](./essential-asset.md)
- [SupportAsset](./support-asset.md)
- [AssetDependency](./asset-dependency.md)
- [AssetGroup](./asset-group.md)
- [AssetValuation](./asset-valuation.md)
- [Site](./site.md) (geographic / physical location, defined in the context app)
- [Supplier](./supplier.md) (third-party vendor, with `SupplierType` and `SupplierTypeRequirement` sub-entities)
- [SupplierRequirement](./supplier-requirement.md) (security requirement enforced on a supplier, with `SupplierRequirementReview` sub-entity)
- [SupplierDependency](./supplier-dependency.md) (support-asset to supplier link)
- [Contract](./contract.md) (Documents area: multi-party contract with parties, amendments and an attached PDF)

---

## 1. General overview

### 1.1 Module objective

The **Asset Management** module is used to identify, classify and keep up to date the inventory of the organization's information assets. It distinguishes **essential assets** (business processes, information) from **support assets** (hardware, software, networks, people, sites) in line with the ISO 27001 (Annex A: A.5.9 to A.5.14), ISO 27005 and EBIOS RM approaches (security baseline and identification of support assets).

This module is the foundation of risk assessment: essential assets carry the security needs (CIA criteria: Availability, Integrity, Confidentiality) and support assets inherit these needs through their dependency relationships.

### 1.2 Functional scope

The module covers four sub-domains:

1. Essential assets (business processes and information)
2. Support assets (hardware, software, networks, people, sites, services)
3. Dependency relationships between essential assets and support assets
4. Valuation and classification of assets (CIA security needs)

### 1.3 Dependencies on other modules

| Target module | Nature of the dependency |
|---|---|
| Context and Organization | Activities/processes (Module 1) are attached to essential assets. The Scope frames the asset inventory. |
| Risk management | Essential and support assets are the subjects of risk assessment (ISO 27005 and EBIOS RM). The CIA security needs feed the impact evaluation. |
| Compliance | Some regulatory requirements bear directly on asset categories (personal data, health data, etc.). |
| Measures | Security measures are applied to support assets to protect essential assets. |
| Suppliers | Support assets of the outsourced service type are linked to suppliers. |
| Incidents | Incidents are attached to the impacted assets. |

---

## 3. Business rules

### 3.1 General rules

| ID | Rule |
|---|---|
| RG-01 | Every asset (essential asset or support asset) must be attached to an active **Scope**. |
| RG-02 | Every asset must have a designated **owner** (`owner_id`). |
| RG-03 | Deleting an asset referenced by the Risks or Measures module is forbidden. Deactivation (`status = decommissioned` or `disposed`) is used instead. |
| RG-04 | Every change to an asset generates an entry in the **audit trail**. |
| RG-05 | The `created_at` and `updated_at` fields are managed automatically by the system. |
| RG-06 | Configurable value lists (categories, types) are managed through the dedicated configuration table. |
| RG-07 | M2M relationships are stored in dedicated join tables. |
| RG-08 | Reference codes (`reference`) follow a configurable format with automatic incrementing. The default prefix is `BE-` for essential assets and `BS-` for support assets. |

### 3.2 Valuation and CIA inheritance rules

| ID | Rule |
|---|---|
| RV-01 | The CIA levels (Availability, Integrity, Confidentiality) of an essential asset are rated on a 5-level scale: `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4). |
| RV-02 | The CIA scale and its associated descriptions are configurable by the administrator. |
| RV-03 | The CIA levels **inherited** by a support asset correspond to the **maximum** of the CIA levels of all essential assets to which it is attached. This calculation is performed automatically. |
| RV-04 | Any change to the CIA levels of an essential asset triggers a **recalculation** of the inherited levels of its associated support assets. |
| RV-05 | The user can view the detail of a support asset's CIA inheritance (which essential assets contribute to each level). |
| RV-06 | Each time the CIA levels of an essential asset are changed, an `AssetValuation` record is created to preserve the history. |

### 3.3 Specific rules

| ID | Rule |
|---|---|
| RS-01 | An essential asset of type `business_process` can only have process categories, and conversely for `information`. |
| RS-02 | A support asset of a given type can only have categories matching that type. |
| RS-03 | A support asset with a past `end_of_life_date` and `status = active` triggers an end-of-life **alert**. |
| RS-04 | A support asset with `status = decommissioned` or `disposed` cannot be attached to new dependencies. |
| RS-05 | An essential asset flagged `personal_data = true` must have `data_classification` set to a level ≥ `confidential`. The system raises an alert otherwise. |
| RS-06 | A child support asset (`parent_asset_id` set) must belong to the same **Scope** as its parent. |
| RS-07 | An `AssetDependency` relationship flagged `is_single_point_of_failure = true` with `redundancy_level = none` triggers a specific **alert** displayed on the dashboard. |
| RS-08 | An essential asset without any associated support asset triggers an **alert** (unsupported essential asset). |
| RS-09 | A support asset without any associated essential asset triggers a **warning** (orphan support asset). |

---

## 4. REST API specifications

### 4.1 General conventions

Identical to Module 1. Base URL: `/api/v1/assets/`

### 4.2 Endpoints: Essential Assets

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/essential-assets` | List all essential assets (filterable) |
| `GET` | `/scopes/{scope_id}/essential-assets` | List the essential assets of a scope |
| `POST` | `/scopes/{scope_id}/essential-assets` | Create an essential asset |
| `GET` | `/essential-assets/{id}` | Essential asset detail |
| `PUT` | `/essential-assets/{id}` | Full update |
| `PATCH` | `/essential-assets/{id}` | Partial update |
| `DELETE` | `/essential-assets/{id}` | Delete (if not referenced) |
| `GET` | `/essential-assets/{id}/supporting-assets` | List the associated support assets |
| `GET` | `/essential-assets/{id}/dependencies` | List the dependency relationships |
| `GET` | `/essential-assets/{id}/valuations` | CIA valuation history |
| `POST` | `/essential-assets/{id}/valuations` | Record a new valuation |
| `GET` | `/essential-assets/{id}/risks` | List the associated risks (Risks module) |
| `GET` | `/essential-assets/categories` | List the available categories |
| `GET` | `/essential-assets/dashboard` | Dashboard data (aggregated KPIs) |

**Specific filtering parameters:**

- `?type=business_process|information`
- `?category=core_process`
- `?confidentiality_level=high,critical`
- `?integrity_level=high,critical`
- `?availability_level=high,critical`
- `?personal_data=true`
- `?data_classification=confidential,restricted,secret`
- `?owner_id={uuid}`
- `?status=active`
- `?has_supporting_assets=true|false`
- `?activity_id={uuid}` (essential assets linked to an activity)

### 4.3 Endpoints: Support Assets

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/support-assets` | List all support assets (filterable) |
| `GET` | `/scopes/{scope_id}/support-assets` | List the support assets of a scope |
| `POST` | `/scopes/{scope_id}/support-assets` | Create a support asset |
| `GET` | `/support-assets/{id}` | Support asset detail |
| `PUT` | `/support-assets/{id}` | Full update |
| `PATCH` | `/support-assets/{id}` | Partial update |
| `DELETE` | `/support-assets/{id}` | Delete (if not referenced) |
| `GET` | `/support-assets/{id}/essential-assets` | List the supported essential assets |
| `GET` | `/support-assets/{id}/dependencies` | List the dependency relationships |
| `GET` | `/support-assets/{id}/inherited-dic` | Detail of the inherited CIA calculation |
| `GET` | `/support-assets/{id}/children` | List the support sub-assets |
| `GET` | `/support-assets/{id}/measures` | List the applied measures (Measures module) |
| `GET` | `/support-assets/{id}/risks` | List the associated risks (Risks module) |
| `GET` | `/support-assets/{id}/incidents` | List the associated incidents (Incidents module) |
| `GET` | `/support-assets/categories` | List the available categories |
| `GET` | `/support-assets/tree` | Support asset tree |
| `GET` | `/support-assets/end-of-life` | List assets at or near end of life |
| `GET` | `/support-assets/dashboard` | Dashboard data (aggregated KPIs) |

**Specific filtering parameters:**

- `?type=hardware|software|network|person|site|service|paper`
- `?category=server`
- `?exposure_level=internet_facing`
- `?environment=production`
- `?inherited_confidentiality=high,critical`
- `?owner_id={uuid}`
- `?supplier_id={uuid}`
- `?status=active`
- `?end_of_life_before={date}` (assets whose end of life is before a date)
- `?has_essential_assets=true|false`
- `?is_orphan=true` (no associated essential asset)
- `?group_id={uuid}`

### 4.4 Endpoints: Asset Dependencies

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/dependencies` | List all dependency relationships |
| `POST` | `/dependencies` | Create a dependency relationship |
| `GET` | `/dependencies/{id}` | Relationship detail |
| `PUT` | `/dependencies/{id}` | Full update |
| `PATCH` | `/dependencies/{id}` | Partial update |
| `DELETE` | `/dependencies/{id}` | Delete a relationship |
| `GET` | `/dependencies/spof` | List the single points of failure |
| `GET` | `/dependencies/graph` | Dependency graph (data for visualization) |

### 4.5 Endpoints: Asset Groups

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/groups` | List the asset groups |
| `POST` | `/groups` | Create a group |
| `GET` | `/groups/{id}` | Group detail |
| `PUT` | `/groups/{id}` | Full update |
| `PATCH` | `/groups/{id}` | Partial update |
| `DELETE` | `/groups/{id}` | Delete a group |
| `POST` | `/groups/{id}/members` | Add members to the group |
| `DELETE` | `/groups/{id}/members/{asset_id}` | Remove a member from the group |
| `GET` | `/groups/{id}/members` | List the group members |

### 4.6 Cross-cutting endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/assets/dashboard` | Module summary dashboard |
| `GET` | `/assets/export` | Global asset export (PDF, DOCX, JSON, CSV) |
| `GET` | `/assets/audit-trail` | Module audit trail |
| `GET` | `/assets/config/enums` | List all configurable value lists |
| `PUT` | `/assets/config/enums/{enum_name}` | Edit a value list |
| `GET` | `/assets/config/dic-scale` | View the configured CIA scale |
| `PUT` | `/assets/config/dic-scale` | Edit the CIA scale |
| `GET` | `/assets/statistics` | Global statistics (breakdown by type, classification, etc.) |
| `POST` | `/assets/import` | Bulk import (CSV, JSON) |
| `GET` | `/assets/alerts` | List the active alerts (end of life, orphans, SPOF, etc.) |

---

## 5. User interface specifications

### 5.1 Navigation

The module is accessible through a main navigation item "Asset Management" that breaks down into sub-menus: Essential assets, Support assets, Asset groups, Dependency mapping, Dashboard.

### 5.2 "Essential assets" view

- **List:** Table with columns (Reference, Name, Type, Category, Owner, C/I/A, Classification, Status). Each CIA level is shown with a colored indicator (green : red). Filtering and sorting on all columns.
- **Detail / Edit:** Form with tabs:
  - *General information:* identification, type, category, owner, custodian.
  - *CIA valuation:* rating of the 3 criteria with sliders or selectors, justifications, MTD/RTO/RPO.
  - *Classification:* data classification, personal data, regulatory constraints.
  - *Relationships:* associated support assets (with dependency type), linked business activities.
  - *History:* history of valuations and changes.
- **Actions:** Create, Edit, Rate (CIA), Export.

### 5.3 "Support assets" view

- **List:** Table with columns (Reference, Name, Type, Category, Owner, Inherited CIA, Environment, Exposure, Status, End of life). Visual indicator for assets at end of life (warning icon). Filtering and sorting on all columns.
- **View by type:** Display grouped by type (hardware, software, network, etc.) with counters.
- **Detail / Edit:** Form with tabs:
  - *General information:* identification, type, category, owner, custodian.
  - *Technical characteristics:* manufacturer, model, version, IP, hostname, OS, serial number.
  - *Lifecycle:* acquisition, end-of-life and warranty dates, environment, exposure.
  - *Inherited CIA:* read-only display of the inherited CIA levels with the detail of their origin (which essential assets).
  - *Relationships:* supported essential assets, support sub-assets, groups, applied measures.
  - *Supplier:* link to the supplier and the contract reference.
  - *History:* change log.
- **Actions:** Create, Edit, Decommission, Export.

### 5.4 "Asset groups" view

- **List:** Table with columns (Name, Type, Number of members, Owner, Status).
- **Detail:** List of members with the ability to add/remove, group information.
- **Actions:** Create, Edit, Add/Remove members, Delete.

### 5.5 "Dependency mapping" view

- **Interactive graph:** Layered (Sugiyama) graph visualization of the relationships between essential assets, support assets, sites and suppliers. Nodes are ranked into columns following the natural dependency flow (Essential -> Support -> Site -> Supplier) so edges flow one way and the graph stays readable instead of collapsing into a force-directed "hairball". Nodes are colored by asset type, with zoom/pan, an orientation toggle (left-to-right / top-to-bottom, defaulting to horizontal and remembered per device in the `depgraph_orientation` cookie) and highlighting of SPOFs (thicker red edges). Edges are drawn thick with directional arrowheads; nodes are fixed by the layout (no drag) and edges are unlabelled to reduce clutter. Clicking a node spotlights its full dependency chain - every node and edge reachable upstream (what it depends on) and downstream (what depends on it) - and dims everything else; clicking the node again or the background clears the selection. Node and edge boxes are sized from the measured caption widths so labels never overlap, the gap between asset-type ranks is sized so the few type ranks span their own axis of the viewport and all fit on screen (top-to-bottom: the type bands fit the height while the populated horizontal axis is panned; left-to-right: the mirror image across the width), and the view is scaled to show as much as possible (refitting on resize) down to a minimum readable zoom, below which the graph stays legible and overflows (anchored top-left for panning) rather than shrinking into illegibility. The layout is computed client-side with dagre; rendering stays on D3.
- **Dependency matrix:** Cross-tabulated view of essential assets x support assets with criticality indicators and dependency type in each cell.
- **View by essential asset:** Selection of an essential asset to display all its associated support assets as a tree.

### 5.6 "Classification and CIA" view

- **CIA heatmap:** Matrix view of essential assets with the 3 columns C, I, A colored by level. Sortable by the highest level.
- **Breakdown by classification:** Pie or bar chart of the breakdown of assets by classification level.
- **Personal data:** Filtered view of essential assets containing personal data, with GDPR categories.

### 5.7 Module dashboard

A summary dashboard aggregates the key information:

- Total number of essential and support assets, breakdown by type and status
- Breakdown of CIA levels (stacked bar chart)
- Number and list of support assets at or near end of life
- Number and list of single points of failure (SPOF)
- Essential assets without an associated support asset
- Orphan support assets (without an essential asset)
- Essential assets containing personal data
- Critical activities and their support assets
- Top 10 most-relied-upon support assets (number of attached essential assets)
- Alerts and required actions

---

## 6. Permissions and access control

### 6.1 RBAC model

| Permission | Description |
|---|---|
| `assets.essential.read` | View essential assets |
| `assets.essential.write` | Create/edit essential assets |
| `assets.essential.evaluate` | Rate the CIA levels |
| `assets.essential.delete` | Delete essential assets |
| `assets.support.read` | View support assets |
| `assets.support.write` | Create/edit support assets |
| `assets.support.delete` | Delete support assets |
| `assets.dependency.read` | View dependency relationships |
| `assets.dependency.write` | Create/edit dependency relationships |
| `assets.dependency.delete` | Delete dependency relationships |
| `assets.group.read` | View asset groups |
| `assets.group.write` | Create/edit asset groups |
| `assets.group.delete` | Delete asset groups |
| `assets.import` | Bulk import assets |
| `assets.export` | Export the module data |
| `assets.config.manage` | Manage the value lists and the CIA scale |
| `assets.audit_trail.read` | View the audit trail |

### 6.2 Suggested application roles

| Role | Permissions |
|---|---|
| **Administrator** | All permissions |
| **CISO / DPO** | All except `*.delete` and `config.manage` |
| **Auditor** | `*.read` + `assets.export` + `assets.audit_trail.read` |
| **Contributor** | `*.read` + `*.write` + `assets.dependency.write` |
| **Asset owner** | `*.read` + `assets.essential.write` + `assets.support.write` + `assets.essential.evaluate` (restricted to their own assets) |
| **Reader** | `*.read` only |

---

## 7. Logging and traceability

### 7.1 Audit Trail

Identical to Module 1 (§7.1). The actions specific to this module include:

| Action | Description |
|---|---|
| `create` | Creation of an asset, group or dependency |
| `update` | Modification of an asset, group or dependency |
| `delete` | Deletion of an asset, group or dependency |
| `evaluate_dic` | Rating or re-rating of the CIA levels |
| `decommission` | Decommissioning of an asset |
| `import` | Bulk import of assets |
| `add_dependency` | Addition of a dependency relationship |
| `remove_dependency` | Removal of a dependency relationship |
| `add_to_group` | Addition of an asset to a group |
| `remove_from_group` | Removal of an asset from a group |

### 7.2 Retention

Identical to Module 1 (§7.2). Configurable duration, default 7 years.

---

## 8. Export and reporting

### 8.1 Export formats

| Format | Content |
|---|---|
| **JSON** | Raw structured export (for API interoperability) |
| **PDF** | Formatted document with inventory, classifications, mapping |
| **DOCX** | Editable document in Word format |
| **CSV** | Separate tabular export: essential assets, support assets, dependencies |

### 8.2 Import

| Format | Content |
|---|---|
| **CSV** | Tabular import with configurable column mapping |
| **JSON** | Structured import conforming to the API schema |

The import supports the following modes: create only, update only, or create + update (upsert based on the reference).

### 8.3 Predefined reports

| Report | Description |
|---|---|
| Essential asset inventory | Complete list with CIA valuation and classification |
| Support asset inventory | Complete list with technical characteristics and inherited CIA |
| Dependency matrix | Cross-tabulation of essential assets x support assets |
| Classification report | Breakdown of assets by classification level |
| Personal data report | Essential assets containing personal data with categories |
| End-of-life report | Support assets at end of life or approaching it |
| SPOF report | Identified single points of failure |
| Coverage report | Unsupported essential assets and orphan support assets |

---

## 9. Notifications and alerts

| Event | Recipients | Channel |
|---|---|---|
| Support asset approaching end of life (30/60/90 days before) | Owner, Administrator | In-app, email |
| Support asset past end of life | Owner, CISO | In-app, email |
| Essential asset without an associated support asset | Owner | In-app |
| Orphan support asset (without an essential asset) | Owner | In-app |
| Single point of failure detected (SPOF without redundancy) | Owner, CISO | In-app, email |
| Personal data with insufficient classification | DPO, Owner | In-app, email |
| Review date reached (essential or support asset) | Owner | In-app, email |
| Change to the CIA levels of an essential asset | Owners of the impacted support assets | In-app |
| Bulk import completed | User who launched the import | In-app, email |
| Warranty approaching expiry (30/60 days before) | Owner | In-app |

---

## 10. Technical considerations

### 10.1 Automatic CIA inheritance calculation

The calculation of a support asset's inherited CIA levels is performed server-side. The algorithm is as follows:

```
For each support asset BS:
    BS.inherited_confidentiality = MAX(C of all essential assets linked via AssetDependency)
    BS.inherited_integrity = MAX(I of all essential assets linked via AssetDependency)
    BS.inherited_availability = MAX(D of all essential assets linked via AssetDependency)
```

This calculation is triggered:
- On the creation or deletion of an `AssetDependency` relationship
- On a change to the CIA levels of an `EssentialAsset`
- Results are cached and invalidated on the events above

### 10.2 Bulk import

Bulk asset import (CSV, JSON) is processed asynchronously:

1. The user uploads the file and configures the column mapping (for CSV)
2. The system validates the file (format, required fields, reference consistency)
3. A pre-import report is generated (number of records, detected errors, warnings)
4. The user confirms the import
5. Processing runs in the background with a notification on completion
6. An import report is generated (successes, failures, skipped records)

### 10.3 Dependency graph

The dependency graph is rendered with a **layered (Sugiyama) layout** computed
client-side by [dagre](https://github.com/dagrejs/dagre) and drawn with D3: the
view feeds dagre the nodes and edges, ranks them into columns along the
dependency flow (`rankdir: LR`, flippable to `TB`), then reads back the node
positions and edge waypoints to draw the same circles, supplier logos, SPOF
styling and tooltips as before. This replaced the previous force-directed
layout, which produced an unreadable "hairball" beyond a few dozen nodes.

The visualization relies on a dedicated API endpoint that returns data in the following format:

```json
{
  "nodes": [
    {
      "id": "uuid-xxx",
      "label": "BE-001 - HR Process",
      "type": "essential_asset",
      "subtype": "business_process",
      "dic": { "c": 3, "i": 2, "d": 3 }
    },
    {
      "id": "uuid-yyy",
      "label": "BS-012 - HRIS Server",
      "type": "support_asset",
      "subtype": "hardware",
      "inherited_dic": { "c": 3, "i": 2, "d": 3 }
    }
  ],
  "edges": [
    {
      "id": "uuid-zzz",
      "source": "uuid-xxx",
      "target": "uuid-yyy",
      "dependency_type": "runs_on",
      "criticality": "high",
      "is_spof": true
    }
  ]
}
```

### 10.4 Multi-tenant

Identical to Module 1 (§10.2). Data isolation via `tenant_id`.

### 10.5 Internationalization (i18n)

Identical to Module 1 (§10.3). French and English support at minimum.

### 10.6 Performance

- Paginated lists must not exceed a response time of **200 ms** for 1,000 records.
- The CIA inheritance calculation must run in under **500 ms** for an essential asset linked to 100 support assets.
- The dependency graph must load in under **2 seconds** for 500 nodes.
- Aggregated dashboards are cached with a TTL of **5 minutes**.
- Large imports (> 500 records) are processed asynchronously with a notification.

### 10.7 Webhooks

Identical to Module 1 (§10.5). Specific events:

- `assets.essential_asset.created`, `updated`, `deleted`
- `assets.essential_asset.dic_evaluated`
- `assets.support_asset.created`, `updated`, `deleted`, `decommissioned`
- `assets.dependency.created`, `deleted`
- `assets.group.members_changed`
- `assets.import.completed`

---

## 11. Acceptance criteria

### 11.1 Functional

- [ ] Full CRUD on essential assets, support assets, groups and dependencies
- [ ] All relationships between entities are functional
- [ ] List views support pagination, sorting, filtering and search
- [ ] CIA rating of essential assets works with history tracking
- [ ] CIA inheritance to support assets is calculated automatically and correctly
- [ ] The detail of CIA inheritance (origin) can be viewed
- [ ] The dependency graph is displayed and interactive
- [ ] The dependency matrix can be viewed
- [ ] The alerts (end of life, SPOF, orphans, personal data) are functional
- [ ] Bulk import (CSV, JSON) is operational with pre-validation
- [ ] Exports are operational in all the planned formats
- [ ] The summary dashboard displays the correct data
- [ ] The view by type and the tree view work

### 11.2 API

- [ ] All documented endpoints are implemented and functional
- [ ] The OpenAPI (Swagger) documentation is generated automatically
- [ ] The error codes and response structures conform to the specifications
- [ ] Pagination, sorting and filtering work on all list endpoints
- [ ] The graph endpoint returns data in the specified format
- [ ] Webhooks are triggered for every mutation event

### 11.3 Security

- [ ] RBAC access control is enforced on every endpoint and every view
- [ ] The "asset owner" restriction properly limits access to the assets the user owns
- [ ] The audit trail records all operations
- [ ] Data is isolated between tenants

### 11.4 Performance

- [ ] Response times meet the defined thresholds (§10.6)
- [ ] The CIA inheritance calculation meets the 500 ms threshold
- [ ] Large imports are processed asynchronously

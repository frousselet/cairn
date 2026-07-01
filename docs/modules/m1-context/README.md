# Module 1: Context and Organization

## Functional and technical specifications

**Version:** 1.0
**Date:** 27 February 2026
**Status:** Draft

---

## Entities in this module

- [Scope](scope.md)
- [Issue](issue.md)
- [Stakeholder](stakeholder.md) (and `StakeholderExpectation`)
- [Objective](objective.md)
- [SwotAnalysis](swot.md) (and `SwotItem`)
- [Role](role.md) (and `Responsibility`)
- [Activity](activity.md)

---

## 1. Overview

### 1.1 Module objective

The **Context and Organization** module is the foundational layer of the GRC tool. It allows the full set of context elements required for risk and compliance governance to be formalized and kept up to date, in line with the requirements of the ISO 27001, ISO 27005 and EBIOS RM standards (notably chapters 4 and 5 of ISO 27001).

### 1.2 Functional scope

The module covers seven sub-domains:

1. Scope of application (ISMS or GRC framework scope)
2. Internal and external issues
3. Stakeholders
4. Security / compliance objectives
5. SWOT analysis
6. Roles and responsibilities
7. Business activities and processes

### 1.3 Dependencies with other modules

| Target module | Nature of the dependency |
|---|---|
| Asset management | Activities/processes are linked to essential assets |
| Risk management | Issues and the scope feed the risk assessment context |
| Compliance | Stakeholders express requirements linked to standards |
| Measures | Objectives are broken down into security measures |
| Suppliers | Supplier-type stakeholders feed the suppliers module |
| Audits | The scope drives the audit program |
| Incidents | Roles and responsibilities define the actors in incident management |
| Training | Roles drive training needs |

---

## Business rules

### General rules

| ID | Rule |
|---|---|
| RG-01 | Every object in the module must be linked to a **Scope**. |
| ~~RG-02~~ | *Rule removed.* Originally: "a single active Scope at a time, older versions move to `archived`". Since the introduction of the scope hierarchy (`parent_scope_id`), several Scopes can legitimately be active at the same time (a group and its subsidiaries, or several ISMS scopes covering distinct entities). The `status` lifecycle remains open : it is up to the organization to choose which scopes it considers active. |
| RG-03 | Deleting an object referenced by another module is forbidden. Deactivation (`status = inactive` or `archived`) is used instead. |
| RG-04 | Any modification of an object generates an entry in the **audit trail** with the user identifier, the date, and the old and new state. |
| RG-05 | The `created_at` and `updated_at` fields are managed automatically by the system. |
| RG-06 | Configurable `enum` value lists (issue categories, stakeholder categories) are managed through a dedicated configuration table. |
| RG-07 | M2M (many-to-many) relationships are stored in dedicated join tables. |

### Specific rules

| ID | Rule |
|---|---|
| RS-01 | An **Issue** of type `internal` can only have internal categories, and conversely for `external`. |
| RS-02 | An **Objective** with `status = achieved` must have `progress_percentage = 100`. |
| RS-03 | A child **Objective** (`parent_objective_id` set) must belong to the same **Scope** as its parent. |
| RS-04 | A child **Activity** must belong to the same **Scope** as its parent. |
| RS-05 | A **SwotItem** in the `strength` or `weakness` quadrant must be consistent with `internal` **Issues**; `opportunity` and `threat` with `external` Issues. This rule is a recommendation (warning) and not a hard block. |
| RS-06 | A **Role** marked `is_mandatory = true` must have at least one assigned user. Otherwise the system raises a compliance warning. |
| RS-07 | The **RACI** matrix (via Responsibility) must comply with the rule: a single `accountable` person per activity. The system raises a warning if this rule is violated. |

---

## REST API specifications

### General conventions

- **Base URL:** `/api/v1/context/`
- **Format:** JSON (application/json)
- **Authentication:** Bearer Token (JWT) or API Key
- **Pagination:** `?page=1&page_size=25` (default: 25, max: 100)
- **Sorting:** `?ordering=name` or `?ordering=-created_at` (prefix `-` = descending)
- **Filtering:** `?status=active&type=internal`
- **Search:** `?search=term` (full-text search on text fields)
- **Including relations:** `?include=stakeholders,issues`
- **Date format:** ISO 8601 (`2026-02-27T14:30:00Z`)
- **HTTP codes:** 200 (OK), 201 (Created), 204 (No Content), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found), 409 (Conflict), 422 (Unprocessable Entity)

### Standard response structure

```json
{
  "status": "success",
  "data": { },
  "meta": {
    "page": 1,
    "page_size": 25,
    "total_count": 142,
    "total_pages": 6
  }
}
```

**Error structure:**

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "name",
        "message": "This field is required."
      }
    ]
  }
}
```

### Endpoints: Scope (Scope of application)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes` | List scopes |
| `POST` | `/scopes` | Create a scope |
| `GET` | `/scopes/{id}` | Scope detail |
| `PUT` | `/scopes/{id}` | Full update |
| `PATCH` | `/scopes/{id}` | Partial update |
| `DELETE` | `/scopes/{id}` | Delete (if not referenced) |
| `POST` | `/scopes/{id}/archive` | Archive a scope |
| `GET` | `/scopes/{id}/history` | Modification history |
| `GET` | `/scopes/{id}/export` | Export (PDF, DOCX, JSON) |

### Endpoints: Issues

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/issues` | List the issues of a scope |
| `POST` | `/scopes/{scope_id}/issues` | Create an issue |
| `GET` | `/issues/{id}` | Issue detail |
| `PUT` | `/issues/{id}` | Full update |
| `PATCH` | `/issues/{id}` | Partial update |
| `DELETE` | `/issues/{id}` | Delete |
| `GET` | `/issues` | List all issues (all scopes, filterable) |
| `GET` | `/issues/categories` | List the available categories |

### Endpoints: Stakeholders

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/stakeholders` | List the stakeholders of a scope |
| `POST` | `/scopes/{scope_id}/stakeholders` | Create a stakeholder |
| `GET` | `/stakeholders/{id}` | Stakeholder detail |
| `PUT` | `/stakeholders/{id}` | Full update |
| `PATCH` | `/stakeholders/{id}` | Partial update |
| `DELETE` | `/stakeholders/{id}` | Delete |
| `GET` | `/stakeholders/{id}/expectations` | List a stakeholder's expectations |
| `POST` | `/stakeholders/{id}/expectations` | Add an expectation |
| `PUT` | `/stakeholders/{id}/expectations/{exp_id}` | Edit an expectation |
| `DELETE` | `/stakeholders/{id}/expectations/{exp_id}` | Delete an expectation |
| `GET` | `/stakeholders/matrix` | Influence/interest matrix (aggregated data) |

### Endpoints: Objectives

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/objectives` | List the objectives of a scope |
| `POST` | `/scopes/{scope_id}/objectives` | Create an objective |
| `GET` | `/objectives/{id}` | Objective detail |
| `PUT` | `/objectives/{id}` | Full update |
| `PATCH` | `/objectives/{id}` | Partial update |
| `DELETE` | `/objectives/{id}` | Delete |
| `GET` | `/objectives/{id}/children` | List the sub-objectives |
| `GET` | `/objectives/{id}/measures` | List the linked measures |
| `GET` | `/objectives/tree` | Full objective tree |
| `GET` | `/objectives/dashboard` | Dashboard data (aggregated KPIs) |

### Endpoints: SWOT

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/swot-analyses` | List SWOT analyses |
| `POST` | `/scopes/{scope_id}/swot-analyses` | Create a SWOT analysis |
| `GET` | `/swot-analyses/{id}` | SWOT analysis detail |
| `PUT` | `/swot-analyses/{id}` | Full update |
| `PATCH` | `/swot-analyses/{id}` | Partial update |
| `DELETE` | `/swot-analyses/{id}` | Delete |
| `POST` | `/swot-analyses/{id}/validate` | Validate the analysis |
| `POST` | `/swot-analyses/{id}/items` | Add a SWOT item |
| `PUT` | `/swot-analyses/{id}/items/{item_id}` | Edit an item |
| `DELETE` | `/swot-analyses/{id}/items/{item_id}` | Delete an item |
| `PATCH` | `/swot-analyses/{id}/items/reorder` | Reorder the items |
| `GET` | `/swot-analyses/{id}/export` | Export (PDF, image, JSON) |

### Endpoints: Roles (Roles and responsibilities)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/roles` | List the roles of a scope |
| `POST` | `/scopes/{scope_id}/roles` | Create a role |
| `GET` | `/roles/{id}` | Role detail |
| `PUT` | `/roles/{id}` | Full update |
| `PATCH` | `/roles/{id}` | Partial update |
| `DELETE` | `/roles/{id}` | Delete |
| `POST` | `/roles/{id}/assign` | Assign a user |
| `DELETE` | `/roles/{id}/assign/{user_id}` | Remove a user |
| `GET` | `/roles/{id}/responsibilities` | List the responsibilities |
| `POST` | `/roles/{id}/responsibilities` | Add a responsibility |
| `PUT` | `/roles/{id}/responsibilities/{resp_id}` | Edit a responsibility |
| `DELETE` | `/roles/{id}/responsibilities/{resp_id}` | Delete a responsibility |
| `GET` | `/scopes/{scope_id}/raci-matrix` | Full RACI matrix of the scope |
| `GET` | `/roles/compliance-check` | Check unfilled mandatory roles |

### Endpoints: Activities

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/scopes/{scope_id}/activities` | List the activities of a scope |
| `POST` | `/scopes/{scope_id}/activities` | Create an activity |
| `GET` | `/activities/{id}` | Activity detail |
| `PUT` | `/activities/{id}` | Full update |
| `PATCH` | `/activities/{id}` | Partial update |
| `DELETE` | `/activities/{id}` | Delete |
| `GET` | `/activities/{id}/children` | List the sub-activities |
| `GET` | `/activities/tree` | Full tree |
| `GET` | `/activities/{id}/assets` | List the linked essential assets |

### Cross-cutting endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/context/dashboard` | Summary dashboard of the module |
| `GET` | `/context/export` | Full context export (PDF, DOCX, JSON) |
| `GET` | `/context/audit-trail` | Audit trail of the module |
| `GET` | `/context/config/enums` | List all configurable value lists |
| `PUT` | `/context/config/enums/{enum_name}` | Edit a value list |

---

## User interface specifications

### Navigation

The module is accessible through a main navigation item "Context & Organization" that breaks down into sub-menus corresponding to each sub-domain (Scope, Issues, Stakeholders, Objectives, SWOT, Roles, Activities).

### "Scope" view

- **List:** Table with columns (Name, Version, Status, Review date) with filters and sorting.
- **Detail / Edit:** Form with tabs: General information, Scopes (geographic, organizational, technical), Exclusions, Applicable standards, History.
- **Actions:** Create, Edit, Archive, Export.

### "Issues" view

- **List:** Table filterable by type (internal/external), category, impact level, status and trend. Alternative view as a "radar" or "heatmap" chart.
- **Detail / Edit:** Form with the fields defined in the data model, and a section linking to stakeholders.
- **Visualization:** Internal/external matrix view color-coded by impact.

### "Stakeholders" view

- **List:** Table filterable by type, category, influence, interest.
- **Influence/Interest matrix:** Graphical visualization positioning each stakeholder on a quadrant (Keep informed, Keep satisfied, Monitor, Collaborate).
- **Detail / Edit:** Form with tabs: Information, Expectations & Requirements, Relationships (issues, standards).

### "Objectives" view

- **List:** Table with a visual progress bar, filterable by category, type, status, owner.
- **Tree:** Hierarchical tree view of parent/child objectives.
- **Dashboard:** Charts of overall progress, breakdown by category, overdue objectives.
- **Detail / Edit:** Form with a KPI section (target value, current value, measurement method).

### "SWOT" view

- **List:** Table of SWOT analyses with date, status.
- **Matrix view:** Classic display in 4 quadrants (Strengths, Weaknesses, Opportunities, Threats) with drag & drop to reorder.
- **Detail:** Each item displays its impact and its links to issues and objectives.
- **Export:** Image (PNG/SVG), PDF.

### "Roles and responsibilities" view

- **List:** Table of roles with number of assigned users, type, status.
- **RACI matrix:** Cross view Activities × Roles with color-coded RACI cells. Editing directly within the matrix is possible.
- **Alerts:** Visual indicators for unfilled mandatory roles and violations of the RACI rule (several Accountable).
- **Detail / Edit:** Form with a responsibilities section and user assignment.

### "Activities" view

- **List:** Table filterable by type, criticality, owner, status.
- **Tree:** Hierarchical view of processes and sub-processes.
- **Mapping:** Graphical view of the interdependencies between activities (optional, v2).
- **Detail / Edit:** Form with links to stakeholders, objectives and essential assets.

### Module dashboard

A summary dashboard aggregates the key information:

- Number of issues by type and impact
- Stakeholder influence/interest matrix (thumbnail)
- Overall progress of objectives
- Latest SWOT analysis
- Coverage of mandatory roles
- Critical activities without an owner
- Alerts and required actions

---

## Permissions and access control

### RBAC model

The module relies on a role-based access control (RBAC) model defined at the global application level.

| Permission | Description |
|---|---|
| `context.scope.read` | View scopes |
| `context.scope.write` | Create/edit scopes |
| `context.scope.delete` | Delete a scope |
| `context.issue.read` | View issues |
| `context.issue.write` | Create/edit issues |
| `context.issue.delete` | Delete issues |
| `context.stakeholder.read` | View stakeholders |
| `context.stakeholder.write` | Create/edit stakeholders |
| `context.stakeholder.delete` | Delete stakeholders |
| `context.objective.read` | View objectives |
| `context.objective.write` | Create/edit objectives |
| `context.objective.delete` | Delete objectives |
| `context.swot.read` | View SWOT analyses |
| `context.swot.write` | Create/edit SWOT analyses |
| `context.swot.validate` | Validate a SWOT analysis |
| `context.swot.delete` | Delete SWOT analyses |
| `context.role.read` | View roles |
| `context.role.write` | Create/edit roles |
| `context.role.assign` | Assign users to roles |
| `context.role.delete` | Delete roles |
| `context.activity.read` | View activities |
| `context.activity.write` | Create/edit activities |
| `context.activity.delete` | Delete activities |
| `context.config.manage` | Manage configurable value lists |
| `context.export` | Export the module's data |
| `context.audit_trail.read` | View the audit trail |

### Suggested application roles

| Role | Permissions |
|---|---|
| **Administrator** | All permissions |
| **CISO / DPO** | All except `*.delete` and `config.manage` |
| **Auditor** | `*.read` + `context.export` + `context.audit_trail.read` |
| **Contributor** | `*.read` + `*.write` (excluding swot.validate) |
| **Reader** | `*.read` only |

---

## Logging and traceability

### Audit Trail

Each create, update or delete operation generates an audit record containing:

| Field | Description |
|---|---|
| `id` | Unique identifier of the entry |
| `timestamp` | UTC timestamp |
| `user_id` | User who performed the action |
| `action` | `create`, `update`, `delete`, `validate`, `archive`, `assign`, `unassign` |
| `entity_type` | Type of entity concerned (e.g. `Scope`, `Issue`, `Stakeholder`) |
| `entity_id` | Identifier of the entity concerned |
| `changes` | JSON object describing the modified fields (`field`, `old_value`, `new_value`) |
| `ip_address` | User's IP address |
| `user_agent` | User-agent of the browser/client |

### Retention

Audit entries are kept for a configurable period (default: 7 years) in line with regulatory requirements.

---

## Export and reporting

### Export formats

| Format | Content |
|---|---|
| **JSON** | Raw structured export (for API interoperability) |
| **PDF** | Formatted document with header, table of contents, sections per entity |
| **DOCX** | Editable Word document |
| **CSV** | Tabular export per entity (issues, stakeholders, objectives, activities) |

### Predefined reports

| Report | Description |
|---|---|
| Context statement of applicability | Summary of the scope, issues and stakeholders |
| Stakeholder matrix | Influence/interest matrix with expectations |
| Objectives report | Progress status of all objectives |
| SWOT | Exportable SWOT visualization |
| RACI matrix | Cross matrix of activities × roles |
| Activity mapping | Hierarchical list with criticality |

---

## Notifications and alerts

| Événement | Recipients | Channel |
|---|---|---|
| Review date reached (scope, issue, stakeholder, objective, SWOT) | Owner / Creator | In-app, email |
| Unfilled mandatory role | Administrator, CISO | In-app, email |
| RACI rule violation | Administrator | In-app |
| Overdue objective (target_date exceeded, status ≠ achieved) | Objective owner | In-app, email |
| Modification of the active scope | All contributors of the scope | In-app |

---

## Technical considerations

### Data versioning

The Scope supports a versioning mechanism to keep the history of changes. Each version is a timestamped snapshot of the scope data at a point in time.

### Multi-tenant

The data model supports multi-tenancy through a `tenant_id` (or organization) field on each root entity, allowing data isolation between organizations.

### Internationalization (i18n)

All interface labels, error messages and enum labels are externalized and translatable. The system supports at least French and English.

### Performance

- Paginated lists must not exceed a response time of **200 ms** for 1,000 records.
- Aggregated dashboards are cached with a TTL of **5 minutes**.
- Large exports (> 500 records) are processed asynchronously with a notification to the user.

### Webhooks

Each mutation event (create, update, delete, status change) can trigger a configurable webhook, allowing integration with third-party tools (SIEM, ITSM, BI tools, etc.).

Typical payload:

```json
{
  "event": "context.issue.updated",
  "timestamp": "2026-02-27T14:30:00Z",
  "tenant_id": "org_xxx",
  "data": {
    "entity_type": "Issue",
    "entity_id": "uuid-xxx",
    "action": "update",
    "changes": { },
    "actor": {
      "user_id": "uuid-yyy",
      "email": "user@example.com"
    }
  }
}
```

---

## Acceptance criteria

### Functional

- [ ] Full CRUD on the 7 entities of the module
- [ ] All relationships between entities are functional
- [ ] List views support pagination, sorting, filtering and search
- [ ] The RACI matrix can be viewed and edited
- [ ] The Influence/Interest matrix can be displayed graphically
- [ ] The SWOT view in 4 quadrants is functional with drag & drop
- [ ] The objective and activity tree is navigable
- [ ] The compliance alerts (mandatory roles, RACI) are functional
- [ ] Exports are operational in all the planned formats
- [ ] The summary dashboard displays the correct data

### API

- [ ] All documented endpoints are implemented and functional
- [ ] The OpenAPI (Swagger) documentation is generated automatically
- [ ] Error codes and response structures comply with the specifications
- [ ] Pagination, sorting and filtering work on all list endpoints
- [ ] Webhooks are triggered for every mutation event

### Security

- [ ] RBAC access control is applied on every endpoint and every view
- [ ] The audit trail records all operations
- [ ] Data is isolated between tenants

### Performance

- [ ] Response times meet the defined thresholds (Performance)
- [ ] Large exports are processed asynchronously

---

*End of the specifications for Module 1: Context and Organization*

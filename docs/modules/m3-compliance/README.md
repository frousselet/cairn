# Module 3: Compliance

## Functional and technical specifications

**Version:** 1.0
**Date:** 27 February 2026
**Status:** Draft

---

## Entities

- [Framework](framework.md): `compliance.models.framework.Framework`
- [Section](section.md): `compliance.models.section.Section`
- [Requirement](requirement.md): `compliance.models.requirement.Requirement`
- [ComplianceAssessment](compliance-assessment.md): `compliance.models.assessment.ComplianceAssessment` (includes `AssessmentResult`)
- [RequirementMapping](requirement-mapping.md): `compliance.models.mapping.RequirementMapping`
- [ComplianceActionPlan](compliance-action-plan.md): `compliance.models.action_plan.ComplianceActionPlan`
- [Attachment](attachment.md): `compliance.models.assessment.AssessmentResultAttachment`

---

## 1. General overview

### 1.1 Module objective

The **Compliance** module makes it possible to manage all the normative, legal and contractual frameworks applicable to the organization, to break down their requirements, to assess the compliance level and to track gaps. It also offers the ability to map requirements across frameworks in order to share compliance efforts.

This module is aligned with the requirements of ISO 27001 (chapters 4.2, A.5.31 to A.5.36 in particular), the GDPR, and any other applicable sector-specific regulation (NIS 2, DORA, HDS, PCI DSS, etc.).

### 1.2 Functional scope

The module covers five sub-domains:

1. Frameworks (standards, laws, regulations, contracts, internal policies)
2. Requirements per framework (structured breakdown of requirements)
3. Compliance assessments (measurement of the compliance level per requirement)
4. Inter-framework mapping (mappings between requirements of different frameworks)
5. Compliance action plans

### 1.3 Dependencies with other modules

| Target module | Nature of the dependency |
|---|---|
| Context and Organization | Interested parties express expectations that may be linked to compliance requirements. The scope frames the applicable frameworks. |
| Asset management | Some requirements relate to asset categories (personal data, critical infrastructure). |
| Risk management | Non-conformities can generate risks. Risk assessment results can justify the applicability of a requirement. |
| Controls | Security controls are the operational responses to compliance requirements. A requirement can be covered by one or more controls. |
| Suppliers | Contractual or regulatory requirements may apply to suppliers. |
| Audits | Audits assess compliance with frameworks. Audit findings are linked to requirements. |
| Incidents | Some incidents reveal non-conformities that must be tracked. |
| Training | Some requirements impose training obligations. |

---

## 3. Business rules

### 3.1 General rules

| ID | Rule |
|---|---|
| RG-01 | Every framework must be attached to a **Scope**. |
| RG-02 | Deleting a framework or a requirement referenced by another module (Controls, Audits, Risks) is forbidden. A deactivation (`status = deprecated` or `archived`) is used instead. |
| RG-03 | Any modification of an object generates an entry in the **audit trail**. |
| RG-04 | The `created_at` and `updated_at` fields are managed automatically by the system. |
| RG-05 | Configurable value lists (categories, types) are managed through the dedicated configuration table. |
| RG-06 | M2M relationships are stored in dedicated join tables. |
| RG-07 | The reference codes (`reference`) of action plans follow a configurable format with automatic incrementation. |

### 3.2 Compliance and assessment rules

| ID | Rule |
|---|---|
| RC-01 | The **overall compliance level** of a framework is computed automatically as the weighted average of the compliance levels of its applicable requirements. Non-applicable requirements are excluded from the calculation. |
| RC-02 | The compliance level of a **section** is computed as the average of the compliance levels of its applicable requirements (and sub-sections). |
| RC-03 | A requirement marked `is_applicable = false` must have an `applicability_justification` field filled in. The system issues a warning otherwise. |
| RC-04 | A requirement with `compliance_status = compliant` must have a `compliance_level` ≥ 80. The system issues a consistency alert otherwise. |
| RC-05 | A requirement with `compliance_status = non_compliant` and `type = mandatory` and a framework `is_mandatory = true` triggers a **critical alert** of regulatory non-conformity. |
| RC-06 | When a **ComplianceAssessment** is validated, the results (`AssessmentResult`) are carried over to the corresponding requirements (`Requirement`) to update their current `compliance_status` and `compliance_level`. |
| RC-07 | The assessment history is retained via the `ComplianceAssessment` / `AssessmentResult` entities. Previous assessments are never overwritten. |

### 3.3 Mapping rules

| ID | Rule |
|---|---|
| RM-01 | A mapping can only exist between requirements of **different frameworks**. |
| RM-02 | A mapping of type `equivalent` between a requirement A and a requirement B implies that the inverse mapping exists automatically (symmetry). |
| RM-03 | A mapping of type `includes` from A → B automatically generates an inverse `included_by` mapping from B → A. |
| RM-04 | Mappings do not automatically propagate compliance levels. Propagation is a **suggestion** presented to the user for manual validation. |
| RM-05 | The system detects and flags **circular mappings** (A → B → C → A) as a warning. |

### 3.4 Action plan rules

| ID | Rule |
|---|---|
| RP-01 | An action plan with a past `target_date` and `status ≠ completed` or `cancelled` automatically moves to `status = overdue`. |
| RP-02 | An action plan with `status = completed` must have `progress_percentage = 100` and `completion_date` filled in. |
| RP-03 | The completion of an action plan triggers a **reassessment suggestion** for the relevant requirement. |

---

## 4. REST API specifications

### 4.1 General conventions

Identical to the previous modules. Base URL: `/api/v1/compliance/`

### 4.2 Endpoints: Frameworks

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/frameworks` | List all frameworks (filterable) |
| `GET` | `/scopes/{scope_id}/frameworks` | List the frameworks of a scope |
| `POST` | `/scopes/{scope_id}/frameworks` | Create a framework |
| `GET` | `/frameworks/{id}` | Framework detail |
| `PUT` | `/frameworks/{id}` | Full update |
| `PATCH` | `/frameworks/{id}` | Partial update |
| `DELETE` | `/frameworks/{id}` | Delete (if not referenced) |
| `GET` | `/frameworks/{id}/sections` | List the framework's sections |
| `GET` | `/frameworks/{id}/requirements` | List all the framework's requirements |
| `GET` | `/frameworks/{id}/compliance-summary` | Compliance summary (by section, by status) |
| `GET` | `/frameworks/{id}/assessments` | List the framework's assessments |
| `GET` | `/frameworks/{id}/export` | Export (PDF, DOCX, JSON, CSV) |
| `GET` | `/frameworks/{id}/soa` | Statement of Applicability |
| `GET` | `/frameworks/categories` | List the available categories |
| `POST` | `/frameworks/import` | Import a framework (JSON, CSV) |

**Specific filtering parameters:**

- `?type=standard|law|regulation|contract|internal_policy`
- `?category=information_security`
- `?is_mandatory=true`
- `?is_applicable=true`
- `?status=active`
- `?owner_id={uuid}`
- `?compliance_level_min=50&compliance_level_max=80`
- `?search=term`

### 4.3 Endpoints: Sections

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/frameworks/{framework_id}/sections` | Create a section |
| `GET` | `/sections/{id}` | Section detail |
| `PUT` | `/sections/{id}` | Full update |
| `PATCH` | `/sections/{id}` | Partial update |
| `DELETE` | `/sections/{id}` | Delete (if no requirement attached) |
| `GET` | `/sections/{id}/children` | List the sub-sections |
| `GET` | `/sections/{id}/requirements` | List the section's requirements |
| `GET` | `/frameworks/{framework_id}/sections/tree` | Full section tree |
| `PATCH` | `/frameworks/{framework_id}/sections/reorder` | Reorder the sections |

### 4.4 Endpoints: Requirements

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/requirements` | List all requirements (all frameworks, filterable) |
| `POST` | `/frameworks/{framework_id}/requirements` | Create a requirement |
| `GET` | `/requirements/{id}` | Requirement detail |
| `PUT` | `/requirements/{id}` | Full update |
| `PATCH` | `/requirements/{id}` | Partial update |
| `DELETE` | `/requirements/{id}` | Delete (if not referenced) |
| `PATCH` | `/requirements/{id}/assess` | Assess the compliance of a requirement (quick update) |
| `GET` | `/requirements/{id}/measures` | List the linked controls |
| `GET` | `/requirements/{id}/mappings` | List the mappings of this requirement |
| `GET` | `/requirements/{id}/action-plans` | List the linked action plans |
| `GET` | `/requirements/{id}/history` | Assessment history of this requirement |
| `GET` | `/requirements/categories` | List the available categories |

**Specific filtering parameters:**

- `?framework_id={uuid}`
- `?section_id={uuid}`
- `?type=mandatory|recommended|optional`
- `?category=technical`
- `?is_applicable=true|false`
- `?compliance_status=non_compliant,partially_compliant`
- `?compliance_level_min=0&compliance_level_max=50`
- `?owner_id={uuid}`
- `?priority=high,critical`
- `?has_measures=true|false`
- `?has_mappings=true|false`
- `?search=term`

### 4.5 Endpoints: Compliance Assessments

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/assessments` | List all assessments |
| `POST` | `/frameworks/{framework_id}/assessments` | Create an assessment for a framework |
| `GET` | `/assessments/{id}` | Assessment detail |
| `PUT` | `/assessments/{id}` | Full update |
| `PATCH` | `/assessments/{id}` | Partial update |
| `DELETE` | `/assessments/{id}` | Delete (only when in draft) |
| `POST` | `/assessments/{id}/validate` | Validate the assessment (carries the results over to the requirements) |
| `POST` | `/assessments/{id}/results` | Add or update a result |
| `GET` | `/assessments/{id}/results` | List the results |
| `PUT` | `/assessments/{id}/results/{result_id}` | Modify a result |
| `GET` | `/assessments/{id}/summary` | Assessment summary (KPIs) |
| `GET` | `/assessments/{id}/export` | Export (PDF, DOCX, JSON) |
| `GET` | `/assessments/{id}/comparison` | Comparison with the previous assessment |

### 4.6 Endpoints: Requirement Mappings (Inter-framework mappings)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/mappings` | List all mappings (filterable) |
| `POST` | `/mappings` | Create a mapping |
| `GET` | `/mappings/{id}` | Mapping detail |
| `PUT` | `/mappings/{id}` | Full update |
| `PATCH` | `/mappings/{id}` | Partial update |
| `DELETE` | `/mappings/{id}` | Delete a mapping |
| `GET` | `/mappings/matrix` | Mapping matrix between two frameworks |
| `GET` | `/mappings/coverage` | Coverage analysis between frameworks |
| `POST` | `/mappings/import` | Bulk import of mappings (CSV, JSON) |

**Filtering parameters:**

- `?source_framework_id={uuid}`
- `?target_framework_id={uuid}`
- `?mapping_type=equivalent|partial_overlap`
- `?coverage_level=full|partial`

### 4.7 Endpoints: Action Plans

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/action-plans` | List all action plans |
| `POST` | `/action-plans` | Create an action plan |
| `GET` | `/action-plans/{id}` | Action plan detail |
| `PUT` | `/action-plans/{id}` | Full update |
| `PATCH` | `/action-plans/{id}` | Partial update |
| `DELETE` | `/action-plans/{id}` | Delete |
| `GET` | `/action-plans/overdue` | List the overdue action plans |
| `GET` | `/action-plans/dashboard` | Dashboard data (aggregated KPIs) |

**Filtering parameters:**

- `?requirement_id={uuid}`
- `?assessment_id={uuid}`
- `?framework_id={uuid}`
- `?owner_id={uuid}`
- `?status=in_progress|overdue`
- `?priority=high,critical`

### 4.8 Cross-cutting endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/compliance/dashboard` | Module summary dashboard |
| `GET` | `/compliance/export` | Global export (PDF, DOCX, JSON) |
| `GET` | `/compliance/audit-trail` | Module audit trail |
| `GET` | `/compliance/config/enums` | List the configurable value lists |
| `PUT` | `/compliance/config/enums/{enum_name}` | Modify a value list |
| `GET` | `/compliance/statistics` | Global compliance statistics |
| `GET` | `/compliance/alerts` | List the active alerts |

---

## 5. User interface specifications

### 5.1 Navigation

The module is accessible via a main navigation item "Compliance" broken down into sub-menus: Frameworks, Requirements, Assessments, Mappings, Action plans, Dashboard.

### 5.2 "Frameworks" view

- **List:** Table with columns (Reference, Name, Type, Category, Mandatory, Compliance %, Status, Owner). Visual compliance gauge for each framework. Filters and sorting on all columns.
- **Detail / Edit:** Form with tabs:
  - *General information:* identification, type, category, issuing body, dates, jurisdiction.
  - *Applicability:* applicability status, justification, linked interested parties.
  - *Structure:* tree of sections and requirements (editable tree view).
  - *Compliance:* visual summary (bar charts by section, pie chart by status), overall level.
  - *Assessments:* assessment history with trend.
  - *Mappings:* mapped frameworks with coverage.
  - *History:* change log.
- **Actions:** Create, Edit, Import, Export, Generate the SoA.

### 5.3 "Requirements" view

- **List:** Table with columns (Reference, Title, Framework, Section, Type, Applicable, Compliance status, Compliance %, Priority, Owner). Colour coding by compliance status (red/orange/green/grey). Advanced filters.
- **View by framework:** Requirements grouped by section, hierarchical display faithful to the framework structure.
- **Detail / Edit:** Form with tabs:
  - *Information:* requirement text, type, category, applicability, justification.
  - *Compliance:* status, level, evidence, gaps. Quick assessment form.
  - *Relationships:* linked controls, essential assets, risks, interested-party expectations.
  - *Mappings:* requirements mapped in other frameworks.
  - *Action plans:* corrective actions in progress.
  - *History:* evolution of the compliance status over time (trend chart).
- **Actions:** Create, Edit, Assess, Export.

### 5.4 "Assessments" view (Compliance Assessments)

- **List:** Table with columns (Name, Framework, Date, Assessor, Compliance %, Status).
- **Detail:** Assessment campaign view with:
  - Progress bar (requirements assessed / total).
  - List of requirements with an inline assessment form (status, level, evidence, gaps).
  - Requirement-by-requirement navigation ("wizard" mode) for systematic assessments.
  - Real-time graphical summary during the assessment.
- **Comparison:** Comparative view between two successive assessments showing the evolution per requirement (progress/regression).
- **Actions:** Create, Assess, Validate, Export, Compare.

### 5.5 "Inter-framework mappings" view

- **Mapping matrix:** Cross table Framework A (rows) × Framework B (columns) with a mapping indicator in each cell. Selection of the two frameworks via filters.
- **View by requirement:** Selection of a requirement to display all its mappings in the other frameworks.
- **Coverage analysis:** For a given framework, the percentage of requirements covered by another framework. Stacked-bar visualization.
- **Detail / Edit:** Form for creating/modifying a mapping with type, coverage, justification.
- **Actions:** Create, Edit, Bulk import, Export.

### 5.6 "Action plans" view

- **List:** Table with columns (Reference, Title, Requirement, Framework, Priority, Owner, Target date, Progress %, Status). Visual progress bar. Colour coding for overdue actions.
- **Kanban:** Column view by status (Planned → In progress → Completed / Overdue).
- **Detail / Edit:** Form with the gap description, remediation plan, links to controls and requirement.
- **Actions:** Create, Edit, Close, Export.

### 5.7 "Statement of Applicability" view (SoA)

Dedicated view specific to ISO 27001:

- Table listing all the Annex A controls with columns (Reference, Title, Applicable, Inclusion/exclusion justification, Implementation status, Reference to the Cairn control).
- Filters by Annex A section, by applicability, by status.
- PDF/DOCX export formatted in line with the expectations of a certification audit.

### 5.8 Module dashboard

A summary dashboard aggregates the key information:

- Overall compliance level per framework (gauges)
- Breakdown of requirements by compliance status (pie chart / stacked bars)
- Evolution of the compliance level over time (trend curve per framework)
- Number of non-compliant requirements by priority (critical, high, medium, low)
- Critical regulatory non-conformities (alerts)
- Overdue action plans
- Mapping coverage between frameworks
- Upcoming review and assessment dates
- Top 10 most at-risk requirements (non-compliant, high priority, mandatory framework)
- Alerts and required actions

---

## 6. Permissions and access control

### 6.1 RBAC model

| Permission | Description |
|---|---|
| `compliance.framework.read` | View frameworks |
| `compliance.framework.write` | Create/modify frameworks |
| `compliance.framework.delete` | Delete frameworks |
| `compliance.section.read` | View sections |
| `compliance.section.write` | Create/modify sections |
| `compliance.section.delete` | Delete sections |
| `compliance.requirement.read` | View requirements |
| `compliance.requirement.write` | Create/modify requirements |
| `compliance.requirement.assess` | Assess the compliance of requirements |
| `compliance.requirement.delete` | Delete requirements |
| `compliance.assessment.read` | View assessments |
| `compliance.assessment.write` | Create/modify assessments |
| `compliance.assessment.validate` | Validate an assessment |
| `compliance.assessment.delete` | Delete assessments |
| `compliance.mapping.read` | View mappings |
| `compliance.mapping.write` | Create/modify mappings |
| `compliance.mapping.delete` | Delete mappings |
| `compliance.action_plan.read` | View action plans |
| `compliance.action_plan.write` | Create/modify action plans |
| `compliance.action_plan.delete` | Delete action plans |
| `compliance.import` | Bulk import frameworks and mappings |
| `compliance.export` | Export the module's data |
| `compliance.config.manage` | Manage the configurable value lists |
| `compliance.audit_trail.read` | View the audit trail |

### 6.2 Suggested application roles

| Role | Permissions |
|---|---|
| **Administrator** | All permissions |
| **CISO / DPO** | All except `*.delete` and `config.manage` |
| **Auditor** | `*.read` + `compliance.export` + `compliance.audit_trail.read` |
| **Assessor** | `*.read` + `compliance.requirement.assess` + `compliance.assessment.write` |
| **Contributor** | `*.read` + `*.write` (excluding validate and config) |
| **Reader** | `*.read` only |

---

## 7. Logging and traceability

### 7.1 Audit Trail

Identical to the previous modules (§7.1 of Module 1). The actions specific to this module include:

| Action | Description |
|---|---|
| `create` | Creation of a framework, section, requirement, mapping or action plan |
| `update` | Modification of an object |
| `delete` | Deletion of an object |
| `assess` | Assessment of the compliance of a requirement |
| `validate_assessment` | Validation of an assessment campaign |
| `import` | Bulk import (framework, mappings) |
| `create_mapping` | Creation of an inter-framework mapping |
| `delete_mapping` | Deletion of a mapping |
| `complete_action_plan` | Closure of an action plan |

### 7.2 Retention

Identical to the previous modules. Configurable duration, default 7 years.

---

## 8. Export and reporting

### 8.1 Export formats

| Format | Content |
|---|---|
| **JSON** | Raw structured export (for API interoperability) |
| **PDF** | Formatted document with compliance summary, detail per framework |
| **DOCX** | Editable document in Word format |
| **CSV** | Tabular export: frameworks, requirements, assessment results, mappings |

### 8.2 Import

| Format | Content |
|---|---|
| **CSV** | Tabular import of frameworks (sections + requirements) and of mappings |
| **JSON** | Structured import conforming to the API schema |

The import supports the following modes: create only, update only, or upsert based on the reference.

### 8.3 Predefined reports

| Report | Description |
|---|---|
| Compliance summary | Global view per framework with gauges and trends |
| Statement of Applicability (SoA) | Table of requirements with applicability and justification (ISO 27001) |
| Assessment report | Detail of the results of an assessment campaign |
| Gap report | List of non-conformities with prioritization |
| Inter-framework coverage report | Coverage analysis between two frameworks via the mappings |
| Action plan tracking | List of action plans with progress and overdue items |
| Trend report | Evolution of compliance over several assessments |
| Personal data report (GDPR) | GDPR requirements with compliance status and associated controls |

---

## 9. Notifications and alerts

| Événement | Recipients | Channel |
|---|---|---|
| Critical non-conformity detected (mandatory requirement, regulatory framework) | CISO, DPO, Framework owner | In-app, email |
| Assessment pending validation | Designated validator | In-app, email |
| Overdue action plan | Action owner, CISO | In-app, email |
| Review date reached (framework, requirement) | Framework owner | In-app, email |
| Framework approaching expiry | Owner, Administrator | In-app, email |
| New assessment available for a framework | Framework owner | In-app |
| Bulk import completed | User who started the import | In-app, email |
| Mapping created on a requirement you own | Requirement owner | In-app |
| Action plan completed: reassessment suggestion | Requirement owner | In-app |
| Compliance level dropped below a configurable threshold | CISO, Framework owner | In-app, email |

---

## 10. Technical considerations

### 10.1 Automatic calculation of compliance levels

The compliance level is calculated server-side according to the following algorithm:

```
For each Framework F:
    applicable_requirements = Requirements of F where is_applicable = true
    F.compliance_level = AVERAGE(compliance_level of each applicable requirement)
    
For each Section S:
    applicable_requirements = Requirements of S (and sub-sections) where is_applicable = true
    S.compliance_level = AVERAGE(compliance_level of each applicable requirement)
```

Default status → level mapping (configurable):

| Status | Default level |
|---|---|
| `not_assessed` | 0 % |
| `non_compliant` | 0 % |
| `partially_compliant` | 50 % |
| `compliant` | 100 % |
| `not_applicable` | Excluded from the calculation |

The recalculation is triggered:
- When the `compliance_status` or `compliance_level` of a requirement is modified
- When an assessment is validated
- When the applicability of a requirement is modified
- The results are cached with event-driven invalidation

### 10.2 Framework import

The import of a complete framework (sections + requirements) is processed asynchronously:

1. The user uploads the file and configures the column mapping (for CSV)
2. The system validates the structure (section hierarchy, unique references)
3. A pre-import report is generated
4. The user confirms the import
5. The processing is executed in the background
6. An import report is generated (successes, failures, duplicates)

**Predefined framework templates** can be provided (ISO 27001 Annex A, GDPR, NIS 2, etc.) as importable JSON files. These templates contain the structure and requirements but not the assessments.

### 10.3 Attachment management

Attachments (documentary evidence) are stored on a file system or object storage (S3-compatible). The metadata is in the database, the binary files on the storage. Configurable maximum size per file (default: 50 MB). Configurable allowed MIME types.

### 10.4 Multi-tenant

Identical to the previous modules. Data isolation via `tenant_id`.

### 10.5 Internationalization (i18n)

Identical to the previous modules. French and English support at minimum. Frameworks and requirements are entered in the user's language; the system does not handle automatic translation of the requirement content.

### 10.6 Performance

- Paginated lists must not exceed a response time of **200 ms** for 1,000 records.
- The compliance-level calculation of a 500-requirement framework must run in less than **1 second**.
- The mapping matrix between two frameworks of 200 requirements each must load in less than **2 seconds**.
- Aggregated dashboards are cached with a TTL of **5 minutes**.
- Large imports (> 200 requirements) are processed asynchronously.

### 10.7 Webhooks

Identical to the previous modules. Specific events:

- `compliance.framework.created`, `updated`, `deleted`
- `compliance.requirement.created`, `updated`, `assessed`
- `compliance.assessment.created`, `validated`
- `compliance.mapping.created`, `deleted`
- `compliance.action_plan.created`, `completed`, `overdue`
- `compliance.import.completed`

---

## 11. Acceptance criteria

### 11.1 Functional

- [ ] Full CRUD on frameworks, sections, requirements, assessments, mappings and action plans
- [ ] All relationships between entities are functional
- [ ] List views support pagination, sorting, filtering and search
- [ ] The hierarchical structure of sections is navigable and editable
- [ ] Compliance assessment works requirement by requirement and in campaign mode
- [ ] The compliance level is calculated automatically at all levels (requirement, section, framework)
- [ ] The comparison between two successive assessments is functional
- [ ] Inter-framework mappings can be created and viewed as a matrix
- [ ] The coverage analysis between frameworks is functional
- [ ] Action plans can be managed with progress tracking
- [ ] The Statement of Applicability (SoA) view is functional and exportable
- [ ] Alerts (critical non-conformity, overdue plans, reviews) are functional
- [ ] The bulk import of frameworks and mappings is operational
- [ ] Exports are operational in all the planned formats
- [ ] The summary dashboard displays the correct data with trends

### 11.2 API

- [ ] All documented endpoints are implemented and functional
- [ ] The OpenAPI (Swagger) documentation is generated automatically
- [ ] Error codes and response structures conform to the specifications
- [ ] Pagination, sorting and filtering work on all list endpoints
- [ ] Webhooks are triggered for every mutation event

### 11.3 Security

- [ ] RBAC access control is applied on each endpoint and each view
- [ ] The `compliance.assessment.validate` permission is required to validate an assessment
- [ ] The `compliance.requirement.assess` permission is required to assess a requirement
- [ ] The audit trail records all operations
- [ ] Data is isolated between tenants
- [ ] Attachments are only accessible to authorized users

### 11.4 Performance

- [ ] Response times meet the defined thresholds (§10.6)
- [ ] The compliance calculation meets the 1-second threshold for 500 requirements
- [ ] Large imports are processed asynchronously

---

*End of the specifications of Module 3: Compliance*

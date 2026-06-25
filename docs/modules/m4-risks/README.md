# Module 4: Risk Management

## Functional and technical specifications

**Version:** 1.0
**Date:** 27 February 2026
**Status:** Draft

---

## Entities in this module

- [RiskAssessment](risk-assessment.md)
- [RiskCriteria](risk-criteria.md) (with ScaleLevel and RiskLevel sub-entities)
- [Risk](risk.md)
- [RiskTreatmentPlan](risk-treatment-plan.md) (with TreatmentAction sub-entity)
- [RiskAcceptance](risk-acceptance.md)
- [ISO27005Risk](iso27005-risk.md) (ISO 27005 sub-module)
- [EBIOS RM sub-module](ebios-rm/README.md)

---

## 1. General presentation

### 1.1 Module objective

The **Risk Management** module makes it possible to conduct the assessment and treatment of information security risks following two complementary methodologies:

- **ISO 27005:2022**: A systematic risk assessment approach based on the identification of threats, vulnerabilities and consequences on assets, with a quantitative or qualitative evaluation of likelihood and impact.
- **EBIOS RM** (Expression des Besoins et Identification des Objectifs de Sécurité : Risk Manager): A structured approach organized into 5 workshops, oriented towards the identification of risk sources, the construction of strategic and operational scenarios, and the iterative treatment of risks.

The module is designed with a **common foundation** (risk criteria, register, treatment) and two **methodological sub-modules** that share the cross-cutting entities. A risk assessment can be conducted following either methodology, and the results converge towards a unified risk register.

### 1.2 Functional scope

The module breaks down into three parts:

**A. Common foundation:**
1. Risk assessment context (scope, criteria, scales)
2. Risk register (consolidated view)
3. Risk treatment (plans, options, tracking)
4. Mapping and reporting

**B. ISO 27005 sub-module:**
1. Risk identification (threats, vulnerabilities, consequences)
2. Risk analysis (likelihood, impact, risk level)
3. Risk evaluation (comparison against acceptance criteria)

**C. EBIOS RM sub-module:**
1. Workshop 1: Security baseline (framing, business and technical scope, gaps)
2. Workshop 2: Risk sources (RS, targeted objectives TO, RS/TO pairs)
3. Workshop 3: Strategic scenarios (stakeholders, attack paths, scenarios)
4. Workshop 4: Operational scenarios (operating modes, technical scenarios)
5. Workshop 5: Risk treatment (strategy, PACS, residual risks)

### 1.3 Dependencies with other modules

| Target module | Nature of the dependency |
|---|---|
| Context and Organization | The scope (Scope), the issues and the interested parties feed the risk assessment context. Business activities are the objects of EBIOS RM workshop 1. |
| Asset management | Essential assets carry the security needs (CIA) and define the impacted business values. Support assets are the targets of vulnerabilities and operational scenarios. |
| Compliance | Non-conformities can generate risks. Compliance requirements can be linked to identified risks. |
| Measures | Security measures reduce the risk level. Risk treatment generates new or reinforced measures. |
| Suppliers | Suppliers are stakeholders of the ecosystem (EBIOS RM workshop 3) and can be risk vectors. |
| Audits | Audit findings can reveal risks or validate the effectiveness of treatments. |
| Incidents | Incidents feed the reassessment of risks and validate (or invalidate) the identified scenarios. |

---

## ISO 27005 sub-module

The ISO 27005 sub-module relies on the triplet approach (threat × vulnerability × asset) for risk analysis. It builds on the `Threat`, `Vulnerability` and `ISO27005Risk` entities, fed by predefined catalogs (ISO 27005 Annex A, ENISA Threat Landscape, CWE).

See the dedicated entity: [ISO27005Risk](iso27005-risk.md).

---

## EBIOS RM sub-module

The EBIOS RM sub-module implements the ANSSI EBIOS RM v1.5 method (2024 edition), structured into 5 workshops (W1 to W5) supplemented by a prerequisite study framework (W0). It feeds the unified risk register through the consolidation of strategic and operational scenarios.

See the dedicated documentation of the sub-module: [EBIOS RM](ebios-rm/README.md).

> **Replacement note (29 May 2026)**: section 4 of the source document M4 (EBIOS RM data model) is **obsolete** and entirely replaced by the dedicated document [ebios-rm/README.md](ebios-rm/README.md), which aligns the EBIOS RM sub-module with the ANSSI v1.5 (2024) guide. In particular, M4bis adds the study framework (workshop 0), the tracking of validation gates per workshop, the ANSSI scoring formulas (RS threat level, ecosystem threat level, likelihood V1-V4), the strategic vs operational cycle, the MITRE ATT&CK integration and the structuring of the PACS. Any EBIOS RM implementation must refer to M4bis. The following sections (rules, API, UI, permissions, export) remain valid for the non-EBIOS parts.

---

## 5. Business rules

### 5.1 General rules

| ID | Rule |
|---|---|
| RG-01 | Every risk assessment must be attached to a **Scope** and use a set of **RiskCriteria**. |
| RG-02 | Deleting a risk referenced by the Measures, Incidents or Compliance module is forbidden. Deactivation via `status = closed` is used instead. |
| RG-03 | Any modification of an object generates an entry in the **audit trail**. |
| RG-04 | Risk levels (initial, current, residual) are **computed automatically** via the matrix defined in the associated `RiskCriteria`. |
| RG-05 | Reference codes follow a configurable format with automatic incrementation. |

### 5.2 Common foundation rules

| ID | Rule |
|---|---|
| RS-01 | The **risk level** is determined by the likelihood × impact crossing in the `risk_matrix` of the `RiskCriteria`. |
| RS-02 | A risk with `current_risk_level` ≥ `acceptance_threshold` and `treatment_decision = not_decided` triggers a **treatment required alert**. |
| RS-03 | A risk with `treatment_decision = accept` must have a valid `RiskAcceptance` record. The system raises an alert if the acceptance has expired (`valid_until` passed). |
| RS-04 | A `RiskTreatmentPlan` with a `target_date` passed and `status ≠ completed` or `cancelled` automatically moves to `status = overdue`. |
| RS-05 | The completion of a `RiskTreatmentPlan` triggers a **reassessment suggestion** for the associated risk (recalculation of the residual level). |
| RS-06 | Validating a `RiskAssessment` locks its data from modification. Any subsequent modification requires creating a new version or moving the status back to `in_progress`. |

### 5.3 ISO 27005 rules

| ID | Rule |
|---|---|
| RI-01 | An `ISO27005Risk` is attached to an assessment with `methodology = iso27005`. |
| RI-02 | The `combined_likelihood` is computed as `MAX(threat_likelihood, vulnerability_exposure)` by default. This computation mode is configurable (MAX, AVERAGE, or custom formula). |
| RI-03 | The `max_impact` is computed as `MAX(impact_confidentiality, impact_integrity, impact_availability)`. Impacts left blank are excluded from the computation. |
| RI-04 | When an `ISO27005Risk` is created, a corresponding `Risk` is automatically proposed to the user for consolidation into the register. The user can merge it with an existing risk or create a new one. |

### 5.4 EBIOS RM rules

| ID | Rule |
|---|---|
| RE-01 | EBIOS RM entities are attached to an assessment with `methodology = ebios_rm`. |
| RE-02 | A `FearedEvent` is associated with a single CIA criterion (`confidentiality`, `integrity` or `availability`). For a given essential asset, there can be up to 3 feared events (one per criterion). |
| RE-03 | Only RS/TO pairs marked `is_retained = true` can be used in strategic scenarios (workshop 3). |
| RE-04 | Only strategic scenarios marked `is_retained = true` can be broken down into operational scenarios (workshop 4). |
| RE-05 | Each `StrategicScenario` and `OperationalScenario` can be consolidated into a `Risk` in the common register via the `risk_id` field. |
| RE-06 | The `gravity_level` of an operational scenario is by default inherited from the parent strategic scenario. The user can adjust it with justification. |
| RE-07 | The attack path steps (`AttackPathStep`) must follow a logical order (increasing `order`). |
| RE-08 | Attack techniques (`AttackTechnique`) can reference the **MITRE ATT&CK** framework. The system offers autocompletion based on an integrated catalog. |

> The detailed EBIOS RM-specific rules (RE-01 to RE-19) of M4bis are documented in [ebios-rm/README.md](ebios-rm/README.md).

---

## 6. REST API specifications

### 6.1 General conventions

Identical to the previous modules. Base URL: `/api/v1/risks/`

### 6.2 Endpoints: Common foundation

#### Risk Assessments (Assessments)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/assessments` | List all assessments |
| `POST` | `/assessments` | Create an assessment |
| `GET` | `/assessments/{id}` | Assessment detail |
| `PUT` | `/assessments/{id}` | Full update |
| `PATCH` | `/assessments/{id}` | Partial update |
| `DELETE` | `/assessments/{id}` | Delete (if in draft) |
| `POST` | `/assessments/{id}/validate` | Validate the assessment |
| `POST` | `/assessments/{id}/duplicate` | Duplicate for a new iteration |
| `GET` | `/assessments/{id}/export` | Export (PDF, DOCX, JSON) |
| `GET` | `/assessments/{id}/summary` | Summary (KPIs) |

#### Risk Criteria (Criteria)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/criteria` | List the criteria sets |
| `POST` | `/criteria` | Create a criteria set |
| `GET` | `/criteria/{id}` | Criteria set detail |
| `PUT` | `/criteria/{id}` | Full update |
| `PATCH` | `/criteria/{id}` | Partial update |
| `DELETE` | `/criteria/{id}` | Delete (if unused) |
| `GET` | `/criteria/{id}/matrix-preview` | Visual preview of the matrix |

#### Risk Register (Risk register)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/risks` | List all risks (register, filterable) |
| `POST` | `/risks` | Create a risk manually |
| `GET` | `/risks/{id}` | Risk detail |
| `PUT` | `/risks/{id}` | Full update |
| `PATCH` | `/risks/{id}` | Partial update |
| `DELETE` | `/risks/{id}` | Delete (if not referenced) |
| `GET` | `/risks/{id}/treatment-plans` | List the treatment plans |
| `GET` | `/risks/{id}/acceptances` | List the acceptances |
| `GET` | `/risks/{id}/history` | History of evaluations |
| `GET` | `/risks/matrix` | Risk mapping (data for the matrix) |
| `GET` | `/risks/dashboard` | Dashboard (KPIs) |

**Filtering parameters:**

- `?assessment_id={uuid}`
- `?methodology=iso27005|ebios_rm`
- `?risk_source=iso27005_analysis|ebios_strategic_scenario|manual`
- `?treatment_decision=accept|mitigate|transfer|avoid|not_decided`
- `?status=identified|analyzed|treatment_in_progress|accepted`
- `?initial_risk_level_min=3`
- `?current_risk_level_min=2`
- `?risk_owner_id={uuid}`
- `?affected_essential_asset_id={uuid}`
- `?priority=high,critical`
- `?search=term`

#### Treatment Plans (Treatment plans)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/treatment-plans` | List all treatment plans |
| `POST` | `/treatment-plans` | Create a treatment plan |
| `GET` | `/treatment-plans/{id}` | Plan detail |
| `PUT` | `/treatment-plans/{id}` | Update |
| `PATCH` | `/treatment-plans/{id}` | Partial update |
| `DELETE` | `/treatment-plans/{id}` | Delete |
| `POST` | `/treatment-plans/{id}/actions` | Add an action |
| `PUT` | `/treatment-plans/{id}/actions/{action_id}` | Modify an action |
| `DELETE` | `/treatment-plans/{id}/actions/{action_id}` | Delete an action |
| `GET` | `/treatment-plans/overdue` | Overdue plans |

#### Risk Acceptances (Acceptances)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/acceptances` | List all acceptances |
| `POST` | `/acceptances` | Create an acceptance |
| `GET` | `/acceptances/{id}` | Acceptance detail |
| `PATCH` | `/acceptances/{id}` | Update (renewal, revocation) |
| `GET` | `/acceptances/expiring` | Acceptances reaching expiration |

### 6.3 Endpoints: ISO 27005

#### Threats (Threats)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/iso27005/threats` | List the threats |
| `POST` | `/iso27005/threats` | Create a threat |
| `GET` | `/iso27005/threats/{id}` | Threat detail |
| `PUT` | `/iso27005/threats/{id}` | Update |
| `DELETE` | `/iso27005/threats/{id}` | Delete |
| `GET` | `/iso27005/threats/catalog` | Predefined threat catalog |
| `POST` | `/iso27005/threats/import-catalog` | Import from the catalog |

#### Vulnerabilities (Vulnerabilities)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/iso27005/vulnerabilities` | List the vulnerabilities |
| `POST` | `/iso27005/vulnerabilities` | Create a vulnerability |
| `GET` | `/iso27005/vulnerabilities/{id}` | Detail |
| `PUT` | `/iso27005/vulnerabilities/{id}` | Update |
| `DELETE` | `/iso27005/vulnerabilities/{id}` | Delete |
| `GET` | `/iso27005/vulnerabilities/catalog` | Predefined catalog |

#### ISO 27005 Risk Analysis

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/iso27005/analyses` | List the ISO 27005 risk analyses |
| `POST` | `/iso27005/analyses` | Create an analysis |
| `GET` | `/iso27005/analyses/{id}` | Analysis detail |
| `PUT` | `/iso27005/analyses/{id}` | Update |
| `DELETE` | `/iso27005/analyses/{id}` | Delete |
| `POST` | `/iso27005/analyses/{id}/consolidate` | Consolidate into a register risk |
| `GET` | `/assessments/{id}/iso27005/summary` | ISO 27005 summary of an assessment |

### 6.4 Endpoints: EBIOS RM

The EBIOS RM endpoints are documented in [ebios-rm/README.md](ebios-rm/README.md#6-rest-api-specifications). EBIOS base URL: `/api/v1/risks/ebios/`.

### 6.5 Cross-cutting endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/risks/dashboard` | Global dashboard of the module |
| `GET` | `/risks/export` | Global export (PDF, DOCX, JSON) |
| `GET` | `/risks/audit-trail` | Audit trail of the module |
| `GET` | `/risks/config/enums` | List the value lists |
| `PUT` | `/risks/config/enums/{enum_name}` | Modify a value list |
| `GET` | `/risks/statistics` | Global statistics |
| `GET` | `/risks/alerts` | Active alerts |

---

## 7. User interface specifications

### 7.1 Navigation

The module is accessible via a main navigation item "Risk Management" breaking down into:

- **Assessments** (list of campaigns)
- **Risk register** (consolidated view)
- **ISO 27005** (submenu: Threats, Vulnerabilities, Analyses)
- **EBIOS RM** (submenu: Workshop 1 to 5)
- **Treatments** (treatment plans, acceptances)
- **Mapping** (risk matrices)
- **Dashboard**

### 7.2 "Assessments" view

- **List:** Table with columns (Reference, Name, Methodology, Date, Owner, Number of risks, Status). Methodology badge (ISO 27005 / EBIOS RM).
- **Creation:** Step-by-step wizard: methodology choice → scope selection → risk criteria selection → general information.
- **Detail:** Summary view with access to the sub-modules and the analysis progress.

### 7.3 "Risk criteria" view

- **Scale editor:** Configuration interface for likelihood and impact levels (adding, modifying, removing levels with label, description and color).
- **Matrix editor:** Interactive grid likelihood (rows) × impact (columns) where each cell is assigned to a risk level by selection. Colored visual preview in real time.
- **Risk levels:** Configuration of the resulting levels with acceptance threshold.

### 7.4 "Risk register" view

- **List:** Table with columns (Reference, Name, Source, Impacted assets, C/I/A, Likelihood, Impact, Initial level, Current level, Residual level, Treatment, Owner, Status). Color coding by risk level. Advanced filters.
- **Risk matrix:** Matrix view likelihood × impact positioning each risk as a bubble (size proportional to the number of impacted assets). Toggle between initial / current / residual risk.
- **Comparison view:** Overlay of the initial and residual positions to visualize the effect of the treatment.
- **Detail / Edit:** Form with tabs (Identification, Analysis, Treatment, Acceptance, History, Relationships).

### 7.5 ISO 27005 views

#### 7.5.1 Threats and vulnerabilities

- **Lists:** Filterable tables with access to the predefined catalog.
- **Catalog:** Library of threats and vulnerabilities with selection and import.

#### 7.5.2 Risk analysis

- **Working view:** Interface for creating the triplets (threat × vulnerability × asset) with likelihood and impact evaluation. Form mode or inline table mode.
- **Cross matrix:** Threats × vulnerabilities view with the assets concerned and the risk levels.
- **Consolidation:** Consolidation button towards the register with a merge option.

### 7.6 EBIOS RM views

The EBIOS RM views are documented in [ebios-rm/README.md](ebios-rm/README.md#8-user-interface-specifications).

### 7.7 Module dashboard

- Total number of risks by level (initial, current, residual)
- Breakdown by treatment decision (pie chart)
- Evolution of risk levels over time (trend curves)
- Matrix risk mapping (interactive thumbnail)
- Top 10 most critical risks
- Overdue treatment plans
- Risk acceptances reaching expiration
- Most exposed essential assets (number of associated risks)
- Coverage of risks by existing measures
- Alerts and required actions

---

## 8. Permissions and access control

### 8.1 RBAC model

| Permission | Description |
|---|---|
| `risks.assessment.read` | View assessments |
| `risks.assessment.write` | Create/modify assessments |
| `risks.assessment.validate` | Validate an assessment |
| `risks.assessment.delete` | Delete assessments |
| `risks.criteria.read` | View risk criteria |
| `risks.criteria.write` | Create/modify criteria |
| `risks.criteria.delete` | Delete criteria |
| `risks.risk.read` | View the risk register |
| `risks.risk.write` | Create/modify risks |
| `risks.risk.delete` | Delete risks |
| `risks.treatment.read` | View treatment plans |
| `risks.treatment.write` | Create/modify treatment plans |
| `risks.treatment.delete` | Delete treatment plans |
| `risks.acceptance.read` | View acceptances |
| `risks.acceptance.write` | Create/modify acceptances (reserved for risk owners) |
| `risks.iso27005.read` | View ISO 27005 data (threats, vulnerabilities, analyses) |
| `risks.iso27005.write` | Create/modify ISO 27005 data |
| `risks.iso27005.delete` | Delete ISO 27005 data |
| `risks.ebios.read` | View EBIOS RM data (workshops 1-5) |
| `risks.ebios.write` | Create/modify EBIOS RM data |
| `risks.ebios.delete` | Delete EBIOS RM data |
| `risks.export` | Export the module's data |
| `risks.config.manage` | Manage catalogs and value lists |
| `risks.audit_trail.read` | View the audit trail |

### 8.2 Suggested application roles

| Role | Permissions |
|---|---|
| **Administrator** | All permissions |
| **CISO / DPO** | All except `*.delete` and `config.manage` |
| **Risk analyst** | `*.read` + `*.write` + `risks.iso27005.*` + `risks.ebios.*` (excluding validate and config) |
| **Risk owner** | `risks.risk.read` + `risks.treatment.read` + `risks.acceptance.write` (restricted to their risks) |
| **Auditor** | `*.read` + `risks.export` + `risks.audit_trail.read` |
| **Reader** | `*.read` only |

---

## 9. Logging and traceability

### 9.1 Audit Trail

Actions specific to this module:

| Action | Description |
|---|---|
| `create` | Creation of a module entity |
| `update` | Modification |
| `delete` | Deletion |
| `validate_assessment` | Validation of an assessment |
| `consolidate_risk` | Consolidation of an analysis/scenario into a register risk |
| `accept_risk` | Formal acceptance of a risk |
| `revoke_acceptance` | Revocation of an acceptance |
| `complete_treatment` | Closure of a treatment plan |
| `evaluate_risk` | Evaluation/reassessment of a risk |

### 9.2 Retention

Identical to the previous modules. Configurable duration, default 7 years.

---

## 10. Export and reporting

### 10.1 Export formats

| Format | Content |
|---|---|
| **JSON** | Raw structured export |
| **PDF** | Formatted report with matrices, mappings, risk detail |
| **DOCX** | Editable document |
| **CSV** | Tabular export (register, threats, vulnerabilities, scenarios) |

### 10.2 Predefined reports

| Report | Description |
|---|---|
| Risk register | Complete list with initial/current/residual levels and treatments |
| Risk mapping | Likelihood × impact matrix (before and after treatment) |
| ISO 27005 assessment report | Complete summary of an ISO 27005 assessment |
| EBIOS RM assessment report | Complete summary of the 5 EBIOS RM workshops |
| Risk treatment plan | List of treatment plans with progress |
| Risk acceptance report | Accepted risks with justification and review dates |
| Trend report | Evolution of risk levels over time |
| PACS (EBIOS RM) | Continuous Security Improvement Plan |
| MITRE ATT&CK matrix | Mapping of the identified attack techniques |

---

## 11. Notifications and alerts

| Event | Recipients | Channel |
|---|---|---|
| Critical-level risk identified | CISO, Risk owner | In-app, email |
| Treatment required (risk above the threshold, untreated) | Risk owner | In-app, email |
| Overdue treatment plan | Plan owner, CISO | In-app, email |
| Risk acceptance reaching expiration (30 days before) | Risk owner, CISO | In-app, email |
| Expired risk acceptance | Risk owner, CISO | In-app, email |
| Assessment pending validation | Validator | In-app, email |
| Review date of a risk reached | Risk owner | In-app, email |
| New risk consolidated into the register | CISO | In-app |
| Treatment plan completed: reassessment suggestion | Risk owner | In-app |
| Periodic reassessment required (configurable frequency) | Assessment owner | In-app, email |

---

## 12. Technical considerations

### 12.1 Automatic computation of risk levels

The computation of the risk level is performed server-side from the matrix defined in the `RiskCriteria`:

```
risk_level = risk_matrix[likelihood][impact]
```

The matrix is stored in JSON format:

```json
{
  "matrix": [
    [1, 1, 2, 3],
    [1, 2, 3, 4],
    [2, 3, 3, 4],
    [3, 3, 4, 4]
  ]
}
```

Where `matrix[likelihood_index][impact_index]` returns the `risk_level`.

The recalculation is triggered on each modification of likelihood or impact, and on the modification of the risk criteria (recalculation of all the associated risks).

### 12.2 Risk consolidation

The consolidation mechanism makes it possible to create a `Risk` in the common register from an `ISO27005Risk`, `StrategicScenario` or `OperationalScenario`:

1. The user initiates the consolidation from the source entity
2. The system offers to create a new risk or to merge with an existing risk (similarity search)
3. The data is pre-filled from the source entity
4. The user validates and adjusts
5. The bidirectional link is maintained (`source_entity_id` / `risk_id`)

### 12.3 MITRE ATT&CK catalog

A MITRE ATT&CK catalog is integrated and updated periodically. It provides:

- The list of tactics and techniques with descriptions
- Autocompletion when entering attack techniques
- Heatmap visualization of the techniques identified in the scenarios

### 12.4 Threat and vulnerability catalogs

Predefined catalogs are provided at installation:

- **Threats**: based on ISO 27005 Annex A and ENISA Threat Landscape
- **Vulnerabilities**: based on ISO 27005 Annex D and CWE (Common Weakness Enumeration)

These catalogs are importable in one click and can be customized afterwards.

### 12.5 Multi-tenant

Identical to the previous modules. The predefined catalogs are global (shared across tenants); the elements added by users are isolated per tenant.

### 12.6 Internationalization (i18n)

Identical to the previous modules. The predefined catalogs are provided in French and in English.

### 12.7 Performance

- Paginated lists must not exceed **200 ms** for 1,000 records.
- The computation of the risk matrix for 500 risks must run in less than **1 second**.
- The ecosystem graph (Workshop 3) must load in less than **2 seconds** for 50 nodes.
- The MITRE ATT&CK heatmap must load in less than **1 second**.
- Aggregated dashboards are cached with a TTL of **5 minutes**.
- Large exports are processed asynchronously.

### 12.8 Webhooks

Specific events:

- `risks.assessment.created`, `validated`
- `risks.risk.created`, `updated`, `consolidated`
- `risks.risk.level_changed` (risk level change)
- `risks.treatment_plan.created`, `completed`, `overdue`
- `risks.acceptance.created`, `expired`, `revoked`
- `risks.ebios.scenario_created` (strategic or operational)

---

## 13. Acceptance criteria

### 13.1 Common foundation

- [ ] Full CRUD on assessments, criteria, risks, treatment plans and acceptances
- [ ] The risk matrix is configurable (scales, levels, colors)
- [ ] Risk levels (initial, current, residual) are computed automatically via the matrix
- [ ] The risk register can be browsed with all the filters
- [ ] The matrix risk mapping is interactive (initial/current/residual toggle)
- [ ] Treatment plans support progress tracking and overdue detection
- [ ] Formal risk acceptance is functional with expiration management
- [ ] The dashboard displays correct data with trends

### 13.2 ISO 27005

- [ ] The threat and vulnerability catalogs are importable
- [ ] The triplet risk analysis (threat × vulnerability × asset) is functional
- [ ] The combined likelihood computation is correct
- [ ] Consolidation into the register works (creation and merge)
- [ ] The ISO 27005 assessment report can be generated

### 13.3 EBIOS RM

- [ ] The 5 workshops are accessible and sequenced
- [ ] Workshop 1: feared events and baseline gaps are manageable
- [ ] Workshop 2: risk sources, targeted objectives and RS/TO pairs are manageable, the cross matrix is functional
- [ ] Workshop 3: the ecosystem graph is interactive, strategic scenarios and attack paths are editable
- [ ] Workshop 4: operational scenarios and attack techniques are editable, MITRE ATT&CK autocompletion works
- [ ] Workshop 5: the before/after mapping is functional, the PACS can be generated
- [ ] The consolidation of scenarios into the register works
- [ ] The complete EBIOS RM assessment report can be generated

### 13.4 API

- [ ] All the documented endpoints are implemented and functional
- [ ] The OpenAPI (Swagger) documentation is generated automatically
- [ ] The error codes and response structures are compliant
- [ ] The webhooks are triggered for each mutation event

### 13.5 Security

- [ ] The RBAC access control is applied on each endpoint and view
- [ ] The "risk owner" restriction correctly limits acceptance to risks the user owns
- [ ] The audit trail records all operations
- [ ] Data is isolated between tenants

### 13.6 Performance

- [ ] Response times meet the defined thresholds (§12.7)
- [ ] Large exports are processed asynchronously

---

*End of the specifications for Module 4: Risk Management*

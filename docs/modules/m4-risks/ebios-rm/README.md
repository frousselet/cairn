# Module 4 bis - EBIOS Risk Manager

## Functional and technical specifications (ANSSI EBIOS RM v1.5 - 2024 compliance)

**Version:** 1.0
**Date:** 29 May 2026
**Status:** Draft
**Replaces:** Section 4 of document M4 (see [../README.md](../README.md))

---

## Entities in this sub-module

- **W0: Study framework**
  - [StudyFramework](study-framework.md) (EFRA)
  - [EbiosWorkshopProgress](workshop-progress.md) (EWSP)
- **W1: Security baseline**
  - [SecurityBaseline](security-baseline.md) (EBSL)
  - [FearedEvent](feared-event.md) (EFER)
  - [BaselineGap](baseline-gap.md) (EBGP)
- **W2: Risk sources and targeted objectives**
  - [RiskSource](risk-source.md) (ERSC)
  - [TargetedObjective](targeted-objective.md) (ETOV)
  - [RiskSourceObjectivePair](sr-ov-pair.md) (ESOV)
- **W3: Ecosystem and strategic scenarios**
  - [EcosystemStakeholder](ecosystem-stakeholder.md) (EECS)
  - [StrategicScenario](strategic-scenario.md) (ESTS)
  - [AttackPathStep](attack-path-step.md) (EAPS)
- **W4: Operational scenarios**
  - [MitreAttackTechnique](mitre-attack-technique.md)
  - [OperationalScenario](operational-scenario.md) (EOPS)
  - [AttackTechnique](attack-technique.md) (EATT)
- **W5: Summary and PACS**
  - [EbiosSummary](ebios-summary.md) (ESUM)
  - [PACSMeasure](pacs-measure.md) (EPAC)

---

## 1. Overview

### 1.1 Purpose of the module

The **EBIOS Risk Manager** module implements the digital risk assessment and treatment method published by ANSSI (the French National Cybersecurity Agency). It targets **strict compliance with the ANSSI EBIOS RM v1.5 guide (2024 edition)**, which updates the v1.0 (2018) method with an explicit integration of MITRE ATT&CK for modelling operational scenarios and a refinement of the scoring grids.

This document is self-contained: reading it does not require prior knowledge of document M4 (see [../README.md](../README.md)). It nevertheless sits within Module 4 "Risk Management" and reuses the common foundation (risk register, criteria, treatment, acceptance) defined in M4 §2.

### 1.2 Positioning vs ISO 27005

EBIOS RM and ISO 27005:2022 coexist within Module 4 according to the following principle:

| Aspect | ISO 27005 | EBIOS RM |
|---|---|---|
| Approach | Analysis by threat × vulnerability × asset triplet | Approach by scenarios built from risk sources |
| Granularity | Atomic risk on a single asset | High-level strategic scenario + technical operational scenario |
| Cycle | Single iteration per assessment | 5 chained workshops, iterative strategic and operational cycles |
| Common output | Risk (register) | Risk (register) |

Both methods feed a **unified risk register** (the [`Risk`](../risk.md) entity of the common foundation). An assessment ([`RiskAssessment`](../risk-assessment.md)) is conducted according to a single methodology: the `methodology` field is set to `iso27005` or `ebios_rm`.

### 1.3 Functional scope

The EBIOS RM sub-module covers:

- **Workshop 0 - Study framework**: scope, participants, applicable frameworks, assumptions, time and budget constraints (not described as a formal workshop in ANSSI v1.5 but required as a prerequisite).
- **Workshop 1 - Security baseline**: business values, support assets, feared events, gaps against the baseline.
- **Workshop 2 - Risk sources and targeted objectives**: SR/OV, assessment, retained pairs.
- **Workshop 3 - Strategic scenarios**: mapping of the digital threat across the ecosystem, high-level attack paths.
- **Workshop 4 - Operational scenarios**: detailed modes of operation, aligned with MITRE ATT&CK.
- **Workshop 5 - Risk treatment**: strategy, PACS (Continuous Security Improvement Plan), before/after mapping, residual risks.

### 1.4 Dependencies on other modules

| Target module | Nature of the dependency |
|---|---|
| Module 1 - Context | The `Scope` anchors the assessment. `Activity` and `Stakeholder` feed workshop 1 (business values) and 3 (ecosystem). |
| Module 2 - Asset management | `EssentialAsset` carries the DIC security needs. `SupportAsset` and `AssetDependency` structure workshop 4. |
| Module 3 - Compliance | `Framework` and `Requirement` make up the reference security baseline (workshop 1). A `BaselineGap` may reference a `Requirement`. |
| Module 4 - Risk foundation | The [`RiskCriteria`](../risk-criteria.md), [`Risk`](../risk.md), [`RiskTreatmentPlan`](../risk-treatment-plan.md), [`RiskAcceptance`](../risk-acceptance.md) of the common foundation are reused. Strategic and operational scenarios consolidate into `Risk`. |
| Suppliers | `Supplier` appears as an ecosystem stakeholder (workshop 3). |

### 1.5 Integration with the unified risk register

Consolidation into the unified register follows these rules:

- A [`StrategicScenario`](strategic-scenario.md) can be consolidated into a [`Risk`](../risk.md) (field `Risk.risk_source = ebios_strategic_scenario`).
- An [`OperationalScenario`](operational-scenario.md) can be consolidated into a [`Risk`](../risk.md) (field `Risk.risk_source = ebios_operational_scenario`).
- In practice, consolidation occurs mostly at the operational level (workshop 4) because it carries the measured technical likelihood.
- The [`PACSMeasure`](pacs-measure.md) entries (PACS measures) are linked to one or more [`RiskTreatmentPlan`](../risk-treatment-plan.md) of the common foundation.

---

## 2. ANSSI EBIOS RM v1.5 concepts

### 2.1 Vocabulary and glossary

| ANSSI term | Code | Definition |
|---|---|---|
| Business value | - | Service, activity or information to be protected. Modelled by `context.Activity` and `assets.EssentialAsset`. |
| Support asset | - | Technical, organisational or human component that carries business values. Modelled by `assets.SupportAsset`. |
| Feared event (ER) | EFER | Harmful effect on a business value expressed as a breach of a DIC criterion. |
| Risk source (SR) | ERSC | Element (person, group, organisation, State, phenomenon) at the origin of a risk. |
| Targeted objective (OV) | ETOV | Goal pursued by a risk source (e.g. financial gain, destruction, espionage). |
| Risk-source / targeted-objective pair (SR-OV) | ESOV | Formal SR x OV association assessed for relevance. |
| Ecosystem stakeholder | EECS | Ecosystem actor that may constitute an attack vector. |
| Strategic scenario | ESTS | High-level attack path from a risk source to a targeted objective via the ecosystem. |
| Operational scenario | EOPS | Technical breakdown of a strategic scenario with modes of operation on support assets. |
| Severity | - | Impact level of a feared event or a scenario (scale 1 to 4 or 1 to 5). |
| Likelihood | - | Probability of occurrence. ANSSI uses the V1-V4 scale for the operational level. |
| PACS | EPAC | Continuous Security Improvement Plan. Consolidation of the measures arising from workshop 5. |
| Security baseline | EBSL | The set of rules, measures and frameworks that make up the applicable security foundation. |
| DIC | - | Confidentiality, Integrity, Availability. Primary security criteria. |
| Strategic cycle | - | Long (annual) loop for re-assessing workshops 1 to 3 and 5. |
| Operational cycle | - | Short (half-yearly) loop for re-assessing workshops 4 and 5. |

### 2.2 The 5 workshops and their deliverables

| Workshop | Title | Mandatory ANSSI deliverables | Validation gate |
|---|---|---|---|
| W1 | Security baseline | List of business values, list of support assets, feared events, gaps against the baseline | Validation by business management |
| W2 | Risk sources | SR/OV catalogue, retained SR/OV pairs with justification | Validation by the CISO |
| W3 | Strategic scenarios | Mapping of the digital threat across the ecosystem, retained strategic scenarios | Validation by the CISO |
| W4 | Operational scenarios | Operational scenarios with modes of operation (MITRE ATT&CK), V1-V4 assessment | Validation by the CISO |
| W5 | Risk treatment | PACS, before/after mapping, residual risk register | Validation by executive management |

A validation gate can only be cleared once the preceding workshop is validated (state `validated`). The system refuses the creation of entities belonging to a higher workshop if the lower workshop is not validated.

### 2.3 Strategic cycle vs operational cycle

EBIOS RM is iterative:

- **Strategic cycle (long)**: full rework of workshops 1, 2, 3 and 5. Triggered by a major change in context (new activity, merger, regulatory change). Typical cadence: annual.
- **Operational cycle (short)**: rework of workshops 4 and 5 only, building on the outputs of the current strategic cycle. Typical cadence: half-yearly or quarterly.

The [`EbiosWorkshopProgress`](workshop-progress.md) model carries the `iteration_type` (strategic, operational) and `iteration_number` (incremented integer) fields to track these cycles.

### 2.4 Risk sources vs targeted objectives

A **risk source** is the author or vector of the risk. A **targeted objective** is the intent of the risk source. A single SR may pursue several OV, and a single OV may be pursued by several SR. The assessment applies to the **pairs** SR/OV (ANSSI v1.5 §3.3).

SR categories (ANSSI enumeration):

`state`, `organized_crime`, `terrorist`, `activist`, `competitor`, `employee`, `service_provider`, `amateur`, `natural`, `other`.

OV categories (ANSSI enumeration):

`lucrative`, `strategic`, `terrorist`, `ideological`, `revenge`, `ludic`, `other`.

### 2.5 Strategic scenarios vs operational scenarios

| Aspect | Strategic scenario | Operational scenario |
|---|---|---|
| Level | Strategic (who, why, through where) | Technical (how, on what) |
| Granularity | Attack path traversing the ecosystem | Sequence of technical actions |
| Actors | SR + ecosystem stakeholders | SR + support assets |
| Assessment | Severity + strategic likelihood | Severity (inherited) + operational likelihood V1-V4 |
| Technical framework | - | MITRE ATT&CK Enterprise Matrix |
| Workshop | W3 | W4 |

Every operational scenario **must** be attached to a parent strategic scenario.

### 2.6 Mapping of the digital threat across the ecosystem

A central concept of ANSSI v1.5 workshop 3. Each ecosystem stakeholder is positioned on a graph (**control** zone, **monitoring** zone, **danger** zone) according to its computed threat level.

The ANSSI formula is:

```
niveau_de_menace = (dependance * penetration) / (maturite * confiance)
```

Where:
- `dependance`: the organisation's level of dependency on the stakeholder (1 to 4).
- `penetration`: the stakeholder's degree of penetration into the ecosystem (1 to 4).
- `maturite`: the stakeholder's cyber maturity (1 to 4).
- `confiance`: the level of trust in the stakeholder (1 to 4).

Zoning thresholds (configurable):
- `niveau_de_menace < 0.5`: **control** zone (green).
- `0.5 <= niveau_de_menace < 1.5`: **monitoring** zone (orange).
- `niveau_de_menace >= 1.5`: **danger** zone (red).

### 2.7 PACS (Continuous Security Improvement Plan)

The PACS is the structuring deliverable of workshop 5. It lists the security **measures** decided upon to treat residual risks beyond the existing baseline. Each measure is carried by a [`PACSMeasure`](pacs-measure.md) instance with a due date, owner, cost, expected gain, status, and a link to a [`RiskTreatmentPlan`](../risk-treatment-plan.md) of the common foundation.

### 2.8 ANSSI scoring grids

**Grid A - Threat level of an SR** (workshop 2, aggregate of motivation x resources x activity, returning V1 to V4):

| Motivation \ Resources | Limited | Moderate | Significant | Unlimited |
|---|---|---|---|---|
| Low | V1 | V1 | V2 | V2 |
| Moderate | V1 | V2 | V3 | V3 |
| High | V2 | V3 | V3 | V4 |
| Very high | V2 | V3 | V4 | V4 |

Activity (low, medium, high) may raise the resulting level by one notch (configurable).

**Grid B - Operational likelihood V1-V4** (workshop 4):

| Code | Label | ANSSI criterion |
|---|---|---|
| V1 | Minimal | Occurrence unlikely. No known mode of operation, or technically very difficult. |
| V2 | Significant | Occurrence possible. Documented mode of operation, but requires specific skills. |
| V3 | Strong | Occurrence probable. Proven mode of operation, accessible to an intermediate-level attacker. |
| V4 | Maximal | Occurrence almost certain. Automated or trivial mode of operation. |

---

## 3. Technical architecture

### 3.1 Positioning within the `risks/` app

The EBIOS RM sub-module is implemented in the existing Django app `risks/`. The EBIOS models are grouped in a dedicated sub-package `risks/models/ebios/` (one file per model). The sub-package's `__init__.py` re-exports the classes into `risks.models` to keep a stable API.

```
risks/
  models/
    __init__.py            # re-exports everything
    risk.py                # existing
    risk_assessment.py     # existing
    risk_criteria.py       # existing
    iso27005_risk.py       # existing
    threat.py              # existing
    vulnerability.py       # existing
    treatment.py           # existing
    acceptance.py          # existing
    ebios/
      __init__.py
      study_framework.py
      workshop_progress.py
      security_baseline.py
      feared_event.py
      baseline_gap.py
      risk_source.py
      targeted_objective.py
      sr_ov_pair.py
      ecosystem_stakeholder.py
      strategic_scenario.py
      attack_path_step.py
      operational_scenario.py
      attack_technique.py
      mitre_attack.py
      ebios_summary.py
      pacs_measure.py
```

Views, forms, templates and the API are organised in mirror: `risks/views/ebios/...`, `risks/forms/ebios.py`, `risks/templates/risks/ebios/...`, `risks/api/ebios/...`.

### 3.2 Integration with the common foundation

The parent entity remains [`RiskAssessment`](../risk-assessment.md) (existing, M4 §2.1) with `methodology = ebios_rm`. The EBIOS entities are attached via FK to `RiskAssessment` (directly or indirectly). No duplication of criteria, register or treatment plans: everything goes through the entities of the common foundation.

### 3.3 Reuse of existing entities

| Existing entity | EBIOS RM reuse |
|---|---|
| `context.Scope` | Anchor of the assessment. |
| `context.Activity` | Source of business values (workshop 1). |
| `context.Stakeholder` | Optional FK from [`EcosystemStakeholder`](ecosystem-stakeholder.md) (workshop 3). |
| `assets.EssentialAsset` | Target of feared events (workshop 1) and targeted objectives (workshop 2). |
| `assets.SupportAsset` | Target of operational scenarios (workshop 4). |
| `assets.AssetDependency` | Reads the technical mapping to suggest the impacted support assets. |
| `assets.Supplier` | Natural candidate for [`EcosystemStakeholder`](ecosystem-stakeholder.md) (workshop 3). |
| `compliance.Requirement` | FK from [`BaselineGap`](baseline-gap.md) (workshop 1). |
| [`risks.Risk`](../risk.md) | Consolidation target from [`StrategicScenario`](strategic-scenario.md) and [`OperationalScenario`](operational-scenario.md). |
| [`risks.RiskTreatmentPlan`](../risk-treatment-plan.md) | FK from [`PACSMeasure`](pacs-measure.md) (workshop 5). |
| [`risks.RiskCriteria`](../risk-criteria.md) | Source of the likelihood/impact scales and the computation matrix. |

### 3.4 `EbiosWorkshopProgress` workflow

When an assessment with `methodology = ebios_rm` is created, the system automatically creates **6 instances** of [`EbiosWorkshopProgress`](workshop-progress.md) (W0 to W5). Each instance carries a state (`not_started`, `in_progress`, `under_review`, `validated`, `rejected`) and feeds the stepper UI (compliance/assessment_detail.html pattern).

A validation gate is cleared by a POST call to `/risks/ebios/workshops/{id}/validate` which:
1. Checks that the mandatory deliverables of the workshop are present.
2. Checks that all preceding workshops are in state `validated`.
3. Sets the state to `validated`, records `validated_by` and `validated_at`.
4. Emits a `risks.ebios.workshop_validated` webhook.

### 3.5 Summary table of reference prefixes

| EBIOS entity | Prefix | Example |
|---|---|---|
| StudyFramework | EFRA | EFRA-1 |
| EbiosWorkshopProgress | EWSP | EWSP-1 |
| SecurityBaseline | EBSL | EBSL-1 |
| FearedEvent | EFER | EFER-1 |
| BaselineGap | EBGP | EBGP-1 |
| RiskSource | ERSC | ERSC-1 |
| TargetedObjective | ETOV | ETOV-1 |
| RiskSourceObjectivePair | ESOV | ESOV-1 |
| EcosystemStakeholder | EECS | EECS-1 |
| StrategicScenario | ESTS | ESTS-1 |
| AttackPathStep | EAPS | EAPS-1 |
| OperationalScenario | EOPS | EOPS-1 |
| AttackTechnique | EATT | EATT-1 |
| EbiosSummary | ESUM | ESUM-1 |
| PACSMeasure | EPAC | EPAC-1 |

The [`MitreAttackTechnique`](mitre-attack-technique.md) model (catalogue) does not use an internal prefix: its natural key is `mitre_id` (e.g. T1566.001).

---

## 4. Data model by workshop

All EBIOS entities inherit from `BaseModel` (UUID, timestamps, `created_by`, approval, versioning, tags) or from `ScopedModel` (same + M2M `scopes`) depending on their scope. Unless stated otherwise, EBIOS entities are attached to a [`RiskAssessment`](../risk-assessment.md) and inherit its scope (no `scopes` of their own).

The detailed definitions of each entity are published in dedicated files:

- **W0**: [StudyFramework](study-framework.md), [EbiosWorkshopProgress](workshop-progress.md)
- **W1**: [SecurityBaseline](security-baseline.md), [FearedEvent](feared-event.md), [BaselineGap](baseline-gap.md)
- **W2**: [RiskSource](risk-source.md), [TargetedObjective](targeted-objective.md), [RiskSourceObjectivePair](sr-ov-pair.md)
- **W3**: [EcosystemStakeholder](ecosystem-stakeholder.md), [StrategicScenario](strategic-scenario.md), [AttackPathStep](attack-path-step.md)
- **W4**: [MitreAttackTechnique](mitre-attack-technique.md), [OperationalScenario](operational-scenario.md), [AttackTechnique](attack-technique.md)
- **W5**: [EbiosSummary](ebios-summary.md), [PACSMeasure](pacs-measure.md)

Workshop 5 also reuses the entities of the common foundation: [`Risk`](../risk.md), [`RiskTreatmentPlan`](../risk-treatment-plan.md), [`TreatmentAction`](../risk-treatment-plan.md), [`RiskAcceptance`](../risk-acceptance.md).

---

## 5. EBIOS RM business rules

| ID | Rule |
|---|---|
| RE-01 | All EBIOS entities are attached to a [`RiskAssessment`](../risk-assessment.md) whose `methodology = ebios_rm`. Creation is refused if the assessment is `iso27005`. |
| RE-02 | When an ebios_rm [`RiskAssessment`](../risk-assessment.md) is created, the system automatically creates: 1 [`StudyFramework`](study-framework.md) (status draft), 6 [`EbiosWorkshopProgress`](workshop-progress.md) (W0 to W5, status not_started). |
| RE-03 | A workshop validation gate can only be cleared once all preceding workshops are in state `validated`. |
| RE-04 | For `EbiosWorkshopProgress.workshop_number = N`, the mandatory deliverables are checked before validation: W0 = StudyFramework status validated; W1 = SecurityBaseline + at least 1 FearedEvent per retained EssentialAsset; W2 = at least 1 RiskSourceObjectivePair is_retained; W3 = at least 1 StrategicScenario is_retained; W4 = at least 1 OperationalScenario per retained StrategicScenario; W5 = EbiosSummary status validated + at least 1 PACSMeasure. |
| RE-05 | A [`FearedEvent`](feared-event.md) is unique per `(essential_asset, dic_criterion)` pair within a given [`SecurityBaseline`](security-baseline.md). |
| RE-06 | [`RiskSource.threat_level`](risk-source.md) is computed in `save()` via ANSSI grid A (§2.8). The snapshot of the scale is kept in `criteria_snapshot`. |
| RE-07 | [`EcosystemStakeholder.threat_level`](ecosystem-stakeholder.md) and `threat_zone` are computed in `save()` via the formula (dependency x penetration) / (maturity x trust) and the configurable thresholds (§2.6). |
| RE-08 | Only SR/OV pairs with `is_retained = true` may be referenced by a [`StrategicScenario`](strategic-scenario.md). |
| RE-09 | Only [`StrategicScenario`](strategic-scenario.md) with `is_retained = true` may be broken down into an [`OperationalScenario`](operational-scenario.md). |
| RE-10 | [`OperationalScenario.gravity_level`](operational-scenario.md) inherits by default from `strategic_scenario.gravity_level`. Any change must fill in `gravity_override_justification` and sets `gravity_inherited` to false. |
| RE-11 | Consolidating an [`OperationalScenario`](operational-scenario.md) into a [`Risk`](../risk.md) is the preferred operation. Consolidating a [`StrategicScenario`](strategic-scenario.md) is possible for scenarios that are not broken down into operational ones. |
| RE-12 | Consolidation creates a [`Risk`](../risk.md) with `risk_source = ebios_operational_scenario` (or `ebios_strategic_scenario`), pre-fills the fields (severity, likelihood via the V1-V4 mapping, assets, DIC) and establishes the bidirectional link `consolidated_risk_id`. |
| RE-13 | An [`AttackTechnique`](attack-technique.md) must reference either a [`MitreAttackTechnique`](mitre-attack-technique.md) (recommended) or a `custom_name`. If MITRE is referenced, the `mitre_version` field of the parent [`OperationalScenario`](operational-scenario.md) must be frozen for traceability. |
| RE-14 | Moving from a strategic cycle to an operational cycle creates new [`EbiosWorkshopProgress`](workshop-progress.md) (W4 and W5) with an incremented `iteration_number`, without touching the W1-W3 entities of the current strategic cycle. |
| RE-15 | Deleting an EBIOS entity is refused if it is referenced by an entity of a higher workshop (e.g. an SR used in a retained SR/OV pair). Deactivate via `is_retained = false` instead. |
| RE-16 | Final validation (W5) locks all EBIOS entities of the assessment as read-only. A new iteration is required to make changes. |
| RE-17 | Any change to an entity with a computed field triggers automatic recomputation on save() and increments the simple_history version. |
| RE-18 | A [`PACSMeasure`](pacs-measure.md) with a `target_date` in the past and `status not in [completed, cancelled]` automatically moves to `overdue` (daily scheduled task). |
| RE-19 | Any change to the [`RiskCriteria.ebios_threat_grid`](../risk-criteria.md) or `ebios_ecosystem_thresholds` scale offers to recompute all EBIOS entities of the associated assessment (manual action, never automatic, to preserve history). |

---

## 6. REST API specifications

Base URL: `/api/v1/risks/ebios/`. All routes inherit the pagination, filtering, sorting and authentication defined for the Risks module (see [../README.md](../README.md#6-rest-api-specifications)).

### 6.1 Workshop 0 - Study framework and progress

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/study-frameworks` | List study frameworks (filter `?assessment_id=`) |
| `POST` | `/study-frameworks` | Create (1 per assessment) |
| `GET` | `/study-frameworks/{id}` | Detail |
| `PUT` / `PATCH` | `/study-frameworks/{id}` | Update |
| `POST` | `/study-frameworks/{id}/validate` | Validate the framework |
| `GET` | `/workshops` | List EbiosWorkshopProgress (filter `?assessment_id=`) |
| `GET` | `/workshops/{id}` | Detail |
| `PATCH` | `/workshops/{id}` | Update status/notes |
| `POST` | `/workshops/{id}/start` | Start the workshop |
| `POST` | `/workshops/{id}/validate` | Validate the workshop (with deliverable checks) |
| `POST` | `/workshops/{id}/reject` | Reject the workshop (with reason) |
| `POST` | `/workshops/{id}/iterate` | Start a new iteration |

### 6.2 Workshop 1 - Security baseline

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/baselines` | List SecurityBaseline |
| `POST` | `/baselines` | Create (1 per assessment) |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/baselines/{id}` | CRUD |
| `GET` | `/baselines/{id}/feared-events` | List the feared events of the baseline |
| `POST` | `/baselines/{id}/feared-events` | Create a feared event |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/feared-events/{id}` | CRUD feared event |
| `GET` | `/baselines/{id}/gaps` | List the gaps |
| `POST` | `/baselines/{id}/gaps` | Create a gap |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/baseline-gaps/{id}` | CRUD gap |
| `POST` | `/baselines/{id}/import-from-context` | Import retained EssentialAsset, SupportAsset, Activity, Stakeholder from the scope |

### 6.3 Workshop 2 - Risk sources

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/risk-sources` | List the SR (filters `?assessment_id`, `?category`, `?is_retained`, `?threat_level_min`) |
| `POST` | `/risk-sources` | Create an SR |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/risk-sources/{id}` | CRUD |
| `POST` | `/risk-sources/{id}/approve` | Approve |
| `GET` | `/risk-sources/catalog` | ANSSI catalogue of SR types |
| `POST` | `/risk-sources/import-catalog` | Import from catalogue |
| `GET` | `/targeted-objectives` | List the OV |
| `POST` | `/risk-sources/{id}/objectives` | Create an OV for an SR |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/targeted-objectives/{id}` | CRUD OV |
| `GET` | `/sr-ov-pairs` | List the SR/OV pairs (filters) |
| `POST` | `/sr-ov-pairs` | Create a pair |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/sr-ov-pairs/{id}` | CRUD |
| `POST` | `/sr-ov-pairs/{id}/approve` | Approve |
| `GET` | `/assessments/{id}/sr-ov-matrix` | SR x OV cross matrix with relevance |

### 6.4 Workshop 3 - Ecosystem and strategic scenarios

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/ecosystem-stakeholders` | List the ecosystem stakeholders (filters `?assessment_id`, `?threat_zone`) |
| `POST` | `/ecosystem-stakeholders` | Create a stakeholder |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/ecosystem-stakeholders/{id}` | CRUD |
| `POST` | `/ecosystem-stakeholders/{id}/approve` | Approve |
| `POST` | `/ecosystem-stakeholders/import-suppliers` | Import from Module 2 Suppliers |
| `GET` | `/assessments/{id}/ecosystem-graph` | Ecosystem graph (nodes + edges + zones) |
| `GET` | `/strategic-scenarios` | List (filters `?assessment_id`, `?is_retained`, `?risk_level_min`) |
| `POST` | `/strategic-scenarios` | Create |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/strategic-scenarios/{id}` | CRUD |
| `POST` | `/strategic-scenarios/{id}/approve` | Approve |
| `POST` | `/strategic-scenarios/{id}/consolidate` | Consolidate into a Risk |
| `GET` | `/strategic-scenarios/{id}/attack-path` | List the steps |
| `POST` | `/strategic-scenarios/{id}/attack-path` | Add a step |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/attack-path-steps/{id}` | CRUD step |
| `PATCH` | `/strategic-scenarios/{id}/attack-path/reorder` | Reorder |

### 6.5 Workshop 4 - Operational scenarios

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/operational-scenarios` | List (filters `?strategic_scenario_id`, `?likelihood_v`, `?risk_level_min`) |
| `POST` | `/operational-scenarios` | Create |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/operational-scenarios/{id}` | CRUD |
| `POST` | `/operational-scenarios/{id}/approve` | Approve |
| `POST` | `/operational-scenarios/{id}/consolidate` | Consolidate into a Risk |
| `GET` | `/operational-scenarios/{id}/techniques` | List the techniques |
| `POST` | `/operational-scenarios/{id}/techniques` | Add a technique |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/attack-techniques/{id}` | CRUD |
| `PATCH` | `/operational-scenarios/{id}/techniques/reorder` | Reorder |
| `GET` | `/mitre-attack/techniques` | MITRE catalogue (search `?search`, `?tactic`) |
| `GET` | `/mitre-attack/techniques/{mitre_id}` | MITRE technique detail |
| `GET` | `/assessments/{id}/mitre-heatmap` | MITRE heatmap of the techniques used |

### 6.6 Workshop 5 - Summary and PACS

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/summaries` | List EbiosSummary |
| `POST` | `/summaries` | Create (1 per assessment) |
| `GET` / `PUT` / `PATCH` | `/summaries/{id}` | CRUD |
| `POST` | `/summaries/{id}/snapshot-mappings` | Capture the before/after snapshots |
| `POST` | `/summaries/{id}/validate` | Validate the summary (executive management) |
| `GET` | `/pacs-measures` | List the PACS measures (filters) |
| `POST` | `/pacs-measures` | Create |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/pacs-measures/{id}` | CRUD |
| `GET` | `/pacs-measures/overdue` | Overdue measures |
| `GET` | `/assessments/{id}/risk-mapping` | Before/after mapping (matrices side by side) |

### 6.7 Cross-cutting endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/assessments/{id}/ebios/progress` | Progress summary (6 workshops) |
| `GET` | `/assessments/{id}/ebios/export` | Export full report as DOCX/PDF |
| `GET` | `/assessments/{id}/ebios/export-pacs` | Export PACS as DOCX/XLSX |
| `GET` | `/assessments/{id}/ebios/audit-trail` | EBIOS audit trail of the assessment |
| `POST` | `/assessments/{id}/ebios/recompute-scores` | Recompute EBIOS scores following a scale change |

---

## 7. MCP specifications

All EBIOS entities are exposed via MCP in `mcp/tools.py` according to the existing pattern (`@require_perm("risks.ebios_xxx.action")` + `_list_handler`, `_get_handler`, `_create_handler`, `_update_handler` helpers).

### 7.1 Standard CRUD tools (per entity)

For each of the 15 EBIOS entities (StudyFramework, EbiosWorkshopProgress, SecurityBaseline, FearedEvent, BaselineGap, RiskSource, TargetedObjective, RiskSourceObjectivePair, EcosystemStakeholder, StrategicScenario, AttackPathStep, OperationalScenario, AttackTechnique, EbiosSummary, PACSMeasure):

- `list_{entity}` (exposed filters)
- `get_{entity}` (by id or reference)
- `create_{entity}`
- `update_{entity}`
- `delete_{entity}`
- `approve_{entity}` (for approvable entities: SecurityBaseline, RiskSource, RiskSourceObjectivePair, EcosystemStakeholder, StrategicScenario, OperationalScenario, EbiosSummary)
- `batch_create_{entity}` (M4 keeps this pattern)

Total: around 90 to 100 CRUD tools.

### 7.2 EBIOS-specific tools

| Tool | Permission | Description |
|---|---|---|
| `transition_workshop` | `risks.ebios_assessment.update` | Change the status of an EbiosWorkshopProgress (start, validate, reject, iterate) |
| `validate_workshop` | `risks.ebios_assessment.validate` | Validate a workshop with mandatory deliverable checks |
| `consolidate_strategic_to_risk` | `risks.risk.create` | Consolidate a StrategicScenario into a register Risk |
| `consolidate_operational_to_risk` | `risks.risk.create` | Consolidate an OperationalScenario into a register Risk |
| `compute_risk_source_threat_level` | `risks.ebios_risk_source.read` | Recompute the threat level of an SR |
| `compute_stakeholder_threat_level` | `risks.ebios_ecosystem.read` | Recompute the threat level of an ecosystem stakeholder |
| `recompute_assessment_scores` | `risks.ebios_assessment.update` | Recompute all scores of an assessment following a scale change |
| `list_mitre_techniques` | `risks.ebios_operational.read` | Search the MITRE catalogue |
| `get_mitre_technique` | `risks.ebios_operational.read` | Detail of a MITRE technique |
| `get_ecosystem_graph` | `risks.ebios_ecosystem.read` | Ecosystem graph (nodes, edges, zones) |
| `get_sr_ov_matrix` | `risks.ebios_risk_source.read` | SR x OV matrix |
| `get_mitre_heatmap` | `risks.ebios_operational.read` | MITRE heatmap of the techniques used |
| `get_assessment_progress` | `risks.ebios_assessment.read` | Progress summary of the 6 workshops |
| `generate_ebios_report` | `risks.export` | Generate the full EBIOS DOCX report |
| `generate_pacs_report` | `risks.export` | Generate the PACS DOCX/XLSX |
| `import_risk_source_catalog` | `risks.ebios_risk_source.create` | Import the ANSSI catalogue of SR types |
| `import_ecosystem_from_suppliers` | `risks.ebios_ecosystem.create` | Import Suppliers as candidate stakeholders |

---

## 8. User interface specifications

### 8.1 Navigation

The EBIOS RM sub-module is accessible from the detail page of a [`RiskAssessment`](../risk-assessment.md) whose `methodology = ebios_rm`. The detail page displays in a top banner:
- The **5-workshop stepper** (W1 to W5, with a cancelled branch on rejection).
- The **strategic vs operational cycle** indicator (badge).
- The "New iteration" button (CISO/Admin).

An entry in the Risks module side menu offers "EBIOS RM", which displays the table of EBIOS assessments (filter `methodology=ebios_rm` on the M4 list).

### 8.2 The 5-workshop stepper

Reproduces the pattern of [compliance/templates/compliance/assessment_detail.html](compliance/templates/compliance/assessment_detail.html):

- 5 horizontal pills (W1 to W5) with connectors.
- A 6th pill (W0) upstream, smaller and greyed (prerequisite).
- State `validated` -> green check. State `in_progress` -> accent pill. State `under_review` -> orange pill. State `not_started` -> dashed grey pill. State `rejected` -> secondary branch downward.
- Clicking a pill -> navigation to the view of the corresponding workshop.
- The server-side context is built by the `EbiosWorkshopMixin.get_workshop_steps(assessment)` method, which returns the ordered list of the 6 progress records with their state.

### 8.3 View W0 - Study framework

2-column layout:
- **Main column (col-lg-8)**: StudyFramework form (description, scopes, assumptions, constraints, expected deliverables).
- **Sidebar (col-lg-4)**: status, internal participants (multi-select User), external participants (mini formset), applicable frameworks (multi-select Framework), budget envelope, dates, "Validate the framework" button.

### 8.4 View W1 - Security baseline

2-column layout:
- **Main column**:
  - "Business scope" card: recap of the retained Activity and EssentialAsset (read-only, with a link to Module 1/2 for editing).
  - "Feared events" card: Essential asset x DIC x Description x Severity table with inline actions. Add button. Compact mobile view (stacked cards).
  - "Gaps against the baseline" card: Framework x Description x Severity x Status table with a Requirement link and inline actions.
- **Sidebar**:
  - Baseline frameworks (multi-select Framework).
  - Workshop status (W1 stepper).
  - "Validate workshop 1" button (CISO).
  - "Import from Context/Assets" button, which pre-fills the business values and support assets.

### 8.5 View W2 - Risk sources and targeted objectives

Three sub-tabs:

1. **Risk sources**: table with columns Reference, Name, Category, Motivation, Resources, Activity, Threat level (V1-V4 badge), Retained. Filters. Add form in a modal. "Import ANSSI catalogue" button.
2. **Targeted objectives**: grouped by SR (accordion). For each SR, a table of OV with targeted essential assets and feared events.
3. **SR x OV matrix**: cross grid. Rows = retained SR, columns = OV. Cell = relevance (low/medium/high/critical) with a colour code. An empty cell is clickable to create the pair. A filled cell is clickable to edit or exclude (`is_retained`).

### 8.6 View W3 - Ecosystem and strategic scenarios

Two sub-tabs:

1. **Ecosystem mapping**:
   - Interactive graph (vis.js or D3.js) with 3 visual zones (green/orange/red).
   - Nodes = EcosystemStakeholder, size proportional to `dependency`, colour according to `threat_zone`.
   - Edges = relationships (aggregated M2M `accessible_support_assets`).
   - Detail panel on the right (selecting a node -> editing the ANSSI dimensions: dependency, penetration, maturity, trust; live recomputation of `threat_level`).
   - Legend of the zone thresholds.
   - Toggle to a tabular view.

2. **Strategic scenarios**:
   - List with columns Reference, Name, SR/OV pair, Severity, Likelihood, Level, Retained, Consolidated risk.
   - Detail: attack-path editor in visual mode (horizontal timeline of steps with the involved stakeholder at each step, drag-and-drop to reorder).
   - "Consolidate into a risk" button.

### 8.7 View W4 - Operational scenarios

Two sub-tabs:

1. **Operational scenarios**:
   - List grouped by parent strategic scenario (accordion).
   - Columns: Reference, Name, Support assets, Likelihood V1-V4, Severity ("inherited"/"adjusted" badge), Level, Consolidated risk.
   - Detail: attack-sequence editor (chained techniques), MITRE ATT&CK autocompletion on input (search by tactic or ID).
   - "Consolidate into a risk" button.

2. **MITRE ATT&CK heatmap**:
   - Matrix of the 14 tactics x techniques, colour-coded by the number of operational scenarios using each technique.
   - Filter by parent strategic scenario.
   - PNG/PDF export.

### 8.8 View W5 - Summary and PACS

2-column layout:
- **Main column**:
  - "Before/after mapping" card: two risk matrices (initial vs residual) side by side with a heatmap.
  - "Residual strategy" card: editor for `residual_risk_strategy`.
  - "PACS" card: structured list of PACSMeasure (kanban by status or sortable table).
  - For each measure: reference, description, type, due date, owner, status, cost, expected gain, RiskTreatmentPlan link.
- **Sidebar**:
  - W5 workshop status (stepper).
  - Next cycles (strategic and operational dates).
  - Validation by executive management.
  - Export full report as DOCX/PDF.
  - Export PACS as DOCX/XLSX.

### 8.9 Mobile adaptations

- Stepper: switches to vertical mode on screens < 768px, with horizontal scroll for the pills.
- Matrices and graphs: switch to a tabular view with an explicit toggle.
- Multi-select: use of the project's existing `select2-mobile` component.
- Sticky bars: the primary action (Validate/Approve) sticks to the bottom of the screen on mobile.
- Formsets: vertical stacking with touch affordances.

### 8.10 Light/dark themes

All EBIOS RM-specific components (ecosystem graph, MITRE heatmap, before/after matrices) use the theme CSS variables (`--color-bg`, `--color-text`, `--color-accent`, `--color-success`, `--color-warning`, `--color-danger`). Mandatory checks in dark theme:
- Readability of the labels on the graph (light text on dark nodes).
- Sufficient contrast of the colour zones (green/orange/red in the dark version).
- MITRE heatmap: palette adapted so as not to saturate in dark mode.

---

## 9. Permissions and internationalisation

### 9.1 PERMISSION_REGISTRY

Added in `accounts/constants.py` under the `risks` key:

```python
PERMISSION_REGISTRY["risks"].update({
    "ebios_assessment": {
        "actions": ["read", "update", "validate"],
        "label": _("EBIOS RM assessment pilotage"),
    },
    "ebios_baseline": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM security baseline (workshop 1)"),
    },
    "ebios_risk_source": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM risk sources and objectives (workshop 2)"),
    },
    "ebios_ecosystem": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM ecosystem stakeholders (workshop 3)"),
    },
    "ebios_strategic": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM strategic scenarios (workshop 3)"),
    },
    "ebios_operational": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM operational scenarios (workshop 4)"),
    },
    "ebios_summary": {
        "actions": ["create", "read", "update", "delete", "approve"],
        "label": _("EBIOS RM summary and PACS (workshop 5)"),
    },
})
```

Generated codes: `risks.ebios_assessment.read`, `risks.ebios_baseline.create`, etc. (around 35 new permissions).

### 9.2 System group mappings

| Group | EBIOS permissions granted |
|---|---|
| Super Admin | all |
| Admin | all except `*.delete` |
| CISO / DPO | `*.read`, `*.create`, `*.update`, `*.approve`, `ebios_assessment.validate` |
| Auditor | `*.read` only |
| Contributor | `*.read`, `*.create`, `*.update` (excluding `approve` and `validate`) |
| Reader | `*.read` only |

To be added in the data migration `accounts/migrations/00xx_add_ebios_permissions.py`.

### 9.3 Internationalisation (FR)

All UI strings are wrapped in `_()`, `gettext_lazy()` or `{% trans %}`. The FR translations must be added in `locale/fr/LC_MESSAGES/django.po`, avoiding duplicate `msgid` entries (use `pgettext_lazy` with a context in case of conflict).

FR keys to verify/add (non-exhaustive list):

| msgid (EN) | msgstr (FR) | Context if needed |
|---|---|---|
| Workshop 1 | Atelier 1 - Socle de sécurité | already present |
| Workshop 2 | Atelier 2 - Sources de risque | already present |
| Workshop 3 | Atelier 3 - Scénarios stratégiques | already present |
| Workshop 4 | Atelier 4 - Scénarios opérationnels | already present |
| Workshop 5 | Atelier 5 - Traitement du risque | already present |
| Study framework | Cadre de l'étude | - |
| Security baseline | Socle de sécurité | ebios |
| Feared event | Événement redouté | - |
| Baseline gap | Écart au socle | - |
| Risk source | Source de risque | - |
| Targeted objective | Objectif visé | - |
| Risk source / objective pair | Couple source de risque / objectif visé | - |
| Ecosystem stakeholder | Partie prenante de l'écosystème | - |
| Threat level | Niveau de menace | - |
| Threat zone | Zone de menace | - |
| Control zone | Zone de contrôle | - |
| Monitoring zone | Zone de surveillance | - |
| Danger zone | Zone de danger | - |
| Strategic scenario | Scénario stratégique | - |
| Attack path step | Étape du chemin d'attaque | - |
| Operational scenario | Scénario opérationnel | - |
| Attack technique | Technique d'attaque | - |
| EBIOS summary | Synthèse EBIOS RM | - |
| PACS measure | Mesure du PACS | - |
| Continuous security improvement plan | Plan d'amélioration continue de la sécurité | - |
| Strategic cycle | Cycle stratégique | - |
| Operational cycle | Cycle opérationnel | - |
| MITRE ATT&CK heatmap | Cartographie MITRE ATT&CK | - |
| Minimal (V1) | Minimal (V1) | likelihood |
| Significant (V2) | Significatif (V2) | likelihood |
| Strong (V3) | Fort (V3) | likelihood |
| Maximal (V4) | Maximal (V4) | likelihood |

---

## 10. Tests

### 10.1 Mandatory test matrix

| Domain | Mandatory tests |
|---|---|
| ANSSI computations | SR grid A (4x4x3 combinations) returns the expected V1-V4. Ecosystem formula (dependency x penetration) / (maturity x trust) returns the expected threat_zone over 12 boundary cases. Mapping likelihood_v -> integer (V1=1, V4=4) for the risk_level matrix. |
| Validation gates | W1 cannot be validated without a SecurityBaseline and at least 1 FearedEvent. W2 cannot be validated without 1 ESOV is_retained. W3 without 1 ESTS is_retained. W4 without 1 EOPS per retained ESTS. W5 without a validated EbiosSummary and 1 PACSMeasure. |
| Iterative cycle | Creating a new operational iteration does not touch the strategic entities. iteration_number increments correctly. |
| Severity inheritance | OperationalScenario inherits by default. A change triggers gravity_inherited switching to false and requires a justification. |
| is_retained filters | A non-retained SR -> OV unusable. A non-retained ESOV -> cannot be referenced by an ESTS. A non-retained ESTS -> cannot be broken down into an EOPS. |
| Risk consolidation | EOPS consolidation creates a Risk with pre-filled fields. Bidirectional link consolidated. risk_source = ebios_operational_scenario. |
| MITRE catalog | Seed via fixture loads >500 techniques. Search by tactic works. Sub-techniques attached to the parent. |
| Permissions | Access denied for non-granted codenames. CISO can validate, Auditor cannot. |
| Criteria snapshot | A scale change does not automatically recompute existing entities. The manual `recompute_assessment_scores` action recomputes while preserving the simple_history history. |

### 10.2 factory-boy factories

Additions in `risks/tests/factories.py` (15 factories): `StudyFrameworkFactory`, `EbiosWorkshopProgressFactory`, `SecurityBaselineFactory`, `FearedEventFactory`, `BaselineGapFactory`, `RiskSourceFactory`, `TargetedObjectiveFactory`, `RiskSourceObjectivePairFactory`, `EcosystemStakeholderFactory`, `StrategicScenarioFactory`, `AttackPathStepFactory`, `OperationalScenarioFactory`, `AttackTechniqueFactory`, `MitreAttackTechniqueFactory`, `EbiosSummaryFactory`, `PACSMeasureFactory`.

Each factory guarantees a valid EBIOS assessment as a dependency (sub_factory or trait).

### 10.3 Test organisation

| File | Content |
|---|---|
| `risks/tests/test_ebios_models.py` | Tests of `save()` computations, ANSSI formulas, criteria snapshots, uniqueness constraints. |
| `risks/tests/test_ebios_views.py` | Workflow transitions, stepper views, UI rendering, permission access. |
| `risks/tests/test_ebios_api.py` | CRUD endpoints, custom actions (validate, consolidate, recompute), filters. |
| `risks/tests/test_ebios_mcp.py` | MCP CRUD tools + specific ones. |
| `risks/tests/test_ebios_workflow.py` | End-to-end scenarios (create assessment -> validate the 6 workshops -> export report). |
| `risks/tests/test_ebios_mitre.py` | MITRE catalogue (seed, search, heatmap). |

Target coverage: >= 85% on the `risks/models/ebios/`, `risks/api/ebios/`, `risks/views/ebios/` modules.

---

## 11. Migration and seed data

### 11.1 Migration order

1. `risks/migrations/00NN_ebios_study_framework_workshop.py`: StudyFramework + EbiosWorkshopProgress.
2. `risks/migrations/00NN_ebios_baseline.py`: SecurityBaseline + FearedEvent + BaselineGap.
3. `risks/migrations/00NN_ebios_risk_sources.py`: RiskSource + TargetedObjective + RiskSourceObjectivePair.
4. `risks/migrations/00NN_ebios_ecosystem.py`: EcosystemStakeholder.
5. `risks/migrations/00NN_ebios_strategic.py`: StrategicScenario + AttackPathStep.
6. `risks/migrations/00NN_mitre_catalog.py`: MitreAttackTechnique.
7. `risks/migrations/00NN_ebios_operational.py`: OperationalScenario + AttackTechnique.
8. `risks/migrations/00NN_ebios_summary_pacs.py`: EbiosSummary + PACSMeasure.
9. `risks/migrations/00NN_risk_link_ebios_scenarios.py`: adds `consolidated_risk_id` (reverse) and completes the `Risk.source_entity_type` choices.

### 11.2 MITRE ATT&CK data migration

`risks/migrations/00NN_seed_mitre_attack.py`: loads `risks/fixtures/mitre_attack_v15.json` (full Enterprise Matrix, around 600+ techniques, ~14 tactics). Offline-compatible (no API call). Updated via the management command:

```
python manage.py refresh_mitre_attack --version 15.1
```

The command takes the local JSON file as an argument (downloaded manually from the official MITRE/CTI repo on GitHub) and updates the catalogue while preserving the existing FK.

### 11.3 Permissions data migration

`accounts/migrations/00NN_add_ebios_permissions.py`:
- Creates the 35 `risks.ebios_*.*` permissions from the extended registry.
- Assigns the permissions to the system groups (see §9.2).

### 11.4 Risk source catalogue data migration

`risks/migrations/00NN_seed_ebios_risk_source_catalog.py`: adds an ANSSI catalogue of SR types with `is_from_catalog = true` (cybercriminal, State, hacktivist, malicious employee, negligent employee, competitor, service provider, etc.). These entries serve as a copy pool when creating an EBIOS assessment (the "Import catalogue" action).

### 11.5 Historical compatibility

For existing [`RiskAssessment`](../risk-assessment.md) with `methodology = ebios_rm` (only the shell for now):
- Data migration `00NN_backfill_ebios_workshops.py`: creates, for each existing ebios_rm assessment, 1 StudyFramework status draft + 6 EbiosWorkshopProgress not_started.
- No migration of prior EBIOS entities (there are none).

---

## 12. Appendices

### Appendix A - ANSSI SR threat-level grid (Grid A)

Details of the [`RiskSource.threat_level`](risk-source.md) computation grid (4 motivations x 4 resources x 3 activities = 48 flattened combinations). Reference table (excerpt):

| Motivation | Resources | Activity | Threat level |
|---|---|---|---|
| Low (1) | Limited (1) | Low | V1 |
| Low (1) | Limited (1) | Medium | V1 |
| Low (1) | Limited (1) | High | V2 |
| Moderate (2) | Moderate (2) | Medium | V2 |
| High (3) | Significant (3) | High | V4 |
| Very high (4) | Unlimited (4) | High | V4 |

The full grid is provided in the file `risks/constants/ebios_grids.py` and feeds the computation of `threat_level`. Configurable at the [`RiskCriteria.ebios_threat_grid`](../risk-criteria.md) level.

### Appendix B - ANSSI operational likelihood grid V1-V4 (Grid B)

| Code | EN label | FR label | Assessment criterion |
|---|---|---|---|
| V1 | Minimal | Minimal | Mode of operation unknown or hard to carry out. Expert skills required, bespoke tooling. |
| V2 | Significant | Significatif | Documented mode of operation but requires specific skills. Uncommon tooling. |
| V3 | Strong | Fort | Proven mode of operation, accessible to an intermediate attacker with standard tooling. |
| V4 | Maximal | Maximal | Automated mode of operation, turnkey kits, or trivial. No particular skills required. |

### Appendix C - Ecosystem threat_zone thresholds

| Zone | `threat_level` range | UI colour | ANSSI semantics |
|---|---|---|---|
| Control (control) | `threat_level < 0.5` | Green | Stakeholder under control, low residual exposure. |
| Monitoring (monitoring) | `0.5 <= threat_level < 1.5` | Orange | Stakeholder to be monitored. Reduction measures recommended. |
| Danger (danger) | `threat_level >= 1.5` | Red | Critical stakeholder. Reduction measures mandatory. |

The thresholds are configurable on [`RiskCriteria.ebios_ecosystem_thresholds`](../risk-criteria.md) (JSON: `{"control": 0.5, "monitoring": 1.5}`).

### Appendix D - Examples of typical ANSSI scenarios

1. **Targeted ransomware**:
   - SR: cybercriminal (lucrative motivation, significant resources, high activity -> V4).
   - OV: financial gain (lucrative).
   - SR/OV pair: critical.
   - Ecosystem stakeholder: MSP (monitoring zone).
   - Strategic path: MSP -> remote access -> lateral movement -> encryption.
   - Operational scenario: phishing (T1566.001) -> initial access (T1078) -> lateral movement (T1021) -> encryption (T1486).
   - Operational likelihood: V3.

2. **Supply chain compromise**:
   - SR: State (strategic motivation, unlimited resources, high activity -> V4).
   - OV: espionage (strategic).
   - Ecosystem stakeholder: critical software vendor (danger zone).
   - Strategic path: vendor -> poisoned update -> persistence -> exfiltration.
   - Operational scenario: T1195.002 -> T1543 -> T1041.
   - Operational likelihood: V2.

3. **Insider committing fraud**:
   - SR: internal employee (revenge motivation, moderate resources, medium activity -> V2).
   - OV: revenge.
   - Ecosystem stakeholder: none (internal).
   - Strategic path: privilege abuse -> data manipulation -> concealment.
   - Operational scenario: T1078.003 -> T1565 -> T1070.
   - Operational likelihood: V3.

### Appendix E - ANSSI glossary

| Term | Definition |
|---|---|
| SR | Risk Source. Element at the origin of the risk. |
| OV | Targeted Objective. Goal pursued by the SR. |
| ER | Feared Event. Breach of a DIC criterion on a business value. |
| PACS | Continuous Security Improvement Plan. Deliverable of workshop 5. |
| DIC | Availability, Integrity, Confidentiality. Primary security criteria. |
| Business value | Service, activity or information to be protected (Module 1/2 terminology). |
| Support asset | Component that carries the business value (Module 2 terminology). |
| Ecosystem | The set of external stakeholders interacting with the organisation. |
| Security baseline | The set of applicable rules and measures (frameworks, state of the art). |
| Strategic cycle | Long re-assessment of workshops 1-3 and 5. |
| Operational cycle | Short re-assessment of workshops 4 and 5. |
| V1 to V4 | ANSSI operational likelihood scale. |

### Appendix F - ANSSI vocabulary <-> code mapping

| ANSSI vocabulary | Code (Django model) | App |
|---|---|---|
| Mission | StudyFramework.mission_statement | risks |
| Study framework | StudyFramework | risks |
| Workshop | EbiosWorkshopProgress | risks |
| Business value | Activity / EssentialAsset | context / assets |
| Support asset | SupportAsset | assets |
| Security baseline | SecurityBaseline | risks |
| Feared event | FearedEvent | risks |
| Baseline gap | BaselineGap | risks |
| Risk source (SR) | RiskSource | risks |
| Targeted objective (OV) | TargetedObjective | risks |
| SR/OV pair | RiskSourceObjectivePair | risks |
| Ecosystem stakeholder | EcosystemStakeholder | risks |
| Threat level | EcosystemStakeholder.threat_level | risks |
| Zone (control/monitoring/danger) | EcosystemStakeholder.threat_zone | risks |
| Strategic scenario | StrategicScenario | risks |
| Attack path | StrategicScenario.attack_path (via AttackPathStep) | risks |
| Step | AttackPathStep | risks |
| Operational scenario | OperationalScenario | risks |
| Mode of operation | OperationalScenario.attack_techniques (via AttackTechnique) | risks |
| MITRE technique | MitreAttackTechnique | risks |
| Likelihood V1-V4 | OperationalScenario.likelihood_v | risks |
| Severity | OperationalScenario.gravity_level / FearedEvent.gravity_level | risks |
| Summary | EbiosSummary | risks |
| PACS | EbiosSummary.pacs_summary + PACSMeasure | risks |
| Residual strategy | EbiosSummary.residual_risk_strategy | risks |
| Residual risk | Risk.residual_risk_level | risks |

### Appendix G - Note on the replacement of M4 §4

Section 4 of document M4 ("Data model - EBIOS RM sub-module") is obsolete. This M4bis spec replaces it in full. Future implementations must refer to this document. The cross-references to M4 §2 (common foundation), §5 (rules), §6 (API), §7 (UI), §10 (export) remain valid for the non-EBIOS parts.

---

*End of the specifications for Module 4 bis - EBIOS Risk Manager (ANSSI v1.5).*

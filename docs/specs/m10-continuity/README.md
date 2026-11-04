# Module 10 : Business continuity

## Functional and technical specification

The register of the organisation's **business continuity and ICT readiness** (ISO/IEC 27001:2022 A.5.29 information security during disruption, A.5.30 ICT readiness for business continuity, A.8.13 / A.8.14 backup and redundancy; ISO 22301 clause 8.2 to 8.5; NIS2 article 21.2 c; DORA articles 11 and 12). It answers the questions an auditor asks : *which activities are critical and how fast must they come back, which plan brings them back, was the plan exercised and did it meet its objectives, and what happened when it was really used.*

**Status : proposed for v0.37.0.**

## Entities

| Entity | Class | Reference prefix | Lifecycle |
| --- | --- | --- | --- |
| [BusinessImpactAnalysis](business-impact-analysis.md) | `continuity.models.bia.BusinessImpactAnalysis` | `BIAN` | `business_impact_analysis` |
| [BiaEntry](bia-entry.md) | `continuity.models.bia.BiaEntry` | none | none (child of the analysis) |
| [ContinuityPlan](continuity-plan.md) | `continuity.models.plan.ContinuityPlan` | `BCPL` | `continuity_plan` |
| [RecoveryStep](recovery-step.md) | `continuity.models.plan.RecoveryStep` | none | none (child of the plan) |
| [ContinuityExercise](continuity-exercise.md) | `continuity.models.exercise.ContinuityExercise` | `BCEX` | `continuity_exercise` |
| [PlanActivation](plan-activation.md) | `continuity.models.activation.PlanActivation` | `BCAC` | `plan_activation` |
| [ActivationLogEntry](plan-activation.md#activationlogentry) | `continuity.models.activation.ActivationLogEntry` | none | none (write-once record) |

---

## 1. Overview

### 1.1 Purpose

Cairn knows the organisation's activities (`context.Activity`), its essential and support assets and their dependencies, its sites and suppliers, and its incidents. Essential assets carry MTD / RTO / RPO, but as free text nobody validated, with no impact analysis behind them and no plan, exercise or activation using them.

This module adds the continuity cycle :

- a **business impact analysis** (BIA) assesses, for each critical activity or essential asset, the impact of a disruption over time (financial, operational, legal and regulatory, reputational, safety), and sets its **MTD**, **RTO**, **RPO** and minimum service level, with its dependencies; it is reviewed and validated as a whole, and its validated values become the reference figures of the assets;
- a **continuity plan** (business continuity, disaster recovery, crisis management, ICT continuity) covers activities, assets and sites with a strategy, activation criteria and ordered **recovery steps** owned by roles, each with a target time; it is approved before use and revised through its lifecycle;
- **exercises** test a plan (tabletop, walkthrough, simulation, technical recovery, full interruption), record the achieved recovery time against the objective, the outcome and the lessons learned, and can raise a finding;
- a plan **activation**, possibly from a major incident, opens a timestamped, write-once **activation log** until the plan is stood down.

### 1.2 Functional scope

| Area | In v0.37.0 |
| --- | --- |
| BIA with entries per activity or essential asset : impacts per category and time window, MTD / RTO / RPO in hours, minimum service level, dependencies (support assets, suppliers, sites), validation | yes |
| Validated BIA values written to the essential assets' MTD / RTO / RPO, as a recorded change | yes |
| Continuity plans with type, coverage, strategy, activation criteria, ordered recovery steps owned by roles, linked formal document, exercise frequency | yes |
| Feasibility check : a plan whose recovery time exceeds a covered RTO is flagged | yes |
| Exercises with type, scenario, participants, achieved recovery time, outcome, lessons learned; raising a finding | yes |
| Plan activation from a plan or from an incident, write-once activation log, stand-down | yes |
| REST API, MCP tools, global search, calendar, dashboard widget, kanban, predefined indicators, help banners, demo seed | yes |
| Crisis communication tooling (mass notification, call trees) | no (see §11) |
| Per-step exercise results and timings | no (see §11) |
| Automatic import of BIA from a questionnaire campaign | no (see §11) |

### 1.3 Dependencies on other modules

| Target module | Nature of the dependency |
| --- | --- |
| Context | `ScopedModel`, `Scope`, `Activity` (BIA entries, plan coverage), `Role` (recovery step owners), `Site`. |
| Assets | `EssentialAsset` (BIA entries, plan coverage, MTD / RTO / RPO written on validation), `SupportAsset` and `Supplier` (dependencies, plan coverage). |
| Documents | `Policy` (of type `plan`) through `ContinuityPlan.document` : the formal, approved plan document. |
| Incidents | `Incident` through `PlanActivation.incident`; the incident page lists and starts activations. |
| Compliance | `Requirement` through `ContinuityPlan.requirements`; `Finding.continuity_exercise` (FK `SET_NULL`) and `FindingSource.CONTINUITY_EXERCISE`. |
| Controls | `Control.continuity_plans` is not added; a control such as *"Daily off-site backups"* links to the support assets the plan covers. |

---

## 2. Business rules : the RG-BCM register

### 2.1 Business impact analysis

| ID | Rule |
| --- | --- |
| RG-BCM-01 | A [BIA](business-impact-analysis.md) holds one [entry](bia-entry.md) per assessed activity or essential asset; an entry targets **exactly one** of them, and the same target appears at most once per analysis. |
| RG-BCM-02 | Impacts are scored 1 (negligible) to 4 (critical) for each category (`financial`, `operational`, `legal`, `reputational`, `safety`) at each time window of the analysis (default `4h`, `24h`, `72h`, `1w`, `1m`). A score never decreases as the window grows (an impact gets worse with time, never better); the form and the API refuse a decreasing series. |
| RG-BCM-03 | MTD, RTO and RPO are stored as **hours** (decimal, >= 0). `RTO <= MTD` always; an entry without MTD is incomplete. The *suggested MTD* is the start of the first window where any category reaches 3 (shown, never imposed). |
| RG-BCM-04 | Entries are editable only while the analysis is `draft`. Submitting requires at least one entry and every entry complete (MTD, RTO, RPO set). |
| RG-BCM-05 | Validating an analysis (`approve`) writes, for each entry targeting an essential asset, its MTD / RTO / RPO to the asset's existing fields, formatted (`"24 h"`, `"3 days"`), as a recorded save with the change reason *"From BIAN-n"*. Activities carry no such fields; their figures are read from the latest validated analysis. |
| RG-BCM-06 | Validating an analysis archives the previously validated analysis **of the same scopes** (label *Superseded*), in the same transaction : at most one validated BIA per scope set. |

### 2.2 Continuity plans

| ID | Rule |
| --- | --- |
| RG-BCM-07 | A [plan](continuity-plan.md) covers at least one activity, essential asset, support asset or site. Its [recovery steps](recovery-step.md) are ordered; each has a title, an owning role and a target time in minutes from activation. |
| RG-BCM-08 | Steps and coverage are editable only while the plan is `draft`. An `active` plan is changed by **Revise** (`active -> draft`, comment required), then approved again; the history records both. |
| RG-BCM-09 | Approving a plan requires at least one step and its coverage. Approval stamps `approved_by` / `approved_at` and computes `next_exercise_due` = approval date + `exercise_frequency_months` when the plan was never exercised. |
| RG-BCM-10 | **Feasibility** : `recovery_minutes` (the latest step target) is compared with the smallest RTO of the covered targets in the latest validated BIA. A plan whose recovery time exceeds it is flagged *RTO not met* on its page, its list and the dashboard; approval is not refused (the gap is a risk to treat, not a data error). |
| RG-BCM-11 | Retiring a plan requires a comment and is refused while an activation of it is `active`. |

### 2.3 Exercises

| ID | Rule |
| --- | --- |
| RG-BCM-12 | An [exercise](continuity-exercise.md) tests one `active` plan. Its results (conducted on, achieved recovery minutes, outcome, lessons learned) are recorded in `planned`, then frozen by **Record results** (`planned -> conducted`); it is then validated by a holder of `continuity.exercise.approve`. |
| RG-BCM-13 | Validating an exercise stamps the plan's `last_exercised_on` and recomputes `next_exercise_due` = conducted on + `exercise_frequency_months`. A plan is **exercise overdue** when it is active and `next_exercise_due < today` (derived, never a step). |
| RG-BCM-14 | `objective_met` is derived : achieved recovery minutes <= the plan's smallest covered RTO (in minutes), when both are known. |
| RG-BCM-15 | "Raise a finding" on a validated exercise whose outcome is `partial` or `fail` creates one [Finding](../m3-compliance/finding.md) with `source = continuity_exercise`, pre-filled from the lessons learned, as RG-CTL-16 does for control tests. |

### 2.4 Activations

| ID | Rule |
| --- | --- |
| RG-BCM-16 | A plan is **activated** (an [activation](plan-activation.md) created in `active`) by a holder of `continuity.activation.create`, from the plan page or from an incident's page (`incident` then set). The plan must be `active`. Several plans may be active for one incident; one plan has at most one `active` activation. |
| RG-BCM-17 | The **activation log** is write-once : each entry (timestamp, author, text, optional recovery step reached) is appended and never edited or deleted. Activation, each step reached and stand-down append entries automatically. |
| RG-BCM-18 | **Stand down** (`active -> stood_down`, comment required) stamps `stood_down_at` / `stood_down_by` and the achieved recovery minutes (activation to the last step reached); the activation then counts in the plan's history like an exercise for feasibility reading, but does **not** reset `next_exercise_due`. |
| RG-BCM-19 | Activation notifies the plan owner and the assigned users of every step's owning role (`PLAN_ACTIVATED`). |

### 2.5 Integration

| ID | Rule |
| --- | --- |
| RG-BCM-20 | Every report, KPI, calendar feed and picker filters through `reportable()` / `linkable()` / `linkable_or_linked()`. |
| RG-BCM-21 | `BusinessImpactAnalysis` and `ContinuityPlan` are `ScopedModel`s; entries, steps, exercises, activations and log entries inherit through `scope_parent_lookup` (`analysis__scopes`, `plan__scopes`, `activation__plan__scopes`). |
| RG-BCM-22 | The essential asset, activity, support asset, site and incident pages gain a *Continuity* card (latest validated BIA figures, covering plans, activations). |

---

## 3. Lifecycles

Generated from `continuity/constants.py`, registered in `continuity/lifecycles.py`. Exit steps keep the code `archived`.

### 3.1 `business_impact_analysis`

| Code | Label | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | no | no | **yes** | neutral |
| `in_review` | In review | no | no | no | info |
| `validated` | Validated | **yes** | **yes** | no | success |
| `archived` | Superseded | no | no | no | muted |

Submit (`update`), Send back (`approve`, comment), Validate (`approve` : RG-BCM-05 / RG-BCM-06), Archive (`validated -> archived`, `approve`, comment; also the system path of RG-BCM-06).

### 3.2 `continuity_plan`

| Code | Label | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- |
| `draft` | Draft | no | no | **yes** | neutral |
| `in_review` | In review | no | no | no | info |
| `active` | Active | **yes** | **yes** | no | success |
| `archived` | Retired | no | no | no | muted |

Submit (`update`, RG-BCM-09 gate), Send back (`approve`, comment), Approve (`approve`, stamps), Revise (`active -> draft`, `update`, comment), Retire (`active -> archived`, `approve`, comment, RG-BCM-11; `draft -> archived`, `update`, comment).

### 3.3 `continuity_exercise`

| Code | Label | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- |
| `draft` | Planned | no | no | **yes** | neutral |
| `conducted` | Conducted | no | no | no | info |
| `validated` | Validated | **yes** | no | no | success |
| `archived` | Cancelled | no | no | no | muted |

Record results (`draft -> conducted`, `update` : conducted on and outcome required), Send back (`conducted -> draft`, `approve`, comment), Validate (`approve`, RG-BCM-13), Cancel (`draft -> archived`, `update`, comment).

### 3.4 `plan_activation`

| Code | Label | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- |
| `active` | Active (initial) | **yes** | no | no | danger |
| `stood_down` | Stood down | **yes** | no | no | success |
| `archived` | Archived | no | no | no | muted |

Stand down (`active -> stood_down`, `update`, comment), Archive (`stood_down -> archived`, `approve`, comment). There is no draft : an activation exists from the moment it is declared.

---

## 4. Permissions and access control

`PERMISSION_REGISTRY` gains a `continuity` module (`MODULE_LABELS["continuity"] = _("Continuity")`) with four features, each with `create`, `read`, `update`, `delete`, `approve` : `continuity.bia`, `continuity.plan`, `continuity.exercise`, `continuity.activation`. Activation is its own feature so crisis staff can be allowed to activate and log without being able to change plans. System groups follow the platform filters.

---

## 5. API

Base path `/api/v1/continuity/`, house pattern.

| Path | Notes |
| --- | --- |
| `analyses/`, `analyses/{id}/`, `transition/`, `history/` | Filters `status`, `scope_id`, `owner_id` |
| `bia-entries/`, `bia-entries/{id}/` | Filter `analysis_id`; writable only while the analysis is draft |
| `plans/`, `plans/{id}/`, `transition/`, `history/` | Filters `status`, `plan_type`, `scope_id`, `exercise_overdue`, `rto_not_met`, `activity_id`, `essential_asset_id` |
| `recovery-steps/`, `recovery-steps/{id}/` | Filter `plan_id`; writable only while the plan is draft |
| `exercises/`, `exercises/{id}/`, `transition/`, `raise-finding/` | Filters `plan_id`, `status`, `outcome`, `scheduled_before` |
| `activations/`, `activations/{id}/`, `transition/` | Filters `plan_id`, `incident_id`, `status` |
| `activations/{id}/log/` | `GET` the log, `POST` an entry (`text`, optional `step_id`) |

---

## 6. MCP tools

`_register_continuity_tools()`, a `TOPIC_CONTINUITY` help topic, the `BIAN` / `BCPL` / `BCEX` / `BCAC` prefixes.

- `_register_crud` for `business_impact_analysis`, `continuity_plan`, `continuity_exercise`; child tools for BIA entries and recovery steps (`add_bia_entry`, `update_bia_entry`, `delete_bia_entry`, `add_recovery_step`, `update_recovery_step`, `delete_recovery_step`, `reorder_recovery_steps`).
- `get_plan_feasibility(plan_id)` (RG-BCM-10), `list_exercise_overdue_plans()`.
- `activate_continuity_plan(plan_id, reason, incident_id=None)`, `add_activation_log_entry(activation_id, text, step_id=None)`, `stand_down_activation(activation_id, comment)`, `get_activation_log(activation_id)`.
- `raise_finding_from_exercise(exercise_id, finding_type, recommendation="")`.

---

## 7. Notifications

| Event | Recipients |
| --- | --- |
| `PLAN_ACTIVATED` | Plan owner, assigned users of the steps' roles (RG-BCM-19) |
| `EXERCISE_DUE` : daily sweep, `next_exercise_due` within 30 days, then overdue weekly | Plan owner |
| `BIA_REVIEW_DUE` : daily sweep, validated analysis older than its `review_frequency_months` | Analysis owner |

Submissions use `LIFECYCLE_SUBMITTED` (RG-LC-06).

---

## 8. User interface

- **Sidebar** : a new **Continuity** section after Training : *Impact analyses*, *Plans*, *Exercises*, *Activations*.
- **BIA detail** : stepper, rail (stage, entries, critical entries, period). The entries card is a flush table (target, MTD, RTO, RPO, worst impact) and each entry opens a drawer with the impact grid (categories x windows, 1 to 4 selects, the suggested MTD shown live). A heat-map rendering of the grid uses the `ebios_scale` badge tones.
- **Plan detail** : stepper, rail (stage, recovery time vs RTO with the *RTO not met* flag, next exercise, active activation). Cards : strategy and activation criteria, recovery steps (ordered table, drag-free *Move up / Move down* buttons while draft), coverage, document, exercises, activations. An **Activate** button (danger) opens a drawer asking for the reason and the optional incident.
- **Exercise detail** : stepper, results, objective met badge, lessons learned, finding.
- **Activation detail** : a live timeline of the log (append form at the top for holders of `continuity.activation.update`), each step with a *Reached* button, the elapsed time since activation, *Stand down*.
- **Reverse cards** on essential asset, activity, support asset, site and incident pages (RG-BCM-22); the incident page has *Activate a plan*.

Platform surfaces : search, calendar (exercises scheduled, next exercise due, BIA review), dashboard widget *Continuity* (active activations first, plans RTO not met, exercises overdue), kanban (my planned exercises, my steps in active activations), indicators `plans_exercised_on_time` and `critical_activities_covered`, help banners.

---

## 9. Technical considerations

### 9.1 App wiring checklist

- [ ] `INSTALLED_APPS` gains `"continuity"`; lifecycles imported in `ready()`; models, admin, migrations, permission migration, notification types.
- [ ] `Finding.continuity_exercise` and `FindingSource.CONTINUITY_EXERCISE`.
- [ ] Navigation, accent, sidebar; reverse cards; incident integration.
- [ ] Calendar, dashboard widget, kanban, search, indicators.
- [ ] REST, MCP, assistant catalogue, generated reference.
- [ ] `continuity_sweep` scheduled with the other sweeps.
- [ ] Seed : a validated Voltara BIA (grid operations, billing, customer portal, SCADA telemetry), a DRP for the data centre and a crisis plan with steps, a validated exercise (partial, with a finding) and a planned one, a stood-down activation from a seed incident with its log.
- [ ] Translations, help banners, user guide, README, CHANGELOG.

### 9.2 Audit

- Activation log entries are append-only and history-tracked; the elapsed times are computed from their timestamps, never typed.
- BIA values reach the assets only through RG-BCM-05, with a change reason naming the analysis.

---

## 10. Acceptance criteria

- [ ] A BIA entry refuses RTO > MTD and a decreasing impact series; a validated BIA writes the asset figures and supersedes the previous one of the same scopes.
- [ ] An active plan cannot have its steps changed without Revise; its feasibility flag follows the covered RTOs.
- [ ] Validating an exercise moves the next exercise date; a failed exercise raises one finding.
- [ ] An activation from an incident appears on both pages; its log cannot be edited; standing down records the achieved time.
- [ ] Scope tenancy, light / dark, desktop / mobile, translations, generated reference.

---

## 11. Out of scope for v0.37.0

- Crisis communication (mass notification, call trees, status pages).
- Per-step timings in exercises (the exercise records the overall achieved recovery time).
- Collecting BIA inputs from activity owners through a questionnaire campaign.
- Supplier continuity attestations and third-party exit plans (DORA article 28), which belong with the supplier register.

# Module 8 : Controls

## Functional and technical specification

The register of the organisation's **security controls** (in French, *mesures de sécurité*) and of the tests that prove they work. A control is something the organisation actually does : "multi-factor authentication on every remote access", "quarterly access review of the ERP", "encrypted off-site backups". Each control answers one or more requirements of one or more frameworks (ISO/IEC 27001:2022 Annex A, NIS2, a customer contract), treats one or more risks, protects support assets, and contributes to objectives. Its **effectiveness** is not declared : it is derived from recorded, reviewed test runs with their evidence.

It answers the questions an auditor asks of the Statement of Applicability and of clause 9.1 : *what does the organisation do for this requirement, is it implemented, who owns it, how do you know it works, and when was it last tested.*

**Status : proposed for v0.37.0.**

## Entities

| Entity | Class | Reference prefix | Lifecycle |
| --- | --- | --- | --- |
| [Control](control.md) | `controls.models.control.Control` | `CTRL` | `control` |
| [ControlTest](control-test.md) | `controls.models.control_test.ControlTest` | `CTST` | `control_test` |
| [ControlTestRun](control-test-run.md) | `controls.models.control_test_run.ControlTestRun` | `CTRN` | `control_test_run` |
| [ControlTestEvidence](control-test-evidence.md) | `controls.models.evidence.ControlTestEvidence` | none | none (write-once record) |

---

## 1. Overview

### 1.1 Purpose

Today the treatment of a requirement or a risk is scattered : compliance action plans, risk treatment plans and EBIOS PACS measures all describe *work to do*, but none of them is the durable thing that work produces. The specifications of the risk, treatment plan, objective, support asset and requirement entities all anticipate a `Measure` entity "(Measures module)" that was never built; `Requirement` still carries a commented-out `linked_measures` field. As a result the SoA can only say that a requirement is applicable and which action plans touch it, not which control implements it or whether that control works.

This module makes the controls a governed register :

- a **control** has an identity (reference, name, ISO 27001 theme, nature, automation, owner, scopes) and a lifecycle from proposed to planned, implemented and retired;
- it is linked to the **requirements** it satisfies (any framework, many-to-many : one control serves ISO 27001 A.8.5, NIS2 article 21 and a customer clause at once), the **risks** it treats, the **treatment plans** and **PACS measures** that create or reinforce it, the **support assets** it applies to, the **objectives** it contributes to and the **documents** that describe it;
- each control has one or more **tests** (method, procedure, acceptance criteria, frequency, tester);
- each **test run** records who tested, when, over which period, on which sample, with what result and which evidence; it is frozen once submitted and validated by a second person (segregation of duties);
- the control's **effectiveness** is derived from the latest validated run of each of its active tests, and every test has a derived next due date with reminders;
- a failed or partial run can **raise a finding** in the nonconformity register (clause 10.2), pre-filled from the run;
- the **SoA** lists, for every applicable requirement, the controls implementing it, their implementation state and their effectiveness.

### 1.2 Functional scope

| Area | In v0.37.0 |
| --- | --- |
| Control register with theme, nature, automation, owner, scopes, tags, implementation date, description of how it operates | yes |
| Links to requirements, risks, treatment plans, PACS measures, support assets, objectives and documents | yes |
| "Create controls from requirements" : draft one control per selected requirement of a framework (bootstraps an Annex A register) | yes |
| Tests with method, procedure, acceptance criteria, frequency, default tester; derived next due date | yes |
| Test runs with result, period, sample, observations, evidence files (SHA-256), submission and independent validation | yes |
| Derived control effectiveness; overdue tests | yes |
| "Raise a finding" from a failed or partial run | yes |
| SoA enriched with implementing controls, their state and their effectiveness | yes |
| Control cards on the requirement, risk, treatment plan, PACS measure, support asset, objective and document detail pages | yes |
| REST API, MCP tools, global search, calendar, dashboard widget, kanban (my tests due, my runs to validate), predefined indicators, help banners, demo seed | yes |
| Automatic adjustment of a risk's residual level from control effectiveness | no (see §11) |
| Automated test runs pushed by an external scanner or CI job | no (see §11) |
| Control maturity scoring (CMMI-like levels) | no (see §11) |

### 1.3 Dependencies on other modules

| Target module | Nature of the dependency |
| --- | --- |
| Accounts | `User` for owners, testers and reviewers; `accounts.Notification` for every notification; `PERMISSION_REGISTRY` and `SYSTEM_GROUPS`. |
| Context | `ScopedModel` / `BaseModel`, `Scope` tenancy, `Tag`; `Objective` through `Control.objectives`. |
| Assets | `SupportAsset` through `Control.support_assets`. |
| Compliance | `Requirement` through `Control.requirements`; `Finding.control_test_run` (FK, `SET_NULL`) and a new `FindingSource.CONTROL_TEST` value. |
| Risks | `Risk` through `Control.risks`; `RiskTreatmentPlan` through `Control.treatment_plans`; `PACSMeasure` through `Control.pacs_measures`. |
| Documents | `Policy` through `Control.policies` (the procedure or standard that describes the control). |
| Reports | The SoA generator (`reports.generators.build_soa_frameworks_data`) reads `Requirement.controls`. |

Every relation is declared **on `Control`**, with the reverse accessor `controls` on the target model. No other app gains a column except `Finding`; the commented-out placeholders (`Requirement.linked_measures`, `SupportAsset.related_measures`, `Objective.linked_measures`) are removed and the entity specifications that named a future `Measure` now point here.

---

## 2. Business rules : the RG-CTL register

### 2.1 Controls

| ID | Rule |
| --- | --- |
| RG-CTL-01 | A control is a durable practice, not a task. Work to set it up lives in the plans that link to it (treatment plans, PACS measures, compliance action plans through the requirements); the control's lifecycle says where the practice itself stands : proposed (`draft`), decided but not yet operating (`planned`), operating (`implemented`), retired (`archived`). |
| RG-CTL-02 | Declaring a control implemented stamps `implemented_on` (default today, may be set earlier, never in the future) and is gated by `controls.control.approve`. Sending an implemented control back to `planned` requires a comment (the practice stopped or regressed) and clears nothing : `implemented_on` keeps the original date, and history shows the regression. |
| RG-CTL-03 | A control can be retired only with a comment. Retiring it retires its active tests in the same transaction (RG-CTL-08 mechanics). A retired control stays visible on the pages of the entities it was linked to, flagged as retired, and drops out of the SoA and every KPI. |
| RG-CTL-04 | Every relation picker of the control form offers `linkable_or_linked()` targets : a requirement, risk, plan, asset, objective or document in a linkable step, plus the ones already linked. The reverse cards on the target pages list controls in any step, with their state badge. |
| RG-CTL-05 | "Create controls from requirements" creates, for each selected applicable requirement of a framework that has no linked control yet, one `draft` control named after the requirement, with its description copied as a starting point, the framework's scopes and the requirement linked. It never links an existing control and never runs twice for the same requirement (requirements already covered are skipped and reported). |

### 2.2 Tests and runs

| ID | Rule |
| --- | --- |
| RG-CTL-06 | A [test](control-test.md) belongs to one control. It can be activated only when its control is `planned` or `implemented` and it has a procedure and acceptance criteria : a test with no pass criterion proves nothing. |
| RG-CTL-07 | `next_due_date` of an active test is **derived** and stored (indexed, for the calendar, the dashboard and the sweep) : the `performed_on` date of its latest validated run plus `frequency_months`; with no validated run yet, its `first_due_date`, or the activation date when none was given. A test is **overdue** when it is active and `next_due_date < today`; overdue is never a lifecycle step. |
| RG-CTL-08 | Retiring a test requires a comment. A retired test no longer counts towards effectiveness and is no longer due; its runs stay readable. |
| RG-CTL-09 | A [run](control-test-run.md) is recorded against an **active** test. Its content (result, performed by, performed on, period, sample, observations, evidence) is **editable only in `draft`**; from `in_review` onward it is frozen on every surface. Sending it back to draft re-opens it. |
| RG-CTL-10 | Submitting a run requires a result; a `partial` or `fail` result also requires observations. `performed_on` cannot be in the future; when a period is given, `period_start <= period_end <= performed_on`. |
| RG-CTL-11 | **Segregation of duties** : a run is validated by a holder of `controls.test.approve` who is **not** its `performed_by`. The gate applies to superusers too; the only bypass is the system path used by the seed (`enforce_permission=False`). Validation stamps `reviewed_by` / `reviewed_at` from the transition. |
| RG-CTL-12 | Validating a run recomputes, in the same transaction, the test's `next_due_date` (RG-CTL-07) and the control's effectiveness (RG-CTL-14). Withdrawing a validated run (to `archived`, with a comment : the run was found unreliable) recomputes both as well. |
| RG-CTL-13 | Evidence files follow the incident evidence rules : allowed extensions, at most 25 MB each, SHA-256 stored at upload, served only through the permission-checked, scope-filtered download view, never serialized. Files are added or removed only while the run is in `draft`; afterwards an [evidence](control-test-evidence.md) row is write-once. |

### 2.3 Effectiveness

| ID | Rule |
| --- | --- |
| RG-CTL-14 | `Control.effectiveness` is **derived** and stored (for filters, the SoA and the KPIs), from the latest validated run of each **active** test of the control : `not_effective` if any of them failed, otherwise `partially_effective` if any is partial, otherwise `effective` if every active test has one, otherwise `not_tested`. A control with no active test is `not_tested`. It is recomputed on every run transition, on test activation and retirement, and by the daily sweep. |
| RG-CTL-15 | `Control.is_test_overdue` is true when any active test of the control is overdue. A control whose effectiveness rests on an overdue test still shows its last effectiveness, flagged as stale; it is never silently downgraded. |
| RG-CTL-16 | "Raise a finding" on a validated `partial` or `fail` run creates a [Finding](../m3-compliance/finding.md) with `source = control_test`, `control_test_run` set, the run's observations as its description, the control's requirements as its related requirements, and the acting user as `assessor`. It is an explicit action (the finding type, minor / major nonconformity or observation, is a judgement), offered once per run and recorded on the run page. |

### 2.4 Integration

| ID | Rule |
| --- | --- |
| RG-CTL-17 | Every report, KPI, calendar feed and picker filters through `reportable()` / `linkable()` / `linkable_or_linked()`. Controls in `planned` and `implemented` are reportable and linkable; tests count only when `active`; runs only when `validated`. |
| RG-CTL-18 | The **SoA** gains, for each applicable requirement, the list of its reportable controls with their implementation state and effectiveness, and an *Implementation* column summarising them (*Implemented*, *Partially implemented* when some controls are only planned, *Planned*, *No control*). When at least one control is linked, the justification of an applicable requirement lists the controls before the action plans. Not-applicable requirements keep their stored justification. |
| RG-CTL-19 | `Control` is a `ScopedModel` and carries its own `scopes` (defaulting, on creation from a requirement, to the framework's scopes); `ControlTest`, `ControlTestRun` and `ControlTestEvidence` inherit through `scope_parent_lookup` (`control__scopes`, `test__control__scopes`, `run__test__control__scopes`) in `ScopeFilterMixin`, the API mixin and the MCP scope filter. |
| RG-CTL-20 | A risk's residual level is **not** computed from its controls in v0.37.0 (see §11) : the risk and treatment plan pages show the linked controls and their effectiveness so the assessor can justify the residual level they set. |

---

## 3. Lifecycles

Each lifecycle is generated from its transition constants in `controls/constants.py` and registered in `controls/lifecycles.py`, imported from `ControlsConfig.ready()`. A test asserts each model's `get_lifecycle().name`. As in the documents module, the exit step of each lifecycle keeps the platform code `archived` with a domain label, so the engine never appends unguarded archive / restore edges.

### 3.1 `control`

| Code | Label | Kind | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- | --- |
| `draft` | Proposed | DRAFT | no | no | **yes** | neutral |
| `planned` | Planned | INTERMEDIATE | **yes** | **yes** | no | info |
| `implemented` | Implemented | INTERMEDIATE | **yes** | **yes** | no | success |
| `archived` | Retired | ARCHIVED | no | no | no | muted |

| Verb | Transition | `permission_action` | `requires_comment` | Side effect |
| --- | --- | --- | --- | --- |
| Plan | `draft -> planned` | `approve` | no | |
| Declare implemented | `draft -> implemented`, `planned -> implemented` | `approve` | no | stamps `implemented_on` (RG-CTL-02) |
| Back to planned | `implemented -> planned` | `update` | **yes** | |
| Retire | `planned -> archived`, `implemented -> archived` | `approve` | **yes** | retires the active tests (RG-CTL-03) |
| Retire | `draft -> archived` | `update` | **yes** | |

`draft -> implemented` exists for the initial inventory : most controls already operate when the register is first filled.

### 3.2 `control_test`

| Code | Label | Kind | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- | --- |
| `draft` | Draft | DRAFT | no | no | **yes** | neutral |
| `active` | Active | INTERMEDIATE | **yes** | **yes** | no | success |
| `archived` | Retired | ARCHIVED | no | no | no | muted |

| Verb | Transition | `permission_action` | `requires_comment` | Side effect |
| --- | --- | --- | --- | --- |
| Activate | `draft -> active` | `approve` | no | RG-CTL-06 gate; computes `next_due_date`; recomputes the control's effectiveness |
| Retire | `active -> archived` | `approve` | **yes** | recomputes the control's effectiveness |
| Retire | `draft -> archived` | `update` | **yes** | |

### 3.3 `control_test_run`

| Code | Label | Kind | In reports | Linkable | Deletable | Tone |
| --- | --- | --- | --- | --- | --- | --- |
| `draft` | In progress | DRAFT | no | no | **yes** | neutral |
| `in_review` | In review | INTERMEDIATE | no | no | no | info |
| `validated` | Validated | INTERMEDIATE | **yes** | no | no | success |
| `archived` | Withdrawn | ARCHIVED | no | no | no | muted |

| Verb | Transition | `permission_action` | `requires_comment` | Side effect |
| --- | --- | --- | --- | --- |
| Submit for review | `draft -> in_review` | `update` | no | RG-CTL-10 gate; `notify_lifecycle_submitted` to the test's reviewers |
| Send back | `in_review -> draft` | `approve` | **yes** | |
| Validate | `in_review -> validated` | **`approve`** | no | RG-CTL-11 gate and stamps; RG-CTL-12 recomputation; `CONTROL_TEST_FAILED` when the result is `partial` or `fail` |
| Withdraw | `validated -> archived` | `approve` | **yes** | RG-CTL-12 recomputation |
| Cancel | `draft -> archived` | `update` | **yes** | |

The gates and side effects live in each model's `transition_to()`, inside one `transaction.atomic()` block that locks the control row, so every surface (stepper, REST, MCP) goes through them.

---

## 4. Permissions and access control

`PERMISSION_REGISTRY` gains a `controls` module (`MODULE_LABELS["controls"] = _("Controls")`) with two features :

| Codename | Description |
| --- | --- |
| `controls.control.read` | List and read controls and their links |
| `controls.control.create` | Create a control, including from requirements |
| `controls.control.update` | Edit a control's identity and links, send it back to planned |
| `controls.control.approve` | Plan, declare implemented, retire a control |
| `controls.control.delete` | Delete a proposed control |
| `controls.test.read` | Read tests, runs and evidence |
| `controls.test.create` | Create a test, record a run |
| `controls.test.update` | Edit a draft test or run, add or remove its evidence, submit a run |
| `controls.test.approve` | Activate / retire a test, validate / send back / withdraw a run, raise a finding from a run |
| `controls.test.delete` | Delete a draft test or a draft run |

System groups : Super Administrateur and Administrateur get every codename; RSSI / DPO get read, create, update, approve; Contributeur gets read, create, update; Auditeur and Lecteur get read (an auditor who records runs is given the Contributeur group as well, so the read-only meaning of the Auditeur group is kept). A migration creates the rows and attaches them.

---

## 5. API

Base path `/api/v1/controls/`. House pattern (`ModulePermission`, `ScopeFilterAPIMixin`, `LifecycleAPIMixin`, `status` read-only from `workflow_state`).

| Method | Path | Description |
| --- | --- | --- |
| `GET` / `POST` | `controls/` | List (filters `status`, `theme`, `nature`, `owner_id`, `scope_id`, `effectiveness`, `test_overdue`, `requirement_id`, `risk_id`) / create |
| `GET` / `PUT` / `PATCH` / `DELETE` | `controls/{id}/` | Read / update / delete a proposed control |
| `GET` / `POST` | `controls/{id}/transition/` | Allowed transitions / perform one |
| `GET` | `controls/{id}/history/` | Timeline |
| `POST` | `controls/from-requirements/` | RG-CTL-05 : `framework_id`, optional `requirement_ids`, `scope_ids`; returns created and skipped |
| `GET` / `POST` | `tests/` | List (filters `control_id`, `status`, `overdue`, `due_before`, `tester_id`) / create |
| `GET` / `PATCH` / `DELETE` | `tests/{id}/` | Read / edit a draft / delete a draft |
| `GET` / `POST` | `tests/{id}/transition/` | Activate, retire |
| `GET` / `POST` | `runs/` | List (filters `test_id`, `control_id`, `status`, `result`, `performed_by_id`) / create a draft run |
| `GET` / `PATCH` / `DELETE` | `runs/{id}/` | Read / edit a draft (RG-CTL-09) / delete a draft |
| `GET` / `POST` | `runs/{id}/transition/` | Submit, send back, validate, withdraw, cancel |
| `POST` | `runs/{id}/raise-finding/` | RG-CTL-16 : `finding_type`, optional `recommendation` |

Evidence files are uploaded through the web form only (binary payloads stay out of the JSON API and MCP, as for contracts and policy PDFs); the run serializer lists its evidence with `file_name`, `size`, `sha256` and `download_url`.

---

## 6. MCP tools

`_register_controls_tools()` in `mcp/tools.py`, a `TOPIC_CONTROLS` help topic, and the `CTRL` / `CTST` / `CTRN` reference prefixes in `HELP_TEXT`.

- `_register_crud` for `control`, `control_test` and `control_test_run` (list, get, create, batch create, update, delete, transition, allowed transitions, history), with `m2m_fields` for scopes and every control relation.
- `create_controls_from_requirements(framework_id, requirement_ids=None, scope_ids=None)` (RG-CTL-05).
- `get_control_effectiveness(control_id)` : the effectiveness, each active test with its latest validated run and next due date.
- `list_overdue_control_tests()` and `list_my_control_tests_due()`.
- `raise_finding_from_run(run_id, finding_type, recommendation="")` (RG-CTL-16).
- `get_requirement_coverage(framework_id)` : per applicable requirement, its controls, their state and effectiveness (the data behind the SoA).

`assistant/catalog.py` gains read-only `ToolSpec` entries for listing controls, reading a control's effectiveness and reading a framework's coverage.

---

## 7. Notifications

New `NotificationType` values with `notify_*` helpers in `accounts/notifications.py`; an accounts migration alters the choices.

| Event | Recipients | Channel |
| --- | --- | --- |
| `CONTROL_TEST_DUE` : daily sweep, `next_due_date` within 14 days | The test's tester, else the control owner | In-app, email |
| `CONTROL_TEST_OVERDUE` : same sweep, due date passed (sent once, then weekly) | The tester and the control owner | In-app, email |
| `CONTROL_TEST_FAILED` : a `partial` or `fail` run is validated | The control owner | In-app, email |

Submission of a run sends the existing `LIFECYCLE_SUBMITTED` notification (RG-LC-06) through the RG-LC-09 recipient chain, which resolves to the holders of `controls.test.approve`, excluding the submitter.

---

## 8. User interface

All pages follow the [UI components](../../sdk/ui-components.md) anatomies.

- **Sidebar** : a new **Controls** section between Compliance and Documents, with *Controls* and *Tests*. The section sits in the compliance family of the navigation tree.
- **Control list** (`/controls/`) : reference, name, theme, owner, state, effectiveness (badge), next test due (red when overdue), requirement count. Rail : implemented controls, effective rate (effective / tested), overdue tests, controls never tested. Filters on theme, nature, owner, scope, state, effectiveness, overdue. A *Create from requirements* action opens a drawer (framework, then a checklist of uncovered applicable requirements).
- **Control detail** : stepper (`control`), rail (lifecycle stage, effectiveness, next test due, implemented on). Cards : *Description* (how the control operates, theme, nature, automation), *Tests* (flush table : name, method, frequency, latest result, next due; "New test"), *Recent runs*, *Requirements* (grouped by framework), *Risks and treatment* (risks with their residual level, treatment plans, PACS measures), *Applies to* (support assets), *Objectives*, *Documents*, traceability card.
- **Test detail** : stepper (`control_test`), rail (stage, latest result, next due, frequency). Cards : *Procedure* (objective, method, procedure, acceptance criteria), *Runs* (flush table : date, performer, result, state, reviewer; "Record a run").
- **Run detail** : stepper (`control_test_run`), rail (stage, result, performed on, reviewer). Cards : *Result* (result, period, sample, observations), *Evidence* (files with size and SHA-256, upload / remove while in progress), *Review* (reviewer, date), *Finding* ("Raise a finding" on a validated partial / failed run, or the finding raised).
- **Test register** (`/controls/tests/`) : every test with control, tester, frequency, latest result, next due; filters on overdue, due window, tester, result.
- **Reverse cards** : a *Controls* `section_card` on the requirement, risk, treatment plan, PACS measure, support asset, objective and document detail pages (reference, name, state, effectiveness).
- Forms are drawer modals with their page fallbacks; the run form opens prefilled with the test's default tester as performer and today as date.

Platform surfaces : global search (controls and tests), calendar (`controls` category : next test due dates), dashboard widget *Controls* (implemented, effective rate, overdue tests, failed runs awaiting a finding), kanban (my tests due within 14 days in *To do*, my runs in progress in *In progress*, runs I can validate in *To review*), predefined indicators `control_effectiveness_rate` and `control_tests_overdue`, help banners on the five pages, the SoA (RG-CTL-18).

---

## 9. Technical considerations

### 9.1 App wiring checklist

- [ ] `INSTALLED_APPS` gains `"controls"`; `ControlsConfig.ready()` imports `controls.lifecycles` and the signal handlers.
- [ ] Models, admin (`SimpleHistoryAdmin`), initial migration; `HistoricalRecords(excluded_fields=["file"])` on the evidence.
- [ ] `Finding.control_test_run` (FK `SET_NULL`) and `FindingSource.CONTROL_TEST`, with a compliance migration; the finding page shows the originating run.
- [ ] Removal of the commented-out `linked_measures` / `related_measures` placeholders; the entity specs updated to point at `Control`.
- [ ] `PERMISSION_REGISTRY`, `MODULE_LABELS`, the permission migration attaching the rows to the six system groups.
- [ ] `core/navigation.py` `NAV_TREE` entries; `MODULE_ACCENTS["controls"]` with its tokens in both blocks of `static/css/cairn/00-tokens.css`; the sidebar section.
- [ ] `BADGE_REGISTRY` : an `effectiveness` scale extended with `not_tested`, a `test_result` scale (`pass`, `partial`, `fail`), a `control_theme` scale.
- [ ] Calendar categories, dashboard widget, kanban builder, global search categories, predefined indicators.
- [ ] The SoA generator and its PDF template (RG-CTL-18).
- [ ] REST routes under `/api/v1/controls/`, MCP tools, assistant catalog entries.
- [ ] The daily sweep `controls_sweep` (due / overdue reminders, effectiveness recomputation) scheduled like the documents sweep.
- [ ] `scripts/seed_demo_data.py` : a Voltara control set created from the ISO 27001 Annex A framework, linked to risks, treatment plans, assets, objectives and policies; tests with validated runs (pass, partial, fail with a finding), one overdue test, one run in review.
- [ ] Translations (with `msgctxt "control"` where a label collides, e.g. "Planned", "Implemented", "Active"), help banners, user guide page, README feature table, CHANGELOG.

### 9.2 History and audit trail

Every model is history-tracked. A run's content is frozen from `in_review` (RG-CTL-09), so its history after submission records only transitions and review stamps : the result, the evidence and their SHA-256 are the record. Evidence rows are append-only after submission (RG-CTL-13).

### 9.3 Security

- The evidence download view checks `controls.test.read` and the control's scopes, and serves the file as an attachment with its stored content type forced to a safe list.
- Segregation of duties (RG-CTL-11) is enforced in the model, so no surface can validate one's own run.
- The SoA keeps filtering through `reportable()`, so a proposed or retired control never appears in an audit deliverable.

---

## 10. Acceptance criteria

- [ ] A control links to requirements of several frameworks, to risks, plans, PACS measures, assets, objectives and documents, and appears on each of their pages.
- [ ] "Create controls from requirements" creates one proposed control per uncovered applicable requirement and skips covered ones.
- [ ] A run's content cannot change once submitted, through the form, the API or MCP; its performer cannot validate it.
- [ ] Validating or withdrawing a run updates the test's next due date and the control's effectiveness in the same transaction.
- [ ] A validated failed run can raise exactly one finding, linked back to the run and pre-filled.
- [ ] The SoA lists, for each applicable requirement, its controls with their state and effectiveness.
- [ ] Scope tenancy holds on every list, detail, API and MCP surface, including tests, runs and evidence downloads.
- [ ] Every page renders in light and dark, at desktop and mobile widths, with the lifecycle stepper as the only way to change a state.
- [ ] Every string is translated; the generated reference (`generate_docs`) and the wiki check are clean.

---

## 11. Out of scope for v0.37.0

- Computing a risk's residual likelihood / impact from the effectiveness of its controls (the assessor keeps setting the residual level; the controls are shown as its justification).
- Automated test runs pushed by a scanner, a CSPM or a CI job through a dedicated ingestion endpoint (the REST API can already create and submit runs).
- Control maturity scoring (CMMI or C2M2 levels) and a maturity target per control.
- Sampling helpers (population size, statistically driven sample sizes).
- A shared control catalogue imported from an external source (the "create from requirements" action covers bootstrapping from a framework already in Cairn).

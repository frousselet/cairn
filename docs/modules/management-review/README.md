# Management review : ISO 27001:2022 compliance (clause 9.3)

## Functional and technical specifications

**Version :** 1.0
**Date :** 17 April 2026
**Status :** Draft
**Module concerned :** `reports` (cross-cutting : context, compliance, risks, accounts)

## Entities in this module

- [ManagementReview](management-review.md) : `reports.models.management_review.ManagementReview`
- [ManagementReviewParticipant](participant.md) : `reports.models.management_review.ManagementReviewParticipant`
- [ManagementReviewDecision](decision.md) : `reports.models.management_review.ManagementReviewDecision`
- [IsmsChange](isms-change.md) : `reports.models.management_review.IsmsChange`
- [StakeholderFeedback](stakeholder-feedback.md) : `context.models.stakeholder_feedback.StakeholderFeedback`
- [ManagementReviewComment](comment.md) : `reports.models.management_review.ManagementReviewComment`
- [ManagementReviewTransition](transition.md) : `reports.models.management_review_transition.ManagementReviewTransition`

---

## 1. Overview

### 1.1 Objective

Equip Cairn with a complete **management review** process compliant with clause 9.3 of ISO 27001:2022. The current state is limited to a **one-off export** (PPTX + DOCX) aggregating the inputs of clause 9.3.2. This specification adds the missing elements to produce **auditable, persistent and traceable** management reviews :

- a complete review lifecycle (preparation, holding, closure)
- the structured capture of the **decisions** and **ISMS changes** required by clause 9.3.3
- **review-to-review traceability** (follow-up of actions arising from previous reviews)
- the formalisation of **stakeholder feedback** (clause 9.3.2.e)
- **measurement trends** (clause 9.3.2.d.2) by leveraging `IndicatorMeasurement`

### 1.2 Functional scope

The module covers six sub-domains :

1. **Management reviews** (full lifecycle : persistent entity [ManagementReview](management-review.md))
2. **Decisions** arising from a review (entity [ManagementReviewDecision](decision.md))
3. **ISMS changes** identified (entity [IsmsChange](isms-change.md))
4. **Stakeholder feedback** (entity [StakeholderFeedback](stakeholder-feedback.md))
5. **Enriched export** (PPTX/DOCX) consuming the persistent data
6. **Back-chaining** of action plans, risk treatment plans and objectives to the deciding review

### 1.3 Exhaustive mapping to ISO 27001:2022 clause 9.3

| Clause | Requirement | Current coverage | Target coverage |
|---|---|---|---|
| 9.3.1 | Review planning | Missing | `ManagementReview.planned_date`, `frequency`, reminders |
| 9.3.2.a | Actions from previous reviews | Partial (action plans listed) | FK `originating_review` on actions + follow-up table |
| 9.3.2.b | External/internal issues | Complete | Unchanged |
| 9.3.2.c | Needs/expectations of interested parties | Complete | Unchanged |
| 9.3.2.d.1 | Nonconformities and corrective actions | Complete | Unchanged |
| 9.3.2.d.2 | Monitoring and measurement | Partial (current value) | Trend via `IndicatorMeasurement` |
| 9.3.2.d.3 | Audit results | Complete | Unchanged |
| 9.3.2.d.4 | Achievement of information security objectives | Complete | Unchanged |
| 9.3.2.e | Stakeholder feedback | Partial (expectations) | New entity `StakeholderFeedback` |
| 9.3.2.f | Risk assessment results and treatment plan | Complete | Unchanged |
| 9.3.2.g | Opportunities for improvement | Partial (audit findings) | Free-form entry in the review + findings |
| 9.3.3 | Outputs (decisions, ISMS changes) | Missing (placeholder) | `ManagementReviewDecision` + `IsmsChange` |

### 1.4 Dependencies on other modules

| Target module | Nature of the dependency |
|---|---|
| `accounts` | Review not limited to its creator : multiple participants, minute-taker, approver. Permissions `reports.management_review.*`. |
| `context` | Indicators (trend), objectives, issues, interested parties, feedback. |
| `compliance` | Action plans, findings, audits, frameworks : back-chained to a review. |
| `risks` | Assessments, critical risks, treatment plans : back-chained to a review. |
| `reports` | Generation of the enriched PPTX/DOCX exports. |
| `mcp` | Exposure of reviews, decisions, feedback, ISMS changes. |

---

## Changes to existing models

Addition of **back-chaining** foreign keys (nullable, `SET_NULL`). Allows clause 9.3.2.a to be addressed and the decisional origin to be traced.

| Model | New field | Type | Role |
|---|---|---|---|
| `compliance.ComplianceActionPlan` | `originating_review` | FK → ManagementReview, null=True | Originating review |
| `compliance.ComplianceActionPlan` | `originating_decision` | FK → ManagementReviewDecision, null=True | Source decision |
| `risks.RiskTreatmentPlan` | `originating_review` | FK → ManagementReview, null=True | Originating review |
| `risks.RiskTreatmentPlan` | `originating_decision` | FK → ManagementReviewDecision, null=True | Source decision |
| `context.Objective` | `originating_review` | FK → ManagementReview, null=True | Originating review |
| `context.Objective` | `originating_decision` | FK → ManagementReviewDecision, null=True | Source decision |

No deletions. The migrations are additive and backward-compatible (all fields nullable).

---

## 3. Views and user journey

### 3.1 URL patterns

File : `reports/urls.py`

```
/reports/management-reviews/                    → ManagementReviewListView
/reports/management-reviews/create/             → ManagementReviewCreateView
/reports/management-reviews/<uuid:pk>/          → ManagementReviewDetailView
/reports/management-reviews/<uuid:pk>/edit/     → ManagementReviewUpdateView
/reports/management-reviews/<uuid:pk>/delete/   → ManagementReviewDeleteView
/reports/management-reviews/<uuid:pk>/transition/   → ManagementReviewTransitionView
/reports/management-reviews/<uuid:pk>/export/pptx/  → ManagementReviewExportPptxView
/reports/management-reviews/<uuid:pk>/export/docx/  → ManagementReviewExportDocxView
/reports/management-reviews/<uuid:pk>/snapshot/     → ManagementReviewSnapshotView (POST)

/reports/management-reviews/<uuid:pk>/decisions/create/ → DecisionCreateView
/reports/decisions/<uuid:pk>/                           → DecisionDetailView
/reports/decisions/<uuid:pk>/edit/                      → DecisionUpdateView
/reports/decisions/<uuid:pk>/promote/                   → DecisionPromoteView (creates an ActionPlan)

/reports/management-reviews/<uuid:pk>/isms-changes/create/ → IsmsChangeCreateView
/reports/isms-changes/<uuid:pk>/                           → IsmsChangeDetailView

/context/stakeholder-feedback/                   → StakeholderFeedbackListView
/context/stakeholder-feedback/create/            → StakeholderFeedbackCreateView
/context/stakeholder-feedback/<uuid:pk>/         → StakeholderFeedbackDetailView
```

### 3.2 Detail page `ManagementReviewDetailView`

**2-column, no-tabs** pattern (cf. `CLAUDE.md` : prefer 2-column card layout). Status stepper at the top, sticky sidebar on the right.

**Sidebar (right column, sticky)** :

- Status badge (mini stepper)
- Facilitator, approver
- Review period (`period_start` → `period_end`)
- Planned / held date
- Participants (list with roles and "present" indicator)
- Next review
- Buttons : Export PPTX, Export DOCX, Add a decision, Add an ISMS change

**Main column** : collapsible `<details>` sections, each corresponding to a 9.3.2 input :

1. **9.3.2.a Actions from previous reviews** : table of `pending`/`in_progress` decisions arising from earlier reviews, with status and due date.
2. **9.3.2.b Issues** : internal/external (uses `Issue` filtered on the period).
3. **9.3.2.c Stakeholder expectations** : uses `StakeholderExpectation` filtered.
4. **9.3.2.d.1 Nonconformities** : uses `Finding`.
5. **9.3.2.d.2 Monitoring and measurement** : table with a **"Trend" column** (🔺 improvement, = stable, 🔻 degradation) and **"Frequency compliance"**.
6. **9.3.2.d.3 Audits** : uses `ComplianceAssessment`.
7. **9.3.2.d.4 Objectives** : uses `Objective`.
8. **9.3.2.e Stakeholder feedback** : new section consuming `StakeholderFeedback`.
9. **9.3.2.f Risks and treatment plan** : summary + critical risks.
10. **9.3.2.g Opportunities for improvement** : findings of type `IMPROVEMENT_OPPORTUNITY` + free-text field `summary`.
11. **Decisions (output 9.3.3)** : editable table, inline "Promote to action plan" actions.
12. **ISMS changes (output 9.3.3)** : list of `IsmsChange`.
13. **Summary and next review** : `summary`, `next_review_date`.
14. **Comments** : thread (`ManagementReviewComment`).
15. **History** : `HistoricalRecords` of the review and its decisions.

### 3.3 Forms

- `ManagementReviewForm` : create/edit (title, description, scopes, frequency, period_start, period_end, planned_date, location, facilitator, approver, next_review_date, agenda, summary, tags).
- `ManagementReviewParticipantFormSet` : inline management of participants.
- `ManagementReviewTransitionForm` : target status + comment (required if `cancelled`).
- `ManagementReviewDecisionForm` : all the fields of [decision.md](decision.md).
- `IsmsChangeForm` : all the fields of [isms-change.md](isms-change.md).
- `StakeholderFeedbackForm` : all the fields of [stakeholder-feedback.md](stakeholder-feedback.md).
- `DecisionPromoteForm` : modal generating a `ComplianceActionPlan` pre-filled from a decision.

### 3.4 List `ManagementReviewListView`

- `SortableListMixin` (sorting persisted per user)
- Columns : Reference, Title, Period, Planned on, Status, Facilitator, Decisions (count), Scopes
- Filters : status, year, scope, facilitator
- Coloured status badges
- Full-text search on `title`, `description`, `reference`

### 3.5 Snapshot and auditability freeze

On the `held → closed` transition, the **"Close review"** button runs :

1. Generation of `gather_management_review_data(...)` with the review's `period_start`/`period_end`.
2. Serialization of the result into `ManagementReview.snapshot_data` (JSONField).
3. Subsequent exports consume `snapshot_data` **in priority** if it is not empty. The UI displays a "Data frozen on DD/MM/YYYY" badge to signal immutability.

Rationale : a closed review must no longer vary over time (auditability requirement). The live data keeps evolving but does not alter the approved minutes.

---

## 4. Enriched PPTX and DOCX exports

### 4.1 Data source

File : `reports/management_review.py` : refactoring of `gather_management_review_data` into **two modes** :

- `gather_live(...)` : current mode, live aggregation (for `planned`/`in_preparation`/`held` reviews).
- `gather_from_snapshot(review)` : rehydrate from `snapshot_data` (for `closed` reviews).

Enriched signature :
```python
gather_management_review_data(
    user,
    review=None,              # new : ManagementReview, takes priority
    scope_ids=None,
    period_start=None,
    period_end=None,
)
```

If `review` is provided :
- `scope_ids`, `period_start`, `period_end` are derived from it.
- If `review.status == closed`, the snapshot is used.
- Sections 11 (decisions) and 12 (ISMS changes) are added.
- Participants are injected into the DOCX cover page and the PPTX title slide.

### 4.2 Additions to the export

**Section 4b (measurement)** : new columns :

| Ref. | Indicator | Current value | Previous value | Trend | Target | Freq. compliance |
|---|---|---|---|---|---|---|

**Section 5 (stakeholder feedback)** : two blocks :
- `StakeholderFeedback` table (channel, subject, sentiment, severity, status)
- existing table of applicable expectations

**Section 9.3.3 (outputs)** : new slides / DOCX sections :

- **Decisions taken** : table (reference, category, title, owner, due date, priority, status)
- **ISMS changes** : table (reference, type, title, owner, status, target)
- **Executive summary** : insertion of `review.summary` (stripped rich text)
- **Next review** : `review.next_review_date`

**Signature page (DOCX)** : replace the current empty table with a table pre-filled with the participants (name, role, signature box). If `signature_data` contains a base64 image, embed it.

### 4.3 `[A completer]` placeholders

Completely removed. The data is now entered in the UI before the export and injected from the persistent review.

---

## 5. REST API

File : `reports/api/urls.py`, `reports/api/serializers.py`, `reports/api/views.py`.

Base URL : `/api/v1/reports/`

### 5.1 Endpoints

| Method | URL | Action |
|---|---|---|
| GET/POST | `/management-reviews/` | List / create |
| GET/PATCH/DELETE | `/management-reviews/<id>/` | Detail, partial update, delete |
| POST | `/management-reviews/<id>/transition/` | Status transition `{to_status, comment}` |
| POST | `/management-reviews/<id>/close/` | Closure (triggers snapshot) |
| GET | `/management-reviews/<id>/export/?format=pptx\|docx` | Download the export |
| GET/POST | `/management-reviews/<id>/decisions/` | List / create decisions |
| GET/PATCH/DELETE | `/decisions/<id>/` | Decision detail |
| POST | `/decisions/<id>/promote-to-action-plan/` | Creates a linked `ComplianceActionPlan` |
| GET/POST | `/management-reviews/<id>/isms-changes/` | List / create ISMS changes |
| GET/PATCH | `/isms-changes/<id>/` | ISMS change detail |
| GET/POST | `/management-reviews/<id>/participants/` | Manage participants |

And in `context` :

| Method | URL | Action |
|---|---|---|
| GET/POST | `/api/v1/context/stakeholder-feedback/` | List / create |
| GET/PATCH/DELETE | `/api/v1/context/stakeholder-feedback/<id>/` | Detail |

### 5.2 Serialization

- `ManagementReviewSerializer` : exhaustive, includes `decisions_count`, `participants`, `status_display`, `snapshot_available`.
- `ManagementReviewDetailSerializer` : extends it with nested decisions and ISMS changes.
- Permissions : `ManagementReviewPermission` class inheriting from `ModulePermission`.
- Approval workflow (`ApprovableAPIMixin`) reused for the `held → closed` transition.

---

## 6. MCP tools

File : `mcp/tools.py`. Follow the existing convention (detailed docstring, `@require_perm`).

| Tool | Permission | Description |
|---|---|---|
| `list_management_reviews` | `reports.management_review.read` | Filtered list (status, period, scope). |
| `get_management_review` | `reports.management_review.read` | Detail of a review (id or reference). |
| `create_management_review` | `reports.management_review.create` | Creates a review. |
| `update_management_review` | `reports.management_review.update` | Updates it. |
| `transition_management_review` | `reports.management_review.update` | Status transition. |
| `close_management_review` | `reports.management_review.approve` | Closure with snapshot. |
| `generate_management_review_report` | `reports.management_review.read` | Returns an export (base64) PPTX or DOCX. |
| `list_management_review_decisions` | `reports.management_review.read` | Lists the decisions of a review. |
| `create_management_review_decision` | `reports.management_review.update` | Adds a decision. |
| `promote_decision_to_action_plan` | `reports.management_review.update` + `compliance.action_plan.create` | Generates an action plan. |
| `list_isms_changes` | `reports.management_review.read` | Lists the ISMS changes. |
| `create_isms_change` | `reports.management_review.update` | Adds an ISMS change. |
| `list_stakeholder_feedback` | `context.stakeholder_feedback.read` | Lists the feedback. |
| `create_stakeholder_feedback` | `context.stakeholder_feedback.create` | Adds feedback. |

---

## 7. Permissions

Additions to `PERMISSION_REGISTRY` (`accounts/constants.py`) :

```python
"reports.management_review.read",
"reports.management_review.create",
"reports.management_review.update",
"reports.management_review.delete",
"reports.management_review.approve",
"context.stakeholder_feedback.read",
"context.stakeholder_feedback.create",
"context.stakeholder_feedback.update",
"context.stakeholder_feedback.delete",
```

Assignment to system groups :

| Group | Permissions |
|---|---|
| Super Admin, Admin | All |
| RSSI/DPO | All except `delete` |
| Auditor | `read` only |
| Contributor | `read`, `create`, `update` on stakeholder_feedback ; `read` on management_review |
| Reader | `read` only |

Added via a **data migration** (proven pattern, cf. existing migrations populating `PERMISSION_REGISTRY`).

---

## 8. Internationalization

- All new UI strings are wrapped with `_()` / `{% trans %}`.
- Systematic FR translations in `locale/fr/LC_MESSAGES/django.po`.
- **No-duplicate** check on `msgid` (cf. CLAUDE.md). Use `pgettext_lazy` with the context `"management review"` to disambiguate if needed (e.g. "Decision", "Status").
- `compilemessages` must succeed without error.

---

## 9. Navigation and helpers

- Addition of a **"Management reviews"** item in the main menu, under "Reports" (new sub-group).
- New `HelpContent` entries in `helpers` for : list page, detail page, decision creation, ISMS change creation, feedback creation.
- Dashboard (`core/views.py`) : addition of a "Next management review" widget (countdown + link) and "Overdue decisions".

---

## 10. Tests

Minimum expected coverage :

### 10.1 Unit

- `reports/tests/test_management_review_model.py` : lifecycle, snapshot, closure constraint (all decisions must have owner+due_date).
- `reports/tests/test_decision_model.py` : link to action plan, back-chaining.
- `reports/tests/test_isms_change_model.py` : workflow.
- `context/tests/test_stakeholder_feedback_model.py` : integrity, links.
- `reports/tests/test_indicator_trend.py` : trend computation, frequency compliance.

### 10.2 Views

- Full journey : create review → add decisions → close → export.
- Safeguard : closure refused if a decision has no `owner` or `due_date`.
- Snapshot : data frozen after closure (a later modification of an indicator must not alter the export).

### 10.3 API

- Full CRUD on the 4 new endpoints.
- Per-role permissions (matrix §7).
- Export via API : check the `Content-Type` and `Content-Disposition` headers.

### 10.4 MCP

- Each tool tested with success and refusal (missing permission).
- `generate_management_review_report` returns non-empty content, correct file name.

### 10.5 Export

- Integration test : generated DOCX contains the decisions, the participants, the summary.
- Integration test : generated PPTX no longer contains the `[A completer]` placeholders.

**Factories** (`factory-boy`) to add : `ManagementReviewFactory`, `ManagementReviewParticipantFactory`, `ManagementReviewDecisionFactory`, `IsmsChangeFactory`, `StakeholderFeedbackFactory`.

---

## 11. Migration and compatibility

### 11.1 Django migrations

Order :

1. `reports/migrations/0002_management_review.py` : creation of the 5 tables (`ManagementReview`, `ManagementReviewParticipant`, `ManagementReviewDecision`, `IsmsChange`, `ManagementReviewComment`, `ManagementReviewTransition`).
2. `context/migrations/XXXX_stakeholder_feedback.py` : creation of `StakeholderFeedback`.
3. `compliance/migrations/XXXX_action_plan_originating_review.py` : addition of nullable FK.
4. `risks/migrations/XXXX_treatment_plan_originating_review.py` : addition of nullable FK.
5. `context/migrations/XXXX_objective_originating_review.py` : addition of nullable FK.
6. `accounts/migrations/XXXX_management_review_permissions.py` : data migration populating `PERMISSION_REGISTRY` and system groups.

All additive. No existing data lost.

### 11.2 Compatibility with the existing export

The current export remains **functional without a review** : if `review=None`, the API keeps the v0.22 behaviour (live export with scopes+period). The existing screens (`report_list.html`, `management_review_form.html`) are kept as a **quick alternative** for users who do not want to create a persistent review.

In time (v+1), soft deprecation : an information banner recommending the use of `ManagementReview`.

---

## 12. CHANGELOG and README

In accordance with `CLAUDE.md` :

- **CHANGELOG.md** : add under `## [Unreleased]` :
  - `### Added` : "Persistent management review workflow (ISO 27001:2022 clause 9.3) with decisions, ISMS changes, participants, and snapshot-based auditability."
  - `### Added` : "Stakeholder feedback module."
  - `### Added` : "Indicator trend analysis in management review exports."
  - `### Changed` : "Management review export now consumes persistent review data when available."

- **README.md** : update :
  - Feature table (Reports column : + Management reviews).
  - MCP tools table : add the 14 new tools.
  - Tech stack : no new dependency (python-pptx, python-docx already present).

---

## 13. Acceptance criteria (Definition of Done)

The feature is considered delivered when **all** the following criteria are met :

### 13.1 Functional

- [ ] Create, edit, transition, close, cancel a `ManagementReview` from the UI.
- [ ] Add participants (internal and external), decisions, ISMS changes.
- [ ] Promote a decision to a `ComplianceActionPlan` via an inline button ; the created plan carries `originating_review` and `originating_decision`.
- [ ] Create `StakeholderFeedback` independently of a review.
- [ ] The DOCX/PPTX export of a `closed` review contains : decisions, ISMS changes, participants, summary, next review : zero `[A completer]` placeholder.
- [ ] The indicator trend appears in section 4b.
- [ ] Closure forbidden if a decision is incomplete (clear error message).
- [ ] The data of a `closed` review is frozen (does not vary with later changes in the database).

### 13.2 Technical

- [ ] All models use `BaseModel` or `ScopedModel` as relevant.
- [ ] `HistoricalRecords` on all new domain models.
- [ ] Complete DRF API with permissions, pagination, filters.
- [ ] MCP tools exposed with docstrings and `@require_perm`.
- [ ] Data migration populating permissions and groups without overwriting the existing ones.
- [ ] 100% of UI strings translated to FR, `compilemessages` OK, no duplicate `msgid`.
- [ ] Correct rendering on mobile + dark mode on all new pages.
- [ ] Horizontal stepper used for the review workflow.
- [ ] 2-column layout (no tabs) on the detail page.
- [ ] pytest test coverage ≥ 80% on the new files.

### 13.3 Auditability

- [ ] `HistoricalRecords` makes it possible to retrieve who modified what and when on the review, the decisions, the ISMS changes.
- [ ] `snapshot_data` of a closed review is timestamped and immutable (regression-tested).
- [ ] An external auditor (`Auditor` role) can view any closed review without being able to modify it.
- [ ] The export produced at T+N is identical to the export produced at the time of closure (for a `closed` review).

---

## 14. Out of scope (for a v+1)

- Qualified electronic signatures (eIDAS) integrated : remain manual in the DOCX.
- Formalised `Policy` model (currently `IsmsChange.affected_policies` = free text).
- Automatic email reminders to participants before the review.
- Pre-configured review templates by industry/certification.
- PDF export (possibly reusing the `reportlab` pipeline).
- "Management review process compliance" dashboard (frequency respected, approval delays).

---

## 15. Estimate

| Work package | Effort (person-days) |
|---|---|
| Models + migrations + admin | 3 |
| UI views + templates + workflow stepper | 6 |
| Forms and validations | 2 |
| Enriched DOCX/PPTX export + indicator trends + snapshot | 4 |
| DRF API | 2 |
| MCP tools | 2 |
| `StakeholderFeedback` (model, UI, API, MCP) | 2 |
| Permissions + groups + data migration | 1 |
| Tests (unit, integration, API, MCP) | 4 |
| i18n + FR translations | 1 |
| Documentation (README, CHANGELOG) | 0.5 |
| **Total** | **~27.5 days** |

---

_End of document._

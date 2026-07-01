# Lifecycle governance framework

`core.lifecycle` - the single, standardised engine every domain element runs on.

> **History.** This document was originally the spec for the first-generation
> `core.workflow` engine (issue #105). That engine, its per-app `workflows.py`
> machines, the `WorkflowStepperMixin`, the separate boolean **approval** axis
> (`is_approved` / `approved_by` / `approved_at`) and the `VersioningConfig`
> admin have all been **removed**. Everything below describes the current state:
> a single `core.lifecycle` engine, with validation expressed purely as reaching
> a reportable lifecycle step. The engine internals are documented in
> [`lifecycle.md`](lifecycle.md); this file is the governance / cross-cutting-rules
> reference.

Every domain element runs a **lifecycle**: an ordered set of steps with the
allowed transitions between them. Governance is metadata carried by each step, so
the cross-cutting rules (inclusion in reports / KPIs / the calendar, linking,
deletion, notifications) read step flags instead of hardcoded status values.

## Architecture

Declared in code, assigned per model, governed by flags:

- **`Step`** : `code`, translatable `label`, UI `tone` (badge colour), `kind`
  (`StepKind.DRAFT` - the single entry; `StepKind.INTERMEDIATE`; `StepKind.ARCHIVED`
  - the detached exit shown on the stepper's single line but separated by a gap with
  no connector to the main flow), and the governance flags:
  - `counts_in_reports` - included in reports, KPIs, the calendar and exports;
  - `linkable` - may be targeted by a new link;
  - `deletable` - may be deleted.
- **`Transition`** : `target`, `source` (a specific step or `ANY`), translatable
  `label`, `permission_action` (permission action suffix, resolved against the
  entity's `module.feature` namespace) and `requires_comment`.
- **`Lifecycle`** : name + steps + transitions + `layout` (`line` / `graph`);
  invariants validated at construction (exactly one Draft, at least one Archived).
  Every performed transition is recorded as an immutable `core.models.LifecycleEvent`
  (actor, from, to, comment, form data, timestamp).
- **Registry** : `register_lifecycle(lifecycle)` populates the name -> lifecycle map.
  Specific lifecycles are registered from each app's `AppConfig.ready()`
  (`assets/lifecycles.py`, `compliance/lifecycles.py`, `risks/lifecycles.py`,
  `reports/lifecycles.py`, `trust_center/lifecycles.py`, `context/lifecycles.py`).
- **Assignment** : the model's `LIFECYCLE_NAME` class attribute names its lifecycle;
  a model that declares none runs the **default lifecycle**. `resolve_lifecycle(model)`
  never returns `None`.

Model API (`context.models.base.BaseModel`): `workflow_state` field (indexed),
`get_lifecycle()`, `lifecycle_label`, `lifecycle_tone`, the governance properties
(`counts_in_reports`, `is_linkable`, `is_deletable`, `is_terminal_state`),
`available_transitions(user)`, `transition_to(target, user, comment=..., enforce_permission=...)`
and a `workflow_perm_namespace` property (overridden where the permission feature
differs from the model name, e.g. `compliance.action_plan`). A new-element save
snaps `workflow_state` to the lifecycle's initial step. Models with a domain status
enum (Risk, Objective, ...) mix in `LegacyStatusMixin`, which aliases `obj.status`
and `obj.get_status_display()` onto `workflow_state`.

Queryset helpers (`core.lifecycle`): `reportable(qs)`, `linkable(qs)`,
`linkable_or_linked(qs, linked_qs)` plus the state-set functions (`reportable_states`,
`linkable_states`, `deletable_states`). All no-op for models without a lifecycle
(plain child models).

## The default lifecycle (`default`)

Applies to every model without a specific lifecycle.

| Step | In reports | Linkable | Deletable | Kind |
|---|---|---|---|---|
| `draft` (initial) | no | no | **yes** | draft |
| `pending` | no | no | no | intermediate |
| `validated` | **yes** | **yes** | no | intermediate |
| `archived` | no | no | no | archived |

| Verb | Transition | Permission | Effect |
|---|---|---|---|
| Submit | draft -> pending | `.update` | notify owner |
| Send back to draft | pending -> draft | `.update` | - |
| Validate | pending -> validated | `.approve` | element counts in reports |
| Archive | validated -> archived | `.approve` | - |

Validation is no longer a separate boolean: an element is "approved" exactly when
it sits on a step that `counts_in_reports` (here, `validated`), reached through the
permission-gated transition. There is no approval reset or version-on-major-field
machinery.

## Specific lifecycles

The registered specific lifecycles preserve the operational semantics that the
4-step default does not cover. Step codes equal the historical status values, so no
`workflow_state` data migration was needed.

| Lifecycle | Model | Highlights |
|---|---|---|
| `action_plan` | compliance.ComplianceActionPlan | 8 steps; refusals require a comment; per-step permissions (`update`, `validate`, `implement`, `close`, `cancel`); `to_implement` / `implementation_to_validate` / `validated` linkable; `new` / `to_define` deletable; transitions logged in `ActionPlanTransition` |
| `compliance_assessment` | compliance.ComplianceAssessment | only `draft` deletable; `cancelled` leaves reports / the calendar; EVALUATED-results reset on completion preserved |
| `management_review` | reports.ManagementReview | closure (`held -> closed`) carries `.approve`; cancellation requires a comment; `can_close()` preconditions and the closure snapshot preserved |
| `essential_asset` / `support_asset` | assets | natural ITAM progressions; decommissioned / disposed not linkable (RS-04) and not deletable; every step stays reportable (audit history) |
| `risk` | risks.Risk | `identified` is the draft analog (not in the register, not linkable); monitoring -> analysis review loop; `closed` terminal but reportable |
| `risk_treatment_plan` | risks.RiskTreatmentPlan | automated overdue flip preserved; `cancelled` leaves reports |
| `risk_acceptance` | risks.RiskAcceptance | renewal cycle; `revoked` terminal; every step reportable (audit trail) |
| `vulnerability` | risks.Vulnerability | direct false-positive closure |
| `risk_assessment` | risks.RiskAssessment | rework loop from `completed`; `validated_by` stamp on validation |
| `ebios_workshop` | risks (EBIOS) | review verdicts; rejection requires a comment; rework loop |
| `ebios_study_framework`, `ebios_security_baseline`, `ebios_summary`, `ebios_baseline_gap`, `ebios_pacs_measure` | risks (EBIOS) | natural deliverable progressions |
| `scope` / `site` | context | perimeter / location flows on the directed-graph layout; `in_force` + `review` (scope) and `operational` + `review` (site) count in reports |
| `publication` / `document_request` | trust_center | publishing gated by the trust-center permission |

Decisions recorded during the rollout:

- **Binary toggles** (Stakeholder, Role, Activity, AssetGroup, Threat, Indicator) and
  **outcome trackers** (Objective, Issue, StakeholderFeedback) keep their `status` as a
  non-governing operational attribute over the default lifecycle. A toggle has no
  terminal step, so it is not a lifecycle.
- **Publication statuses retired**: Scope, Site, SwotAnalysis and RiskCriteria lost
  their legacy `status` field entirely. Framework and Requirement keep `status` as a
  versioning attribute (`under_review` / `deprecated` / `superseded` carry semantics
  the lifecycle does not).

## Governance rules (as built)

- **RG-LC-01** : an element whose step has `counts_in_reports = false` is excluded
  from generated reports (SoA, risk register), computed KPI rates, the compliance
  donut and the calendar. Dashboard inventory count tiles deliberately stay full
  (product decision: counts are a working inventory). Assessment-scoped documents
  (audit report, ISO 27005, management review exports) keep the full content of the
  explicitly chosen assessment.
- **RG-LC-03 / RG-LC-04 (target-side linking)** : a new link may only target a
  `linkable` element; already-linked elements stay selectable so an edit never drops
  an existing link; an element in a terminal step cannot gain new links; unlinking
  is always allowed. Authoring links *from* a draft element is allowed by design.
- **RG-LC-05** : deletion is blocked at the model level (`BaseModel.delete()` raises
  `LifecycleProtectedError`) unless the step is `deletable`. Cascade and bulk
  deletes bypass it by design.
- **RG-LC-06 / RG-LC-09 (notifications)** : transitions that notify (Submit on the
  default lifecycle) notify, in fallback order: the element's own `managers`
  (scope-like containers), the managers of its scopes, the holders of the entity's
  `.approve` permission, then the creator. The actor and inactive users are never
  notified. Delivery: in-app `accounts.Notification` rows (rendered in the
  recipient's language) + email on `transaction.on_commit` (per-user
  `email_notifications` opt-out) + a per-user WebSocket badge push
  (`/ws/notifications/`).
- **RG-LC-07** : each transition requires its declared permission action, resolved
  against the entity's `module.feature` namespace.

## Surfaces

- **REST** : `GET /api/v1/<entity>/<pk>/transition/` lists the caller's permitted
  transitions; `POST` performs one (`target_state`, optional `comment`). Lifecycle
  lists accept `?workflow_state=a,b`. Provided by `accounts.api.mixins.LifecycleAPIMixin`;
  the bespoke transition endpoints (assessment required-fields gating, action plan,
  management review closure) keep their extra side effects and shadow the generic
  action.
- **MCP** : `transition_<entity>(id, target_state, comment)` and
  `<entity>_allowed_transitions(id)` for every CRUD entity. Link tools enforce the
  linking rules with explicit error lists. Domain approvals that are real lifecycle
  actions keep dedicated tools (`approve_trust_center_document_request`,
  `reject_trust_center_document_request`).
- **UI** : every detail page renders the generic stepper
  (`includes/lifecycle_stepper.html`, context built by
  `accounts.mixins.LifecycleStepperMixin`) - a single centred line drawn directly on
  the page background (no card) holding the main flow pills and the archived off-ramp
  (detached, no connector); cyclic lifecycles use the directed-graph layout. Both the
  forward next step and an allowed backward move are **clickable pills**, with the
  shared comment modal gated by each transition's `requires_comment`. Transitions post
  to `workflow:transition` (`/workflow/<app>/<model>/<pk>/transition/`, validated-referer
  redirect) or to the entity's bespoke endpoint (`lifecycle_transition_url_name`).
  State badges render via `{% workflow_badge obj %}` (`helpers.templatetags.workflow_tags`).

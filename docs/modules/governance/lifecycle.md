# Lifecycles (standardised)

> Status: **architecture / foundation**. The engine, the event log and the
> service exist and are tested; entities are migrated onto it incrementally
> (Suppliers first). The legacy `core/workflow.py` engine still runs the
> not-yet-migrated entities and the two coexist during the transition.

Every domain element moves through a **lifecycle**: a declarative *schema* of
**steps** (étapes) and the **transitions** between them. This is the single,
standard way state is modelled, replacing the previous per-entity status fields
and the first-generation workflow engine.

## The contract

1. **Mandatory bookend steps.** Every lifecycle has exactly one **Draft** step
   (the single entry point) and at least one **Archived** step (the exit). What
   sits between is entity-specific.
2. **Linear or cyclic.** The transition graph is free-form: a straight line, a
   cycle, or a line with an exit. Returning to an earlier step (rework,
   reactivation) and leaving Archived (restore) are both allowed.
3. **Free or constrained transitions.** A transition declares a specific
   `source` step, or `ANY` ("from any state") - e.g. *any → Archived* while
   *Draft → Validated* is only legal via the explicit path.
4. **Form per transition.** A transition may require a Django `Form`; its
   cleaned data is recorded with the transition.
5. **Role / people restriction.** A transition may be restricted to ISO 27001
   roles (by `RoleType`) and/or to named users resolved from the instance.
6. **Full history.** Every performed transition is recorded as an immutable
   `LifecycleEvent` (actor, from, to, comment, form data, timestamp).

## Architecture

Three layers, deliberately separated so the schema stays pure and testable:

### 1. Schema and engine - `core/lifecycle.py` (no model imports)

- **`StepKind`** : `DRAFT`, `INTERMEDIATE`, `ARCHIVED`.
- **`Step`** : `code`, translatable `label`, `kind`, the governance flags
  (`counts_in_reports`, `linkable`, `deletable`) and a UI `tone`. Helpers
  `draft_step()` / `archived_step()` build the canonical bookends.
- **`Transition`** : `target`, `source` (a step code or `ANY`), `label`,
  `form_class` (a Django `Form` class or its dotted path), `allowed_roles`
  (a tuple of `RoleType`), `allowed_users` (a callable `(instance) → iterable`),
  `requires_comment`. `from_any`, `is_restricted` and `get_form_class()` are
  derived.
- **`Lifecycle`** : ordered steps + transitions. Validates the invariants
  (unique codes, exactly one Draft, ≥ one Archived, transition endpoints exist
  or are `ANY`). Exposes `initial_step`, `transitions_from(code)` (specific
  source + wildcards, self-target excluded), `find_transition(source, target)`
  (explicit wins over wildcard) and the governance code sets.
- **Registry** : `register_lifecycle()` / `get_lifecycle()` / `LIFECYCLE_REGISTRY`.
- **Evaluation** : `user_can_perform(transition, instance, user)` (open ⇒ anyone;
  superuser bypass; ISO role assignment **scoped to the instance**; or the
  resolved allowed users), `available_transitions(...)` and `validate_transition(...)`
  (raises `UnknownStepError` / `IllegalTransitionError` /
  `TransitionNotAllowedError` / `CommentRequiredError`).

### 2. History - `core.models.LifecycleEvent`

A generic (content-type) append-only log: `content_type` + `object_id` (char, so
both UUID and integer PKs work), `lifecycle_name`, `from_step`, `to_step`,
`actor`, `comment`, `form_data` (JSON), `created_at`. `LifecycleEvent.record(...)`
appends one; `LifecycleEvent.for_instance(obj)` returns an instance's timeline.

### 3. Service - `core/lifecycle_service.py` (ties engine to the DB)

`perform_transition(instance, target, *, user, comment, data, files, lifecycle,
step_field="workflow_state", enforce_permission, save)` is the single funnel for
every layer (web, DRF, MCP): it reads the current step from the instance,
validates the move (legality, role/user restriction, required comment),
validates the per-transition form when one is declared, writes the new step,
persists, and appends the `LifecycleEvent`. Returns `(event, transition)`.

## Restriction model

Restriction is **by ISO 27001 role and/or named user**, not by Django
permission (a deliberate departure from the legacy engine). `allowed_roles`
lists `RoleType` categories; a user passes if assigned to a `context.Role` of
one of those types **that shares a scope with the instance** (a role's authority
is bounded by its scopes). `allowed_users` is a callable resolved against the
instance for dynamic people (e.g. `lambda obj: [obj.owner]`). An unrestricted
transition is open to anyone with access; superusers always pass.

> Binding a transition to a *specific* named role (e.g. exactly "CISO" rather
> than any Governance role) is the planned next extension point - a small DB
> mapping from `(lifecycle, transition)` to concrete `Role` rows - layered on
> top of the `RoleType` mechanism without changing the schema API.

## Migration plan (incremental)

1. Foundation: engine + `LifecycleEvent` + service + tests. **Done.**
2. Per-entity lifecycle definitions registered in each app. **Supplier and
   Scope done.** Supplier (`assets/lifecycles.py`): the audit-proof
   supplier-risk lifecycle - Draft → Onboarding → Risk questionnaire →
   Evaluation → Compliant / Non-compliant, cycling, with Archived as the exit.
   Scope (`context/lifecycles.py`): the perimeter governance lifecycle - Draft →
   Definition → Validation → In force → Review (periodic, looping back to In
   force), with Archived as the from-any exit (and restore to Draft); `in_force`
   and `review` count in reports and are linkable.
   `BaseModel` routes governance / transitions / history through the new engine
   whenever a model sets `LIFECYCLE_NAME` (`Supplier.LIFECYCLE_NAME = "supplier"`,
   `Scope.LIFECYCLE_NAME = "scope"`).
3. Stepper UI reads through `LifecycleStepperMixin` +
   `includes/lifecycle_stepper.html` (main flow as a connected wrapping line,
   available transition targets clickable, the Archived exit detached). DRF and
   MCP perform through the service. **Stepper done. DRF/MCP done**: the generic
   `transition_<entity>` / `<entity>_allowed_transitions` MCP tools and the
   `WorkflowTransitionView` endpoint branch on `get_lifecycle()` and route
   standardised-engine entities through `transition_to` / `available_transitions`.
4. Reports / KPIs / linking / deletion read the governance code sets from the
   resolved lifecycle. **Done**: `reportable()` / `linkable()` /
   `deletable_states()`, the list summary rail and the unified history timeline
   resolve a model's code set off its lifecycle when it sets `LIFECYCLE_NAME`,
   falling back to the legacy workflow otherwise.
5. Retire `core/workflow.py` once every entity is migrated.

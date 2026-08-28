# IncidentResponseAction

`incidents.models.response_action.IncidentResponseAction`

One operational step taken **during** an [Incident](incident.md) : isolate the host, revoke the token, block the sender, restore from backup, wake the on-call, pull the logs before they rotate. ISO/IEC 27001:2022 A.5.26 (response to information security incidents) and the response phase of the ISO/IEC 27035 cycle.

File : `incidents/models/response_action.py`

A `ReferenceGeneratorMixin` subclass on a plain `models.Model` : own UUID primary key, an auto-generated `IRAC-N` reference, explicit row timestamps, a `version` counter and a `django-simple-history` audit trail. It is **not** a `BaseModel`, it is **not** a `ScopedModel`, and it carries a plain `status` column rather than a lifecycle. That last choice is in tension with a standing project rule and is argued out in full below, because it must be a decision on the record and not a silent shortcut.

## What this entity is not

**Not a `ComplianceActionPlan`.** Post-incident **corrective** actions under ISO 27001 clause 10.2 are `compliance.ComplianceActionPlan` rows, linked from [PostIncidentReview](post-incident-review.md) through `corrective_action_plans` (RG-INC-35). Those reuse the existing eight-step approval lifecycle, its owner and assignees, its target date, progress, cost estimate, cancellation rules and its `ActionPlanTransition` audit rows. They live for weeks and they deserve every one of those gates.

An in-incident containment step lives for twenty minutes. Running it through an eight-step approval workflow designed for audit-gap remediation would be absurd, and worse, an action parked below a reportable step would be excluded from reports for the whole duration of the incident, which is exactly the window in which somebody needs to see it. The two objects are kept apart on purpose, and the split is the single most important thing to understand about this entity : **during** the incident it is an `IncidentResponseAction`; **because of** the incident it is a `ComplianceActionPlan`.

**Not a timeline entry.** [IncidentTimelineEntry](incident-timeline-entry.md) narrates what happened, append-only and never edited. An `IncidentResponseAction` is a tracked unit of work with an owner, a deadline and a completion state, and it is edited as it progresses. An action that is executed normally produces one or more timeline entries pointing back at it through `related_action`.

## Decision : a plain status column instead of a lifecycle

`CLAUDE.md` states that lifecycles govern every domain element : all `BaseModel` subclasses run a registered lifecycle, and new entities with operational stages get a specific lifecycle generated from their transition constants. This entity does not, and that is a deliberate, argued deviation rather than an oversight. It was raised as an open question in the design and is recorded here as a decision **the maintainer must confirm before merge**.

### The argument for the deviation

1. **It is a child row, not a domain element.** It has no independent existence, no list page of its own, no filter set of its own, no detail page and no scope. It is created, worked and completed entirely inside one incident's detail page, and it is meaningless detached from its parent. The doctrine governs domain elements : things a user navigates to, reports on, links from elsewhere and archives. This is none of those.
2. **Its parent already carries the governance.** The [Incident](incident.md) runs the `incident` lifecycle with eleven steps, permission-gated transitions, mandatory comments and a confirm-gated closure. The response actions follow their parent : they are created after triage, they are expected complete before the incident can be contained or closed, and their governance is the incident's governance.
3. **The tempo is wrong for a workflow.** A lifecycle transition costs a permission check, a `LifecycleEvent` row, a possible comment modal and a page interaction. A responder marking four containment steps done in ninety seconds should not pay that four times, and any approval step inserted into that path manufactures delay in the exact window where delay is the harm.
4. **Nothing outside the incident links to it.** `linkable()` exists so that pickers elsewhere in the platform do not offer half-finished objects. Nothing outside the incident detail page ever picks a response action, so there is nothing for `linkable()` to protect.

### The consequences, stated plainly

The deviation is not free. Everything below is a real capability given up :

- **Invisible to the governance helpers.** `reportable()`, `linkable()`, `linkable_or_linked()` and `deletable_states()` all read a lifecycle. A response action answers none of them. Any report, KPI, kanban bucket or picker that needs to reason about response actions must filter on `status` explicitly, using the `ResponseActionStatus` constants and never a bare string literal (RG-INC-37 forbids state literals outside `incidents/constants.py`, and that prohibition covers this enum as much as it covers the lifecycle step codes).
- **No per-state governance.** There is no way to say "a containment step may only be closed by someone holding `approve`", no `requires_comment` on a status change, no `permission_action` per step. Every status change costs the same `incidents.incident.update`.
- **No `LifecycleEvent` row per change.** A status change leaves a `HistoricalRecords` row and nothing else. The account of who moved a step and why lives in the field diff and, when a responder wrote one, in the chronology; it is not in the lifecycle history where an auditor looks first.
- **Deletable at any status.** `BaseModel.delete()`'s state guard does not apply, so deletion is gated by permission alone (`incidents.incident.delete`) rather than by state. A `done` action can be deleted where a validated `BaseModel` could not. `HistoricalRecords` records the deletion.
- **A migration is owed if this is ever revisited.** If the organisation later decides that containment steps must be approved, or that a response action must be excluded from reports until validated, converting this to a `BaseModel` means adding `workflow_state`, `created_by`, tags and the `BaseModel` timestamps, backfilling `workflow_state` from `status` for every existing row, registering an `incident_response_action` lifecycle and reworking the six-feature permission cap in RG-INC-39. That is a real migration on a live table, and it is the price of this decision being wrong.

### The decision

Phase 1 ships the plain `status` column, on the reading that a child row worked inside its parent's page is not a domain element in the sense the doctrine means. **If the maintainer reads the doctrine as covering every persisted model without exception, this entity becomes a `BaseModel` with a registered `incident_response_action` lifecycle before merge, not after** : converting later costs the data migration described above. RG-INC-35 records the decision in the module's business rules so it is discoverable from the register rather than only from this file.

Note one genuine, if small, benefit of the plain column, worth stating because it cuts the other way from every point above : `status` is a plain field choice, so its labels never make the `post_migrate` round trip through `LifecycleDefinition`. Step labels do, and `lifecycle_from_json` re-wraps them with bare `gettext_lazy`, silently dropping any `msgctxt` a label carried in code. A plain column's labels keep their translation context.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, `default=uuid.uuid4`, `editable=False` | Unique identifier. `ReferenceGeneratorMixin` supplies only the `reference` field, so the PK is declared here. |
| `reference` | string | auto-generated `IRAC-N`, unique, max 50 | Citable identifier for the incident file and for regulatory correspondence ("containment step IRAC-42"). The full-table max scan `_generate_next_reference()` performs on insert is acceptable here : actions are counted in tens per incident, not hundreds, and each one is a deliberate human act. |
| `incident` | relation | FK -> [Incident](incident.md), required, `CASCADE`, `related_name="response_actions"` | The incident this step belongs to. |
| `action_type` | enum | required | Which ISO 27035 response step this action belongs to. See [Enums](#enums). |
| `title` | string | required, max 255 | What is being done, in the imperative : `Isolate WEB-PRD-02 from the network`. |
| `description` | text | optional, blank default | Detail and instructions : the command to run, the runbook section, the person to call. |
| `status` | enum | required, default `planned` | Operational progress. **A plain status column, not `workflow_state`** : this model runs no lifecycle and follows its parent. See [the decision](#decision--a-plain-status-column-instead-of-a-lifecycle). |
| `owner` | relation | FK -> User, optional, `SET_NULL`, `related_name="incident_response_actions"` | Who is accountable for the step being done. |
| `performed_by` | relation | FK -> User, optional, `SET_NULL`, `related_name="performed_incident_response_actions"` | Who actually executed it, when that differs from the owner. |
| `due_at` | datetime | optional, indexed | When it must be done by. Drives the SLA escalation sweep (RG-INC-40) and the overdue styling on the incident page. |
| `started_at` | datetime | optional | Execution start. |
| `completed_at` | datetime | optional; required when `status = done` | Execution end. Together with `started_at` this is the raw material for the mean-time-to-contain indicator. |
| `outcome` | text | optional, blank default; **required non-blank when `status = done`** (DB `CheckConstraint` + `clean()`) | What the action actually achieved. A containment step marked done with no stated outcome is not evidence of containment. |
| `effectiveness` | enum | required, default `not_assessed` | Whether the step worked, assessed during the post-incident review. Reuses `compliance.constants.EffectivenessVerdict`, introduced in phase 0. Feeds A.5.27. |
| `version` | int | `PositiveIntegerField`, default `1` | Row version counter, mirroring the `SupplierSubprocessor` precedent for non-`BaseModel` child rows. |
| `created_at` / `updated_at` | datetime | `auto_now_add` / `auto_now` | Row timestamps. Declared explicitly because `BaseModel` is not inherited. |
| `history` | `HistoricalRecords()` | | Audit trail : the only per-change record this entity has, since it emits no `LifecycleEvent`. |

There is deliberately no `created_by` field : `owner` and `performed_by` already name the accountable and the executing person, and `HistoricalRecords` records the creating user on the first historical row. Adding a third people field would invite the three to disagree.

`Meta.ordering = ["incident", "due_at", "reference"]`, so an incident's actions read in deadline order with a stable tie-break. `Meta.constraints` carries `response_action_done_has_outcome` : `Q(status="done") & ~Q(outcome="")` or `~Q(status="done")`.

## Enums

Reproduced verbatim from `incidents/constants.py` (DB value = Label).

`ResponseActionType` :

| Value | Label |
|---|---|
| `containment` | Containment |
| `eradication` | Eradication |
| `recovery` | Recovery |
| `evidence_collection` | Evidence collection |
| `communication` | Communication |
| `escalation` | Escalation |
| `workaround` | Workaround |
| `other` | Other |

`ResponseActionStatus` :

| Value | Label |
|---|---|
| `planned` | Planned |
| `in_progress` | In progress |
| `done` | Done |
| `blocked` | Blocked |
| `cancelled` | Cancelled |

`effectiveness` reuses `compliance.constants.EffectivenessVerdict` (`effective` = Effective, `partially_effective` = Partially effective, `ineffective` = Ineffective, `too_early` = Too early to assess, `not_assessed` = Not assessed), introduced by the phase-0 `compliance.Finding` generalisation. It is **imported**, never redeclared : a second copy would drift within a release and would also duplicate five `msgid` values in the translation catalogue.

## Creation, defaults and initial state

Because this entity runs no lifecycle, `Lifecycle.initial_step` and `BaseModel._ensure_initial_step()` never touch it, and a row genuinely is created in `status = planned` (or in whatever status the caller passes). That is worth stating precisely, because it is **not** true of the module's lifecycle-bearing entities and the difference is a frequent source of wrong code :

- For any `BaseModel` in this module, `_ensure_initial_step()` fires only on a blank or unknown `workflow_state`, so every ordinary insert lands in `draft`; an explicitly assigned domain step would stick, but it would leave **no `core.LifecycleEvent` row**, which is why the pattern is banned. A row cannot be created directly in a domain step. Auto-creation paths must `save()` the row and then call `transition_to("<step>", user, enforce_permission=False)` inside the same transaction. This applies to the [IncidentNotification](incident-notification.md) obligations instantiated at triage and to the [PostIncidentReview](post-incident-review.md) created when an incident enters the review phase.
- For `IncidentResponseAction`, there is no lifecycle and therefore no snapping : the plain field default applies on insert exactly as written.

Response actions are created by hand from the incident detail page, in bulk through the API or MCP batch endpoints when a runbook is being instantiated, or by an integration. Nothing in phase 1 auto-generates them from a template; the [IncidentResponsePlan](incident-response-plan.md) documents the procedure in prose rather than as a machine-executable checklist, and turning that prose into generated actions is deliberately out of scope.

## Mutability and audit trail

This row is **deliberately mutable**. Its whole purpose is to move from `planned` to `in_progress` to `done` while the incident is live, and every one of those writes goes through `save()` and leaves a `HistoricalRecords` row with the acting user. No immutability of any kind is claimed for it.

That matters because two of its neighbours *do* claim an append-only guarantee, and the module is careful about how strong that claim is. [IncidentTimelineEntry](incident-timeline-entry.md) and [EvidenceCustodyEvent](evidence-custody-event.md) refuse updates and deletions in `save()` and `delete()` by raising `LifecycleProtectedError`. That is **prevention at application level, and detection via `HistoricalRecords`** : `QuerySet.update()`, `bulk_update()`, cascade deletion, raw SQL and a `manage.py shell` session all bypass the Python guards, and what catches them afterwards is the historical trail, not the schema. The module says "append-only, enforced in Python and detectable in history", never "immutable". The same honest framing governs anything anyone might be tempted to assert about a completed response action : a `done` action with a stated outcome is a durable record only in the sense that changing it leaves a historical row naming who changed it.

Three trails describe an incident, and they are not interchangeable. This entity's place in them :

| Trail | What it holds about a response action | Authoritative for |
|---|---|---|
| `core.LifecycleEvent` | Nothing. The entity emits no transitions. | The parent incident's process only : which state the incident was in when the action was created, worked and completed, and who moved it. |
| `HistoricalRecords` | Everything : a full row snapshot per `save()`, with the acting user, covering every `status`, `outcome`, `owner` and `due_at` change. | The data. When the action was marked done, by whom, and with what outcome text at that moment. This is the only per-change record this entity has, and it is what an auditor is pointed at. |
| `IncidentTimelineEntry` | The narrative entries that reference it through `related_action`. | The facts. What the responder actually observed when executing the step, in real-world order. An action row says "containment done at 10:47"; the chronology says what containment looked like. |

Reconciling the three at audit time is real work and the module does not pretend otherwise. The rule of thumb : ask `LifecycleEvent` about **state**, `HistoricalRecords` about **field values**, and the chronology about **the world**. When a response action's history shows a `done` transition with no corresponding timeline entry, the action was completed without being narrated : that is legal, common under pressure, and worth flagging in the post-incident review rather than treating as corruption.

## Scope and tenancy

RG-INC-38. `IncidentResponseAction` is not a `ScopedModel`. It inherits the parent incident's scope through `scope_parent_lookup = "incident__scopes"` so it cannot drift when the incident is re-scoped.

Making that inheritance real requires the same three core call sites the rest of the module's child rows need, because scope inheritance for non-`ScopedModel` children is **not** currently enforced there :

- `mcp/tools.py` `_filter_by_scopes()` handles `context.Scope` and a direct `scopes` M2M and then returns the queryset unfiltered, with no `scope_parent_lookup` equivalent. Phase 1 extends it with a `parent_lookup` argument and threads a `scope_parent_lookup` through `_register_crud` / `_list_handler` / `_get_handler`. Registering this entity's tools with `scope_filtered=False` would leak every response action on the instance to any holder of `incidents.incident.read`, so the registration passes `scope_parent_lookup="incident__scopes"` instead.
- `core/workflow_views.py` guards with `hasattr(obj, "scopes")`. This entity exposes no transition endpoint, but the guard is extended for its lifecycle-bearing siblings in the same change.
- `core/history_views.py` carries the same `hasattr(obj, "scopes")` guard, so without the fix a response action's full history is readable cross-scope.

These are core changes in the phase-1 PR, not incidents-app details, and they are logged under a `### Security` entry in `CHANGELOG.md`.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-35 | Corrective work is recorded exclusively as `compliance.ComplianceActionPlan` rows linked from `PostIncidentReview.corrective_action_plans`. `IncidentResponseAction` exists ONLY for in-incident operational steps and carries a plain status column, never a lifecycle. |
| RG-INC-37 | Every report, KPI, indicator, calendar feed, kanban bucket and link picker filters through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. No state literal appears anywhere outside `incidents/constants.py`. Response actions answer none of those helpers, so any surface reasoning about them filters on the `ResponseActionStatus` constants explicitly. |
| RG-INC-38 | Scope tenancy : response actions are never independently scoped and inherit the incident's scope through `scope_parent_lookup="incident__scopes"` on the web, API and MCP surfaces. |
| RG-INC-40 | The daily `escalate_incident_deadlines` command sweeps overdue `IncidentResponseAction` rows alongside unfiled notification obligations and stalled incidents. It takes `--dry-run`, uses `timezone.localdate()`, excludes terminal statuses, and iterates with a per-row `save()` (never `.update()`) so `HistoricalRecords` captures every change. |

Two constraints local to this entity complete the set : `outcome` must be non-blank when `status = done` (DB `CheckConstraint` `response_action_done_has_outcome`, plus `clean()` so the form and serializer report it as a field error rather than an integrity error), and `completed_at` is required when `status = done`.

## Endpoints

### REST

Base path `/api/v1/incidents/`, router registration `response-actions`. Full CRUD, no `transition/` route.

- `GET /api/v1/incidents/response-actions/` : list, filters `incident`, `action_type`, `status`, `owner`, `overdue` (method filter deriving `due_at < now` and `status` not in `done` / `cancelled`), `due_before`.
- `POST /api/v1/incidents/response-actions/` (+ `POST .../batch/` via `BatchCreateMixin`, max 100 items, non-atomic, per-item `{index, status, id, reference}`).
- `GET/PUT/PATCH/DELETE /api/v1/incidents/response-actions/<uuid>/`.
- `GET /api/v1/incidents/response-actions/<uuid>/history/` via `HistoryAPIMixin`.

Viewset stack : `BatchCreateMixin`, `ScopeFilterAPIMixin` (with `scope_parent_lookup = "incident__scopes"`), `HistoryAPIMixin`, `CreatedByMixin`, `viewsets.ModelViewSet`. `LifecycleAPIMixin` is **not** mixed in : the entity runs no lifecycle, so there is no transition action and no `status` field sourced from `workflow_state`. Here `status` is a genuine model field and is writable, which is the one place in the module where a writable `status` is correct rather than a bug. Permissions use `ModulePermission` with `permission_module = "incidents"` and an explicit `permission_feature`, following the newest module precedent (`trust_center/api/views.py`). `id`, `reference`, `created_at`, `updated_at` and `version` are read-only.

### MCP

Registered through `_register_crud(server, "incident_response_action", IncidentResponseAction, "incidents.incident", has_approve=False, scope_parent_lookup="incident__scopes", ...)`, which generates :

- `list_incident_response_actions` (filters `incident_id`, `action_type`, `status`, `owner_id`), `get_incident_response_action`, `create_incident_response_action`, `batch_create_incident_response_actions`, `update_incident_response_action`, `delete_incident_response_action`, `get_incident_response_action_history`.

No `transition_incident_response_action` and no `incident_response_action_allowed_transitions` tool is generated : the child row runs no lifecycle. `action_type`, `status` and `effectiveness` carry explicit `enum` lists in `field_overrides`; every user FK id carries a description naming its lookup tool. `mcp/tools.py` `HELP_TEXT` gains `IncidentResponseAction=IRAC` in the reference-prefix block, and the entity gets its Writable / enum values / Filters / Ref prefix section in the new `TOPIC_INCIDENTS` help topic.

## Permissions

Gated by the parent incident's codenames, with no separate feature :

| Codename | Covers |
|---|---|
| `incidents.incident.read` | List and read response actions |
| `incidents.incident.create` | Create a response action |
| `incidents.incident.update` | Edit a response action, including every status change |
| `incidents.incident.delete` | Delete a response action |

`incidents.incident.approve` is not consumed by this entity : there is no approval step, which is precisely the consequence recorded in [the decision](#decision--a-plain-status-column-instead-of-a-lifecycle). RG-INC-39 caps the module at exactly six features (`incident`, `security_event`, `evidence`, `notification`, `review`, `response_plan`) with the five standard actions each, so no `incidents.response_action` feature exists or will.

## UI

Rendered as the **Response actions** card in the left column of the incident detail page (strict 2-column layout, no nav-tabs) :

- A typed table : reference, action type icon, title, owner avatar, due date, status pill.
- Status pills use the platform's semantic tones and nothing else : `planned` neutral, `in_progress` info, `done` success, `blocked` warning, `cancelled` muted. Semantic colour is reserved for status, per the brand guidelines; the single navy identity colour is not repurposed here.
- A row whose `due_at` is past and whose status is neither `done` nor `cancelled` renders in the overdue state, matching the notification deadline treatment so "late" looks the same everywhere on the page.
- An inline **Add action** form at the foot of the card posts over HTMX into the `#response-actions` partial, so a responder never leaves the incident page. Editing a row and changing a status both happen in place through the same partial : a status change is one click, never a modal, never a workflow stepper.
- Marking an action `done` reveals the `outcome` field as required in the same inline form, so the constraint is met at the moment of completion rather than reported as an error afterwards.
- `effectiveness` is hidden during the incident and only rendered once the incident reaches the post-incident review phase, where the review facilitator assesses each action.
- Completing an action offers, but does not force, appending a matching [IncidentTimelineEntry](incident-timeline-entry.md) prefilled from the action's title and outcome, with `related_action` set. Forcing it would make responders type twice; offering it is what keeps the chronology complete.

Bootstrap Icons only, correct rendering in light and dark mode, and explicit care on mobile widths where the typed table collapses to stacked rows.

## Translations

Every user-facing string is wrapped and given a French translation in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `manage.py compilemessages` fail, and CI runs `compilemessages` **before** `pytest`, so a collision breaks the build rather than the page.

The colliding labels declared by this entity are **Planned**, **In progress**, **Done**, **Cancelled** and **Other** : all five already exist in the catalogue, several of them more than once. They are declared with `pgettext_lazy("incident", ...)` in `incidents/constants.py` and rendered with `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po` file. `Containment`, `Eradication`, `Recovery`, `Evidence collection`, `Communication`, `Escalation`, `Workaround` and `Blocked` are new `msgid` values and are added bare. The `EffectivenessVerdict` labels are imported from `compliance.constants` and are therefore already translated : redeclaring them here would duplicate five entries.

The `lifecycle_from_json` trap does not reach this entity. Step labels stored in a `LifecycleDefinition` row are re-wrapped with bare `gettext_lazy` when the definition is read back after `post_migrate`, which silently drops any `msgctxt` the label carried in code and resolves it to the wrong French string. `status` here is a plain field choice that never makes that round trip, so its `pgettext_lazy("incident", ...)` context survives. The trap does apply to every lifecycle-bearing entity in the module : see [Incident](incident.md), [SecurityEvent](security-event.md), [IncidentEvidence](incident-evidence.md), [IncidentNotification](incident-notification.md) and [PostIncidentReview](post-incident-review.md), whose step labels include the colliding `Draft`, `Closed`, `Archived`, `Approved`, `Required`, `Confirmed`, `Retained`, `In progress` and `Cancelled`.

## References

- ISO/IEC 27001:2022 A.5.26 (response to information security incidents) : incidents shall be responded to in accordance with the documented procedures.
- ISO/IEC 27035-1 and 27035-2 : the response phase, and containment / eradication / recovery as distinct acts.
- ISO/IEC 27001:2022 clause 10.2 : the corrective actions that follow an incident, which are `ComplianceActionPlan` rows and not this entity.
- [Incident](incident.md) : the parent, its lifecycle and the governance this entity borrows.
- [IncidentTimelineEntry](incident-timeline-entry.md) : the append-only chronology, the `related_action` back-reference and the full three-trail reconciliation table.
- [PostIncidentReview](post-incident-review.md) : where `effectiveness` is assessed and where corrective `ComplianceActionPlan` rows are linked.
- [IncidentResponsePlan](incident-response-plan.md) : the documented procedure these steps execute.
- [README.md](README.md) : module business rules, permission codenames, scope inheritance and the phase plan.
- [governance/workflow.md](../governance/workflow.md) : the lifecycle doctrine this entity deviates from, and the terms `reportable()` / `linkable()` / `deletable_states()`.

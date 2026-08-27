# IncidentResponsePlan

`incidents.models.response_plan.IncidentResponsePlan`

The documented incident management procedure of record : ISO/IEC 27001:2022 **A.5.24 (information security incident management planning and preparation)**. It holds the reporting channels, the classification scale, the escalation matrix, the evidence procedure, the lessons-learned procedure and the regulatory regimes the organisation has decided it is subject to.

Every [Incident](incident.md) points at the plan it was handled under through a `PROTECT` foreign key. That single link is what makes a two-year-old incident file readable at audit time : *this is the procedure that was in force when we handled it*. It is also the clause 7.5.3 (control of documented information) answer that a module built around a bare incident table cannot give.

File: `incidents/models/response_plan.py`

`ScopedModel` subclass : UUID PK, sequential `reference` (prefix **`IRPL`**, e.g. `IRPL-1`), `scopes` M2M, `tags`, `version`, `created_by`, `django-simple-history` audit trail. It runs the **core `default` 4-state lifecycle** - it is a governance document, and `validated` means *in force*. `workflow_perm_namespace` is overridden to `incidents.response_plan`, because the default `app_label.model_name` would spell `incidents.incidentresponseplan`, which matches no feature in `PERMISSION_REGISTRY`.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `IRPL-N`, unique | Business reference |
| `scopes` | relation | M2M -> `context.Scope` | ISMS scopes the plan governs. A multi-entity group can run one plan per scope. |
| `name` | string | required, max 255 | Plan title, e.g. `ISMS incident response procedure` |
| `purpose` | text | optional, blank default | Scope and objectives of the plan |
| `procedure` | text | optional, HTML | The response procedure itself : detect, assess, respond, learn. The operational body of A.5.24. |
| `classification_scale` | text | optional, HTML | What `low` / `medium` / `high` / `critical` mean **in this organisation's terms**, which is the A.5.25 decision criterion. This is what an auditor asks for, and it is deliberately prose rather than a second configurable matrix engine : [Incident](incident.md) `severity` reuses `context.constants.Criticality`, and this field is what gives those four values meaning. |
| `escalation_matrix` | text | optional, HTML | Who is escalated to, at which severity, within which delay |
| `reporting_channels` | text | optional, HTML | How events and weaknesses are reported, **including the anonymous channel** A.6.8 requires. The prose counterpart of [SecurityEvent](security-event.md) `is_anonymous`. |
| `evidence_procedure` | text | optional, HTML | Identification, collection, acquisition and preservation of evidence (A.5.28) |
| `lessons_learned_procedure` | text | optional, HTML | How knowledge gained from incidents is used to strengthen controls (A.5.27) |
| `applicable_regimes` | JSON | list, default `[]`, blank | A list of `NotificationRegime` values : the regulatory regimes this plan is built to satisfy. **A `JSONField`, not a `django.contrib.postgres` `ArrayField`**, so the SQLite in-memory `core.settings_test` database used by `pytest.ini` keeps working. Drives the [IncidentNotification](incident-notification.md) rows instantiated at triage in phase 1; in phase 2 obligation matching moves to `ReportingObligationTemplate` and this field becomes a display-only summary of intent. |
| `owner` | relation | FK -> User, `SET_NULL`, optional | Accountable owner of the procedure. Reverse accessor `owned_incident_response_plans`. Receives the `INCIDENT_DECLARED` and `NOTIFICATION_OVERDUE` notifications. |
| `approved_by` | relation | FK -> User, `SET_NULL`, optional | Management approver (clause 5.1 leadership commitment). Reverse accessor `approved_incident_response_plans`. |
| `approved_at` | date | optional | Approval date |
| `effective_from` | date | optional | Date the plan entered into force |
| `review_date` | date | optional, indexed | Next scheduled review of the plan. Feeds the calendar and the upcoming-deadlines widget. |
| `last_exercise_date` | date | optional | Date the plan was last tested. **Maintained by the [Incident](incident.md) `transition_to()` override, never edited by hand** : see [Plan testing](#plan-testing-a524). |
| `workflow_state` | string | indexed, default `draft` | Lifecycle step (core `default` lifecycle) |
| `tags` | relation | M2M -> `context.Tag` | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | Timestamps |

### Relations

| Name | Type | Target | Reverse accessor | Description |
|---|---|---|---|---|
| `responsible_roles` | M2M | `context.Role` | `incident_response_plans` | The RACI roles staffing the response. People are resolved through `Role.assigned_users` in the UI; there is deliberately **no** `Role` FK on the incident itself, where responsibility is an `AUTH_USER_MODEL` FK (`incident_manager`), following `EssentialAsset.owner` / `custodian` and `ComplianceActionPlan.owner` / `assignees`. |
| `linked_requirements` | M2M | `compliance.Requirement` | `linked_incident_response_plans` | The controls this plan implements : A.5.24 through A.5.28, A.6.8, clause 10.1. The established traceability pattern already used by `Risk`, `Finding`, `ActionPlan`, `Indicator` and `Supplier`. |

Reverse accessors on `IncidentResponsePlan` : `incidents` ([Incident](incident.md) `response_plan`, `PROTECT`) and `post_incident_reviews` ([PostIncidentReview](post-incident-review.md) `response_plan`, `SET_NULL`).

### Meta

- `ordering = ["-effective_from", "name"]`

## What the `PROTECT` foreign key does and does not guarantee

`Incident.response_plan` is `on_delete=PROTECT`. A plan that has handled at least one incident can therefore never be deleted, only archived. That is the point : deleting the procedure would orphan every incident file that cites it.

The honest limit, which an implementer and an auditor both need to know : **the FK points at the plan row, not at a frozen copy of its text.** Editing `procedure` today changes what a reader sees when they open a two-year-old incident. The evolution is fully recoverable - `HistoricalRecords` keeps every revision, with its author and timestamp, and the incident's own `created_at` bounds which revision was in force - but reconstructing it is a history read, not a field read. If a true point-in-time snapshot is ever required (the pattern `risks.Risk.criteria_snapshot` and phase 2's `ReportingObligationTemplate` snapshotting already use), that is a deliberate, separate change with its own migration. It is **not** silently assumed anywhere in this module.

The practical convention that keeps this workable : a material change to the procedure is a **new plan row** put into force with its own `effective_from`, with the previous one archived, rather than an in-place rewrite. Incidents keep pointing at the plan they were actually handled under.

## Plan testing (A.5.24)

A.5.24 requires the plan to be **tested**, not merely written. Cairn records that test as a real [Incident](incident.md) flagged `is_exercise=True`, run through the identical lifecycle with identical gates, rather than as a separate drill entity that would exercise nothing.

`last_exercise_date` is the evidence produced by that mechanism:

- it is set **only** by the `post_incident_review -> closed` transition on an incident with `is_exercise=True`, from that incident's `closed_at`, and only when the new value is more recent than the stored one;
- it is excluded from the plan's `ModelForm`, is `read_only` in the serializer, and is absent from the MCP `writable_fields` list. A hand-edited plan-testing date is worthless as evidence, so no surface offers the edit;
- an exercise instantiates **no** regulatory notification obligations (RG-INC-17), and is exempt from the RG-INC-19 justification gate for exactly that reason.

The plan detail page shows `last_exercise_date` beside `review_date` in the sidebar, and links to the exercise incidents (`plan.incidents.filter(is_exercise=True)`) so the evidence is one click from the claim.

## Lifecycle

`IncidentResponsePlan` declares **no** `LIFECYCLE_NAME` and runs the core `default` lifecycle (`core/lifecycle.py` `DEFAULT_LIFECYCLE`). A governance document does not need operational stages; it needs a controlled approval.

### Steps

| Code | Label | StepKind | In reports | Linkable | Deletable | Tone | Meaning |
|---|---|---|---|---|---|---|---|
| `draft` | Draft | `DRAFT` | no | no | **yes** | `neutral` | Being written. The only deletable step. |
| `pending` | Pending validation | `INTERMEDIATE` | no | no | no | `info` | Submitted for management approval |
| `validated` | Validated | `INTERMEDIATE` | **yes** | **yes** | no | `success` | **In force.** Only a plan in this step is offered in the incident's response-plan picker, and only a validated plan is counted in reports. |
| `archived` | Archived | `ARCHIVED` | no | no | no | `muted` | Superseded or withdrawn |

### Transitions

| Verb | Transition | `permission_action` | `requires_comment` |
|---|---|---|---|
| Submit | `draft -> pending` | `update` | no |
| Send back to draft | `pending -> draft` | `update` | no |
| Validate | `pending -> validated` | **`approve`** | no |
| Archive | `validated -> archived` | **`approve`** | no |

Concretely, `permission_action="approve"` means the actor must hold `incidents.response_plan.approve`, built from the overridden `workflow_perm_namespace`.

### Why this entity needs no bookend correction

The other lifecycles in this module have to declare their `archived` step explicitly and hand-declare both bookend edges, because `lifecycle_from_state_flags()` auto-wires `ANY -> archived` and `archived -> draft` with **no `permission_action` and no `requires_comment`** (`core/lifecycle.py` `lifecycle_from_state_flags()`), and `user_can_perform()` allows any transition whose `permission_action` is empty - which, with a `deletable=True` draft step, yields an `archive -> restore -> delete` path.

The core `default` lifecycle has neither problem : its archive edge already carries `permission_action="approve"`, and it declares **no restore transition at all**. There is therefore no path from `validated` back into a deletable step, and this entity needs no override. Do not "fix" it by adding one.

Note also that submitting a `default`-lifecycle element for validation (`draft -> pending`) fires `notify_lifecycle_submitted` from `BaseModel.transition_to()` (RG-LC-06), so the plan's owners are notified with no module-specific code.

### Creation and the initial step

`BaseModel.save()` calls `_ensure_initial_step()` (`context/models/base.py` `BaseModel._ensure_initial_step()`), and `Lifecycle.initial_step` (`core/lifecycle.py` `Lifecycle.initial_step`) returns the single `StepKind.DRAFT` step. Every new plan therefore lands in `draft`, including one created by the demo seed or by MCP.

A plan that must arrive already in force - the seeded Voltara Energy procedure, an import - is `save()`d and then walked through `transition_to("pending", user, enforce_permission=False)` and `transition_to("validated", user, enforce_permission=False)` inside one `transaction.atomic()` block. Writing `workflow_state="validated"` at insert would stick, because `_ensure_initial_step()` only snaps a blank or unknown value, but it would leave **no `core.LifecycleEvent` rows**, so the plan would appear in force with no record of ever having been approved - which is precisely the evidence A.5.24 and clause 7.5.3 are asking for.

## Obligation generation

In phase 1, the triage transition on an [Incident](incident.md) reads `response_plan.applicable_regimes` and instantiates one [IncidentNotification](incident-notification.md) per regime, then transitions each new row from `draft` to `assessed` ("To decide") in the same atomic block. Only a plan in a `reportable()` step is consulted : a draft plan's regime list is a work in progress, not a legal position.

Two consequences the operator must see rather than infer:

- an incident with `personal_data_involved=True` gets the `gdpr_art33_authority` obligation **regardless** of what the plan lists (RG-INC-18). A regime the organisation forgot to configure does not remove the duty;
- an incident whose triage produces **zero** obligations must carry a non-blank `no_obligation_justification` unless `personal_data_involved` or `is_exercise` is true (RG-INC-19). A missing regime configuration must never read as compliance on a green dashboard.

In phase 2 `ReportingObligationTemplate` takes over the matching, with per-obligation snapshotting of the legal terms, and `applicable_regimes` becomes a display-only statement of which regimes the plan claims to cover - useful in the plan document, no longer load-bearing at runtime.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-17 | An incident with `is_exercise=True` runs the identical lifecycle but is excluded from every KPI, indicator, report, calendar deadline and dashboard count, and never instantiates regulatory notifications. Its closure updates `IncidentResponsePlan.last_exercise_date`, which is the A.5.24 plan-testing evidence. |
| RG-INC-19 | When triage produces zero notification obligations, `personal_data_involved` is `False` **and** `is_exercise` is `False`, a non-blank `no_obligation_justification` is mandatory on the incident. |
| RG-INC-30 | Obligation generation only considers configuration in a `reportable()` lifecycle state - the plan in phase 1, the template in phase 2 - never an `is_active` boolean literal. |
| RG-INC-37 | Every report, KPI, calendar feed and link picker filters through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. The response-plan picker on the incident form uses `linkable_or_linked()`, so an incident already pointing at a since-archived plan keeps rendering it. |
| RG-INC-38 | `IncidentResponsePlan` is a `ScopedModel` and carries its own `scopes`, so `ScopeFilterMixin` and `ScopeFilterAPIMixin` filter it with no extra work. |
| RG-INC-39 | The module has exactly six permission features and never grows. `incidents.response_plan` gates this entity and, in phase 2, the `ReportingAuthority` and `ReportingObligationTemplate` catalogue. |

## Endpoints

### REST

- `GET /api/v1/incidents/response-plans/` : list, with filters `status`, `owner_id`, `scope_id`, `review_before`
- `POST /api/v1/incidents/response-plans/` and `POST /api/v1/incidents/response-plans/batch/`
- `GET/PUT/PATCH/DELETE /api/v1/incidents/response-plans/<uuid>/`
- `GET/POST /api/v1/incidents/response-plans/<uuid>/transition/` : `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`
- `GET /api/v1/incidents/response-plans/<uuid>/history/` : `core.history.build_timeline`

`IncidentResponsePlanSerializer` / `IncidentResponsePlanListSerializer`, with `read_only_fields` covering `id`, `reference`, `created_by`, `created_at`, `updated_at`, `version` and `last_exercise_date`. `status` is exposed as `CharField(source="workflow_state", read_only=True)`. `applicable_regimes` is validated as a list whose members are all valid `NotificationRegime` values. The viewset uses `ModulePermission` plus the module's `_IncidentViewSet` base (`permission_module = "incidents"`, `custom_action_map = {"transition": "update"}`), following `trust_center/api/views.py` `_ManagedViewSet`.

### MCP

- `_register_crud(server, "incident_response_plan", IncidentResponsePlan, "incidents.response_plan", ...)` generates `list_incident_response_plans`, `get_incident_response_plan`, `create_incident_response_plan`, `batch_create_incident_response_plans`, `update_incident_response_plan`, `delete_incident_response_plan`, `transition_incident_response_plan`, `incident_response_plan_allowed_transitions`, `get_incident_response_plan_history`.
- `m2m_fields` maps `scope_ids`, `responsible_role_ids`, `linked_requirement_ids`.
- `applicable_regimes` carries a `field_overrides` entry with the explicit `NotificationRegime` `enum` list; every HTML field uses `_html_field()`; `last_exercise_date` is absent from `writable_fields`.

`mcp/tools.py` `HELP_TEXT` gains `IncidentResponsePlan=IRPL` in the reference-prefix block.

## Permissions

| Codename | Description |
|---|---|
| `incidents.response_plan.read` | List / read response plans |
| `incidents.response_plan.create` | Create a plan |
| `incidents.response_plan.update` | Edit a plan, submit it for validation, send it back to draft |
| `incidents.response_plan.approve` | Put a plan into force (`pending -> validated`) and archive it. In phase 2, also gates the reporting authority and obligation template catalogue. |
| `incidents.response_plan.delete` | Delete a draft plan |

## UI

- **List** (`/incidents/response-plans/`) : the house stack, with columns for name, owner, `effective_from`, `review_date`, `last_exercise_date` and state. A plan whose `review_date` has passed is flagged in the row, and a plan whose `last_exercise_date` is more than twelve months old carries a warning badge : an untested plan is an A.5.24 nonconformity waiting to be written up.
- **Detail** (`/incidents/response-plans/<uuid>/`) : a strict 2-column card layout, no nav-tabs. Left column, as collapsible Bootstrap sections so a long procedure does not bury the rest : *Purpose*, *Procedure*, *Classification scale*, *Escalation matrix*, *Reporting channels*, *Evidence procedure*, *Lessons learned procedure*, and *Applicable regimes* as a chip list. Right column, sticky : `{% workflow_badge %}`, owner, approver with `approved_at`, `effective_from`, `review_date`, `last_exercise_date`, responsible roles, linked requirements, scopes, tags, the history trigger, and a count of the incidents handled under this plan linking to the filtered incident list.
- **Stepper** : `{% include "includes/lifecycle_stepper.html" %}` fed by `LifecycleStepperMixin`, rendering the standard four-step `default` lifecycle. Never a status select, never plain buttons.
- Create / update / delete use `HtmxFormMixin` drawer modals. The six rich-text fields make this the tallest form in the module : on small screens they are rendered as an accordion so the sticky action bar stays reachable.
- `review_date` is fed into the calendar under the `incident` category, alongside the review and evidence-retention dates.

## Translations

This entity declares **no** label that collides with an existing `msgid` in `locale/fr/LC_MESSAGES/django.po` : its field verbose names ("Purpose", "Procedure", "Classification scale", "Escalation matrix", "Reporting channels", "Evidence procedure", "Lessons learned procedure", "Applicable regimes", "Effective from", "Review date", "Last exercise date", "Approved by", "Approved at") are all new bare `msgid`s. Two points still apply:

1. It renders labels declared elsewhere in the module - the `NotificationRegime` values in the `applicable_regimes` widget, documented in [IncidentNotification](incident-notification.md) - which **do** collide and which therefore use `pgettext_lazy("incident", ...)` with a matching `msgctxt "incident"` block. Do not re-declare them here.
2. It runs the core `default` lifecycle, so its step and transition labels ("Draft", "Pending validation", "Validated", "Archived", "Submit", "Send back to draft", "Validate", "Archive") are core-owned and already in the catalogue. **Should a bespoke lifecycle ever be added to this entity, its step labels must not use `pgettext_lazy`** : `lifecycle_to_json()` stringifies each label with `str(...)` and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy` (`core/lifecycle.py` `lifecycle_from_json()`), so a `msgctxt` is lost after the `post_migrate` DB round-trip and the label silently resolves to the wrong French string. The fix in that case is a distinct English label, never a context.

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt` : `compilemessages` runs before `pytest` in `.github/workflows/tests.yml`, so a duplicate breaks CI outright.

## References

- ISO/IEC 27001:2022 A.5.24 (information security incident management planning and preparation), and by reference A.5.25, A.5.26, A.5.27, A.5.28, A.6.8
- ISO/IEC 27001:2022 clause 5.1 (leadership and commitment), clause 7.5.3 (control of documented information)
- ISO/IEC 27035-1 : the *plan and prepare* phase
- [Incident](incident.md) : `response_plan` (`PROTECT`), `is_exercise`, and the closure transition that maintains `last_exercise_date`
- [SecurityEvent](security-event.md) : the register `reporting_channels` describes
- [IncidentEvidence](incident-evidence.md) : governed by `evidence_procedure`
- [PostIncidentReview](post-incident-review.md) : governed by `lessons_learned_procedure`, and carries `response_plan_update_required` when the review concludes the plan itself must change
- [IncidentNotification](incident-notification.md) : instantiated from `applicable_regimes` at triage
- [README.md](README.md) : module business rules, permissions, notifications
- [governance/workflow.md](../governance/workflow.md) : the lifecycle framework, and the `default` 4-state lifecycle this entity runs
- [Role](../m1-context/role.md), [Requirement](../m3-compliance/requirement.md)

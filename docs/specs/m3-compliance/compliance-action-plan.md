# ComplianceActionPlan

`compliance.models.action_plan.ComplianceActionPlan`

Action plan aimed at remediating a compliance gap identified during an [assessment](compliance-assessment.md), mitigating a [risk](../m4-risks/risk.md), or addressing a finding from a management review. It drives its lifecycle through a 7-state Kanban workflow and retains the full history of transitions.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `CAPL-N`, unique | Business reference |
| `scopes` | relation | M2M -> Scope | Relevant ISMS scopes |
| `name` | string | required, max 255 | Action plan title |
| `description` | text | optional, HTML | Detailed description |
| `gap_description` | text | required, HTML | Description of the gap to be closed |
| `remediation_plan` | text | required, HTML | Remediation plan |
| `priority` | enum | required | `low`, `medium`, `high`, `critical` |
| `owner` | relation | FK -> User, required, PROTECT | Supervisor (responsible for follow-up) |
| `assignees` | relation | M2M -> User | Assignees (those who carry out the plan) |
| `requirements` | relation | M2M -> Requirement | Requirements the plan addresses |
| `findings` | relation | M2M -> Finding | Audit findings the plan addresses |
| `risks` | relation | M2M -> Risk | Risks the plan mitigates |
| `originating_review` | relation | FK -> ManagementReview, optional | Management review that generated this plan |
| `start_date` | date | optional | Planned start date |
| `target_date` | date | required | Target completion date |
| `completion_date` | date | optional | Actual completion date. Set automatically on transition to `closed`. |
| `progress_percentage` | integer | default 0, 0-100 | Progress percentage. Forced to 100 on transition to `closed`. |
| `cost_estimate` | decimal(12,2) | optional | Cost estimate |
| `status` | enum | required, default `new` | See "Workflow" below. **Read-only via standard REST/MCP**: use the `action_plan_transition` tool to change the status. |
| `is_overdue` | boolean | computed, read-only | `true` if `target_date` has passed and `status` is neither `closed` nor `cancelled`. Computed on read, not stored. |
| `tags` | relation | M2M -> Tag | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | |

## Workflow

The action plan follows a 7-state Kanban workflow plus `cancelled`. Each transition is validated by `ComplianceActionPlan.transition_to(new_status, user, comment)`; backward transitions ("refusal") require a mandatory comment and are recorded as `is_refusal=True` in the history.

```text
new -> to_define -> to_validate -> to_implement -> implementation_to_validate -> validated -> closed
                  <-              <-              <-                            <-
                                              (refusal with mandatory comment)

(all steps <= implementation_to_validate) -> cancelled  (terminal)
```

| Status | Direction |
|---|---|
| `new` | Draft created, pending definition |
| `to_define` | Definition in progress (specify the remediation plan, scope, resources) |
| `to_validate` | Definition submitted, pending validation by the supervisor |
| `to_implement` | Definition validated, pending implementation by the assignees |
| `implementation_to_validate` | Implementation submitted, pending final validation |
| `validated` | Implementation validated, ready to close |
| `closed` | Plan completed (terminal). `completion_date` and `progress_percentage=100` are auto-populated on entry. |
| `cancelled` | Plan cancelled (terminal). Reachable from any status except `validated`, `closed` and `cancelled`. |

> UI note: the action plan keeps this 7-state lifecycle on the model, but it no longer has a dedicated Kanban board. The `/compliance/action-plans/` page is now the list, transitions are performed from the detail page, and plans appear on the global Kanban board **To do / Doing / Done** (`/kanban/`, see [governance/kanban.md](../governance/kanban.md)).

### Transitions and permissions

- **Progress**: each forward transition requires at least the `compliance.action_plan.update` permission, and some validation steps may require `compliance.action_plan.approve` (configurable).
- **Refusal**: backward transition from `to_validate -> to_define`, `implementation_to_validate -> to_implement`, etc. The `comment` is required to record the reason for the refusal. The transition is recorded as `ActionPlanTransition.is_refusal=True`.
- **Cancellation**: `cancelled` is reachable from `new`, `to_define`, `to_validate`, `to_implement`, `implementation_to_validate` (see `ACTION_PLAN_CANCELLABLE_STATUSES`). Once `validated` or `closed`, cancellation is no longer possible.
- **History**: each transition creates an `ActionPlanTransition` (`from_status`, `to_status`, `performed_by`, `comment`, `is_refusal`, `created_at`). The detail is accessible via `assessment.transitions.all().order_by('created_at')`.

The API exposes `GET /api/v1/compliance/action-plans/<uuid>/allowed-transitions/` (and the MCP `action_plan_allowed_transitions`), which returns the list of transitions available from the current status for the current user, taking their permissions into account. This is the API to call before offering a UI action or an MCP transition tool.

## Business rules

| ID | Rule |
|---|---|
| RG-CAP-01 | The `status` is not directly modifiable via `update_compliance_action_plan`: use `action_plan_transition`, which applies the workflow rules, the permission check, and writes the history. |
| RG-CAP-02 | A backward transition (refusal) requires a non-empty `comment`. The request is rejected with an explicit 400 if the comment is missing. |
| RG-CAP-03 | On transition to `closed`, `completion_date` is forced to today's date and `progress_percentage` is forced to 100. Completion RP-02 is therefore attached to the terminal `closed` status. |
| RG-CAP-04 | `is_overdue` is a computed property, true iff `target_date < today` and `status not in (closed, cancelled)`. Used for indicators and for the "overdue plans" filters. No automatic status migration: the plan remains in its Kanban state until an operator advances or closes it. |

## Deviations from the original spec

The M3 spec §2.7 listed a 5-status workflow (`planned`, `in_progress`, `completed`, `cancelled`, `overdue`). The implementation evolved towards a 7-state Kanban workflow:

| Original spec | Current implementation |
|---|---|
| `planned` | `new` then `to_define`, `to_validate`, `to_implement` (definition is a process, not a status) |
| `in_progress` | `implementation_to_validate` (implementation is under review) |
| `completed` | `validated` (implementation accepted) then `closed` (terminal). RP-02 (auto-100% + date) attached to the move to `closed`. |
| `cancelled` | `cancelled` (identical) |
| `overdue` | **Computed property `is_overdue`**, not a status. RP-01 (automatic move to overdue) is not applied as a workflow transition; instead, `is_overdue` is computed on every read. This avoids the friction of a status that updates on its own at midnight every day, without losing anything on the detection side. |

The richer workflow reflects real-world practice: moving an action plan from "definition" to "validated implementation" is not a binary jump but a chain of validations (auditor -> supervisor -> assignee -> supervisor), and rejections are frequent ("no, this definition is not precise enough"). The 7-step Kanban status captures this chain without burdening the application code with a parallel "waiting for what" state. The original spec is acknowledged as too simple for real usage, and the deviation is kept as is with this documented mapping.

## Endpoints

### REST

- `GET /api/v1/compliance/action-plans/`: list with filters `status`, `priority`, `owner_id`, `requirement_id`, `assignee_id`
- `POST /api/v1/compliance/action-plans/`
- `GET /api/v1/compliance/action-plans/<uuid>/`
- `PATCH /api/v1/compliance/action-plans/<uuid>/`: modify business fields (except `status`)
- `DELETE /api/v1/compliance/action-plans/<uuid>/`
- `GET /api/v1/compliance/action-plans/<uuid>/allowed-transitions/`: transitions available to the user
- `POST /api/v1/compliance/action-plans/<uuid>/transition/`: apply a transition (`{"status": "...", "comment": "..."}`)
- `GET /api/v1/compliance/action-plans/<uuid>/transitions/`: history

### MCP

- `list_action_plans` / `get_action_plan` / `create_action_plan` / `update_action_plan` (without `status`) / `delete_action_plan` / `batch_create_action_plans`
- `action_plan_allowed_transitions(id)`: lists the available transitions
- `action_plan_transition(id, status, comment=...)`: applies a transition
- `action_plan_transitions(id)`: chronological history

## Permissions

| Codename | Description |
|---|---|
| `compliance.action_plan.read` | Read action plans |
| `compliance.action_plan.create` | Create |
| `compliance.action_plan.update` | Modify business fields + apply standard forward transitions |
| `compliance.action_plan.approve` | Apply validation transitions (`to_validate -> to_implement`, `implementation_to_validate -> validated`) |
| `compliance.action_plan.delete` | Delete |

## Références

- ISO/IEC 27001:2022 §10.1 (Continual improvement) and §10.2 (Nonconformity and corrective action)
- [ComplianceAssessment](compliance-assessment.md): typical source of action plans via `Finding`
- [Risk](../m4-risks/risk.md) and [RiskTreatmentPlan](../m4-risks/risk-treatment-plan.md): a compliance action plan can be linked to a risk treatment plan via `RiskTreatmentPlan.related_action_plans`
- [ManagementReview](../management-review/management-review.md): an action plan can be generated from a management review decision (`originating_review`)

# Unified Kanban board

Cross-cutting, read-only **To do / Doing / Done** board that aggregates governance
work items from several modules into a single view. It lives at the top level of the
navigation (`/kanban/`, in the sidebar right under the Calendar) and is implemented in
the `core` app.

## Purpose

Give every user a single place to see what is queued, in progress and finished across
the platform, without having to open each module. This first version is deliberately
simple: three columns, no drag-and-drop, cards link straight to the underlying detail
page.

## Aggregated entities (v1)

| Type | Model | Detail link | Due date used |
| --- | --- | --- | --- |
| Action plan | `compliance.ComplianceActionPlan` | `compliance:action-plan-detail` | `target_date` |
| Treatment action | `risks.TreatmentAction` | `risks:treatment-plan-detail` | `target_date` |
| Audit | `compliance.ComplianceAssessment` | `compliance:assessment-detail` | `assessment_end_date` |
| Risk assessment | `risks.RiskAssessment` | `risks:assessment-detail` | `next_review_date` |

## Column mapping

Each entity declares how its statuses map to the three columns. Terminal
"removed from tracking" states (`cancelled`, `archived`) are **excluded**: such an item
simply disappears from the board (there is no Cancelled column).

| Type | To do | Doing | Done | Excluded |
| --- | --- | --- | --- | --- |
| Action plan | new, to_define, to_validate | to_implement, implementation_to_validate | validated, closed | cancelled |
| Treatment action | planned | in_progress | completed | cancelled |
| Audit | draft, planned | in_progress | completed, closed | cancelled |
| Risk assessment | draft | in_progress | completed, validated | archived |

The single source of truth for the mapping, the per-status badge tone and the card
shape is [`core/kanban.py`](../../../core/kanban.py).

## Behaviour

- **Read-only.** No drag-and-drop, no inline transitions. Workflow transitions still
  happen on each entity's own detail page.
- **Permission-aware.** A user only sees the entity types they can read
  (`compliance.action_plan.read`, `risks.treatment.read`, `compliance.assessment.read`,
  `risks.assessment.read`). Types without the read permission are omitted entirely.
- **Scope-aware.** Scope-tenant entities (action plans, audits, risk assessments) are
  filtered by the user's allowed scopes, mirroring `ScopeFilterMixin`. Treatment actions
  are not scope-tenant and are gated by the treatment read permission only.
- **Card sorting.** Within each column: overdue first, then by due date (undated last),
  then by reference.
- **Overdue cards** (a due date in the past, for a card not in *Done*) carry a red
  border and an `Overdue` hint on the date.

## Integration surfaces

- **Web view** : `core.views.KanbanBoardView` → `templates/kanban.html` (card partial
  `templates/includes/_kanban_card.html`).
- **JSON feed** : `GET /api/kanban-board/` (`core.views.KanbanBoardDataView`) returns the
  three columns with serialised cards.
- **MCP tool** : `kanban_board` returns the same structure for external clients.

## Extending

To add a new entity type, declare its status → (column, tone) map and a small builder in
`core/kanban.py`, register it in `_BUILDERS` and `ENTITY_PERMS`, and add its icon/label to
`TYPE_ICONS` / `TYPE_LABELS`. The web view, JSON feed and MCP tool pick it up automatically.

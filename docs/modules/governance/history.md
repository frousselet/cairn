# History / audit-trail framework

`core.history` - the single, audit-grade traceability layer over `django-simple-history`.

Every domain element records *who changed what, and when*. The framework turns raw
historical records into one normalized, chronological **timeline** of events, computed in
exactly one place and rendered identically everywhere: the detail-page panel, the REST
API and the MCP tools all build their view from `core.history`, so diff logic, hidden
fields and event classification never diverge.

## What is tracked

History applies to **every `BaseModel` / `ScopedModel` subclass**: each declares
`history = HistoricalRecords()` (per-model, not on the base class), so the historical
table captures every field change with the acting user and timestamp. `django-simple-history`
middleware (`HistoryRequestMiddleware`) fills `history_user` from the request.

The authoritative, exhaustive list of history-tracked models is machine-discoverable
(the `Historical*` model scan used by the system audit log, `accounts.views.ActionLogListView`).
The unified UI panel is surfaced on the detail page of each `BaseModel` entity, covering
the context, assets, compliance, risks, reports and trust-center modules.

## Event model

`build_timeline(instance, *, limit, extra)` returns a reverse-chronological list of
`HistoryEntry`. Each entry is one of `EntryKind`:

| Kind | Source | Shown as |
| ---- | ------ | -------- |
| `create` | `+` record | field snapshot |
| `update` | `~` record with ordinary field diffs | per-field `old -> new` diff |
| `transition` | `~` record whose delta touches `workflow_state` | `from -> to` state labels (+ comment where one exists) |
| `approval` | `~` record whose delta is approval fields only | "Approval granted / revoked" |
| `delete` | `-` record | field snapshot |

Precedence on a modification: **transition > approval-only > update**. Approval and
version churn (`is_approved`, `approved_by`, `approved_at`, `version`) are hidden from
ordinary diffs. A transition's `is_refusal` flag is **recomputed from the registered
workflow** (a backward move along the main flow), never persisted.

### Merged sources

`HISTORY_SOURCE_HOOKS` (keyed by `app_label.model`) merges extra events into an entity's
timeline via `extra_source_for(instance)`:

- `context.role` - each responsibility's history, so adding / editing a responsibility
  shows on the role timeline (`entity_label` distinguishes the rows).
- `compliance.complianceactionplan` / `reports.managementreview` - their dedicated
  `*Transition` logs, which carry transition **comments**. For these the generic
  `workflow_state`-diff transitions are suppressed (`suppress_generic_transitions`) so a
  transition appears once, with its comment, instead of twice.

> Persisting transition comments for *all* entities (not only the two with a dedicated
> log) is intentionally out of scope: generic transitions show `from -> to`, the actor and
> the timestamp, but no comment.

## Surfaces

All three consumers call `core.history`; none reimplements diffing.

- **UI (lazy off-canvas panel).** Detail views mix in `accounts.mixins.HistoryUrlMixin`,
  which exposes `history_url` + `history_available`. The trigger
  (`includes/history_trigger.html`) lives in the page-header action slot on **every**
  detail page; opening it lazily HTMX-loads `includes/history_panel.html`'s body from
  `history:partial` (`core.history_views.HistoryPartialView`), which renders
  `includes/history_timeline.html`. The timeline is never queried on page load, only on
  first open. The endpoint enforces the entity's `.read` permission and the user's scope.
- **REST API.** `accounts.api.mixins.HistoryAPIMixin` adds `GET /<entity>/<id>/history/`
  returning the same entries (`?limit=`, `?offset=`).
- **MCP.** `_register_crud` registers `get_<entity>_history` for every entity with
  history, gated by `<perm_prefix>.read`.
- **System audit log.** `ActionLogListView` classifies records with
  `core.history.classify_record` (shared with the timeline).

## UI contract

- The history trigger is **always** the first action in the `{% page_header %}` block,
  icon `bi-clock-history`, label "History" / "Historique".
- The panel is a right-side Bootstrap off-canvas (`offcanvas-end`), full-height, internally
  scrolling, near-full-width on mobile, with native focus-trap / ESC / backdrop.
- Never reintroduce per-entity history markup (nav-tabs tab, bottom collapse card,
  `<details>`); converge on the trigger + panel includes.

## Key files

- `core/history.py` - constants, `EntryKind`, `FieldChange`, `HistoryEntry`,
  `classify_record`, `build_entry`, `build_timeline`, `HISTORY_SOURCE_HOOKS`.
- `core/history_views.py` + `core/history_urls.py` - the lazy panel endpoint.
- `accounts/mixins.py` (`HistoryUrlMixin`), `accounts/api/mixins.py` (`HistoryAPIMixin`).
- `templates/includes/history_{trigger,panel,timeline}.html`.

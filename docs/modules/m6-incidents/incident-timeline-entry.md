# IncidentTimelineEntry

`incidents.models.timeline.IncidentTimelineEntry`

The chronology of an [Incident](incident.md) : one dated, attributed, append-only entry per thing that happened. This is the single narrative an auditor, a supervisory authority or a court reads. It is the source of the GDPR Art. 33(3)(a) "facts relating to the personal data breach", of the NIS2 Art. 23(4)(d) final-report narrative, and of the sequence-of-events section of the incident register export.

File : `incidents/models/timeline.py`

Not a `BaseModel`, not a `ScopedModel`, and not a `ReferenceGeneratorMixin` : a plain `models.Model` with its own UUID primary key, explicitly declared row timestamps, a `version` counter and a `django-simple-history` audit trail. The reasons are set out in [Why this is not a BaseModel](#why-this-is-not-a-basemodel) and they are load-bearing : changing any of them changes what the register is worth in front of a regulator.

## Why this is not a BaseModel

**No lifecycle.** A `BaseModel` runs a registered lifecycle, and `_ensure_initial_step()` fires only on a blank or unknown `workflow_state`, so every ordinary insert lands in `draft`; an explicitly assigned domain step would stick, but it would leave **no `core.LifecycleEvent` row**, which is why the pattern is banned; the snap targets to that lifecycle's step. A narrative entry has no states : "10:42 EDR isolated WEB-PRD-02" is never draft, never pending, never validated. Giving it a lifecycle would put a governance workflow around a sentence, and would make the chronology filterable by a step that carries no meaning. The entity therefore has no `workflow_state` column at all, `_ensure_initial_step()` never runs against it, and it is deliberately invisible to `reportable()`, `linkable()` and `deletable_states()`. It is read through its parent incident, always.

**Never edited.** An account of an incident that can be rewritten is not evidence. `save()` refuses any write against an existing primary key and `delete()` refuses outright, both raising `core.lifecycle.LifecycleProtectedError` (the house exception, the same one `BaseModel.delete()` raises when a lifecycle state forbids deletion). Corrections are appended, never applied in place : see [Correction by supersession](#correction-by-supersession).

**Never deleted.** No delete view, no `DELETE` route, no MCP delete tool, no admin delete action. The entity is create-and-read only on every one of the three surfaces.

**No reference prefix.** `ReferenceGeneratorMixin._generate_next_reference()` (`context/models/base.py`) selects every existing reference sharing the prefix, pulls the whole list into Python and takes the maximum, on every single insert. That is acceptable for a few hundred suppliers or risks; it is the wrong shape for a log that takes a row on every lifecycle transition and every responder note during a live incident, where a major incident alone can produce hundreds of entries in an afternoon. Entries are cited by their `occurred_at` and their position in the incident file, not by a business reference, so the prefix buys nothing and costs a full-table scan per write. Entries are addressed by UUID everywhere : in the API, in MCP payloads and in the `superseded_entry` self-relation.

**Cheap to write.** A responder types an entry mid-incident. The write path is a single `INSERT` with no reference scan, no lifecycle resolution, no scope M2M and no transition bookkeeping.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, `default=uuid.uuid4`, `editable=False` | Unique identifier. Matches the `BaseModel` convention without inheriting it. |
| `incident` | relation | FK -> [Incident](incident.md), required, `CASCADE`, `related_name="timeline_entries"` | The incident being narrated. |
| `occurred_at` | datetime | required, indexed | Real-world time of the act being narrated. May be backdated. **This is the ordering key** : the chronology reads in the order things happened, not in the order they were typed. |
| `recorded_at` | datetime | `auto_now_add=True` | When the entry was written. `occurred_at != recorded_at` is normal during a live incident and is itself evidence of the response tempo. |
| `entry_type` | enum | required, default `observation` | Nature of the entry. See [Enums](#enums). |
| `summary` | string | required, non-blank, max 500 | The one-line entry, e.g. `EDR isolated WEB-PRD-02`. Rendered in the chronology card and exported verbatim. |
| `detail` | text | optional, HTML rich text, blank default | The full account : commands run, output observed, people spoken to. |
| `source` | enum | required, default `manual` | Who wrote the row : a human, the lifecycle engine, a background job or a bulk import. See [Enums](#enums). |
| `author` | relation | FK -> User, required, `PROTECT`, `related_name="incident_timeline_entries"` | Who wrote the entry. `PROTECT` so a user who wrote incident history can never be hard-deleted : the account must stay attributable. Deactivate or anonymise the user instead. |
| `related_action` | relation | FK -> [IncidentResponseAction](incident-response-action.md), optional, `SET_NULL`, `related_name="timeline_entries"` | The operational action this entry narrates, when there is one. |
| `related_evidence` | relation | FK -> [IncidentEvidence](incident-evidence.md), optional, `SET_NULL`, `related_name="timeline_entries"` | The evidence item this entry narrates, when there is one. |
| `superseded_entry` | relation | FK -> self, optional, `SET_NULL`, `related_name="corrections"` | The earlier entry this one corrects. Set only on `entry_type=correction`. |
| `correction_reason` | text | required non-blank when `superseded_entry` is set, blank default | Why the earlier entry is being corrected. A correction with no stated reason is a rewrite. |
| `is_evidence` | boolean | default `False` | Marks the entry for verbatim inclusion in generated regulatory filings and in the incident register export. |
| `version` | int | `PositiveIntegerField`, default `1` | Row version counter, mirroring the `SupplierSubprocessor` precedent for non-`BaseModel` audit rows. Never incremented in practice, since the row is never updated; kept so the shape matches the platform's other child rows and so a non-`1` value is itself a signal. |
| `created_at` / `updated_at` | datetime | `auto_now_add` / `auto_now` | Row timestamps. Declared explicitly because `BaseModel` is not inherited. |
| `history` | `HistoricalRecords()` | | Tamper **detection**. See [Append-only : what is actually guaranteed](#append-only--what-is-actually-guaranteed). |

`Meta.ordering = ["incident", "occurred_at", "recorded_at"]`. The three-key ordering is deliberate : two entries can legitimately share an `occurred_at` (two responders narrating the same minute), and `recorded_at` then breaks the tie deterministically so the exported narrative is stable between two renders of the same incident file.

## Enums

Reproduced verbatim from `incidents/constants.py` (DB value = Label).

`TimelineEntryType` :

| Value | Label |
|---|---|
| `observation` | Observation |
| `action` | Action |
| `decision` | Decision |
| `communication` | Communication |
| `escalation` | Escalation |
| `evidence` | Evidence |
| `external_input` | External input |
| `correction` | Correction |
| `system` | System |

`TimelineEntrySource` :

| Value | Label |
|---|---|
| `manual` | Manual |
| `lifecycle` | Lifecycle transition |
| `system` | System |
| `import` | Import |

## Append-only : what is actually guaranteed

The module states this plainly rather than claiming an immutability the schema does not provide.

**Prevention is at application level.** `save()` raises `LifecycleProtectedError` when `self._state.adding` is false, and `delete()` raises `LifecycleProtectedError` unconditionally. Every documented write path in Cairn goes through `Model.save()`, so the web forms, the DRF serializers, the MCP tools and the Django admin are all covered.

**What bypasses it :**

- `QuerySet.update()` and `QuerySet.bulk_update()` issue SQL without calling `save()`.
- `QuerySet.delete()` and cascade deletion do not call `Model.delete()`. A cascade from the parent incident therefore removes entries without the guard firing. In practice this only ever reaches a `draft` incident, because RG-INC-07 makes an incident undeletable from `detected` onward, and a draft incident has no narrative worth losing; but the mechanism is stated here so nobody discovers it during an audit.
- Raw SQL, a `manage.py shell` session and direct database access bypass Python entirely.

**Detection is via `HistoricalRecords`.** Every ORM-level write that does go through `save()` leaves a historical row, and `django-simple-history` records the acting user. An entry whose historical trail shows more than one row has been altered, and that is visible on the entry's history panel and in the merged timeline built by `core.history.build_timeline`. The honest claim to make to an auditor is therefore: *tampering with the chronology is prevented on every supported path and detectable on the rest*, not *the chronology is immutable*.

Real database-level immutability would need PostgreSQL rules or triggers, which `core.settings_test` (SQLite in memory, migrations disabled) cannot exercise. That divergence is not taken in this module; if it is ever taken, it must be taken deliberately and documented here.

## Correction by supersession

A factual error in the chronology is fixed by **appending**, never by editing :

1. Create a new entry with `entry_type = correction`.
2. Point `superseded_entry` at the entry being corrected.
3. Give a non-blank `correction_reason`.
4. Set `occurred_at` to the real-world time of the fact being restated, not to the time of the correction. The chronology then still reads in the order things happened, and `recorded_at` reveals how long the error stood uncorrected.

The superseded entry is never modified and never hidden. The chronology card renders it with a struck-through summary and a link to its correction, and the correction renders with a back-link. A correction may itself be corrected : the chain is followed to its end.

Exports follow the chain. `is_evidence` entries that have been superseded are exported as the latest non-superseded version of the fact, with the superseded original kept in the appendix, so a regulatory filing never quotes a statement the organisation has since retracted while still showing that the retraction happened.

## Auto-append on every parent lifecycle transition

RG-INC-09. Every lifecycle transition on the parent [Incident](incident.md) automatically appends one entry with `source = lifecycle`, carrying the transition label as the summary, the acting user as `author`, the transition comment as `detail` and the transition time as `occurred_at`. This is what keeps the narrative and the state machine from diverging : an incident cannot move from `contained` to `eradicated` without the chronology saying so, and a reader of the chronology alone can reconstruct the whole process.

The append lives in the `Incident.transition_to()` override (RG-INC-08), which is the one place that binds all three surfaces : the web stepper (`core/workflow_views.py`), the DRF `LifecycleAPIMixin` and the MCP transition tool all funnel through `BaseModel.transition_to`. It runs inside the transition's transaction, so a rolled-back transition leaves no entry and a committed transition always leaves exactly one.

**Ordering with auto-created sibling rows.** Two incident transitions create governed sibling rows : `detected -> triaged` instantiates the [IncidentNotification](incident-notification.md) obligations, and `recovered -> post_incident_review` creates the [PostIncidentReview](post-incident-review.md). Neither row may be created directly in its domain step : `_ensure_initial_step()` fires only on a blank or unknown `workflow_state`, so an ordinary insert lands in `draft`, and an explicitly assigned domain step would stick but would leave **no `core.LifecycleEvent` row**. A `PostIncidentReview(...)` saved with `workflow_state="scheduled"` would hold that step with no recorded entry into the register. Each auto-creation path must therefore `save()` the row and then call `transition_to("scheduled" | "assessed", user, enforce_permission=False)` in the same transaction. The lifecycle timeline entry describing the creation is written **after** that transition has completed, so the narrative never claims a row is in a step it has not actually reached.

**Where a hole can appear.** Any future code path that assigns `workflow_state` directly instead of calling `transition_to()`, and any bulk import that writes incident rows without replaying their transitions, produces a chronology with a gap while the lifecycle history stays complete. There is no way to detect that from the timeline alone. The module therefore ships a reconciliation check (see below) and forbids direct `workflow_state` assignment in review.

## The three overlapping audit trails

An incident carries three record sets that describe overlapping facts. They are not redundant, they answer different questions, and reconciling them at audit time is real work. This table is what the docs owe the auditor.

| Trail | What it records | Written by | Authoritative for |
|---|---|---|---|
| `core.LifecycleEvent` | One immutable row per performed transition : `lifecycle_name`, `from_step`, `to_step`, `actor`, comment, timestamp, plus the cleaned data of any per-transition form. Generic (content type), so it covers every lifecycle-bearing entity in the module. | `BaseModel.transition_to()` only. | **The process.** Which state the incident was in, from when to when, who moved it and on what stated grounds. This is the record of whether the documented procedure was followed, and it is the one to cite for a permission or approval question. |
| `HistoricalRecords` (django-simple-history) | A full row snapshot per `save()`, with the acting user and the change reason, on every entity in the module including this one. | Every `save()`, including saves that write no narrative. | **The data.** What a given field held at a given instant, and whether it changed outside the documented flow. This is the tamper-detection trail and the only one that can expose an edit nobody narrated. |
| `IncidentTimelineEntry` | Free-text narrative, one entry per act, `occurred_at` distinct from `recorded_at`, attributed to a named author, correctable only by supersession. | Responders, plus the transition override (`source=lifecycle`) and background jobs (`source=system`). | **The facts.** What actually happened in the world, in real-world order, in words. This is the account a regulator or a court reads, and the source of the GDPR Art. 33(3)(a) description. It is the only trail that can be backdated, which is exactly why it is append-only and attributed. |

Reading rules, applied in this order when the three disagree :

1. A question about **state** ("was it contained before the notification went out?") is answered by `LifecycleEvent`. The timeline can be backdated; the lifecycle history cannot.
2. A question about **a field value** ("when did severity become critical?") is answered by `HistoricalRecords`. The narrative may summarise a change loosely; the historical row is exact.
3. A question about **the world** ("what did the responder see at 10:42?") is answered by the timeline. Neither of the other two records observations.
4. A `source=lifecycle` timeline entry with no matching `LifecycleEvent`, or a `LifecycleEvent` on an incident with no matching entry, is a defect and is reported as one. The incident register export includes a reconciliation line stating whether the counts match, so a hole is visible on the document the auditor is holding rather than discovered by interview.

`core.history.build_timeline` already merges `LifecycleEvent` and `HistoricalRecords` into the generic history panel; the chronology card is rendered separately and deliberately, because mixing a narrative written for humans into a diff feed written for machines makes both unreadable.

## Scope and tenancy

RG-INC-38. `IncidentTimelineEntry` is not a `ScopedModel` and never carries its own `scopes`. It inherits the parent incident's scope through `scope_parent_lookup = "incident__scopes"`, so it can never drift out of alignment when the incident is re-scoped.

Phase 1 must **extend three call sites** for that inheritance to be real, because scope inheritance for non-`ScopedModel` children is not currently enforced everywhere :

- `mcp/tools.py` `_filter_by_scopes()` handles `context.Scope` and a direct `scopes` M2M, then returns the queryset unfiltered. A `parent_lookup` parameter is added and threaded through `_register_crud` / `_list_handler` / `_get_handler`, otherwise `list_incident_timeline_entries` returns every entry on the instance to any holder of `incidents.incident.read`.
- `core/workflow_views.py` guards with `hasattr(obj, "scopes")`, so a non-scoped child is reachable cross-scope. The guard is extended to honour a model-level `scope_parent_lookup`. (This entity exposes no transition endpoint, but its siblings do, and the fix is one guard.)
- `core/history_views.py` carries the same `hasattr(obj, "scopes")` guard, so the full history of a timeline entry is otherwise readable cross-scope.

These three changes are core work in the phase-1 PR, not an incidents-app detail, and they are logged under a `### Security` entry in `CHANGELOG.md`.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-09 | Every lifecycle transition on an Incident automatically appends an `IncidentTimelineEntry` with `source=lifecycle`, carrying the transition label, the actor and the comment, so the narrative and the state machine can never diverge. |
| RG-INC-10 | The incident chronology is append-only. `save()` refuses any update to an existing row and `delete()` refuses outright, both raising `LifecycleProtectedError`; no update or delete route exists on the web, API or MCP surfaces. A correction is a NEW entry of type `correction` pointing at `superseded_entry` with a non-blank `correction_reason`. This is a Python-level guarantee : `QuerySet.update()`, `bulk_update()`, cascade deletion and raw SQL bypass it, and `HistoricalRecords` therefore makes tampering DETECTABLE, not impossible. The module docs state this to the auditor rather than claiming an immutability the schema does not provide. |
| RG-INC-16 | Reopening a closed incident requires `approve` and a mandatory comment, clears `closed_at`, and appends a timeline entry. The original closure remains in the lifecycle history. |
| RG-INC-38 | Scope tenancy : the chronology is never independently scoped and inherits the incident's scope through `scope_parent_lookup="incident__scopes"` on the web, API and MCP surfaces. |

## Endpoints

### REST

Base path `/api/v1/incidents/`, router registration `timeline-entries`. The viewset is **create, list and retrieve only** : `http_method_names` is restricted so no `PUT`, `PATCH` or `DELETE` route is generated at all, matching the append-only rule at the routing layer rather than only in the serializer.

- `GET /api/v1/incidents/timeline-entries/` : list, filters `incident`, `entry_type`, `source`, `is_evidence`, `occurred_after`, `occurred_before`.
- `POST /api/v1/incidents/timeline-entries/` (+ `POST .../batch/` via `BatchCreateMixin`, max 100 items, non-atomic, per-item `{index, status, id}`).
- `GET /api/v1/incidents/timeline-entries/<uuid>/`.
- `GET /api/v1/incidents/timeline-entries/<uuid>/history/` via `HistoryAPIMixin`.

Viewset stack : `BatchCreateMixin`, `ScopeFilterAPIMixin` (with `scope_parent_lookup = "incident__scopes"`), `HistoryAPIMixin`, `CreatedByMixin`, `viewsets.ModelViewSet`. `LifecycleAPIMixin` is **not** mixed in : the entity runs no lifecycle, so no `transition/` route exists. Permissions use `ModulePermission` with `permission_module = "incidents"` and an explicit `permission_feature`, following the newest module precedent (`trust_center/api/views.py`) rather than another app's `ModulePermission` subclass. `recorded_at`, `created_at`, `updated_at`, `version` and `author` are read-only; `author` is stamped from the request user.

### MCP

- `create_incident_timeline_entry` : append one entry to an incident's chronology. Requires `incidents.incident.create`.
- `list_incident_timeline_entries` : read the chronology, filters `incident_id`, `entry_type`, `source`, `is_evidence`. Requires `incidents.incident.read`. Scope-filtered through `incident__scopes`.

There is **no update and no delete tool**, deliberately : the entity is create-and-read only on every surface, and an agent must not be able to rewrite an incident narrative. `entry_type` and `source` carry explicit `enum` lists in `field_overrides`, and `detail` is declared with `_html_field()`.

## Permissions

Gated by the parent incident's codenames : reading the chronology needs `incidents.incident.read`, appending needs `incidents.incident.create`. There is no `incidents.timeline_entry` feature, and there will never be one : RG-INC-39 caps the module at exactly six features (`incident`, `security_event`, `evidence`, `notification`, `review`, `response_plan`), each with the five standard actions, so the six `SYSTEM_GROUPS` suffix filters grant the module unchanged and the group matrix screen renders every codename.

Because the entity is append-only, the `incidents.incident.update`, `.delete` and `.approve` actions have no meaning here : no route consumes them.

## UI

Rendered as the **Chronology** card in the left column of the incident detail page (strict 2-column layout, no nav-tabs, per the platform's detail-page doctrine) :

- Entries ordered by `occurred_at` ascending, so the card reads top to bottom as the incident unfolded.
- Each row shows `occurred_at`, the entry-type icon (Bootstrap Icons only), the author avatar and the summary, with `detail` in a Bootstrap collapse.
- `source = lifecycle` entries are visually distinguished from hand-written ones : a muted background and a system icon, so a reader can tell instantly which parts of the narrative the machine wrote.
- `recorded_at` is shown as a relative hint next to `occurred_at` whenever the two differ by more than a few minutes, since the delay is itself meaningful.
- Superseded entries render struck-through with a link to their correction; corrections render with a back-link and the `correction_reason` always visible, never collapsed.
- An **Add entry** form sits inline at the foot of the card and posts over HTMX into the `#timeline-entries` partial, so a responder never leaves the incident page mid-incident. The form has no edit or delete affordance anywhere.
- `is_evidence` entries carry a small marker indicating they will be quoted verbatim in regulatory filings.

The card must render correctly in light and dark mode and on mobile widths; the inline add form in particular is checked at small widths alongside the incident page's other sticky elements.

## Translations

Every user-facing string is wrapped and given a French translation in `locale/fr/LC_MESSAGES/django.po`. Several of this entity's labels collide with `msgid` values that already exist in the catalogue, and a duplicate `(msgctxt, msgid)` pair makes `manage.py compilemessages` fail, which the CI workflow runs **before** `pytest`. The colliding labels here are **Observation**, **Action**, **Decision**, **Evidence**, **System**, **Manual** and **Import**.

Those seven are declared with `pgettext_lazy("incident", ...)` in `incidents/constants.py` and rendered with `{% trans "..." context "incident" %}` in templates, and the `.po` file carries a matching `msgctxt "incident"` block for each. `Communication`, `Escalation`, `External input`, `Correction` and `Lifecycle transition` are new `msgid` values and are added bare.

The `lifecycle_from_json` trap does **not** apply to this entity : it re-wraps stored step labels with bare `gettext_lazy` after the `post_migrate` round-trip through `LifecycleDefinition`, so a step label's `msgctxt` is lost. This entity declares no lifecycle and no steps, so its labels are plain field choices that never make that round trip. The trap does apply to its parent [Incident](incident.md), whose step labels include the colliding `Draft`, `Closed` and `Archived` : see that file.

## References

- ISO/IEC 27001:2022 A.5.26 (response to information security incidents) : the response must be recorded.
- ISO/IEC 27035-2 (guidelines to plan and prepare for incident response) : the incident chronology as a response artefact.
- GDPR Art. 33(3)(a) : the notification must describe the nature of the breach and the facts relating to it. The `is_evidence` entries are that description's source.
- NIS2 Art. 23(4)(d) : the final report's detailed description of the incident, its severity and its impact.
- [Incident](incident.md) : the parent, its lifecycle, and the transition override that auto-appends entries.
- [IncidentResponseAction](incident-response-action.md) : the typed operational steps entries can point at through `related_action`.
- [IncidentEvidence](incident-evidence.md) and [EvidenceCustodyEvent](evidence-custody-event.md) : the A.5.28 evidence register and its own append-only ledger, which follows the same prevention-plus-detection framing.
- [README.md](README.md) : module business rules, permission codenames, scope inheritance and the phase plan.
- [governance/workflow.md](../governance/workflow.md) and [governance/lifecycle.md](../governance/lifecycle.md) : the lifecycle framework the parent plugs into, and `LifecycleEvent`.
- [governance/history.md](../governance/history.md) : `HistoricalRecords` and the merged history timeline.

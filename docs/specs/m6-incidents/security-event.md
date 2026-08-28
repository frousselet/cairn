# SecurityEvent

`incidents.models.security_event.SecurityEvent`

The register of reported information security **events** and **weaknesses** : ISO/IEC 27001:2022 **A.6.8 (reporting of information security events)** on the way in, and **A.5.25 (assessment and decision on information security events)** on the way out.

Every reported occurrence enters here, and **it is not an incident until a named person decides it is**. That single constraint is the whole point of the entity. It turns the promotion decision into an auditable, permissioned, comment-bearing lifecycle transition instead of an implicit data entry, and it is the only way to answer the question every ISO 27001 auditor asks : *show me the events you decided were **not** incidents, and who decided.* A design that jumps straight to an incident table with a status column cannot answer it at all, because the events that were correctly dismissed leave no trace.

File: `incidents/models/security_event.py`

`ScopedModel` subclass : UUID PK, sequential `reference` (prefix **`EVNT`**, e.g. `EVNT-1`), `scopes` M2M, `tags`, `version`, `created_by`, `django-simple-history` audit trail, and the dedicated **`security_event`** lifecycle. `workflow_perm_namespace` is overridden to `incidents.security_event` : the default `app_label.model_name` would spell `incidents.securityevent`, which matches no feature in `PERMISSION_REGISTRY`, and every transition would then be refused for everyone.

## The event / incident / weakness distinction

The three words are not synonyms, and A.6.8 and A.5.25 rest on keeping them apart:

- an **event** is an identified occurrence of a system, service or network state indicating a possible breach of policy, a failure of controls, or a previously unknown situation that may be security-relevant;
- a **weakness** is a reported flaw that has **not** been exploited : an unlocked door, an unpatched host, a shared credential, a mis-scoped bucket;
- an **incident** is one or more unwanted or unexpected events that a **named person has assessed** as having a significant probability of compromising business operations and threatening information security.

`SecurityEvent` carries the first two through `event_class`. The third is a separate entity, [Incident](incident.md), reachable only through the `under_assessment -> confirmed_incident` transition. A confirmed weakness is promoted into the **existing** `risks.Vulnerability` register, never into a parallel weakness table : two weakness registers would be two answers to *what do we know is broken*.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `EVNT-N`, unique | Business reference |
| `scopes` | relation | M2M -> `context.Scope` | ISMS scopes the event belongs to |
| `title` | string | required, max 255 | Short label of what was observed |
| `description` | text | optional, HTML | What was observed, in the reporter's own words. Never rewritten on promotion : the original report is part of the A.6.8 record. |
| `event_class` | enum | required, default `event` | `SecurityEventClass`. Governs which promotion targets are legal (RG-INC-03). |
| `category` | enum | optional, blank default | `risks.constants.ThreatCategory` (23 values). Provisional classification, refined on promotion. |
| `detection_source` | enum | required, default `other` | `DetectionSource` : how the event surfaced |
| `source_reference` | string | optional, max 255, blank default | External identifier : SIEM alert id, ticket number, CERT bulletin reference |
| `occurred_at` | datetime | optional | Best estimate of when the occurrence started |
| `detected_at` | datetime | required, indexed | When it was detected. Base of the mean-time-to-detect KPI. |
| `reported_at` | datetime | required, indexed, `>= detected_at` | When it reached the incident response function. `reported_at - detected_at` **is** the A.6.8 reporting delay that the control's "as quickly as possible" is measured against. Enforced in `clean()`. |
| `reporter` | relation | FK -> User, `SET_NULL`, optional | Internal reporter. Reverse accessor `reported_security_events`. Null when the report is anonymous or external. |
| `reporter_label` | string | optional, max 255, blank default | Free-text reporter identity for external or non-user reporters (customer, researcher, authority) |
| `is_anonymous` | boolean | required, default `False` | Reported through the anonymous channel A.6.8 requires. `CheckConstraint event_anonymous_has_no_reporter` : `is_anonymous = False OR (reporter IS NULL AND reporter_label = '')`. The database, not a form, is what guarantees the channel is actually anonymous. |
| `assessed_by` | relation | FK -> User, `SET_NULL`, optional | Person who performed the A.5.25 assessment. Reverse accessor `assessed_security_events`. Stamped by the transition. |
| `assessed_at` | datetime | optional, **write-once** | When the assessment began. Stamped by the `transition_to()` override; never editable in a form, a serializer or an MCP writable list. |
| `assessment_notes` | text | optional, blank default | The reasoning behind the decision. Required non-blank to leave `under_assessment` **by any route** (RG-INC-05) : an undocumented assessment is not an assessment. |
| `triage_decision` | enum | optional, blank default | `EventTriageDecision`. Mirrors the terminal step and is set by the `transition_to()` override, kept as a column so filters, list facets and MCP enums never have to read the lifecycle. |
| `workflow_state` | string | indexed, default `draft` | Lifecycle step (`security_event`) |
| `tags` | relation | M2M -> `context.Tag` | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | Timestamps |

### Relations

| Name | Type | Target | Reverse accessor | Description |
|---|---|---|---|---|
| `incident` | FK, `SET_NULL`, optional | [Incident](incident.md) | `source_events` | The incident this event was promoted into. Several events may feed one incident; an event promotes into at most one (RG-INC-06). |
| `vulnerability` | FK, `SET_NULL`, optional | `risks.Vulnerability` | `source_events` | The vulnerability a confirmed weakness was promoted into. No parallel weakness register. |
| `duplicate_of` | FK -> self, `SET_NULL`, optional | SecurityEvent | `duplicates` | The earlier event this one repeats. Also the link used when a previously reported weakness is later exploited (RG-INC-03). |
| `reported_by_supplier` | FK, `SET_NULL`, optional | `assets.Supplier` | `reported_security_events` | Third-party notification (NIS2 supply chain, GDPR Art. 33(2) inbound) |
| `affected_support_assets` | M2M | `assets.SupportAsset` | `security_events` | |
| `affected_essential_assets` | M2M | `assets.EssentialAsset` | `security_events` | |
| `affected_sites` | M2M | `context.Site` | `security_events` | |

> `reported_security_events` is used as the reverse accessor on **two** different targets : `assets.Supplier` (for `reported_by_supplier`) and `AUTH_USER_MODEL` (for `reporter`). This is legal because the targets differ, but it is genuinely confusing to read : `user.reported_security_events` and `supplier.reported_security_events` mean different things. Always name the model when writing either.

### Meta

- `ordering = ["-reported_at"]`
- `CheckConstraint event_incident_decision_requires_incident` : `Q(triage_decision != "incident") | Q(incident__isnull=False)`
- `CheckConstraint event_weakness_decision_requires_vulnerability` : `Q(triage_decision != "weakness") | Q(vulnerability__isnull=False)`
- `CheckConstraint event_anonymous_has_no_reporter`

The first two constraints are the database half of RG-INC-02 : the transition gate refuses the promotion, and the constraint refuses the row, so neither a raw SQL insert nor a `QuerySet.update()` can leave a "promoted" event that points at nothing.

## Enumerations

### SecurityEventClass

| Value | Label |
|---|---|
| `event` | Event |
| `weakness` | Weakness |

### EventTriageDecision

| Value | Label |
|---|---|
| `incident` | Promoted to incident |
| `weakness` | Confirmed weakness |
| `duplicate` | Duplicate |
| `false_positive` | False positive |
| `no_action` | No action required |

### DetectionSource

Declared once in `incidents/constants.py` and shared with [Incident](incident.md).

| Value | Label |
|---|---|
| `internal_monitoring` | Internal monitoring |
| `soc_alert` | SOC or SIEM alert |
| `employee_report` | Employee report |
| `customer_report` | Customer report |
| `supplier_notification` | Supplier notification |
| `authority_notification` | Authority notification |
| `researcher` | External researcher |
| `audit` | Audit |
| `penetration_test` | Penetration test |
| `threat_intel` | Threat intelligence |
| `other` | Other |

## Lifecycle

`LIFECYCLE_NAME = "security_event"`, `layout="graph"`, generated by `lifecycle_from_state_flags()` in `incidents/lifecycles.py` from the state and transition constants in `incidents/constants.py`, and registered from `IncidentsConfig.ready()`.

Unlike the `incident` and `incident_evidence` lifecycles, this one needs no step trigger, so it keeps the generated form the project's rules prescribe. It does, however, declare **both** bookend steps explicitly - see below.

### Steps

| Code | Label | StepKind | In reports | Linkable | Deletable | Tone | Meaning |
|---|---|---|---|---|---|---|---|
| `draft` | Draft | `DRAFT` | no | no | **yes** | `neutral` | Being written up; not yet in the register |
| `reported` | Reported | `INTERMEDIATE` | **yes** | no | **yes** | `secondary` | In the A.6.8 register, awaiting assessment. Still deletable : a genuine mis-entry made two minutes ago should not need an approver to remove, and nothing downstream references it yet. |
| `under_assessment` | Under assessment | `INTERMEDIATE` | **yes** | no | no | `info` | The A.5.25 judgement is in progress; `assessed_by` and `assessed_at` are stamped |
| `confirmed_incident` | Promoted to incident | `ARCHIVED` (terminal) | **yes** | **yes** | no | `danger` | Assessed as an incident; `incident` FK set |
| `confirmed_weakness` | Confirmed weakness | `ARCHIVED` (terminal) | **yes** | **yes** | no | `warning` | Assessed as a real weakness; `vulnerability` FK set |
| `discarded` | Discarded | `ARCHIVED` (terminal) | no | no | no | `muted` | Duplicate, false positive, or genuinely nothing to do. **This is the step an auditor asks to see.** |
| `archived` | Archived | `ARCHIVED` | no | no | no | `muted` | The generic exit, declared **explicitly** |

`discarded` keeps `counts_in_reports=False` because a false positive is not a security event of record; the *number* of discarded events is still reportable through a direct queryset, and the A.6.8 evidence an auditor wants is the individual rows with their `assessment_notes`, not a KPI.

### Transitions

`permission_action` is appended to `workflow_perm_namespace` (`incidents.security_event`).

| Verb | Transition | `permission_action` | `requires_comment` | Side effects |
|---|---|---|---|---|
| Report | `draft -> reported` | `update` | no | Enters the A.6.8 register |
| Start assessment | `reported -> under_assessment` | `update` | no | Stamps `assessed_by` (the acting user) and `assessed_at` |
| Promote to incident | `under_assessment -> confirmed_incident` | `update` | no | Sets `triage_decision = incident`; copies `detection_source`, `category` and the affected-asset links onto the incident |
| Promote to vulnerability | `under_assessment -> confirmed_weakness` | `update` | no | Sets `triage_decision = weakness` |
| Discard | `under_assessment -> discarded` | **`approve`** | **yes** | The comment is written into `assessment_notes` **and** into the immutable `core.LifecycleEvent`; `triage_decision` is set to `duplicate`, `false_positive` or `no_action` from the form |
| Reopen assessment | `discarded -> under_assessment` | `update` | **yes** | Clears `triage_decision`; the original discard stays in the lifecycle history |
| Archive | `* -> archived` | **`approve`** | **yes** | Hand-declared, not auto-wired |
| Restore | `archived -> draft` | **`approve`** | no | Hand-declared |

> **Both bookend edges are hand-declared, and so is `draft -> reported`.** `lifecycle_from_state_flags()` auto-wires `draft -> <initial step>`, `ANY -> archived` and `archived -> draft` **only when the corresponding step is absent** from the state-flag list (`core/lifecycle.py` `lifecycle_from_state_flags()`). This lifecycle declares `draft` and `archived` explicitly, precisely so nothing is auto-wired : the auto-wired archive and restore edges carry **no `permission_action` and no `requires_comment`**, and `user_can_perform()` (`core/lifecycle.py` `user_can_perform()`) allows any transition whose `permission_action` is empty. Left generated, they would give any holder of the transition endpoint an `archive -> restore -> delete` path out of a `reported` or `under_assessment` event, destroying an A.6.8 record. All three edges are therefore listed in `SECURITY_EVENT_TRANSITIONS` with explicit actions.

### Transition gates

Per RG-INC-08, every gate below lives in a `transition_to()` override on `SecurityEvent`, **never** in `Transition.form_class`, `allowed_roles` or `allowed_users`. `lifecycle_to_json()` (`core/lifecycle.py` `lifecycle_to_json()`) omits those three fields by design, `lifecycle_from_json()` rebuilds transitions without them, and `get_lifecycle()` prefers the `post_migrate`-seeded `LifecycleDefinition` row over the code default - so a gate declared that way is silently dead on every migrated database. All three write surfaces (`core/workflow_views.py` `WorkflowTransitionView.post()`, `accounts/api/mixins.py` `_lifecycle_transition()`, `mcp/tools.py` `_transition_handler()`) funnel through `BaseModel.transition_to()`, so the model override is the one place that binds web, API and MCP at once.

| Gate | Transition | Refused unless |
|---|---|---|
| **G-01 Documented assessment** (RG-INC-05) | every transition leaving `under_assessment` | `assessment_notes` is non-blank. This applies to promotion **and** to discarding, by any route including MCP. |
| **G-02 Incident target** (RG-INC-02) | `under_assessment -> confirmed_incident` | The `incident` FK is non-null. Also a DB `CheckConstraint`. |
| **G-03 Weakness cannot become an incident** (RG-INC-03) | `under_assessment -> confirmed_incident` | `event_class != weakness`. A weakness that has actually been exploited is a **new** event of class `event`, linked back through `duplicate_of`, so the original reporting history stays intact and the reporting delay of the exploitation is measured from its own detection. |
| **G-04 Vulnerability target** (RG-INC-02) | `under_assessment -> confirmed_weakness` | The `vulnerability` FK is non-null. Also a DB `CheckConstraint`. |
| **G-05 Named discard** (RG-INC-04) | `under_assessment -> discarded` | The actor holds `incidents.security_event.approve` and supplies a comment. The comment is persisted into `assessment_notes`, not only into the event ledger, so the register itself is readable without joining the history. |
| **G-06 One decision only** | any promotion transition | `triage_decision` is blank or matches the target. A single event never carries two verdicts. |
| **G-07 Write-once stamps** (RG-INC-12) | all | `assessed_at` is stamped by the override and never by a form, serializer or MCP field. |

### Auto-created rows and the initial step

`BaseModel.save()` calls `_ensure_initial_step()` (`context/models/base.py` `BaseModel._ensure_initial_step()`), and `Lifecycle.initial_step` (`core/lifecycle.py` `Lifecycle.initial_step`) returns the single `StepKind.DRAFT` step. The `workflow_state` field default is the literal `"draft"`, which **is** a valid step here, so `_ensure_initial_step()` leaves it untouched and every new row lands in `draft` - not in `reported`.

**No row in this module is ever "created in" a domain step.** Any path that needs a `SecurityEvent` to arrive already reported (a bulk import, an inbound integration, the seed) must, inside one `transaction.atomic()`:

```python
event = SecurityEvent(...)
event.save()
event.transition_to("reported", user, enforce_permission=False)
```

Assigning `workflow_state="reported"` at insert would stick - the snap only fires on a blank or unknown value - but it would leave **no `core.LifecycleEvent` row**, so the event would have no recorded entry into the A.6.8 register, which is exactly the evidence the register exists to hold.

## Promotion to an incident

Promotion is one atomic act, not a sequence a user can abandon halfway:

1. The event is in `under_assessment`, `event_class = event`, and `assessment_notes` is non-blank.
2. An [Incident](incident.md) is created in `draft` and immediately transitioned to `detected` (`save()` then `transition_to("detected", user, enforce_permission=False)`), copying `detection_source`, `category`, `affected_support_assets`, `affected_essential_assets`, `affected_sites` and `scopes` from the event. `Incident.reporter` is taken from the event's `reporter` when set.
3. The event's `incident` FK is set, `triage_decision` becomes `incident`, and the event transitions to `confirmed_incident`.

On the web surface this runs from the event detail page's stepper; on MCP it is the single bespoke `declare_incident_from_event` tool, which exists precisely so an agent cannot leave a half-promoted event behind.

Promotion to a **vulnerability** follows the same shape against the existing `risks.Vulnerability` register, which already carries `cve_references` and `affected_assets`. The event's `assessment_notes` are what justify the entry.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-01 | A `SecurityEvent` is never an incident. An [Incident](incident.md) exists only after an explicit, permissioned A.5.25 assessment transition on the event, or a direct declaration recorded with a `detection_source` and a named declarer. |
| RG-INC-02 | Exactly one triage decision per event. Reaching `confirmed_incident` requires a non-null `incident` FK; reaching `confirmed_weakness` requires a non-null `vulnerability` FK. Both are enforced by DB `CheckConstraint`s **as well as** by the transition gate. |
| RG-INC-03 | An event with `event_class = weakness` can never be promoted to an incident. A weakness that has actually been exploited is a **new** event of class `event`, linked to the weakness through `duplicate_of`, so the reporting history stays intact. |
| RG-INC-04 | Discarding an event requires `incidents.security_event.approve` and a mandatory comment; the comment is written into `assessment_notes` and into the immutable `core.LifecycleEvent`. |
| RG-INC-05 | `assessment_notes` must be non-blank to leave `under_assessment` **by any route**. An undocumented assessment is not an assessment. |
| RG-INC-06 | Several events may promote into one incident (`Incident.source_events`); an event promotes into at most one incident. |
| RG-INC-12 | `assessed_at` is stamped by the `transition_to()` override only : excluded from every `ModelForm`, `read_only` in every serializer, absent from every MCP writable list. Write-once is prevented at application level and **detected** through `HistoricalRecords`; `QuerySet.update()`, `bulk_update()` and raw SQL bypass `save()`. |
| RG-INC-37 | Every report, KPI, calendar feed, kanban bucket and link picker filters through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. No `security_event` state literal appears outside `incidents/constants.py`. |
| RG-INC-38 | `SecurityEvent` is a `ScopedModel` and carries its own `scopes`, so `ScopeFilterMixin` and `ScopeFilterAPIMixin` filter it with no extra work. Scopes are copied onto the incident it promotes into. |

## Endpoints

### REST

- `GET /api/v1/incidents/security-events/` : list, filtered by `SecurityEventFilter` (`status`, `event_class`, `triage_decision`, `detection_source`, `is_anonymous`, `reported_after` / `reported_before`)
- `POST /api/v1/incidents/security-events/` and `POST /api/v1/incidents/security-events/batch/` (max 100 items, non-atomic, per-item `{index, status, id, reference}`)
- `GET/PUT/PATCH/DELETE /api/v1/incidents/security-events/<uuid>/`
- `GET/POST /api/v1/incidents/security-events/<uuid>/transition/` : `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`, so every gate above applies identically to an API caller
- `GET /api/v1/incidents/security-events/<uuid>/history/` : `core.history.build_timeline`

`SecurityEventSerializer` / `SecurityEventListSerializer`, with `read_only_fields` covering `id`, `reference`, `created_by`, `created_at`, `updated_at`, `version`, `assessed_at`, `assessed_by` and `triage_decision`. `status` is exposed as `CharField(source="workflow_state", read_only=True)`. The viewset uses `ModulePermission` plus the module's `_IncidentViewSet` base (`permission_module = "incidents"`, `custom_action_map = {"transition": "update"}`), following `trust_center/api/views.py` `_ManagedViewSet`.

### MCP

- `_register_crud(server, "security_event", SecurityEvent, "incidents.security_event", ...)` generates `list_security_events`, `get_security_event`, `create_security_event`, `batch_create_security_events`, `update_security_event`, `delete_security_event`, `transition_security_event`, `security_event_allowed_transitions`, `get_security_event_history`.
- Filters : `status`, `event_class`, `triage_decision`, `detection_source`, `is_anonymous`.
- `declare_incident_from_event` (bespoke; requires `incidents.security_event.update` **and** `incidents.incident.create`) performs the full promotion atomically.
- `triage_decision`, `assessed_by` and `assessed_at` are absent from `writable_fields` : the decision is a transition, never a field write.

`mcp/tools.py` `HELP_TEXT` gains `SecurityEvent=EVNT` in the reference-prefix block, and `assistant/catalog.py` gains a read-only `list_security_events` `ToolSpec` with `detail_route="incidents:security-event-detail"`.

## Permissions

| Codename | Description |
|---|---|
| `incidents.security_event.read` | List / read events and weaknesses |
| `incidents.security_event.create` | Report an event or a weakness |
| `incidents.security_event.update` | Edit an event, start an assessment, promote it, reopen a discarded one |
| `incidents.security_event.approve` | Discard an event (the A.5.25 "this was not an incident" verdict), archive, restore |
| `incidents.security_event.delete` | Delete a `draft` or `reported` event |

Promotion to an incident additionally requires `incidents.incident.create`.

## UI

- **List** (`/incidents/events/`) : the same house stack as the incident list, with predefined filters for *Awaiting assessment* (`workflow_state = reported`), *Under assessment*, *Discarded* and *Weaknesses*. The *Awaiting assessment* count is the A.6.8 backlog and is surfaced in `list_rail_kpis`.
- **Detail** (`/incidents/events/<uuid>/`) : a strict 2-column card layout, no nav-tabs. Left column : *Observation* (description, category, detection source, source reference, occurred / detected / reported stamps with the reporting delay computed and shown); *Assessment* (`assessed_by`, `assessed_at`, `assessment_notes`); *Promotion targets* (the incident or vulnerability link, and the duplicate-of link). Right column, sticky : `{% workflow_badge %}`, the triage decision badge, the reporter avatar - replaced by an **"Anonymous report"** badge when `is_anonymous`, never by a blank - the reporting supplier, affected assets and sites, scopes, tags and the history trigger.
- The triage decision is driven **entirely** by the stepper : there is no decision select anywhere on the page.
- **Stepper** : `{% include "includes/lifecycle_stepper.html" %}` fed by `LifecycleStepperMixin`. This lifecycle has **four** `StepKind.ARCHIVED` steps (`confirmed_incident`, `confirmed_weakness`, `discarded`, `archived`), so the dagre renderer draws four detached exits : more than any existing Cairn lifecycle, and requiring an explicit visual check at desktop and mobile widths in **both** light and dark mode before merge.
- The anonymous reporting channel A.6.8 requires is served by the create form : ticking *Anonymous report* clears and disables the reporter and reporter-label inputs client-side, and the `CheckConstraint` enforces it server-side regardless.

## Translations

Several of this entity's labels collide with `msgid`s already present in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`.

**Enum labels, field verbose names and template strings** use `pgettext_lazy("incident", ...)` in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po`:

| String | Existing bare entry | Action |
|---|---|---|
| `SecurityEventClass.WEAKNESS` "Weakness" | `django.po` -> "Faiblesse" | `pgettext_lazy("incident", "Weakness")` |
| `DetectionSource.AUDIT` "Audit" | `django.po` -> "Audit" | `pgettext_lazy("incident", "Audit")` |
| `DetectionSource.OTHER` "Other" | `django.po` -> "Autre" | `pgettext_lazy("incident", "Other")` |
| "Evidence" (evidence links on the detail page) | `django.po` -> "Preuves" | `{% trans "Evidence" context "incident" %}` |

**Step and transition labels must never use `pgettext_lazy`.** `lifecycle_to_json()` stringifies each label with `str(...)` and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy` (`core/lifecycle.py` `lifecycle_from_json()`), so a `msgctxt` carried in code is lost after the `post_migrate` DB round-trip and the label resolves to whatever the bare `msgid` maps to. This lifecycle is safe as declared : "Draft" (`django.po` -> "Brouillon") and "Archived" (`django.po` -> "Archivé") are **reused** from the core bookend steps with the correct French, "Archive" and "Restore" are the existing core transition labels, and every other label ("Reported", "Under assessment", "Promoted to incident", "Confirmed weakness", "Discarded", "Report", "Start assessment", "Promote to incident", "Promote to vulnerability", "Discard", "Reopen assessment") is a new, non-colliding bare `msgid`. Note in particular that the `confirmed_weakness` **step** is labelled "Confirmed weakness", not "Weakness", which is what keeps it clear of the collision that the enum label has to solve with a `msgctxt`.

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- ISO/IEC 27001:2022 A.6.8 (reporting of information security events), A.5.25 (assessment and decision on information security events)
- ISO/IEC 27035-1 / -2 : the *detect and report* and *assess and decide* phases
- ISO/IEC 27001:2022 A.8.8 (technical vulnerability management) : a confirmed weakness promotes into the existing vulnerability register
- [Incident](incident.md) : what an event becomes when a named person decides it is one
- [IncidentResponsePlan](incident-response-plan.md) : `reporting_channels` documents how events reach this register, including the anonymous channel
- [README.md](README.md) : module business rules, permissions, notifications
- [governance/workflow.md](../governance/workflow.md) : the lifecycle framework this workflow plugs into
- [Vulnerability](../m4-risks/README.md), [Supplier](../m2-assets/supplier.md), [Site](../m2-assets/site.md)

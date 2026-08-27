# NotificationFiling

`incidents.models.filing.NotificationFiling`

The **filing log** : one append-only record per actual transmission made against an [IncidentNotification](incident-notification.md) obligation. Who sent what, to whom, when, through which channel, with the authority's case number and the verbatim content that left the organisation.

This is the evidence handed to an auditor or an inspector who asks *prove you filed the 72-hour notification*. The obligation says what was owed and when; the filing says what was actually done, and it is the only record that can answer the question with a document rather than a status.

File : `incidents/models/filing.py`

Phase 2. Not a `BaseModel` and not a `ScopedModel` : a plain `models.Model` with `ReferenceGeneratorMixin`, its own UUID primary key, sequential `reference` (prefix **`NFIL`**, e.g. `NFIL-12`), explicitly declared row timestamps, a `version` counter and a `django-simple-history` audit trail.

## Why this shape

**No lifecycle.** A transmission has no states. It happened, at a time, through a channel, with a content. Giving it a workflow would put a governance process around a fact, and would make the log filterable by a step that carries no meaning. The entity has no `workflow_state` column, `BaseModel._ensure_initial_step()` never runs against it, and it is deliberately invisible to `reportable()`, `linkable()` and `deletable_states()`. It is read through its parent obligation, always. What the filing *does* carry is `outcome`, which records the recipient's response - a fact about the world, not a state of our process.

**A reference prefix, unlike the chronology.** [IncidentTimelineEntry](incident-timeline-entry.md) deliberately has none, because `ReferenceGeneratorMixin._generate_next_reference()` scans every existing reference sharing the prefix on each insert and a live incident produces hundreds of narrative entries. Filings are the opposite shape : a busy obligation has two or three, a heavily contested one perhaps a dozen, and each one is **cited** - in correspondence with the authority, in the incident register export, in the Art. 33(5) extract, in a later legal exchange. "The 72-hour notification was filed as NFIL-12 on 14 March at 08:41 and supplemented by NFIL-19 on 21 March" is a sentence someone has to be able to write. The scan cost is paid a handful of times per incident and buys a citable identity, which is the trade the mixin exists for.

**Never rewritten.** A filing that can be edited after the fact is not evidence of what was sent. `content`, `subject`, `submitted_at`, `channel`, `was_late`, `is_correction` and `supersedes` refuse any update once the row exists. A correction to what the organisation told a regulator is a **new filing**, never an edit of the old one.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, `default=uuid.uuid4`, `editable=False` | Unique identifier |
| `reference` | string | auto-generated `NFIL-N`, unique, max 50 | Citable filing reference |
| `notification` | relation | FK -> [IncidentNotification](incident-notification.md), required, `CASCADE`, `related_name="filings"` | The obligation this transmission discharges, in whole or in part. `CASCADE` is safe : the obligation itself is `PROTECT`ed against deletion from `required` onward, and an obligation that can still be deleted has no filings by construction. |
| `submitted_at` | datetime | required, indexed, **immutable** | When the filing actually left the organisation. Not the time the row was typed : a portal submission recorded two hours later carries the submission time, and `created_at` reveals the delay. |
| `channel` | enum | required, default `portal`, max 20 | `NotificationChannel`, declared once in `incidents/constants.py` and shared with the parent obligation. |
| `recipient_name` | string | optional, max 255, blank default | The named desk, mailbox or person who received it, when it is finer-grained than the obligation's recipient (e.g. "CNIL - service des violations de données"). |
| `external_reference` | string | optional, max 200, blank default | The authority's case, ticket or receipt number. **Write-once completion field** : see [Append-only : what is actually guaranteed](#append-only--what-is-actually-guaranteed). |
| `subject` | string | optional, max 500, blank default, **immutable** | Subject line of the filing |
| `content` | text | optional, HTML, blank default, **immutable** | **Verbatim** content of what was sent. Never edited : a correction is a new row. This is the field an inspector reads. |
| `outcome` | enum | required, default `sent`, max 25 | `FilingOutcome` : the recipient's response. **Write-once completion field.** |
| `acknowledged_at` | datetime | optional | When the recipient acknowledged receipt of **this** filing. **Write-once completion field.** |
| `is_correction` | boolean | required, default `False`, **immutable** | Marks a corrective or supplementary filing (GDPR Art. 33(4) phased provision, or a response to a NIS2 information request). The first filing on an obligation is never a correction. |
| `was_late` | boolean | required, default `False`, **write-once, computed at insert** | Frozen lateness verdict for this filing, computed once from the obligation's `due_at` at the moment of insert and **never recomputed**. False when the obligation carries no `due_at`. |
| `proof_file_content` | binary | optional, `editable=False` | The filed document, the generated PDF or the portal receipt, stored as bytes following `Contract.file_content`, `Certificate.file_content` and `TrustCenterDocument.file_content`. Excluded from list serializers, from MCP `list_fields` and from `HistoricalRecords`. Capped by `INCIDENT_NOTIFICATION_MAX_PROOF_BYTES`. |
| `proof_filename` | string | optional, max 255, blank default | Original filename of the proof |
| `version` | int | `PositiveIntegerField`, default `1` | Row version counter, mirroring the `SupplierSubprocessor` precedent for non-`BaseModel` audit rows. A value other than `1` means a completion field was filled in after the insert, which is legitimate but visible. |
| `created_at` / `updated_at` | datetime | `auto_now_add` / `auto_now` | Row timestamps. Declared explicitly because `BaseModel` is not inherited. `created_at` versus `submitted_at` is the recording delay. |
| `history` | `HistoricalRecords(excluded_fields=["proof_file_content"])` | | Tamper **detection**. Any post-hoc write to a filing record is visible, including the permitted completion writes. |

### Relations

| Name | Type | Target | Reverse accessor | Description |
|---|---|---|---|---|
| `notification` | FK, `CASCADE`, required | [IncidentNotification](incident-notification.md) | `filings` | The obligation being discharged |
| `submitted_by` | FK -> User, `SET_NULL`, optional | User | `incident_filings` | Who transmitted it. `SET_NULL` rather than `PROTECT` : the filing's evidential weight rests on its content and its receipt, not on the account still existing, and `HistoricalRecords` keeps the name. |
| `supersedes` | FK -> self, `SET_NULL`, optional, **immutable** | NotificationFiling | `superseded_by` | The earlier filing on the **same obligation** that this one replaces. Null on a supplementary filing that adds information without retracting anything. |

### Meta

- `ordering = ["-submitted_at"]` : the most recent transmission first, which is what the detail page and the API caller both want. The obligation's *narrative* order is the reverse, and the UI renders it ascending.
- `CheckConstraint filing_supersedes_implies_correction` : `Q(supersedes__isnull=True) | Q(is_correction=True)`. A filing that replaces another is by definition a correction.
- `clean()` refuses a `supersedes` pointing at a filing on a **different** obligation. A supersession chain that crosses obligations would break the one guarantee this entity provides.
- `clean()` refuses `submitted_at` in the future.

## Enums

Reproduced verbatim from `incidents/constants.py` (DB value = Label).

### FilingOutcome

| Value | Label |
|---|---|
| `sent` | Sent |
| `acknowledged` | Acknowledged |
| `rejected` | Rejected |
| `information_requested` | Information requested |
| `superseded` | Superseded |

`information_requested` is the value that matters operationally : a NIS2 competent authority asking for more, or a supervisory authority reverting on a 72-hour filing, drives the parent obligation's `acknowledged -> drafted` transition and produces the next filing on the same row.

### NotificationChannel

Declared once in `incidents/constants.py` and shared with [IncidentNotification](incident-notification.md) : `portal`, `email`, `postal`, `phone`, `api`, `in_person`, `public_notice`. The full table is in that file.

## Append-only : what is actually guaranteed

The module states this plainly rather than claiming an immutability the schema does not provide.

**Prevention is at application level.** `save()` inspects `self._state.adding`. On an insert it proceeds. On any subsequent save it compares the incoming values against the stored row and raises `core.lifecycle.LifecycleProtectedError` (the house exception, the same one `BaseModel.delete()` raises when a lifecycle state forbids deletion) unless the only changed fields are the three completion fields below. `delete()` raises `LifecycleProtectedError` unconditionally.

**The narrow completion exception.** Exactly three fields may be written after the insert, exactly once each, and only from their insert value to a set value - never from one set value to another :

| Field | Why it cannot be known at insert |
|---|---|
| `outcome` | The recipient's response arrives after the transmission, sometimes days later |
| `acknowledged_at` | Same |
| `external_reference` | A portal returns a case number immediately, an email filing does not |

Every other field is immutable from the instant the row exists. This is the deliberate boundary : **what we said is frozen, what they answered is completable.** The exception is implemented in one place (`NotificationFiling.record_outcome()`), the `save()` guard refuses any other post-insert write including a second write to a completion field, and every completion write is historised, so a filing whose historical trail shows more than two rows has been touched more than the design allows.

One consequence is worth stating because it is easy to get wrong : **`FilingOutcome.SUPERSEDED` is not stamped on an old filing when a new one replaces it.** Doing so would be a post-insert write to a field outside the completion set. Supersession is **derived** from `filing.superseded_by.exists()`, which is what the UI and the exports read. The `superseded` value exists only for a historical import that records a filing already known to have been replaced.

**What bypasses the guard :**

- `QuerySet.update()` and `QuerySet.bulk_update()` issue SQL without calling `save()`.
- `QuerySet.delete()` and cascade deletion do not call `Model.delete()`. A cascade from the obligation therefore removes filings without the guard firing; in practice the obligation is undeletable from `required` onward and cannot have filings before that, but the mechanism is stated here so nobody discovers it during an audit.
- Raw SQL, a `manage.py shell` session and direct database access bypass Python entirely.

**Detection is via `HistoricalRecords`.** Every ORM-level write that does go through `save()` leaves a historical row with the acting user. The honest claim to make to an auditor is therefore : *tampering with the filing log is prevented on every supported path and detectable on the rest*, not *the filing log is immutable*. Real database-level immutability would need PostgreSQL rules or triggers, which `core.settings_test` (SQLite in memory, migrations disabled) cannot exercise; that divergence is not taken in this module, and if it is ever taken it must be taken deliberately and documented here.

## One obligation, successive filings

This is the entity's reason to exist, and it is worth spelling out against the two designs it replaces.

GDPR Art. 33(4) says that where, and in so far as, it is not possible to provide the information at the same time, the information **may be provided in phases without undue further delay**. A 72-hour notification is routinely filed with an approximate number of data subjects and a provisional description, and completed a week later. NIS2 works the same way by construction : Art. 23(4)(c) is an intermediate report *on request of the competent authority*, and an authority can ask more than once.

Two obvious models both fail :

- **Editing the original.** The record then says the organisation filed, on day one, a document it actually assembled on day eight. That is not what happened, and the difference is exactly what an inspection looks for. It also destroys the evidence of the *first* filing, which is the one the 72-hour clock is measured against.
- **A second obligation row.** The register then shows two GDPR Art. 33(1) obligations on one incident, each with its own clock, and the answer to *when did you notify* becomes ambiguous. Worse, the second row's `due_at` would be recomputed from the anchor and would look on time when the duty was discharged late.

The filing log resolves both. **The obligation stays one row : one duty, one clock, one decision, one lateness verdict.** Each transmission is a filing :

1. `NFIL-12`, `submitted_at` day 1, `is_correction = False`, `supersedes = null`, `outcome = sent`. This filing stamps the obligation's `first_submitted_at`, `late_by` and `sent_at`.
2. `NFIL-19`, `submitted_at` day 8, `is_correction = True`, `supersedes = null` : a supplementary Art. 33(4) filing that adds the confirmed subject count without retracting anything.
3. `NFIL-24`, `submitted_at` day 21, `is_correction = True`, `supersedes = NFIL-12` : a correction that replaces a statement made in the first filing. `NFIL-12` remains, verbatim and unmodified, and renders as superseded with a link to `NFIL-24`.

The obligation's lateness verdict never moves : it was set by `NFIL-12` and it is a fact about the 72-hour duty, not about the last thing anyone sent. A chain may be arbitrarily long, and `supersedes` is followed to its end when the register export quotes a statement, so a generated document never quotes text the organisation has since retracted while still showing, in an appendix, that the retraction happened.

An authority information request runs the same way : the obligation moves `acknowledged -> drafted` with a mandatory comment, the response is a new filing with `is_correction = True`, and the request itself is narrated in the incident's [chronology](incident-timeline-entry.md) with `entry_type = external_input`.

## The first filing freezes the clock

Creating the **first** filing on an obligation is a single atomic act performed through the obligation's `transition_to()` override (RG-INC-08), never by writing the filing alone. Inside one `transaction.atomic()` block it :

1. inserts the filing, computing `was_late` from `notification.due_at` against `submitted_at`;
2. stamps the obligation's `first_submitted_at = submitted_at`, `sent_at`, `sent_by` and `channel`;
3. computes the obligation's `late_by` as the positive part of `first_submitted_at - due_at`, or null when the obligation carries no `due_at`;
4. moves the obligation to `sent`;
5. recomputes `anchor_at` and `due_at` on every obligation in `notification.dependents` whose `clock_anchor` is `previous_stage` - this is the moment the NIS2 Art. 23(4)(d) one-month final-report clock actually starts;
6. appends a lifecycle entry to the incident's chronology.

After step 2 the obligation's `save()` stops recomputing `anchor_at` and `due_at` for good (RG-INC-28). A later correction to `Incident.awareness_at` - which stays editable, because facts change - therefore cannot move a filed obligation's deadline and cannot silently un-breach it. The full argument is in [The clock model](incident-notification.md#the-clock-model).

Subsequent filings insert normally and change none of the frozen values.

On MCP this is the bespoke `record_notification_filing` tool, which exists precisely so an agent cannot record a transmission without freezing the lateness verdict that goes with it. On the web it is the *Record filing* form on the obligation's stepper.

## Scope and tenancy

RG-INC-38. `NotificationFiling` is not a `ScopedModel` and never carries its own `scopes`. It is a grandchild of the incident and chains its parent's lookup : `scope_parent_lookup = "notification__incident__scopes"`.

Scope inheritance for non-`ScopedModel` children is **not currently enforced on three surfaces**, and phase 1 extends all three; this entity depends on that work being in place before it ships. The change is core work, logged under a `### Security` entry in `CHANGELOG.md` :

- `mcp/tools.py` `_filter_by_scopes()` handles `context.Scope` and a direct `scopes` M2M, then returns the queryset **unfiltered**. A `parent_lookup` parameter is added and threaded through `_register_crud` / `_list_handler` / `_get_handler`. Without it, `list_notification_filings` returns every filing on the instance - verbatim regulatory content included - to any holder of `incidents.notification.read`.
- `core/workflow_views.py` guards with `hasattr(obj, "scopes")`. This entity exposes no transition endpoint, but the obligation it hangs off does, and the fix is one guard.
- `core/history_views.py` carries the same `hasattr(obj, "scopes")` guard, so the full history of a filing is otherwise readable cross-scope.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-26 | Recording a filing requires only `incidents.notification.update`. Only the transitions that declare an obligation extinguished require `approve`, so the operator on a 24-hour clock is never blocked waiting for an approver. |
| RG-INC-28 | Lateness is frozen once : `IncidentNotification.first_submitted_at`, `IncidentNotification.late_by` and `NotificationFiling.was_late` are stamped at the first filing and never recomputed, so a later anchor correction can never silently un-breach a filed record. |
| RG-INC-29 | A notification's `content`, `channel` and `sent_at` are write-once once `sent_at` is set (prevention at application level, detection via `HistoricalRecords`). An amendment is an **additional filing** with `is_correction = True` and, where it replaces a statement, `supersedes`, on the **same** obligation - so the same-obligation relationship is never lost and the register never shows two answers to one duty. |
| RG-INC-37 | Every report, KPI, calendar feed and export filters through the governance helpers on the parent obligation. No state literal appears outside `incidents/constants.py`. |
| RG-INC-38 | Scope tenancy : filings are never independently scoped and chain the incident's scope through `scope_parent_lookup = "notification__incident__scopes"` on the web, API and MCP surfaces. |
| RG-INC-39 | Gated by `incidents.notification.*`. There is no `incidents.filing` feature and there will never be one : the module is capped at exactly six permission features. |

## Endpoints

### REST

Base path `/api/v1/incidents/`, router registration `notification-filings`. The viewset is **create, list, retrieve and one narrow completion `PATCH`** : `http_method_names` is restricted so no `PUT` or `DELETE` route is generated at all, matching the append-only rule at the routing layer rather than only in the serializer. A single `PATCH` route is exposed and accepts **only** the three completion fields, rejecting every other key with a 400 rather than silently ignoring it.

- `GET /api/v1/incidents/notification-filings/` : list, filters `notification_id`, `incident_id`, `channel`, `outcome`, `is_correction`, `was_late`, `submitted_after`, `submitted_before`.
- `POST /api/v1/incidents/notification-filings/` (+ `POST .../batch/` via `BatchCreateMixin`, max 100 items, non-atomic, per-item `{index, status, id, reference}`). Creating the first filing on an obligation performs the whole freeze described above, inside one transaction.
- `GET /api/v1/incidents/notification-filings/<uuid>/`
- `PATCH /api/v1/incidents/notification-filings/<uuid>/` : completion only (`outcome`, `acknowledged_at`, `external_reference`).
- `GET /api/v1/incidents/notification-filings/<uuid>/history/` via `HistoryAPIMixin`.
- `GET /api/v1/incidents/notification-filings/<uuid>/proof/` : a dedicated permission-checked and scope-checked detail action returning the proof bytes. `proof_file_content` never appears in a list or detail payload.

Viewset stack : `BatchCreateMixin`, `ScopeFilterAPIMixin` (with `scope_parent_lookup = "notification__incident__scopes"`), `HistoryAPIMixin`, `CreatedByMixin`, `viewsets.ModelViewSet`. `LifecycleAPIMixin` is **not** mixed in : the entity runs no lifecycle, so no `transition/` route exists. Permissions use `ModulePermission` with `permission_module = "incidents"` and `permission_feature = "notification"`, following the newest module precedent (`trust_center/api/views.py` `_ManagedViewSet`). `reference`, `was_late`, `created_at`, `updated_at`, `version` and `submitted_by` are read-only; `submitted_by` is stamped from the request user.

### MCP

- `record_notification_filing` (bespoke; requires `incidents.notification.update`) creates the filing and, when it is the first on its obligation, freezes `first_submitted_at`, `late_by` and `was_late` and starts any dependent clock, all atomically.
- `list_notification_filings` (bespoke; requires `incidents.notification.read`) reads the log, filters `notification_id`, `incident_id`, `outcome`, `is_correction`, `was_late`. Scope-filtered through `notification__incident__scopes`.
- `get_notification_filing_history` via the standard history handler.

There is **no update tool and no delete tool.** Completion is done through `record_filing_outcome` (requires `incidents.notification.update`), which sets `outcome`, `acknowledged_at` and `external_reference` once and refuses everything else - an agent must not be able to rewrite what an organisation told a regulator. `content` is declared with `_html_field()`, `channel` and `outcome` carry explicit `enum` lists in `field_overrides`, and `proof_file_content` is never readable or writable through MCP.

`mcp/tools.py` `HELP_TEXT` gains `NotificationFiling=NFIL` in the reference-prefix block.

## Permissions

Gated entirely by the parent obligation's codenames :

| Codename | Description |
|---|---|
| `incidents.notification.read` | Read the filing log and download a proof |
| `incidents.notification.update` | Record a filing and complete its outcome |

`create`, `delete` and `approve` have no meaning here : no route consumes them. Recording a filing is deliberately an `update` on the obligation rather than a `create` on a separate feature, because a filing is not an independent object - it is the discharge of a duty that already exists, and the person who can drive the obligation is the person who can file it (RG-INC-26).

## UI

Rendered as the **Filing history** table inside the *Filing* card on the [IncidentNotification](incident-notification.md) detail page. There is no standalone list page and no standalone detail page : a filing is meaningless outside its obligation.

- Rows ordered by `submitted_at` **ascending**, so the card reads as the exchange unfolded, with the reference, the channel icon (Bootstrap Icons only), `submitted_at`, `submitted_by`, `external_reference` and the outcome badge.
- A `was_late = True` row carries a semantic danger badge stating by how much, computed from the obligation's frozen `late_by` on the first filing. The badge uses the status palette, never the navy identity colour.
- Superseded rows render struck-through with a link to the filing that replaced them; the replacing row renders with a back-link. Supersession is read from `superseded_by`, never from a stored `outcome`.
- `is_correction` rows carry a distinct marker so a reader can see at a glance which parts of the exchange were phased provision (Art. 33(4)) rather than the original filing.
- `content` opens in a Bootstrap collapse, rendered verbatim, with a copy affordance : this is the text someone will need to quote.
- A **Record filing** form sits at the foot of the card and posts over HTMX into the `#notification-filings` partial, pre-filling `channel` and `recipient_name` from the obligation and `submitted_at` from now. It offers no edit and no delete affordance anywhere; completing an outcome is a separate, narrow inline control on the row itself.
- The proof download is a permission-checked and scope-checked action, never a raw media URL.
- The card must render correctly in light and dark mode and at mobile widths; the verbatim content collapse and the filing table are checked at small widths in particular, since regulatory content is long and must scroll inside its own container rather than widening the page.

## Translations

Every user-facing string is wrapped and given a French translation in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `manage.py compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`.

Two `FilingOutcome` labels already exist as bare `msgid`s with the correct French and are **reused as they stand**, adding no new entry : "Rejected" (`django.po` -> "Rejeté") and "Superseded" (`django.po` -> "Remplacé"). "Sent", "Acknowledged" and "Information requested" are new, non-colliding bare `msgid`s, as are the field labels "Filing", "Filing history", "Correction", "Supersedes" and "Proof".

`NotificationChannel` is declared once in `incidents/constants.py` and its colliding member is handled there : `EMAIL` uses `pgettext_lazy("incident", "Email")` because the bare "Email" entry (`django.po`) is shared with several hundred unrelated uses and the notification channel must be retranslatable ("Courriel") without touching them. `PHONE` reuses the existing bare "Phone" -> "Téléphone", which is correct as it stands. See [IncidentNotification](incident-notification.md#translations) for the full table.

The `lifecycle_from_json` trap does **not** apply to this entity : it re-wraps stored step labels with bare `gettext_lazy` after the `post_migrate` round-trip through `LifecycleDefinition` (`core/lifecycle.py` `lifecycle_from_json()`), so a step label's `msgctxt` is lost. This entity declares no lifecycle and no steps, so its labels are plain field choices that never make that round trip. The trap does apply to its parent obligation, whose step labels include the colliding "Draft", "Required" and "Archived" : see that file.

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- GDPR Art. 33(4) : *where, and in so far as, it is not possible to provide the information at the same time, the information may be provided in phases without undue further delay.* The reason this entity exists rather than an editable content field.
- GDPR Art. 33(1) and Art. 33(5) : the 72-hour duty the first filing is measured against, and the internal register a filing log is the evidence for.
- GDPR Art. 34(1) : communication to data subjects, which is frequently phased in the same way.
- NIS2 Art. 23(4)(b), (c) and (d) : the incident notification, the intermediate report **on request of the competent authority**, and the final report whose one-month clock starts at the first filing of the notification.
- DORA Art. 19 : initial, intermediate and final major ICT incident reports, which are three obligations, each with its own filings.
- ISO/IEC 27001:2022 clause 10.2 f) : retained documented information on the results of the action taken.
- [IncidentNotification](incident-notification.md) : the parent obligation, the clock model, and the transition that creates the first filing
- [Incident](incident.md) : `awareness_at` as the legal anchor, and why correcting it after a filing changes nothing
- [IncidentTimelineEntry](incident-timeline-entry.md) : the same prevention-plus-detection framing, and why it carries no reference prefix while this entity does
- [IncidentEvidence](incident-evidence.md) : when a receipt is itself registered as A.5.28 evidence, through `IncidentNotification.proof_evidence`
- [ReportingAuthority](reporting-authority.md) : the portal, mailbox and procedure a filing is transmitted through
- [README.md](README.md) : module business rules, permission codenames, scope inheritance and the phase plan
- [governance/history.md](../governance/history.md) : `HistoricalRecords` and the merged history timeline

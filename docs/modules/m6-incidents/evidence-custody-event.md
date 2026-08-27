# EvidenceCustodyEvent

`incidents.models.evidence.EvidenceCustodyEvent`

The chain of custody of an [IncidentEvidence](incident-evidence.md) item : one append-only row per handling act, answering the question ISO/IEC 27001:2022 **A.5.28 (collection of evidence)** actually asks, which is not *do you have the artefact* but **who held this item, when, where, and did the hash still match**.

File : `incidents/models/evidence.py`

Not a `BaseModel`, not a `ScopedModel` and not a `ReferenceGeneratorMixin` : a plain `models.Model` with its own UUID primary key, explicitly declared row timestamps, a `version` counter and a `django-simple-history` audit trail. The reasons are set out below and they are load-bearing : changing any of them changes what the evidence register is worth in front of a court or an authority.

## Why this is not a BaseModel

**No lifecycle.** A `BaseModel` runs a registered lifecycle and `_ensure_initial_step()` fires only on a blank or unknown `workflow_state`, so every ordinary insert lands in `draft`; an explicitly assigned domain step would stick, but it would leave **no `core.LifecycleEvent` row**, which is why the pattern is banned; the snap targets that lifecycle's DRAFT step. A custody act has no states : *"14:03, image handed to Forensics SARL, seal 44821, hash re-measured, matched"* is never draft, never pending, never validated. Giving it a lifecycle would put an approval workflow around a fact that has already happened, and would let a custody row exist in a step where it does not count. The entity therefore has no `workflow_state` column at all, and is deliberately invisible to `reportable()`, `linkable()` and `deletable_states()`. It is always read through its parent evidence item.

**Never edited.** A custody ledger that can be rewritten is not a custody ledger. `save()` refuses any write against an existing primary key and `delete()` refuses outright, both raising `core.lifecycle.LifecycleProtectedError` (the house exception, the same one `BaseModel.delete()` raises when a lifecycle step forbids deletion). A mistake is corrected by appending a further row whose `notes` state what the earlier row got wrong; the earlier row is never touched.

**Never deleted.** No delete view, no `DELETE` route, no MCP delete tool, no admin delete action. The entity is create-and-read only on every one of the three surfaces.

**No reference prefix.** `ReferenceGeneratorMixin._generate_next_reference()` selects every existing reference sharing the prefix, pulls the list into Python and takes the maximum, on **every single insert**. That is fine for a few hundred suppliers; it is the wrong shape for a ledger that takes a row on every lifecycle transition, every transfer, every read and every re-hash across the whole evidence register. Custody rows are cited by their parent's reference and their `occurred_at`, not by a business reference of their own, so the prefix buys nothing and costs a full-table scan per write. Rows are addressed by UUID everywhere.

**Cheap to write.** A responder records a handover on a phone at a loading dock. The write path is a single `INSERT` : no reference scan, no lifecycle resolution, no scope M2M, no transition bookkeeping.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, `default=uuid.uuid4`, `editable=False` | Unique identifier. Matches the `BaseModel` convention without inheriting it. |
| `evidence` | relation | FK -> [IncidentEvidence](incident-evidence.md), required, **`PROTECT`**, `related_name="custody_events"` | The item whose handling is being recorded. `PROTECT` so an evidence row that has ever been handled can never be deleted, whatever any other guard does. See [What PROTECT actually buys](#what-protect-actually-buys). |
| `action` | enum | required | The handling act. See [Enums](#enums). |
| `occurred_at` | datetime | required, indexed, **must be `>=` the previous row's `occurred_at`** | Real-world time of the act. **This is the ordering key** : the ledger reads in the order things happened, not in the order they were typed. |
| `recorded_at` | datetime | `auto_now_add=True` | When the row was logged. `occurred_at != recorded_at` is normal and is itself evidence of how promptly the ledger was kept. |
| `actor` | relation | FK -> User, required, **`PROTECT`**, `related_name="evidence_custody_events"` | The Cairn user performing or witnessing the act. `PROTECT` so a custody act attributed to a deleted row is never a custody act attributed to nobody. Deactivate or anonymise the user instead. |
| `counterparty` | string | optional, max 255, **required non-blank when `action` is `transferred`, `released`, `returned` or `destroyed`** | The named person receiving or relinquishing custody : forensics analyst, law enforcement officer, supervisory-authority agent, disposal witness. A handover to an organisation with no named individual is not a handover. |
| `counterparty_organisation` | string | optional, max 255, blank default | Their organisation. Free text rather than an `assets.Supplier` FK : a police force, a court bailiff or a data subject's counsel is not a supplier, and forcing them into the supplier register would pollute it. |
| `location` | string | optional, max 500, blank default | Where the act took place, or where the item went : safe number, evidence-bag identifier, address, data-centre rack, bucket and object key. |
| `hash_at_event` | string | max 128, blank default, **required non-blank when `action = integrity_verified`** | The digest measured **at this act**, not copied from the parent. This is the column that makes the ledger falsifiable : a row claiming a verification without a measurement is rejected. |
| `integrity_ok` | boolean | three-state, `null=True` | Whether `hash_at_event` matched the parent's `content_hash`. `null` when the act involved no verification, **and also when a verification was attempted but could not read the artefact**. See [Integrity verification](#integrity-verification-and-the-three-way-outcome). |
| `notes` | text | optional, blank default | Free-text detail : seal number, transport conditions, packaging, witness names, the reason a read could not be completed, or what an earlier row got wrong. |
| `source` | enum | required, default `manual` | Whether the row was appended by a lifecycle transition or recorded by hand. Reuses `TimelineEntrySource`, declared once in `incidents/constants.py`. See [Enums](#enums). |
| `version` | int | `PositiveIntegerField`, default `1` | Row version counter, mirroring the `SupplierSubprocessor` precedent for non-`BaseModel` audit rows. Never incremented in practice, since the row is never updated; kept so the shape matches the platform's other child rows and so a non-`1` value is itself a signal. |
| `created_at` / `updated_at` | datetime | `auto_now_add` / `auto_now` | Row timestamps. Declared explicitly because `BaseModel` is not inherited. |
| `history` | `HistoricalRecords()` | | Tamper **detection**. See [Append-only : what is actually guaranteed](#append-only--what-is-actually-guaranteed). |

`Meta.ordering = ["evidence", "occurred_at", "recorded_at"]`. The three-key ordering is deliberate : two acts can legitimately share an `occurred_at` (a transfer recorded by both parties in the same minute), and `recorded_at` then breaks the tie deterministically so the exported ledger is stable between two renders of the same evidence file.

### What PROTECT actually buys

`evidence` is `PROTECT`, so an evidence row with even one custody event cannot be deleted at the database level, independently of the lifecycle guard. That is not redundant with `deletable_states()`, it is the backstop for it:

- A `draft` evidence registration is `deletable=True` and has **zero** custody rows, because the first row is appended by the `draft -> collected` transition. Deleting a mistyped registration therefore still works.
- The instant an item is registered as collected, it has a custody row, and `PROTECT` makes deletion raise `ProtectedError` even if a future refactor loosened the lifecycle flags, even from the Django admin, and even from a shell.

Combined with the approve-gated archive and restore bookends described in [IncidentEvidence](incident-evidence.md#the-archive-and-restore-bookends), this closes the archive -> restore -> delete path completely : the restore edge is refused for any row that ever left `draft`, and even if it were reached, `PROTECT` refuses the delete.

## Enums

Reproduced verbatim from `incidents/constants.py` (DB value = Label).

### CustodyAction

| Value | Label |
|---|---|
| `collected` | Collected |
| `sealed` | Sealed |
| `transferred` | Transferred |
| `accessed` | Accessed |
| `copied` | Copied |
| `analysed` | Analysed |
| `integrity_verified` | Integrity verified |
| `released` | Released |
| `returned` | Returned |
| `destroyed` | Destroyed |

`returned` has no matching lifecycle step on purpose : an item lent to a forensics provider and handed back is a round trip inside the `analysed` or `retained` state, not a state change. Recording it as two rows (`transferred`, then `returned`) is exactly the pair a custody form asks for.

### TimelineEntrySource

Shared with [IncidentTimelineEntry](incident-timeline-entry.md) and declared once:

| Value | Label |
|---|---|
| `manual` | Manual |
| `lifecycle` | Lifecycle transition |
| `system` | System |
| `import` | Import |

## Which acts are appended automatically, and which are recorded by hand

**RG-INC-22.** The split is between acts that **are** state changes of the parent and acts that are not. The first are appended by the lifecycle; the second are the operator's responsibility, because Cairn cannot observe them.

### Auto-appended by the parent's `transition_to()` override

Every [IncidentEvidence](incident-evidence.md) lifecycle transition **that is a handling act** appends exactly one row with `source = "lifecycle"`, inside the transition's transaction, so a rolled-back transition leaves no row and a committed one leaves precisely one. Three edges are not handling acts and append nothing : the two `Retain` edges, and the `Archive` and `Restore` bookends, for which no `CustodyAction` value exists.

| Parent transition | Appended `action` | `occurred_at` | Other fields |
|---|---|---|---|
| `draft -> collected` (Register the item) | `collected` | the parent's `collected_at` | `actor` = the acquirer (`collected_by`); `location` from `storage_location` when set |
| `collected -> secured` (Seal) | `sealed` | the transition time | `hash_at_event` copied from the now-frozen `content_hash`; `integrity_ok` left null (sealing measures, it does not verify) |
| `secured -> analysed` (Record analysis) | `analysed` | the transition time | `notes` from the transition comment when one was given |
| `analysed -> retained` / `secured -> retained` (Retain) | `retained` is **not** a custody action : the appended row is `accessed` only if the retention involved handling. In practice this transition appends no row of its own and the ledger stays silent, which is correct : moving an item into its retention period is a bookkeeping act, not a handling act. | | |
| `retained -> released` (Release to a counterparty) | `released` | the transition time | `counterparty` and `counterparty_organisation` are **mandatory** on the transition form and are written here; `notes` from the mandatory comment |
| `retained -> destroyed` (Destroy) | `destroyed` | the transition time | `counterparty` (the disposal service, witness or performer) is mandatory; `location`; `notes` from the mandatory comment |

> The `retained` row in that table is the one exception to *one transition, one custody row*, and it is stated rather than hidden : `Retain` changes how the platform governs the item, not who is holding it. Where an organisation's own procedure treats moving an item into long-term storage as a handover, it records a `transferred` row by hand at the same time.

### Recorded by hand

Everything Cairn cannot observe, through the inline *Record custody act* form on the evidence detail page, the REST endpoint or the `create_evidence_custody_event` MCP tool, always with `source = "manual"`:

- **`transferred`** : the item goes to a forensics provider, to counsel, to law enforcement. `counterparty` mandatory.
- **`accessed`** : someone read or examined the artefact. See the note below.
- **`copied`** : a working copy was taken. The `notes` should carry the copy's own digest, since the copy is not itself an `IncidentEvidence` row unless it is registered as one.
- **`integrity_verified`** : a digest was measured and compared. `hash_at_event` mandatory.
- **`returned`** : custody came back. `counterparty` mandatory.

**On `accessed`, an honest limitation.** Cairn does **not** auto-append an `accessed` row when a user downloads an artefact through the permission-checked download action. The in-platform download is recorded by `accounts.AccessLog`, which is where access to the platform is audited. The custody ledger is deliberately left to human recording because the majority of reads happen **outside** Cairn : at the vault, on the analyst's workstation, in the provider's lab. A ledger that auto-logged only the reads Cairn happened to serve would look complete while covering the minority of them, and a reader would draw exactly the wrong conclusion from a short `accessed` list. The evidence detail page states this next to the ledger rather than leaving it to be discovered.

## Ordering and the monotonicity rule

`clean()` requires `occurred_at >= ` the `occurred_at` of the most recent existing row for the same evidence item. A custody ledger that jumps backwards in time is not a chain.

Two consequences worth knowing before implementing:

1. **Equality is allowed, strictly-greater is not required.** Two acts genuinely occur in the same minute, and forcing a strict ordering would push operators into falsifying a timestamp to get a row saved.
2. **The check is a validation, not a database constraint.** It runs in `clean()` and is called from the form, the serializer and the MCP handler. Like everything else here, it is prevention at application level; a row inserted by raw SQL out of order is detectable in the ledger's own reading, since the export renders `occurred_at` and `recorded_at` side by side.

A backdated row is legitimate and expected : a transfer that happened on Friday and was recorded on Monday is normal, and the gap between `occurred_at` and `recorded_at` is itself information the auditor is entitled to see. The UI therefore always shows both when they differ by more than a few minutes, and never hides the delay.

## Integrity verification and the three-way outcome

An `integrity_verified` row is the ledger's most consequential entry, and it must be able to express **three** outcomes, not two.

| Outcome | `hash_at_event` | `integrity_ok` | Effect on the parent | Notification |
|---|---|---|---|---|
| **Match** | the measured digest | `True` | `last_integrity_check_at` and `last_integrity_check_ok = True` | none |
| **Mismatch** | the measured digest | `False` | `last_integrity_check_at` and `last_integrity_check_ok = False` | `EVIDENCE_INTEGRITY_FAILED` to the collector, the incident manager and the holders of `incidents.evidence.approve` in scope |
| **Not verifiable** | blank | `null` | `last_integrity_check_at` stamped; `last_integrity_check_ok` **left unchanged** | none; an operational alert goes to the administrator |

**RG-INC-23.** A mismatch is a chain-of-custody break. It raises a danger badge on the evidence row, on the incident detail page and on the dashboard widget, and it fires `EVIDENCE_INTEGRITY_FAILED`. Nothing clears that badge : a later matching verification appends a further row and the ledger shows both, because the fact that the item once failed does not stop being true.

**Why "not verifiable" must be a distinct outcome.** `core/urls.py` (the `settings.DEBUG` media block) serves `MEDIA_URL` only under `DEBUG`, and `MEDIA_ROOT` is a volume an operator mounts. A restored database paired with a lost or unmounted media volume makes every inline artefact unreadable at once. If that were recorded as `integrity_ok = False`, a single infrastructure mistake would write a permanent chain-of-custody break into the ledger of **every** evidence item in the platform, on a day when nothing was tampered with, and the register would be unrecoverable : the rows are append-only by design, so the false breaks could never be removed. The distinction is therefore structural, not cosmetic:

- a **mismatch** is a claim about the artefact and is permanent;
- a **missing file** is a claim about the infrastructure, is recorded in `notes`, leaves `integrity_ok` null, and is surfaced as a warning to whoever can remount a volume.

The same applies to an item [registered by reference](incident-evidence.md#registration-by-reference-and-what-that-honestly-means) : Cairn never held it, so Cairn never concludes about it. Its verification is a wholly manual act, where an operator measures the digest at the storage location and records the result here by hand.

## Append-only : what is actually guaranteed

The module states this plainly rather than claiming an immutability the schema does not provide.

**Prevention is at application level.** `save()` raises `LifecycleProtectedError` when `self._state.adding` is false, and `delete()` raises `LifecycleProtectedError` unconditionally. Every documented write path in Cairn goes through `Model.save()`, so the web forms, the DRF serializers, the MCP tools and the Django admin are all covered.

**What bypasses it:**

- `QuerySet.update()` and `QuerySet.bulk_update()` issue SQL without calling `save()`.
- `QuerySet.delete()` and cascade deletion do not call `Model.delete()`. Here the `PROTECT` on `evidence` blocks the only cascade that could reach these rows, so this path is closed by the schema rather than by Python, which is worth noting as the one place in the module where it is.
- Raw SQL, a `manage.py shell` session and direct database access bypass Python entirely.

**Detection is via `HistoricalRecords`.** Every ORM-level write that does go through `save()` leaves a historical row, and `django-simple-history` records the acting user. A custody row whose historical trail shows more than one row has been altered, and that is visible on the row's history panel and in the merged timeline built by `core.history.build_timeline`. The honest claim to make to an auditor is therefore : *tampering with the custody ledger is prevented on every supported path and detectable on the rest*, not *the ledger is immutable*.

Real database-level immutability would need PostgreSQL rules or triggers, which `core.settings_test` (SQLite in memory, migrations disabled) cannot exercise. That divergence is not taken in this module; if it is ever taken, it must be taken deliberately and documented here.

## No hash chain, and why

**RG-INC-22.** There is deliberately **no** `chain_signature` column, no HMAC over the previous row, and no `verify_evidence_chain` management command. Three reasons, all of them specific to this codebase:

1. **Nothing in Cairn hash-chains anything.** The platform's tamper story is `HistoricalRecords` plus the immutable `core.LifecycleEvent`, applied uniformly across every module. Introducing a second, incompatible integrity mechanism in one entity would leave a reader unable to say which guarantee applies where.
2. **A key rotation would invalidate the register wholesale.** An HMAC keyed on `SECRET_KEY` breaks on the first routine rotation, and every row in the ledger would then read as tampered. A control that fails loudly on a correct operational act is worse than no control : it trains operators to ignore it.
3. **It would guarantee the wrong thing.** A chain proves that the rows were not reordered or edited *in the database*. It says nothing about whether the artefact in the vault is the one that was acquired. That question is answered by `hash_at_event` and a measurement, which is what this entity actually records.

The integrity claim the module makes is precise and defensible : each evidence item carries a digest recorded at acquisition and frozen by sealing, each verification is a dated, attributed, measured row, and every write to either is historised.

## Scope tenancy

**RG-INC-38.** `EvidenceCustodyEvent` is not a `ScopedModel` and never carries its own `scopes`. It is a **grandchild** of a scoped model and chains the lookup : `scope_parent_lookup = "evidence__incident__scopes"`.

That inheritance is real today on the two list surfaces and **absent on three others**. Phase 1 must extend all three; this is core work in the phase-1 PR, not an incidents-app detail, and it is logged under a **`### Security`** entry in `CHANGELOG.md`.

| Call site | Current behaviour | Required change | What is exposed without it |
|---|---|---|---|
| `accounts/mixins.py` `ScopeFilterMixin` and `accounts/api/mixins.py` `ScopeFilterAPIMixin` | Already honour `scope_parent_lookup` | none | - |
| `mcp/tools.py` `_filter_by_scopes` | Handles `context.Scope`, then a direct `scopes` M2M, then `return qs` **unfiltered** | Accept `model` / `parent_lookup` and thread a `scope_parent_lookup` argument through `_register_crud` / `_list_handler` / `_get_handler` | `list_evidence_custody_events` returns **every custody row on the instance** to any holder of `incidents.evidence.read` : counterparty names, counterparty organisations, locations, seal numbers and measured digests from every other tenant's incidents. This is arguably the most sensitive read in the module, because a custody ledger names people at other organisations. |
| `core/workflow_views.py` `WorkflowTransitionView` | Guards with `if allowed_scopes is not None and hasattr(obj, "scopes")`, which is false for this model and for its parent | Honour a model-level `scope_parent_lookup` attribute | This entity exposes no transition endpoint, but its **parent** does : without the fix, an out-of-scope user can perform the `destroy` transition on a sealed evidence item, which appends a `destroyed` row to this ledger and deletes the artefact. The ledger would then correctly record a destruction that should never have been reachable. |
| `core/history_views.py` `HistoryPartialView` | Same `hasattr(obj, "scopes")` guard | Same change | The full history of an out-of-scope custody row is readable |

The module ships a test asserting that a user scoped out of an incident receives an empty result from `list_evidence_custody_events` and a 404 from the history partial for one of its custody rows.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-22 | Every [IncidentEvidence](incident-evidence.md) lifecycle transition **that is a handling act** appends exactly one `EvidenceCustodyEvent` with `source="lifecycle"`; the two `Retain` edges and the archive and restore bookends are the stated exceptions and append nothing; acts that are not state changes (transfer, access, copy, integrity verification, return) are recorded manually. Custody rows are append-only, ordered by `occurred_at`, and each `occurred_at` must be `>=` the previous row's. `transferred` / `released` / `returned` / `destroyed` require a named `counterparty`. There is **no** cryptographic hash chain : nothing in Cairn hash-chains anything, and an HMAC keyed on `SECRET_KEY` would be invalidated wholesale by a routine key rotation. |
| RG-INC-23 | An integrity verification recording `integrity_ok=False` sets the parent's `last_integrity_check_ok`, raises a danger badge on the evidence row, the incident detail and the dashboard widget, and fires the `EVIDENCE_INTEGRITY_FAILED` notification to the evidence collector, the incident manager and the holders of `incidents.evidence.approve` in scope. A verification that could not read the artefact leaves `integrity_ok` null, leaves the parent's verdict unchanged, and raises an operational alert instead. |
| RG-INC-24 | Destroying evidence appends a final `destroyed` custody row with a named counterparty; the `IncidentEvidence` row itself is **never** deleted, and `PROTECT` on `evidence` means these ledger rows can never be deleted either. |
| RG-INC-37 | The ledger is read through `reportable()` / `linkable()` on its parent, never through a state literal. This entity has no states of its own. |
| RG-INC-38 | Scope tenancy : custody rows are never independently scoped and inherit through `scope_parent_lookup="evidence__incident__scopes"` on the web, API and MCP surfaces. See [Scope tenancy](#scope-tenancy) for the three call sites phase 1 must extend. |

Append-only is a **Python-level guarantee** : `QuerySet.update()`, `bulk_update()`, raw SQL and the shell bypass the `save()` guards. Prevention at application level, detection via `HistoricalRecords`.

## Endpoints

### REST

Base path `/api/v1/incidents/`, router registration `custody-events`. The viewset is **create, list and retrieve only** : `http_method_names` is restricted so no `PUT`, `PATCH` or `DELETE` route is generated at all, matching the append-only rule at the routing layer rather than only in the serializer.

- `GET /api/v1/incidents/custody-events/` : list, filters `evidence`, `incident`, `action`, `source`, `integrity_ok`, `occurred_after`, `occurred_before`
- `POST /api/v1/incidents/custody-events/` (+ `POST .../batch/` via `BatchCreateMixin`, max 100 items, non-atomic, per-item `{index, status, id}`)
- `GET /api/v1/incidents/custody-events/<uuid>/`
- `GET /api/v1/incidents/custody-events/<uuid>/history/` via `HistoryAPIMixin`

Viewset stack : `BatchCreateMixin`, `ScopeFilterAPIMixin` (with `scope_parent_lookup = "evidence__incident__scopes"`), `HistoryAPIMixin`, `CreatedByMixin`, `viewsets.ModelViewSet`. `LifecycleAPIMixin` is **not** mixed in : the entity runs no lifecycle, so no `transition/` route exists. Permissions use `ModulePermission` with `permission_module = "incidents"` and `permission_feature = "evidence"`, following the newest module precedent (`trust_center/api/views.py`) rather than importing another app's `ModulePermission` subclass.

`recorded_at`, `created_at`, `updated_at` and `version` are read-only; `actor` is stamped from the request user and is not client-settable. The serializer runs the same `clean()` monotonicity check and the same conditional `counterparty` requirement as the form, so an API caller cannot append a handover to nobody.

### MCP

- `create_evidence_custody_event` (bespoke, requires `incidents.evidence.update`) : append one handling act. Arguments `evidence_id`, `action`, `occurred_at`, `counterparty`, `counterparty_organisation`, `location`, `hash_at_event`, `integrity_ok`, `notes`. `action` and `source` carry explicit `enum` lists in `field_overrides`; `evidence_id` names `list_incident_evidence` as its lookup tool.
- `list_evidence_custody_events` (bespoke, requires `incidents.evidence.read`) : read a ledger, filters `evidence_id`, `incident_id`, `action`, `integrity_ok`. Scope-filtered through `evidence__incident__scopes`, which requires the `_filter_by_scopes` change described above.
- `verify_evidence_integrity` (bespoke, requires `incidents.evidence.update`) : documented in [IncidentEvidence](incident-evidence.md#mcp). It appends an `integrity_verified` row with the measured digest and the three-way verdict rather than letting an agent assert one by hand.

There is **no update and no delete tool**, deliberately : the entity is create-and-read only on every surface, and an agent must never be able to rewrite a chain of custody. `source` is forced to `manual` on every MCP-created row : an agent recording an act is a human recording it through an agent, not the lifecycle engine.

## Permissions

Gated by the parent evidence item's codenames : reading the ledger needs `incidents.evidence.read`, appending a row needs `incidents.evidence.update` (not `.create` : recording a handling act is maintaining the evidence item, not creating a new governed object). There is no `incidents.custody_event` feature and there will never be one : RG-INC-39 caps the module at exactly six features (`incident`, `security_event`, `evidence`, `notification`, `review`, `response_plan`), each with the five standard actions, so the six `SYSTEM_GROUPS` suffix lambdas grant the module unchanged and the group matrix screen renders every codename.

Because the entity is append-only, the `.delete` and `.approve` actions have no meaning here : no route consumes them. `.approve` is spent on the parent's release and destruction transitions, both of which append a row here as a side effect of an act that was already approved.

## UI

Rendered as the **Chain of custody** card in the left column of the [IncidentEvidence](incident-evidence.md#ui) detail page (strict 2-column layout, no nav-tabs, per the platform's detail-page doctrine):

- A table ordered by `occurred_at` ascending, so the card reads top to bottom as custody moved.
- Each row shows `occurred_at`, the action icon (Bootstrap Icons only), the actor avatar, the counterparty and organisation when set, the location, and `notes` in a Bootstrap collapse.
- `source = lifecycle` rows are visually distinguished from hand-recorded ones with a muted background and a system icon, so a reader can tell instantly which parts of the ledger the machine wrote and which a person attested.
- `recorded_at` is shown as a relative hint next to `occurred_at` whenever the two differ by more than a few minutes, since the delay is itself meaningful.
- An `integrity_verified` row renders its verdict as three visually distinct states and never two : a success tick for a match, a **danger** badge for a mismatch, and a **warning** "not verifiable" badge when `integrity_ok` is null on a verification attempt. The measured `hash_at_event` is shown truncated with a copy affordance.
- An inline **Record custody act** form sits at the foot of the card and posts over HTMX into the `#custody-events` partial, so a responder never leaves the evidence page. `counterparty` becomes required in the browser as soon as `transferred`, `released`, `returned` or `destroyed` is selected, mirroring the server-side rule rather than replacing it.
- There is **no edit and no delete affordance anywhere** on the card.
- A short standing note under the table states that reads performed outside Cairn must be recorded by hand, so nobody reads a short `accessed` list as *nobody looked at it*.

The card must render correctly in light and dark mode and at mobile widths; the inline form, with its conditional required field and its datetime picker, is checked at small widths on the same pass as the evidence page's sticky sidebar.

## Translations

Every user-facing string is wrapped with `_()` / `pgettext_lazy()` in Python or `{% trans %}` in templates and has a French translation in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `manage.py compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`, so a collision breaks CI outright.

**No `CustodyAction` label collides.** "Collected", "Sealed", "Transferred", "Accessed", "Copied", "Analysed", "Integrity verified", "Released", "Returned" and "Destroyed" are all new bare `msgid`s. So are "Counterparty", "Chain of custody", "Record custody act", "Hash at event" and "Not verifiable".

**Colliding labels** use `pgettext_lazy("incident", ...)` in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po` file:

| Label | Where | Existing bare entry |
|---|---|---|
| `Manual` | `TimelineEntrySource.MANUAL` | present, and already declared with `pgettext_lazy("incident", ...)` in `incidents/constants.py` for [IncidentTimelineEntry](incident-timeline-entry.md), which shares the enum. Declared **once**, used by both entities. |
| `System` | `TimelineEntrySource.SYSTEM` | same |
| `Import` | `TimelineEntrySource.IMPORT` | same |
| `Evidence` | the parent link label on this card | present, `msgstr "Preuves"` (plural, wrong for a singular item label) |

`Actor`, `Location`, `Notes`, `Source` and `Recorded at` already exist in the catalogue with a French translation that is correct in this context, so the same `msgid` is reused and **no new entry is added** : gettext merges the occurrences into one entry with several `#:` references, which is not a duplicate and does not fail `compilemessages`.

The `lifecycle_from_json` trap does **not** apply to this entity : it re-wraps stored step labels with bare `gettext_lazy` after the `post_migrate` round-trip through `LifecycleDefinition`, so a step label's `msgctxt` is lost. This entity declares no lifecycle and no steps, and its labels are plain field choices that never make that round trip. The trap does apply to its parent [IncidentEvidence](incident-evidence.md#translations), whose step labels "Retained in custody" and transition label "Register the item" were renamed in English for exactly that reason.

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- ISO/IEC 27001:2022 **A.5.28** (collection of evidence) : preservation of evidence and its chain of custody
- ISO/IEC 27037 (identification, collection, acquisition and preservation of digital evidence) : the source of the acquisition and chain-of-custody vocabulary, including the handover-with-named-counterparty requirement
- ISO/IEC 27035-2 : evidence handling as a prepared procedure, documented in [IncidentResponsePlan](incident-response-plan.md)`.evidence_procedure`
- [IncidentEvidence](incident-evidence.md) : the parent, its lifecycle, its sealing and immutability rules, its storage split and the archive / restore correction
- [Incident](incident.md) : the grandparent, its scope, and the closure gate that requires every evidence item to have left `collected`
- [IncidentTimelineEntry](incident-timeline-entry.md) : the incident chronology, which shares this entity's append-only framing and its `TimelineEntrySource` enum
- [README.md](README.md) : module business rules, permission codenames, notifications and environment variables
- [governance/history.md](../governance/history.md) : `HistoricalRecords` and the merged history timeline
- [governance/workflow.md](../governance/workflow.md) : the lifecycle framework the parent plugs into, and `LifecycleEvent`

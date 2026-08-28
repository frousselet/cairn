# IncidentEvidence

`incidents.models.evidence.IncidentEvidence`

The evidence register of an [Incident](incident.md) : the ISO/IEC 27001:2022 **A.5.28 (collection of evidence)** record. One row per evidence item, carrying its acquisition metadata, its cryptographic fingerprint, its handling caveat, its legal hold and its retention date. Its handling history is kept separately in the append-only [EvidenceCustodyEvent](evidence-custody-event.md) ledger, which answers the other half of A.5.28 : *who held this, when, where, and did the hash still match*.

File : `incidents/models/evidence.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`EVID`**, e.g. `EVID-1`), `tags`, `version`, `created_by`, `django-simple-history` audit trail, and the dedicated **`incident_evidence`** lifecycle. `workflow_perm_namespace` is overridden to **`incidents.evidence`**, because the default `app_label.model_name` would spell `incidents.incidentevidence`, which matches no feature in `PERMISSION_REGISTRY` and would silently grant nobody anything.

It is **not** a `ScopedModel` : it inherits the incident's scope through `scope_parent_lookup = "incident__scopes"`, so it can never drift out of alignment when the incident is re-scoped. That inheritance is **not enforced today on three call sites**, and phase 1 must extend them : see [Scope tenancy](#scope-tenancy). This is the entity where that gap is most damaging, because the endpoints it leaves open are the ones that destroy sealed evidence.

## Why a governed entity and not a child row

Evidence is the one child of an incident that genuinely needs its own lifecycle, for three reasons that no plain child row can express:

1. **Deletion must be state-dependent.** An evidence row can be deleted only while it is still a `draft` registration : a typo, a duplicate, an artefact that turned out not to exist. From `collected` onward `BaseModel.delete()` raises `LifecycleProtectedError`.
2. **Destruction is not deletion.** Disposing of an artefact at the end of its retention period is a permissioned, comment-bearing, confirmation-gated **transition** to a terminal `destroyed` step. The row survives, the hash survives, the custody ledger survives. A `DELETE` would erase the proof that the organisation ever held the item, which is precisely the fact A.5.28 asks it to be able to show. See [Destruction is a transition, never a DELETE](#destruction-is-a-transition-never-a-delete).
3. **Sealing is a state, not a flag.** `secured` means the acquisition metadata is frozen. Expressing that as a boolean would leave it settable by any update path; expressing it as a lifecycle step puts it behind a permission, a gate and an immutable `core.LifecycleEvent` row.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `EVID-N`, unique | Business reference. Cited in the incident file, in filings and in correspondence with a forensics provider. |
| `title` | string | required, max 255 | Evidence label, e.g. `Memory image - WEB-PRD-02` |
| `description` | text | optional, blank default | What the item is and why it matters to this incident |
| `evidence_type` | enum | required | Nature of the item, which drives the acceptable acquisition method. See [Enumerations](#enumerations). |
| `collected_at` | datetime | required, **immutable once `sealed_at` is set** | Acquisition timestamp. The moment the artefact left the live system. |
| `collection_method` | text | optional at creation, **required non-blank to leave `collected`**, immutable once sealed | How it was acquired : tooling and version, write-blocker, exact command line, witness present, whether the source was live or powered down. **This is the heart of admissibility** : an artefact with a perfect hash and no stated method is a file, not evidence. |
| `source_description` | string | optional, max 500, **required when `source_support_asset` is null** | Free-text origin when it is not a registered support asset : a personal device, a third-party service, a printed document, a physical location. |
| `storage_location` | string | optional, max 500 | Where the item physically or logically resides : safe number, evidence bag identifier, vault, bucket and object key, forensics provider case number. **This is how bulk artefacts are registered by reference.** |
| `file` | file | optional, `upload_to=_evidence_upload_path`, `FileExtensionValidator(ALLOWED_EVIDENCE_EXTENSIONS)`, capped by `INCIDENT_EVIDENCE_MAX_UPLOAD_BYTES`, immutable once sealed | Optional inline copy of a small artefact. See [Storage : two patterns, honestly](#storage--two-patterns-honestly). |
| `original_filename` | string | optional, max 255, blank default | Filename as acquired, preserved because the name is often itself evidence. Retained after destruction. |
| `file_size` | int | `PositiveBigIntegerField`, default `0` | Size in bytes of the acquired item, recorded **even when the artefact is stored externally**, so the register states the scale of what is held elsewhere. `PositiveBigIntegerField` and not `PositiveIntegerField` : a disk image passes the 2 GB signed-32-bit ceiling routinely. |
| `content_hash` | string | max 128, blank default, **required non-blank to leave `collected`**, immutable once `sealed_at` is set | Hex digest of the acquired item. Computed server-side on upload, entered by hand for externally stored evidence. An **integrity fingerprint, not a hash chain** : it proves this item has not changed since acquisition, and claims nothing about any other item. |
| `hash_algorithm` | enum | required, default `sha256` | Digest algorithm, recorded because a 2019 MD5 hash must stay verifiable in 2026. `sha1` and `md5` are labelled *(legacy)* in the UI and are accepted for historical items but warned against on new acquisitions. |
| `sealed_at` | datetime | optional, **write-once**, stamped by the `secure` transition | When the item was sealed. After this instant the acquisition metadata is frozen (RG-INC-20). |
| `last_integrity_check_at` | datetime | optional | When the last re-hash verification ran, whatever its outcome, including a verification that could not conclude |
| `last_integrity_check_ok` | boolean | three-state, `null=True` | Verdict of the last **conclusive** verification. `null` means never checked. `False` is a chain-of-custody break and is surfaced as a danger badge on the evidence row, on the incident detail page and on the dashboard widget. A verification that could not read the artefact leaves this field **unchanged** : see [Integrity verification](#integrity-verification). |
| `tlp` | enum | required, default `red` | `TrafficLightProtocol` handling caveat. Defaults **stricter than the incident's** (`amber`), because an artefact usually contains more than the incident summary does : credentials, personal data, customer content, a third party's internal names. |
| `legal_hold` | boolean | required, default `False`, indexed | Under legal hold. Blocks the `destroy` transition **outright, regardless of `retention_until`**, and is shown as a lock badge everywhere the item appears. |
| `retention_until` | date | optional, indexed | Date after which destruction is permitted. Feeds the calendar and the upcoming-deadlines widget so retention expiry is a scheduled act, not a discovery. |
| `admissibility_notes` | text | optional, blank default | Jurisdictional or contractual notes : which court or authority the item may be produced to, which chain-of-custody form was countersigned, which counsel was consulted. |
| `workflow_state` | string | indexed, default `draft` | Lifecycle step (`incident_evidence`). Never written directly : see [Lifecycle](#lifecycle). |
| `tags` | relation | M2M -> `context.Tag` | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | Who registered the row, which is not necessarily who acquired the artefact (`collected_by`) |
| `created_at` / `updated_at` | datetime | auto | Timestamps |
| `history` | `HistoricalRecords()` | | Audit trail. The `file` column stores only a path, so the historical table stays small. |

### Relations

| Name | Type | Target | Reverse accessor | Description |
|---|---|---|---|---|
| `incident` | FK, **`PROTECT`**, required | [Incident](incident.md) | `evidence_items` | The incident this artefact belongs to. `PROTECT` is belt and braces on top of the lifecycle delete guard : an incident holding evidence can never be deleted, whatever its own state. |
| `source_support_asset` | FK, `SET_NULL`, optional | `assets.SupportAsset` | `evidence_items` | The registered machine, service or device the artefact came off. Ties the artefact to the asset register rather than to a hostname typed twice. |
| `collected_by` | FK -> User, **`PROTECT`**, required | User | `collected_evidence` | The named acquirer. `PROTECT` so the identity survives : an acquisition attributed to a deleted row is an acquisition attributed to nobody. Deactivate or anonymise the user instead. |
| `destruction_authorised_by` | FK -> User, `SET_NULL`, optional | User | `authorised_evidence_destructions` | Who authorised the disposal. Stamped by the `destroy` transition, never editable. |

Reverse accessors on `IncidentEvidence` : `custody_events` ([EvidenceCustodyEvent](evidence-custody-event.md)), `timeline_entries` ([IncidentTimelineEntry](incident-timeline-entry.md) rows whose `related_evidence` points here).

### Meta

- `ordering = ["incident", "collected_at"]` : the evidence register reads in acquisition order within an incident, which is the order a forensics report is written in.
- `UniqueConstraint(fields=["incident", "content_hash"], condition=~Q(content_hash=""), name="unique_evidence_hash_per_incident")` : the same artefact is never registered twice against the same incident. The partial condition exempts rows that have not yet been hashed.
- `CheckConstraint evidence_sealed_requires_hash` : `sealed_at IS NULL OR content_hash != ''`. A sealed item with no fingerprint is not sealed.

> The unique constraint here does **not** suffer the NULL-distinctness trap that affects a constraint spanning nullable foreign keys : `content_hash` is a non-null `CharField` with a blank default, so two unhashed rows collide on `''` rather than being treated as distinct. That is why the condition excludes them explicitly instead of relying on `nulls_distinct`.

The same artefact registered against **two different incidents** is legal and intentional : one memory image can be evidence in two files, and each incident keeps its own custody ledger for its own copy.

## Enumerations

Reproduced verbatim from `incidents/constants.py` (DB value = Label).

### EvidenceType

| Value | Label |
|---|---|
| `disk_image` | Disk image |
| `memory_dump` | Memory dump |
| `log_extract` | Log extract |
| `network_capture` | Network capture |
| `screenshot` | Screenshot |
| `email` | Email |
| `document` | Document |
| `database_export` | Database export |
| `malware_sample` | Malware sample |
| `physical_device` | Physical device |
| `witness_statement` | Witness statement |
| `other` | Other |

`malware_sample` and `physical_device` are the two values that must never be stored inline : a live sample uploaded into the platform's media volume is a new incident, and a seized laptop has no file representation. Both are registered by reference with a `storage_location` (see [Storage](#storage--two-patterns-honestly)).

### HashAlgorithm

| Value | Label |
|---|---|
| `sha256` | SHA-256 |
| `sha512` | SHA-512 |
| `sha1` | SHA-1 (legacy) |
| `md5` | MD5 (legacy) |

`tlp` reuses `TrafficLightProtocol`, declared once in `incidents/constants.py` and documented in [Incident](incident.md#trafficlightprotocol).

## Storage : two patterns, honestly

This module uses **two different storage patterns**, and the split is by artefact size, not by habit. Stating it plainly here is cheaper than having an implementer discover it while adding a third.

| Pattern | Used by | Why |
|---|---|---|
| `FileField` on a media volume | `IncidentEvidence.file` | A multi-gigabyte disk image has no business in a database column. Follows `compliance.AssessmentResultAttachment` (`FileField` + `FileExtensionValidator` + `original_filename` + `file_size`), which is the house pattern for uploads. |
| `BinaryField` in the database | [IncidentNotification](incident-notification.md)`.proof_file_content` | A portal receipt is a few hundred kilobytes and must survive a restore alongside the row it proves. Follows `assets.Contract.file_content`, `assets.Certificate.file_content` and `trust_center.TrustCenterDocument.file_content`, all of which exclude the column from `HistoricalRecords`. |

### The upload path and the cap

- `upload_to=_evidence_upload_path` yields `incidents/<incident_id>/evidence/<uuid>/<filename>`. The per-row UUID directory means two artefacts with the same filename never collide and a path never leaks another incident's identifiers.
- `INCIDENT_EVIDENCE_MAX_UPLOAD_BYTES` (`core/settings.py`, read from the environment, default **52428800**, i.e. 50 MB) caps the inline copy. It is enforced in the form, in the serializer and in the MCP layer, not only in the reverse proxy, so every surface refuses the same thing. It is documented in the module README's environment-variables table.

### Registration by reference, and what that honestly means

Above the cap, the artefact is **registered by reference** : `file` stays null, `storage_location` names where it actually is, `file_size` records how big it is, and `content_hash` records its fingerprint. The consequence must be stated rather than glossed:

> **The platform then holds the hash of something it does not hold.** Cairn can prove that the digest recorded at acquisition has not been altered inside Cairn. It cannot, by itself, prove anything about the artefact sitting in the vault. Verifying that item is a manual act : someone re-computes the digest at the storage location and records the result as an [EvidenceCustodyEvent](evidence-custody-event.md) with `action = integrity_verified` and a `hash_at_event`.

This is standard forensic practice - a case register holds references and hashes, not the exhibits - but a reader of a green integrity column is entitled to know which of the two claims it is making. The UI therefore renders "Held in Cairn" and "Registered by reference" as two visually distinct states on every evidence row, and never shows a verification badge that was not produced by an actual measurement.

### The production media-volume requirement

`core/urls.py` (the `settings.DEBUG` media block)` serves `MEDIA_URL` **only under `DEBUG`** :

```python
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

Three deployment consequences follow, and they are operational requirements of this module, not caveats:

1. **A persistent media volume is required.** `MEDIA_ROOT` defaults to `BASE_DIR / "media"`, which inside a container is ephemeral. A Docker or Kubernetes install must mount a persistent volume there, and it must be backed up **in the same operation** as the database. A restored database paired with a lost volume yields evidence rows whose artefact no longer exists : see [Integrity verification](#integrity-verification) for why that must never be reported as a chain-of-custody break.
2. **The volume must not be served directly.** Because Django does not serve it in production, nothing else should either : the reverse proxy must **not** be configured with a `location /media/` alias for this path. Evidence downloads go through a permission-checked and scope-checked detail action that resolves the row, checks `incidents.evidence.read` and the caller's scopes, and streams the file. A raw media URL would be an unauthenticated, unscoped, guessable-by-UUID download of forensic material.
3. **Storage-level protection is the operator's job.** Cairn guarantees the row, the hash and the ledger. It does not guarantee the bytes on a volume an administrator can `rm`. Encryption at rest, restrictive filesystem permissions and volume-level snapshots are named in the deployment notes as the operator's side of A.5.28.

## Sealing and immutability

**RG-INC-21.** The `collected -> secured` transition (*Seal*) is refused unless `content_hash` **and** `collection_method` are both non-blank. There is no path to `secured` without both, on any surface.

**RG-INC-20.** Once `sealed_at` is set, the acquisition metadata is frozen : `file`, `content_hash`, `hash_algorithm`, `collected_at`, `collected_by` and `collection_method`. `save()` re-reads the stored row and raises `ValidationError` naming the field on any attempted change, so the guard applies to the web form, the DRF serializer, the MCP update tool and the Django admin alike.

What stays editable after sealing, deliberately, because these are judgements about the item rather than facts of its acquisition : `title`, `description`, `storage_location` (an artefact legitimately moves), `tlp`, `legal_hold`, `retention_until` and `admissibility_notes`. Every one of those changes is historised, and a physical move should additionally be recorded as a `transferred` custody event.

Like everything else in the module, this is **prevention at application level and detection via `HistoricalRecords`** : `QuerySet.update()`, `bulk_update()`, raw SQL and a `manage.py shell` session bypass `save()` entirely. The honest claim is that the acquisition metadata cannot be altered on any supported path and that an alteration on the remaining paths leaves a historical row that exposes it. It is not immutable, and the docs do not say it is.

## Integrity verification

`verify_evidence_integrity(evidence, actor)` re-reads the stored artefact, recomputes the digest with the row's `hash_algorithm` and compares it against `content_hash`. It is reachable from the evidence detail page, from the REST detail action and from the `verify_evidence_integrity` MCP tool, and it always appends an [EvidenceCustodyEvent](evidence-custody-event.md) with `action = integrity_verified`.

**It has three outcomes, and the third must never be collapsed into the second.**

| Outcome | Condition | `integrity_ok` on the custody row | `last_integrity_check_ok` | Notification |
|---|---|---|---|---|
| **Match** | Artefact read, digest equals `content_hash` | `True` | set to `True` | none |
| **Mismatch** | Artefact read, digest differs | `False` | set to `False` | `EVIDENCE_INTEGRITY_FAILED` to the collector, the incident manager and the holders of `incidents.evidence.approve` in scope (RG-INC-23) |
| **Not verifiable** | `file` is null (registered by reference), or the file is referenced but **missing from the media volume**, or unreadable | `null` | **left unchanged** | none; an operational alert is raised to the administrator instead |

`last_integrity_check_at` is stamped in all three cases, because an attempt that could not conclude is still a dated attempt and the register should say when it was last tried.

**Why the third row matters.** A restored database paired with a lost or unmounted media volume makes every inline artefact unreadable at once. Reporting that as `integrity_ok = False` would write a chain-of-custody break into the permanent ledger of every evidence item in the platform, on a day when nothing was tampered with. The break is a claim about the artefact; a missing volume is a claim about the infrastructure. The custody row records the failure to read in `notes` and leaves `integrity_ok` null, the evidence row shows a **warning**-tone "not verifiable" badge rather than the **danger**-tone "integrity failed" badge, and the alert goes to whoever can remount a volume rather than to whoever would open a forensic investigation.

Re-verification is not scheduled in phase 1. Phase 3 adds a periodic sweep; until then it is an operator act, and the evidence list exposes a `last_integrity_check_at` column and a filter so stale items are findable.

## Handling caveat, legal hold and retention

- **`tlp`** is the handling caveat travelling with the item. It is rendered on the evidence row, on the detail page, in the export and in any generated filing that quotes the item, so a reader can never see the artefact reference without seeing how it may be shared. It defaults to `red` : the strictest sensible default, loosened deliberately rather than tightened after a leak.
- **`legal_hold`** is an absolute block on destruction. It defeats `retention_until` in every direction : an item under hold is never destroyable, whatever its retention date, and the `destroy` transition refuses with a message naming the hold. Setting or clearing a hold needs `incidents.evidence.update`, is historised, and should be accompanied by a custody entry naming the counsel or authority that imposed it.
- **`retention_until`** is the date after which destruction becomes permissible. It is a **permission to destroy, never an instruction** : nothing in Cairn destroys anything automatically. The date feeds the calendar so that expiry surfaces as a scheduled review, and the evidence list offers a `retention_before` filter so a periodic disposal review is a single query.

## Lifecycle

`LIFECYCLE_NAME = "incident_evidence"`, `layout="graph"`, registered from `IncidentsConfig.ready()` in `incidents/lifecycles.py`.

> `lifecycle_name_for()` resolves `LIFECYCLE_NAME` only `if name and name in LIFECYCLE_REGISTRY`. An `incidents/apps.py` whose `ready()` forgets to import `incidents.lifecycles` therefore **fails silently** : this model would quietly run the default 4-state lifecycle, with no `secured`, no `destroyed` and no gates, in tests as well as in production. The module ships a test asserting `IncidentEvidence.get_lifecycle().name == "incident_evidence"`.

### Authoring : hand-written `Step` / `Transition` lists

Together with [Incident](incident.md), this lifecycle is one of the two in the module that deviate from the `CLAUDE.md` rule of generating a lifecycle from its transition constants. `lifecycle_from_state_flags()` builds every `Step(...)` with no `triggers=` argument and its tuple contract has no slot for them, so a generated lifecycle **physically cannot** declare the confirmation gate that evidence destruction rests on. Both lifecycles are therefore declared as explicit `Step` and `Transition` lists in `incidents/lifecycles.py`, with the step codes still exported as constants from `incidents/constants.py` so no state literal appears outside that module (RG-INC-37).

### Steps

Eight steps : one draft entry, four custody stages, two domain terminal exits and the generic archived exit.

| Code | Label | StepKind | In reports | Linkable | Deletable | Tone | Meaning |
|---|---|---|---|---|---|---|---|
| `draft` | Draft registration | `DRAFT` | no | no | **yes** | `neutral` | The registration form before the item is confirmed acquired. The **only** step in which an evidence row can be deleted. |
| `collected` | Collected | `INTERMEDIATE` | **yes** | no | no | `secondary` | The artefact exists and is attributed. Not yet sealed, so not yet linkable and not yet quotable. An incident cannot close while any item sits here (RG-INC-14). |
| `secured` | Secured | `INTERMEDIATE` | **yes** | **yes** | no | `info` | Sealed : hashed, method recorded, acquisition metadata frozen |
| `analysed` | Analysed | `INTERMEDIATE` | **yes** | **yes** | no | `primary` | Examined, with findings recorded in the incident chronology |
| `retained` | Retained in custody | `INTERMEDIATE` | **yes** | **yes** | no | `success` | Held for its retention period. The steady state of a closed incident's evidence. |
| `released` | Released | `ARCHIVED` (terminal) | **yes** | no | no | `dark` | Handed to a named counterparty : law enforcement, a supervisory authority, counsel, the data owner. Cairn no longer holds it, and says so. |
| `destroyed` | Destroyed | `ARCHIVED` (terminal) | no | no | no | `muted` | Disposed of after its retention period. Carries a `confirm` trigger. The row survives; the artefact does not. |
| `archived` | Archived | `ARCHIVED` | no | no | no | `muted` | The generic exit, declared **explicitly** (see below) |

`released` keeps `counts_in_reports=True` : an item handed to an authority is exactly what the register must still show. `destroyed` does not, because the point of the disposal record is that the organisation no longer holds it; its existence is proved by the row and its custody ledger, not by a report count.

`collected` is deliberately **not** linkable. An unsealed artefact must not be quotable from a filing, from the chronology's `is_evidence` set or from a report : sealing is what makes it citable.

### Transitions

`permission_action` is the suffix appended to `workflow_perm_namespace` (`incidents.evidence`), so `update` means `incidents.evidence.update` and `approve` means `incidents.evidence.approve`.

| Verb | Transition | `permission_action` | `requires_comment` | Side effects |
|---|---|---|---|---|
| Register the item | `draft -> collected` | `update` | no | Appends a `collected` custody event with the acquirer as actor and `collected_at` as `occurred_at` |
| Seal | `collected -> secured` | `update` | no | **Gate GE-02.** Stamps `sealed_at`; freezes the acquisition metadata; appends a `sealed` custody event |
| Record analysis | `secured -> analysed` | `update` | no | Appends an `analysed` custody event |
| Retain | `analysed -> retained` | `update` | no | Appends **no** custody row : see the stated exception in [EvidenceCustodyEvent](evidence-custody-event.md). There is no `retained` value in `CustodyAction`. |
| Retain | `secured -> retained` | `update` | no | For items never analysed in house. Appends **no** custody row, for the same reason. |
| Release to a counterparty | `retained -> released` | **`approve`** | **yes** | **Gate GE-03.** Requires a named counterparty, carried on the appended `released` custody event |
| Destroy | `retained -> destroyed` | **`approve`** | **yes** | `confirm` trigger on entry. **Gate GE-04.** Stamps `destruction_authorised_by`, deletes the stored file, appends a final `destroyed` custody event. The row is never deleted. |
| Archive | `* -> archived` | **`approve`** | **yes** | Hand-declared, not auto-wired |
| Restore | `archived -> draft` | **`approve`** | no | Hand-declared, and refused for any row that has ever left `draft` (gate GE-05) |

There is no `lifecycle_transition_url_name` override : every transition posts to the generic `workflow:transition` endpoint, and every gate lives on the model.

Every transition that is a **handling act** appends exactly one [EvidenceCustodyEvent](evidence-custody-event.md) with `source = "lifecycle"` (RG-INC-22), inside the transition's transaction, so a rolled-back transition leaves no ledger row and a committed one leaves precisely one. The two `Retain` edges are the single stated exception : moving an item into its retention period changes how the platform governs it, not who is holding it, so no row is appended and `CustodyAction` has no `retained` value. The exception is documented in [EvidenceCustodyEvent](evidence-custody-event.md) rather than left for an implementer to discover.

### The archive and restore bookends

**This is the single most audit-damaging hole the design review found, and it lands hardest on this entity.**

`lifecycle_from_state_flags()` appends `Transition(target="archived", source=ANY, label=_("Archive"))` and `Transition(target="draft", source="archived", label=_("Restore"))` **with no `permission_action` and no `requires_comment`** (`core/lifecycle.py` `lifecycle_from_state_flags()`), and `user_can_perform()` (`core/lifecycle.py` `user_can_perform()`) allows any transition whose `permission_action` is empty. Because `draft` is `deletable=True`, that pair yields an **archive -> restore -> delete** path open to anyone who can reach the transition endpoint. On this entity that path **destroys a sealed A.5.28 evidence row** : the artefact, its hash, its custody ledger through the `PROTECT` chain, and the organisation's ability to show it ever held the item. No amount of care in the `collected -> secured` gate matters if the row can be walked back to a deletable step by an unpermissioned edge.

The lifecycle therefore:

1. declares `archived` **explicitly** among its steps, so `has_archived` is `True` and nothing is auto-wired;
2. hand-declares `ANY -> archived` with `permission_action="approve"` and `requires_comment=True`;
3. hand-declares `archived -> draft` with `permission_action="approve"`;
4. and refuses the restore edge in `transition_to()` for any row that has ever left `draft`, which the immutable `core.LifecycleEvent` ledger answers exactly (gate GE-05).

Because it is hand-authored rather than generated, the `draft -> collected` entry transition is likewise not auto-wired and is declared explicitly.

The same correction is applied to every lifecycle in the module (`incident`, `security_event`, `incident_notification`, `post_incident_review`, and `personal_data_breach` in phase 2). [IncidentResponsePlan](incident-response-plan.md) needs none of it : it runs the core `default` lifecycle, whose archive edge already carries `permission_action="approve"` and which has no restore transition at all.

The module ships a regression test that walks an evidence row from `secured` to `archived`, attempts `archived -> draft` as a holder of `incidents.evidence.update`, and asserts both that the transition is refused and that `IncidentEvidence.objects.filter(pk=...).exists()` is still true.

### Transition gates

Every audit gate is enforced in a `transition_to()` override on the model, never through `Transition.form_class`, `allowed_roles` or `allowed_users` (RG-INC-08) : `lifecycle_to_json()` drops those three by design, `lifecycle_from_json()` rebuilds transitions without them, and `get_lifecycle()` prefers the `post_migrate`-seeded `LifecycleDefinition` row, so a gate declared that way is green in an in-memory unit test and absent on every migrated database. All three write surfaces funnel through `BaseModel.transition_to()`, so the model override is the one place that binds web, API and MCP at once.

Each gate raises `ValidationError` with a translated, actionable message naming the missing precondition, before `perform_transition()` runs, and the whole transition body runs inside `transaction.atomic()`. Gate identifiers are local to this entity.

| Gate | Transition | Refused unless |
|---|---|---|
| **GE-01 Registration** | `draft -> collected` | `evidence_type`, `collected_at` and `collected_by` are set, **and** either `source_support_asset` or a non-blank `source_description` identifies the origin. |
| **GE-02 Sealing** (RG-INC-21) | `collected -> secured` | `content_hash` is non-blank **and** `collection_method` is non-blank. Stamps `sealed_at` and freezes the acquisition metadata from that instant. |
| **GE-03 Release** | `retained -> released` | Holder of `incidents.evidence.approve`, a mandatory comment, **and** a named counterparty supplied with the transition, which is written onto the appended `released` custody event. Releasing an artefact to nobody in particular is not a release. |
| **GE-04 Destruction** (RG-INC-24) | `retained -> destroyed` | Holder of `incidents.evidence.approve`, a mandatory comment, a confirmation, `legal_hold` is `False`, **and** `retention_until` is set and strictly in the past. All four, evaluated server-side. |
| **GE-05 Restore** | `archived -> draft` | No `core.LifecycleEvent` on the row records a step other than `draft` or `archived`. A row that ever reached `collected` can be archived but never restored into a deletable step. |
| **GE-06 Write-once stamps** (RG-INC-12) | all | `sealed_at` and `destruction_authorised_by` are stamped by the override only. They are excluded from every `ModelForm`, are `read_only` in every serializer, and are absent from every MCP `writable_fields` list. |

The `confirm` trigger on `destroyed` is a **UX affordance, not a security control** : GE-04 is enforced server-side and applies identically to a DRF or MCP caller that never sees a modal. Two implementation notes carry over from [Incident](incident.md#the-confirmation-trigger-on-closed) : no lifecycle in Cairn uses `Trigger` today, so the `opts.confirm` branch of `templates/includes/lifecycle_stepper.html` has never run and this module is its first user; and triggers do survive the `LifecycleDefinition` round-trip, so only the *generator* cannot express them.

### Destruction is a transition, never a DELETE

**RG-INC-24.** Disposing of an artefact at the end of its retention period is a governed act with a permanent record. Concretely, the `retained -> destroyed` transition, inside one atomic block:

1. checks GE-04 : approve permission, mandatory comment, confirmation, no legal hold, retention date past;
2. stamps `destruction_authorised_by` from the acting user;
3. deletes the stored artefact from the media volume and clears `file`, **retaining** `original_filename`, `file_size`, `content_hash` and `hash_algorithm` so the record of *what* was destroyed survives its destruction;
4. appends a final `destroyed` [EvidenceCustodyEvent](evidence-custody-event.md) with the named counterparty (the disposal service, the witness, or the person who performed it), the location and the comment;
5. leaves the `IncidentEvidence` row in place, permanently, in the terminal `destroyed` step.

Step 3 is the **only** modification of `file` permitted after sealing, and it is performed by the transition, never by an edit. Everything else about the row is already frozen by RG-INC-20.

Registered-by-reference items follow the same transition with no step 3 : the artefact was never in Cairn, the custody event records who destroyed it and where, and the register states that the disposal is attested rather than performed by the platform.

## Scope tenancy

**RG-INC-38.** `IncidentEvidence` is not a `ScopedModel` and never carries its own `scopes`. It inherits the parent incident's scope through `scope_parent_lookup = "incident__scopes"`; its own child, [EvidenceCustodyEvent](evidence-custody-event.md), chains that to `evidence__incident__scopes`.

That inheritance is real today on exactly two surfaces and **absent on three others**. Phase 1 must extend all three. This is core work in the phase-1 PR, not an incidents-app detail, and it is logged under a **`### Security`** entry in `CHANGELOG.md`.

| Call site | Current behaviour | Required change | What is exposed without it |
|---|---|---|---|
| `accounts/mixins.py` `ScopeFilterMixin` | Already honours `scope_parent_lookup` | none | - |
| `accounts/api/mixins.py` `ScopeFilterAPIMixin` | Already honours `scope_parent_lookup` | none | - |
| `mcp/tools.py` `_filter_by_scopes` | Handles `context.Scope`, then a direct `scopes` M2M, then `return qs` **unfiltered** | Accept `model` / `parent_lookup` and thread a `scope_parent_lookup` argument through `_register_crud` / `_list_handler` / `_get_handler` / `_transition_handler` / `_allowed_transitions_handler` | `list_incident_evidence` and `list_evidence_custody_events` return **every evidence row and every custody row on the instance** to any holder of `incidents.evidence.read`, including hashes, storage locations, counterparties and TLP:RED handling caveats from other tenants' incidents |
| `core/workflow_views.py` `WorkflowTransitionView` | Guards with `if allowed_scopes is not None and hasattr(obj, "scopes")`, which is false for this model | Honour a model-level `scope_parent_lookup` attribute | The `destroy` and `release` transitions are performable **cross-scope**. A user scoped to one subsidiary can destroy another subsidiary's sealed evidence, with a valid `approve` permission and a perfectly clean audit trail showing they were entitled to. |
| `core/history_views.py` `HistoryPartialView` | Same `hasattr(obj, "scopes")` guard | Same change | The full field-level history of an out-of-scope evidence row is readable, including every value the acquisition metadata ever held |

The two web endpoints are shared by every module, so the guard is fixed once and benefits every non-`ScopedModel` child in the platform. The module ships tests asserting that a user scoped out of an incident receives a 404 from `workflow:transition` and from the history partial for its evidence, and an empty list from `list_incident_evidence`.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-12 | Transition-stamped timestamps (`sealed_at` here) are written by the `transition_to()` override only. They are excluded from every `ModelForm`, are `read_only` in every serializer, and are absent from every MCP `writable_fields` list. |
| RG-INC-14 | An incident cannot close while any of its evidence items is still in the `collected` step. Sealing is what makes an artefact citable, and an incident file quoting unsealed artefacts is not closeable. |
| RG-INC-20 | Evidence acquisition metadata (`file`, `content_hash`, `hash_algorithm`, `collected_at`, `collected_by`, `collection_method`) is immutable once `sealed_at` is set : `save()` compares against the stored row and raises `ValidationError` on any attempted change. Prevention at application level, detection via `HistoricalRecords`. |
| RG-INC-21 | Sealing evidence requires a non-blank `content_hash` **and** a non-blank `collection_method`. There is no path to `secured` without both. |
| RG-INC-22 | Every `IncidentEvidence` lifecycle transition that is a handling act appends exactly one [EvidenceCustodyEvent](evidence-custody-event.md) with `source="lifecycle"`; the two `Retain` edges are the stated exception and append nothing. Acts that are not state changes (transfer, return, access, copy, integrity verification) are recorded manually. Custody rows are append-only, ordered by `occurred_at`, and each `occurred_at` must be `>=` the previous row's. `transferred` / `released` / `returned` / `destroyed` require a named counterparty. There is **no** cryptographic hash chain. |
| RG-INC-23 | An integrity verification recording `integrity_ok=False` sets the parent's `last_integrity_check_ok`, raises a danger badge on the evidence row, the incident detail and the dashboard widget, and fires the `EVIDENCE_INTEGRITY_FAILED` notification to the collector, the incident manager and the holders of `incidents.evidence.approve` in scope. A verification that could not read the artefact is **not** a verification failure : `integrity_ok` stays null, `last_integrity_check_ok` is untouched, `EVIDENCE_INTEGRITY_FAILED` does **not** fire, and an operational alert goes to whoever can remount a volume. |
| RG-INC-24 | Destroying evidence requires `incidents.evidence.approve`, a mandatory comment, a confirmation, `legal_hold=False` and a `retention_until` in the past. Destruction stamps `destruction_authorised_by` and appends a final custody event; the `IncidentEvidence` row itself is **never** deleted. |
| RG-INC-37 | Every report, KPI, calendar feed, kanban bucket and link picker filters through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. No evidence state literal appears anywhere outside `incidents/constants.py`. |
| RG-INC-38 | Scope tenancy : evidence is never independently scoped and inherits the incident's scope through `scope_parent_lookup="incident__scopes"` on the web, API and MCP surfaces. See [Scope tenancy](#scope-tenancy) for the three call sites phase 1 must extend. |

## Endpoints

### REST

Base path `/api/v1/incidents/`, router registration `evidence`.

- `GET /api/v1/incidents/evidence/` : list, filtered by `IncidentEvidenceFilter` (`incident_id`, `evidence_type`, `status`, `legal_hold`, `retention_before`, `last_integrity_check_ok`)
- `POST /api/v1/incidents/evidence/` and `POST /api/v1/incidents/evidence/batch/` (max 100 items, non-atomic, per-item `{index, status, id, reference}`)
- `GET/PUT/PATCH/DELETE /api/v1/incidents/evidence/<uuid>/` : `DELETE` succeeds only while the row is in `draft`; from `collected` onward `BaseModel.delete()` raises and the endpoint returns 409
- `GET/POST /api/v1/incidents/evidence/<uuid>/transition/` : supplied by `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`, so every gate above applies identically to an API caller
- `GET /api/v1/incidents/evidence/<uuid>/download/` : the **only** way to retrieve the artefact. Resolves the row, checks `incidents.evidence.read` and the caller's scopes through `incident__scopes`, then streams the file with `Content-Disposition: attachment` and the original filename. Returns 404 for a registered-by-reference row and for a destroyed one.
- `POST /api/v1/incidents/evidence/<uuid>/verify-integrity/` : runs the verification described above and returns the outcome, including the distinct `not_verifiable` result. Requires `incidents.evidence.update`.
- `GET /api/v1/incidents/evidence/<uuid>/history/` : `core.history.build_timeline`, merging `LifecycleEvent` and `HistoricalRecords`

Viewset stack in the house order : `BatchCreateMixin`, `ScopeFilterAPIMixin` (with `scope_parent_lookup = "incident__scopes"`), `LifecycleAPIMixin`, `HistoryAPIMixin`, `CreatedByMixin`, `viewsets.ModelViewSet`. Permissions follow the newest module precedent (`trust_center/api/views.py` `_ManagedViewSet`) : `ModulePermission` directly, plus an `_IncidentViewSet` base fixing `permission_module = "incidents"` and `custom_action_map = {"transition": "update"}`. `IncidentEvidenceViewSet` **extends** that base map with its own two actions, `{"verify-integrity": "update", "download": "read"}`, rather than redefining it : those actions exist on no other viewset in the module, and the shared base must stay identical across all ten. Another app's `ModulePermission` subclass (`ContextPermission`) is **not** imported.

Two serializers : `IncidentEvidenceSerializer` (full) and `IncidentEvidenceListSerializer` for the index, switched on `self.action == "list"`. `read_only_fields` cover `id`, `reference`, `created_by`, `created_at`, `updated_at`, `version`, `sealed_at`, `destruction_authorised_by`, `last_integrity_check_at` and `last_integrity_check_ok`. `status` is exposed as `CharField(source="workflow_state", read_only=True)`. **The `file` payload never appears in any serializer**, list or detail : the list exposes `has_file`, `file_size` and `original_filename`, and the bytes are reachable only through the `download` action.

### MCP

- `_register_crud(server, "incident_evidence", IncidentEvidence, "incidents.evidence", ...)` generates `list_incident_evidence`, `get_incident_evidence`, `create_incident_evidence`, `batch_create_incident_evidence`, `update_incident_evidence`, `delete_incident_evidence`, `transition_incident_evidence`, `incident_evidence_allowed_transitions`, `get_incident_evidence_history`. Filters : `incident_id`, `evidence_type`, `status`, `legal_hold`, `last_integrity_check_ok`. Search fields : `reference`, `title`, `description`, `storage_location`.
- **The `file` field is never writable through MCP**, and its bytes are never readable through MCP. An agent registers evidence by reference or updates metadata; uploading a forensic artefact is a human act performed on a surface that can show the operator what they are uploading.
- `verify_evidence_integrity` (bespoke, requires `incidents.evidence.update`) records an `integrity_verified` custody act with its measured hash and verdict, and returns the three-way outcome explicitly so an agent can distinguish a tamper from a missing volume.
- `create_evidence_custody_event` and `list_evidence_custody_events` are documented in [EvidenceCustodyEvent](evidence-custody-event.md).
- `_register_crud` is called with the new `scope_parent_lookup="incident__scopes"` argument. Without the `_filter_by_scopes` change described in [Scope tenancy](#scope-tenancy), that argument does not exist and the tool leaks every row on the instance.
- Every enum field carries an explicit `enum` list in `field_overrides`; `sealed_at`, `destruction_authorised_by`, `last_integrity_check_at` and `last_integrity_check_ok` never appear in `writable_fields`; the `incident_id` argument description names `list_incidents` as its lookup tool.

`mcp/tools.py` `HELP_TEXT` gains `IncidentEvidence=EVID` in the reference-prefix block, and the entity gets its own section in `TOPIC_INCIDENTS` listing writable fields, enum values, filters and the reference prefix.

## Permissions

| Codename | Description |
|---|---|
| `incidents.evidence.read` | List and read evidence rows, read the custody ledger, download an artefact |
| `incidents.evidence.create` | Register an evidence item |
| `incidents.evidence.update` | Edit business fields, seal, record analysis, retain, record a custody act, run an integrity verification |
| `incidents.evidence.approve` | Release, destroy, archive, restore |
| `incidents.evidence.delete` | Delete a draft registration |

`incidents.evidence.*` also gates [EvidenceCustodyEvent](evidence-custody-event.md), which has no feature of its own. RG-INC-39 caps the module at exactly six features (`incident`, `security_event`, `evidence`, `notification`, `review`, `response_plan`), each with the five standard actions, so the six `SYSTEM_GROUPS` suffix lambdas grant them unchanged and the group matrix screen, which renders a hardcoded action list, displays every one of them. The rows are created and attached to the six system groups by `accounts/migrations/0056_add_incidents_permissions.py`.

`workflow_perm_namespace = "incidents.evidence"` is **mandatory** on this model : without it the namespace resolves to `incidents.incidentevidence`, which matches no registry feature, and every lifecycle permission check on the entity silently evaluates against a codename nobody holds.

## UI

**List** (`/incidents/evidence/`) : the house stack, with `ScopeFilterMixin` configured for `scope_parent_lookup`. Columns : reference, title, type, incident, sealed state, hash (truncated, with a copy affordance), TLP chip, legal-hold lock, retention date, last integrity check. The integrity column renders three visually distinct states and never two : a success tick, a **danger** badge for a mismatch, and a **warning** "not verifiable" badge for an artefact that could not be read.

**Detail** (`/incidents/evidence/<uuid>/`) : a strict 2-column card layout, no nav-tabs.

- Left column, stacked cards:
  - **Acquisition** : method, source (the linked support asset or the free-text description), storage location, and the artefact itself, shown either as a permission-checked download button or as a "Registered by reference" statement naming the storage location. Every field in this card renders read-only with a lock icon once `sealed_at` is set.
  - **Integrity** : hash and algorithm (with a *(legacy)* warning on `sha1` and `md5`), the last check with its date and its three-way verdict, and a **Verify now** button. The card states in words whether the platform holds the artefact or only its fingerprint, so nobody reads a fingerprint as a possession.
  - **Chain of custody** : the append-only [EvidenceCustodyEvent](evidence-custody-event.md) table, one row per act, with an inline *Record custody act* form that posts over HTMX and never leaves the page. Lifecycle-sourced rows are visually distinguished from hand-recorded ones.
- Right column, sticky sidebar : `{% workflow_badge %}`, the TLP chip, the legal-hold state, `retention_until` with a relative hint, `sealed_at` / `sealed_by`, `collected_at` / `collected_by`, the parent incident link, tags, the history trigger and the lifecycle stepper.

**Stepper** : `{% include "includes/lifecycle_stepper.html" %}` fed by `LifecycleStepperMixin`. Never a status select, never plain buttons. This lifecycle has three `StepKind.ARCHIVED` steps (`released`, `destroyed`, `archived`), so the dagre renderer draws three detached exits and needs an explicit visual check at desktop and mobile widths in **both** light and dark mode before merge. The `destroy` transition is the module's first user of the confirmation modal and is checked in both themes on the same pass.

**On the incident detail page**, evidence appears as a card in the left column : one row per item with its hash, sealed state, TLP, legal hold, retention date and a danger badge when `last_integrity_check_ok` is `False`. Create, update and delete use `HtmxFormMixin` drawer modals, with mobile-first care on the upload widget and the sticky action bar.

## Translations

Every user-facing string is wrapped with `_()` / `pgettext_lazy()` in Python or `{% trans %}` in templates and has a French translation in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `manage.py compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`, so a collision breaks CI outright.

**Enum labels, field verbose names and template strings** whose English already exists in the catalogue use `pgettext_lazy("incident", ...)` in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po` file. For this entity that covers:

| Label | Where | Existing bare entry |
|---|---|---|
| `Email` | `EvidenceType.EMAIL` | present, `msgstr "Email"` |
| `Document` | `EvidenceType.DOCUMENT` | present, `msgstr "Document"` |
| `Other` | `EvidenceType.OTHER` | present four times, bare entry `msgstr "Autre"` |
| `Evidence` | the evidence card title on the incident detail page | present, `msgstr "Preuves"` (plural, wrong for a singular item label) |
| `Integrity` | the Integrity card title | present, `msgstr "Intégrité"` |

`Collection method`, `Location`, `Notes` and `Source` already exist with a French translation that is correct in this context, so the same `msgid` is reused and **no new entry is added** : gettext merges the occurrences into one entry with several `#:` references, which is not a duplicate.

**Step and transition labels are different, and must never use `pgettext_lazy`.** `lifecycle_to_json()` stringifies each label with `str(...)` and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy` (`core/lifecycle.py` `lifecycle_from_json()`), so a step label carrying a `msgctxt` in code loses that context after the `post_migrate` round-trip through `LifecycleDefinition` and resolves to whatever the bare `msgid` maps to. Two labels in this lifecycle collide, and both are therefore **renamed in English** rather than disambiguated by context:

| Intended label | Existing bare entry | Decision |
|---|---|---|
| `retained` step "Retained" | `Retained` -> "Retenu" (as in *a retained risk*, i.e. selected) | **Rename to "Retained in custody"** -> "Conservée sous scellé". A `msgctxt` would be stripped by the round-trip and the step would read as *selected*, which is the opposite of what a custody state means. |
| `draft -> collected` transition "Register" | `Register` -> "Registre" (the noun) | **Rename to "Register the item"** -> "Enregistrer l'élément". The bare entry is a noun; a transition label must be a verb. |
| `draft` step "Draft registration" | `Draft` -> "Brouillon" | New `msgid`, no collision. Deliberately not the bare "Draft", so the step reads as *a registration not yet confirmed* rather than *a document being written*. |
| `archived` step "Archived" | `Archived` -> "Archivé" | **Reuse.** The core `archived_step()` already emits this exact string and the French is correct. |
| "Archive" / "Restore" transitions | present as the core bookend labels | **Reuse.** |

The remaining step and transition labels ("Collected", "Secured", "Analysed", "Released", "Destroyed", "Seal", "Record analysis", "Retain", "Release to a counterparty", "Destroy") are new bare `msgid`s with no collision. After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- ISO/IEC 27001:2022 **A.5.28** (collection of evidence) : identification, collection, acquisition and preservation of evidence
- ISO/IEC 27037 (identification, collection, acquisition and preservation of digital evidence) : the source of the acquisition-method and chain-of-custody vocabulary used here
- ISO/IEC 27035-2 (guidelines to plan and prepare for incident response) : evidence handling as a prepared procedure, documented in [IncidentResponsePlan](incident-response-plan.md)`.evidence_procedure`
- FIRST Traffic Light Protocol 2.0 : the `tlp` handling caveat
- [EvidenceCustodyEvent](evidence-custody-event.md) : the append-only chain-of-custody ledger
- [Incident](incident.md) : the parent, its lifecycle, the closure gate that requires every item to have left `collected`, and the archive / restore correction applied module-wide
- [IncidentTimelineEntry](incident-timeline-entry.md) : the chronology, whose entries point at evidence through `related_evidence`
- [IncidentNotification](incident-notification.md) : the other storage pattern in this module (`BinaryField` proof-of-filing)
- [SupportAsset](../m2-assets/support-asset.md) : the registered source of an artefact
- [README.md](README.md) : module business rules, permission codenames, notifications and the `INCIDENT_EVIDENCE_MAX_UPLOAD_BYTES` environment variable
- [governance/workflow.md](../governance/workflow.md) and [governance/lifecycle.md](../governance/lifecycle.md) : the lifecycle framework, `LifecycleEvent` and the engine internals
- [governance/history.md](../governance/history.md) : `HistoricalRecords` and the merged history timeline

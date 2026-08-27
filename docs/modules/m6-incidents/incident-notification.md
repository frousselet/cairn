# IncidentNotification

`incidents.models.notification.IncidentNotification`

One regulatory or contractual **notification obligation** : exactly one row per (incident, regime, recipient) triple. The obligation is the unit of record, not the message. A row exists as soon as the obligation is conceivable, carries the legal clock, carries the decision on whether it applies, and carries the trail of what was actually filed against it.

File : `incidents/models/notification.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`INOT`**, e.g. `INOT-1`), `tags`, `version`, `created_by`, `django-simple-history` audit trail, and the dedicated **`incident_notification`** lifecycle. `workflow_perm_namespace` is overridden to `incidents.notification` : the default `app_label.model_name` would spell `incidents.incidentnotification`, which matches no feature in `PERMISSION_REGISTRY`, and every transition would then be refused for everyone. It is **not** a `ScopedModel` : it inherits the incident's scope through `scope_parent_lookup = "incident__scopes"` (see [Scope and tenancy](#scope-and-tenancy)).

Phase 1 ships the entity with a flat clock (`deadline_hours` counted from `Incident.awareness_at`). Phase 2 grafts the anchor engine onto **this same table** rather than introducing a parallel obligation entity, so no live row is ever migrated and the platform never grows a second answer to *what do we owe, to whom, by when*. Fields belonging to phase 2 are marked as such in the tables below.

## Why the decision not to notify is a governed state

This is the argument the whole entity is built on, and it is worth stating before the fields.

GDPR Art. 33(1) does not say *notify the supervisory authority*. It says notify **unless the breach is unlikely to result in a risk to the rights and freedoms of natural persons**. The omission is not the absence of an act : it is a legal act, taken under a derogation the controller must be able to justify, and Art. 33(5) requires it to be documented well enough for the authority to verify compliance. NIS2 Art. 23 and DORA Art. 19 work the same way : an incident that is judged not significant produces no filing, and the judgement is the thing the regulator inspects.

An obligation that was correctly not notified therefore has to leave a record with four elements, all four of them:

1. a **named decider** (`decided_by`) who held the permission to decide;
2. a **timestamp** (`decided_at`) that can be compared against the clock;
3. a **written rationale** (`decision_rationale`) - the single most audited sentence in a breach file;
4. an **approval**, in the sense that reaching the omission step requires `incidents.notification.approve` and a mandatory transition comment, so a responder cannot quietly rule out an obligation alone at 02:00.

A boolean column, a nullable `sent_at`, or a filing table with no row in it can carry none of those. That is why the omission is a **terminal lifecycle step** (`not_required`) reached through an approve-gated, comment-bearing transition, and not a field write.

The same reasoning explains why obligations are **instantiated at triage rather than when someone decides to file**. An obligation nobody has thought about must be *visible* rather than *absent* : it sits in `assessed` ("To decide"), it appears in the incident's notification card, in the "To decide" bucket of the list, and it blocks closure through RG-INC-14. A design that creates the row only when the notification is drafted cannot distinguish *we considered GDPR Art. 33 and concluded it did not apply* from *nobody looked*, which is precisely the distinction an inspection turns on.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `INOT-N`, unique | Business reference, citable in a filing and in correspondence with the authority |
| `regime` | enum | required, max 32 | `NotificationRegime`. The legal or contractual basis of the obligation. Snapshotted from the template in phase 2 (RG-INC-30). |
| `recipient_kind` | enum | required, max 25 | `NotificationRecipientKind`. Class of recipient. |
| `recipient_name` | string | optional, max 255, blank default | Free-text recipient when it is not a registered stakeholder, supplier or authority. Required when every recipient FK is null **and** the obligation is not addressed to an authority of record. |
| `recipient_key` | string | max 255, blank default, **derived** | Non-nullable recipient discriminator computed in `save()`, used by the uniqueness constraint. See [Uniqueness of an obligation](#uniqueness-of-an-obligation). Never edited, never exposed as a writable field. |
| `obligation_reference` | string | optional, max 255, blank default | The cited article, e.g. `GDPR Art. 33(1)`, `NIS2 Art. 23(4)(a)`. Snapshotted from the template's `legal_reference` in phase 2. |
| `content_requirements` | text | optional, HTML, blank default | The legal checklist of what the filing must contain, rendered beside the drafting field so the drafter never leaves the page to find it. Snapshotted in phase 2. |
| `deadline_hours` | int | optional, `PositiveIntegerField` | Statutory delay in wall-clock hours from the anchor. Typical values `24`, `72`, `720`. Null **if and only if** `no_fixed_deadline` is `True`. |
| `no_fixed_deadline` | boolean | required, default `False` | The obligation is a "without undue delay" duty with no numeric limit (GDPR Art. 33(2), Art. 34(1), NIS2 Art. 23(1) to recipients). `due_at` stays null, the row is never counted late, and it surfaces in its own bucket. **Never fabricate a deadline for an obligation that legally has none.** |
| `clock_anchor` | enum | required, default `awareness_at`, max 30 | **Phase 2.** `ClockAnchor` : which timestamp starts the clock. Phase 1 behaves as if this were always `awareness_at`. |
| `anchor_at` | datetime | optional, indexed | **Phase 2.** The resolved anchor timestamp actually used, **stored** so the derivation is auditable and historised rather than re-derived by today's code against today's data. Frozen with `due_at` at the first filing. |
| `due_at` | datetime | optional, indexed | The statutory deadline. Recomputed in `save()` from the anchor plus `deadline_hours` **only while `first_submitted_at` is null**; never editable directly on any surface. Stored rather than derived so lateness is filterable, sortable, indexable and reachable from the calendar, the kanban, the escalation command and MCP. |
| `decision` | enum | required, default `undecided`, max 15 | `NotificationDecision`. Mirrors the lifecycle step and is set by the `transition_to()` override, kept as a column so filters, list facets, the closure gate and MCP enums never have to read the lifecycle. |
| `decision_rationale` | text | optional, blank default | Required non-blank when `decision = not_required` (DB `CheckConstraint` **and** the transition's `requires_comment`). The Art. 33(1) justification. |
| `decided_by` | relation | FK -> User, `SET_NULL`, optional, `related_name="incident_notification_decisions"` | Who took the decision. Stamped by the transition, never by a form. |
| `decided_at` | datetime | optional, **write-once** | When the decision was taken. Stamped by the transition. |
| `channel` | enum | optional, blank default, max 20 | `NotificationChannel` : how the notification was actually transmitted. Declared once in `incidents/constants.py` and shared with [NotificationFiling](notification-filing.md), with the same `max_length` on both fields. |
| `content` | text | optional, HTML, blank default | The exact text transmitted (GDPR Art. 33(3) minimum content : nature, DPO contact, likely consequences, measures taken). **Write-once once `sent_at` is set.** |
| `sent_at` | datetime | optional, **write-once** | Transmission timestamp, stamped by the filing transition. Must be `<= now` : a filing cannot be recorded in the future. |
| `sent_by` | relation | FK -> User, `SET_NULL`, optional, `related_name="sent_incident_notifications"` | Who filed it. |
| `first_submitted_at` | datetime | optional, **write-once** | **Phase 2.** Stamped by the first [NotificationFiling](notification-filing.md). Once set, `anchor_at` and `due_at` stop recomputing for good. |
| `late_by` | duration | optional, **write-once** | **Phase 2.** `DurationField`. Frozen lateness at the first filing : `first_submitted_at - due_at` when positive, otherwise null. Null when `no_fixed_deadline`. The frozen breach record. |
| `acknowledgement_reference` | string | optional, max 255, blank default | The authority's case, ticket or receipt number. Required to reach `acknowledged`. |
| `acknowledged_at` | datetime | optional | When receipt was confirmed by the recipient. |
| `proof_file_content` | binary | optional, `editable=False` | The filed document or the portal receipt, stored as bytes following `Contract.file_content`, `Certificate.file_content` and `TrustCenterDocument.file_content`, so backup and restore stay a single source of truth. Capped by `INCIDENT_NOTIFICATION_MAX_PROOF_BYTES`. Excluded from list serializers, from MCP `list_fields` and from `HistoricalRecords`. Not base64 in a `TextField`, which would bloat the row, the historical table and every API and MCP payload. In phase 2 the authoritative proof moves to the filing; see [Relationship with NotificationFiling](#relationship-with-notificationfiling). |
| `proof_filename` | string | optional, max 255, blank default | Original filename of the proof. |
| `source` | enum | required, default `auto`, max 10 | `ObligationSource` : whether the row was generated from the plan or the template, or added by hand. Governs deletability (see [Deleting an obligation](#deleting-an-obligation)). |
| `workflow_state` | string | indexed, default `draft` | Lifecycle step (`incident_notification`) |
| `tags` | relation | M2M -> `context.Tag` | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | Timestamps |
| `history` | `HistoricalRecords(excluded_fields=["proof_file_content"])` | | Audit trail. Every deadline recomputation is historised, so the derivation of a due date is reconstructable months later. |

### Relations

| Name | Type | Target | Reverse accessor | Description |
|---|---|---|---|---|
| `incident` | FK, `PROTECT`, required | [Incident](incident.md) | `notifications` | The incident the obligation arises from. `PROTECT` : an incident that owes, or owed, a regulator anything can never be deleted. |
| `recipient_stakeholder` | FK, `SET_NULL`, optional | `context.Stakeholder` | `incident_notifications` | Registered stakeholder recipient, reusing the existing stakeholder register rather than retyping a contact. |
| `recipient_supplier` | FK, `SET_NULL`, optional | `assets.Supplier` | `incident_notifications` | Supplier recipient. Also the **controller** we must notify under GDPR Art. 33(2) when we act as processor. |
| `authority` | FK, `PROTECT`, optional | [ReportingAuthority](reporting-authority.md) | `obligations` | **Phase 2.** The body the filing goes to, with its portal, mailbox and procedure. |
| `template` | FK, `PROTECT`, optional | [ReportingObligationTemplate](reporting-obligation-template.md) | `obligations` | **Phase 2.** The rule this obligation was generated from. `PROTECT` : a template with instantiated obligations can never be deleted. The obligation's legal terms are snapshotted, not read through this FK (RG-INC-30). |
| `depends_on` | FK -> self, `SET_NULL`, optional | IncidentNotification | `dependents` | **Phase 2.** The sibling obligation whose **filing** anchors this one. See [The clock model](#the-clock-model). |
| `proof_evidence` | FK, `SET_NULL`, optional | [IncidentEvidence](incident-evidence.md) | `notification_proofs` | Used when the receipt is itself registered as evidence under A.5.28. |
| `filings` | reverse FK | [NotificationFiling](notification-filing.md) | | **Phase 2.** The append-only log of actual transmissions against this obligation. |

### Meta

- `ordering = ["incident", "due_at"]`
- `Index(fields=["due_at", "workflow_state"])` : the index the "are we late" query runs on, on the list page, in the calendar, in the dashboard widget and in the daily escalation command.
- `UniqueConstraint(fields=["incident", "regime", "recipient_key"], name="unique_notification_per_incident_regime_recipient")`
- `CheckConstraint notification_not_required_has_rationale` : `~Q(decision="not_required") | ~Q(decision_rationale="")`
- `CheckConstraint notification_deadline_hours_xor_no_fixed_deadline` : `Q(no_fixed_deadline=True, deadline_hours__isnull=True) | Q(no_fixed_deadline=False, deadline_hours__isnull=False)`
- `CheckConstraint notification_pending_anchor_only_for_previous_stage` (phase 2) : an obligation may carry `no_fixed_deadline=False` with a null `due_at` **only** when `clock_anchor = previous_stage`. Every other combination of a numeric deadline with no due date is a bug, and the database says so.

### Uniqueness of an obligation

The obvious constraint - `UniqueConstraint(["incident", "regime", "recipient_stakeholder", "recipient_supplier", "recipient_name"])` - **does not prevent the duplicate it is written for**, and the module does not use it.

In PostgreSQL, NULLs are distinct inside a unique index by default. On every auto-generated authority obligation both recipient FKs are null, so two identical `gdpr_art33_authority` rows on the same incident do not collide : the index treats them as different keys and inserts both. This is not a theoretical case. Obligation generation deliberately **re-runs** at three points : at triage, on `INCIDENT_SEVERITY_RAISED` (a severity raise can cross a template's `min_severity` floor and start a 24-hour NIS2 clock that did not exist an hour earlier), and on confirmation of a personal data breach (which is when `controller_role` and the Art. 34 high-risk verdict become known). Each re-run would silently add a second copy of every authority obligation, and the incident would then show two 72-hour GDPR clocks, one of which nobody is watching.

Two fixes are needed, and both are taken :

1. **A non-nullable discriminator.** `recipient_key` is computed in `save()` and holds `stakeholder:<uuid>`, `supplier:<uuid>`, `authority:<uuid>`, `name:<casefolded recipient_name>`, or `""` when the obligation is addressed to the regime's authority of record with no authority row yet (the phase-1 shape). The unique constraint is then over three **non-nullable** columns and behaves identically on PostgreSQL and on the SQLite the test suite runs against. `nulls_distinct=False` (PostgreSQL 15+) would be a shorter fix, but Django raises `models.W047` and drops the clause on backends that do not support it, so `core.settings_test` could never exercise it : the constraint would be untested precisely where the regression would be introduced.
2. **An idempotent generator.** The constraint is the last line of defence, never the mechanism. `generate_obligations()` resolves each candidate through an explicit `get_or_create`-style lookup on `(incident, regime, recipient_key)`, updates nothing on an existing row, and returns the set of rows it actually created. Relying on the constraint alone would turn a re-run into an `IntegrityError` in the middle of a severity-raise save, which is a worse failure than the duplicate.

The regression test asserts that running the generator twice over the same incident leaves the obligation count unchanged and creates no second `core.LifecycleEvent`.

## Enums

Reproduced verbatim from `incidents/constants.py` (DB value = Label).

### NotificationRegime

| Value | Label |
|---|---|
| `gdpr_art33_authority` | GDPR Art. 33(1) - supervisory authority |
| `gdpr_art34_data_subject` | GDPR Art. 34 - data subjects |
| `gdpr_art33_2_controller` | GDPR Art. 33(2) - controller |
| `nis2_early_warning` | NIS2 Art. 23(4)(a) - early warning |
| `nis2_notification` | NIS2 Art. 23(4)(b) - incident notification |
| `nis2_intermediate` | NIS2 Art. 23(4)(c) - intermediate report |
| `nis2_final` | NIS2 Art. 23(4)(d) - final report |
| `nis2_recipients` | NIS2 Art. 23(1) - recipients of the service |
| `dora_initial` | DORA Art. 19 - initial report |
| `dora_intermediate` | DORA Art. 19 - intermediate report |
| `dora_final` | DORA Art. 19 - final report |
| `eprivacy` | ePrivacy Directive Art. 4(3) |
| `cra` | Cyber Resilience Act Art. 14 |
| `sector_regulator` | Sector regulator |
| `law_enforcement` | Law enforcement |
| `cert_csirt` | CERT / CSIRT |
| `contractual_customer` | Contractual - customer |
| `contractual_supplier` | Contractual - supplier |
| `insurer` | Insurer |
| `internal_management` | Internal management |
| `public_communication` | Public communication |
| `other` | Other |

### NotificationRecipientKind

| Value | Label |
|---|---|
| `supervisory_authority` | Supervisory authority |
| `csirt` | CSIRT |
| `competent_authority` | Competent authority |
| `financial_regulator` | Financial regulator |
| `law_enforcement` | Law enforcement |
| `data_subject` | Data subject |
| `customer` | Customer |
| `controller` | Controller |
| `supplier` | Supplier |
| `insurer` | Insurer |
| `internal` | Internal |
| `public` | Public |

### NotificationDecision

| Value | Label |
|---|---|
| `undecided` | Undecided |
| `required` | Required |
| `not_required` | Not required |

### NotificationChannel

Shared with [NotificationFiling](notification-filing.md).

| Value | Label |
|---|---|
| `portal` | Portal |
| `email` | Email |
| `postal` | Postal mail |
| `phone` | Phone |
| `api` | API |
| `in_person` | In person |
| `public_notice` | Public notice |

### ClockAnchor

Phase 2.

| Value | Label |
|---|---|
| `occurred_at` | Occurrence |
| `detected_at` | Detection |
| `awareness_at` | Awareness |
| `significance_determined_at` | Significance determination |
| `previous_stage` | Previous filing |

### ObligationSource

| Value | Label |
|---|---|
| `auto` | Generated |
| `manual` | Added manually |

## The clock model

Everything about statutory timing lives here, in one place, so an implementer never has to reconstruct it from three files.

### The anchor

The first four `ClockAnchor` values are, deliberately, **the exact field names on [Incident](incident.md)** : `occurred_at`, `detected_at`, `awareness_at`, `significance_determined_at`. Resolution is therefore a `getattr(self.incident, self.clock_anchor)` with no mapping dictionary to drift out of date, and a `grep` for the enum value finds both the constant and the field it reads. `previous_stage` is the one value that is not an incident field, which is exactly why it needs its own branch and its own foreign key.

```python
def resolve_anchor(self):
    if self.first_submitted_at:          # frozen : never recompute a filed obligation
        return self.anchor_at
    if self.no_fixed_deadline:
        return None
    if self.clock_anchor == ClockAnchor.PREVIOUS_STAGE:
        return self.depends_on.first_submitted_at if self.depends_on_id else None
    return getattr(self.incident, self.clock_anchor)
```

`awareness_at` is the default and is the anchor of every GDPR and NIS2 obligation in the shipped catalogue. It is **not** `detected_at` : anchoring a statutory deadline to technical detection is legally wrong, and it is the first thing an inspector attacks. The distinction, its justification field and its rules live on [Incident](incident.md) (RG-INC-13).

### The derived deadline

`save()` sets `anchor_at = resolve_anchor()` and, when both `anchor_at` and `deadline_hours` are known, `due_at = anchor_at + timedelta(hours=deadline_hours)`. All arithmetic is **wall-clock**, which is correct for GDPR, NIS2 and DORA : the 72 hours of Art. 33(1) run through nights, weekends and public holidays. A contractual clause written in business days cannot be expressed by this model and is stated as out of scope rather than approximated (RG-INC-33 records the same discipline for RTO claims).

`due_at` is **stored, not computed on read**. A property would be unfilterable, unsortable, unindexable and invisible to the calendar, the kanban, the dashboard widget, the daily escalation command and MCP - which is to say invisible everywhere the deadline actually matters. It is never editable directly : it carries no form field, is `read_only` in every serializer and is absent from every MCP `writable_fields` list.

### `previous_stage` and `depends_on`

NIS2 Art. 23(4)(d) gives one month for the final report, counted **from the incident notification** of Art. 23(4)(b), not from awareness. An implementation that anchors it on awareness produces a deadline that is wrong by however long the 72-hour notification actually took, on every single NIS2 incident in the register, always in the direction that makes the organisation look later than it is.

The `nis2_final` obligation therefore carries `clock_anchor = previous_stage` and `depends_on` pointing at the `nis2_notification` obligation on the same incident. Its `anchor_at` is that row's `first_submitted_at`, and it stays **null until the 72-hour notification is actually filed**. Filing an obligation therefore recomputes its `dependents` in the same transaction.

### The three deadline buckets

An obligation with a null `due_at` is not one thing but two, and collapsing them is how a real deadline disappears from a dashboard :

| Bucket | Condition | Behaviour |
|---|---|---|
| **Dated** | `due_at` is not null | Counted in the overdue query, shown with a live countdown, swept by `escalate_incident_deadlines` |
| **No statutory deadline** | `no_fixed_deadline = True`, `due_at` null | Never counted late. Surfaced in its own "no statutory deadline" bucket with its own badge, never hidden from the list. `NOTIFICATION_DEADLINE_APPROACHING` never fires; the obligation is still blocking closure until decided. |
| **Deadline pending** | `no_fixed_deadline = False`, `due_at` null, `clock_anchor = previous_stage`, `depends_on` not yet filed | Shown as *pending : starts when INOT-N is filed*, with a link to the obligation it waits on. Explicitly **not** merged into the bucket above : the deadline exists, it has simply not started. The `notification_pending_anchor_only_for_previous_stage` constraint keeps any other row out of this bucket. |

### Overdue is derived, lateness is frozen

**Overdue** is always derived, never stored : `due_at < now() AND sent_at IS NULL AND the step is not terminal`. It is a query, so it is right the instant the clock passes, and there is no status column to fall out of date.

**Lateness**, once a filing exists, is frozen forever. At the first filing, in one transaction, the obligation stamps `first_submitted_at`, computes `late_by` (the positive part of `first_submitted_at - due_at`, null when there is no `due_at`), and `NotificationFiling.was_late` records the same verdict on the filing itself. After that, `save()` stops recomputing `anchor_at` and `due_at` entirely.

This is not an optimisation, it is the point. `awareness_at` stays editable after triage, because facts change : a forensic finding can move the moment the organisation is deemed to have become aware. Without the freeze, correcting the anchor forward by six hours would silently move `due_at` past a filing that was late when it was made, and an obligation that breached the 72-hour limit would quietly stop having breached it, with nothing in the record to show it ever did. With the freeze, the correction is recorded on the incident and historised, the filed obligation keeps its `late_by`, and a material change to the facts is communicated the way the law expects : as a **correction filing** on the same obligation (see [NotificationFiling](notification-filing.md)), not as a retroactive edit.

### Recomputation triggers

While `first_submitted_at` is null, `anchor_at` and `due_at` are recomputed on : any save of the obligation; a change to the anchoring field on the incident (propagated by `Incident.save()`); the severity raise that re-runs generation; the confirmation of a [PersonalDataBreach](personal-data-breach.md); and the filing of an obligation this one `depends_on`. Every recomputation goes through a per-row `save()`, never `QuerySet.update()`, so `HistoricalRecords` captures each one and the derivation of a due date is reconstructable from the history alone.

## Lifecycle

`LIFECYCLE_NAME = "incident_notification"`, `layout="graph"`, generated by `lifecycle_from_state_flags()` in `incidents/lifecycles.py` from the state and transition constants in `incidents/constants.py`, and registered from `IncidentsConfig.ready()`. Unlike `incident` and `incident_evidence`, this lifecycle needs no step trigger, so it keeps the generated form the project's rules prescribe. It declares **both** bookend steps explicitly - see below.

### Steps

| Code | Label | StepKind | In reports | Linkable | Deletable | Tone | Meaning |
|---|---|---|---|---|---|---|---|
| `draft` | Draft | `DRAFT` | no | no | **yes** | `neutral` | Being written up by hand; not yet an obligation of record |
| `assessed` | To decide | `INTERMEDIATE` | **yes** | no | **yes** | `warning` | The obligation exists and **no decision has been taken**. This is the state the whole "an unanswered obligation is visible rather than absent" argument rests on, and the state the closure gate refuses. |
| `required` | Required | `INTERMEDIATE` | **yes** | no | no | `info` | Decided to apply; `decision = required` |
| `drafted` | Drafted | `INTERMEDIATE` | **yes** | no | no | `primary` | The filing text is written and under review |
| `sent` | Sent | `INTERMEDIATE` | **yes** | no | no | `success` | Transmitted; `sent_at`, `first_submitted_at` and `late_by` are frozen |
| `acknowledged` | Acknowledged | `INTERMEDIATE` | **yes** | no | no | `dark` | Receipt confirmed by the recipient, with a case number |
| `not_required` | Not required | `ARCHIVED` (terminal) | **yes** | no | no | `muted` | The Art. 33(1) omission, decided, justified and approved. **This is the step an auditor asks to see.** |
| `archived` | Archived | `ARCHIVED` | no | no | no | `muted` | The generic exit, declared **explicitly** |

`not_required` keeps `counts_in_reports = True`, unlike the `discarded` step of [SecurityEvent](security-event.md). The difference is deliberate : a false-positive event is not a security event of record, whereas an obligation ruled out **is** part of the compliance record and must appear in the incident register, the notification report and any Art. 33(5) extract. An omission that vanishes from reports is an omission nobody can review.

### Transitions

`permission_action` is appended to `workflow_perm_namespace` (`incidents.notification`).

| Verb | Transition | `permission_action` | `requires_comment` | Side effects |
|---|---|---|---|---|
| Open obligation | `draft -> assessed` | `update` | no | Hand-declared. The step every generated obligation is moved to immediately after insert. |
| Confirm required | `assessed -> required` | `update` | no | Sets `decision = required`; stamps `decided_by` and `decided_at` |
| Decide not to notify | `assessed -> not_required` | **`approve`** | **yes** | Sets `decision = not_required`; writes the mandatory comment into `decision_rationale`; stamps `decided_by` and `decided_at` |
| Draft the filing | `required -> drafted` | `update` | no | |
| Record submission | `drafted -> sent` | `update` | no | Stamps `sent_at` and `sent_by`; `content` becomes write-once; freezes `first_submitted_at` and `late_by`; creates the first [NotificationFiling](notification-filing.md) (phase 2) |
| Record submission made outside Cairn | `required -> sent` | `update` | no | Same side effects. The path for a filing made on a portal at 03:00 and recorded afterwards. |
| Record acknowledgement | `sent -> acknowledged` | `update` | no | Requires `acknowledgement_reference`; sets `acknowledged_at` |
| Reopen for correction | `sent -> drafted` | `update` | **yes** | Phase 1 only. Phase 2 replaces this with an additional filing carrying `is_correction = True`. |
| Authority requested more information | `acknowledged -> drafted` | `update` | **yes** | Phase 2 records the request and the response as successive filings on this same obligation |
| Archive | `* -> archived` | **`approve`** | **yes** | Hand-declared, not auto-wired |
| Restore | `archived -> draft` | **`approve`** | no | Hand-declared, and additionally gated by G-07 |

**Recording a filing needs only `update`** (RG-INC-26). This is a deliberate asymmetry with the omission path : putting an approver in the loop on a 24-hour NIS2 clock manufactures late filings, and a late filing is a breach while an early one never is. Only the transitions that declare an obligation **extinguished** - `not_required`, and the archive bookend - require `approve`.

> **Both bookend edges are hand-declared, and so is `draft -> assessed`.** `lifecycle_from_state_flags()` auto-wires `draft -> <initial step>`, `ANY -> archived` and `archived -> draft` only when the corresponding step is absent from the state-flag list (`core/lifecycle.py` `lifecycle_from_state_flags()`). The auto-wired archive and restore edges carry **no `permission_action` and no `requires_comment`**, and `user_can_perform()` (`core/lifecycle.py` `user_can_perform()`) allows any transition whose `permission_action` is empty. Left generated, they would give anyone able to reach the transition endpoint an **archive -> restore -> delete** path out of an obligation sitting in `required` or even `sent` : a regulatory obligation, including the record of a decision not to notify, could be erased by a user holding no approve permission at all. This lifecycle therefore declares `draft` and `archived` explicitly so nothing is auto-wired, and lists all three edges in `NOTIFICATION_TRANSITIONS` with explicit actions.

### Transition gates

Per RG-INC-08, every gate below lives in a `transition_to()` override on `IncidentNotification`, **never** in `Transition.form_class`, `allowed_roles` or `allowed_users`. `lifecycle_to_json()` (`core/lifecycle.py` `lifecycle_to_json()`) omits those three fields by design, `lifecycle_from_json()` rebuilds transitions without them, and `get_lifecycle()` prefers the `post_migrate`-seeded `LifecycleDefinition` row over the code default, so a gate declared that way is silently dead on every migrated database. All three write surfaces funnel through `BaseModel.transition_to()` (`core/workflow_views.py` `WorkflowTransitionView.post()`, `accounts/api/mixins.py` `_lifecycle_transition()`, `mcp/tools.py` `_transition_handler()`), so the model override is the one place that binds web, API and MCP at once. Each gate raises a translated `ValidationError` naming the missing precondition, and the whole transition body runs inside `transaction.atomic()`.

| Gate | Transition | Refused unless |
|---|---|---|
| **G-01 Named omission** (RG-INC-25) | `assessed -> not_required` | The actor holds `incidents.notification.approve` **and** supplies a comment. The comment is persisted into `decision_rationale`, not only into the `core.LifecycleEvent`, so the register itself is readable without joining the history; a DB `CheckConstraint` refuses the row if it is blank. `decided_by` and `decided_at` are stamped from the actor and the transition time. |
| **G-02 Filing preconditions** | `drafted -> sent`, `required -> sent` | `channel` is set, and either `content` is non-blank or a [NotificationFiling](notification-filing.md) is supplied with the transition. `sent_at` defaults to the transition time and is refused if it is in the future. |
| **G-03 NIS2 early warning content** (phase 2) | `drafted -> sent` where `regime = nis2_early_warning` | `Incident.is_significant`, `Incident.cross_border_impact` and `Incident.suspected_malicious` are all non-null. Art. 23(4)(a) requires the early warning to state whether the incident is suspected of being caused by an unlawful or malicious act and whether it has cross-border impact; an early warning that cannot answer those two questions cannot be completed from the record, and the gate says so rather than filing a blank. |
| **G-04 Acknowledgement** | `sent -> acknowledged` | `acknowledgement_reference` is non-blank. An acknowledgement with no case number is not an acknowledgement. |
| **G-05 Content immutability** (RG-INC-29) | all | Once `sent_at` is set, `content`, `channel` and `sent_at` are write-once : `save()` compares against the stored row and raises `ValidationError` on any attempted change. Write-once is prevented at application level and **detected** through `HistoricalRecords`; `QuerySet.update()`, `bulk_update()` and raw SQL bypass `save()`. An amendment is a new filing (phase 2) or a new obligation of the appropriate follow-up regime (phase 1), never a rewrite of what was transmitted. |
| **G-06 Clock freeze** (RG-INC-28) | all | Once `first_submitted_at` is set, `anchor_at`, `due_at` and `late_by` are never recomputed and are refused as writes. |
| **G-07 Restore** | `archived -> draft` | No `core.LifecycleEvent` on this obligation records a step other than `draft` or `archived`. An obligation that ever reached `assessed` can be archived but never restored into a deletable step. Mirrors the [Incident](incident.md) G-07 gate. |
| **G-08 Write-once stamps** (RG-INC-12) | all | `decided_at`, `sent_at`, `first_submitted_at` and `late_by` are stamped by the override only : excluded from every `ModelForm`, `read_only` in every serializer, absent from every MCP writable list, and never cleared. |

## Obligation generation and the initial step

`BaseModel.save()` calls `_ensure_initial_step()` (`context/models/base.py` `BaseModel._ensure_initial_step()`) on every insert, and `Lifecycle.initial_step` (`core/lifecycle.py` `Lifecycle.initial_step`) returns the single `StepKind.DRAFT` step. The `workflow_state` field default is the literal `"draft"`, which **is** a valid step of this lifecycle, so `_ensure_initial_step()` leaves it alone and the row lands in `draft`.

**An obligation is never "created in" `assessed`.** Writing `IncidentNotification.objects.create(..., workflow_state="assessed")` would stick - the snap only fires on a blank or unknown value - but it would leave **no `core.LifecycleEvent` row**, so the obligation would have no recorded entry into the register, which is precisely the audit trail this entity exists to produce. And a row left in `draft` because nobody made the second call is worse than absent : `draft` is `deletable=True`, the row is missing from the "To decide" bucket the visibility argument rests on, and it still carries `decision = ""`, so it blocks incident closure through RG-INC-14 with no explanation on any screen.

Every generation path therefore does, inside one `transaction.atomic()` block :

```python
obligation, created = IncidentNotification.objects.get_or_create(
    incident=incident,
    regime=regime,
    recipient_key=recipient_key,
    defaults={...snapshotted legal terms...},
)
if created:
    obligation.transition_to("assessed", user, enforce_permission=False)
```

`enforce_permission=False` is correct here : the permission was already checked on the **parent** transition the user actually performed (the incident's `detected -> triaged`), and the obligations are a consequence of it, not a separate act by the user.

Generation runs at three points, and is idempotent at all three (see [Uniqueness of an obligation](#uniqueness-of-an-obligation)) :

1. **Triage** (`detected -> triaged` on the incident) : one obligation per applicable regime. Phase 1 reads `IncidentResponsePlan.applicable_regimes`; phase 2 matches [ReportingObligationTemplate](reporting-obligation-template.md) rows in a `reportable()` lifecycle state and snapshots their legal terms onto each generated row (RG-INC-30). `personal_data_involved = True` forces `gdpr_art33_authority` regardless of configuration (RG-INC-18). An incident with `is_exercise = True` generates nothing at all (RG-INC-17) : filing a real notification for a drill is an incident in its own right.
2. **Severity raise** (`INCIDENT_SEVERITY_RAISED`) : a raise can cross a template's `min_severity` floor and start a clock that did not exist before. Its absence is a missed 24-hour NIS2 deadline, which is why it is a trigger and not a nightly job.
3. **Personal data breach confirmation** (phase 2) : `controller_role` decides which GDPR obligations exist at all - a processor owes Art. 33(2) to the controller, not Art. 33(1) to the supervisory authority - and `high_risk_to_rights` decides whether Art. 34 applies.

The module ships regression tests asserting that :

- `IncidentNotification.objects.create(...).workflow_state == "assessed"` **fails** (the row lands in `draft`);
- after `incident.transition_to("triaged", user)`, every row in `incident.notifications` is in `assessed` and each has exactly one matching `core.LifecycleEvent` with `to_step="assessed"`;
- running generation a second time (severity raise, then breach confirmation) leaves the obligation count and the `LifecycleEvent` count unchanged.

### Deleting an obligation

`draft` and `assessed` are `deletable = True` so a manually added obligation typed in error can be removed without an approver. `delete()` is overridden to refuse any row with `source = auto` : a generated obligation is answered through `not_required` with a rationale, never deleted, because deleting it destroys the evidence that the organisation considered the regime at all. From `required` onward no step is deletable on any surface.

## Relationship with NotificationFiling

Phase 1 records the transmission on the obligation itself : `channel`, `content`, `sent_at`, `sent_by`, `acknowledgement_reference`, `proof_file_content`. That is enough for a single filing and nothing more.

Phase 2 adds [NotificationFiling](notification-filing.md), the append-only log of actual transmissions, and the split becomes : **the obligation carries the duty and the clock; the filing carries the act**. GDPR Art. 33(4) phased provision and a NIS2 authority information request then become successive filings on **one** obligation rather than edits of the original or duplicate obligation rows, which is what keeps *the 72-hour notification* a single thing an auditor can point at.

The obligation-level fields are kept, not migrated : `sent_at`, `channel` and `sent_by` are mirrored from the **first** filing and stay the fast path for list rendering and filtering, and `proof_file_content` stays populated for rows filed before phase 2. The filing log is authoritative whenever the two could disagree, and the notification detail page renders the filing history rather than the mirrored fields as soon as more than one filing exists.

## Scope and tenancy

RG-INC-38. `IncidentNotification` is not a `ScopedModel` and never carries its own `scopes`. It inherits the parent incident's scope through `scope_parent_lookup = "incident__scopes"`, so it can never drift out of alignment when the incident is re-scoped.

Scope inheritance for non-`ScopedModel` children is **not currently enforced on three surfaces**, and phase 1 extends all three. This is core work in the phase-1 PR, not an incidents-app detail, and it is logged under a `### Security` entry in `CHANGELOG.md`.

| Call site | Today | Change |
|---|---|---|
| `mcp/tools.py` `_filter_by_scopes()` | Handles `context.Scope`, then a direct `scopes` M2M, then returns the queryset **unfiltered** | Accept `model` / `parent_lookup` and thread a `scope_parent_lookup` argument through `_register_crud` / `_list_handler` / `_get_handler` / `_transition_handler` / `_allowed_transitions_handler`. Without it, `list_incident_notifications` and `list_overdue_incident_notifications` return every obligation on the instance - regime, recipient, deadline and omission rationale included - to any holder of `incidents.notification.read`. |
| `core/workflow_views.py` `WorkflowTransitionView` | Guards with `if allowed_scopes is not None and hasattr(obj, "scopes")` | Honour a model-level `scope_parent_lookup`. Without it, the `not_required` decision - the GDPR Art. 33(1) omission - is performable cross-scope by a user with no access to the incident. |
| `core/history_views.py` `HistoryPartialView` | Same `hasattr(obj, "scopes")` guard | Same change. Without it, the full history of an out-of-scope obligation, including every version of its rationale, is readable. |

`ScopeFilterMixin` (`accounts/mixins.py`) and `ScopeFilterAPIMixin` (`accounts/api/mixins.py`) already support `scope_parent_lookup`, so list views and viewsets need only declare it.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-12 | `decided_at`, `sent_at`, `first_submitted_at` and `late_by` are stamped by the `transition_to()` override only : excluded from every `ModelForm`, `read_only` in every serializer, absent from every MCP writable list. Write-once is prevented at application level and **detected** through `HistoricalRecords`; `QuerySet.update()`, `bulk_update()` and raw SQL bypass `save()`. |
| RG-INC-14 | An incident cannot close while any obligation still has `decision = undecided`. The obligation register is a closure gate, not a side panel. |
| RG-INC-15 | Reclassifying an incident as a mere event is refused when any obligation already carries a `sent_at`. You cannot un-declare something you have already told a regulator about. |
| RG-INC-17 | An incident with `is_exercise = True` never instantiates obligations, and is exempt from the RG-INC-19 justification gate. |
| RG-INC-18 | `personal_data_involved = True` forces `gdpr_art33_authority` to be instantiated at triage regardless of the plan's configured regimes, and in phase 2 creates the [PersonalDataBreach](personal-data-breach.md) record (saved, then transitioned to `under_qualification`). |
| RG-INC-19 | When triage produces zero obligations, `personal_data_involved` is `False` **and** `is_exercise` is `False`, a non-blank `Incident.no_obligation_justification` is mandatory. A missing regime or template must never read as compliance on a green dashboard. |
| RG-INC-25 | An obligation whose decision is `not_required` must carry a non-blank `decision_rationale` (DB `CheckConstraint`), and reaching that step requires `incidents.notification.approve`, a mandatory comment, a named `decided_by` and a `decided_at`. This is the GDPR Art. 33(1) omission judgement. |
| RG-INC-26 | Recording an actual filing requires only `incidents.notification.update`. Only the transitions that declare an obligation extinguished require `approve`, so the operator on a 24-hour clock is never blocked waiting for an approver. |
| RG-INC-27 | `due_at` is recomputed in `save()` from the anchor plus `deadline_hours` **only while `first_submitted_at` is null**, and is never editable directly. Obligations with `no_fixed_deadline = True` carry a null `due_at`, are never counted late, and are surfaced in a dedicated bucket rather than hidden. |
| RG-INC-28 | Overdue is always **derived** (`due_at < now` AND `sent_at IS NULL` AND the step is not terminal), never stored as a status. Lateness is **frozen once** : `first_submitted_at`, `late_by` and `NotificationFiling.was_late` are stamped at the first filing and never recomputed, so a later anchor correction can never silently un-breach a filed record. |
| RG-INC-29 | `content` and `sent_at` are write-once once `sent_at` is set (prevention at application level, detection via `HistoricalRecords`). In phase 1 an amendment is a new obligation of the appropriate follow-up regime; in phase 2 it is an additional filing with `is_correction = True` and `supersedes`, on the **same** obligation, so the same-obligation relationship is never lost. |
| RG-INC-30 | Obligation terms generated from a template (`regime`, `recipient_kind`, `obligation_reference`, `clock_anchor`, `deadline_hours`, `no_fixed_deadline`, `content_requirements`, `authority`) are **snapshotted** at creation and are never rewritten by later template edits; the template FK is `PROTECT`. Generation only considers templates in a `reportable()` lifecycle state, never an `is_active` literal. |
| RG-INC-37 | Every report, KPI, calendar feed, kanban bucket and link picker filters through `reportable()` / `linkable()` / `deletable_states()`. No `incident_notification` state literal appears outside `incidents/constants.py`. |
| RG-INC-38 | Scope tenancy : the obligation is never independently scoped and inherits the incident's scope through `scope_parent_lookup = "incident__scopes"` on the web, API and MCP surfaces. |
| RG-INC-39 | Gated by `incidents.notification.*`. Phase 2 adds no new permission feature : [PersonalDataBreach](personal-data-breach.md) gates on the same one. |
| RG-INC-40 | The daily `escalate_incident_deadlines` command sweeps obligations with `decision = required`, a null `sent_at` and a `due_at` inside the alert window or already past. It takes `--dry-run`, excludes terminal steps via `workflow_state__in`, and iterates with a per-row `save()` - never `QuerySet.update()` - so `HistoricalRecords` captures every change. |

## Endpoints

### REST

Base path `/api/v1/incidents/`, router registration `notifications`.

- `GET /api/v1/incidents/notifications/` : list, filtered by `IncidentNotificationFilter` (`incident_id`, `regime`, `recipient_kind`, `decision`, `status`, `overdue`, `due_before`, `no_fixed_deadline`). `overdue` is a method filter deriving `due_at < now AND sent_at IS NULL AND step not terminal` - there is no stored overdue flag to filter on.
- `POST /api/v1/incidents/notifications/` and `POST .../batch/` (max 100 items, non-atomic, per-item `{index, status, id, reference}`). A manually added obligation is created in `draft` and moved on by a transition like any other row.
- `GET/PUT/PATCH/DELETE /api/v1/incidents/notifications/<uuid>/`
- `GET/POST /api/v1/incidents/notifications/<uuid>/transition/` : `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`, so every gate above applies identically to an API caller.
- `GET /api/v1/incidents/notifications/<uuid>/history/` : `core.history.build_timeline`.
- `GET /api/v1/incidents/notifications/<uuid>/proof/` : a dedicated permission-checked and scope-checked detail action returning the proof bytes. `proof_file_content` never appears in a list or detail payload.

Viewset stack in the house order : `BatchCreateMixin`, `ScopeFilterAPIMixin` (with `scope_parent_lookup = "incident__scopes"`), `LifecycleAPIMixin`, `HistoryAPIMixin`, `CreatedByMixin`, `viewsets.ModelViewSet`. Permissions use `ModulePermission` plus the module's `_IncidentViewSet` base (`permission_module = "incidents"`, `custom_action_map = {"transition": "update"}`), following the newest module precedent (`trust_center/api/views.py` `_ManagedViewSet`) rather than importing another app's `ModulePermission` subclass. `IncidentNotificationSerializer` / `IncidentNotificationListSerializer`, with `read_only_fields` covering `id`, `reference`, `created_by`, `created_at`, `updated_at`, `version`, `recipient_key`, `decision`, `decided_by`, `decided_at`, `sent_at`, `sent_by`, `anchor_at`, `due_at`, `first_submitted_at` and `late_by`. `status` is exposed as `CharField(source="workflow_state", read_only=True)`, and `is_overdue` as a read-only derived boolean.

### MCP

- `_register_crud(server, "incident_notification", IncidentNotification, "incidents.notification", scope_parent_lookup="incident__scopes", ...)` generates `list_incident_notifications`, `get_incident_notification`, `create_incident_notification`, `batch_create_incident_notifications`, `update_incident_notification`, `delete_incident_notification`, `transition_incident_notification`, `incident_notification_allowed_transitions`, `get_incident_notification_history`. Filters : `incident_id`, `regime`, `recipient_kind`, `decision`, `status`.
- `list_overdue_incident_notifications` (bespoke; requires `incidents.notification.read`) returns obligation, incident, regime, recipient, `due_at`, hours overdue and owner, scope-filtered. This is the single highest-value read tool in the module for an external agent : it is the *are we late* question, answered in one call.
- `record_notification_filing` (bespoke, phase 2; requires `incidents.notification.update`) creates the [NotificationFiling](notification-filing.md) and freezes `first_submitted_at`, `late_by` and `was_late` atomically, so an agent cannot record a transmission without freezing the lateness verdict that goes with it.
- `decision`, `decided_by`, `decided_at`, `sent_at`, `anchor_at`, `due_at`, `first_submitted_at` and `late_by` are absent from `writable_fields` : the decision and the filing are transitions, never field writes. `proof_file_content` is never readable or writable through MCP.
- Every enum field carries an explicit `enum` list in `field_overrides`; `content` and `content_requirements` are declared with `_html_field()`; each recipient FK id carries a description naming its lookup tool.

`mcp/tools.py` `HELP_TEXT` gains `IncidentNotification=INOT` in the reference-prefix block, and `assistant/catalog.py` gains a read-only `list_incident_notifications` `ToolSpec` with `detail_route="incidents:notification-detail"`.

## Permissions

| Codename | Description |
|---|---|
| `incidents.notification.read` | List and read obligations, deadlines and decisions |
| `incidents.notification.create` | Add an obligation by hand |
| `incidents.notification.update` | Edit an obligation, confirm it is required, draft it, **record a filing**, record an acknowledgement |
| `incidents.notification.approve` | Decide **not** to notify, archive, restore |
| `incidents.notification.delete` | Delete a manually added obligation still in `draft` or `assessed` |

The same feature gates [PersonalDataBreach](personal-data-breach.md) and [NotificationFiling](notification-filing.md) in phase 2 : RG-INC-39 caps the module at exactly six features, and this is one of them.

## UI

- **Detail** (`/incidents/notifications/<uuid>/`) : a strict 2-column card layout, no nav-tabs. Left column, stacked cards :
  - *Obligation* : regime, `obligation_reference`, recipient, and the `content_requirements` checklist rendered **beside** the drafting field, so the drafter reads the legal minimum content without leaving the page.
  - *Decision* : `decision_rationale`, `decided_by`, `decided_at`. Rendered as a prominent, full-width card whenever `decision = not_required`, because that is the sentence an inspector reads first. When the decision is still `undecided` the card shows an explicit "no decision taken" state, never an empty block.
  - *Filing* : channel, content, `sent_at`, acknowledgement reference, proof download; in phase 2, the [NotificationFiling](notification-filing.md) history table with `supersedes` chains.
  - Right column, sticky : `{% workflow_badge %}`, the deadline with a live countdown, **the anchor it derives from** stated in words ("72 h from awareness, 14 Mar 09:12"), the "no statutory deadline" or "deadline pending" badge where applicable, the incident link, and the history trigger.
- **On the incident detail page**, obligations render as a *Regulatory notifications* card : regime, recipient, `due_at`, live countdown, a muted badge for `no_fixed_deadline` rows, a distinct badge for `deadline pending` rows, and a red overdue state. A row in `assessed` is visually the loudest thing in the card : an undecided obligation is the one thing on that page that must not read as calm.
- **List** (`/incidents/notifications/`) : the house stack, with predefined filters for *To decide*, *Overdue*, *Due in 24 h*, *Not required* and *No statutory deadline*, and `list_rail_kpis` showing the undecided and overdue counts.
- **Stepper** : `{% include "includes/lifecycle_stepper.html" %}` fed by `LifecycleStepperMixin`. Never a decision select, never plain buttons : the decision **is** the transition. This lifecycle has two `StepKind.ARCHIVED` steps (`not_required`, `archived`), so the dagre renderer draws two detached exits; check both at desktop and mobile widths in light and dark mode.
- Countdown colours use the semantic status palette only, never the navy identity colour, per the brand guidelines; the countdown must remain legible in both themes and must degrade to a plain absolute datetime when JavaScript is unavailable.

## Translations

Every user-facing string is wrapped and given a French translation in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `manage.py compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`.

**Enum labels, field verbose names and template strings** that collide with an existing bare `msgid` use `pgettext_lazy("incident", ...)` in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po` :

| String | Existing bare entry | Action |
|---|---|---|
| `NotificationDecision.REQUIRED` "Required" | `django.po` -> "Requis" | `pgettext_lazy("incident", "Required")` |
| `NotificationRegime.OTHER` "Other" | `django.po` (and three more) -> "Autre" | `pgettext_lazy("incident", "Other")` |
| `NotificationChannel.EMAIL` "Email" | `django.po` -> "Email" | `pgettext_lazy("incident", "Email")` |
| "Incident" (field label and card headings) | existing bare entry | `pgettext_lazy("incident", "Incident")` |
| "Evidence" (`proof_evidence` label) | `django.po` -> "Preuves" | `{% trans "Evidence" context "incident" %}` |
| "Decision" (the decision card heading) | existing bare entry | `{% trans "Decision" context "incident" %}` |

`NotificationChannel.PHONE` reuses the existing bare "Phone" -> "Téléphone", which is correct as it stands. Every other label in this file ("Undecided", "Not required", "Portal", "Postal mail", "In person", "Public notice", "Generated", "Added manually", the five `ClockAnchor` labels, and all 22 regime and 12 recipient-kind labels) is a new, non-colliding bare `msgid`.

**Step and transition labels must never use `pgettext_lazy`.** `lifecycle_to_json()` stringifies each label with `str(...)` and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy` (`core/lifecycle.py` `lifecycle_from_json()`), so a `msgctxt` carried in code is lost after the `post_migrate` round-trip through `LifecycleDefinition` and the label resolves to whatever the bare `msgid` maps to. Three of this lifecycle's step labels collide, and all three are safe **because the existing bare French is the right word here** : "Draft" (`django.po` -> "Brouillon"), "Required" (`django.po` -> "Requis") and "Archived" (`django.po` -> "Archivé") are reused as they stand, as are the core "Archive" and "Restore" transition labels. Where an existing translation had been wrong for this context, the fix would be to **rename the step**, not to add a context : that is exactly why the `assessed` step is labelled "To decide" rather than "Assessed", and why the omission step is "Not required" rather than the already-taken "Not applicable".

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- GDPR Art. 33(1) : notification to the supervisory authority without undue delay and, where feasible, not later than 72 hours after becoming aware, **unless** the breach is unlikely to result in a risk. The omission path is this entity's `not_required` step.
- GDPR Art. 33(2) : a processor notifies the controller without undue delay - `no_fixed_deadline = True`, recipient is the controller.
- GDPR Art. 33(3)(a)-(d) : the minimum content of a notification, rendered as `content_requirements` and structured on [PersonalDataBreach](personal-data-breach.md) in phase 2.
- GDPR Art. 33(4) : information may be provided in phases - successive [NotificationFiling](notification-filing.md) rows on one obligation.
- GDPR Art. 33(5) and Art. 34(1) / 34(3) : the internal register and the communication to data subjects with its exemptions.
- NIS2 Art. 23(1), 23(3) and 23(4)(a)-(d) : recipients of the service, the significance test, and the 24 h / 72 h / on-request / one-month sequence. Art. 23(4)(d) is the reason `ClockAnchor.PREVIOUS_STAGE` and `depends_on` exist.
- DORA Art. 19 : initial, intermediate and final major ICT incident reports on the same mechanism.
- ISO/IEC 27001:2022 A.5.26 (response to information security incidents), clause 10.2 f) (retained documented information)
- [Incident](incident.md) : the parent, `awareness_at` as the legal anchor, and the triage transition that generates obligations
- [NotificationFiling](notification-filing.md) : the append-only log of actual transmissions
- [ReportingAuthority](reporting-authority.md), [ReportingObligationTemplate](reporting-obligation-template.md), [PersonalDataBreach](personal-data-breach.md) : the phase-2 catalogue and GDPR qualification record
- [IncidentResponsePlan](incident-response-plan.md) : `applicable_regimes` drives phase-1 generation
- [README.md](README.md) : module business rules, permissions, notifications, environment variables
- [governance/workflow.md](../governance/workflow.md) and [governance/lifecycle.md](../governance/lifecycle.md) : the lifecycle framework and `LifecycleEvent`

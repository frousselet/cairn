# PersonalDataBreach

`incidents.models.personal_data_breach.PersonalDataBreach`

The **GDPR qualification** of an incident and the **Art. 33(5) internal register entry**, in one record. It answers three questions that an [Incident](incident.md) deliberately does not : *is this a personal data breach at all*, *in what capacity were we processing* and *does it meet the Art. 34 high-risk threshold*. It then holds the Art. 33(3)(a)-(d) content that any filing is drafted from, and its `documented` lifecycle state **is** the register entry that Art. 33(5) requires the controller to keep of every breach, notified or not.

It is a distinct entity, with a distinct lifecycle and a distinct approver - the **DPO** - for two reasons that a boolean on the incident cannot serve:

- **The verdict must survive independently of the incident's operational state.** An incident can be contained, recovered and closed long before the qualification is settled, and a qualification can be reopened years later when a forensic finding changes what was actually exfiltrated. Tying the verdict to the incident's step would force one of those two truths to lie.
- **`controller_role` alone decides which obligations exist at all.** See below. That is not a display field; it is the input that determines whether the organisation owes a filing to a supervisory authority or a notice to a customer.

File: `incidents/models/personal_data_breach.py`

Phase **2**. `BaseModel` subclass : UUID PK, sequential `reference` (prefix **`PDBR`**, e.g. `PDBR-1`), `tags`, `version`, `created_by`, `django-simple-history` audit trail, and the dedicated **`personal_data_breach`** lifecycle. `workflow_perm_namespace` is overridden to `incidents.notification` : the default would spell `incidents.personaldatabreach`, which matches no feature in `PERMISSION_REGISTRY`, and every transition would then be refused for everyone. Phase 2 introduces **no new permission feature** (RG-INC-39) : qualifying a breach is part of the same duty of care as deciding what to notify.

Not a `ScopedModel` : it inherits the incident's scope through `scope_parent_lookup = "incident__scopes"`, so it can never drift out of alignment when the incident is re-scoped. See [Scope tenancy](#scope-tenancy).

## `controller_role` decides which obligations exist at all

This is the sharpest point in the entity, and getting it wrong is the difference between a compliant response and an unlawful one.

- A **controller** (or a **joint controller**) that suffers a personal data breach owes **GDPR Art. 33(1)** : notification to the competent supervisory authority without undue delay and, where feasible, within **72 hours** of becoming aware, unless the breach is unlikely to result in a risk to the rights and freedoms of natural persons. It may additionally owe **Art. 34(1)** : communication to the data subjects themselves, when the breach is likely to result in a **high** risk.
- A **processor** owes **neither**. It owes **Art. 33(2)** : notify **the controller** without undue delay. It has no 72-hour clock, no supervisory authority to file with, and no data subjects to communicate with. Filing with the supervisory authority as a processor is not a harmless excess of zeal : it discloses a client's breach on that client's behalf, without the client's decision, and it may pre-empt or contradict the controller's own filing.

The module therefore treats `controller_role` as a **generation input**, not as documentation. [ReportingObligationTemplate](reporting-obligation-template.md) carries a `controller_roles` list, and the GDPR templates are conditioned on it : the Art. 33(1) and Art. 34 templates list `controller` and `joint_controller`, the Art. 33(2) template lists `processor` alone. Obligation generation is re-run on the `under_qualification -> confirmed` transition precisely because that is the moment `controller_role` becomes a settled fact rather than an assumption (see [Regeneration on confirmation](#regeneration-on-confirmation)).

One organisation is frequently both, on different processing operations, and the split is **per incident**, not per organisation. A SaaS provider is a controller for its own employee data and a processor for its customers' data, and a single incident touching both is qualified through the capacity in which **the affected data** was processed. When one incident genuinely spans both capacities with materially different consequences, the honest modelling is two incidents with a `parent_incident` link, not one record trying to hold two legal positions.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `PDBR-N`, unique | Business reference. The citable identifier of the Art. 33(5) register entry. |
| `controller_role` | enum | required, default `controller` | `ControllerRole`. **Decides the obligation set** : see the section above. |
| `nature` | text | optional, blank default | Nature of the breach, GDPR Art. 33(3)(a). Mandatory to reach `confirmed`. |
| `data_categories` | JSON | optional, `default=list` | Categories of personal data concerned, Art. 33(3)(a). Same value shape as `assets.EssentialAsset.personal_data_categories`, so the two registers are comparable and a breach can be pre-filled from the affected essential assets. |
| `special_categories` | boolean | required, default `False` | Art. 9 special-category data (health, biometrics, political opinions, ...) is involved. A strong pointer towards high risk, and rendered as such in the UI : it never sets `high_risk_to_rights` automatically, because Art. 34 is a judgement and not a lookup. |
| `data_subject_categories` | JSON | optional, `default=list` | Categories of data subjects concerned (employees, customers, patients, minors, ...), Art. 33(3)(a) |
| `approximate_data_subjects` | int | optional, positive | Approximate number of data subjects concerned, Art. 33(3)(a) |
| `approximate_records` | int | optional, positive | Approximate number of personal data records concerned |
| `volume_is_estimate` | boolean | required, default `True` | Marks the two counts as provisional. Defaulting to `True` is the correct default : a 72-hour filing normally contains an estimate, and Art. 33(4) explicitly allows the information to be provided in phases. |
| `dpo_contact` | string | optional, max 255, blank default | Name and contact details of the DPO or other contact point, Art. 33(3)(b). Mandatory to reach `confirmed`. |
| `likely_consequences` | text | optional, blank default | Likely consequences of the breach, Art. 33(3)(c). Mandatory to reach `confirmed`. |
| `measures_taken` | text | optional, blank default | Measures taken or proposed, including measures to mitigate possible adverse effects, Art. 33(3)(d). Mandatory to reach `confirmed`. |
| `high_risk_to_rights` | boolean | **three-state**, `null=True, default=None` | The Art. 34(1) determination. `True` generates the data-subject communication obligation; `False` is a recorded negative verdict; `None` means *not yet determined*, and is not a match for anything. Must be non-null to reach `confirmed`. |
| `high_risk_justification` | text | optional, blank default | Reasoning behind the Art. 34 determination. Expected in both directions : a recorded "no high risk" with no reasoning is the weakest sentence in a breach file. |
| `article_34_exemption` | enum | required, default `none` | `Art34Ground` : the Art. 34(3) exemption relied on, if any. Recorded, never assumed : see [Article 34(3) exemptions](#article-343-exemptions). |
| `article_34_exemption_justification` | text | optional, blank default | Written justification for not informing data subjects. Mandatory (`clean()`) whenever `article_34_exemption != none`. |
| `cross_border_eu` | boolean | required, default `False` | Cross-border **processing** within the meaning of GDPR Art. 4(23). Distinct from `Incident.cross_border_impact`, which is operational cross-border impact and exists for NIS2 incidents with no personal data at all : see [ReportingObligationTemplate](reporting-obligation-template.md#the-two-incident-fields-this-entity-needs). |
| `register_entry_reference` | string | optional, max 100, blank default | External reference, for organisations that also keep the Art. 33(5) register outside Cairn. Recording the pointer is what keeps the two registers reconcilable. |
| `qualified_by` | relation | FK -> User, `SET_NULL`, optional | Who reached the verdict. Reverse accessor `qualified_data_breaches`. Stamped by the transition. |
| `qualified_at` | datetime | optional, **write-once** | When the verdict was reached. Stamped by the `confirm` or the `rule out` transition; never editable in a form, a serializer or an MCP writable list (RG-INC-12). |
| `workflow_state` | string | indexed, default `draft` | Lifecycle step (`personal_data_breach`) |
| `tags` | relation | M2M -> `context.Tag` | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | Timestamps |

`JSONField` is used for the three list fields rather than `ArrayField` so `core.settings_test` (SQLite in memory) runs the module unchanged.

**Write-once is enforced at application level.** `save()` refuses to change `qualified_at` once it is set, and the field is absent from every form, serializer and MCP writable list. This is a Python-level guarantee : `QuerySet.update()`, `bulk_update()`, raw SQL and a Django shell all bypass `save()`. `HistoricalRecords` therefore turns prevention into **detection** - any out-of-band change leaves a historical row - and this document says so to the auditor rather than claiming an immutability the schema does not provide.

### Relations

| Name | Type | Target | Reverse accessor | Description |
|---|---|---|---|---|
| `incident` | OneToOne, `PROTECT`, required | [Incident](incident.md) | `personal_data_breach` | Exactly one qualification record per incident. `PROTECT` : an incident with a breach record can never be deleted, which is belt and braces on top of the incident's own lifecycle delete guard (RG-INC-07). |
| `lead_authority` | FK, `SET_NULL`, optional | [ReportingAuthority](reporting-authority.md) | `lead_breaches` | The lead supervisory authority under GDPR Art. 56 (one-stop-shop). `SET_NULL` : a withdrawn one-stop-shop determination must not destroy the breach record. |
| `controller_supplier` | FK, `SET_NULL`, optional | `assets.Supplier` | `notified_data_breaches` | When the organisation acts as a **processor**, the controller it must notify under Art. 33(2). A real supplier row, so the contract, the requirements and the review history are one click away. |

### Meta

- `ordering = ["-created_at"]`
- The `OneToOneField` supplies the uniqueness of one record per incident; no additional constraint is needed.
- `CheckConstraint pdbr_exemption_has_justification` : `Q(article_34_exemption="none") | ~Q(article_34_exemption_justification="")`

The check constraint is the database half of the Art. 34(3) rule : the transition gate refuses the verdict and the constraint refuses the row, so neither a raw SQL insert nor a `QuerySet.update()` can leave an exemption asserted with no written justification.

## Enumerations

### ControllerRole

Declared in `incidents/constants.py` and referenced by [ReportingObligationTemplate](reporting-obligation-template.md) `.controller_roles`.

| Value | Label |
|---|---|
| `controller` | Controller |
| `joint_controller` | Joint controller |
| `processor` | Processor |

### Art34Ground

| Value | Label |
|---|---|
| `none` | None |
| `encryption` | Art. 34(3)(a) encryption |
| `subsequent_measures` | Art. 34(3)(b) subsequent measures |
| `disproportionate_effort` | Art. 34(3)(c) disproportionate effort |

## Lifecycle

`LIFECYCLE_NAME = "personal_data_breach"`, `layout="graph"`, generated by `lifecycle_from_state_flags()` in `incidents/lifecycles.py` from the state and transition constants in `incidents/constants.py`, and registered from `IncidentsConfig.ready()`.

> `incidents/apps.py` **must** define `ready()` and import `incidents.lifecycles`. Omitting it fails **silently** : `lifecycle_name_for()` (`core/lifecycle.py` `lifecycle_name_for()`) tests `if name and name in LIFECYCLE_REGISTRY`, so an unregistered name quietly downgrades the model to the core `default` 4-state lifecycle - in tests as well as in production - and every gate below would then be attached to steps that no longer exist. A test asserts `PersonalDataBreach.get_lifecycle().name == "personal_data_breach"` so the omission fails loudly.

### Steps

| Code | Label | StepKind | In reports | Linkable | Deletable | Tone | Meaning |
|---|---|---|---|---|---|---|---|
| `draft` | Draft | `DRAFT` | no | no | **yes** | `neutral` | The row exists for a few milliseconds during auto-creation, and permanently only for a record created by hand and abandoned. Deletable, as is `under_qualification`. |
| `under_qualification` | Qualification in progress | `INTERMEDIATE` | no | no | **yes** | `warning` | The GDPR verdict is being formed. **Not** counted in reports : an unqualified suspicion is not a breach, and counting it would inflate the Art. 33(5) register with events that turned out to be nothing. |
| `confirmed` | Confirmed breach | `INTERMEDIATE` | **yes** | **yes** | no | `danger` | It is a personal data breach. The full Art. 33(3)(a)-(d) content is present and the Art. 34 verdict is recorded. |
| `documented` | Documented (Art. 33(5)) | `INTERMEDIATE` | **yes** | **yes** | no | `success` | The internal register entry is complete : facts, effects, remedial action taken. **This step is the Art. 33(5) evidence.** |
| `not_a_breach` | Not a personal data breach | `ARCHIVED` (terminal) | no | no | no | `muted` | Ruled out by a named person, with a mandatory comment. **This is the step an inspector asks to see** when the incident register says personal data was involved and no filing was made. |
| `archived` | Archived | `ARCHIVED` | no | no | no | `muted` | The generic exit, declared **explicitly** |

### Transitions

`permission_action` is appended to `workflow_perm_namespace` (`incidents.notification`).

| Verb | Transition | `permission_action` | `requires_comment` | Side effects |
|---|---|---|---|---|
| Open qualification | `draft -> under_qualification` | `update` | no | Hand-declared, not auto-wired. Performed by the incident's triage with `enforce_permission=False`. |
| Confirm breach | `under_qualification -> confirmed` | **`approve`** | **yes** | Stamps `qualified_by` and `qualified_at`; re-runs obligation generation with the now-known `controller_role` and Art. 34 verdict |
| Rule out | `under_qualification -> not_a_breach` | **`approve`** | **yes** | Stamps `qualified_by` and `qualified_at`; the comment is the recorded reason |
| Complete the Art. 33(5) record | `confirmed -> documented` | **`approve`** | no | The register entry is declared complete |
| Reopen qualification | `confirmed -> under_qualification` | **`approve`** | **yes** | New facts changed the verdict; the original confirmation stays in the lifecycle history |
| Reopen | `documented -> confirmed` | **`approve`** | **yes** | The register entry needs amending |
| Reopen a ruled-out qualification | `not_a_breach -> under_qualification` | **`approve`** | **yes** | New facts contradict the exclusion. Mirrors `discarded -> under_assessment` on [SecurityEvent](security-event.md). The original exclusion and its reason stay in the lifecycle history : re-qualifying is an added act, never an erasure. |
| Archive | `* -> archived` | **`approve`** | **yes** | Hand-declared, not auto-wired |
| Restore | `archived -> draft` | **`approve`** | no | Hand-declared, and additionally refused by the `transition_to()` override for any record that has ever left `draft` |

> **Both bookend edges are hand-declared, and so is `draft -> under_qualification`.** `lifecycle_from_state_flags()` auto-wires `draft -> <initial step>`, `ANY -> archived` and `archived -> draft` **only when the corresponding step is absent** from the state-flag list (`core/lifecycle.py` `lifecycle_from_state_flags()`). This lifecycle declares `draft` and `archived` **explicitly**, precisely so that nothing is auto-wired : the auto-wired archive and restore edges carry **no `permission_action` and no `requires_comment`**, and `user_can_perform()` (`core/lifecycle.py` `user_can_perform()`) allows any transition whose `permission_action` is empty. Left generated, they would give any holder of the transition endpoint an `archive -> restore -> delete` path out of an `under_qualification` record - which is `deletable=True` - and the GDPR qualification of an incident would be destroyable by anyone with `incidents.notification.update`. All three edges are therefore listed in `PERSONAL_DATA_BREACH_TRANSITIONS` with explicit actions, and the restore edge is refused outright by the model override for any record with a `core.LifecycleEvent` history beyond `draft`.

### Transition gates

Per RG-INC-08, every gate below lives in a `transition_to()` override on `PersonalDataBreach`, **never** in `Transition.form_class`, `allowed_roles` or `allowed_users`. `lifecycle_to_json()` (`core/lifecycle.py` `lifecycle_to_json()`) omits those three fields by design, `lifecycle_from_json()` rebuilds transitions without them, and `get_lifecycle()` prefers the `post_migrate`-seeded `LifecycleDefinition` row over the code default - so a gate declared that way is silently dead on every migrated database. All three write surfaces (`core/workflow_views.py` `WorkflowTransitionView.post()`, `accounts/api/mixins.py` `_lifecycle_transition()`, `mcp/tools.py` `_transition_handler()`) funnel through `BaseModel.transition_to()`, so the model override is the one place that binds web, API and MCP at once.

| Gate | Transition | Refused unless |
|---|---|---|
| **G-01 Art. 33(3) completeness** (RG-INC-41) | `under_qualification -> confirmed` | `nature`, `dpo_contact`, `likely_consequences` and `measures_taken` are all non-blank, i.e. the full Art. 33(3)(a)-(d) set. A confirmed breach with an empty *likely consequences* is a filing that cannot be drafted. |
| **G-02 Art. 34 verdict** | `under_qualification -> confirmed` | `high_risk_to_rights` is **not null**. `None` is not a verdict; the DPO is made to say yes or no, in writing. |
| **G-03 Named qualification** | `under_qualification -> confirmed`, `under_qualification -> not_a_breach` | The actor holds `incidents.notification.approve` and supplies a comment. Both directions are approver-gated : ruling a breach **out** is the more consequential of the two, and it is exactly the decision an inspector asks about. |
| **G-04 Exemption justification** | `under_qualification -> confirmed` | `article_34_exemption_justification` is non-blank whenever `article_34_exemption != none`. Also a DB `CheckConstraint`. |
| **G-05 Write-once stamps** (RG-INC-12) | all | `qualified_at` is stamped by the override, never by a form, a serializer or an MCP field, and never re-stamped by a reopen. |
| **G-06 No restore of a qualified record** | `archived -> draft` | The record has never left `draft`. A record that reached `under_qualification` or beyond can be archived, but never restored into a deletable step. |

### Creation and the initial step

**`PersonalDataBreach` is not created in `under_qualification`. It is created, and then transitioned there.**

`BaseModel.save()` calls `_ensure_initial_step()` (`context/models/base.py` `BaseModel._ensure_initial_step()`), and `Lifecycle.initial_step` (`core/lifecycle.py` `Lifecycle.initial_step`) returns the single `StepKind.DRAFT` step. Every insert therefore lands in `draft`, whatever the caller intended. The incident's triage creates the record and moves it in the same atomic block:

```python
with transaction.atomic():
    breach = PersonalDataBreach(incident=incident, controller_role=...)
    breach.save()
    breach.transition_to("under_qualification", user, enforce_permission=False)
```

Assigning `workflow_state="under_qualification"` at insert would stick, because `_ensure_initial_step()` only snaps a blank or unknown value, but it would leave **no `core.LifecycleEvent` row**, so the register would hold a qualification nobody is recorded as having opened. And leaving the record in `draft` is worse still : `draft` is `deletable=True`, the record would not appear in the *Awaiting qualification* bucket the DPO works from, and the GDPR qualification of a real incident would be invisible until someone thought to look for it.

A test asserts that the triage path yields a record in `under_qualification`, and a second test asserts that a bare `PersonalDataBreach.objects.create(...)` does **not**.

## Creation and ruling out

The record is created automatically when [Incident](incident.md) `.personal_data_involved` is set to `True` and no record exists yet : at triage (RG-INC-18), and again on any later save that flips the flag on.

**Clearing `personal_data_involved` never deletes the record.** This is the rule the whole entity turns on. A breach is ruled out through the **`not_a_breach`** transition : by a named person, holding `incidents.notification.approve`, with a mandatory comment, at a stamped time, leaving an immutable `core.LifecycleEvent`. Unchecking a box leaves nothing at all, and "we considered it and concluded it was not a personal data breach" is precisely the sentence a supervisory authority asks to see when it notices an incident involving personal data that was never notified.

Concretely:

- Setting `personal_data_involved = True` creates the record (in `draft`, then transitioned to `under_qualification`) if none exists, and does nothing if one already does - including one already in `not_a_breach`. Re-opening a ruled-out qualification is a deliberate `not_a_breach -> under_qualification` act, not a side effect of a checkbox.
- Setting `personal_data_involved = False` leaves the record exactly where it is. The incident detail page then shows the qualification card with a plain warning : *the incident no longer declares personal data, and the qualification record is still open*. The operator resolves the contradiction through the lifecycle, in one direction or the other.
- The record is deletable only in `draft`, which in practice means only a record created by hand and immediately abandoned.

## Regeneration on confirmation

The `under_qualification -> confirmed` transition re-runs obligation generation ([ReportingObligationTemplate](reporting-obligation-template.md#when-generation-runs)) inside its own atomic block, because two of the template conditions can only now be evaluated:

- `controller_roles` can finally be matched against a settled `controller_role`. This is what makes the Art. 33(1) obligation appear for a controller and the Art. 33(2) obligation appear for a processor - and what stops both appearing for either.
- `requires_high_risk` can finally be matched against a non-null `high_risk_to_rights`. `True` generates the Art. 34 data-subject communication obligation.

Generation is idempotent : obligations already created at triage are found by an explicit lookup on `(incident, regime, recipient)` and left untouched, snapshot included, and an obligation that has already left `assessed` is never revisited. A confirmation that produces new obligations therefore adds rows to the *To decide* bucket without disturbing a decision already taken.

The reverse never happens : **confirming a breach never removes an obligation**. If triage generated an Art. 33(1) obligation and the qualification later establishes that the organisation was a processor, the obligation is closed through its own `not_required` decision, with the qualification cited as the mandatory rationale (RG-INC-25). An obligation that was once believed to exist and is later found not to leaves a recorded decision, never a gap.

## Article 34(3) exemptions

Art. 34(3) lets a controller skip communicating to data subjects when the data was rendered unintelligible by encryption (a), when subsequent measures have removed the high risk (b), or when the communication would involve disproportionate effort (c).

The module records the exemption. It does **not** let the exemption suppress the obligation. The Art. 34 obligation is still generated, and is closed through its own `not_required` transition with `article_34_exemption` and `article_34_exemption_justification` as the mandatory rationale (RG-INC-25). An exemption that is written down, approved and timestamped is audit evidence; an exemption that quietly prevents a row from ever existing is an absence nobody can review, and it is indistinguishable from having forgotten.

One consequence is worth stating explicitly : **`disproportionate_effort` does not remove the duty.** Art. 34(3)(c) replaces individual communication with a public communication or a similar measure of equivalent effectiveness, so relying on that ground **additionally** generates a `public_communication` obligation rather than closing the matter.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-12 | `qualified_at` and `qualified_by` are stamped by the `transition_to()` override only : excluded from every `ModelForm`, `read_only` in every serializer, absent from every MCP writable list. Write-once is prevented at application level and **detected** through `HistoricalRecords`; `QuerySet.update()` and raw SQL bypass `save()`. |
| RG-INC-18 | `personal_data_involved = True` forces the `gdpr_art33_authority` obligation at triage regardless of the plan's configured regimes, and creates the `PersonalDataBreach` record : **saved, then transitioned to `under_qualification`** in the same atomic block. Clearing the flag never deletes that record; a breach is ruled out through the `not_a_breach` transition, never by unchecking a box. |
| RG-INC-41 | Confirming a breach requires the full Art. 33(3)(a)-(d) set (`nature`, `dpo_contact`, `likely_consequences`, `measures_taken`) and a non-null `high_risk_to_rights`, plus `incidents.notification.approve` and a mandatory comment. |
| RG-INC-25 | An obligation whose decision is `not_required` carries a non-blank rationale, is approver-gated and is comment-bearing. An Art. 34(3) exemption is discharged through that path, never by suppressing the obligation. |
| RG-INC-30 | Obligations generated on confirmation snapshot their legal terms from the [template](reporting-obligation-template.md) at creation; a later template edit never rewrites them. Generation only considers templates and authorities in a `reportable()` state. |
| RG-INC-37 | Every report, KPI, calendar feed, kanban bucket and picker filters through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. No `personal_data_breach` state literal appears outside `incidents/constants.py`. |
| RG-INC-38 | `PersonalDataBreach` is **not** independently scoped : it inherits the incident's scope through `scope_parent_lookup = "incident__scopes"`. See [Scope tenancy](#scope-tenancy). |
| RG-INC-39 | The entity introduces **no** new permission feature : it is gated by `incidents.notification.*`, alongside the obligations its verdict drives. |

## Scope tenancy

`PersonalDataBreach` carries no `scopes` of its own and declares `scope_parent_lookup = "incident__scopes"`. That is the right model : a qualification record that could be scoped differently from its incident would be a way to make a breach visible to people the incident is not, and re-scoping the incident would silently leave it behind.

**This inheritance is not enforced today on three call sites, and phase 1 extends them.** This is a security fix, logged under a `### Security` entry in `CHANGELOG.md`:

| Call site | Current behaviour | Required change |
|---|---|---|
| `mcp/tools.py` `_filter_by_scopes` | Handles `context.Scope`, then a `scopes` M2M, then `return qs` **unfiltered** | Accept `model` / `parent_lookup`, and thread a `scope_parent_lookup` argument through `_register_crud` / `_list_handler` / `_get_handler` / `_transition_handler` / `_allowed_transitions_handler`. Without it, `list_personal_data_breaches` returns every breach qualification on the instance - approximate data-subject counts, special-category flags, DPO contact - to any holder of `incidents.notification.read`. |
| `core/workflow_views.py` `WorkflowTransitionView` | Guards with `if allowed_scopes is not None and hasattr(obj, "scopes")` | Honour a model-level `scope_parent_lookup` attribute. Without it, the `confirm` and `not_a_breach` verdicts are performable cross-scope. |
| `core/history_views.py` `HistoryPartialView` | The same `hasattr(obj, "scopes")` guard | The same change. Without it, the full qualification history of an out-of-scope breach is readable. |

This is core work in the phase-1 PR, not a phase-2 detail : the two generic web endpoints are shared by every module, and this entity's data is among the most sensitive in the platform.

## Endpoints

### REST

- `GET /api/v1/incidents/personal-data-breaches/` : list, filtered by `PersonalDataBreachFilter` (`incident_id`, `status`, `controller_role`, `high_risk_to_rights`, `special_categories`, `article_34_exemption`, `lead_authority_id`)
- `POST /api/v1/incidents/personal-data-breaches/` and `POST /api/v1/incidents/personal-data-breaches/batch/` (max 100 items, non-atomic, per-item `{index, status, id, reference}`)
- `GET/PUT/PATCH/DELETE /api/v1/incidents/personal-data-breaches/<uuid>/`
- `GET/POST /api/v1/incidents/personal-data-breaches/<uuid>/transition/` : `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`, so every gate above applies identically to an API caller
- `GET /api/v1/incidents/personal-data-breaches/<uuid>/history/` : `core.history.build_timeline`

`PersonalDataBreachSerializer` / `PersonalDataBreachListSerializer`, with `read_only_fields` covering `id`, `reference`, `created_by`, `created_at`, `updated_at`, `version`, `qualified_at` and `qualified_by`. `status` is exposed as `CharField(source="workflow_state", read_only=True)`; `incident_reference`, `lead_authority_name` and `controller_supplier_name` are read-only property-backed display fields. The viewset stacks `BatchCreateMixin`, `ScopeFilterAPIMixin` (with `scope_parent_lookup = "incident__scopes"`), `LifecycleAPIMixin`, `HistoryAPIMixin`, `CreatedByMixin` and `viewsets.ModelViewSet`, uses `ModulePermission` plus the module's `_IncidentViewSet` base (`permission_module = "incidents"`, `custom_action_map = {"transition": "update"}`), and sets `permission_feature = "notification"`.

The list serializer omits `nature`, `likely_consequences`, `measures_taken`, `data_categories` and `data_subject_categories` : an index does not need the narrative content of a breach, and a smaller list payload is a smaller accidental disclosure.

### MCP

- `_register_crud(server, "personal_data_breach", PersonalDataBreach, "incidents.notification", scope_parent_lookup="incident__scopes", ...)` generates `list_personal_data_breaches`, `get_personal_data_breach`, `create_personal_data_breach`, `batch_create_personal_data_breaches`, `update_personal_data_breach`, `delete_personal_data_breach`, `transition_personal_data_breach`, `personal_data_breach_allowed_transitions`, `get_personal_data_breach_history`.
- Filters : `incident_id`, `status`, `controller_role`, `high_risk_to_rights`, `special_categories`.
- `controller_role`, `article_34_exemption` and the two JSON list fields each get an explicit `enum` entry in `field_overrides`; `incident_id`, `lead_authority_id` and `controller_supplier_id` carry descriptions naming their lookup tools (`Use list_incidents to get valid IDs`, `Use list_reporting_authorities to get valid IDs`, `Use list_suppliers to get valid IDs`).
- `qualified_at` and `qualified_by` are absent from `writable_fields` : the verdict is a transition, never a field write.
- The `scope_parent_lookup` argument depends on the `_filter_by_scopes` fix described above. **Until that fix lands, these tools must not be registered**, because an unfiltered `list_personal_data_breaches` is a cross-tenant disclosure of breach content.

`mcp/tools.py` `HELP_TEXT` gains `PersonalDataBreach=PDBR` in the reference-prefix block, and the `TOPIC_INCIDENTS` help topic gains a section for this entity.

## Permissions

| Codename | Description |
|---|---|
| `incidents.notification.read` | Read a breach qualification and the Art. 33(5) register |
| `incidents.notification.create` | Create a qualification record by hand (the normal path is automatic) |
| `incidents.notification.update` | Fill in the Art. 33(3) content, open the qualification |
| `incidents.notification.approve` | **Confirm** a breach, **rule one out**, complete or reopen the Art. 33(5) record, archive |
| `incidents.notification.delete` | Delete a `draft` record |

Under the six `SYSTEM_GROUPS` suffix filters, the **DPO** group holds read / create / update / approve, which is exactly the set this entity needs : the qualification verdict is the DPO's to make, and the approve action is what makes that accountability real rather than nominal. Contributeur holds read / create / update and can therefore prepare the Art. 33(3) content but never pronounce the verdict.

## UI

- **Where it lives** : the qualification is reached from the [Incident](incident.md) detail page, as a dedicated *Personal data* card in the left column, and has its own detail page for the DPO's own working view. There is no top-level "breaches" navigation entry : a breach is always a qualification **of** an incident, and a separate register would invite the two to drift.
- **Incident card** : `{% workflow_badge %}`, `controller_role` rendered in words (*We acted as processor : Art. 33(2) to the controller, not Art. 33(1) to the authority*), the Art. 34 verdict, the approximate counts with the *estimate* qualifier, and a direct link to the qualification page. When `personal_data_involved` is `False` and the record is still open, the card carries the plain warning described under [Creation and ruling out](#creation-and-ruling-out).
- **Detail** (`/incidents/personal-data-breaches/<uuid>/`) : strict 2-column card layout, no nav-tabs. Left column : *Qualification* (`controller_role` with its consequence spelled out, `cross_border_eu`, `lead_authority`, `controller_supplier`); *Art. 33(3) content* (nature, data categories, data-subject categories, counts with `volume_is_estimate`, DPO contact, likely consequences, measures taken - in article order, each labelled with its article letter, because that is the order the filing form asks for); *Art. 34 determination* (`high_risk_to_rights` with its justification, the exemption ground and its justification); *Generated obligations* (the [IncidentNotification](incident-notification.md) rows this verdict produced, with their deadlines). Right column, sticky : the stepper, `qualified_by` / `qualified_at`, `register_entry_reference`, tags, and the history trigger.
- **Stepper** : `{% include "includes/lifecycle_stepper.html" %}` fed by `LifecycleStepperMixin`, never a status select and never plain buttons. This lifecycle has **two** `StepKind.ARCHIVED` steps (`not_a_breach`, `archived`), so the dagre renderer draws two detached exits : lighter than the incident and security-event graphs, but still checked at desktop and mobile widths in **both** light and dark mode.
- **`special_categories` is rendered as a warning, not as a verdict.** Art. 9 data is a strong pointer to high risk and the UI says so, but the `high_risk_to_rights` control stays a deliberate three-state choice the DPO makes. Auto-ticking it would replace a judgement with a lookup and would put words in the DPO's mouth in a document a supervisory authority reads.
- Create and update use `HtmxFormMixin` drawer modals, with mobile-first care on the two multi-select category widgets.

## Translations

Several of this entity's labels collide with `msgid`s already present in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`.

**Enum labels, field verbose names and template strings** use `pgettext_lazy("incident", ...)` in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po`:

| String | Existing bare entry | Action |
|---|---|---|
| `Art34Ground.NONE` "None" | `django.po` -> "Aucun" | `pgettext_lazy("incident", "None")` |
| "Confirmed" (the *Confirmed* filter label on the qualification list) | `django.po` -> "Confirmé" | `{% trans "Confirmed" context "incident" %}` |
| "Required" (the *Required* obligation badge on the generated-obligations card) | `django.po` -> "Requis" | `{% trans "Required" context "incident" %}` |
| "Incident" (the incident link label on the qualification page) | `django.po` -> "Incident" | `{% trans "Incident" context "incident" %}` |

The three `ControllerRole` labels ("Controller", "Joint controller", "Processor") and every other field label on this entity ("Nature", "Data categories", "Special categories", "Data subject categories", "Approximate data subjects", "Approximate records", "DPO contact", "Likely consequences", "Measures taken", "High risk to rights and freedoms", "Article 34 exemption", "Cross-border processing", "Register entry reference") are new, non-colliding bare `msgid`s.

**Step and transition labels must never use `pgettext_lazy`.** `lifecycle_to_json()` stringifies each label with `str(...)` and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy` (`core/lifecycle.py` `lifecycle_from_json()`), so a `msgctxt` carried in code is lost after the `post_migrate` DB round-trip and the label then resolves to whatever the bare `msgid` maps to. This lifecycle is safe as declared, and deliberately so : "Draft" (`django.po` -> "Brouillon") and "Archived" (`django.po` -> "Archivé") are **reused** from the core bookend steps with the correct French, "Archive" and "Restore" are the existing core transition labels, and the `confirmed` step is labelled **"Confirmed breach"**, not "Confirmed" - which is exactly what keeps it clear of the `django.po` collision that the filter label above has to solve with a `msgctxt`. Every remaining label ("Qualification in progress", "Documented (Art. 33(5))", "Not a personal data breach", "Open qualification", "Confirm breach", "Rule out", "Complete the Art. 33(5) record", "Reopen qualification", "Reopen") is a new, non-colliding bare `msgid`.

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- GDPR Art. 4(12) (definition of a personal data breach) and Art. 4(23) (cross-border processing)
- GDPR Art. 33(1) (controller notifies the supervisory authority within 72 hours), Art. 33(2) (**processor notifies the controller**), Art. 33(3)(a)-(d) (minimum content), Art. 33(4) (phased provision), **Art. 33(5) (internal documentation of every breach)**
- GDPR Art. 34(1) (communication to data subjects) and Art. 34(3)(a)-(c) (exemptions)
- GDPR Art. 9 (special categories of personal data), Art. 28 (processor obligations), Art. 56 (lead supervisory authority)
- EDPB Guidelines 9/2022 on personal data breach notification under GDPR
- [Incident](incident.md) : the `personal_data_involved` flag that creates this record, and `awareness_at`, the anchor every GDPR deadline derives from
- [IncidentNotification](incident-notification.md) : the obligations this verdict generates, and the `not_required` decision an exemption is discharged through
- [ReportingObligationTemplate](reporting-obligation-template.md) : `controller_roles` and `requires_high_risk`, the two conditions this record supplies
- [ReportingAuthority](reporting-authority.md) : `lead_authority` under Art. 56
- [Supplier](../m2-assets/supplier.md) : `controller_supplier`, the controller notified under Art. 33(2)
- [README.md](README.md) : module business rules, permissions, notifications
- [governance/workflow.md](../governance/workflow.md) : the lifecycle framework this workflow plugs into

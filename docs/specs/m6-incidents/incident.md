# Incident

`incidents.models.incident.Incident`

The information security incident record : the ISO/IEC 27001:2022 **A.5.26 (response to information security incidents)** file, and the anchor every other entity in the module hangs off. An incident is reached either by promoting a [SecurityEvent](security-event.md) through its A.5.25 assessment, or by a direct declaration recorded with a detection source and a named declarer. It carries the impact picture, the process clock stamps every ISO/IEC 27035 KPI is computed from, the **legal awareness anchor** every statutory deadline derives from, and the blast-radius links into the asset, supplier, risk and compliance registers.

File: `incidents/models/incident.py`

`ScopedModel` subclass : UUID PK, sequential `reference` (prefix **`INCD`**, e.g. `INCD-1`), `scopes` M2M, `tags`, `version`, `created_by`, `django-simple-history` audit trail, and the dedicated **`incident`** lifecycle. `workflow_perm_namespace` is *not* overridden : `app_label.model_name` already spells `incidents.incident`, which is the permission feature.

> The reference prefix `INCD` is one letter-order away from `INDC` ([Indicator](../m1-context/indicator.md)). They are visually confusable in a reference string and in the MCP help block; never copy a neighbouring `HELP_TEXT` line when adding the incidents entries.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `INCD-N`, unique | Business reference |
| `scopes` | relation | M2M -> `context.Scope` | ISMS scopes the incident belongs to. Drives tenancy for the incident and, through `scope_parent_lookup`, for every child row. |
| `title` | string | required, max 255 | Incident title |
| `summary` | text | optional, blank default | One-paragraph executive summary. What management review and any external statement are drafted from. |
| `description` | text | optional, HTML | Full narrative of the incident |
| `category` | enum | required, default `other` | `risks.constants.ThreatCategory` (23 values), reused verbatim : an incident is a threat that materialised. A parallel taxonomy would drift within one release and break the incident -> threat -> risk chain. |
| `severity` | enum | required, default `medium` | `context.constants.Criticality` : `low`, `medium`, `high`, `critical`. The scale assets and suppliers already share; no `IncidentSeverity` enum is created. Interpreted through the response plan's `classification_scale`. |
| `initial_severity` | enum | optional, blank default, **write-once** | `context.constants.Criticality`. Stamped at triage by the `transition_to()` override and write-once afterwards (prevention at application level, detection via `HistoricalRecords`), so severity drift is auditable by comparing two columns instead of by reading history diffs. |
| `detection_source` | enum | required, default `other` | `DetectionSource` (shared with [SecurityEvent](security-event.md)). Copied from the promoting event. |
| `is_exercise` | boolean | required, default `False`, indexed | Simulation or tabletop exercise run through the real process. See [Exercises](#exercises-is_exercise). |
| `tlp` | enum | required, default `amber` | `TrafficLightProtocol` handling caveat for the incident file and its evidence |
| `confidentiality_impact` | boolean | required, default `False` | Confidentiality was impacted. Mirrors `risks.Risk.impact_confidentiality` so incident and risk impact read the same way in reports. |
| `integrity_impact` | boolean | required, default `False` | Integrity was impacted |
| `availability_impact` | boolean | required, default `False` | Availability was impacted |
| `personal_data_involved` | boolean | required, default `False`, indexed | Personal data was or may have been affected. Forces the `gdpr_art33_authority` obligation to be instantiated at triage regardless of the plan's configuration (RG-INC-18). Deliberately the **only** personal-data field in phase 1 : the GDPR Art. 33(3) structured content lands on `PersonalDataBreach` in phase 2, so no field is migrated between phases. |
| `occurred_at` | datetime | optional | Best estimate of when the incident began |
| `detected_at` | datetime | required, indexed | Technical detection timestamp. Base of mean-time-to-detect. **Not** the legal clock. `CheckConstraint incident_detected_after_occurred` : `detected_at >= occurred_at` when both are known. |
| `awareness_at` | datetime | optional, indexed | **The** legal clock anchor. Defaults to `detected_at` on first save; must be `>= detected_at`. See [The two clocks](#the-two-clocks). |
| `awareness_justification` | text | optional, blank default | Written justification for a gap between technical detection and legal awareness. Mandatory (`clean()` + the triage gate) whenever `awareness_at > detected_at`. |
| `declared_at` | datetime | optional, **write-once** | Stamped by the `draft -> detected` transition. When the record was formally declared an incident. |
| `triaged_at` | datetime | optional, **write-once** | Stamped by `detected -> triaged`. A.5.25 assessment and decision complete. |
| `contained_at` | datetime | optional, **write-once** | Stamped on entry to `contained` |
| `eradicated_at` | datetime | optional, **write-once** | Stamped on entry to `eradicated` |
| `recovered_at` | datetime | optional, **write-once** | Stamped on entry to `recovered`; cleared by the `recovered -> investigating` reopen |
| `closed_at` | datetime | optional, **write-once** | Stamped on entry to `closed`; cleared by the `closed -> investigating` reopen and re-stamped on re-closure |
| `outage_duration` | duration | optional | Measured service interruption. **The first `DurationField` in the codebase** : Django renders it as `[DD] [HH:[MM:]]ss[.uuuuuu]` and SQLite stores it as microseconds, so the form widget, the serializer representation and the MCP argument all need an explicit test. Reported alongside each affected essential asset's declared objectives verbatim; no automated breach claim is made (RG-INC-33). |
| `estimated_cost` | decimal(12,2) | optional | Estimated financial impact. Same shape as `ComplianceActionPlan.cost_estimate`. |
| `no_obligation_justification` | text | optional, blank default | Why nothing is owed to anyone. Mandatory at the end of triage when zero notification obligations were instantiated, `personal_data_involved` is `False` **and** `is_exercise` is `False` (RG-INC-19). A missing regime configuration must never read as compliance on a green dashboard. |
| `is_significant` | boolean | **PHASE 2**, three-state, `null=True, default=None` | NIS2 Art. 23(3) significance verdict, deliberately separate from `severity` because the two are different judgements |
| `significance_determined_at` | datetime | **PHASE 2**, optional | When significance was determined. Usable as a `ClockAnchor`. |
| `significance_justification` | text | **PHASE 2**, optional, blank default | Reasoning behind the significance verdict |
| `cross_border_impact` | boolean | **PHASE 2**, three-state, `null=True, default=None` | Whether the incident affects entities or users in more than one Member State. Feeds `ReportingObligationTemplate.requires_cross_border` and gate G-03. Not the same concept as [PersonalDataBreach](personal-data-breach.md) `cross_border_eu`, which is GDPR Art. 4(23) cross-border *processing* : an incident with no personal data at all can still be cross-border for NIS2. |
| `cross_border_justification` | text | **PHASE 2**, optional, blank default, mandatory once `cross_border_impact` is non-null | Reasoning behind the cross-border verdict |
| `suspected_malicious` | boolean | **PHASE 2**, three-state, `null=True, default=None` | Whether the incident is suspected of being caused by an unlawful or malicious act. NIS2 Art. 23(4)(a) requires the 24 hour early warning to state this, so the obligation cannot be completed while it is null. |
| `suspected_malicious_justification` | text | **PHASE 2**, optional, blank default, mandatory once `suspected_malicious` is non-null | Reasoning behind the malicious-act verdict |
| `workflow_state` | string | indexed, default `draft` | Lifecycle step (`incident`). Never written directly : see [Lifecycle](#lifecycle). |
| `tags` | relation | M2M -> `context.Tag` | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | Timestamps |

### Relations

| Name | Type | Target | Reverse accessor | Description |
|---|---|---|---|---|
| `response_plan` | FK, `PROTECT`, optional | [IncidentResponsePlan](incident-response-plan.md) | `incidents` | The procedure version this incident was handled under. `PROTECT` is what makes a two-year-old incident file readable at audit time (clause 7.5.3). |
| `reporter` | FK -> User, `SET_NULL`, optional | User | `reported_incidents` | Who reported it |
| `incident_manager` | FK -> User, `SET_NULL`, optional | User | `managed_incidents` | The single accountable responder (A.5.24). Required to reach `triaged`. |
| `parent_incident` | FK -> self, `SET_NULL`, optional | Incident | `child_incidents` | Major incident composed of sub-incidents, or merge target |
| `origin_supplier` | FK, `SET_NULL`, optional | `assets.Supplier` | `originated_incidents` | The third party whose breach or outage **caused** this. A sub-processor is itself a `Supplier` row via `SupplierSubprocessor.subprocessor`, so nth-party origin needs no extra field. |
| `affected_suppliers` | M2M | `assets.Supplier` | `incidents` | Suppliers impacted or notified downstream. The causal direction matters for NIS2 / DORA third-party reporting and GDPR Art. 28. |
| `affected_essential_assets` | M2M | `assets.EssentialAsset` | `incidents` | Name copied verbatim from `risks.Risk` |
| `affected_support_assets` | M2M | `assets.SupportAsset` | `incidents` | |
| `affected_sites` | M2M | `context.Site` | `incidents` | Sites live in `context`, not `assets` |
| `affected_activities` | M2M | `context.Activity` | `incidents` | For a halted business activity with no named asset |
| `threats` | M2M | `risks.Threat` | `incidents` | The threat that materialised |
| `exploited_vulnerabilities` | M2M | `risks.Vulnerability` | `incidents` | |
| `realised_risks` | M2M | `risks.Risk` | `incidents` | Which registered risks actually materialised. Fills the reserved `# linked_incidents = ...` placeholder at `risks/models/risk.py` `Risk`, which the phase-1 migration deletes. |
| `linked_requirements` | M2M | `compliance.Requirement` | `linked_incidents` | The controls in play |

Reverse accessors on `Incident` : `source_events` ([SecurityEvent](security-event.md)), `timeline_entries`, `response_actions`, `evidence_items`, `notifications`, `post_incident_review` (OneToOne), `findings` (`compliance.Finding.incident`), `personal_data_breach` (phase 2).

> `incident.findings` and `user.findings` are two different reverse accessors on the same model (`compliance.Finding` already declares `findings` on `ComplianceAssessment`, on `User` and on `Requirement`). Legal, but never write `obj.findings` in shared code without naming the model it hangs off.

### Meta

- `ordering = ["-detected_at"]`
- Indexes on `(workflow_state, severity)`, `(severity, detected_at)`, `(awareness_at,)`
- `CheckConstraint incident_detected_after_occurred`

## Enumerations

### TrafficLightProtocol

| Value | Label |
|---|---|
| `clear` | TLP:CLEAR |
| `green` | TLP:GREEN |
| `amber` | TLP:AMBER |
| `amber_strict` | TLP:AMBER+STRICT |
| `red` | TLP:RED |

`severity` reuses `context.constants.Criticality` (`low`, `medium`, `high`, `critical`), `category` reuses `risks.constants.ThreatCategory` (23 values), and `detection_source` reuses the module's `DetectionSource`, declared once in `incidents/constants.py` and documented in [SecurityEvent](security-event.md#enumerations).

## The two clocks

The module keeps the technical clock (`detected_at`) and the legal clock (`awareness_at`) apart, and this separation is the single most consequential modelling decision in the entity.

- **`detected_at`** is when a control, a person or a tool saw something. It is the base of the mean-time-to-detect indicator and of the A.6.8 reporting-delay measurement. It has no legal meaning.
- **`awareness_at`** is the point at which the organisation *became aware* within the meaning of **GDPR Art. 33(1)** and **NIS2 Art. 23**. Every statutory deadline in the module derives from this field and from no other. Anchoring a 72-hour clock to technical detection is legally wrong and is the first thing a supervisory-authority inspector attacks.

Rules :

1. On first save, a blank `awareness_at` is set to `detected_at`. The common case is therefore correct with no operator action.
2. `awareness_at >= detected_at` is enforced in `clean()`. Becoming legally aware *before* the technical detection that produced the record is incoherent.
3. Whenever `awareness_at > detected_at`, a non-blank `awareness_justification` is mandatory, in `clean()` and again as a precondition of the `detected -> triaged` transition (RG-INC-13, RG-INC-11). A gap between detection and awareness is defensible - an alert sat unread in a queue over a weekend, a supplier notification arrived three days after their own detection - but only when it is written down at the time, not reconstructed under inspection.
4. `awareness_at` stays editable after triage (facts change), and every change is historised. Phase 2 freezes the derived deadline instead of the anchor : once `IncidentNotification.first_submitted_at` is set, `anchor_at`, `due_at` and `late_by` stop recomputing, so a later anchor correction can never silently un-breach a filed obligation (RG-INC-28).

## Exercises (`is_exercise`)

A.5.24 requires the incident response plan to be **tested**. Cairn tests it by running a simulation or tabletop through the identical lifecycle, on a real `Incident` row flagged `is_exercise=True`, rather than by adding a separate drill entity that would never exercise the real gates.

An exercise:

- runs the identical lifecycle, with identical permission gates and identical timestamp stamping;
- is excluded from every KPI, predefined indicator, report, calendar deadline feed, kanban bucket and dashboard count (the exclusion is a `.exclude(is_exercise=True)` on the querysets, never a lifecycle state);
- **never instantiates regulatory notification obligations** : filing a real notification for a drill is an incident in its own right;
- is therefore **exempt from the RG-INC-19 `no_obligation_justification` gate**. This resolves the contradiction the two rules would otherwise create : RG-INC-17 guarantees an exercise always produces zero obligations, so an unqualified RG-INC-19 would force the operator to type a legal justification for owing nothing on every single drill, training the wrong reflex and polluting the exact field an auditor reads. The gate reads `if not obligations and not incident.personal_data_involved and not incident.is_exercise`.
- on closure, updates `IncidentResponsePlan.last_exercise_date` from `closed_at` when it is more recent than the stored value. That field is maintained here and nowhere else : it is the A.5.24 plan-testing evidence, and hand-editing it would make it worthless.

## Lifecycle

`LIFECYCLE_NAME = "incident"`, `layout="graph"`, registered from `IncidentsConfig.ready()` in `incidents/lifecycles.py`.

> `lifecycle_name_for()` (`core/lifecycle.py` `lifecycle_name_for()`) resolves `LIFECYCLE_NAME` only `if name and name in LIFECYCLE_REGISTRY`. An `incidents/apps.py` that forgets to import `incidents.lifecycles` from `ready()` therefore **fails silently** : every model in the module quietly runs the default 4-state lifecycle, in tests as well as in production, with no error anywhere. The module ships a test asserting `Incident.get_lifecycle().name == "incident"` so the omission fails loudly.

### Authoring : hand-written `Step` / `Transition` lists, not `lifecycle_from_state_flags`

`CLAUDE.md` says new entities with operational stages get a lifecycle **generated from their transition constants**. The `incident` lifecycle (and the `incident_evidence` one) deviate from that rule, deliberately, for two reasons that the generator cannot accommodate:

1. **`lifecycle_from_state_flags()` cannot carry triggers.** It builds every `Step(...)` with no `triggers=` argument (`core/lifecycle.py` `lifecycle_from_state_flags()`), and its tuple contract has eight slots with no ninth for them. A lifecycle generated from constants physically cannot declare the confirmation gate that closure and evidence destruction rest on.
2. **The auto-wired archive / restore bookends are unsafe here.** See [The archive and restore bookends](#the-archive-and-restore-bookends).

Both lifecycles are therefore declared as explicit `Step` and `Transition` lists in `incidents/lifecycles.py`, with the step codes still exported as constants from `incidents/constants.py` so no state literal ever appears outside that module (RG-INC-37). The other lifecycles in the module (`security_event`, `incident_notification`, `post_incident_review`, and `personal_data_breach` in phase 2) keep the generated form, feeding `lifecycle_from_state_flags()` a state-flag list that **includes an explicit `archived` item** and a transition list that hand-declares both bookends.

### Steps

Eleven steps : one draft entry, seven operational stages, two domain terminal exits and the generic archived exit.

| Code | Label | StepKind | In reports | Linkable | Deletable | Tone | Meaning |
|---|---|---|---|---|---|---|---|
| `draft` | Draft | `DRAFT` | no | no | **yes** | `neutral` | The write-up before declaration. The **only** step in which an incident can be deleted. |
| `detected` | Detected | `INTERMEDIATE` | **yes** | no | no | `secondary` | Declared. A.6.8 reporting done. |
| `triaged` | Triaged | `INTERMEDIATE` | **yes** | **yes** | no | `info` | A.5.25 assessment and decision complete : severity, category and incident manager fixed, notification obligations instantiated. |
| `investigating` | Investigating | `INTERMEDIATE` | **yes** | **yes** | no | `primary` | Analysis in progress, evidence collected under A.5.28 |
| `contained` | Contained | `INTERMEDIATE` | **yes** | **yes** | no | `warning` | Spread stopped |
| `eradicated` | Eradicated | `INTERMEDIATE` | **yes** | **yes** | no | `primary` | Cause removed from the environment |
| `recovered` | Recovered | `INTERMEDIATE` | **yes** | **yes** | no | `success` | Normal service restored |
| `post_incident_review` | Post-incident review | `INTERMEDIATE` | **yes** | **yes** | no | `info` | A.5.27 learning phase. The mandatory gate before closure. |
| `closed` | Incident closed | `ARCHIVED` (terminal) | **yes** | no | no | `dark` | Formally closed after an approved review. Carries a `confirm` trigger. |
| `reclassified` | Reclassified as event | `ARCHIVED` (terminal) | no | no | no | `muted` | Determined after declaration not to have been an incident. The honest off-ramp that keeps the register clean without deleting the record. |
| `archived` | Archived | `ARCHIVED` | no | no | no | `muted` | The generic exit, declared **explicitly** (see below) |

`closed` keeps `counts_in_reports=True` on purpose : a closed incident is exactly what the annual register, the management review and the indicator series are about. `reclassified` does not, because it was never an incident.

### Transitions

`permission_action` is the suffix appended to `workflow_perm_namespace` (`incidents.incident`), so `update` means `incidents.incident.update` and `approve` means `incidents.incident.approve`.

| Verb | Transition | `permission_action` | `requires_comment` | Side effects |
|---|---|---|---|---|
| Declare | `draft -> detected` | `update` | no | Stamps `declared_at`; defaults `awareness_at` to `detected_at` if still blank; appends a `lifecycle` timeline entry |
| Triage | `detected -> triaged` | `update` | no | Stamps `triaged_at`; copies `severity` into the write-once `initial_severity`; instantiates the notification obligations |
| Investigate | `triaged -> investigating` | `update` | no | |
| Contain | `triaged -> contained` | `update` | no | For incidents contained on sight, with no investigation phase. Stamps `contained_at`. |
| Contain | `investigating -> contained` | `update` | no | Stamps `contained_at` |
| Eradicate | `contained -> eradicated` | `update` | no | Stamps `eradicated_at` |
| Recover | `eradicated -> recovered` | `update` | no | Stamps `recovered_at` |
| Open post-incident review | `recovered -> post_incident_review` | `update` | no | Creates the [PostIncidentReview](post-incident-review.md) if absent (see [Auto-created children](#auto-created-children-and-the-initial-step)) |
| Close the incident | `post_incident_review -> closed` | **`approve`** | **yes** | `confirm` trigger on entry. Stamps `closed_at`; updates `IncidentResponsePlan.last_exercise_date` when `is_exercise`. |
| Re-triage | `investigating -> triaged` | `update` | **yes** | Severity or classification changed. `triaged_at` is **not** re-stamped (write-once). |
| Resume investigation | `contained -> investigating` | `update` | **yes** | |
| Reopen | `recovered -> investigating` | `update` | **yes** | Clears `recovered_at` |
| Reopen after closure | `closed -> investigating` | **`approve`** | **yes** | Clears `closed_at`. The original closure stays in the lifecycle history; the reopen is appended to the timeline ledger. |
| Reclassify as event | `detected -> reclassified` | **`approve`** | **yes** | |
| Reclassify as event | `triaged -> reclassified` | **`approve`** | **yes** | Refused when any notification already carries a `sent_at` |
| Reclassify as event | `investigating -> reclassified` | **`approve`** | **yes** | Not reachable from `contained` onward : once you have contained something, it happened |
| Archive | `* -> archived` | **`approve`** | **yes** | Hand-declared, not auto-wired |
| Restore | `archived -> draft` | **`approve`** | no | Hand-declared, and refused for any incident that has ever left `draft` |

There is **no** `lifecycle_transition_url_name` override : every transition posts to the generic `workflow:transition` endpoint, and every gate below lives on the model.

### The archive and restore bookends

`lifecycle_from_state_flags()` appends `Transition(target="archived", source=ANY, label=_("Archive"))` and `Transition(target="draft", source="archived", label=_("Restore"))` **with no `permission_action` and no `requires_comment`** (`core/lifecycle.py` `lifecycle_from_state_flags()`), and `user_can_perform()` (`core/lifecycle.py` `user_can_perform()`) allows any transition whose `permission_action` is empty. Since `draft` is `deletable=True`, that pair yields an **archive -> restore -> delete** path open to anyone who can reach the transition endpoint, defeating RG-INC-07 entirely.

Every lifecycle in this module therefore:

1. declares `archived` **explicitly** among its steps, so `has_archived` is `True` and nothing is auto-wired;
2. hand-declares `ANY -> archived` with `permission_action="approve"` and `requires_comment=True`;
3. hand-declares `archived -> draft` with `permission_action="approve"`;
4. and, on `Incident`, additionally refuses the restore edge in `transition_to()` for any row that has ever left `draft`, which the immutable `core.LifecycleEvent` ledger answers exactly.

The same three-line correction is applied to `security_event`, `incident_evidence`, `incident_notification`, `post_incident_review` and (phase 2) `personal_data_breach`. Where a lifecycle also declares its own `draft` step explicitly, the `draft -> <initial step>` entry transition is likewise no longer auto-wired and must be hand-declared.

[IncidentResponsePlan](incident-response-plan.md) needs none of this : it runs the core `default` lifecycle, whose archive edge already carries `permission_action="approve"` and which has **no restore transition at all** (`core/lifecycle.py` `DEFAULT_LIFECYCLE`).

### Transition gates

**Every audit gate in this module is enforced in a `transition_to()` override on the model, and never through `Transition.form_class`, `allowed_roles` or `allowed_users`** (RG-INC-08). This is not a stylistic preference:

- `lifecycle_to_json()` (`core/lifecycle.py` `lifecycle_to_json()`) serialises only codes, labels, kind, governance flags, tone, step `triggers`, and each transition's source, target, label, `requires_comment` and `permission_action`. `form_class`, `allowed_roles` and `allowed_users` are **omitted by design**.
- `lifecycle_from_json()` (`core/lifecycle.py` `lifecycle_from_json()`) rebuilds transitions without them.
- `get_lifecycle()` (`core/lifecycle.py` `get_lifecycle()`) **prefers the `post_migrate`-seeded `LifecycleDefinition` row** over the code default.

So a gate declared through `form_class` or `allowed_roles` is silently dead on every migrated database - green in a unit test that builds the lifecycle in memory, absent in production. Conversely, all three write surfaces funnel through `BaseModel.transition_to()` : the web stepper (`core/workflow_views.py` `WorkflowTransitionView.post()`), the DRF `LifecycleAPIMixin` (`accounts/api/mixins.py` `_lifecycle_transition()`) and MCP (`mcp/tools.py` `_transition_handler()`). A model-level override is the one place that binds web, API and MCP at once.

Each gate raises `django.core.exceptions.ValidationError` with a translated, actionable message naming the missing precondition, before `perform_transition()` is called, and the whole transition body runs inside `transaction.atomic()`.

| Gate | Transition | Refused unless |
|---|---|---|
| **G-01 Declaration** | `draft -> detected` | `detected_at` is set and `awareness_at >= detected_at`. Stamps `declared_at` and back-fills `awareness_at`. |
| **G-02 Triage** (RG-INC-11) | `detected -> triaged` | `severity`, `category` and `incident_manager` are all set, **and** `awareness_justification` is non-blank whenever `awareness_at > detected_at`. |
| **G-03 Obligation coverage** (RG-INC-19) | `detected -> triaged`, evaluated at the **end** of the transition body, after obligation generation, inside the same atomic block | Either at least one `IncidentNotification` was instantiated, or `personal_data_involved` is `True` (which forces one), or `is_exercise` is `True`, or `no_obligation_justification` is non-blank. Placing the check at the end of the triage transition is the only point at which the obligation count is knowable; a failure rolls the whole triage back, obligations included. |
| **G-04 Reclassification** (RG-INC-15) | `triaged -> reclassified`, `investigating -> reclassified` | No `IncidentNotification` on the incident carries a `sent_at`. The `detected -> reclassified` edge predates obligation generation, so no check is possible or needed there. You cannot un-declare something you have already told a regulator about. |
| **G-05 Closure** (RG-INC-14) | `post_incident_review -> closed` | The [PostIncidentReview](post-incident-review.md) exists **and** is in `approved` or `effectiveness_verified`; **and** every [IncidentNotification](incident-notification.md) has `decision != undecided`; **and** no [IncidentEvidence](incident-evidence.md) item is still in the `collected` step. Membership tests use the step codes from `incidents/constants.py`, never literals. |
| **G-06 Reopen after closure** (RG-INC-16) | `closed -> investigating` | Holder of `incidents.incident.approve` with a comment. Clears `closed_at`. |
| **G-07 Restore** | `archived -> draft` | No `core.LifecycleEvent` on the incident records a step other than `draft` or `archived`. An incident that was ever declared can be archived but never restored into a deletable step. |
| **G-08 Write-once stamps** (RG-INC-12) | all | `declared_at`, `triaged_at`, `contained_at`, `eradicated_at`, `recovered_at` and `closed_at` are stamped by the override only. They are excluded from every `ModelForm`, are `read_only` in every serializer, are absent from every MCP `writable_fields` list, and are cleared **only** by their matching reopen transition. |

Every transition, whatever its outcome, appends exactly one [IncidentTimelineEntry](incident-timeline-entry.md) with `source="lifecycle"`, carrying the transition label, the actor and the comment (RG-INC-09), so the narrative and the state machine can never diverge.

### The confirmation trigger on `closed`

`closed` carries `triggers=(Trigger(TRIGGER_CONFIRM),)`. The stepper shows a Yes/No modal before the transition is performed, then collects the mandatory comment, then submits.

Two honest caveats an implementer must know:

1. **No lifecycle in Cairn uses `Trigger` today.** `grep -rn 'TRIGGER_CONFIRM\|triggers='` over the tree returns hits only inside `core/lifecycle.py`. The confirm branch in `templates/includes/lifecycle_stepper.html` (the `opts.confirm` path, lines 85-99) has therefore **never run**. The module is its first user and ships an explicit test of that path, in both light and dark mode and at mobile width, before merge.
2. Triggers *do* survive the DB round-trip (`lifecycle_to_json` emits a `triggers` key and `_triggers_from_json` parses it back), so the seeded `LifecycleDefinition` row keeps the confirmation. It is only the **generator** that cannot express them, which is why this lifecycle is hand-authored.

The confirmation is a UX affordance, not a security control : it is not a substitute for G-05, which is enforced server-side and applies identically to a DRF or MCP caller that never sees a modal.

### Auto-created children and the initial step

`BaseModel.save()` calls `_ensure_initial_step()` (`context/models/base.py` `BaseModel._ensure_initial_step()`) on every insert, and `Lifecycle.initial_step` (`core/lifecycle.py` `Lifecycle.initial_step`) returns the single `StepKind.DRAFT` step. The `workflow_state` field default is the literal `"draft"`, which **is** a valid step of every lifecycle in this module, so `_ensure_initial_step()` leaves it alone and the row lands in `draft`.

**No entity in this module is ever "created in" a domain step.** Setting `workflow_state="assessed"` in the `create()` call would stick - the snap only fires on a blank or unknown value - but it would leave **no `core.LifecycleEvent` row**, so the obligation would have no recorded entry into the register, which is precisely the audit trail the design exists to produce.

Every auto-creation path therefore does, inside one `transaction.atomic()` block:

```python
obj = Model(...)
obj.save()
obj.transition_to("<domain step>", user, enforce_permission=False)
```

Applied here:

- the `detected -> triaged` transition creates each `IncidentNotification`, then transitions it to **`assessed`** ("To decide"). Without the second call the obligation sits in `draft`, where it is `deletable=True`, is absent from the "To decide" bucket the whole *an unanswered obligation is visible rather than absent* argument rests on, and still carries `decision=""` - blocking G-05 invisibly;
- the `recovered -> post_incident_review` transition creates the `PostIncidentReview`, copies the incident's `scopes`, then transitions it to **`scheduled`**;
- phase 2's personal-data path creates the `PersonalDataBreach`, then transitions it to **`under_qualification`**.

`enforce_permission=False` is correct on these three : the permission was already checked on the *parent* transition the user actually performed, and the child rows are a consequence of it, not a separate act.

The module ships a regression test asserting that `IncidentNotification.objects.create(...).workflow_state == "assessed"` **fails**, and that the generator's output is `assessed` with a matching `LifecycleEvent`.

## Promotion from a security event

An incident normally begins life as a [SecurityEvent](security-event.md). Promotion is a single atomic act, not a two-step data entry:

1. The event must be in `under_assessment` with non-blank `assessment_notes` (RG-INC-05) and `event_class = event` : an event classed `weakness` can never be promoted to an incident (RG-INC-03).
2. An `Incident` is created in `draft` and immediately transitioned to `detected`, copying `detection_source`, `category`, `affected_support_assets`, `affected_essential_assets`, `affected_sites` and `scopes` from the event.
3. The event's `incident` FK is set (a DB `CheckConstraint` also requires it before `triage_decision` may be `incident`), `triage_decision` is set to `incident`, and the event transitions to `confirmed_incident`.

Several events may feed one incident through `Incident.source_events`; an event promotes into at most one incident (RG-INC-06). On the MCP surface the whole sequence is the single `declare_incident_from_event` tool, precisely so an agent cannot leave a half-promoted event behind.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-01 | A [SecurityEvent](security-event.md) is never an incident. An `Incident` exists only after an explicit, permissioned A.5.25 assessment transition on the event, or a direct declaration recorded with a `detection_source` and a named declarer. |
| RG-INC-06 | Several events may promote into one incident (`Incident.source_events`); an event promotes into at most one incident. |
| RG-INC-07 | An incident is deletable only in `draft`. From `detected` onward `BaseModel.delete()` raises `LifecycleProtectedError`, and `PROTECT` on `IncidentEvidence.incident`, `IncidentNotification.incident` and `PostIncidentReview.incident` makes deletion impossible in practice. The archive / restore bookends are approve-gated and the restore edge is refused for any incident that ever left `draft` (G-07), so there is no archive -> restore -> delete path. |
| RG-INC-08 | Every audit gate is enforced in a `transition_to()` override on the model, never through `Transition.form_class`, `allowed_roles` or `allowed_users`, because `lifecycle_to_json` drops those and the seeded `LifecycleDefinition` row wins at runtime. |
| RG-INC-09 | Every lifecycle transition on an incident automatically appends an [IncidentTimelineEntry](incident-timeline-entry.md) with `source="lifecycle"`, carrying the transition label, the actor and the comment. |
| RG-INC-11 | Reaching `triaged` requires `severity`, `category` and `incident_manager`, plus `awareness_justification` when `awareness_at` postdates `detected_at`. The transition stamps `triaged_at` and copies `severity` into the write-once `initial_severity`. |
| RG-INC-12 | Phase timestamps are stamped by the `transition_to()` override only, are excluded from every form, serializer and MCP writable list, and are cleared only by their matching reopen transition. Write-once is prevented at application level and **detected** through `HistoricalRecords`; `QuerySet.update()`, `bulk_update()` and raw SQL bypass `save()`. |
| RG-INC-13 | `awareness_at` is the single legal clock anchor and is distinct from `detected_at`. It defaults to `detected_at`, must be `>= detected_at`, and requires a non-blank `awareness_justification` whenever it postdates detection. Statutory deadlines are **never** derived from `detected_at`. |
| RG-INC-14 | Closing an incident is refused unless its post-incident review is in `approved` or `effectiveness_verified`, every notification has `decision != undecided`, and every evidence item has left `collected`. Closure additionally requires `incidents.incident.approve`, a mandatory comment and a confirmation. |
| RG-INC-15 | Reclassification is reachable only up to `investigating`, requires `approve` plus a mandatory comment, and is refused when any notification already carries a `sent_at`. Once an incident is contained, it happened. |
| RG-INC-16 | Reopening a closed incident requires `approve` and a mandatory comment, clears `closed_at`, and appends a timeline entry. The original closure remains in the lifecycle history. |
| RG-INC-17 | An incident with `is_exercise=True` runs the identical lifecycle but is excluded from every KPI, indicator, report, calendar deadline and dashboard count, and never instantiates regulatory notifications. Its closure updates `IncidentResponsePlan.last_exercise_date`, which is the A.5.24 plan-testing evidence. |
| RG-INC-18 | `personal_data_involved=True` forces the `gdpr_art33_authority` obligation to be instantiated at triage regardless of the plan's configured regimes, and in phase 2 creates the `PersonalDataBreach` record (saved, then transitioned to `under_qualification`). Clearing the flag never deletes that record : a breach is ruled out through the `not_a_breach` transition, never by unchecking a box. |
| RG-INC-19 | When triage produces zero notification obligations, `personal_data_involved` is `False` **and** `is_exercise` is `False`, a non-blank `no_obligation_justification` is mandatory. A missing regime or template must never read as compliance on a green dashboard; an exercise, which by RG-INC-17 always produces zero obligations, is exempt. |
| RG-INC-33 | No automated RTO / MTD breach claim is made anywhere in the module. `assets.EssentialAsset.max_tolerable_downtime`, `recovery_time_objective` and `recovery_point_objective` are free-text `CharField(max_length=100)` values like `4 hours`, so the register reports `outage_duration` and lists each affected asset's declared objective verbatim, and declines to conclude. Migrating those three fields to `DurationField` is an m2 prerequisite, not smuggled into m6. |
| RG-INC-34 | A risk revealed by an incident is a `risks.Risk` with `risk_source = RiskSourceType.INCIDENT`, `source_entity_type = "incidents.Incident"` and `source_entity_id = incident.pk`, reusing the existing generic back-pointer. No new FK on `Risk`. |
| RG-INC-36 | An incident realising a risk that carries an **active** `risks.RiskAcceptance` forces that acceptance under review : the daily cron notifies the acceptance owner and sets `review_date` on every linked risk still in a reportable step. A derived query hung off the existing `expire_risk_acceptances` sweep, not a stored edge. |
| RG-INC-37 | Every report, KPI, indicator, calendar feed, kanban bucket and link picker filters through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. No incident state literal appears anywhere outside `incidents/constants.py`. |
| RG-INC-38 | Scope tenancy : `Incident` carries `scopes` (`ScopedModel`). Its non-scoped children inherit through `scope_parent_lookup`. See [Scope tenancy](#scope-tenancy). |

## Scope tenancy

`Incident` is a `ScopedModel`, so `ScopeFilterMixin` (`accounts/mixins.py` `ScopeFilterMixin.get_queryset()`) and `ScopeFilterAPIMixin` (`accounts/api/mixins.py` `get_queryset()`) filter list views and viewsets with no extra work. Its non-scoped children ([IncidentEvidence](incident-evidence.md), [IncidentNotification](incident-notification.md), and phase 2's `PersonalDataBreach`) declare `scope_parent_lookup = "incident__scopes"`; grandchildren chain it (`evidence__incident__scopes`).

**This inheritance is not enforced today on three call sites, and phase 1 must extend them.** This is a security fix, logged under a `### Security` entry in `CHANGELOG.md`:

| Call site | Current behaviour | Required change |
|---|---|---|
| `mcp/tools.py` `_filter_by_scopes` | Handles `context.Scope`, then a `scopes` M2M, then `return qs` **unfiltered** | Accept `model` / `parent_lookup`, and thread a `scope_parent_lookup` argument through `_register_crud` / `_list_handler` / `_get_handler` / `_transition_handler` / `_allowed_transitions_handler`. Without it, `list_incident_evidence`, `list_incident_notifications` and `list_overdue_incident_notifications` return every row on the instance to any holder of `.read`. |
| `core/workflow_views.py` `WorkflowTransitionView` | Guards with `if allowed_scopes is not None and hasattr(obj, "scopes")` | Honour a model-level `scope_parent_lookup` attribute. Without it, the evidence `destroy` transition and the notification `not_required` decision are performable cross-scope. |
| `core/history_views.py` `HistoryPartialView` | Same `hasattr(obj, "scopes")` guard | Same change. Without it, the full history of an out-of-scope evidence or notification row is readable. |

This is core work in the phase-1 PR, not an incidents-app detail : the two generic web endpoints are shared by every module.

## Endpoints

### REST

Base path `/api/v1/incidents/`, mounted in `core/urls.py`; `incidents/api/urls.py` declares `app_name = "incidents-api"` and a `DefaultRouter`.

- `GET /api/v1/incidents/incidents/` : list, filtered by `IncidentFilter` (`status`, `severity`, `category`, `detection_source`, `is_exercise`, `personal_data_involved`, `incident_manager_id`, `origin_supplier_id`, `scope_id`, `detected_after` / `detected_before`, `awareness_after` / `awareness_before`, `has_overdue_notifications`, `has_unsealed_evidence`, `realised_risk_id`)
- `POST /api/v1/incidents/incidents/` and `POST /api/v1/incidents/incidents/batch/` (max 100 items, non-atomic, per-item `{index, status, id, reference}`)
- `GET/PUT/PATCH/DELETE /api/v1/incidents/incidents/<uuid>/`
- `GET/POST /api/v1/incidents/incidents/<uuid>/transition/` : supplied by `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`, so every gate above applies identically to an API caller
- `GET /api/v1/incidents/incidents/<uuid>/history/` : `core.history.build_timeline`, merging `LifecycleEvent` and `HistoricalRecords`

The viewset stack, in the house order : `BatchCreateMixin`, `ScopeFilterAPIMixin`, `LifecycleAPIMixin`, `HistoryAPIMixin`, `CreatedByMixin`, `viewsets.ModelViewSet`. Permissions follow the newest module precedent (`trust_center/api/views.py` `_ManagedViewSet`) : `ModulePermission` directly, plus an `_IncidentViewSet` base fixing `permission_module = "incidents"` and `custom_action_map = {"transition": "update"}`. Another app's `ModulePermission` subclass (`ContextPermission`) is **not** imported.

Two serializers per entity : `IncidentSerializer` (full; `read_only_fields` covering `id`, `reference`, `created_by`, `created_at`, `updated_at`, `version` and every transition-stamped timestamp) and `IncidentListSerializer` for the index, switched on `self.action == "list"`. `status` is exposed as `CharField(source="workflow_state", read_only=True)`.

### MCP

Registered by `_register_incidents_tools(server)`, resolving models through `_get_model("incidents", ...)` rather than a direct import.

- `_register_crud(server, "incident", Incident, "incidents.incident", ...)` generates `list_incidents`, `get_incident`, `create_incident`, `batch_create_incidents`, `update_incident`, `delete_incident`, `transition_incident`, `incident_allowed_transitions`, `get_incident_history`.
- Filters : `status`, `severity`, `category`, `detection_source`, `is_exercise`, `personal_data_involved`. Search fields : `reference`, `title`, `summary`, `description`.
- `m2m_fields` maps `scope_ids`, `affected_essential_asset_ids`, `affected_support_asset_ids`, `affected_site_ids`, `affected_activity_ids`, `affected_supplier_ids`, `threat_ids`, `exploited_vulnerability_ids`, `realised_risk_ids`, `linked_requirement_ids`.
- `declare_incident_from_event` (bespoke; requires `incidents.security_event.update` **and** `incidents.incident.create`) runs the whole A.5.25 promotion atomically.
- Transition-stamped timestamps never appear in `writable_fields`; every enum field carries an explicit `enum` list in `field_overrides`; `description` uses `_html_field()`.

`mcp/tools.py` `HELP_TEXT` gains `Incident=INCD` in the reference-prefix block, and a new `TOPIC_INCIDENTS` constant joins `ALL_TOPICS`.

## Permissions

| Codename | Description |
|---|---|
| `incidents.incident.read` | List / read incidents |
| `incidents.incident.create` | Declare an incident |
| `incidents.incident.update` | Edit business fields and perform the operational transitions (declare, triage, investigate, contain, eradicate, recover, open the review, re-triage, resume, reopen before closure) |
| `incidents.incident.approve` | Close, reopen after closure, reclassify, archive, restore |
| `incidents.incident.delete` | Delete a draft incident |

`incidents.incident.*` also gates [IncidentResponseAction](incident-response-action.md) and [IncidentTimelineEntry](incident-timeline-entry.md), which have no feature of their own. `MODULE_LABELS` gains `"incidents": _("Incidents")`. The rows are created and attached to the six system groups by `accounts/migrations/0056_add_incidents_permissions.py`, which depends on `("accounts", "0055_alter_accesslog_event_type")` and copies `0053_add_certificate_permissions.py` verbatim. The `PERMISSION_REGISTRY` entry alone makes tests pass (`conftest.py` seeds from `get_all_permissions()`), so the migration must land in the same commit or production silently lacks the grants.

## UI

- **List** (`/incidents/`) : the full house stack (`LoginRequiredMixin`, `PermissionRequiredMixin`, `ListSummaryMixin`, `PredefinedFilterMixin`, `AdvancedFilterMixin`, `SavedFilterMixin`, `ColumnPreferenceMixin`, `ScopeFilterMixin`, `SortableListMixin`, `ListView`, with `ListSummaryMixin` strictly left of `ScopeFilterMixin`), `page_header` with `nav="incidents:incident-list"` and `accent="incidents"`, `list_rail_kpis` showing open incidents by severity and overdue obligations, an `#item-table-body` HTMX partial, pagination and the filter offcanvas. `INCIDENT_FILTER_GROUPS` / `INCIDENT_TEXT_FILTERS` / `INCIDENT_COLUMNS` are module-level constants above the view.
- **Detail** (`/incidents/<uuid>/`) : a **strict 2-column card layout, no nav-tabs**. Left column, stacked cards : *Summary and impact* (CIA flags, personal data, TLP, category, `outage_duration` shown beside each affected asset's declared RTO / MTD verbatim, with no breach claim); *Chronology* (the append-only timeline ordered by `occurred_at`, with an inline add form that never leaves the page and lifecycle-sourced entries visually distinguished); *Response actions*; *Evidence* (hash, sealed state, TLP, legal hold, retention date, and a danger badge when `last_integrity_check_ok` is `False`); *Regulatory notifications* (regime, recipient, `due_at`, a live countdown, a "no statutory deadline" badge, a red overdue state); *Post-incident review* summary; *Linked registers* as collapsible Bootstrap sections. Right column, sticky sidebar : `{% workflow_badge %}`, the severity badge with `initial_severity` shown alongside when they differ, incident manager and reporter avatars, the response plan link, the detected / awareness / declared / triaged / contained / eradicated / recovered / closed stamps, scopes, tags, and the history trigger.
- **Stepper** : `{% include "includes/lifecycle_stepper.html" %}` fed by `LifecycleStepperMixin`. Never a status select, never plain buttons. This lifecycle has **three** `StepKind.ARCHIVED` steps (`closed`, `reclassified`, `archived`), so the dagre renderer draws three detached exits - busier than any existing Cairn lifecycle, and requiring an explicit visual check at desktop and mobile widths in **both** light and dark mode before merge.
- Create / update / delete use `HtmxFormMixin` drawer modals, with mobile-first care on the many multi-select widgets (assets, sites, suppliers, risks, requirements) and on the sticky action bar.
- `MODULE_ACCENTS` gains `"incidents"` (matching the app label; note that the map stores `trust-center` hyphenated, which is the exception, not the rule), with `--module-accent-incidents` and `--module-accent-incidents-soft` defined in **both** the light and dark token blocks of `base.html`. An unregistered accent is silently dropped.

## Translations

Three of this entity's user-facing strings collide with `msgid`s that already exist in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`, so a collision breaks CI outright.

**Enum labels, field verbose names and template strings** use `pgettext_lazy("incident", ...)` in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po` file. For this entity that covers `DetectionSource.AUDIT` ("Audit", bare entry at `django.po`) and `DetectionSource.OTHER` ("Other", bare entry at `django.po`), plus the `Severity` column header (`django.po`).

**Step and transition labels are different, and must never use `pgettext_lazy`.** `lifecycle_to_json()` stringifies each label with `str(...)`, and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy` (`core/lifecycle.py` `lifecycle_from_json()`). A step label carrying a `msgctxt` in code therefore loses that context after the `post_migrate` DB round-trip and resolves to whatever the *bare* `msgid` maps to. The rule for labels is:

| Label | Existing bare entry | Decision |
|---|---|---|
| `draft` step "Draft" | `django.po` -> "Brouillon" | **Reuse.** The core `draft_step()` already emits this exact string, and the French is correct. No new entry. |
| `archived` step "Archived" | `django.po` -> "Archivé" | **Reuse.** Same reason. |
| `closed` step | bare "Closed" at `django.po` -> "Clôturée" (feminine) | **Rename to "Incident closed"** -> "Incident clôturé". A `msgctxt` would be stripped by the round-trip and the step would render "Clôturée", which is the wrong gender for `incident`. |
| Close transition | bare "Close" at `django.po` -> "Fermer" (as in closing a dialog) | **Rename to "Close the incident"** -> "Clôturer l'incident". Same reason. |

The remaining step and transition labels ("Detected", "Triaged", "Investigating", "Contained", "Eradicated", "Recovered", "Post-incident review", "Reclassified as event", "Declare", "Triage", "Investigate", "Contain", "Eradicate", "Recover", "Open post-incident review", "Re-triage", "Resume investigation", "Reopen", "Reopen after closure", "Reclassify as event") are new bare `msgid`s with no collision; "Archive" and "Restore" already exist as the core bookend labels and are reused. After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- ISO/IEC 27001:2022 A.5.26 (response to information security incidents), A.5.24 (planning and preparation), A.5.25 (assessment and decision), A.5.27 (learning), A.5.28 (collection of evidence)
- ISO/IEC 27035-1 / -2 (incident management : plan and prepare, detect and report, assess and decide, respond, learn)
- ISO/IEC 27001:2022 clause 10.1 / 10.2 (continual improvement, nonconformity and corrective action)
- GDPR Art. 33(1) (72 hours from becoming aware), NIS2 Art. 23 (24h early warning, 72h notification, one-month final report), DORA Art. 19
- [SecurityEvent](security-event.md) : the A.6.8 register an incident is promoted from
- [IncidentResponsePlan](incident-response-plan.md) : the A.5.24 procedure this incident was handled under
- [IncidentTimelineEntry](incident-timeline-entry.md), [IncidentResponseAction](incident-response-action.md), [IncidentEvidence](incident-evidence.md), [IncidentNotification](incident-notification.md), [PostIncidentReview](post-incident-review.md)
- [README.md](README.md) : module business rules, permissions, notifications, environment variables
- [governance/workflow.md](../governance/workflow.md) and [governance/lifecycle.md](../governance/lifecycle.md) : the lifecycle framework and engine internals
- [Risk](../m4-risks/risk.md), [RiskAcceptance](../m4-risks/risk-acceptance.md), [Vulnerability](../m4-risks/README.md), [ComplianceActionPlan](../m3-compliance/compliance-action-plan.md), [Supplier](../m2-assets/supplier.md)

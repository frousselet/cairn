# Module 6 : Security Incident Management

## Functional and technical specification

**Version:** 1.0
**Date:** 27 August 2026
**Status:** Draft

Django app: `incidents/`.

---

## Entities

| Entity | Importable path | Reference prefix | Lifecycle |
|---|---|---|---|
| [IncidentResponsePlan](incident-response-plan.md) | `incidents.models.response_plan.IncidentResponsePlan` | `IRPL` | core `default` |
| [SecurityEvent](security-event.md) | `incidents.models.security_event.SecurityEvent` | `EVNT` | `security_event` |
| [Incident](incident.md) | `incidents.models.incident.Incident` | `INCD` | `incident` |
| [IncidentTimelineEntry](incident-timeline-entry.md) | `incidents.models.timeline.IncidentTimelineEntry` | none (append-only log) | none |
| [IncidentResponseAction](incident-response-action.md) | `incidents.models.response_action.IncidentResponseAction` | `IRAC` | none (plain `status`) |
| [IncidentEvidence](incident-evidence.md) | `incidents.models.evidence.IncidentEvidence` | `EVID` | `incident_evidence` |
| [EvidenceCustodyEvent](evidence-custody-event.md) | `incidents.models.evidence.EvidenceCustodyEvent` | none (append-only ledger) | none |
| [PostIncidentReview](post-incident-review.md) | `incidents.models.post_incident_review.PostIncidentReview` | `PIRV` | `post_incident_review` |
| [IncidentNotification](incident-notification.md) | `incidents.models.notification.IncidentNotification` | `INOT` | `incident_notification` |
| [ReportingAuthority](reporting-authority.md) | `incidents.models.reporting_authority.ReportingAuthority` | `RGAU` | core `default` |
| [ReportingObligationTemplate](reporting-obligation-template.md) | `incidents.models.reporting_obligation_template.ReportingObligationTemplate` | `ROBT` | core `default` |
| [PersonalDataBreach](personal-data-breach.md) | `incidents.models.personal_data_breach.PersonalDataBreach` | `PDBR` | `personal_data_breach` |
| [NotificationFiling](notification-filing.md) | `incidents.models.filing.NotificationFiling` | `NFIL` | none |

> `INCD` is one letter-order away from `INDC` ([Indicator](../m1-context/indicator.md)). The two are visually confusable in a reference string, in a list column and in the MCP help block. Read them twice.

---

## 1. Overview

### 1.1 Purpose : the ISO/IEC 27035 five-phase process

The **Security Incident Management** module is the ISO/IEC 27001:2022 Annex A.5.24 to A.5.28 and A.6.8 surface of the platform, and the operational half of clause 10.1 / 10.2. Its structure is not an arbitrary decomposition : it **is** the five-phase process of ISO/IEC 27035-1 and 27035-2, one phase per group of entities.

| ISO/IEC 27035 phase | Entities | What the phase produces |
|---|---|---|
| **Plan and prepare** | [IncidentResponsePlan](incident-response-plan.md), [ReportingAuthority](reporting-authority.md), [ReportingObligationTemplate](reporting-obligation-template.md) | The documented procedure in force, the classification scale that gives `severity` its meaning, the reporting channels including the anonymous one, and the filing contacts and legal rules prepared **before** anything happens (A.5.24, A.5.5). |
| **Detect and report** | [SecurityEvent](security-event.md) | The A.6.8 register of every reported occurrence, with `reported_at - detected_at` as the measurable reporting delay and an anonymous channel the database, not a form, guarantees. |
| **Assess and decide** | the `security_event` lifecycle | The A.5.25 judgement : a named person, a written `assessment_notes`, a stamped `assessed_at`, and three mutually exclusive permissioned outcomes plus an approve-gated discard. The events that were correctly **not** incidents leave a trace, which is the question every auditor asks. |
| **Respond** | [Incident](incident.md), [IncidentResponseAction](incident-response-action.md), [IncidentTimelineEntry](incident-timeline-entry.md), [IncidentEvidence](incident-evidence.md), [EvidenceCustodyEvent](evidence-custody-event.md), [IncidentNotification](incident-notification.md), [PersonalDataBreach](personal-data-breach.md), [NotificationFiling](notification-filing.md) | A.5.26 response with write-once phase stamps, A.5.28 evidence with its chain of custody, and the regulatory obligation register with its legal clock (GDPR Art. 33 / 34, NIS2 Art. 23, DORA Art. 19). |
| **Learn** | [PostIncidentReview](post-incident-review.md), and through it `compliance.Finding` and `compliance.ComplianceActionPlan` | A.5.27 learning, and the bridge into clause 10.2 : root cause, similar-occurrence check, corrective actions, and the effectiveness review that closes 10.2 d). |

Two properties are load-bearing across all five phases and are repeated in every entity file rather than assumed :

- **A decision is a lifecycle transition, never a field write.** Promoting an event, ruling out a notification obligation, sealing evidence, confirming a personal data breach and closing an incident are all permissioned, comment-bearing transitions that leave an immutable `core.LifecycleEvent`. A boolean column cannot carry a decider, a timestamp, a rationale and an approval, and those four together are what an inspection actually reads.
- **The module never claims immutability the schema does not provide.** The append-only entities prevent rewriting at application level and make tampering **detectable** through `HistoricalRecords`. That is the honest claim, and it is the one made to the auditor.

### 1.2 Functional scope

1. The **incident management procedure** of record, with its plan-testing evidence produced by real exercises run through the real lifecycle.
2. The **event and weakness register** (A.6.8) and the assessment that decides what is an incident (A.5.25).
3. The **incident file** (A.5.26) : impact picture, two clocks, phase stamps, blast radius into the asset, supplier, site, activity, threat, vulnerability, risk and requirement registers.
4. The **chronology** : an append-only, attributed narrative with correction by supersession, which is the account a regulator or a court reads.
5. The **evidence register** (A.5.28) with acquisition metadata, fingerprints, TLP handling caveats, legal hold, retention and an append-only chain-of-custody ledger.
6. The **regulatory obligation register** : one row per (incident, regime, recipient), carrying the legal clock, the decision on whether it applies, the omission judgement, and the filing log.
7. The **GDPR qualification** of an incident and the Art. 33(5) internal register entry.
8. The **post-incident review** (A.5.27) and its outputs into the single nonconformity register, the corrective action plans and the risk register.

### 1.3 The module ships as one block

**Everything above is delivered together, in one release.** The `PHASE 1` / `PHASE 2` markers that appear against individual fields and entities in the entity specifications are an **internal build order**, not a delivery boundary and not a feature flag. They record the order in which the work is sequenced and merged, and they are kept in the specs because the specs are final and because the order is genuinely useful to an implementer : the flat obligation clock is built and tested before the anchor engine is grafted onto the same table, and the module is deliberately shaped so that no field is ever migrated between the two steps.

Nothing in the module is gated on a later release. There is no shipped configuration in which [PersonalDataBreach](personal-data-breach.md), [NotificationFiling](notification-filing.md), [ReportingAuthority](reporting-authority.md) or [ReportingObligationTemplate](reporting-obligation-template.md) is absent, and no documentation, screenshot, seed row or acceptance criterion in this module describes a half-delivered state.

One genuine prerequisite sits **outside** the module and lands before it : the `compliance.Finding` generalisation described in §1.5. It is a separate pull request against the compliance app because it has its own blast radius and its own breaking permission change, not because the incident module is phased.

### 1.4 Dependencies on other modules

The module reads widely and is depended on by nothing. Every link below reuses an existing register rather than introducing a parallel one.

| Target module | Nature of the dependency |
|---|---|
| Context | `scopes` tenancy on [Incident](incident.md), [SecurityEvent](security-event.md), [IncidentResponsePlan](incident-response-plan.md) and [PostIncidentReview](post-incident-review.md); `context.constants.Criticality` reused as `severity`; `context.Site` and `context.Activity` as affected entities; `context.Stakeholder` as a notification recipient; `context.Role` as the RACI staffing of the plan; `context.Indicator` extended with seven predefined incident sources. |
| Assets | `assets.EssentialAsset` and `assets.SupportAsset` as affected entities and as the source of an evidence artefact; `assets.Supplier` split deliberately into `origin_supplier` (the third party who **caused** it) and `affected_suppliers` (impacted or notified downstream), because NIS2 / DORA third-party reporting and GDPR Art. 28 depend on the causal direction. |
| Risks | `risks.constants.ThreatCategory` reused verbatim as the incident taxonomy; `risks.Threat` as the threat that materialised; `risks.Vulnerability` as the promotion target of a confirmed weakness and as `exploited_vulnerabilities`; `risks.Risk` through `realised_risks` and through the existing generic `source_entity_type` / `source_entity_id` back-pointer; `risks.RiskAcceptance` forced under review by RG-INC-36. |
| Compliance | `compliance.Requirement` as `linked_requirements` on the incident and the plan, and as `failed_controls` / `controls_to_strengthen` on the review; `compliance.Finding` as the single nonconformity register (§1.5); `compliance.ComplianceActionPlan` as the corrective work (RG-INC-35); `compliance.constants.EffectivenessVerdict` imported, never redeclared. |
| Accounts | The custom `User` model for every people field; `accounts.Notification` (a `GenericForeignKey` target, so no new notification model); `PERMISSION_REGISTRY` and the six `SYSTEM_GROUPS`; `accounts.AccessLog` for in-platform reads. |
| Governance (lifecycle) | Six registered lifecycles plus three entities on the core `default` lifecycle; `core.LifecycleEvent` as the immutable transition ledger; `core.history.build_timeline` as the merged history panel. See [governance/workflow.md](../governance/workflow.md) and [governance/lifecycle.md](../governance/lifecycle.md). |
| Reports | Phase-3 polish only : the incident register report and the incident input block of the management review. Clause 9.3.2 d)1) and d)2) are reached through the generalised `Finding` and the predefined indicators, with **no** new plumbing. |
| Trust Center | **No coupling at all.** The internal incident register is never foreign-keyed to a published surface. |

The direction is one-way : the incidents module reads the other registers, and no other module gains a foreign key into `incidents` except `compliance.Finding.incident`, which is the deliberate bridge described next.

### 1.5 The prerequisite : `compliance.Finding` becomes the nonconformity register

A nonconformity raised by a post-incident review has nowhere clean to live today. It is not a `risks.Vulnerability` (an organisational weakness such as *the joiner-mover-leaver process is not followed* has no CVE and no affected asset), and a second nonconformity model would give ISO 27001 clause 10.2 two registers and two answers.

`compliance.Finding` is therefore generalised from *audit finding* to **nonconformity register entry**, in a separate pull request against the compliance app that lands before this module :

- `assessment` becomes `null=True, blank=True`, `on_delete` moves from `CASCADE` to `SET_NULL`;
- a `source` enum is added (`audit` | `incident` | `management_review` | `monitoring` | `complaint`), defaulting to `audit` so every existing row is semantically unchanged;
- `effectiveness_reviewed_at`, `effectiveness_reviewed_by` and `effectiveness_verdict` are added, closing clause 10.2 d) for audit findings as well as for incident-born ones;
- `assessor` is currently a **required** `PROTECT` foreign key to `AUTH_USER_MODEL` with no `null=True`. It becomes `null=True, blank=True`, **keeps its column**, is re-labelled **"Raised by"** through `verbose_name` only (no column change, no data migration), and a `clean()` requires it whenever `source == audit`. The [PostIncidentReview](post-incident-review.md) transition that raises a finding stamps it with the review facilitator;
- a **`compliance.finding` permission feature** is introduced. Findings are gated by `compliance.assessment.*` today, which would force an incident responder to hold audit permissions to record a nonconformity. Introducing the feature needs its own `accounts` data migration, otherwise the codenames exist in `PERMISSION_REGISTRY` (so tests pass, since `conftest.py` seeds from `get_all_permissions()`) and are granted to nobody on a real database;
- the **existing** MCP tools `list_findings`, `get_finding`, `create_finding`, `update_finding` and `delete_finding` are re-gated from `compliance.assessment.*` to `compliance.finding.*`. This is a **breaking contract change** for any live MCP integration and is logged as a `### Changed` entry in `CHANGELOG.md`, alongside the standalone finding list, detail, viewset and URL routes that `compliance/urls.py` does not have today (every finding route is nested under an assessment).

`Finding.incident` is **not** added in that pull request : it would create a circular application dependency. It lands with the incidents app, together with `PostIncidentReview.raised_findings`.

The management-review consequence is stated rather than left to be discovered : section 4a is **deliberately source-agnostic**, so an incident-born nonconformity reaches the review for free, while the assessment-scoped queries (`compliance/models/assessment.py` and `apply_findings_to_results`) stay audit-only **by construction**, because they iterate the reverse accessor `self.findings`, which by definition never yields a null-assessment row.

---

## 2. Business rules : the RG-INC register

Every rule cited anywhere in the module appears exactly once below. The register runs **RG-INC-01 to RG-INC-41** with no gaps and no retired identifiers. Each entity file restates the subset that governs it; this table is the reconciled whole, and it is the one to cite in a commit message or a code comment.

| ID | Rule |
|---|---|
| RG-INC-01 | A [SecurityEvent](security-event.md) is never an incident. An [Incident](incident.md) exists only after an explicit, permissioned A.5.25 assessment transition on the event, or a direct declaration recorded with a `detection_source` and a named declarer. |
| RG-INC-02 | Exactly one triage decision per event. Reaching `confirmed_incident` requires a non-null `incident` FK and reaching `confirmed_weakness` a non-null `vulnerability` FK; both are enforced by DB `CheckConstraint`s **as well as** by the transition gate, so neither raw SQL nor a `QuerySet.update()` can leave a promoted event pointing at nothing. |
| RG-INC-03 | An event with `event_class = weakness` can never be promoted to an incident. A weakness that has actually been exploited is a **new** event of class `event` linked to the weakness through `duplicate_of`, so the original reporting history stays intact and the exploitation's reporting delay is measured from its own detection. |
| RG-INC-04 | Discarding an event requires `incidents.security_event.approve` and a mandatory comment; the comment is written into `assessment_notes` **and** into the immutable `core.LifecycleEvent`, so the register itself is readable without joining the history. |
| RG-INC-05 | `assessment_notes` must be non-blank to leave `under_assessment` **by any route**, promotion and discard alike. An undocumented assessment is not an assessment. |
| RG-INC-06 | Several events may promote into one incident (`Incident.source_events`); an event promotes into at most one incident. |
| RG-INC-07 | An incident is deletable only in `draft`. From `detected` onward `BaseModel.delete()` raises `LifecycleProtectedError`, and `PROTECT` on `IncidentEvidence.incident`, `IncidentNotification.incident` and `PostIncidentReview.incident` makes deletion impossible in practice. The archive and restore bookends are approve-gated and the restore edge is refused for any incident that has ever left `draft`, so there is no archive -> restore -> delete path. |
| RG-INC-08 | Every audit gate in this module is enforced in a `transition_to()` override on the model, **never** through `Transition.form_class`, `allowed_roles` or `allowed_users`. `core/lifecycle.py` `lifecycle_to_json()` omits those three by design, `lifecycle_from_json()` rebuilds transitions without them, and `get_lifecycle()` prefers the `post_migrate`-seeded `LifecycleDefinition` row over the code default, so a gate declared that way is green in an in-memory unit test and silently dead on every migrated database. All three write surfaces funnel through `BaseModel.transition_to()` : `core/workflow_views.py` `WorkflowTransitionView.post()`, `accounts/api/mixins.py` `_lifecycle_transition()` and `mcp/tools.py` `_transition_handler()`. A model-level override is the one place that binds web, API and MCP at once. No entity in this module sets `lifecycle_transition_url_name`. |
| RG-INC-09 | Every lifecycle transition on an incident automatically appends exactly one [IncidentTimelineEntry](incident-timeline-entry.md) with `source = lifecycle`, carrying the transition label, the actor and the comment, inside the transition's transaction, so the narrative and the state machine can never diverge. |
| RG-INC-10 | The incident chronology is append-only. `IncidentTimelineEntry.save()` refuses any update to an existing row and `delete()` refuses outright, both raising `LifecycleProtectedError`; no update or delete route exists on the web, API or MCP surfaces. A correction is a **new** entry of type `correction` pointing at `superseded_entry` with a non-blank `correction_reason`. This is a Python-level guarantee : `QuerySet.update()`, `bulk_update()`, cascade deletion and raw SQL bypass it, and `HistoricalRecords` therefore makes tampering **detectable**, not impossible. |
| RG-INC-11 | Reaching `triaged` requires `severity`, `category` and `incident_manager`, plus a non-blank `awareness_justification` when `awareness_at` postdates `detected_at`. The transition stamps `triaged_at` and copies `severity` into the write-once `initial_severity`, so later severity drift is visible as a difference between two columns rather than only in a history diff. |
| RG-INC-12 | Phase timestamps (`declared_at`, `triaged_at`, `contained_at`, `eradicated_at`, `recovered_at`, `closed_at`, `assessed_at`, `sealed_at`, `decided_at`, `sent_at`, `qualified_at`, `effectiveness_reviewed_at`) are stamped by the `transition_to()` override **only**. They are excluded from every `ModelForm`, are `read_only` in every serializer, are absent from every MCP `writable_fields` list, and are cleared only by their matching reopen transition. Prevention at application level, detection via `HistoricalRecords`. |
| RG-INC-13 | `awareness_at` is the single legal clock anchor and is distinct from `detected_at`. It defaults to `detected_at` on first save when left blank, must be `>= detected_at`, and requires a non-blank `awareness_justification` whenever it postdates detection. Statutory deadlines are **never** derived from `detected_at`. |
| RG-INC-14 | Closing an incident is refused unless its [PostIncidentReview](post-incident-review.md) is in `approved` or `effectiveness_verified`, **and** every [IncidentNotification](incident-notification.md) has `decision != undecided`, **and** every [IncidentEvidence](incident-evidence.md) item has left the `collected` step. Closure additionally requires `incidents.incident.approve`, a mandatory comment and a confirmation trigger. |
| RG-INC-15 | Reclassification as a mere event is reachable only up to `investigating`, requires `approve` plus a mandatory comment, and is refused when any notification already carries a `sent_at`. Once an incident is contained, it happened; and you cannot un-declare something you have already told a regulator about. |
| RG-INC-16 | Reopening a closed incident requires `approve` and a mandatory comment, clears `closed_at`, and appends a timeline entry. The original closure remains in the lifecycle history. |
| RG-INC-17 | An incident with `is_exercise = True` runs the identical lifecycle with identical gates but is excluded from every KPI, indicator, report, calendar deadline, kanban bucket and dashboard count (an `.exclude(is_exercise=True)` on the querysets, never a lifecycle state), and **never instantiates regulatory notification obligations**. Its closure updates `IncidentResponsePlan.last_exercise_date`, which is the A.5.24 plan-testing evidence and is maintained there and nowhere else. |
| RG-INC-18 | `personal_data_involved = True` forces the `gdpr_art33_authority` obligation to be instantiated at triage regardless of the plan's configured regimes, and creates the [PersonalDataBreach](personal-data-breach.md) record : saved, then transitioned to `under_qualification` in the same atomic block. Clearing the flag never deletes that record : a breach is ruled out through the `not_a_breach` transition, never by unchecking a box. |
| RG-INC-19 | When triage produces zero notification obligations, `personal_data_involved` is `False` **and** `is_exercise` is `False`, a non-blank `Incident.no_obligation_justification` is mandatory. A missing regime or template must never read as compliance on a green dashboard. An exercise, which by RG-INC-17 always produces zero obligations, is explicitly exempt : an unqualified gate would force a legal justification for owing nothing on every drill. |
| RG-INC-20 | Evidence acquisition metadata (`file`, `content_hash`, `hash_algorithm`, `collected_at`, `collected_by`, `collection_method`) is immutable once `sealed_at` is set : `save()` re-reads the stored row and raises `ValidationError` naming the field on any attempted change, so the guard covers the form, the serializer, the MCP update tool and the Django admin alike. Prevention at application level, detection via `HistoricalRecords`. |
| RG-INC-21 | Sealing evidence requires a non-blank `content_hash` **and** a non-blank `collection_method`. There is no path to `secured` without both, on any surface : an artefact with a perfect hash and no stated method is a file, not evidence. |
| RG-INC-22 | Every [IncidentEvidence](incident-evidence.md) lifecycle transition that is a **handling act** appends exactly one [EvidenceCustodyEvent](evidence-custody-event.md) with `source = lifecycle`, inside the transition's transaction; the two `Retain` edges are the single stated exception and append nothing, because moving an item into its retention period changes how the platform governs it, not who is holding it. Acts that are not state changes (transfer, access, copy, integrity verification, return) are recorded by hand. Custody rows are append-only, ordered by `occurred_at`, and each `occurred_at` must be `>=` the previous row's. `transferred` / `released` / `returned` / `destroyed` require a named counterparty. There is **no** cryptographic hash chain : nothing in Cairn hash-chains anything, an HMAC keyed on `SECRET_KEY` would be invalidated wholesale by a routine key rotation, and a chain would in any case prove something about the database rather than about the artefact in the vault. |
| RG-INC-23 | An integrity verification recording `integrity_ok = False` sets the parent's `last_integrity_check_ok`, raises a danger badge on the evidence row, on the incident detail page and on the dashboard widget, and fires `EVIDENCE_INTEGRITY_FAILED` to the evidence collector, the incident manager and the holders of `incidents.evidence.approve` in scope. A verification that could **not read** the artefact is not a verification failure : `integrity_ok` stays null, `last_integrity_check_ok` is left unchanged, the failure to read is recorded in `notes`, and an operational alert goes to whoever can remount a volume. |
| RG-INC-24 | Destroying evidence requires `incidents.evidence.approve`, a mandatory comment, a confirmation, `legal_hold = False` and a `retention_until` strictly in the past. Destruction stamps `destruction_authorised_by`, deletes the stored artefact while retaining `original_filename`, `file_size`, `content_hash` and `hash_algorithm`, and appends a final `destroyed` custody event. The `IncidentEvidence` row itself is **never** deleted. |
| RG-INC-25 | An obligation whose decision is `not_required` must carry a non-blank `decision_rationale` (DB `CheckConstraint`), and reaching that step requires `incidents.notification.approve`, a mandatory comment, a named `decided_by` and a `decided_at`. This is the GDPR Art. 33(1) omission judgement, and it is the single most audited sentence in a breach file. |
| RG-INC-26 | Recording an actual filing requires only `incidents.notification.update`. Only the transitions that declare an obligation **extinguished** (`not_required`, and the archive bookend) require `approve`, so the operator on a 24-hour clock is never blocked waiting for an approver : a late filing is a breach, an early one never is. |
| RG-INC-27 | `due_at` is recomputed in `save()` from the resolved anchor plus `deadline_hours` **only while `first_submitted_at` is null**, and is never editable directly on any surface. Obligations with `no_fixed_deadline = True` carry a null `due_at`, are never counted late, and are surfaced in a dedicated *no statutory deadline* bucket rather than hidden. Never fabricate a deadline for an obligation that legally has none. |
| RG-INC-28 | Overdue is always **derived** (`due_at < now` AND `sent_at IS NULL` AND the step is not terminal), never stored as a status. Lateness is **frozen once** : `first_submitted_at`, `late_by` and `NotificationFiling.was_late` are stamped at the first filing and never recomputed, so a later correction of `awareness_at` can never silently un-breach a filed record. |
| RG-INC-29 | A notification's `content`, `channel` and `sent_at` are write-once once `sent_at` is set. An amendment is an **additional** [NotificationFiling](notification-filing.md) with `is_correction = True` and, where it replaces a statement, `supersedes`, on the **same** obligation, so the same-obligation relationship is never lost and the register never shows two answers to one duty. |
| RG-INC-30 | Obligation terms generated from a [ReportingObligationTemplate](reporting-obligation-template.md) (`regime`, `recipient_kind`, `obligation_reference`, `clock_anchor`, `deadline_hours`, `no_fixed_deadline`, `content_requirements`, `authority`) are **snapshotted** at creation and are never rewritten by a later template edit; the `template` foreign key is `PROTECT`. Generation only considers templates **and** authorities in a `reportable()` lifecycle state, never an `is_active` boolean literal. |
| RG-INC-31 | Exactly one [PostIncidentReview](post-incident-review.md) per incident (`OneToOneField`, `PROTECT`), created automatically on entry to the `post_incident_review` step : saved, then transitioned to `scheduled` in the same atomic block. Its `scopes` are copied from the incident at creation **and** re-synced by `Incident.save()` whenever the incident's scopes change, so the review can never drift out of scope alignment with the incident it reviews. |
| RG-INC-32 | Leaving `in_progress` on a review requires a non-blank `root_cause` and `similar_incidents_checked = True`; reaching `approved` additionally requires an `effectiveness_review_date`; reaching `effectiveness_verified` requires `incidents.review.approve`, a mandatory comment, a non-blank `effectiveness_verdict` and an `effectiveness_reviewed_by`. This is the ISO 27001 clause 10.2 d) and f) record. |
| RG-INC-33 | No automated RTO / MTD breach claim is made anywhere in the module. `assets.EssentialAsset.max_tolerable_downtime`, `recovery_time_objective` and `recovery_point_objective` are free-text `CharField(max_length=100)` values such as `4 hours`, so the register reports the measured `outage_duration` and lists each affected asset's declared objective **verbatim, side by side**, and declines to conclude. Migrating those three fields to `DurationField` is recorded as an m2 prerequisite, not smuggled into this module. |
| RG-INC-34 | A nonconformity raised by a post-incident review is a `compliance.Finding` with `source = incident` and `incident = <incident>`, `assessment` left null : the **one** ISO 27001 clause 10.2 register. A risk revealed by an incident is a `risks.Risk` with `risk_source = RiskSourceType.INCIDENT`, `source_entity_type = "incidents.Incident"` and `source_entity_id = incident.pk`, reusing the existing generic back-pointer. No new foreign key on `Risk`, and no second nonconformity model. |
| RG-INC-35 | Corrective work is recorded exclusively as `compliance.ComplianceActionPlan` rows linked from `PostIncidentReview.corrective_action_plans`, reusing that model's eight-step lifecycle, owner and assignees, target date, progress, cost estimate and per-transition audit row. [IncidentResponseAction](incident-response-action.md) exists **only** for in-incident operational steps and carries a plain `status` column, never a lifecycle : during the incident it is a response action, because of the incident it is an action plan. |
| RG-INC-36 | An incident realising a risk that carries an **active** `risks.RiskAcceptance` forces that acceptance under review : the daily sweep notifies the acceptance owner and sets `review_date` on every linked risk still in a reportable step. This is a derived query hung off the existing `expire_risk_acceptances` sweep, not a stored edge. |
| RG-INC-37 | Every report, KPI, indicator, calendar feed, kanban bucket and link picker filters through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. No incident, event, evidence, notification, review or breach state literal appears anywhere outside `incidents/constants.py`, and the prohibition covers the plain `ResponseActionStatus` enum as much as it covers the lifecycle step codes. |
| RG-INC-38 | Scope tenancy : [Incident](incident.md), [SecurityEvent](security-event.md), [IncidentResponsePlan](incident-response-plan.md) and [PostIncidentReview](post-incident-review.md) carry `scopes` (`ScopedModel`). [IncidentEvidence](incident-evidence.md), [IncidentNotification](incident-notification.md), [IncidentTimelineEntry](incident-timeline-entry.md), [IncidentResponseAction](incident-response-action.md) and [PersonalDataBreach](personal-data-breach.md) inherit the incident's scope through `scope_parent_lookup = "incident__scopes"` and are never independently scoped; grandchildren chain it (`evidence__incident__scopes`, `notification__incident__scopes`). [ReportingAuthority](reporting-authority.md) and [ReportingObligationTemplate](reporting-obligation-template.md) are deliberately instance-wide and set `scope_filtered = False` explicitly. See §5. |
| RG-INC-39 | Permission features are exactly six and never grow : `incident`, `security_event`, `evidence`, `notification`, `review` and `response_plan`, each with the five standard `create` / `read` / `update` / `delete` / `approve` actions only. The catalogue entities gate on `response_plan` and [PersonalDataBreach](personal-data-breach.md) on `notification`. No custom verbs, so the six `SYSTEM_GROUPS` suffix lambdas grant the module unchanged and the group matrix screen, which renders a hardcoded action list, displays every codename. |
| RG-INC-40 | The daily `escalate_incident_deadlines` management command sweeps unfiled notification obligations whose `due_at` is inside the alert window or already past, overdue [IncidentResponseAction](incident-response-action.md) rows, and incidents sitting in `detected` or `triaged` past the severity SLA. It takes `--dry-run`, uses `timezone.localdate()`, excludes terminal steps and statuses, and iterates with a per-row `save()` (never `QuerySet.update()`) so `HistoricalRecords` captures every change. |
| RG-INC-41 | Confirming a personal data breach requires the full GDPR Art. 33(3)(a)-(d) set (`nature`, `dpo_contact`, `likely_consequences`, `measures_taken`, all non-blank), a **non-null** `high_risk_to_rights` for the Art. 34(1) determination, a non-blank `article_34_exemption_justification` whenever an Art. 34(3) ground is claimed, plus `incidents.notification.approve` and a mandatory comment. A confirmed breach with an empty *likely consequences* is a filing that cannot be drafted, and `None` is not a verdict. |

---

## 3. Lifecycles

The module registers **six** lifecycles of its own in `incidents/lifecycles.py`, runs **three** entities on the core `default` 4-state lifecycle, and gives **four** entities no lifecycle at all.

| Lifecycle | Entity | Authoring | Steps |
|---|---|---|---|
| `security_event` | [SecurityEvent](security-event.md) | generated from transition constants | `draft`, `reported`, `under_assessment`, `confirmed_incident`, `confirmed_weakness`, `discarded`, `archived` |
| `incident` | [Incident](incident.md) | **hand-authored** `Step` / `Transition` lists | `draft`, `detected`, `triaged`, `investigating`, `contained`, `eradicated`, `recovered`, `post_incident_review`, `closed`, `reclassified`, `archived` |
| `incident_evidence` | [IncidentEvidence](incident-evidence.md) | **hand-authored** | `draft`, `collected`, `secured`, `analysed`, `retained`, `released`, `destroyed`, `archived` |
| `incident_notification` | [IncidentNotification](incident-notification.md) | generated | `draft`, `assessed`, `required`, `drafted`, `sent`, `acknowledged`, `not_required`, `archived` |
| `post_incident_review` | [PostIncidentReview](post-incident-review.md) | generated | `draft`, `scheduled`, `in_progress`, `submitted`, `approved`, `effectiveness_verified`, `cancelled`, `archived` |
| `personal_data_breach` | [PersonalDataBreach](personal-data-breach.md) | generated | `draft`, `under_qualification`, `confirmed`, `documented`, `not_a_breach`, `archived` |
| core `default` | [IncidentResponsePlan](incident-response-plan.md), [ReportingAuthority](reporting-authority.md), [ReportingObligationTemplate](reporting-obligation-template.md) | core | `draft`, `pending`, `validated`, `archived` |
| none | [IncidentTimelineEntry](incident-timeline-entry.md), [EvidenceCustodyEvent](evidence-custody-event.md), [NotificationFiling](notification-filing.md), [IncidentResponseAction](incident-response-action.md) | n/a | n/a |

Four cross-cutting properties apply to every lifecycle-bearing entity in the module, and each is argued in full in the entity file that owns it.

**Registration fails silently if forgotten.** `core/lifecycle.py` `lifecycle_name_for()` resolves `LIFECYCLE_NAME` only `if name and name in LIFECYCLE_REGISTRY`. An `incidents/apps.py` whose `ready()` does not import `incidents.lifecycles` therefore downgrades every model in the module to the core 4-state lifecycle, quietly, in tests as well as in production, with no error anywhere. The module ships a test per entity asserting `Model.get_lifecycle().name == "<expected>"` so the omission fails loudly.

**The archive and restore bookends are hand-declared everywhere.** `lifecycle_from_state_flags()` appends `ANY -> archived` and `archived -> draft` with **no `permission_action` and no `requires_comment`**, and `user_can_perform()` allows any transition whose `permission_action` is empty. With a `deletable = True` draft step, that pair is an **archive -> restore -> delete** path open to anyone who can reach the transition endpoint : on [IncidentEvidence](incident-evidence.md) it destroys a sealed A.5.28 row, on [IncidentNotification](incident-notification.md) it erases the record of a decision not to notify, on [PersonalDataBreach](personal-data-breach.md) it destroys a GDPR qualification. Every lifecycle the module declares therefore lists `archived` **explicitly** among its steps so nothing is auto-wired, hand-declares `ANY -> archived` with `permission_action = "approve"` and `requires_comment = True`, hand-declares `archived -> draft` with `permission_action = "approve"`, hand-declares the `draft -> <first domain step>` entry edge, and refuses the restore edge in `transition_to()` for any row whose `core.LifecycleEvent` history records a step other than `draft` or `archived`. The three entities on the core `default` lifecycle need none of this : its archive edge already carries `approve` and it declares **no restore transition at all**. Do not add one.

**Nothing is ever created in a domain step.** `BaseModel.save()` calls `_ensure_initial_step()` and `Lifecycle.initial_step` returns the single `StepKind.DRAFT` step, so every insert lands in `draft`. Assigning `workflow_state = "<domain step>"` at insert would stick, because the snap only fires on a blank or unknown value, but it would leave **no `core.LifecycleEvent` row**, so the object would have no recorded entry into the register, which is exactly the audit trail the module exists to produce. Every auto-creation path therefore does, inside one `transaction.atomic()` block :

```python
obj = Model(...)
obj.save()
obj.transition_to("<domain step>", user, enforce_permission=False)
```

`enforce_permission=False` is correct on these paths : the permission was already checked on the **parent** transition the user actually performed, and the child row is a consequence of it, not a separate act. The three cases are the notification obligations moved to `assessed` at triage, the [PostIncidentReview](post-incident-review.md) moved to `scheduled` when the incident enters the review phase, and the [PersonalDataBreach](personal-data-breach.md) moved to `under_qualification`. Regression tests assert both that the generators produce the domain step with a matching `LifecycleEvent`, and that a bare `Model.objects.create(...)` does **not**.

**Two lifecycles are hand-authored on purpose.** `CLAUDE.md` prescribes generating a lifecycle from its transition constants, and four of the module's six follow that rule. `incident` and `incident_evidence` do not, for a reason the generator cannot accommodate : `lifecycle_from_state_flags()` builds every `Step(...)` with no `triggers=` argument and its tuple contract has no slot for one, so a generated lifecycle **physically cannot** declare the confirmation gate that incident closure and evidence destruction rest on. Both are declared as explicit `Step` and `Transition` lists, with the step codes still exported as constants from `incidents/constants.py` so RG-INC-37 holds. Two honest caveats : **no lifecycle in Cairn uses `Trigger` today**, so the `opts.confirm` branch of `templates/includes/lifecycle_stepper.html` has never run and this module is its first user, shipping an explicit test of that path in both themes and at mobile width; and triggers **do** survive the `LifecycleDefinition` round-trip, so it is only the generator that cannot express them. The confirmation is a UX affordance, not a security control : the server-side gates apply identically to a DRF or MCP caller that never sees a modal.

---

## 4. Permissions and access control

### 4.1 The six-feature cap (RG-INC-39)

Module `incidents` in `accounts/constants.py` `PERMISSION_REGISTRY`, with `MODULE_LABELS` gaining `"incidents": _("Incidents")`. Codenames follow the platform convention `module.feature.action`. **Six features times five standard actions is thirty codenames, and the number is capped for the life of the module.**

| Codename family | Covers | What `approve` gates |
|---|---|---|
| `incidents.incident.create` / `.read` / `.update` / `.delete` / `.approve` | [Incident](incident.md), and by delegation [IncidentTimelineEntry](incident-timeline-entry.md) and [IncidentResponseAction](incident-response-action.md) | Close, reopen after closure, reclassify, archive, restore |
| `incidents.security_event.create` / `.read` / `.update` / `.delete` / `.approve` | [SecurityEvent](security-event.md) | Discard an event : the A.5.25 *this was not an incident* verdict |
| `incidents.evidence.create` / `.read` / `.update` / `.delete` / `.approve` | [IncidentEvidence](incident-evidence.md), and by delegation [EvidenceCustodyEvent](evidence-custody-event.md) | Release to a counterparty, destroy, archive, restore |
| `incidents.notification.create` / `.read` / `.update` / `.delete` / `.approve` | [IncidentNotification](incident-notification.md), [PersonalDataBreach](personal-data-breach.md), [NotificationFiling](notification-filing.md) | Decide **not** to notify, confirm or rule out a breach, complete or reopen the Art. 33(5) record. Recording an actual filing needs only `update` (RG-INC-26) |
| `incidents.review.create` / `.read` / `.update` / `.delete` / `.approve` | [PostIncidentReview](post-incident-review.md) | Approve the review and record the effectiveness verdict |
| `incidents.response_plan.create` / `.read` / `.update` / `.delete` / `.approve` | [IncidentResponsePlan](incident-response-plan.md), [ReportingAuthority](reporting-authority.md), [ReportingObligationTemplate](reporting-obligation-template.md) | Put a plan, an authority or a legal template **into force**, and archive it |

Promotion of an event to an incident additionally requires `incidents.incident.create`.

### 4.2 Why the cap matters : the six system group lambdas grant it unchanged

`SYSTEM_GROUPS` in `accounts/constants.py` assigns permissions to the six system roles through **suffix filters on the codename**, not through per-module enumeration. Because the module uses only the standard `PermissionAction` verbs and invents no custom one, every group picks up all thirty codenames with no change to the registry :

| Role | Filter | Resulting incidents permissions |
|---|---|---|
| **Super Administrateur** | everything | All thirty. |
| **Administrateur** | everything except `system.admin_django.access` | All thirty. |
| **RSSI / DPO** | suffixes `.read`, `.create`, `.update`, `.approve` (plus `.access`, `.validate`, `.close`, `.cancel`) | `read` + `create` + `update` + `approve` on all six features, **no `delete`**. This is the correct set : the DPO pronounces the breach verdict, the CISO puts the plan into force, and neither hard-deletes an audit record. |
| **Contributeur** | suffixes `.read`, `.create`, `.update`, `.implement`, not `system.*` | `read` + `create` + `update`. Responders declare, triage, investigate, collect evidence, draft filings and record them, but never close an incident, never discard an event, never destroy evidence and never rule out an obligation. |
| **Auditeur** | suffix `.read` | Read on all six features, which is exactly the set an auditor needs and no more. |
| **Lecteur** | suffix `.read`, not `system.*` | Read on all six features. |

The `approve` / non-`approve` split is the module's governance in one line : the person who works the incident is not the person who declares it over, declares an obligation extinguished, or destroys the evidence.

The group matrix screen in `accounts/views.py` renders a **hardcoded action list**, so a custom verb would exist in the database and be invisible in the UI that administers it. That is the second reason the cap is a rule and not a preference.

### 4.3 `workflow_perm_namespace` overrides

`BaseModel` derives the permission namespace from `app_label.model_name`. That is correct for exactly one entity in this module. Every other lifecycle-bearing model **must** override it, because the derived namespace would match no feature in `PERMISSION_REGISTRY` and every lifecycle permission check would then silently evaluate against a codename nobody holds.

| Model | Derived (wrong) | `workflow_perm_namespace` |
|---|---|---|
| `Incident` | `incidents.incident` | **not overridden** : already correct |
| `SecurityEvent` | `incidents.securityevent` | `incidents.security_event` |
| `IncidentEvidence` | `incidents.incidentevidence` | `incidents.evidence` |
| `IncidentNotification` | `incidents.incidentnotification` | `incidents.notification` |
| `PostIncidentReview` | `incidents.postincidentreview` | `incidents.review` |
| `IncidentResponsePlan` | `incidents.incidentresponseplan` | `incidents.response_plan` |
| `ReportingAuthority` | `incidents.reportingauthority` | `incidents.response_plan` |
| `ReportingObligationTemplate` | `incidents.reportingobligationtemplate` | `incidents.response_plan` |
| `PersonalDataBreach` | `incidents.personaldatabreach` | `incidents.notification` |

### 4.4 The accounts data migration

`accounts/migrations/0056_add_incidents_permissions.py` creates the thirty `Permission` rows and attaches them to the six system groups. It copies `accounts/migrations/0053_add_certificate_permissions.py` verbatim in shape : self-contained constants, an `_ends()` helper reproducing the group lambdas, `get_or_create(is_system=True)`, a `Group.DoesNotExist` guard, and a reverse operation that deletes the codenames. It depends on `("accounts", "0055_alter_accesslog_event_type")`.

**The `PERMISSION_REGISTRY` entry alone makes the test suite pass**, because `conftest.py` seeds groups from `get_all_permissions()`. The migration must therefore land in the same commit, or a production database will have a green test suite and no grants.

The `compliance.finding` feature introduced by the prerequisite (§1.5) needs its **own** accounts data migration in its own pull request, for exactly the same reason.

---

## 5. Scope tenancy, and the security fix this module forces

`ScopeFilterMixin` (`accounts/mixins.py`) and `ScopeFilterAPIMixin` (`accounts/api/mixins.py`) already honour a model-level `scope_parent_lookup`, so list views and viewsets filter a non-`ScopedModel` child correctly by declaring one. **Three other call sites do not, and they leak every non-`ScopedModel` child across scopes today, for the existing modules as well as for this one.** All three guard scope with `hasattr(obj, "scopes")`, which is false for exactly the models that need the parent lookup.

This is a **core** change in the module's pull request, not an incidents-app detail : two of the three endpoints are generic and shared by every module. It is logged under a **`### Security`** entry in `CHANGELOG.md`.

| Call site | Current behaviour | Required change | What is reachable without it |
|---|---|---|---|
| `mcp/tools.py` `_filter_by_scopes()` | Handles `context.Scope`, then a direct `scopes` M2M, then `return qs` **unfiltered**. There is no `scope_parent_lookup` equivalent at all. | Extend the signature to accept a `parent_lookup`, and thread a `scope_parent_lookup` argument through `_register_crud()`, `_list_handler()`, `_get_handler()`, `_transition_handler()` and `_allowed_transitions_handler()`. | `list_incident_evidence`, `list_evidence_custody_events`, `list_incident_notifications`, `list_overdue_incident_notifications`, `list_incident_timeline_entries`, `list_incident_response_actions`, `list_personal_data_breaches` and `list_notification_filings` return **every row on the instance** to any holder of the corresponding `.read`. That includes evidence hashes, storage locations, TLP:RED handling caveats, custody counterparties named at other organisations, verbatim regulatory filing content, omission rationales, and breach data-subject counts. |
| `core/workflow_views.py` `WorkflowTransitionView` | Guards with `if allowed_scopes is not None and hasattr(obj, "scopes")` | Honour a model-level `scope_parent_lookup` attribute in the same guard. | The evidence `release` and `destroy` transitions, the notification `not_required` decision (the GDPR Art. 33(1) omission), and the breach `confirm` / `not_a_breach` verdicts are **performable cross-scope**. A user scoped to one subsidiary can destroy another subsidiary's sealed evidence with a valid `approve` permission and a perfectly clean audit trail showing they were entitled to. |
| `core/history_views.py` `HistoryPartialView` | The same `hasattr(obj, "scopes")` guard | The same change. | The full field-level history of an out-of-scope evidence row, obligation, breach qualification, custody row, timeline entry, response action or filing is readable, including every value the acquisition metadata or the omission rationale ever held. |

Because the two web endpoints are generic, the guard is fixed once and every non-`ScopedModel` child in the platform benefits. The module ships tests asserting that a user scoped out of an incident receives a 404 from `workflow:transition` and from the history partial for its evidence and its obligations, and an empty list from `list_incident_evidence`, `list_evidence_custody_events` and `list_personal_data_breaches`.

The catalogue entities are the deliberate exception : [ReportingAuthority](reporting-authority.md) and [ReportingObligationTemplate](reporting-obligation-template.md) carry neither `scopes` nor `scope_parent_lookup`, because the CNIL is the CNIL for every scope of the ISMS. Their viewsets and MCP registrations set `scope_filtered = False` **explicitly** rather than inheriting it by omission, so the choice reads as a decision in review instead of looking like the same oversight this fix repairs.

---

## 6. API conventions

Base path **`/api/v1/incidents/`**, mounted in `core/urls.py`. `incidents/api/urls.py` declares `app_name = "incidents-api"` and a `DefaultRouter`.

### 6.1 Router registrations

`incidents`, `security-events`, `response-plans`, `evidence`, `custody-events`, `notifications`, `response-actions`, `timeline-entries`, `post-incident-reviews`, `reporting-authorities`, `obligation-templates`, `personal-data-breaches`, `notification-filings`.

### 6.2 The `_IncidentViewSet` base

Permissions follow the **newest** module precedent, `trust_center/api/views.py` `_ManagedViewSet`, and not the older habit of importing another app's `ModulePermission` subclass. `ContextPermission` is the context app's subclass and its only content is an extra action map; importing it into a new module borrows another domain's vocabulary for no benefit.

```python
class _IncidentViewSet:
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "incidents"
    custom_action_map = {"transition": "update"}
```

Every viewset in the module extends this base and sets an explicit `permission_feature`. Two viewsets add their own actions to the map rather than redefining it, because the shared base must stay identical across all thirteen :

- `IncidentEvidenceViewSet` extends it with `{"verify-integrity": "update", "download": "read"}`;
- `IncidentNotificationViewSet` and `NotificationFilingViewSet` extend it with `{"proof": "read"}`.

### 6.3 Viewset stack, in the house order

`BatchCreateMixin`, `ScopeFilterAPIMixin`, `LifecycleAPIMixin`, `HistoryAPIMixin`, `CreatedByMixin`, `viewsets.ModelViewSet`.

- `LifecycleAPIMixin` is **dropped** on the four entities that run no lifecycle ([IncidentTimelineEntry](incident-timeline-entry.md), [EvidenceCustodyEvent](evidence-custody-event.md), [IncidentResponseAction](incident-response-action.md), [NotificationFiling](notification-filing.md)), so no `transition/` route is generated for them.
- `ScopeFilterAPIMixin` declares `scope_parent_lookup` on every child : `incident__scopes`, `evidence__incident__scopes`, `notification__incident__scopes`. The catalogue viewsets set `scope_filtered = False` explicitly.

### 6.4 Common endpoints and conventions

| Route | Notes |
|---|---|
| `GET/POST /<resource>/` | List with per-entity filters (`incidents/api/filters.py`), search (`?search=`), ordering (`?ordering=`) and lifecycle filtering (`?workflow_state=a,b`). |
| `POST /<resource>/batch/` | `BatchCreateMixin` : max 100 items, non-atomic, per-item `{index, status, id, reference}`. |
| `GET/PUT/PATCH/DELETE /<resource>/<uuid>/` | `DELETE` succeeds only in a `deletable_states()` step; otherwise `BaseModel.delete()` raises and the endpoint returns **409**. |
| `GET/POST /<resource>/<uuid>/transition/` | `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`, so **every gate in §2 applies identically to an API caller**. A forbidden transition returns 403, an invalid one 400. |
| `GET /<resource>/<uuid>/history/` | `core.history.build_timeline`, merging `LifecycleEvent` and `HistoricalRecords`. |
| `GET /evidence/<uuid>/download/` | The **only** way to retrieve an artefact. Resolves the row, checks `incidents.evidence.read` and the caller's scopes through `incident__scopes`, then streams with `Content-Disposition: attachment`. 404 for a registered-by-reference row and for a destroyed one. |
| `POST /evidence/<uuid>/verify-integrity/` | Runs the verification and returns the **three-way** outcome explicitly, so a caller can tell a tamper from a missing volume. |
| `GET /notifications/<uuid>/proof/` and `GET /notification-filings/<uuid>/proof/` | Permission-checked and scope-checked proof bytes. `proof_file_content` never appears in a list or detail payload. |

**Append-only entities restrict `http_method_names` at the routing layer**, not only in the serializer : `timeline-entries` and `custody-events` are create, list and retrieve only, and `notification-filings` adds exactly one `PATCH` route that accepts **only** the three completion fields (`outcome`, `acknowledged_at`, `external_reference`) and rejects every other key with a 400 rather than ignoring it.

Two serializers per entity : `<Entity>Serializer` (full, with `read_only_fields` covering `id`, `reference`, `created_by`, `created_at`, `updated_at`, `version` and every transition-stamped timestamp) and `<Entity>ListSerializer` for the index, switched in `get_serializer_class()` on `self.action == "list"`. Lifecycle entities expose `status = CharField(source="workflow_state", read_only=True)`. Foreign-key display names are exposed as `*_name` read-only fields backed by a model `@property`. File payloads and `proof_file_content` never appear in any serializer.

---

## 7. MCP tools

`_register_incidents_tools(server)` is added to `register_all_tools()` and resolves every model through `_get_model("incidents", ...)` rather than a direct import.

### 7.1 Generated CRUD

`_register_crud()` generates the nine standard tools (`list_*`, `get_*`, `create_*`, `batch_create_*`, `update_*`, `delete_*`, `transition_*`, `*_allowed_transitions`, `get_*_history`) for :

| Registration | Permission namespace | Scope argument |
|---|---|---|
| `incident` | `incidents.incident` | `scopes` M2M |
| `security_event` | `incidents.security_event` | `scopes` M2M |
| `incident_response_plan` | `incidents.response_plan` | `scopes` M2M |
| `post_incident_review` | `incidents.review` | `scopes` M2M |
| `incident_evidence` | `incidents.evidence` | `scope_parent_lookup="incident__scopes"` |
| `incident_notification` | `incidents.notification` | `scope_parent_lookup="incident__scopes"` |
| `personal_data_breach` | `incidents.notification` | `scope_parent_lookup="incident__scopes"` |
| `incident_response_action` | `incidents.incident`, `has_approve=False` | `scope_parent_lookup="incident__scopes"` |
| `reporting_authority` | `incidents.response_plan` | `scope_filtered=False` |
| `obligation_template` | `incidents.response_plan` | `scope_filtered=False` |

`incident_response_action` generates no `transition_*` and no `*_allowed_transitions` tool : the child row runs no lifecycle.

### 7.2 Bespoke tools

| Tool | Permission | Purpose |
|---|---|---|
| `declare_incident_from_event` | `incidents.security_event.update` **and** `incidents.incident.create` | Runs the whole A.5.25 promotion as one atomic act, so an agent cannot leave a half-promoted event behind. |
| `create_incident_timeline_entry` / `list_incident_timeline_entries` | `incidents.incident.create` / `.read` | Create-and-read only. No update tool, no delete tool : an agent must never rewrite an incident narrative. |
| `create_evidence_custody_event` / `list_evidence_custody_events` | `incidents.evidence.update` / `.read` | Same append-only shape. `source` is forced to `manual` on every MCP-created row. |
| `verify_evidence_integrity` | `incidents.evidence.update` | Appends an `integrity_verified` custody act with the **measured** digest and returns the three-way verdict, rather than letting an agent assert one. |
| `list_overdue_incident_notifications` | `incidents.notification.read` | The *are we late* question answered in one call : obligation, incident, regime, recipient, `due_at`, hours overdue, owner. The single highest-value read tool in the module. |
| `record_notification_filing` | `incidents.notification.update` | Creates the [NotificationFiling](notification-filing.md) and freezes `first_submitted_at`, `late_by` and `was_late` atomically, so a transmission can never be recorded without the lateness verdict that goes with it. |
| `record_filing_outcome` | `incidents.notification.update` | Sets `outcome`, `acknowledged_at` and `external_reference` once, and refuses everything else. |

### 7.3 Conventions and the HELP_TEXT trap

Every enum field carries an explicit `enum` list in `field_overrides`; every HTML field uses `_html_field()`; every foreign-key id argument carries a description naming its lookup tool (`Use list_suppliers to get valid IDs`). Transition-stamped timestamps never appear in `writable_fields` : a decision is a transition, never a field write. The `file` payload of an evidence item and the `proof_file_content` bytes are neither readable nor writable through MCP.

`mcp/tools.py` `HELP_TEXT` gains the reference-prefix entries `Incident=INCD`, `SecurityEvent=EVNT`, `IncidentResponsePlan=IRPL`, `IncidentEvidence=EVID`, `IncidentNotification=INOT`, `PostIncidentReview=PIRV`, `IncidentResponseAction=IRAC`, `ReportingAuthority=RGAU`, `ReportingObligationTemplate=ROBT`, `PersonalDataBreach=PDBR`, `NotificationFiling=NFIL`, and a new `TOPIC_INCIDENTS` constant joins `ALL_TOPICS` with a per-entity *Writable fields / enum values / Filters / Ref prefix* section, plus the topic name in the help tool's description and its `topic` property.

> **Do not copy a neighbouring `HELP_TEXT` line when adding these.** The existing block **mis-states two prefixes** : it says `Indicator=INDI` where the model declares `INDC`, and `ActionPlan=ACTPL` where the model declares `CAPL`. Read each prefix off the model's `REFERENCE_PREFIX`, and note that the correct `INDC` is one letter-order away from this module's `INCD`.

`assistant/catalog.py` gains read-only `ToolSpec` entries for `list_incidents`, `get_incident`, `list_incident_notifications` and `list_security_events`, with `allowed_args`, `title_fields`, `summary_fields = ("incident_manager_name", "severity", "status")` and `detail_route = "incidents:incident-detail"`. Without them Ask Cairn cannot reach the register at all.

---

## 8. Notifications

New `NotificationType` values plus matching `notify_*` helpers in `accounts/notifications.py`, following `notify_lifecycle_submitted` : render per recipient under `translation.override(recipient.language)`, create the rows in the same transaction, then `transaction.on_commit(_deliver)` so a rolled-back transition sends nothing. **No new notification model** : `accounts.Notification` already targets any object through a `GenericForeignKey`, and naming the route `incidents:incident-detail` makes `_target_url` resolve with no special casing. A matching accounts migration alters the `notification_type` choices.

| Event | Recipients | Channel |
|---|---|---|
| `INCIDENT_DECLARED` : the `draft -> detected` transition | Holders of `incidents.incident.read` in the incident's scopes, and the response plan owner | In-app, email |
| `INCIDENT_ASSIGNED` : `incident_manager` set or changed | The new incident manager | In-app, email |
| `INCIDENT_SEVERITY_RAISED` : `severity` moves above `initial_severity` after triage | The incident manager, the response plan owner, holders of `incidents.incident.approve` in scope | In-app, email |
| `NOTIFICATION_DEADLINE_APPROACHING` : daily sweep, `decision = required`, `sent_at` null, `due_at` inside the alert window | The incident manager, holders of `incidents.notification.approve` in scope | In-app, email |
| `NOTIFICATION_OVERDUE` : same sweep, `due_at` already past | As above, plus the response plan owner | In-app, email |
| `EVIDENCE_INTEGRITY_FAILED` : a custody event records `integrity_ok = False` | The evidence collector, the incident manager, holders of `incidents.evidence.approve` in scope | In-app, email |
| `POST_INCIDENT_REVIEW_DUE` : `scheduled_date` or `effectiveness_review_date` falls due | The facilitator and the participants | In-app |
| `RISK_REVIEW_TRIGGERED_BY_INCIDENT` : a review sets `risk_reassessment_required`, or an incident realises a risk carrying an active `RiskAcceptance` (RG-INC-36) | The risk owner and the acceptance owner | In-app, email |

`INCIDENT_SEVERITY_RAISED` is not only a message : it is the **second trigger point that re-runs obligation generation**, because a severity raise can cross a template's `min_severity` floor and start a 24-hour NIS2 clock that did not exist an hour earlier. Its absence is a missed statutory deadline, which is why it is an event and not a nightly job.

Exercises (`is_exercise = True`) are excluded from every deadline feed and therefore from the two deadline notifications.

---

## 9. User interface

### 9.1 Principles

Every detail page in this module uses a **strict 2-column card layout with no nav-tabs** : stacked cards and collapsible Bootstrap sections in the left column, a sticky metadata sidebar on the right, per the platform's detail-page doctrine. Every state change is driven by `{% include "includes/lifecycle_stepper.html" %}` fed by `LifecycleStepperMixin`, and by nothing else : **never a status select, never plain buttons**. State badges use `{% workflow_badge obj %}`.

List pages use the full house stack : `LoginRequiredMixin`, `PermissionRequiredMixin`, `ListSummaryMixin`, `PredefinedFilterMixin`, `AdvancedFilterMixin`, `SavedFilterMixin`, `ColumnPreferenceMixin`, `ScopeFilterMixin`, `SortableListMixin`, `ListView`, with `ListSummaryMixin` strictly to the left of `ScopeFilterMixin`, and per-entity `*_FILTER_GROUPS` / `*_TEXT_FILTERS` / `*_COLUMNS` constants declared above the view. Create, update and delete use `HtmxFormMixin` drawer modals.

### 9.2 Pages

| Surface | Left column | Sticky sidebar |
|---|---|---|
| **Incident detail** `/incidents/<uuid>/` | Summary and impact (CIA flags, personal data, TLP, category, `outage_duration` shown beside each affected asset's declared RTO / MTD verbatim with no breach claim); Chronology (append-only, ordered by `occurred_at`, inline add form over HTMX, lifecycle-sourced entries visually distinguished); Response actions; Evidence; Regulatory notifications; Personal data qualification; Post-incident review summary; Linked registers as collapsible sections | State badge, severity with `initial_severity` alongside when they differ, incident manager and reporter, response plan link, the eight clock stamps, scopes, tags, history trigger |
| **Security event detail** | Observation (with the reporting delay computed and shown); Assessment; Promotion targets | State badge, triage decision, reporter avatar **replaced by an "Anonymous report" badge** when `is_anonymous`, never left blank |
| **Evidence detail** | Acquisition; Integrity; Chain of custody with an inline *Record custody act* form | TLP chip, legal hold, `retention_until`, sealed and collected stamps, parent incident |
| **Notification detail** | Obligation with the `content_requirements` checklist rendered **beside** the drafting field; Decision (a prominent full-width card when `decision = not_required`); Filing with the filing history table | The deadline with a live countdown **and the anchor it derives from stated in words**, the *no statutory deadline* or *deadline pending* badge |
| **Post-incident review detail** | Root cause; What went well and what failed; Outcomes; Effectiveness | Facilitator, participants, `held_at` |
| **Response plan detail** | Procedure, classification scale, escalation matrix, reporting channels, evidence procedure, lessons-learned procedure, as collapsible sections | Owner, approver, `effective_from`, `review_date`, `last_exercise_date`, the incidents handled under this plan |
| **Catalogue** (`reporting-authorities`, `obligation-templates`) | Identity and filing channel; the clock rendered as **one plain-language sentence** above the raw fields | Templates and generated obligations, with counts linking to filtered lists |

### 9.3 Platform surfaces

- **Dashboard** : an `open_incidents` widget registered in `DASHBOARD_WIDGETS` with its partial under `templates/dashboard/widgets/`, showing open incidents by severity, overdue notification obligations and any evidence item whose last integrity check failed. Widget partials read context variables, so `GeneralDashboardView.get_context_data` must set them (see §12).
- **Kanban** : an `incident` entity added to `ENTITY_PERMS`, `TYPE_ICONS` and `TYPE_LABELS`, an `_INCIDENT_BUCKETS` step-to-(column, tone) map, a `_build_incidents` builder and its `_BUILDERS` registration.
- **Calendar** : an `incident` category in `ALL_CATEGORIES` with entries for notification `due_at` (as a deadline), review `scheduled_date` and `effectiveness_review_date`, evidence `retention_until` and plan `review_date`, plus the label in `build_upcoming_deadlines`. Exercises are excluded from every feed.
- **Global search** : a `NAVIGATION_ENTRIES` row, an `ACTION_ENTRIES` quick-create gated on `incidents.incident.create`, and category entries for `Incident` and `SecurityEvent` (both scope-filtered automatically, since both carry `scopes`).
- **Accent and navigation** : `MODULE_ACCENTS` gains `"incidents"` (matching the app label; the map stores `trust-center` hyphenated, which is the exception, not the rule), with `--module-accent-incidents` and `--module-accent-incidents-soft` defined in **both** the light and dark token blocks of `base.html`. An unregistered accent is silently dropped. The sidebar section sits between Risk management and Compliance.

### 9.4 Visual checks that are not optional

- The `incident` lifecycle has **three** `StepKind.ARCHIVED` steps and `security_event` has **four**, so the dagre renderer draws three and four detached exits : busier than any existing Cairn lifecycle. Both are checked at desktop and mobile widths in **both** themes before merge.
- The confirmation modal (`opts.confirm` in the stepper template) has **never run** in this codebase. Incident closure and evidence destruction are its first users, and both are exercised in both themes on the same pass.
- Semantic colour is reserved for status, per the brand guidelines : deadline countdowns, status pills and integrity badges use the status palette, and the navy identity colour is never repurposed for them. Trigger-condition badges on a template, which are not statuses, use navy.
- Integrity is rendered as **three** visually distinct states and never two : a success tick for a match, a **danger** badge for a mismatch, and a **warning** *not verifiable* badge for an artefact that could not be read.
- Bootstrap Icons exclusively. The multi-select widgets (assets, sites, suppliers, risks, requirements, categories) and the sticky action bars get explicit mobile-first attention, and the six rich-text fields of the response plan form render as an accordion at small widths.

---

## 10. Technical considerations

### 10.1 Architecture

Dedicated `incidents` Django app. Models in `incidents/models/`, lifecycles in `incidents/lifecycles.py` (registered from `IncidentsConfig.ready()`), state codes and enums in `incidents/constants.py`, web views in `incidents/views.py`, forms in `incidents/forms.py`, REST layer in `incidents/api/` (`serializers.py`, `filters.py`, `views.py`, `urls.py`), the daily sweep in `incidents/management/commands/escalate_incident_deadlines.py`, and `incidents/admin.py` registering every model with `SimpleHistoryAdmin`.

Mounted in the root URL configuration at `/incidents/` (`incidents.urls`, `app_name = "incidents"`) and `/api/v1/incidents/` (`incidents.api.urls`, `app_name = "incidents-api"`).

### 10.2 Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `INCIDENT_EVIDENCE_MAX_UPLOAD_BYTES` | `52428800` (50 MB) | Caps the inline copy of an evidence artefact ([IncidentEvidence](incident-evidence.md) `file`). Enforced in the form, in the serializer **and** in the MCP layer, not only in the reverse proxy, so every surface refuses the same thing. Above the cap an artefact is registered by reference. |
| `INCIDENT_NOTIFICATION_MAX_PROOF_BYTES` | `10485760` (10 MB) | Caps the proof-of-filing bytes on [IncidentNotification](incident-notification.md) and [NotificationFiling](notification-filing.md). Deliberately an order of magnitude below the evidence cap, because these bytes live in a database column rather than on a volume : a portal receipt is a few hundred kilobytes. |

Both are read from the environment in `core/settings.py`.

**The production media-volume requirement.** `IncidentEvidence.file` is the module's only `FileField`, and `core/urls.py` serves `MEDIA_URL` **only under `DEBUG`**. Three consequences are operational requirements of this module, not caveats :

1. **A persistent media volume is required.** `MEDIA_ROOT` defaults to `BASE_DIR / "media"`, which inside a container is ephemeral. A Docker or Kubernetes install must mount a persistent volume there, and it must be backed up **in the same operation** as the database.
2. **The volume must not be served directly.** Because Django does not serve it in production, nothing else should : the reverse proxy must **not** be given a `location /media/` alias for this path. A raw media URL would be an unauthenticated, unscoped, guessable-by-UUID download of forensic material. Downloads go through the permission-checked and scope-checked detail action described in §6.4.
3. **Storage-level protection is the operator's job.** Cairn guarantees the row, the hash and the ledger. It does not guarantee bytes on a volume an administrator can remove. Encryption at rest, restrictive filesystem permissions and volume snapshots are named in the deployment notes as the operator's side of A.5.28.

A restored database paired with a lost volume makes every inline artefact unreadable at once. That is precisely why `verify_evidence_integrity` reports *file missing* as a **distinct** third outcome and never as a hash mismatch (RG-INC-23) : a single infrastructure mistake must not write a permanent chain-of-custody break into the append-only ledger of every evidence item in the platform on a day when nothing was tampered with.

### 10.3 Internationalization

Every user-facing string is wrapped with `_()` / `pgettext_lazy()` in Python or `{% trans %}` in templates, with a French entry in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `manage.py compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`, so a collision breaks CI outright rather than breaking a page.

**Colliding labels use `pgettext_lazy("incident", ...)`** in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po`. The confirmed collisions across the module are : *Closed*, *Draft*, *Archived*, *Approved*, *Cancelled*, *Required*, *Confirmed*, *Retained*, *In progress*, *Planned*, *Done*, *Other*, *Close*, *Incident*, *Evidence*, *Severity*, *Weakness*, *Audit*, *Monitoring*, *Complaint*, *Observation*, *Action*, *Decision*, *System*, *Manual*, *Import* and *Email*. Where a label already exists with the right French for this context (*Jurisdiction*, *Country*, *Order*, *Phone*, *Rejected*, *Superseded*, *Collection method*, *Location*, *Notes*, *Source*, *Actor*, *Recorded at*), the same `msgid` is **reused** and no entry is added : gettext merges the occurrences into one entry with several `#:` references, which is not a duplicate.

**Step and transition labels are the trap, and they must never carry a `msgctxt`.** `lifecycle_to_json()` stringifies each label with `str(...)`, and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy`. A step label carrying a context in code therefore **loses that context** after the `post_migrate` round-trip through `LifecycleDefinition` and resolves to whatever the bare `msgid` maps to. The fix for a colliding step label is a **different English label**, never a context :

| Intended label | Existing bare entry | Decision |
|---|---|---|
| `closed` step "Closed" | "Clôturée" (feminine) | Renamed **"Incident closed"** : a context would be stripped and the step would render with the wrong gender for *incident*. |
| Close transition "Close" | "Fermer" (as in closing a dialog) | Renamed **"Close the incident"**. |
| `retained` step "Retained" | "Retenu" (as in *a retained risk*, i.e. selected) | Renamed **"Retained in custody"** : the bare French means the opposite of a custody state. |
| `draft -> collected` transition "Register" | "Registre" (the noun) | Renamed **"Register the item"** : a transition label must be a verb. |
| `assessed` step | "Assessed" would read as a verdict | Labelled **"To decide"**, which is what the step means. |
| `confirmed` step on a breach | "Confirmé" is taken | Labelled **"Confirmed breach"**, clearing the collision by construction. |
| `confirmed_weakness` step | "Weakness" is taken | Labelled **"Confirmed weakness"**, same reason. |
| "Draft" / "Archived" / "Archive" / "Restore" | correct French already present | **Reused** from the core bookend labels. No new entry. |

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

### 10.4 The three audit trails, and which is authoritative for what

An incident carries three record sets describing overlapping facts. They are **not redundant** : they answer different questions, and reconciling them at audit time is real work the module does not pretend away.

| Trail | What it records | Written by | Authoritative for |
|---|---|---|---|
| `core.LifecycleEvent` | One immutable row per performed transition : lifecycle name, from-step, to-step, actor, comment, timestamp. Generic, so it covers every lifecycle-bearing entity in the module. | `BaseModel.transition_to()` only | **The process.** Which state something was in, from when to when, who moved it and on what stated grounds. The record to cite for a permission or approval question. |
| `HistoricalRecords` | A full row snapshot per `save()`, with the acting user, on every entity in the module. | Every `save()`, including saves that write no narrative | **The data.** What a field held at a given instant, and whether it changed outside the documented flow. The tamper-detection trail, and the only one that can expose an edit nobody narrated. |
| [IncidentTimelineEntry](incident-timeline-entry.md) | Free-text narrative, one entry per act, `occurred_at` distinct from `recorded_at`, attributed, correctable only by supersession. | Responders, plus the transition override (`source = lifecycle`) and background jobs (`source = system`) | **The facts.** What happened in the world, in real-world order, in words. The account a regulator or a court reads, and the source of the GDPR Art. 33(3)(a) description. The only trail that can be backdated, which is exactly why it is append-only and attributed. |

Reading rules, applied in this order when the three disagree : a question about **state** is answered by `LifecycleEvent`; a question about **a field value** is answered by `HistoricalRecords`; a question about **the world** is answered by the chronology. A `source = lifecycle` entry with no matching `LifecycleEvent`, or a `LifecycleEvent` with no matching entry, is a **defect** and is reported as one : the incident register export carries a reconciliation line stating whether the counts match, so a hole is visible on the document the auditor is holding rather than discovered by interview.

`core.history.build_timeline` merges the first two into the generic history panel. The chronology is rendered separately and deliberately : mixing a narrative written for humans into a diff feed written for machines makes both unreadable.

### 10.5 Storage patterns

The module uses two, split by artefact size, and the split is stated here so nobody adds a third :

| Pattern | Used by | Why |
|---|---|---|
| `FileField` on a media volume | `IncidentEvidence.file` | A multi-gigabyte disk image has no business in a database column. Follows `compliance.AssessmentResultAttachment`. |
| `BinaryField` in the database | `IncidentNotification.proof_file_content`, `NotificationFiling.proof_file_content` | A portal receipt is a few hundred kilobytes and must survive a restore alongside the row it proves. Follows `assets.Contract`, `assets.Certificate` and `trust_center.TrustCenterDocument`, all of which exclude the column from `HistoricalRecords`. |

### 10.6 Performance notes

`ReferenceGeneratorMixin._generate_next_reference()` scans every existing reference sharing a prefix on **each** insert. That is acceptable for entities counted in tens or hundreds per incident, and it is why [IncidentTimelineEntry](incident-timeline-entry.md) and [EvidenceCustodyEvent](evidence-custody-event.md) deliberately carry **no** reference prefix : a live incident produces hundreds of narrative rows in an afternoon, and each would cost a full-table scan. [NotificationFiling](notification-filing.md) does carry one, because a filing is **cited** in correspondence and a busy obligation has two or three.

`IncidentNotification` carries `Index(fields=["due_at", "workflow_state"])`, which is the index the *are we late* query runs on from the list page, the calendar, the dashboard widget, the escalation command and MCP. `Incident` indexes `(workflow_state, severity)`, `(severity, detected_at)` and `(awareness_at,)`.

---

## 11. Regulatory coverage matrix

Each row states an obligation and the field or entity that satisfies it. Where nothing satisfies it, the row says so.

### 11.1 ISO/IEC 27001:2022

| Obligation | Satisfied by |
|---|---|
| **A.5.24** planning and preparation | [IncidentResponsePlan](incident-response-plan.md) : `procedure`, `classification_scale`, `escalation_matrix`, `reporting_channels`, `evidence_procedure`, `lessons_learned_procedure`, `responsible_roles`, `approved_by` / `approved_at` / `effective_from`. `Incident.response_plan` (`PROTECT`) records which version each incident was handled under (clause 7.5.3). Plan **testing** is `Incident.is_exercise` run through the identical lifecycle, stamping `last_exercise_date`. |
| **A.5.25** assessment and decision | The `security_event` lifecycle : `under_assessment` with mandatory `assessment_notes`, stamped `assessed_by` / `assessed_at`, three mutually exclusive permissioned outcomes and an approve-gated, comment-bearing `discarded`. |
| **A.5.26** response | The eleven-step `incident` lifecycle with write-once phase stamps, [IncidentResponseAction](incident-response-action.md) typed by containment / eradication / recovery with a required `outcome` on completion, and the append-only [IncidentTimelineEntry](incident-timeline-entry.md) chronology. |
| **A.5.27** learning from incidents | [PostIncidentReview](post-incident-review.md) : `root_cause_method`, `root_cause`, `contributing_factors`, `detection_gap`, `failed_controls`, `controls_to_strengthen`, `identified_risks`, `identified_vulnerabilities`, `response_plan_update_required` feeding back into A.5.24. Closure is **blocked** until the review is approved (RG-INC-14). |
| **A.5.28** collection of evidence | [IncidentEvidence](incident-evidence.md) : `evidence_type`, `collection_method`, `content_hash` + `hash_algorithm`, `sealed_at`, `tlp`, `legal_hold`, `retention_until`, `admissibility_notes`; and the append-only [EvidenceCustodyEvent](evidence-custody-event.md) ledger with `counterparty`, `location`, `hash_at_event` and `integrity_ok`. |
| **A.6.8** reporting of events and weaknesses | [SecurityEvent](security-event.md) : `event_class`, `detection_source`, `detected_at` versus `reported_at` as the measurable reporting delay, and `reporter` / `reporter_label` / `is_anonymous` with a `CheckConstraint` guaranteeing the anonymous channel. |
| **A.5.5** contact with authorities | [ReportingAuthority](reporting-authority.md) : the documented catalogue with portal, mailbox, phone, language and filing procedure. |
| **A.8.8** technical vulnerability management | A confirmed weakness promotes into the **existing** `risks.Vulnerability` register (`SecurityEvent.vulnerability`); `PostIncidentReview.identified_vulnerabilities` feeds it after the fact. No parallel weakness register. |
| **A.8.16** monitoring activities | `PostIncidentReview.detection_gap` plus the `mean_time_to_detect` predefined indicator, making monitoring effectiveness measurable rather than asserted. |
| **clause 10.1** continual improvement | The review outputs : corrective action plans, controls to strengthen, plan updates and the predefined indicator series that shows whether the trend improves. |
| **clause 10.2 a)** correction | [IncidentResponseAction](incident-response-action.md) and `Incident.contained_at` / `eradicated_at` / `recovered_at`. |
| **clause 10.2 b)** determine the causes, and whether similar nonconformities exist | `PostIncidentReview.root_cause_method` + `root_cause` + `contributing_factors`, mandatory to leave `in_progress`; `recurrence_likelihood` + `similar_incidents_checked`, which must be `True` to submit. |
| **clause 10.2 c) and e)** implement action, make changes to the ISMS | `PostIncidentReview.corrective_action_plans` (`compliance.ComplianceActionPlan`, eight-step lifecycle), `isms_changes` (M2M to the existing `reports.ISMSChange`, so *show me the ISMS change this incident forced* is answered with a record rather than a checkbox), `risk_reassessment_required` and `training_required`. |
| **clause 10.2 d)** review the effectiveness of corrective action | `PostIncidentReview.effectiveness_review_date` / `effectiveness_reviewed_at` / `effectiveness_reviewed_by` / `effectiveness_verdict` (RG-INC-32), mirrored onto `compliance.Finding` by the prerequisite so the same record exists for audit findings. |
| **clause 10.2 f)** retained documented information | The whole record, plus `HistoricalRecords` on every model and the immutable `core.LifecycleEvent` per transition. |
| **clause 9.3.2 d)1) and d)2)** management review inputs | Incidents reach the review as **nonconformities and corrective actions** through the generalised `compliance.Finding` (section 4a) and as **monitoring and measurement results** through the predefined incident indicators (section 4b). Clause 9.3.2 does not name incidents as a separate input, and 9.3.2 c) is *changes in the needs and expectations of interested parties* : citing it for incidents would be wrong, and this module does not. |

### 11.2 GDPR

| Obligation | Satisfied by |
|---|---|
| **Art. 33(1)** notify the supervisory authority within 72 hours of becoming aware, unless unlikely to result in a risk | [IncidentNotification](incident-notification.md) with `regime = gdpr_art33_authority`, anchored on `Incident.awareness_at` (**never** `detected_at`), `deadline_hours = 72`, stored `due_at`. The **unless** is the `not_required` terminal step : an approve-gated, comment-bearing transition with a named `decided_by`, a stamped `decided_at` and a mandatory `decision_rationale` (RG-INC-25). |
| **Art. 33(2)** a processor notifies the controller without undue delay | `regime = gdpr_art33_2_controller`, `no_fixed_deadline = True`, `recipient_supplier` as the controller. Generated **only** when `PersonalDataBreach.controller_role = processor`, and never alongside Art. 33(1). |
| **Art. 33(3)(a)-(d)** minimum content | [PersonalDataBreach](personal-data-breach.md) : `nature` + `data_categories` + `data_subject_categories` + `approximate_data_subjects` + `approximate_records` (a), `dpo_contact` (b), `likely_consequences` (c), `measures_taken` (d), all enforced as preconditions of the confirm transition (RG-INC-41), and rendered in article order on the page because that is the order the filing form asks for. |
| **Art. 33(4)** information may be provided in phases | Successive [NotificationFiling](notification-filing.md) rows with `is_correction = True` and, where a statement is replaced, `supersedes`, on the **same** obligation. Never an edit of the original filing. |
| **Art. 33(5)** internal documentation of every breach, notified or not | The [PersonalDataBreach](personal-data-breach.md) record itself : its `documented` lifecycle step **is** the register entry, and `register_entry_reference` keeps an externally held register reconcilable. The `not_a_breach` step is the entry an inspector asks for when personal data was involved and no filing was made. |
| **Art. 34(1)** communicate to data subjects on high risk | `regime = gdpr_art34_data_subject`, `no_fixed_deadline = True`, generated only when `high_risk_to_rights` is exactly `True`. `None` is not a match. |
| **Art. 34(3)(a)-(c)** exemptions | `Art34Ground` (`encryption`, `subsequent_measures`, `disproportionate_effort`), each requiring a written justification. The obligation is **still generated** and is closed through its own `not_required` decision with that justification as the rationale : an exemption that silently suppresses a row is an absence nobody can review. `disproportionate_effort` **additionally** generates the public-communication obligation, because Art. 34(3)(c) substitutes a public communication rather than removing the duty. |
| **Art. 56** one-stop-shop | `PersonalDataBreach.lead_authority` naming the lead supervisory authority, with `Incident.cross_border_impact` driving templates marked `requires_cross_border`. Deliberately distinct from `cross_border_eu`, which is Art. 4(23) cross-border **processing**. |

### 11.3 NIS2 and DORA

| Obligation | Satisfied by |
|---|---|
| **NIS2 Art. 23(1)** inform the recipients of the service | `regime = nis2_recipients`, `recipient_kind = customer`, `no_fixed_deadline = True`. |
| **NIS2 Art. 23(3)** significance test | `Incident.is_significant` (three-state), `significance_determined_at` (usable as a `ClockAnchor`) and `significance_justification`. A null verdict never silently generates or suppresses a NIS2 duty. |
| **NIS2 Art. 23(4)(a)** 24-hour early warning, stating whether the incident is suspected of being caused by an unlawful or malicious act and whether it has cross-border impact | `regime = nis2_early_warning`, anchored on awareness, 24 hours, `requires_significant`. The `drafted -> sent` gate is **refused** while `is_significant`, `suspected_malicious` or `cross_border_impact` is null : the form the operator is filing has a mandatory field for each, so the record must be able to answer them. |
| **NIS2 Art. 23(4)(b)** 72-hour incident notification | `regime = nis2_notification`, anchored on awareness, 72 hours. |
| **NIS2 Art. 23(4)(c)** intermediate report **on request** | `regime = nis2_intermediate`, `no_fixed_deadline = True`, `source = manual`, created when the authority asks. Deliberately **not** seeded : generating it speculatively would put a permanent open obligation on every significant incident and train the operator to ignore the bucket. |
| **NIS2 Art. 23(4)(d)** final report within one month **of the incident notification** | `regime = nis2_final`, `clock_anchor = previous_stage`, `depends_on` the `nis2_notification` obligation, 720 hours. Its `due_at` stays null until that filing is actually made and appears the moment it is. Anchoring it on awareness instead would make **every** NIS2 final-report deadline in the register wrong, always in the direction that makes the organisation look later than it is. |
| **DORA Art. 19** initial, intermediate and final major ICT incident reports | `regime = dora_initial` / `dora_intermediate` / `dora_final` on the identical mechanism, with `origin_supplier` and `affected_suppliers` carrying the ICT third-party dimension and sub-processors reachable as ordinary `Supplier` rows. |
| **ePrivacy Art. 4(3)**, **CRA Art. 14** | Expressible with the same template shape as regimes `eprivacy` and `cra` : available, not shipped as defaults. |
| **Contractual and internal duties** | `contractual_customer`, `contractual_supplier`, `insurer`, `internal_management` and `public_communication` run through the identical clock machinery, so a contractual 48-hour clause is tracked exactly like a statutory one. |

### 11.4 What is deliberately not covered

- **Automated RTO / MTD breach detection** (RG-INC-33). `assets.EssentialAsset.max_tolerable_downtime`, `recovery_time_objective` and `recovery_point_objective` are free-text `CharField(max_length=100)` values such as `4 hours`. The register reports the measured `outage_duration` and each affected asset's declared objective **verbatim, side by side**, and declines to conclude. Migrating those three fields to `DurationField` is an m2 prerequisite.
- **Business-day and public-holiday clock semantics.** All arithmetic is wall-clock, which is correct for GDPR, NIS2 and DORA : the 72 hours of Art. 33(1) run through nights, weekends and public holidays. A contractual clause written in business days cannot be expressed by this model and is stated as out of scope rather than approximated.
- **A maintained European authority directory.** The seeded CNIL and ANSSI rows are demo data for the Voltara Energy dataset so the screenshots show a real portal link. An organisation outside France writes its own rows, which is exactly why the catalogue is a table and not a hardcoded matrix.

---

## 12. App wiring checklist

A new Django app touches a fixed set of global registration points, and the count is independent of the data model. Every item below is required, and the four marked **(silent)** fail without an error message.

**Application and data**

- [ ] `INSTALLED_APPS` gains `"incidents"` in `core/settings.py`.
- [ ] **(silent)** `incidents/apps.py` defines `IncidentsConfig.ready()` and imports `incidents.lifecycles` there. `lifecycle_name_for()` resolves `LIFECYCLE_NAME` only `if name and name in LIFECYCLE_REGISTRY`, so omitting the import quietly downgrades every model to the core 4-state lifecycle, in tests as well as in production. A test asserts `Incident.get_lifecycle().name == "incident"` per entity so the omission fails loudly.
- [ ] `incidents/admin.py` registers every model with `SimpleHistoryAdmin`.
- [ ] Initial migration, plus the migration deleting the reserved `# linked_incidents = ...` placeholder on `risks.Risk`.
- [ ] `scripts/seed_demo_data.py` gains an incidents phase exercising every model and field, including the two authorities and the seeded template set, each created through `save()` then `transition_to(..., enforce_permission=False)`.

**Permissions**

- [ ] `PERMISSION_REGISTRY` gains the `incidents` module with its six features, and `MODULE_LABELS` gains `"incidents": _("Incidents")`.
- [ ] `accounts/migrations/0056_add_incidents_permissions.py` creates the rows and attaches them to the six system groups.

**Navigation and theming**

- [ ] `core/navigation.py` `NAV_TREE` gains the module's sections and pages.
- [ ] `core/templatetags/ui.py` `MODULE_ACCENTS` gains `"incidents"`.
- [ ] `base.html` defines `--module-accent-incidents` and `--module-accent-incidents-soft` in **both** the light and the dark token block. An unregistered accent is silently dropped.
- [ ] The sidebar gains its section between Risk management and Compliance.

**Cross-cutting surfaces**

- [ ] `GlobalSearchView` : `NAVIGATION_ENTRIES`, `ACTION_ENTRIES` and the search categories for `Incident` and `SecurityEvent`.
- [ ] Calendar : `ALL_CATEGORIES`, the `add()` / `add_range()` blocks for the five date sources, and the label in `build_upcoming_deadlines`.
- [ ] Kanban : `ENTITY_PERMS`, `TYPE_ICONS`, `TYPE_LABELS`, `_INCIDENT_BUCKETS`, `_build_incidents` and its `_BUILDERS` registration.
- [ ] Dashboard : the widget in `DASHBOARD_WIDGETS`, its partial under `templates/dashboard/widgets/`, the entry in `core/signals.py` `_DASHBOARD_MODELS` for cache invalidation, **and the context variables the partial reads, set in `GeneralDashboardView.get_context_data`**. A registered widget whose context variables are never populated renders empty with no error.
- [ ] `context.PredefinedIndicatorSource` gains `incidents_per_period`, `mean_time_to_detect`, `mean_time_to_contain`, `mean_time_to_resolve`, `open_incidents`, `overdue_notifications` and `unsealed_evidence`, with matching `_compute_*` methods and `PREDEFINED_SOURCE_FORMAT` entries.

**Integration surfaces**

- [ ] `mcp/tools.py` : `_register_incidents_tools()` added to `register_all_tools()`, the `HELP_TEXT` reference-prefix entries, and `TOPIC_INCIDENTS` added to `ALL_TOPICS` and to the help tool's description and `topic` property.
- [ ] `mcp/tools.py` `_filter_by_scopes()` and the `_register_crud()` handler chain extended with `scope_parent_lookup` (§5), plus the two generic web endpoints.
- [ ] `assistant/catalog.py` : the four read-only `ToolSpec` entries.
- [ ] `accounts/notifications.py` : the eight `NotificationType` values, their `notify_*` helpers and the accounts migration altering the choices.
- [ ] `helpers` : a help-content migration adding the module's help banners.

**Documentation and translation**

- [ ] `locale/fr/LC_MESSAGES/django.po` : every new string, with `msgctxt "incident"` blocks for the collisions listed in §10.3, and a verification pass for duplicate `msgid` entries before commit.
- [ ] `docs/specs/README.md` layout table gains the `m6-incidents/` row; `docs/user-guide/`, `docs/reference/rest-api.md` and `docs/reference/mcp-server.md` are updated.
- [ ] **`README.md`** : the feature table, the MCP tools section and the module list reflect the new module.
- [ ] **`CHANGELOG.md`** : an `### Added` entry for the module, a `### Security` entry for the scope-inheritance fix, and a `### Changed` entry for the `compliance.finding` permission re-gating.

---

## 13. Known limitations

These are stated plainly because an implementer and an auditor both need them, and because discovering any of them during an inspection is worse than reading it here.

**Append-only is an application-level guarantee, not a database one.** [IncidentTimelineEntry](incident-timeline-entry.md), [EvidenceCustodyEvent](evidence-custody-event.md) and [NotificationFiling](notification-filing.md) refuse updates and deletions in `save()` and `delete()`. Every documented write path in Cairn goes through `Model.save()`, so the web forms, the DRF serializers, the MCP tools and the Django admin are covered. `QuerySet.update()`, `QuerySet.bulk_update()`, `QuerySet.delete()`, cascade deletion, raw SQL and a `manage.py shell` session are not. `HistoricalRecords` turns prevention into **detection** : a row whose historical trail shows more writes than the design allows has been altered, and that is visible on its history panel. Real database-level immutability would need PostgreSQL rules or triggers, which `core.settings_test` (SQLite in memory, migrations disabled) cannot exercise. That divergence is not taken here; if it is ever taken it must be taken deliberately and documented in this file. The claim to make to an auditor is *tampering is prevented on every supported path and detectable on the rest*, never *the ledger is immutable*.

**Three overlapping audit trails.** See §10.4 for what each is authoritative for. The residual risk is a **narrative hole** : any future code path that assigns `workflow_state` directly instead of calling `transition_to()`, and any bulk import that writes rows without replaying their transitions, produces a chronology with a gap while the lifecycle history stays complete. There is no way to detect that from the timeline alone, which is why the register export carries a reconciliation line and why direct `workflow_state` assignment is forbidden in review.

**Gates live in `transition_to()`, so an administrator can add an edge the gate does not know about.** RG-INC-08 is the only working choice, because `form_class`, `allowed_roles` and `allowed_users` are dropped by the `LifecycleDefinition` round-trip. The cost is that an administrator editing the lifecycle at `/config/lifecycles` can add, say, a `triaged -> closed` edge. The required-field, review-approved, obligations-decided and evidence-sealed checks would still run inside `transition_to()`, but a step the gate does not enumerate could be reached, and the transition's `permission_action` would then be the only surviving control on that path. Marking a lifecycle `is_customized` also detaches it permanently from the code definition, and a `migrate` run is required after every `incidents/lifecycles.py` edit before a change takes effect. A lifecycle-definition validator that refuses to save an edge the module declares as gate-bearing is a worthwhile follow-up and is not in this module.

**The template applicability engine is a flat conjunction.** [ReportingObligationTemplate](reporting-obligation-template.md) evaluates its conditions as an AND, in a fixed order. Real regulatory rules are disjunctive (*significant **or** affecting more than N users*) and conditional (*unless the data was encrypted*). The gap is paid for with near-duplicate templates rather than with a rule expression language, and with the deliberately stricter treatment of negative conditions : the obligation is still generated and the exemption is discharged through its own approve-gated `not_required` decision. A rule language would need a parser, an evaluator, a test surface, an editing UI, a migration path for stored expressions and a way to explain to an operator at 02:00 why a rule did or did not fire. It is reconsidered **only** if a real regime cannot be expressed at all, not because expressing it takes three templates instead of one.

**The ThreatCategory reuse is a real coupling.** `Incident.category` and `SecurityEvent.category` reuse `risks.constants.ThreatCategory` (23 values) verbatim, so that the incident, threat and risk chain reads as one taxonomy. The ENISA and ISO/IEC 27035-2 incident taxonomies do not map onto those values one-to-one : there is no clean *misconfiguration* or *third-party outage* bucket. A regulator demanding its own scheme forces either a second field or a mapping table, and adding an incident-specific value means editing `risks/constants.py` and accepting that the value then also appears in every threat picker. The alternative, two taxonomies, drifts within one release and breaks the chain, so this coupling is chosen knowingly.

**Two further consequences worth knowing.** [IncidentResponseAction](incident-response-action.md) runs a plain `status` column rather than a lifecycle, which is an argued deviation from the platform doctrine : it is invisible to `reportable()` / `linkable()` / `deletable_states()`, cannot be governed per state, emits no `LifecycleEvent`, and would need a data migration on a live table if the decision is ever reversed. And the platform holds, for any evidence item **registered by reference**, the hash of something it does not hold : Cairn can prove that the digest recorded at acquisition has not been altered inside Cairn, and nothing about the artefact sitting in a vault. The UI renders *Held in Cairn* and *Registered by reference* as two visually distinct states precisely so a reader of a green integrity column knows which of the two claims it is making.

---

## 14. Acceptance criteria

### 14.1 Functional

- [ ] An event can be reported (including anonymously), assessed with mandatory notes, and promoted, confirmed as a weakness or discarded, each through a permissioned transition; a discarded event is still findable with its rationale.
- [ ] An incident runs the full lifecycle with write-once phase stamps, and cannot be closed until its review is approved, every obligation is decided and every evidence item has left `collected`.
- [ ] `awareness_at` drives every statutory deadline, defaults to `detected_at`, and requires a justification whenever it postdates detection.
- [ ] Triage instantiates obligations in `assessed` with a matching `LifecycleEvent`, is idempotent when re-run, and refuses to complete with zero obligations unless personal data is involved or the incident is an exercise.
- [ ] Evidence can be registered, sealed, analysed, retained, released and destroyed; sealed acquisition metadata refuses to change; destruction is a transition that keeps the row and appends a final custody event.
- [ ] Integrity verification reports three distinct outcomes and never collapses *not verifiable* into *mismatch*.
- [ ] A personal data breach can be confirmed only with the complete Art. 33(3) set and a non-null Art. 34 verdict, and is ruled out through a transition, never by clearing a checkbox.
- [ ] A filing freezes `first_submitted_at`, `late_by` and `was_late`, starts any dependent clock, and cannot be un-breached by a later anchor correction.
- [ ] An exercise runs the identical lifecycle, generates no obligation, appears in no KPI or deadline feed, and updates the plan's `last_exercise_date` on closure.

### 14.2 Governance and permissions

- [ ] All thirty codenames exist, are granted to the six system groups by the accounts migration, and appear on the group matrix screen.
- [ ] Every lifecycle-bearing model resolves the expected lifecycle by name (the test that catches a missing `ready()` import).
- [ ] No archive -> restore -> delete path exists on any entity : the restore edge is approve-gated and refused for any row that ever left `draft`, and the regression test asserting a sealed evidence row survives the attempt passes.
- [ ] No state literal appears outside `incidents/constants.py`.

### 14.3 Security

- [ ] A user scoped out of an incident gets an empty list from every child-entity MCP tool, a 404 from `workflow:transition` and a 404 from the history partial for its evidence, obligations, custody rows and breach record.
- [ ] Evidence bytes and proof bytes are reachable only through the permission-checked and scope-checked detail actions, never through `/media/` and never in a list or detail payload.
- [ ] The upload caps are enforced in the form, the serializer and the MCP layer.

### 14.4 Quality

- [ ] `compilemessages` succeeds : no duplicate `msgid` without a distinguishing `msgctxt`, and no step label carrying a `msgctxt`.
- [ ] Every detail page renders the lifecycle stepper, in a 2-column layout with no nav-tabs, correctly in light and dark mode and at mobile widths, with the three- and four-exit graphs and the confirmation modal explicitly checked.
- [ ] `ruff check` and `pytest -x --cov` pass, and the seed produces a demo dataset exercising every model and field.

---

*End of Module 6 : Security Incident Management*

# PostIncidentReview

`incidents.models.post_incident_review.PostIncidentReview`

The learning record : ISO/IEC 27001:2022 **A.5.27 (learning from information security incidents)**, and the bridge from an incident file into **clause 10.1 / 10.2** (continual improvement, nonconformity and corrective action). It holds the determined root cause with the method used to determine it, the detection gap, the controls that failed, and the outward links that make an incident actually change something : the nonconformities it raised, the corrective action plans it produced, the risks to reassess, the vulnerabilities to register, the controls to strengthen, the ISMS changes it forced and the response plan it obliges the organisation to rewrite.

It is also the gate. An [Incident](incident.md) cannot reach `closed` until its review is in `approved` or `effectiveness_verified` (RG-INC-14), so this entity carries the module's audit value : without it the register would hold a tidy chronology of things that happened and no evidence that anything changed because of them.

File: `incidents/models/post_incident_review.py`

`ScopedModel` subclass : UUID PK, sequential `reference` (prefix **`PIRV`**, e.g. `PIRV-1`), `scopes` M2M, `tags`, `version`, `created_by`, `django-simple-history` audit trail, and the dedicated **`post_incident_review`** lifecycle. `workflow_perm_namespace` is overridden to `incidents.review`, because the default `app_label.model_name` would spell `incidents.postincidentreview`, which matches no feature in `PERMISSION_REGISTRY` and would make every lifecycle permission check on the entity silently evaluate against a codename nobody holds.

> **The module ships as one block.** `PostIncidentReview` is phase 1 and declares no `PHASE 2` field, but the phase markers carried by other entity specs in this module are **build order, not a delivery boundary**. In particular the phase 0 generalisation of `compliance.Finding`, on which `raised_findings` and the whole clause 10.2 story below depend, lands in the same release as this entity.

## Why the review is a gate and not a report

A.5.27 says knowledge gained from incidents shall be used to strengthen controls. That sentence is trivially satisfiable on paper and almost never satisfied in practice, because the natural end of an incident is the moment service is restored : the responders are exhausted, the pressure is off, and the write-up slips.

Cairn answers that with a structural constraint rather than a reminder. The review is a governed row with its own lifecycle, created automatically when the incident enters the post-incident review phase (the `recovered -> post_incident_review` transition), and the incident's closure transition is refused while it is unapproved. There is no way to reach a closed incident that has not been through a review, on any surface : the gate lives in `Incident.transition_to()` and therefore applies identically to the web stepper, to DRF and to MCP.

The second structural constraint is the `effectiveness_verified` step, which exists because the platform could not previously answer clause 10.2 d) at all. See [Effectiveness verification](#effectiveness-verification--the-clause-102-df-record).

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `PIRV-N`, unique | Business reference. The review carries **no title of its own** : exactly one exists per incident (RG-INC-31), so it is identified by its reference and its incident everywhere it is rendered, and `__str__` returns `PIRV-N - INCD-N`. |
| `scopes` | relation | M2M -> `context.Scope` | Copied from the incident at creation and re-synced by `Incident.save()` whenever the incident's scopes change. See [Scope tenancy](#scope-tenancy). |
| `scheduled_date` | date | optional, indexed | When the review is planned. Feeds the calendar and the upcoming-deadlines widget. Left blank by the automatic creation : a review nobody has scheduled shows up as an incident parked in `post_incident_review`, which is the honest signal. |
| `held_at` | datetime | optional, **write-once** | When the review actually took place. Stamped by the `scheduled -> in_progress` transition (RG-INC-12). |
| `root_cause_method` | enum | required, default `five_whys` | `RootCauseMethod`. Naming the technique is what separates a determined root cause from a plausible guess, and it is the first thing an auditor asks after reading `root_cause`. |
| `root_cause` | text | optional, blank default | The determined cause of the nonconformity : not the symptom, not the remediation. **Mandatory to leave `in_progress`** (clause 10.2 b)). |
| `contributing_factors` | text | optional, blank default | Secondary factors that let the incident happen, or that made it worse than it needed to be |
| `detection_gap` | text | optional, blank default | Why it was not detected earlier. Drives monitoring improvements (A.8.16) and is what makes the mean-time-to-detect indicator actionable rather than decorative. |
| `containment_assessment` | text | optional, blank default | Whether the response itself was adequate and timely : the honest verdict on the A.5.26 handling, distinct from the verdict on the controls that failed |
| `what_went_well` | text | optional, blank default | Practices to keep |
| `what_failed` | text | optional, blank default | Practices to change |
| `recurrence_likelihood` | enum | optional, blank default | `context.constants.Criticality` (`low`, `medium`, `high`, `critical`). Clause 10.2 b) 3) : whether similar nonconformities exist, or could occur. Reuses the scale severity, assets and suppliers already share; no parallel enum is created. |
| `similar_incidents_checked` | boolean | required, default `False` | **Must be `True` to leave `in_progress`.** Confirms that clause 10.2 b) 3) was actually performed rather than silently skipped. A boolean here is defensible precisely because it is gated : it cannot be left `False` and still produce an approved review. |
| `risk_reassessment_required` | boolean | required, default `False` | The incident invalidates a registered risk evaluation. Fires `RISK_REVIEW_TRIGGERED_BY_INCIDENT` to the risk owners. |
| `response_plan_update_required` | boolean | required, default `False` | The [IncidentResponsePlan](incident-response-plan.md) itself must change : A.5.27 feeding back into A.5.24 |
| `training_required` | boolean | required, default `False` | Awareness or training action needed (A.6.3) |
| `effectiveness_review_date` | date | optional, indexed | Date the corrective actions' effectiveness will be verified. **Required to reach `approved`**, which is what puts the clause 10.2 d) verification on the calendar instead of in someone's memory. |
| `effectiveness_reviewed_at` | datetime | optional, **write-once** | When effectiveness was actually verified. Stamped by the `approved -> effectiveness_verified` transition (RG-INC-12). |
| `effectiveness_verdict` | enum | optional, blank default | `EffectivenessVerdict`. **Required non-blank to reach `effectiveness_verified`.** Clause 10.2 f) retained documented information on the results of the corrective action. |
| `effectiveness_notes` | text | optional, blank default | The evidence supporting the verdict : what was measured, tested or observed, and when |
| `workflow_state` | string | indexed, default `draft` | Lifecycle step (`post_incident_review`). Never written directly : see [Lifecycle](#lifecycle). |
| `tags` | relation | M2M -> `context.Tag` | |
| `version` | int | auto-incremented | |
| `created_by` | relation | FK -> User | |
| `created_at` / `updated_at` | datetime | auto | Timestamps |

### Relations

| Name | Type | Target | Reverse accessor | Description |
|---|---|---|---|---|
| `incident` | OneToOne, `PROTECT`, required | [Incident](incident.md) | `post_incident_review` | Exactly one review per incident (RG-INC-31). `PROTECT` means an incident that has been reviewed can never be deleted. |
| `response_plan` | FK, `SET_NULL`, optional | [IncidentResponsePlan](incident-response-plan.md) | `post_incident_reviews` | The plan this review concludes must be updated. Copied from the incident at creation; editable, because the review may conclude that a *different* plan is the one at fault. |
| `facilitator` | FK -> User, `SET_NULL`, optional | User | `facilitated_post_incident_reviews` | Who ran the review. Fills `assessor` on every nonconformity the review raises : see [Nonconformities and `assessor`](#nonconformities-and-assessor). |
| `effectiveness_reviewed_by` | FK -> User, `SET_NULL`, optional | User | `verified_post_incident_reviews` | Who verified that the corrective action worked. Required to reach `effectiveness_verified`. |
| `participants` | M2M -> User | User | `post_incident_reviews` | Who took part. Recipients of `POST_INCIDENT_REVIEW_DUE`. |
| `raised_findings` | M2M | `compliance.Finding` | `post_incident_reviews` | The nonconformities this review raised, with `source = incident` and `incident` set : the **one** ISO 27001 clause 10.2 register, reached through the phase 0 generalisation of `Finding`. |
| `corrective_action_plans` | M2M | `compliance.ComplianceActionPlan` | `post_incident_reviews` | Clause 10.2 c) corrective actions, reusing the existing 8-step action-plan lifecycle with its owner, assignees, target date, progress, cost estimate and cancellation rules |
| `failed_controls` | M2M | `compliance.Requirement` | `failing_post_incident_reviews` | The controls that were in place and did not hold |
| `controls_to_strengthen` | M2M | `compliance.Requirement` | `improving_post_incident_reviews` | The controls the organisation has decided to reinforce as a result |
| `identified_risks` | M2M | `risks.Risk` | `post_incident_reviews` | Risks the incident revealed or invalidated. Pickers use `linkable_or_linked()`. |
| `identified_vulnerabilities` | M2M | `risks.Vulnerability` | `post_incident_reviews` | Weaknesses to register in the **existing** vulnerability register, never a parallel table |
| `isms_changes` | M2M | `reports.IsmsChange` | `post_incident_reviews` | Clause 10.2 e) : the changes to the ISMS this incident forced. See [ISMS changes](#isms-changes--clause-102-e). |

`failed_controls` and `controls_to_strengthen` are deliberately two distinct M2Ms on the same target rather than one list with a role column. They answer two different questions - *what broke* and *what we are doing about it* - and an auditor reads them side by side. A single list would make the review look complete while saying nothing.

Four of these M2Ms declare the reverse accessor `post_incident_reviews` on four different targets (`compliance.Finding`, `compliance.ComplianceActionPlan`, `risks.Risk`, `risks.Vulnerability`, plus `reports.IsmsChange` and `settings.AUTH_USER_MODEL` for `participants`). That is legal because the targets differ, and none of those names is taken today. It does mean `finding.post_incident_reviews` and `user.post_incident_reviews` are different relations : never write `obj.post_incident_reviews` in shared code without naming the model it hangs off.

### Meta

- `ordering = ["-scheduled_date"]`
- Indexes on `(workflow_state,)`, `(scheduled_date,)`, `(effectiveness_review_date,)`
- `OneToOneField` on `incident` supplies its own uniqueness; no extra constraint is declared

## Enumerations

### RootCauseMethod

Declared in `incidents/constants.py`.

| Value | Label |
|---|---|
| `five_whys` | 5 Whys |
| `ishikawa` | Ishikawa |
| `fault_tree` | Fault tree analysis |
| `timeline_analysis` | Timeline analysis |
| `barrier_analysis` | Barrier analysis |
| `other` | Other |

### EffectivenessVerdict

| Value | Label |
|---|---|
| `effective` | Effective |
| `partially_effective` | Partially effective |
| `not_effective` | Not effective |

**Declared once, in `compliance/constants.py`, by phase 0**, alongside `FindingSource`, and imported by `incidents`. The canonical definition is [Finding](../m3-compliance/finding.md#effectivenessverdict); this entity adds no value of its own. The same enum types `PostIncidentReview.effectiveness_verdict` and `compliance.Finding.effectiveness_verdict`, so the propagation described below is a straight copy and the two fields can never drift apart. `incidents` imports `compliance`; `compliance` does not import `incidents` except through the string-referenced `incidents.Incident` FK, so there is no cycle.

`recurrence_likelihood` reuses `context.constants.Criticality` and declares no enum of its own.

## What a review must change : the outward links

A review whose only output is prose is a story. The outward links are what make it a control.

| Outcome | Where it lands | Field on the review | Clause |
|---|---|---|---|
| A nonconformity is raised | `compliance.Finding` with `source = incident`, `incident` set, `assessment` null | `raised_findings` | 10.2 (the single register) |
| A corrective action is decided | `compliance.ComplianceActionPlan` | `corrective_action_plans` | 10.2 c) |
| A control is named as having failed | `compliance.Requirement` | `failed_controls` | A.5.27, 10.2 b) |
| A control is to be reinforced | `compliance.Requirement` | `controls_to_strengthen` | A.5.27, 10.1 |
| A risk must be reassessed or registered | `risks.Risk` (RG-INC-34) | `identified_risks` + `risk_reassessment_required` | 6.1.2, 8.2 |
| A weakness must be registered | `risks.Vulnerability` | `identified_vulnerabilities` | A.8.8 |
| The ISMS itself must change | `reports.IsmsChange` | `isms_changes` | 10.2 e) |
| The response procedure must change | [IncidentResponsePlan](incident-response-plan.md) | `response_plan` + `response_plan_update_required` | A.5.24, A.5.27 |
| Awareness or training is needed | a `ComplianceActionPlan` against the A.6.3 requirement | `training_required` + `corrective_action_plans` | A.6.3 |

Every one of these targets already exists in the platform. **No entity in this list was invented for m6**, and that is the point : an incident that produces a nonconformity produces the *same kind* of nonconformity an audit produces, lands in the same register, is scored the same way and reaches the same management review.

### Nonconformities and `assessor`

Phase 0 generalises `compliance.Finding` from *audit finding* to *nonconformity register entry* : `assessment` becomes nullable (`CASCADE` -> `SET_NULL`), a `source` enum is added (`audit` | `incident` | `management_review` | `monitoring` | `complaint`, default `audit`), an `incident` FK is added, and the three effectiveness fields are added.

`Finding.assessor` is today a **required** `PROTECT` foreign key to `AUTH_USER_MODEL` with no `null=True`. A nonconformity raised by a post-incident review has no auditor, so phase 0:

- makes it `null=True, blank=True`, **keeping the column and every existing row untouched**;
- re-labels it `verbose_name = _("Raised by")`, a label change only : no column rename, no data migration, no reverse accessor change (`user.findings` is unchanged);
- adds a `clean()` requiring it whenever `source == audit`, so nothing about the audit path is loosened.

This review fills it. **Gate GP-02** (`in_progress -> submitted`) normalises every row in `raised_findings`, inside the transition's atomic block and idempotently :

```python
for finding in review.raised_findings.all():
    finding.source = FindingSource.INCIDENT
    finding.incident = review.incident
    if finding.assessor_id is None:
        finding.assessor = review.facilitator or user
    finding.save()
```

The same normalisation runs again on entry to `approved`, so a nonconformity attached during a send-back-and-rework loop is normalised too. `assessment` is left null : fabricating an audit to hang an incident's nonconformity off is exactly the practice the generalisation exists to end.

Two consequences worth stating rather than discovering:

1. **Incident-born findings reach management review section 4a for free.** `reports/management_review.py` builds section 4a with `Finding.objects.select_related("assessment", "assessor")`, filtered on `created_at` and `finding_type` only : it is source-agnostic by construction, and `select_related` on a now-nullable FK is null-safe. Nothing in that module changes.
2. **Assessment-scoped queries stay audit-only by construction**, because they walk the reverse accessor from a `ComplianceAssessment` and an incident-born finding has none. The two statements are not in tension : section 4a is deliberately source-agnostic, the assessment-scoped scoring paths are deliberately assessment-scoped, and the module ships a test for each.

Phase 0 also introduces the `compliance.finding` permission feature and re-gates the **existing** MCP tools (`list_findings`, `get_finding`, `create_finding`, `update_finding`, `delete_finding`) and the existing finding views from `compliance.assessment.*` to `compliance.finding.*`. That is a **breaking contract change** for any live MCP integration and is recorded as such : without it, an incident responder would need audit permissions to write down a nonconformity.

### Corrective action plans, and creating a link before the target is linkable

RG-INC-35 : corrective work is recorded exclusively as `compliance.ComplianceActionPlan` rows linked from `corrective_action_plans`. [IncidentResponseAction](incident-response-action.md) exists only for in-incident operational steps and carries a plain status column, never a lifecycle. The distinction is clean : *stop the bleeding* is a response action, *make sure this cannot happen again* is a corrective action plan.

The plan's own required fields (`owner`, `gap_description`, `remediation_plan`, `priority`, `target_date`) belong to the compliance module and are not duplicated here. The *New corrective action plan* button on the review opens the compliance form modal with `requirements` pre-seeded from `controls_to_strengthen`.

One mechanical point applies to `raised_findings`, `corrective_action_plans`, `identified_risks` and `identified_vulnerabilities` alike. RG-INC-37 requires every link picker to filter through `linkable_or_linked()`, and a freshly created target is not yet linkable : a new `Finding` runs the core `default` lifecycle and is linkable only in `validated`, a new `ComplianceActionPlan` is linkable only from `to_implement` onward. The *create* actions therefore create the row **and attach it in the same atomic block**, so the link exists before the target is linkable; the manual picker then uses `linkable_or_linked()`, which keeps that already-attached draft row visible while offering only linkable rows for new links. This is precisely what `linkable_or_linked()` (`core/lifecycle.py` `linkable_or_linked()`) is for, and it needs no exception to RG-INC-37.

### Risks and vulnerabilities

A risk revealed by an incident is a `risks.Risk` with `risk_source = RiskSourceType.INCIDENT`, `source_entity_type = "incidents.Incident"` and `source_entity_id = incident.pk`, reusing the existing generic back-pointer (RG-INC-34). `RiskSourceType.INCIDENT` already exists in `risks/constants.py` and is unused today; m6 is its first writer.

The review's `identified_risks` M2M is **not** a duplicate of that back-pointer. They record two different facts : the back-pointer says *this risk came from that incident*, the M2M says *this review identified it*. A risk that already existed in the register before the incident materialised has no back-pointer to set and is still an outcome of the review.

`risk_reassessment_required = True` additionally fires `RISK_REVIEW_TRIGGERED_BY_INCIDENT`. Independently of the review, RG-INC-36 makes an incident that realises a risk carrying an **active** `risks.RiskAcceptance` force that acceptance under review, through a derived query hung off the existing `expire_risk_acceptances` sweep.

### ISMS changes : clause 10.2 e)

Clause 10.2 e) is *make changes to the information security management system, if necessary*. Answering it with a boolean would be a checkbox where an auditor expects a record, and a real entity already exists : `reports.IsmsChange`, the clause 9.3.3 management-review output, with its `ICHG` reference, its change type, its impact analysis, its affected scopes and frameworks, its owner, its status and its target and implementation dates.

The review therefore declares `isms_changes = models.ManyToManyField("reports.IsmsChange", blank=True, related_name="post_incident_reviews", verbose_name=_("ISMS changes"))`. This costs **no schema change on the `reports` side** : `related_name` creates a reverse accessor, not a column, the join table belongs to the `incidents` migration, and `post_incident_reviews` is free on that model. There is no circular dependency : `incidents` imports `reports`, and `reports` does not import `incidents`.

Four honest limits an implementer must know before writing the field:

1. **The class is `IsmsChange`, not `ISMSChange`.** `reports/models/management_review.py` declares `class IsmsChange`, and `ManagementReviewDecision.linked_isms_change` references it as `"reports.IsmsChange"`. Use that exact spelling in the M2M string reference.
2. **`IsmsChange.review` is a required `CASCADE` FK to `ManagementReview`.** An ISMS change cannot exist outside a management review. The post-incident review therefore **links** an existing change; it cannot create one from its own page. The real workflow is the correct one : the review concludes the ISMS must change, the change is tabled at the next management review as a clause 9.3.3 output, and it is linked back from here. The picker's empty state says so and links to the management review module rather than offering a create button that cannot work.
3. **`IsmsChange` is a plain `models.Model`, not a `BaseModel`** : no `scopes`, no `workflow_state`, no lifecycle, no `HistoricalRecords`-backed lifecycle events, and a plain `status` column (`proposed`, `approved`, `in_progress`, `implemented`, `rejected`). `linkable_or_linked()` returns the queryset unchanged for a model with no lifecycle field, so the picker filters on `status` instead and excludes `rejected`. This is the single place in the module where RG-INC-37's governance-helper rule does not apply, because the target has no governance to consult.
4. **The `CASCADE` on `IsmsChange.review` is a real exposure.** Deleting a management review destroys its ISMS changes, and the incident's clause 10.2 e) evidence silently becomes an empty list rather than an error, because an M2M link disappears with its target. Hardening that FK belongs to the management-review module, not to m6; m6 states the limit and the review detail page renders "no ISMS change recorded" rather than implying none was ever needed.

## Effectiveness verification : the clause 10.2 d)/f) record

This is the reason the lifecycle has a step after `approved`.

The action-plan lifecycle proves that an action was **implemented**. Its steps run `new` -> `to_define` -> `to_validate` -> `to_implement` -> `implementation_to_validate` -> `validated` -> `closed` (`compliance/lifecycles.py` `_action_plan_steps()`), and the validation in `implementation_to_validate -> validated` is validation *of the implementation* : somebody confirms the thing was done. Nothing in that machine, or anywhere else in the platform before m6, records whether it **worked**.

Clause 10.2 d) requires the organisation to review the effectiveness of any corrective action taken, and 10.2 f) requires documented information on the results. A closed action plan answers neither. That is a platform-wide gap, not an incident-module gap, which is why phase 0 mirrors the same three fields onto `compliance.Finding` : an audit nonconformity gets the identical record.

The mechanism:

1. `submitted -> approved` requires `effectiveness_review_date` (**gate GP-03**). Approval is not allowed to be the end of the story, and the date lands on the calendar feed and in `build_upcoming_deadlines` the same day.
2. When that date falls due, `POST_INCIDENT_REVIEW_DUE` notifies the facilitator and the participants.
3. `approved -> effectiveness_verified` requires `incidents.review.approve`, a mandatory comment, a non-blank `effectiveness_verdict` and a non-null `effectiveness_reviewed_by` (**gate GP-04**, RG-INC-32). It stamps `effectiveness_reviewed_at` and propagates the verdict onto every linked `Finding`, copying `effectiveness_verdict`, `effectiveness_reviewed_at` and `effectiveness_reviewed_by`.
4. The propagation is a **snapshot at that instant, not a live mirror**. The review's verdict is the aggregate judgement; a nonconformity whose individual verdict differs is edited on the finding itself afterwards, and the finding's own history records the divergence. Nothing re-writes a finding after this transition.

The propagation respects RG-FND-06 : a finding with no linked `ComplianceActionPlan` in a reportable state and no recorded justification for having none is **skipped** rather than stamped, and the transition reports which findings it skipped. A verdict about the effectiveness of nothing is not a record, and the review is not allowed to manufacture one in bulk.

`not_effective` and `partially_effective` are first-class outcomes, not failure states. A verified-ineffective corrective action is a *better* record than a closed action plan with no verdict at all : it is the input that produces the next nonconformity. The review does not reopen itself on a `not_effective` verdict, and the module deliberately does not automate that : deciding what to do about a corrective action that did not work is a management judgement, and the honest artefacts of it are a new `Finding` and a new `ComplianceActionPlan`, both reachable from the same page.

Self-verification is permitted and **visible** : `facilitator` and `effectiveness_reviewed_by` are rendered side by side in the sidebar, so a review verified by the person who ran it reads as exactly that.

## Lifecycle

`LIFECYCLE_NAME = "post_incident_review"`, `layout="graph"`, generated by `lifecycle_from_state_flags()` in `incidents/lifecycles.py` from the state and transition constants in `incidents/constants.py`, and registered from `IncidentsConfig.ready()`.

Unlike `incident` and `incident_evidence`, this lifecycle needs no step trigger, so it keeps the generated form the project's rules prescribe. It declares **both** bookend steps explicitly : see [The archive and restore bookends](#the-archive-and-restore-bookends).

> `lifecycle_name_for()` (`core/lifecycle.py` `lifecycle_name_for()`) resolves `LIFECYCLE_NAME` only `if name and name in LIFECYCLE_REGISTRY`. An `incidents/apps.py` whose `ready()` forgets to import `incidents.lifecycles` therefore **fails silently** : this model would quietly run the default 4-state lifecycle, with no `effectiveness_verified` step and no gates, in tests as well as in production, and RG-INC-14 would then compare the incident's review against steps that do not exist. The module ships a test asserting `PostIncidentReview.get_lifecycle().name == "post_incident_review"`.

### Steps

Eight steps : one draft entry, four review stages, two domain terminal exits and the generic archived exit.

| Code | Label | StepKind | In reports | Linkable | Deletable | Tone | Meaning |
|---|---|---|---|---|---|---|---|
| `draft` | Draft | `DRAFT` | no | no | **yes** | `neutral` | A review row that exists but has not been opened. The landing step of every insert (see [Creation and the initial step](#creation-and-the-initial-step)). |
| `scheduled` | Scheduled | `INTERMEDIATE` | **yes** | no | **yes** | `secondary` | The learning phase is open. Created automatically on the incident's `recovered -> post_incident_review` transition; `scheduled_date` may still be blank. |
| `in_progress` | In progress | `INTERMEDIATE` | **yes** | no | no | `info` | Being held and written up. `held_at` is stamped on entry. |
| `submitted` | Submitted | `INTERMEDIATE` | **yes** | **yes** | no | `primary` | Root cause determined and recurrence checked, awaiting approval |
| `approved` | Approved | `INTERMEDIATE` | **yes** | **yes** | no | `success` | **The minimum state an incident needs to close** (RG-INC-14). The effectiveness review is scheduled. |
| `effectiveness_verified` | Effectiveness verified | `ARCHIVED` (terminal) | **yes** | **yes** | no | `dark` | The clause 10.2 d)/f) record : the corrective actions were verified and a verdict is on file |
| `cancelled` | Cancelled | `ARCHIVED` (terminal) | no | no | no | `muted` | The review of an incident that turned out not to be one. See [gate GP-06](#transition-gates). |
| `archived` | Archived | `ARCHIVED` | no | no | no | `muted` | The generic exit, declared **explicitly** |

`effectiveness_verified` keeps `counts_in_reports = True` and stays `linkable` : a verified review is exactly what the annual register, the management review and the A.5.27 evidence pack are about, and a terminal step here means *finished*, not *withdrawn*. `cancelled` does not count, because the review never concluded anything.

`scheduled` and `submitted` are the two steps where the governance flags carry real weight. `scheduled` is `deletable = True` only so a review created by hand in error can be removed without an approver; `delete()` is overridden to refuse the automatic case (see [Deleting a review](#deleting-a-review)). `submitted` is the first `linkable` step, so a review cannot be quoted from a report or attached anywhere until its root cause has actually been determined.

### Transitions

`permission_action` is the suffix appended to `workflow_perm_namespace` (`incidents.review`), so `update` means `incidents.review.update` and `approve` means `incidents.review.approve`.

| Verb | Transition | `permission_action` | `requires_comment` | Side effects |
|---|---|---|---|---|
| Schedule | `draft -> scheduled` | `update` | no | Hand-declared. The step every auto-created review is moved to immediately after insert. |
| Hold the review | `scheduled -> in_progress` | `update` | no | Stamps `held_at` |
| Submit | `in_progress -> submitted` | `update` | no | **Gate GP-02.** Normalises every row in `raised_findings` (`source`, `incident`, `assessor`). |
| Send back for rework | `submitted -> in_progress` | `update` | **yes** | The comment is the approver's reason. `held_at` is **not** re-stamped (write-once). |
| Approve | `submitted -> approved` | **`approve`** | **yes** | **Gate GP-03.** Requires `effectiveness_review_date`; re-runs the finding normalisation. |
| Verify effectiveness | `approved -> effectiveness_verified` | **`approve`** | **yes** | **Gate GP-04.** Stamps `effectiveness_reviewed_at`; propagates the verdict onto each linked `Finding`. |
| Cancel | `* -> cancelled` | **`approve`** | **yes** | **Gate GP-06.** |
| Archive | `* -> archived` | **`approve`** | **yes** | Hand-declared, not auto-wired |
| Restore | `archived -> draft` | **`approve`** | no | Hand-declared, and refused by gate GP-05 |

There is **no** `lifecycle_transition_url_name` override : every transition posts to the generic `workflow:transition` endpoint, and every gate below lives on the model.

Two engine behaviours are worth naming, because both are easy to assume away:

- `transitions_from()` (`core/lifecycle.py` `Lifecycle.transitions_from()`) matches a transition whose source is `ANY` from **every** step except the target itself, and does not exclude terminal steps. Left ungated, `Cancel` would be offered from `effectiveness_verified` and from `archived`, and `Archive` from `cancelled`. Gate GP-06 closes the first; the archive edge from a terminal step is harmless and is left alone.
- `BaseModel.transition_to()` fires `notify_lifecycle_submitted` (RG-LC-06) only when `lifecycle.name == DEFAULT_LIFECYCLE_NAME and target == "pending"` (`context/models/base.py` `BaseModel.transition_to()`). A bespoke lifecycle's `submitted` step therefore fires **nothing**, whatever it is called. The approval request on this entity is an explicit module notification, not an inherited one.

### The archive and restore bookends

`lifecycle_from_state_flags()` auto-wires `draft -> <initial step>`, `ANY -> archived` and `archived -> draft` only when the corresponding step is absent from the state-flag list (`core/lifecycle.py` `lifecycle_from_state_flags()`). The auto-wired archive and restore edges carry **no `permission_action` and no `requires_comment`**, and `user_can_perform()` (`core/lifecycle.py` `user_can_perform()`) allows any transition whose `permission_action` is empty.

Because `draft` and `scheduled` are both `deletable = True`, leaving those edges generated would give anyone able to reach the transition endpoint an **archive -> restore -> delete** path out of an approved review. On this entity that path destroys the A.5.27 record an incident was closed on, and with it the only evidence that closure was ever legitimate : the incident stays `closed`, and the gate that let it close no longer exists.

The lifecycle therefore:

1. declares `draft` **and** `archived` explicitly among its state-flag items, so `has_draft` and `has_archived` are both `True` and nothing is auto-wired;
2. hand-declares `ANY -> archived` with `permission_action="approve"` and `requires_comment=True`;
3. hand-declares `archived -> draft` with `permission_action="approve"`, additionally gated by GP-05;
4. hand-declares the `draft -> scheduled` entry edge, which is no longer auto-wired either.

All four edges are listed in `POST_INCIDENT_REVIEW_TRANSITIONS` in `incidents/constants.py` with explicit actions, so the state literals stay in one file (RG-INC-37). The same correction is applied to every lifecycle in the module. [IncidentResponsePlan](incident-response-plan.md) needs none of it : it runs the core `default` lifecycle, whose archive edge already carries `permission_action="approve"` and which has no restore transition at all.

The module ships a regression test that walks a review from `approved` to `archived`, attempts `archived -> draft` as a holder of `incidents.review.update`, and asserts both that the transition is refused and that the row still exists.

### Transition gates

Per RG-INC-08, every gate below lives in a `transition_to()` override on `PostIncidentReview`, **never** in `Transition.form_class`, `allowed_roles` or `allowed_users`. `lifecycle_to_json()` (`core/lifecycle.py` `lifecycle_to_json()`) omits those three by design, `lifecycle_from_json()` (`core/lifecycle.py` `lifecycle_from_json()`) rebuilds transitions without them, and `get_lifecycle()` (`core/lifecycle.py` `get_lifecycle()`) prefers the `post_migrate`-seeded `LifecycleDefinition` row over the code default, so a gate declared that way is green in an in-memory unit test and absent on every migrated database. All three write surfaces funnel through `BaseModel.transition_to()` (`core/workflow_views.py` `WorkflowTransitionView.post()`, `accounts/api/mixins.py` `_lifecycle_transition()`, `mcp/tools.py` `_transition_handler()`), so the model override is the one place that binds web, API and MCP at once.

Each gate raises a translated `ValidationError` naming the missing precondition, before `perform_transition()` runs, and the whole transition body runs inside `transaction.atomic()`. Gate identifiers are local to this entity.

| Gate | Transition | Refused unless |
|---|---|---|
| **GP-01 Opening** | `scheduled -> in_progress` | The parent incident is in `post_incident_review` or later. Holding a review for an incident still being contained is not a review, it is a status meeting. Stamps `held_at`. |
| **GP-02 Submission** (RG-INC-32) | `in_progress -> submitted` | `root_cause` is non-blank **and** `similar_incidents_checked` is `True`. Clause 10.2 b) and b) 3). The transition then normalises `raised_findings` : `source = incident`, `incident = review.incident`, and `assessor = facilitator or user` where blank. |
| **GP-03 Approval** (RG-INC-32) | `submitted -> approved` | Holder of `incidents.review.approve`, a mandatory comment, **and** a non-null `effectiveness_review_date`. Approving a review with no verification date scheduled is how clause 10.2 d) is missed, so the gate refuses it rather than trusting a reminder. |
| **GP-04 Effectiveness verdict** (RG-INC-32) | `approved -> effectiveness_verified` | Holder of `incidents.review.approve`, a mandatory comment, a non-blank `effectiveness_verdict` **and** a non-null `effectiveness_reviewed_by`. Stamps `effectiveness_reviewed_at` and propagates the verdict onto each linked `Finding`. |
| **GP-05 Restore** | `archived -> draft` | No `core.LifecycleEvent` on this review records a step other than `draft` or `archived`. A review that ever reached `scheduled` can be archived but never restored into a deletable step. Mirrors [Incident](incident.md) G-07. |
| **GP-06 Cancellation** | `* -> cancelled` | The parent incident is itself in a terminal step (`reclassified` or `archived`), and the current step is not already terminal. A live incident must have a live review to reach closure, so there is deliberately **no** path that leaves a closeable incident holding a cancelled one; and because the `OneToOne` is `PROTECT` and RG-INC-31 allows exactly one review per incident, a cancelled review can never be replaced. This is also why no `cancelled -> scheduled` edge exists : a reclassified incident's review is not resumed, and a reclassified incident cannot be un-reclassified. |
| **GP-07 Write-once stamps** (RG-INC-12) | all | `held_at` and `effectiveness_reviewed_at` are stamped by the override only : excluded from every `ModelForm`, `read_only` in every serializer, absent from every MCP `writable_fields` list, and never cleared. Write-once is prevented at application level and **detected** through `HistoricalRecords`; `QuerySet.update()`, `bulk_update()` and raw SQL bypass `save()`. |

The closure gate itself lives on the other side of the relation : [Incident](incident.md) G-05 refuses `post_incident_review -> closed` unless this review exists and is in `approved` or `effectiveness_verified`. Membership is tested against the step codes exported from `incidents/constants.py`, never against literals (RG-INC-37).

### Creation and the initial step

`BaseModel.save()` calls `_ensure_initial_step()` (`context/models/base.py` `BaseModel._ensure_initial_step()`) on every insert, and `Lifecycle.initial_step` (`core/lifecycle.py` `Lifecycle.initial_step`) returns the single `StepKind.DRAFT` step. The `workflow_state` field default is the literal `"draft"`, which **is** a valid step of this lifecycle, so `_ensure_initial_step()` leaves it alone and the row lands in `draft`.

**A review is never "created in" `scheduled`.** Writing `PostIncidentReview.objects.create(..., workflow_state="scheduled")` would stick - the snap only fires on a blank or unknown value - but it would leave **no `core.LifecycleEvent` row**, so the review would exist with no record of ever having been opened. A review left in `draft` because nobody made the second call is worse still : `draft` is `deletable = True`, the review is missing from every "reviews to hold" list, and it silently blocks incident closure through RG-INC-14 with no explanation on any screen.

The incident's `recovered -> post_incident_review` transition therefore does, inside one `transaction.atomic()` block:

```python
review = PostIncidentReview(incident=incident, response_plan=incident.response_plan)
review.save()
review.scopes.set(incident.scopes.all())
review.transition_to("scheduled", user, enforce_permission=False)
```

`enforce_permission=False` is correct here : the permission was already checked on the **parent** transition the user actually performed, and the review is a consequence of it, not a separate act by the user. The creation is idempotent : the transition creates the review only when `incident.post_incident_review` does not already exist, so re-entering `post_incident_review` after a reopen never produces a second row and never resets the first.

`facilitator`, `scheduled_date` and every narrative field are left blank. Nothing is guessed : a review with no facilitator and no date is visibly unstarted, which is the true state of affairs the moment service is restored.

The module ships regression tests asserting that `PostIncidentReview.objects.create(...).workflow_state == "scheduled"` **fails**, that after `incident.transition_to("post_incident_review", user)` the review is in `scheduled` with exactly one matching `core.LifecycleEvent`, and that a second entry into that step leaves the review count and the `LifecycleEvent` count unchanged.

### Deleting a review

`delete()` is overridden to refuse any review whose parent incident has not reached a terminal step, mirroring the [IncidentNotification](incident-notification.md) override that refuses to delete a generated obligation. The reason is the same in both cases : the row is the answer to a question the platform asked on the organisation's behalf, and deleting it destroys the evidence that the question was ever considered. Concretely, deleting an auto-created review would strand its incident, which can then never close (RG-INC-14) and can never obtain a second review (RG-INC-31, `OneToOne`).

From `in_progress` onward no step is deletable on any surface, so `BaseModel.delete()` raises `LifecycleProtectedError` before the override is even consulted. And `PROTECT` on `incident` means the incident can never be deleted while its review exists, which from `detected` onward it already could not be (RG-INC-07).

## Scope tenancy

**RG-INC-38.** `PostIncidentReview` is a `ScopedModel` and carries its own `scopes`, so `ScopeFilterMixin` (`accounts/mixins.py` `ScopeFilterMixin.get_queryset()`) and `ScopeFilterAPIMixin` (`accounts/api/mixins.py` `get_queryset()`) filter its list view and viewset with no extra work, and `mcp/tools.py` `_filter_by_scopes()` handles the direct `scopes` M2M it already supports. Unlike [IncidentEvidence](incident-evidence.md) and [IncidentNotification](incident-notification.md), this entity needs **none** of the three `scope_parent_lookup` call-site extensions phase 1 makes, and its `workflow:transition` and history endpoints are already guarded correctly today.

That is exactly why the scopes must not be allowed to drift. They are copied from the incident at creation **and re-synced by `Incident.save()`** whenever the incident's scopes change (RG-INC-31). Without the re-sync, re-scoping an incident would leave its review visible to the old tenant and invisible to the new one, and the review is where the root cause is written down.

The seed and the tests both assert `set(review.scopes.all()) == set(review.incident.scopes.all())` after a re-scope.

## Business rules

| ID | Rule |
|---|---|
| RG-INC-08 | Every audit gate is enforced in a `transition_to()` override on the model, never through `Transition.form_class`, `allowed_roles` or `allowed_users`, because `lifecycle_to_json` drops those and the seeded `LifecycleDefinition` row wins at runtime. |
| RG-INC-12 | `held_at` and `effectiveness_reviewed_at` are stamped by the `transition_to()` override only. They are excluded from every `ModelForm`, are `read_only` in every serializer, and are absent from every MCP `writable_fields` list. Prevention at application level, detection via `HistoricalRecords`. |
| RG-INC-14 | An incident cannot reach `closed` while its post-incident review is in any step other than `approved` or `effectiveness_verified`. The gate lives in `Incident.transition_to()` and applies identically to the web stepper, DRF and MCP. |
| RG-INC-17 | An exercise (`is_exercise = True`) still requires a review to close : the review **is** the A.5.24 exercise report, and its `what_failed` and `response_plan_update_required` fields are the plan-testing evidence. It runs the identical lifecycle with identical gates, and is excluded from every KPI, indicator, report, calendar deadline and dashboard count. |
| RG-INC-31 | Exactly one `PostIncidentReview` per incident (`OneToOne`, `PROTECT`), created automatically on entry to `post_incident_review` : saved, then transitioned to `scheduled` with `enforce_permission=False` in the same transaction. Its scopes are copied from the incident at creation **and** re-synced by `Incident.save()` whenever the incident's scopes change, so the review can never drift out of scope alignment. |
| RG-INC-32 | Leaving `in_progress` requires a non-blank `root_cause` and `similar_incidents_checked = True`; reaching `approved` additionally requires an `effectiveness_review_date`; reaching `effectiveness_verified` requires `incidents.review.approve`, a mandatory comment, a non-blank `effectiveness_verdict` and a non-null `effectiveness_reviewed_by`. This is the ISO 27001 clause 10.2 d)/f) record the platform does not hold today. |
| RG-INC-34 | A nonconformity raised by a review is a `compliance.Finding` with `source = incident` and `incident` set, `assessment` left null : the **one** ISO clause 10.2 register. A risk revealed by an incident is a `risks.Risk` with `risk_source = RiskSourceType.INCIDENT` and the existing generic back-pointer. No second nonconformity model, no new FK on `Risk`. |
| RG-INC-35 | Corrective work is recorded exclusively as `compliance.ComplianceActionPlan` rows linked from `corrective_action_plans`. [IncidentResponseAction](incident-response-action.md) exists only for in-incident operational steps and carries a plain status column, never a lifecycle. |
| RG-INC-36 | An incident realising a risk that carries an active `risks.RiskAcceptance` forces that acceptance under review, through a derived query hung off the existing `expire_risk_acceptances` sweep. `risk_reassessment_required` on the review is the manual counterpart, and both fire `RISK_REVIEW_TRIGGERED_BY_INCIDENT`. |
| RG-INC-37 | Every report, KPI, indicator, calendar feed and link picker filters through `reportable()` / `linkable()` / `linkable_or_linked()` / `deletable_states()`. No review state literal appears anywhere outside `incidents/constants.py`. The single documented exception is the `isms_changes` picker, whose target has no lifecycle at all. |
| RG-INC-38 | Scope tenancy : `PostIncidentReview` carries its own `scopes` (`ScopedModel`) and needs none of the `scope_parent_lookup` extensions the module's non-scoped children require. |
| RG-INC-39 | The module has exactly six permission features and never grows. `incidents.review` gates this entity and nothing else. |

## Endpoints

### REST

Base path `/api/v1/incidents/`, router registration `post-incident-reviews`.

- `GET /api/v1/incidents/post-incident-reviews/` : list, filtered by `PostIncidentReviewFilter` (`incident_id`, `status`, `facilitator_id`, `root_cause_method`, `recurrence_likelihood`, `effectiveness_verdict`, `risk_reassessment_required`, `response_plan_update_required`, `training_required`, `scheduled_after` / `scheduled_before`, `effectiveness_review_before`, `scope_id`)
- `POST /api/v1/incidents/post-incident-reviews/` and `POST /api/v1/incidents/post-incident-reviews/batch/` (max 100 items, non-atomic, per-item `{index, status, id, reference}`)
- `GET/PUT/PATCH/DELETE /api/v1/incidents/post-incident-reviews/<uuid>/` : `DELETE` succeeds only under the conditions in [Deleting a review](#deleting-a-review); otherwise the endpoint returns 409
- `GET/POST /api/v1/incidents/post-incident-reviews/<uuid>/transition/` : supplied by `LifecycleAPIMixin`, routed through `transition_to(enforce_permission=True)`, so every gate above applies identically to an API caller
- `GET /api/v1/incidents/post-incident-reviews/<uuid>/history/` : `core.history.build_timeline`, merging `LifecycleEvent` and `HistoricalRecords`

Viewset stack in the house order : `BatchCreateMixin`, `ScopeFilterAPIMixin`, `LifecycleAPIMixin`, `HistoryAPIMixin`, `CreatedByMixin`, `viewsets.ModelViewSet`. Permissions follow the newest module precedent (`trust_center/api/views.py` `_ManagedViewSet`) : `ModulePermission` directly, plus the module's `_IncidentViewSet` base fixing `permission_module = "incidents"` and `custom_action_map = {"transition": "update"}`, with `permission_feature = "review"` on this viewset. Another app's `ModulePermission` subclass (`ContextPermission`) is **not** imported.

Two serializers : `PostIncidentReviewSerializer` (full) and `PostIncidentReviewListSerializer` for the index, switched on `self.action == "list"`. `read_only_fields` cover `id`, `reference`, `created_by`, `created_at`, `updated_at`, `version`, `held_at` and `effectiveness_reviewed_at`. `status` is exposed as `CharField(source="workflow_state", read_only=True)`, and `incident_reference`, `facilitator_name` and `effectiveness_reviewed_by_name` as read-only display fields backed by model properties. `incident` is writable on create and `read_only` on update : re-pointing an existing review at a different incident would silently strand the first one.

Phase 0 additionally exposes `/api/v1/compliance/findings/` as a standalone router registration : findings have no standalone route today, every finding URL being nested under an assessment, which an incident-born nonconformity has none of.

### MCP

- `_register_crud(server, "post_incident_review", PostIncidentReview, "incidents.review", ...)` generates `list_post_incident_reviews`, `get_post_incident_review`, `create_post_incident_review`, `batch_create_post_incident_reviews`, `update_post_incident_review`, `delete_post_incident_review`, `transition_post_incident_review`, `post_incident_review_allowed_transitions`, `get_post_incident_review_history`.
- Filters : `incident_id`, `status`, `facilitator_id`, `root_cause_method`, `effectiveness_verdict`. Search fields : `reference`, `root_cause`, `detection_gap`, `what_failed`.
- `m2m_fields` maps `scope_ids`, `tag_ids`, `participant_ids`, `raised_finding_ids`, `corrective_action_plan_ids`, `failed_control_ids`, `control_to_strengthen_ids`, `identified_risk_ids`, `identified_vulnerability_ids` and `isms_change_ids`.
- The entity is a `ScopedModel`, so `_register_crud` is called with the default `scope_filtered=True` and **no** `scope_parent_lookup` argument : `_filter_by_scopes()` already handles a direct `scopes` M2M.
- `root_cause_method`, `recurrence_likelihood` and `effectiveness_verdict` each carry a `field_overrides` entry with an explicit `enum` list; every FK id argument names its lookup tool in its description (`Use list_incidents to get valid IDs`, `Use list_findings to get valid IDs`, `Use list_isms_changes to get valid IDs`); `held_at` and `effectiveness_reviewed_at` never appear in `writable_fields`.
- Attaching a nonconformity through `raised_finding_ids` requires `incidents.review.update`; **creating** one requires `compliance.finding.create`, the phase 0 re-gating of the existing `create_finding` tool away from `compliance.assessment.create`. An agent that holds only incident permissions can link an existing finding and cannot invent one.

`mcp/tools.py` `HELP_TEXT` gains `PostIncidentReview=PIRV` in the reference-prefix block, and the entity gets its own section in `TOPIC_INCIDENTS` listing writable fields, enum values, filters and the reference prefix.

## Permissions

| Codename | Description |
|---|---|
| `incidents.review.read` | List and read post-incident reviews |
| `incidents.review.create` | Create a review by hand (the normal path creates it automatically) |
| `incidents.review.update` | Edit the narrative and the outward links, schedule, hold and submit the review, send it back for rework |
| `incidents.review.approve` | Approve a review, record the effectiveness verdict, cancel, archive, restore |
| `incidents.review.delete` | Delete a review under the conditions above |

`incidents.review` is one of the module's exactly six permission features (`incident`, `security_event`, `evidence`, `notification`, `review`, `response_plan`), each with the five standard `PermissionAction` verbs and no custom ones, so the six `SYSTEM_GROUPS` suffix lambdas grant them unchanged and the group matrix screen, which renders a hardcoded action list, displays every one of them (RG-INC-39). The rows are created and attached to the six system groups by `accounts/migrations/0056_add_incidents_permissions.py`.

`workflow_perm_namespace = "incidents.review"` is **mandatory** on this model : without it the namespace resolves to `incidents.postincidentreview`, which matches no registry feature, and every lifecycle permission check on the entity silently evaluates against a codename nobody holds.

Phase 0's separate `compliance.finding` feature gets its own `accounts` data migration in the same release. Note that granting `incidents.review.update` does **not** grant the ability to create a nonconformity : that needs `compliance.finding.create`, deliberately, because a nonconformity is a compliance record wherever it comes from.

## UI

**List** (`/incidents/post-incident-reviews/`) : the house stack (`LoginRequiredMixin`, `PermissionRequiredMixin`, `ListSummaryMixin`, `PredefinedFilterMixin`, `AdvancedFilterMixin`, `SavedFilterMixin`, `ColumnPreferenceMixin`, `ScopeFilterMixin`, `SortableListMixin`, `ListView`, with `ListSummaryMixin` strictly left of `ScopeFilterMixin`), `page_header` with `accent="incidents"`, an `#item-table-body` HTMX partial and the filter offcanvas. Columns : reference, incident (reference and title), state, facilitator, `scheduled_date`, `held_at`, root cause method, `effectiveness_review_date` and the effectiveness verdict. A review whose `effectiveness_review_date` has passed while it is still in `approved` is flagged in the row : that is an open clause 10.2 d) obligation, and it is the single most useful thing this list shows.

**Detail** (`/incidents/post-incident-reviews/<uuid>/`) : a **strict 2-column card layout, no nav-tabs**.

- Left column, stacked cards:
  - **Root cause** : `root_cause_method` rendered as a chip beside `root_cause`, then `contributing_factors`, `detection_gap` and `containment_assessment`. The method chip sits *before* the cause on purpose.
  - **What went well / what failed** : two columns on desktop, stacked on mobile, with `recurrence_likelihood` and the `similar_incidents_checked` state rendered as a labelled pair rather than a bare checkbox.
  - **Outcomes** : the outward links, each as its own labelled block with an inline picker and a *create and attach* action : raised findings (with their type and state), corrective action plans (with owner, target date and progress), identified risks, identified vulnerabilities, failed controls, controls to strengthen, ISMS changes, and the three flags (`risk_reassessment_required`, `response_plan_update_required`, `training_required`) rendered as consequences with a link to the thing each one points at. The ISMS changes block shows a "no ISMS change recorded" empty state linking to the management review module, never a create button.
  - **Effectiveness** : `effectiveness_review_date`, `effectiveness_verdict`, `effectiveness_reviewed_by`, `effectiveness_reviewed_at` and `effectiveness_notes`. Before verification the card renders the scheduled date with a relative hint and, once past, a warning state.
- Right column, sticky sidebar : `{% workflow_badge %}`, the parent incident link with its own state badge, facilitator and `effectiveness_reviewed_by` **side by side** so self-verification is visible, participants as avatars, `scheduled_date` and `held_at`, the response plan link, scopes, tags, the history trigger and the lifecycle stepper.

**Stepper** : `{% include "includes/lifecycle_stepper.html" %}` fed by `LifecycleStepperMixin`. Never a status select, never plain buttons. This lifecycle has three `StepKind.ARCHIVED` steps (`effectiveness_verified`, `cancelled`, `archived`), so the dagre renderer draws three detached exits and needs an explicit visual check at desktop and mobile widths in **both** light and dark mode before merge. The transitions carrying a mandatory comment (approve, verify, send back, cancel, archive) all use the stepper's shared comment modal; no bespoke form is added.

**On the incident detail page**, the review appears as a summary card in the left column : state badge, facilitator, `scheduled_date`, a one-line root-cause extract, the counts of raised findings and corrective action plans, and a link through. When the incident is in `post_incident_review` and the review is not yet approved, the card states plainly that closure is blocked and why, so the operator never has to deduce the gate from a greyed-out stepper pill.

Create and update use `HtmxFormMixin` drawer modals, with mobile-first care on the eight multi-select widgets in the Outcomes card and on the sticky action bar : this is, after the response plan, the second-tallest form in the module, and on small screens the outcome pickers render as an accordion so the action bar stays reachable.

`scheduled_date` and `effectiveness_review_date` are both fed into the calendar under the `incident` category and into `build_upcoming_deadlines`. Reviews belonging to an exercise incident are excluded from both feeds (RG-INC-17).

## Notifications

| Type | Fired when | Recipients | Channel |
|---|---|---|---|
| `POST_INCIDENT_REVIEW_DUE` | `scheduled_date` or `effectiveness_review_date` falls due, swept daily by `escalate_incident_deadlines` | The facilitator and the participants | In-app |
| `RISK_REVIEW_TRIGGERED_BY_INCIDENT` | The review sets `risk_reassessment_required`, or an incident realises a risk carrying an active `RiskAcceptance` (RG-INC-36) | The risk owners and the acceptance owner | In-app, email |

Both follow `notify_lifecycle_submitted` : the in-app rows are created in the same transaction as the change, rendered per recipient under `translation.override(recipient.language)`, with email and WebSocket delivery scheduled on `transaction.on_commit()` so a rolled-back transition sends nothing. No new notification model is needed : `accounts.Notification` already targets any object through a `GenericForeignKey`, and naming the route `incidents:post-incident-review-detail` makes `_target_url` resolve with no special casing.

There is deliberately no *review submitted for approval* notification of the RG-LC-06 kind, because that helper fires only for the core `default` lifecycle's `pending` step. If one is wanted it is an explicit module notification with its own `NotificationType` value, not something inherited by naming a step `submitted`.

## Translations

Every user-facing string is wrapped with `_()` / `pgettext_lazy()` in Python or `{% trans %}` in templates and has a French translation in `locale/fr/LC_MESSAGES/django.po`. A duplicate `(msgctxt, msgid)` pair makes `manage.py compilemessages` fail, and `.github/workflows/tests.yml` runs `compilemessages` **before** `pytest`, so a collision breaks CI outright.

**Enum labels, field verbose names and template strings** whose English already exists in the catalogue use `pgettext_lazy("incident", ...)` in Python and `{% trans "..." context "incident" %}` in templates, with a matching `msgctxt "incident"` block in the `.po`. For this entity that is a single label:

| Label | Where | Existing bare entry | Decision |
|---|---|---|---|
| `Other` | `RootCauseMethod.OTHER` | present four times, bare entry `msgstr "Autre"` | `pgettext_lazy("incident", "Other")`. This is the **same** `(msgctxt, msgid)` pair `DetectionSource.OTHER` already declares in [Incident](incident.md) : gettext merges the two occurrences into one entry with several `#:` references, which is not a duplicate. Declare the `.po` entry once. |

`Facilitator` (`msgstr "Animateur"`), `Participants`, `Notes`, `Findings` and `ISMS changes` already exist with a French translation that is correct in this context, so the same `msgid` is reused and **no new entry is added**. Every other field verbose name is a new bare `msgid` : "Scheduled date", "Held at", "Root cause method", "Root cause", "Contributing factors", "Detection gap", "Containment assessment", "What went well", "What failed", "Recurrence likelihood", "Similar incidents checked", "Risk reassessment required", "Response plan update required", "Training required", "Effectiveness review date", "Effectiveness reviewed at", "Effectiveness reviewed by", "Effectiveness verdict", "Effectiveness notes", "Raised findings", "Corrective action plans", "Failed controls", "Controls to strengthen", "Identified risks", "Identified vulnerabilities". The three `EffectivenessVerdict` labels ("Effective", "Partially effective", "Not effective"), declared by phase 0 in `compliance`, and the five non-`other` `RootCauseMethod` labels ("5 Whys", "Ishikawa", "Fault tree analysis", "Timeline analysis", "Barrier analysis") are likewise new. `recurrence_likelihood` renders `context.constants.Criticality`, whose labels are already in the catalogue and are not re-declared here.

**Step and transition labels are different, and must never use `pgettext_lazy`.** `lifecycle_to_json()` stringifies each label with `str(...)` and `lifecycle_from_json()` re-wraps the stored string with **bare** `gettext_lazy` (`core/lifecycle.py` `lifecycle_from_json()`), so a label carrying a `msgctxt` in code loses that context after the `post_migrate` round-trip through `LifecycleDefinition` and resolves to whatever the bare `msgid` maps to. A collision-free English label is the only correct fix; a context is not.

This lifecycle is fortunate, and the reason is worth recording so nobody "improves" it later : the French for *post-incident review* is **revue post-incident**, which is feminine, and every colliding bare entry is already in the feminine.

| Label | Existing bare entry | Decision |
|---|---|---|
| `draft` step "Draft" | `Draft` -> "Brouillon" | **Reuse.** The core `draft_step()` emits this exact string and the French is correct. |
| `in_progress` step "In progress" | `In progress` -> "En cours" (two entries : one bare, one with `msgctxt "isms change status"`) | **Reuse the bare entry.** "En cours" is invariable in gender and correct here. |
| `approved` step "Approved" | `Approved` -> "Approuvée" (feminine; a second entry carries `msgctxt "isms change status"`) | **Reuse the bare entry.** Feminine is correct for *revue*. Contrast [Incident](incident.md), whose `closed` step had to be renamed because the bare "Closed" is "Clôturée". |
| `cancelled` step "Cancelled" | `Cancelled` -> "Annulée" (five entries; the bare one plus `assessment`, `action_plan`, `management review status`, `decision status`) | **Reuse the bare entry.** Feminine is correct. |
| `archived` step "Archived" | `Archived` -> "Archivé" | **Reuse.** The core `archived_step()` emits this exact string. |
| Submit transition "Submit" | `Submit` -> "Soumettre" | **Reuse.** A verb in the infinitive, which is what a transition label must be. |
| Approve transition "Approve" | `Approve` -> "Approuver" | **Reuse.** |
| Cancel transition "Cancel" | `Cancel` -> "Annuler" (bare, plus one with `msgctxt "permission"`) | **Reuse the bare entry.** |
| "Archive" / "Restore" transitions | present as the core bookend labels | **Reuse.** |

The remaining labels are new bare `msgid`s with no collision : the `scheduled` step "Scheduled" -> "Planifiée" (distinct from the existing "Planned", which is a different `msgid`), the `submitted` step "Submitted" -> "Soumise", the `effectiveness_verified` step "Effectiveness verified" -> "Efficacité vérifiée", and the transitions "Schedule", "Hold the review", "Send back for rework" and "Verify effectiveness". "Send back for rework" is deliberately not the core `default` lifecycle's "Send back to draft" : this edge returns the review to `in_progress`, not to `draft`, and a label that lies about its target is worse than a long one.

After editing the `.po`, verify there is no duplicate `msgid` without a distinguishing `msgctxt`.

## References

- ISO/IEC 27001:2022 **A.5.27** (learning from information security incidents), and by reference A.5.24 (planning and preparation), A.5.26 (response), A.6.3 (awareness and training), A.8.8 (technical vulnerability management), A.8.16 (monitoring activities)
- ISO/IEC 27001:2022 **clause 10.1** (continual improvement) and **clause 10.2** a) to f) (nonconformity and corrective action), in particular b) 3), c), d), e) and f)
- ISO/IEC 27001:2022 clause 9.3.2 d) 1) and d) 2) (management review inputs : nonconformities and corrective actions, monitoring and measurement results), reached through the generalised `compliance.Finding` and the module's predefined indicators, and clause 9.3.3 (management review outputs, the home of `reports.IsmsChange`)
- ISO/IEC 27035-1 / -2 : the *learn* phase, whose structure this entity mirrors
- [Incident](incident.md) : the parent, the `recovered -> post_incident_review` transition that creates this row, and the G-05 closure gate that this row governs
- [IncidentResponsePlan](incident-response-plan.md) : the A.5.24 procedure whose `lessons_learned_procedure` governs this review, and the plan `response_plan_update_required` sends work back to
- [IncidentEvidence](incident-evidence.md) : the A.5.28 artefacts a review reasons from, and the module-wide archive / restore correction
- [IncidentNotification](incident-notification.md) : the `delete()` override pattern this entity mirrors
- [IncidentResponseAction](incident-response-action.md) : in-incident operational steps, deliberately not corrective actions (RG-INC-35)
- [SecurityEvent](security-event.md) : where a weakness identified by a review is reported when it is found outside an incident
- [README.md](README.md) : module business rules, permission codenames, notifications and the phase-0 `compliance.Finding` generalisation
- [governance/workflow.md](../governance/workflow.md) and [governance/lifecycle.md](../governance/lifecycle.md) : the lifecycle framework, `LifecycleEvent` and the engine internals
- [Finding](../m3-compliance/finding.md) : the nonconformity register phase 0 generalises, and the entity spec the `source`, `incident`, `assessor` and effectiveness changes must be reflected in
- [ComplianceActionPlan](../m3-compliance/compliance-action-plan.md), [Requirement](../m3-compliance/requirement.md)
- [Risk](../m4-risks/risk.md), [RiskAcceptance](../m4-risks/risk-acceptance.md), [Vulnerability](../m4-risks/README.md)
- [IsmsChange](../management-review/isms-change.md) and [Decision](../management-review/decision.md) : the clause 9.3.3 outputs `isms_changes` links to
